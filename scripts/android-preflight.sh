#!/bin/sh
set -eu
for tool in java adb; do command -v "$tool" >/dev/null || { echo "Missing prerequisite: $tool. Install from official sources after reviewing required licenses."; exit 1; }; done
: "${ANDROID_HOME:?Set ANDROID_HOME to an installed, licensed Android SDK}"
test -f "$ANDROID_HOME/platforms/android-35/android.jar" || { echo 'Missing Android SDK Platform 35'; exit 1; }
echo 'Toolchain prerequisites found. Build and actual-device verification are still required.'
