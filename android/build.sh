#!/usr/bin/env bash
# usage: KEYSTORE=/secure/release.jks KEYSTORE_PASS=... KEY_ALIAS=sanket KEY_PASS=... android/build.sh <package> "<App Name>" <url> <#color> <out.apk>
set -euo pipefail
if [ "$#" -ne 5 ]; then echo "Usage: $0 <package> <app-name> <url> <color> <output.apk>" >&2; exit 2; fi
SDK="${ANDROID_HOME:-/opt/android}"
BT="$SDK/build-tools/34.0.0"
JAR="$SDK/platforms/android-34/android.jar"
for f in "$BT/aapt2" "$BT/d8" "$BT/zipalign" "$BT/apksigner" "$JAR"; do
  [ -e "$f" ] || { echo "Missing Android SDK component: $f" >&2; exit 1; }
done
command -v javac >/dev/null || { echo "JDK 17 (javac) is required" >&2; exit 1; }
D=$(dirname "$(readlink -f "$0")")
T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT
P="$1"
mkdir -p "$T/res/drawable" "$T/java/${P//.//}" "$T/obj" "$T/dex"
sed "s/PKG/$P/;s|APPNAME|$2|" "$D/src/AndroidManifest.xml" > "$T/AndroidManifest.xml"
sed "s/COLOR/$4/" "$D/src/ic.xml" > "$T/res/drawable/ic.xml"
sed "s/PKG/$P/;s|APPURL|$3|" "$D/src/MainActivity.java" > "$T/java/${P//.//}/MainActivity.java"
sed "s/PKG/$P/" "$D/src/KeepAliveService.java" > "$T/java/${P//.//}/KeepAliveService.java"
"$BT/aapt2" compile --dir "$T/res" -o "$T/res.zip"
"$BT/aapt2" link -I "$JAR" --manifest "$T/AndroidManifest.xml" -o "$T/u.apk" "$T/res.zip"
javac -source 8 -target 8 -nowarn -cp "$JAR" -d "$T/obj" $(find "$T/java" -name '*.java')
"$BT/d8" --release --min-api 24 --lib "$JAR" --output "$T/dex" $(find "$T/obj" -name '*.class')
(cd "$T/dex" && jar uf "$T/u.apk" classes.dex)
"$BT/zipalign" -f 4 "$T/u.apk" "$T/aligned.apk"
KS="${KEYSTORE:-$D/sanket.keystore}"
ALIAS="${KEY_ALIAS:-sanket}"
STORE_PASS="${KEYSTORE_PASS:-}"
KEY_PASS_VALUE="${KEY_PASS:-$STORE_PASS}"
if [ ! -f "$KS" ]; then
  [ -n "$STORE_PASS" ] || { echo "Set KEYSTORE_PASS before creating a signing keystore." >&2; exit 1; }
  keytool -genkeypair -keystore "$KS" -storepass "$STORE_PASS" -keypass "$KEY_PASS_VALUE" -alias "$ALIAS" -keyalg RSA -keysize 2048 -validity 10000 -dname "CN=Sanket PTT"
fi
[ -n "$STORE_PASS" ] || { echo "Set KEYSTORE_PASS for APK signing." >&2; exit 1; }
export KEYSTORE_PASS="$STORE_PASS" KEY_PASS="$KEY_PASS_VALUE"
"$BT/apksigner" sign --ks "$KS" --ks-key-alias "$ALIAS" --ks-pass env:KEYSTORE_PASS --key-pass env:KEY_PASS --out "$5" "$T/aligned.apk"
"$BT/apksigner" verify --verbose "$5"
echo "Built and verified: $5"
