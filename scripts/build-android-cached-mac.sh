#!/bin/sh
# Explicit local-toolchain override. Offline; never installs SDKs or creates keys.
set -eu
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
APP_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
export JAVA_HOME="${SWAY_JAVA_HOME:-$HOME/.gradle/jdks/eclipse_adoptium-17-aarch64-os_x.2/jdk-17.0.20+8/Contents/Home}"
export ANDROID_HOME="${SWAY_ANDROID_HOME:-$HOME/Library/Android/sdk}"
export GRADLE_USER_HOME="$APP_DIR/.toolchain/gradle-home"
export GRADLE_RO_DEP_CACHE="${SWAY_RO_DEP_CACHE:-$HOME/.gradle/caches}"
export TOGETHERMOVE_DEBUG_KEYSTORE="${SWAY_DEBUG_KEYSTORE:-$HOME/.android/debug.keystore}"
SWAY_GRADLE="${SWAY_GRADLE_EXECUTABLE:-$HOME/.gradle/wrapper/dists/gradle-8.13-bin/5xuhj0ry160q40clulazy9h7d/gradle-8.13/bin/gradle}"
test -x "$JAVA_HOME/bin/java"
test -x "$SWAY_GRADLE"
test -f "$ANDROID_HOME/platforms/android-35/android.jar"
test -f "$TOGETHERMOVE_DEBUG_KEYSTORE"
python3 "$SCRIPT_DIR/prepare-native-video.py" --check
cd "$APP_DIR/android"
exec "$SWAY_GRADLE" --offline --no-daemon --max-workers=1 "-Dorg.gradle.jvmargs=-Xmx768m -Duser.home=$APP_DIR/.toolchain/home -Djava.util.prefs.userRoot=$APP_DIR/.toolchain/java-prefs" -Pandroid.builder.sdkDownload=false -I "$SCRIPT_DIR/android-cached-toolchain.init.gradle" :app:assembleDebug :app:assembleRelease --console=plain
