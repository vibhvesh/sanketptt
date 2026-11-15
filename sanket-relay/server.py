#!/usr/bin/env python3
"""Standalone local-first Sanket WebSocket relay pilot."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import secrets
from collections import defaultdict
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

CONFIG_PATH = Path(os.environ.get("SANKET_RELAY_CONFIG", "/etc/sanket-relay/config.json"))
logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
log = logging.getLogger("sanket-relay")
CHANNEL_RE = re.compile(r"^[A-Za-z0-9_-]{1,48}$")


def load_config() -> dict[str, Any]:
    try:
        cfg = json.loads(CONFIG_PATH.read_text())
    except FileNotFoundError:
        raise RuntimeError(f"Missing config: {CONFIG_PATH}")
    token = str(cfg.get("access_token", ""))
    if len(token) < 32 or token == "REPLACE_WITH_A_LONG_RANDOM_TOKEN":
        raise RuntimeError("Set a strong access_token in config.json")
    cfg.setdefault("host", "0.0.0.0")
    cfg.setdefault("port", 8765)
    cfg.setdefault("max_clients_per_channel", 64)
    cfg.setdefault("max_message_bytes", 262144)
    cfg.setdefault("allowed_channels", [])
    return cfg


CFG = load_config()
CHANNELS: dict[str, set[WebSocket]] = defaultdict(set)
CLIENT_CHANNEL: dict[WebSocket, str] = {}
LOCK = asyncio.Lock()


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Sanket Relay starting on %s:%s", CFG["host"], CFG["port"])
    yield
    log.info("Sanket Relay stopping")


app = FastAPI(title="Sanket Relay", version="0.1.0", lifespan=lifespan)


@app.get("/health")
async def health():
    async with LOCK:
        clients = len(CLIENT_CHANNEL)
        channels = len(CHANNELS)
    return {"status": "ok", "service": "sanket-relay", "clients": clients, "channels": channels}


@app.get("/")
async def root():
    return JSONResponse({"service": "Sanket Relay", "version": "0.1.0", "websocket": "/ws", "health": "/health"})


async def remove_client(ws: WebSocket) -> None:
    async with LOCK:
        channel = CLIENT_CHANNEL.pop(ws, None)
        if channel:
            CHANNELS[channel].discard(ws)
            if not CHANNELS[channel]:
                CHANNELS.pop(channel, None)


@app.websocket("/ws")
async def relay(ws: WebSocket):
    token = ws.query_params.get("token", "")
    channel = ws.query_params.get("channel", "")
    if not secrets.compare_digest(token, CFG["access_token"]):
        await ws.close(code=4401, reason="Unauthorized")
        return
    if not CHANNEL_RE.fullmatch(channel):
        await ws.close(code=4400, reason="Invalid channel")
        return
    allowed = CFG.get("allowed_channels") or []
    if allowed and channel not in allowed:
        await ws.close(code=4403, reason="Channel not allowed")
        return

    await ws.accept()
    async with LOCK:
        members = CHANNELS[channel]
        if len(members) >= int(CFG["max_clients_per_channel"]):
            await ws.close(code=4429, reason="Channel full")
            return
        members.add(ws)
        CLIENT_CHANNEL[ws] = channel
        member_count = len(members)
    await ws.send_json({"type": "welcome", "service": "sanket-relay", "channel": channel, "members": member_count})
    log.info("Client joined channel=%s members=%s", channel, member_count)

    try:
        while True:
            message = await ws.receive()
            if message.get("type") == "websocket.disconnect":
                break
            payload = message.get("bytes")
            if payload is not None:
                if len(payload) > int(CFG["max_message_bytes"]):
                    await ws.close(code=4409, reason="Audio frame too large")
                    break
                async with LOCK:
                    peers = tuple(CHANNELS.get(channel, set()) - {ws})
                # Best-effort fan-out: one slow/disconnected peer cannot block others.
                async def forward(peer: WebSocket):
                    try:
                        await asyncio.wait_for(peer.send_bytes(payload), timeout=0.5)
                    except Exception:
                        await remove_client(peer)
                if peers:
                    await asyncio.gather(*(forward(peer) for peer in peers), return_exceptions=True)
            elif message.get("text"):
                try:
                    control = json.loads(message["text"])
                except json.JSONDecodeError:
                    await ws.send_json({"type": "error", "error": "invalid_json"})
                    continue
                if control.get("type") == "ping":
                    await ws.send_json({"type": "pong"})
                elif control.get("type") == "status":
                    async with LOCK:
                        count = len(CHANNELS.get(channel, set()))
                    await ws.send_json({"type": "status", "channel": channel, "members": count})
                else:
                    await ws.send_json({"type": "error", "error": "unsupported_control"})
    except WebSocketDisconnect:
        pass
    except Exception:
        log.exception("Relay client error on channel=%s", channel)
    finally:
        await remove_client(ws)
        log.info("Client left channel=%s", channel)
