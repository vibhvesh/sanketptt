#!/data/data/com.termux/files/usr/bin/bash
# SuperPTT control room installer: Android phone in Termux (aarch64), e.g. Vivo X300 as a backup control room.
#   curl -fsSL https://vibhvesh.github.io/sanketptt/superptt/android/install-termux.sh | bash
# Does not touch Android itself (no root, nothing outside Termux's own folders). Re-run to update; config/data/PIN kept.
# Env options:
#   SUPERPTT_STT=auto|faster-whisper|whispercpp|cloud   local speech engine (auto: try faster-whisper, then whisper.cpp, then cloud-only)
#   SUPERPTT_MODELS="tiny base small"                   multilingual Whisper models to fetch (never *.en)
#   SUPERPTT_TUNNEL=quick|none   SUPERPTT_DIR=~/superptt   SUPERPTT_BASE=<code url>   DRY_RUN=1 (print only)
set -euo pipefail
BASE=${SUPERPTT_BASE:-https://vibhvesh.github.io/sanketptt/superptt/pi}     # same Python package as the Pi
DIR=${SUPERPTT_DIR:-$HOME/superptt}
TUN=${SUPERPTT_TUNNEL:-quick}
STT=${SUPERPTT_STT:-auto}
MODELS=${SUPERPTT_MODELS:-tiny base small}
PREFIX=${PREFIX:-/data/data/com.termux/files/usr}
ENVF=$HOME/.superptt.env
FILES="requirements.txt worker.py superptt/__init__.py superptt/__main__.py superptt/app.py superptt/config.py
superptt/ingest.py superptt/store.py superptt/stt.py superptt/cloud.py superptt/mixer.py superptt/retention.py
superptt/web.py superptt/console.html superptt/e2e.py"
run() { if [ -n "${DRY_RUN:-}" ]; then echo "+ $*"; else eval "$*"; fi; }
ok()  { [ -z "${DRY_RUN:-}" ] && eval "$*" >/dev/null 2>&1; }
log() { echo "== $*"; }
if [ -z "${DRY_RUN:-}" ] && [ ! -d /data/data/com.termux ] && [ -z "${TERMUX_VERSION:-}" ]; then
  echo "This installer is for Termux on Android (use superptt/pi/install.sh on a Pi)."; exit 1; fi
case "$(uname -m)" in aarch64|arm64) ;; *) echo "warning: $(uname -m) is untested (built for aarch64)";; esac
log "SuperPTT control room (Termux) -> $DIR  stt: $STT  tunnel: $TUN"

# 1. Termux packages (Termux repos ship cloudflared, ffmpeg, CTranslate2 + onnxruntime Python builds)
run "pkg update -y"
run "pkg install -y python python-pip python-numpy python-cryptography ffmpeg cloudflared termux-api curl ca-certificates"
if [ "$STT" = auto ] || [ "$STT" = faster-whisper ]; then
  run "pkg install -y python-ctranslate2 python-onnxruntime rust clang make cmake binutils pkg-config libopenblas" || true
fi

# 2. code (from this checkout when run locally, else from GitHub Pages)
SRC=""; HERE=""; [ -f "${BASH_SOURCE[0]:-}" ] && HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
[ -n "$HERE" ] && [ -f "$HERE/../superptt/app.py" ] && SRC=$(cd "$HERE/.." && pwd)
run "mkdir -p '$DIR/superptt' '$DIR/data' '$DIR/logs' '$DIR/bin' '$HOME/.superptt/models'"
for f in $FILES; do
  if [ -n "$SRC" ]; then run "cp '$SRC/$f' '$DIR/$f'"; else run "curl -fsSL '$BASE/$f' -o '$DIR/$f'"; fi
done

# 3. venv; --system-site-packages so the Termux-built numpy/cryptography/ctranslate2/onnxruntime are used (no source builds)
run "python -m venv --system-site-packages '$DIR/venv'"
PIP="'$DIR/venv/bin/pip' install -q"
run "$PIP -U pip"
run "$PIP 'paho-mqtt>=2.0' 'qrcode>=7'"         # sounddevice is skipped: Android has no ALSA/PortAudio for Termux
PY="$DIR/venv/bin/python"
ok "'$PY' -c 'import numpy, cryptography'" || run "$PIP numpy 'cryptography>=41'"   # only if the pkg builds are missing
ENGINE=cloud
if [ "$STT" = auto ] || [ "$STT" = faster-whisper ]; then
  log "trying faster-whisper (Termux python-ctranslate2; tokenizers/av may compile, can take 10-30 min)"
  if ok "'$PY' -c 'import ctranslate2'" && ok "$PIP tokenizers 'huggingface-hub>=0.21' tqdm av" \
     && ok "$PIP --no-deps 'faster-whisper>=1.0'" \
     && ok "'$PY' -c 'import numpy as n;from faster_whisper import WhisperModel as W;list(W(\"tiny\",device=\"cpu\",compute_type=\"int8\").transcribe(n.zeros(16000,n.float32))[0])'"; then
    ENGINE=faster-whisper
  elif [ -n "${DRY_RUN:-}" ]; then echo "+ (dry run) faster-whisper probe skipped"
  else log "faster-whisper not usable on this device"; fi
fi
if [ "$ENGINE" = cloud ] && { [ "$STT" = auto ] || [ "$STT" = whispercpp ]; }; then
  log "building whisper.cpp from source (Termux has no whisper-cpp package)"
  run "pkg install -y git clang cmake make" || true
  if run "rm -rf '$DIR/src/whisper.cpp' && git clone -q --depth 1 https://github.com/ggml-org/whisper.cpp '$DIR/src/whisper.cpp'" \
     && run "cmake -S '$DIR/src/whisper.cpp' -B '$DIR/src/whisper.cpp/build' -DCMAKE_BUILD_TYPE=Release -DWHISPER_BUILD_TESTS=OFF -DBUILD_SHARED_LIBS=OFF >/dev/null" \
     && run "cmake --build '$DIR/src/whisper.cpp/build' -j\$(nproc) --target whisper-cli >/dev/null" \
     && run "cp '$DIR/src/whisper.cpp/build/bin/whisper-cli' '$DIR/bin/whisper-cli'"; then
    for m in $MODELS; do case "$m" in *.en) continue;; esac
      [ -s "$HOME/.superptt/models/ggml-$m.bin" ] || run "curl -fsSL --retry 3 -o '$HOME/.superptt/models/ggml-$m.bin' https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-$m.bin"
    done
    ENGINE=whispercpp
  else log "whisper.cpp build failed"; fi
fi
[ "$STT" = cloud ] && ENGINE=cloud
log "speech engine: $ENGINE"

# 4. config (same keys/layout as the Pi: $DIR/config.json, $DIR/data); never overwrites an existing one
HAS_SMALL=""; case " $MODELS " in *" small "*) HAS_SMALL=small;; esac
if [ ! -f "$DIR/config.json" ]; then
  run "printf '%s\n' '{\"data_dir\": \"$DIR/data\", \"whisper_model\": \"base\", \"quality_model\": \"$HAS_SMALL\", \"stt_workers\": 2, \"whisper_threads\": 4, \"stt_engine\": \"$ENGINE\", \"whispercpp_bin\": \"$DIR/bin/whisper-cli\", \"whispercpp_models\": \"$HOME/.superptt/models\", \"output\": {\"mode\": \"off\"}}' > '$DIR/config.json'"
else
  run "'$PY' -c \"import json;p='$DIR/config.json';c=json.load(open(p));c['stt_engine']='$ENGINE';c['whispercpp_bin']='$DIR/bin/whisper-cli';c['whispercpp_models']='$HOME/.superptt/models';json.dump(c,open(p,'w'),indent=2)\""
fi
run "chmod 600 '$DIR/config.json'"
if [ "$ENGINE" = faster-whisper ]; then
  log "downloading Whisper models ($MODELS), one time"
  for m in $MODELS; do case "$m" in *.en) continue;; esac
    run "'$PY' -c \"from faster_whisper import WhisperModel; WhisperModel('$m', compute_type='int8')\""; done
fi

# 5. secrets file (never in git, never printed): cloud STT key
if [ ! -f "$ENVF" ]; then
  run "printf '%s\n' '# SuperPTT secrets. Uncomment and set, then: superptt-stop; superptt-start' '# ELEVENLABS_API_KEY=' '# OPENAI_API_KEY=' '# GOOGLE_API_KEY=' > '$ENVF'"
fi
run "chmod 600 '$ENVF'"

# 6. start/stop scripts + Termux:Boot (replaces systemd). Written from templates; @VARS@ filled in here.
put() {  # put <dest> : template on stdin
  local t; t=$(sed -e "s|@DIR@|$DIR|g" -e "s|@PREFIX@|$PREFIX|g" -e "s|@ENVF@|$ENVF|g" -e "s|@TUN@|$TUN|g")
  if [ -n "${DRY_RUN:-}" ]; then echo "+ write $1"; printf '%s\n' "$t" | sed 's/^/    | /'; else printf '%s\n' "$t" > "$1"; chmod 700 "$1"; fi; }
put "$PREFIX/bin/superptt-start" <<'EOF'
#!@PREFIX@/bin/bash
# start SuperPTT control room + Cloudflare quick tunnel in the background
D='@DIR@'; TUN='@TUN@'; mkdir -p "$D/logs"; cd "$D" || exit 1
command -v termux-wake-lock >/dev/null && termux-wake-lock
set -a   # cloud key from the secrets file; never printed
# shellcheck disable=SC1091
[ -f '@ENVF@' ] && . '@ENVF@'
set +a
alive() { [ -f "$1" ] && kill -0 "$(cat "$1")" 2>/dev/null; }
if ! alive "$D/logs/superptt.pid"; then
  PATH="$D/bin:$PATH" nohup "$D/venv/bin/python" -m superptt -c "$D/config.json" >>"$D/logs/superptt.log" 2>&1 &
  echo $! > "$D/logs/superptt.pid"
fi
if [ "$TUN" != none ] && ! alive "$D/logs/tunnel.pid"; then
  nohup cloudflared tunnel --no-autoupdate --metrics 127.0.0.1:20241 --url http://127.0.0.1:8090 >>"$D/logs/tunnel.log" 2>&1 &
  echo $! > "$D/logs/tunnel.pid"
fi
echo "SuperPTT running. On this phone: http://127.0.0.1:8090"
[ "$TUN" = none ] && exit 0
for _ in $(seq 1 30); do
  U=$(superptt-url 2>/dev/null); [ -n "$U" ] && { echo "Public console: $U"; exit 0; }; sleep 2
done
echo "Tunnel URL not ready yet; run superptt-url (log: $D/logs/tunnel.log)"
EOF
put "$PREFIX/bin/superptt-stop" <<'EOF'
#!@PREFIX@/bin/bash
D='@DIR@'
for p in superptt tunnel; do f="$D/logs/$p.pid"; [ -f "$f" ] && kill "$(cat "$f")" 2>/dev/null; rm -f "$f"; done
command -v termux-wake-unlock >/dev/null && termux-wake-unlock
echo "SuperPTT stopped."
EOF
put "$PREFIX/bin/superptt-url" <<'EOF'
#!@PREFIX@/bin/bash
h=$(curl -fs http://127.0.0.1:20241/quicktunnel | sed -n 's/.*"hostname":"\([^"]*\)".*/\1/p'); [ -n "$h" ] && echo "https://$h"
EOF
run "mkdir -p '$HOME/.termux/boot'"
put "$HOME/.termux/boot/superptt" <<'EOF'
#!@PREFIX@/bin/sh
# Termux:Boot: start SuperPTT after the phone boots
termux-wake-lock
sleep 20
exec @PREFIX@/bin/superptt-start >> @DIR@/logs/boot.log 2>&1
EOF

# 7. start now
[ -z "${DRY_RUN:-}" ] && { superptt-stop >/dev/null 2>&1 || true; }
run "'$PREFIX/bin/superptt-start'"
cat <<MSG

== SuperPTT control room installed on this phone (speech engine: $ENGINE).
 1. Open http://127.0.0.1:8090 in the phone browser. First open: set the admin PIN (6+ digits); save the tokens shown.
    Recordings play in the browser (or: termux-media-player play $DIR/data/rec/<file>.wav).
 2. Cloud STT key: nano ~/.superptt.env  (ELEVENLABS_API_KEY=...), then superptt-stop; superptt-start
 3. Outside access: URL printed above, also in the console header, or run: superptt-url
 4. Commands: superptt-start  superptt-stop  superptt-url   Logs: $DIR/logs/
 5. Auto-start: install the Termux:Boot app (F-Droid/GitHub, same source as Termux) and open it once.
 KEEP IT ALIVE (Android kills background apps):
  - Settings > Apps > Termux > Battery: set "Background power consumption" to Allow / "Unrestricted",
    turn off battery optimisation for Termux and Termux:Boot (Settings > Battery > More settings > Optimise battery use).
  - Vivo: Settings > Apps > Autostart (or i Manager > App manager > Autostart): allow Termux + Termux:Boot.
  - Pin/lock Termux in recent apps; keep the Termux notification (wake lock held).
MSG
