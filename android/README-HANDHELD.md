# Sanket PTT Android radio handheld

This is the native Android WebView shell for the existing Sanket PTT radio. It reuses the
production web radio and MQTT-over-WSS protocol; it does not create a second audio stack.

## Build

Requirements: JDK 17, Android SDK platform 34 and build-tools 34.0.0.

```bash
export ANDROID_HOME="$HOME/Android/Sdk"  # adjust for your machine
chmod +x android/build.sh
android/build.sh in.sanket.ptt "Sanket PTT" \
  "https://vibhvesh.github.io/sanketptt/?embed=1" \
  "#174A78" Sanket_PTT_Radio.apk
```

The build script reads `$ANDROID_HOME` (or `/opt/android`). For a first build, create a private
keystore and supply its password through the environment (never commit the keystore):

```bash
keytool -genkeypair -keystore "$HOME/.android/sanket-release.jks" \
  -storepass 'CHOOSE_A_LONG_PASSWORD' -keypass 'CHOOSE_A_LONG_PASSWORD' \
  -alias sanket -keyalg RSA -keysize 2048 -validity 10000 -dname "CN=Sanket PTT"
export KEYSTORE="$HOME/.android/sanket-release.jks"
export KEYSTORE_PASS='CHOOSE_A_LONG_PASSWORD'
export KEY_ALIAS=sanket
export KEY_PASS="$KEYSTORE_PASS"
android/build.sh in.sanket.ptt "Sanket PTT" \
  "https://vibhvesh.github.io/sanketptt/?embed=1" \
  "#174A78" Sanket_PTT_Radio.apk
```

Keep the keystore and passwords out of Git. A different signing key cannot update an
already-installed APK signed with another key.

## Install on Tecno Spark Go 1

1. Copy the APK to the phone and open it from Files.
2. Allow the file manager to install unknown apps when Android prompts.
3. Install and open Sanket PTT; grant Microphone and optional Location permissions.
4. Pair the Bluetooth headset in Android Settings before switching audio output.
5. Tap the top-right **SPEAKER** control to switch to **BLUETOOTH**. If no supported headset
   is connected, the app reports that a headset must be paired and keeps the current route.
6. Enter your call sign, join the required channel and press-and-hold PTT. Release to stop.

## Notes

- Immersive full-screen radio UI; screen stays awake while the app is open.
- Android 12+ uses communication-device routing; older versions use the legacy speaker route.
- Existing web code continues to own MQTT broker fallback, floor control, presence and 12 kHz PCM.
- Set Android battery usage to Unrestricted on Tecno if the vendor battery manager interrupts
  the radio during long background sessions.
- Microphone foreground services must be started while the app is visible and after permission
  is granted on modern Android. This build intentionally does not start microphone capture
  from a boot receiver.
- A SIM data plan or Wi-Fi is required; this is not a cellular voice-call app.
