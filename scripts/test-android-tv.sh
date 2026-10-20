#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
: "${ANDROID_HOME:?Set ANDROID_HOME to your installed Android SDK}"
mkdir -p artifacts
AVD_NAME="${AVD_NAME:-TogetherMoveTV}"
ADB="$ANDROID_HOME/platform-tools/adb"
"$ADB" start-server
"$ANDROID_HOME/emulator/emulator" -avd "$AVD_NAME" -no-window -no-audio -no-boot-anim -no-snapshot -accel "${EMULATOR_ACCEL:-auto}" -gpu swiftshader_indirect -cores 1 -no-metrics -show-kernel -memory 2048 > artifacts/android-tv-emulator.log 2>&1 &
EMU=$!
trap 'kill "$EMU" 2>/dev/null || true' EXIT
for i in $(seq 1 120); do
 if ! kill -0 "$EMU" 2>/dev/null; then echo 'Emulator exited before boot'; tail -20 artifacts/android-tv-emulator.log; exit 1; fi
 READY=$("$ADB" -s emulator-5554 shell getprop sys.boot_completed 2>/dev/null | tr -d '\r' || true)
 if [ "$READY" = 1 ]; then break; fi
 if [ $((i%6)) = 0 ]; then echo "Boot pending after $((i*5)) seconds"; fi
 sleep 5
done
if [ "$READY" != 1 ]; then echo 'Boot did not complete within 10 minutes'; "$ADB" devices; "$ADB" -s emulator-5554 logcat -d -t 300 > artifacts/android-tv-boot-logcat.txt 2>&1 || true; exit 2; fi
echo 'Android TV API 30 boot completed'
"$ADB" -s emulator-5554 shell getprop ro.build.fingerprint
"$ADB" -s emulator-5554 install -r android/app/build/outputs/apk/debug/app-debug.apk
"$ADB" -s emulator-5554 shell am start -n com.togethermove.tv/.MainActivity
sleep 15
"$ADB" -s emulator-5554 exec-out screencap -p > artifacts/android-tv-home.png
"$ADB" -s emulator-5554 shell input keyevent 23
sleep 3
"$ADB" -s emulator-5554 exec-out screencap -p > artifacts/android-tv-setup.png
"$ADB" -s emulator-5554 shell input keyevent 23
sleep 5
"$ADB" -s emulator-5554 shell input keyevent 85
sleep 2
"$ADB" -s emulator-5554 exec-out screencap -p > artifacts/android-tv-paused.png
"$ADB" -s emulator-5554 logcat -d -t 1200 > artifacts/android-tv-logcat.txt
"$ADB" -s emulator-5554 shell dumpsys activity activities | grep -E 'mResumedActivity|topResumedActivity' || true
echo 'Native launch, D-pad center and play/pause inputs exercised; screenshots require visual review.'
