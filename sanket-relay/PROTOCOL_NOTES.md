# Relay protocol and integration boundary

This first isolated install is a generic authenticated WebSocket audio-frame fan-out service. It is intentionally not wired into the existing Sanket PTT service yet.

Before production integration, inspect and map the actual Sanket client/MQTT protocol:
- message envelope and audio codec/sample rate/frame duration
- PTT floor/talk-burst ownership and release events
- channel membership and user/device identity
- reconnect, sequence numbers and packet-loss behavior
- encryption and authorization model

Then implement a compatibility adapter and tests. Do not point existing clients at this pilot until the adapter is verified. The current relay copies binary frames to other connected clients in the same channel; it does not decode, transcode, record or mix audio.
