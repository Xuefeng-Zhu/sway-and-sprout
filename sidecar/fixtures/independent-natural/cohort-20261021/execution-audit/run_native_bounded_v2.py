"""One existing camera-disabled emulator; run only under browser-only.sb.

The SDK-free network preflight happens before any Android tool is started.
No software download, new AVD, external upload, or model substitution.
"""
import errno
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import time

E = Path(__file__).resolve().parent
R = Path('/Users/frank/mygit/sway-and-sprout')
OLD = Path('/Users/frank/Documents/Codex/2026-10-15/task')
PROFILE = E.parents[1] / 'mediapipe-evaluation/browser/browser-only.sb'
ADB = Path('/Users/frank/Library/Android/sdk/platform-tools/adb')
EMULATOR = OLD / 'android-test-sdk/emulator/emulator'
APK = R / 'android/app/build/outputs/apk/debug/app-debug.apk'
OUT = E / 'movenet-results'
CONTROL = E / 'native-control-v2'

def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')

def stamp(stage):
    print(json.dumps({'stage': stage, 'utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}), flush=True)

def main():
    # A fresh output is mandatory: preserve any partial earlier experiment.
    CONTROL.mkdir(exist_ok=False)
    if OUT.exists():
        raise RuntimeError('Native result directory already exists; refusing overwrite')
    guard = {'profile': str(PROFILE), 'profileSha256': digest(PROFILE),
             'physicalCameraEnabled': False, 'externalUploadAllowed': False}
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(('192.0.2.1', 9))  # No payload is sent.
    except OSError as error:
        guard['externalNoSendProbe'] = {'errno': error.errno, 'message': str(error)}
        guard['enforced'] = error.errno == errno.EPERM
    else:
        guard['enforced'] = False
    finally:
        probe.close()
    save(CONTROL / 'privacy-preflight.json', guard)
    if not guard['enforced']:
        raise RuntimeError('OS external-network deny preflight failed; no Android tool started')
    stamp('privacy-preflight-passed')
    # ps is a restricted binary under the existing OS policy. Bind a fresh
    # read-only parent inventory; do not relax the network boundary to run it.
    inventory_path = E / 'native-preparation/process-preflight-v2.json'
    inventory = json.loads(inventory_path.read_text())
    if inventory['existingEmulatorCount'] != 0 or time.time()-inventory['checkedAtUnix'] > 60:
        raise RuntimeError('Parent emulator inventory is stale or nonempty')
    for port in [5038, 5556, 5557]:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as local_probe:
            local_probe.settimeout(0.5)
            if local_probe.connect_ex(('127.0.0.1', port)) == 0:
                raise RuntimeError('Task-owned local emulator/ADB port already in use')
    guard['parentInventorySha256'] = digest(inventory_path)
    save(CONTROL / 'privacy-preflight.json', guard)
    # Existing identity files must already exist. Never generate or copy keys here.
    for path in [OLD/'android-user/adbkey', OLD/'android-emulator-home/adbkey']:
        if not path.is_file():
            raise RuntimeError('Existing Android identity missing')
    env = os.environ.copy()
    env.update(ANDROID_HOME=str(OLD/'android-test-sdk'),
               ANDROID_SDK_ROOT=str(OLD/'android-test-sdk'),
               ANDROID_USER_HOME=str(OLD/'android-user'),
               ANDROID_EMULATOR_HOME=str(OLD/'android-emulator-home'),
               ANDROID_AVD_HOME=str(OLD/'android-avd'),
               ANDROID_ADB_SERVER_PORT='5038', ADB_SERVER_PORT='5038',
               ADB_SERVER_SOCKET='tcp:localhost:5038',
               ADB_VENDOR_KEYS=str(OLD/'android-user/adbkey'))
    adb_command = [str(ADB), '-L', 'tcp:localhost:5038', 'nodaemon', 'server']
    emulator_command = [str(EMULATOR), '-avd', 'codex_mac_tv_api34', '-port', '5556',
        '-read-only', '-no-snapshot', '-memory', '1536', '-cores', '2',
        '-gpu', 'swiftshader_indirect', '-no-window', '-no-audio', '-no-boot-anim',
        '-no-metrics', '-camera-front', 'none', '-camera-back', 'none']
    record = {'status': 'starting', 'profileSha256': guard['profileSha256'],
        'adbBinarySha256': digest(ADB), 'emulatorBinarySha256': digest(EMULATOR),
        'apkSha256': digest(APK), 'apkBytes': APK.stat().st_size,
        'adbCommand': adb_command, 'emulatorCommand': emulator_command,
        'environment': {k:env[k] for k in ['ANDROID_HOME','ANDROID_USER_HOME','ANDROID_AVD_HOME','ANDROID_EMULATOR_HOME','ADB_SERVER_SOCKET']},
        'physicalCameraEnabled': False, 'newCredentials': False,
        'scope': 'Android TV API34 ARM64 emulator; not Fire OS or physical hardware'}
    save(CONTROL/'control-result.json', record)
    adb_process = emulator_process = None
    def adb(args, timeout=20):
        return subprocess.run([str(ADB), '-P', '5038', '-s', 'emulator-5556', *args],
            env=env, text=True, capture_output=True, timeout=timeout, check=True).stdout
    try:
        with open(CONTROL/'adb.local.log', 'wb') as log:
            adb_process = subprocess.Popen(adb_command, env=env, stdout=log, stderr=subprocess.STDOUT)
        time.sleep(0.5)
        if adb_process.poll() is not None:
            raise RuntimeError('Isolated ADB server exited')
        with open(CONTROL/'emulator.local.log', 'wb') as log:
            emulator_process = subprocess.Popen(emulator_command, env=env, stdout=log, stderr=subprocess.STDOUT)
        stamp('one-camera-disabled-emulator-started')
        started = time.monotonic()
        while time.monotonic()-started < 120:
            if emulator_process.poll() is not None:
                raise RuntimeError('Sandboxed emulator exited during boot')
            try:
                if adb(['shell','getprop','sys.boot_completed'], timeout=4).strip() == '1':
                    break
            except (subprocess.SubprocessError, OSError):
                pass
            time.sleep(2)
        else:
            raise RuntimeError('Sandboxed emulator boot deadline exceeded')
        record['bootSeconds'] = time.monotonic()-started
        if adb(['shell','getprop','ro.kernel.qemu']).strip() != '1':
            raise RuntimeError('Target identity is not emulator')
        record['device'] = {name: adb(['shell','getprop',prop]).strip() for name,prop in
            [('api','ro.build.version.sdk'),('abi','ro.product.cpu.abi'),('model','ro.product.model')]}
        stamp('emulator-booted-installing-local-apk')
        record['installOutput'] = adb(['install','-r',str(APK)], timeout=90).strip()
        # Preserve all per-frame scalar diagnostics in the guest's bounded log.
        record['logBufferOutput'] = adb(['logcat','-G','8M']).strip()
        node = shutil.which('node')
        if not node:
            raise RuntimeError('Existing Node executable unavailable')
        command = [node,'scripts/verify-native-video.mjs','--adb',str(ADB),
            '--adb-port','5038','--serial','emulator-5556','--model','float16',
            '--refinement','image','--completion','false','--out',str(OUT),
            'independent-both-press','independent-both-stretch','independent-cross-stretch']
        record['verificationCommand'] = command
        stamp('native-full-application-comparison-running')
        with open(CONTROL/'verification.log','wb') as log:
            completed = subprocess.run(command, cwd=R, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=200)
        record['verificationExitCode'] = completed.returncode
        record['status'] = 'verification-completed' if completed.returncode == 0 else 'verification-failed'
        stamp(record['status'])
    except BaseException as error:
        record['status'] = 'blocked-or-failed'
        record['error'] = {'type': type(error).__name__, 'message': str(error)}
        raise
    finally:
        cleanup = {}
        if emulator_process is not None and emulator_process.poll() is None:
            try:
                adb(['shell','am','force-stop','com.togethermove.tv.motion'])
                adb(['emu','kill'])
                emulator_process.wait(timeout=15)
                cleanup['emulator'] = 'stopped-by-task-owned-adb'
            except (OSError, subprocess.SubprocessError):
                emulator_process.terminate()
                try:
                    emulator_process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    emulator_process.kill()
                    emulator_process.wait(timeout=5)
                cleanup['emulator'] = 'terminated-task-owned-process'
        elif emulator_process is not None:
            cleanup['emulator'] = 'already-exited'
        if adb_process is not None and adb_process.poll() is None:
            adb_process.terminate()
            try:
                adb_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                adb_process.kill()
                adb_process.wait(timeout=5)
            cleanup['isolatedAdb'] = 'stopped-task-owned-server'
        record['cleanup'] = cleanup
        save(CONTROL/'control-result.json',record)
        stamp('cleanup-finished')
    if record.get('verificationExitCode') != 0:
        raise SystemExit(1)

if __name__ == '__main__':
    main()
