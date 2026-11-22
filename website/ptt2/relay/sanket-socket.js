/**
 * Sanket PTT relay. Same calls the MQTT radio exposes: join, claim, release, sendAudio.
 * The wire protocol is the socket.io room used by relay.canberravision.com.
 */
import { PeerAudio } from "./peer-audio.js";
import {
  RELAY_SANKET,
  SANKET_RELAY_ORIGIN,
  SANKET_CHANNEL_PASSWORD,
} from "./config.js";
import { getCredentials, getToken } from "./auth.js";

const SOCKET_MODULE = SANKET_RELAY_ORIGIN + "/vendor/socket.mjs";

async function api(path, { method = "GET", token, body } = {}) {
  let response;
  try {
    response = await fetch(SANKET_RELAY_ORIGIN + path, {
      method,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: "Bearer " + token } : {}),
      },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch (e) {
    const message = e && e.message ? e.message : String(e);
    const error = new Error(message);
    error.blocked = /failed to fetch|cors|access-control/i.test(message);
    throw error;
  }
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message = response.status === 401
      ? "Sign-in failed. Check the email and password."
      : (data && data.error && data.error.message ? data.error.message : "Request failed (" + response.status + ").");
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }
  return data;
}

export function openSanketRelay(options) {
  return new SanketRelay(options || {});
}

/** Public rooms that can be joined without a channel password. */
export async function listFreeRooms() {
  const token = getToken();
  if (!token) {
    const error = new Error("Sign in required.");
    error.status = 401;
    throw error;
  }
  const listed = await api("/api/rooms", { token });
  return (listed.rooms || []).filter((room) => room.roomId && room.accessType === "public" && !room.hasPassword && room.roomStatus !== "disabled");
}

/** Channels assigned to the signed-in account. */
export async function assignedRooms() {
  const token = getToken();
  if (!token) {
    const error = new Error("Sign in required.");
    error.status = 401;
    throw error;
  }
  const listed = await api("/api/rooms", { token });
  return (listed.rooms || []).filter((room) => room.memberRole && room.roomId);
}

class SanketRelay {
  constructor(options) {
    this.cb = options.on || function () {};
    this.ch = String(options.roomId || "RM-LOBY").toUpperCase();
    this.relayId = RELAY_SANKET;
    this.id = "";
    this.name = "";
    this.users = {};
    this.floor = null;
    this.talking = false;
    this.browser = true;
    this.token = "";
    this.floorToken = "";
    this.socket = null;
    this.closed = false;
    this.rooms = [];
    this.relayHost = "relay.canberravision.com";
    this.speakerEmail = "";
    this.username = "";
    this.roomName = "";
    this.audio = new PeerAudio((to, kind, data) => this.signal(to, kind, data), (userId, pcm) => this.hear(userId, pcm));
    this.fail = (reason) => this.cb("net", reason ? "unreachable:" + reason : "unreachable");
    this.start();
  }

  async start() {
    const creds = getCredentials();
    try {
      this.token = getToken();
      if (!this.token) throw Object.assign(new Error("Sign in required."), { status: 401 });
      if (this.closed) return;
      this.speakerEmail = creds ? creds.email : "";
      const me = await api("/api/auth/me", { token: this.token });
      this.username = me.user && me.user.username || "";
      this.id = me.user && me.user.userId || "";
      const listed = await api("/api/rooms", { token: this.token });
      this.rooms = (listed.rooms || []).filter((room) => room.memberRole);
      if (!this.rooms.some((room) => room.roomId === this.ch) && this.rooms[0]) this.ch = this.rooms[0].roomId;
      if (window.ptt2SetRelayRooms) window.ptt2SetRelayRooms(this.rooms, this.ch);
      await this.enterRoom(this.ch);
      await this.connectSocket();
    } catch (e) {
      if (!this.closed) this.fail(e && e.message ? e.message : "login failed");
    }
  }

  async enterRoom(roomId) {
    const data = await api("/api/rooms/" + encodeURIComponent(roomId), { token: this.token });
    const room = data.room || {};
    this.roomName = room.roomName || room.name || roomId;
    if (room.roomStatus && room.roomStatus !== "active") throw new Error("This channel has been disabled.");
    if (!room.memberRole) {
      await api("/api/rooms/" + encodeURIComponent(roomId) + "/join", {
        method: "POST",
        token: this.token,
        body: room.hasPassword ? { password: SANKET_CHANNEL_PASSWORD } : {},
      });
    }
  }

  async connectSocket() {
    const mod = await import(SOCKET_MODULE);
    if (this.closed) return;
    const socket = mod.io(SANKET_RELAY_ORIGIN, {
      auth: { token: this.token },
      reconnection: true,
      transports: ["websocket", "polling"],
    });
    this.socket = socket;
    socket.on("connect", () => this.joinRoom());
    socket.on("connect_error", (error) => this.fail(error && error.message ? error.message : "socket"));
    socket.on("disconnect", () => {
      if (!this.closed) this.cb("net", "disconnected");
    });
    socket.on("room:participants", (payload) => this.applyPeople(payload));
    socket.on("speaker:changed", (payload) => this.applySpeaker(payload && payload.speaker));
    socket.on("ptt:add-listener", ({ userId }) => {
      if (this.talking && userId) this.audio.offerTo(userId).catch(() => {});
    });
    socket.on("webrtc:signal", ({ fromUserId, kind, data }) => {
      this.audio.handle(fromUserId, kind, data).catch(() => {});
    });
    socket.on("webrtc:stop", ({ fromUserId }) => this.audio.closeInbound(fromUserId));
    socket.on("ptt:revoked", () => this.stopTalking());
  }

  async joinRoom() {
    if (!this.socket || this.closed) return;
    try {
      const ack = await this.socket.timeout(5000).emitWithAck("room:join", { roomId: this.ch });
      if (!ack || !ack.ok) {
        this.fail(ack && ack.message ? ack.message : "Could not enter this channel.");
        return;
      }
      this.applyPeople(ack);
      this.applySpeaker(ack.speaker);
      this.cb("net", SANKET_RELAY_ORIGIN);
      if (window.ptt2RelayAuthenticated) window.ptt2RelayAuthenticated(this.username || this.speakerEmail || "Operator");
    } catch (e) {
      this.fail(e && e.message ? e.message : "room:join");
    }
  }

  applyPeople(payload) {
    const now = Date.now();
    this.users = {};
    (payload && payload.participants || []).forEach((person) => {
      if (!person || !person.userId) return;
      this.users[person.userId] = { id: person.userId, name: person.username || person.userId, seen: now, loc: null };
    });
    if (this.id && !this.users[this.id]) this.users[this.id] = { id: this.id, name: this.name || "operator", seen: now, loc: null };
    this.emit();
  }

  applySpeaker(speaker) {
    if (!speaker) {
      if (this.floor && this.floor.id !== this.id) this.floor = null;
      if (!this.talking) this.floor = null;
      this.emit();
      return;
    }
    if (speaker.userId === this.id) return;
    this.floor = { id: speaker.userId, name: speaker.username || "speaker", ts: speaker.startedAt || Date.now(), seen: Date.now(), got: Date.now() };
    this.talking = false;
    this.emit();
  }

  hear(userId, pcm) {
    if (!userId || userId === this.id) return;
    if (!this.floor || this.floor.id !== userId) {
      const person = this.users[userId];
      this.floor = { id: userId, name: person ? person.name : "speaker", ts: Date.now(), seen: Date.now(), got: Date.now() };
      this.emit();
    }
    this.floor.seen = Date.now();
    this.cb("audio", pcm);
  }

  signal(to, kind, data) {
    if (this.socket && this.socket.connected) this.socket.emit("webrtc:signal", { roomId: this.ch, to, kind, data });
  }

  join(name) {
    this.name = String(name || "").slice(0, 40);
    if (this.id) {
      this.users[this.id] = this.users[this.id] || { id: this.id, name: this.name, seen: Date.now(), loc: null };
      this.users[this.id].name = this.name || this.users[this.id].name;
    }
    this.emit();
  }

  list() {
    return Object.keys(this.users).map((id) => this.users[id]).sort((a, b) => a.name < b.name ? -1 : 1);
  }

  emit() {
    this.cb("state", { users: this.list(), floor: this.floor, me: this.id });
  }

  claim(done) {
    if (!this.socket || !this.socket.connected) {
      done(false);
      return;
    }
    this.socket.timeout(5000).emitWithAck("ptt:request", { roomId: this.ch }).then(async (result) => {
      if (!result || !result.ok) {
        done(false);
        return;
      }
      this.floorToken = result.token || "";
      this.talking = true;
      this.floor = { id: this.id, name: this.name || "operator", ts: Date.now(), seen: Date.now(), got: Date.now() };
      this.emit();
      try {
        await this.audio.startTransmitting(result.peers || []);
        done(true);
      } catch (e) {
        this.talking = false;
        done(false);
      }
    }).catch(() => done(false));
  }

  sendAudio() {
    return !!(this.talking && this.floor && this.floor.id === this.id);
  }

  stopTalking() {
    this.talking = false;
    this.audio.stopTransmitting();
    if (this.floor && this.floor.id === this.id) this.floor = null;
    this.emit();
  }

  release() {
    const token = this.floorToken;
    this.floorToken = "";
    this.stopTalking();
    if (this.socket && this.socket.connected && token) {
      this.socket.emit("ptt:release", { roomId: this.ch, token });
    }
  }

  setLoc() {}

  leave() {
    this.closed = true;
    this.release();
    this.audio.stopAll();
    if (this.socket) {
      const socket = this.socket;
      this.socket = null;
      socket.emit("room:leave", { roomId: this.ch });
      socket.disconnect();
    }
  }
}
