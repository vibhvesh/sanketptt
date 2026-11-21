/** WebRTC voice for the Sanket relay. Signaling matches relay.canberravision.com RoomPage. */

const ICE_SERVERS = [
  { urls: "stun:stun.l.google.com:19302" },
  { urls: "stun:stun1.l.google.com:19302" },
];

export class PeerAudio {
  constructor(sendSignal, onPcm) {
    this.sendSignal = sendSignal;
    this.onPcm = onPcm;
    this.localStream = null;
    this.outbound = new Map();
    this.inbound = new Map();
    this.earlyIce = new Map();
    this.generation = 0;
    this.taps = new Map();
  }

  async openMic() {
    this.closeMic();
    this.localStream = await navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
      video: false,
    });
  }

  closeMic() {
    if (this.localStream) this.localStream.getTracks().forEach((track) => track.stop());
    this.localStream = null;
  }

  async startTransmitting(peers) {
    await this.openMic();
    for (const peer of peers || []) {
      if (peer && peer.userId) await this.offerTo(peer.userId);
    }
  }

  async offerTo(userId) {
    if (!this.localStream || this.outbound.has(userId)) return;
    const generation = this.generation;
    const entry = { pc: null, ice: [], closed: false };
    const pc = new RTCPeerConnection({ iceServers: ICE_SERVERS });
    entry.pc = pc;
    this.outbound.set(userId, entry);
    this.localStream.getTracks().forEach((track) => pc.addTrack(track, this.localStream));
    pc.onicecandidate = (event) => {
      if (event.candidate && !entry.closed) this.sendSignal(userId, "ice", event.candidate);
    };
    const offer = await pc.createOffer();
    if (generation !== this.generation || entry.closed) {
      this.closeEntry(this.outbound, userId);
      return;
    }
    await pc.setLocalDescription(offer);
    this.sendSignal(userId, "offer", pc.localDescription);
  }

  async handle(fromUserId, kind, data) {
    if (kind === "offer") {
      this.closeInbound(fromUserId);
      const queued = this.earlyIce.get(fromUserId) || [];
      this.earlyIce.delete(fromUserId);
      const entry = { pc: null, ice: queued.slice(), closed: false };
      const pc = new RTCPeerConnection({ iceServers: ICE_SERVERS });
      entry.pc = pc;
      this.inbound.set(fromUserId, entry);
      pc.onicecandidate = (event) => {
        if (event.candidate && !entry.closed) this.sendSignal(fromUserId, "ice", event.candidate);
      };
      pc.ontrack = (event) => {
        if (entry.closed) return;
        const stream = event.streams && event.streams[0] && event.streams[0].getAudioTracks().length
          ? event.streams[0]
          : new MediaStream([event.track]);
        this.tap(fromUserId, stream);
      };
      await pc.setRemoteDescription(new RTCSessionDescription(data));
      if (entry.closed) return;
      await this.flush(pc, entry);
      const answer = await pc.createAnswer();
      if (entry.closed) return;
      await pc.setLocalDescription(answer);
      this.sendSignal(fromUserId, "answer", pc.localDescription);
      return;
    }
    if (kind === "answer") {
      const entry = this.outbound.get(fromUserId);
      if (!entry || !entry.pc) return;
      await entry.pc.setRemoteDescription(new RTCSessionDescription(data));
      await this.flush(entry.pc, entry);
      return;
    }
    if (kind === "ice") {
      const entry = this.outbound.get(fromUserId) || this.inbound.get(fromUserId);
      if (!entry || !entry.pc || !entry.pc.remoteDescription) {
        const list = entry ? entry.ice : (this.earlyIce.get(fromUserId) || []);
        list.push(data);
        if (!entry) this.earlyIce.set(fromUserId, list);
        return;
      }
      try {
        await entry.pc.addIceCandidate(new RTCIceCandidate(data));
      } catch (e) {
        /* A late candidate can be ignored. */
      }
    }
  }

  async flush(pc, entry) {
    while (entry.ice.length && !entry.closed) {
      const candidate = entry.ice.shift();
      try {
        await pc.addIceCandidate(new RTCIceCandidate(candidate));
      } catch (e) {
        /* ignore */
      }
    }
  }

  tap(userId, stream) {
    this.untap(userId);
    const Ctx = window.AudioContext || window.webkitAudioContext;
    if (!Ctx) return;
    const context = new Ctx();
    const source = context.createMediaStreamSource(stream);
    const proc = context.createScriptProcessor(4096, 1, 1);
    const mute = context.createGain();
    mute.gain.value = 0;
    source.connect(proc);
    proc.connect(mute);
    mute.connect(context.destination);
    const rate = 12000;
    proc.onaudioprocess = (event) => {
      const input = event.inputBuffer.getChannelData(0);
      const step = context.sampleRate / rate;
      const length = Math.floor(input.length / step);
      if (!length) return;
      const pcm = new Int16Array(length);
      for (let i = 0; i < length; i++) {
        const sample = input[Math.floor(i * step)] || 0;
        pcm[i] = Math.max(-1, Math.min(1, sample)) * 32767;
      }
      this.onPcm(userId, pcm);
    };
    context.resume().catch(() => {});
    this.taps.set(userId, () => {
      proc.disconnect();
      source.disconnect();
      context.close().catch(() => {});
    });
  }

  untap(userId) {
    const stop = this.taps.get(userId);
    if (stop) stop();
    this.taps.delete(userId);
  }

  closeEntry(map, userId) {
    const entry = map.get(userId);
    if (!entry) return;
    entry.closed = true;
    if (entry.pc) entry.pc.close();
    map.delete(userId);
    this.untap(userId);
  }

  closeInbound(userId) {
    if (userId) this.closeEntry(this.inbound, userId);
  }

  stopTransmitting() {
    this.generation += 1;
    for (const userId of [...this.outbound.keys()]) this.closeEntry(this.outbound, userId);
    this.closeMic();
  }

  stopAll() {
    this.stopTransmitting();
    this.earlyIce.clear();
    for (const userId of [...this.inbound.keys()]) this.closeEntry(this.inbound, userId);
  }
}
