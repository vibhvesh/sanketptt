#!/usr/bin/env bash
set -euo pipefail
SDK="${ANDROID_HOME:-${ANDROID_SDK_ROOT:-$HOME/Android/Sdk}}";BT="$SDK/build-tools/34.0.0";JAR="$SDK/platforms/android-34/android.jar";D="$(cd "$(dirname "$0")" && pwd)";OUT="${1:-$D/Prisha_Shopper.apk}"
: "${KEYSTORE:?Set KEYSTORE}";: "${KEYSTORE_PASS:?Set KEYSTORE_PASS}";: "${KEY_ALIAS:?Set KEY_ALIAS}"
mkdir -p "$(dirname "$OUT")";T="$(mktemp -d)";trap 'rm -rf "$T"' EXIT
mkdir -p "$T/res/drawable" "$T/java/com/canberravision/prishashopper" "$T/obj" "$T/dex"
cp "$D/res/drawable/ic.xml" "$T/res/drawable/ic.xml";cp "$D/src/AndroidManifest.xml" "$T/AndroidManifest.xml";cp "$D/src/MainActivity.java" "$T/java/com/canberravision/prishashopper/MainActivity.java"
"$BT/aapt2" compile --dir "$T/res" -o "$T/resources.zip"
"$BT/aapt2" link -I "$JAR" --manifest "$T/AndroidManifest.xml" -o "$T/unsigned.apk" "$T/resources.zip"
javac -source 8 -target 8 -classpath "$JAR" -d "$T/obj" "$T/java/com/canberravision/prishashopper/MainActivity.java"
"$BT/d8" --release --min-api 29 --lib "$JAR" --output "$T/dex" $(find "$T/obj" -name '*.class')
(cd "$T/dex" && jar uf "$T/unsigned.apk" classes.dex)
"$BT/zipalign" -f 4 "$T/unsigned.apk" "$T/aligned.apk"
"$BT/apksigner" sign --ks "$KEYSTORE" --ks-pass "env:KEYSTORE_PASS" --ks-key-alias "$KEY_ALIAS" --key-pass "env:KEYSTORE_PASS" --out "$OUT" "$T/aligned.apk"
"$BT/apksigner" verify --verbose "$OUT";echo "APK ready: $OUT"