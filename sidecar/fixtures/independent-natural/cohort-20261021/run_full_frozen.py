"""Existing Full adapter/service/JS pipeline on a separately frozen public set."""
import hashlib
import json
import math
from pathlib import Path
import socket
import sys
import time
from dataclasses import asdict
from unittest import mock

W = Path(__file__).resolve().parent
R = Path('/Users/frank/mygit/sway-and-sprout')
PROFILE = R.parent.parent / 'Documents/Codex/2026-10-19/task/mediapipe-evaluation/support/offline.sb'
PROFILE_SHA = '5c358b8d847211333e7ba22df82d84f796b5f30a41a2682209a949d783adbd08'

class UnsafePreflightError(RuntimeError):
    """Stop before SDK import, or stop all later cases after a pin change."""


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check_pins(plan, repo=R):
    try:
        for binding in plan['sourcePins']:
            if digest(repo / binding['path']) != binding['sha256']:
                raise UnsafePreflightError('Source pin changed: ' + binding['path'])
        for binding in plan['frozenFiles']:
            if digest(binding['path']) != binding['sha256']:
                raise UnsafePreflightError('Frozen file changed: ' + binding['path'])
        for item in plan['cases']:
            if digest(item['video']) != item['sha256']:
                raise UnsafePreflightError('Video pin changed: ' + item['caseId'])
    except (KeyError, TypeError, OSError) as error:
        raise UnsafePreflightError('Missing/invalid frozen binding: ' + str(error)) from error


def validate_plan(plan, repo=R):
    if (plan.get('status') != 'FROZEN_BEFORE_FIRST_MODEL_INFERENCE'
            or plan.get('annotationAuthorType') != 'AI' or plan.get('humanConfirmed') is not False
            or plan.get('fullProfile') != {'runningMode': 'IMAGE', 'numPoses': 2,
                                           'delegate': 'CPU', 'admissionThreshold': .65}):
        raise UnsafePreflightError('Invalid frozen plan/profile/annotation provenance')
    if not isinstance(plan.get('cases'), list) or not plan['cases']:
        raise UnsafePreflightError('Frozen cohort is empty')
    names = set()
    for item in plan['cases']:
        try:
            name, frames, fps = item['caseId'], item['frames'], item['fps']
            tick, pts = item['streamTickMs'], item['displayPtsMs']
            if (not isinstance(name, str) or not name or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in name)
                    or name in names or type(frames) is not int or not 1 <= frames <= 3600
                    or type(fps) not in (int, float) or not math.isfinite(fps) or not 1 <= fps <= 120
                    or frames * 1000 / fps > 30000.1
                    or type(tick) not in (int, float) or not math.isfinite(tick) or not 0 < tick <= 1000
                    or not isinstance(pts, list) or len(pts) != frames
                    or any(type(v) not in (int, float) or not math.isfinite(v) or abs(v - i * 1000 / fps) > tick
                           for i, v in enumerate(pts))
                    or any(b <= a for a, b in zip(pts, pts[1:]))
                    or type(item['expectationKnown']) is not bool
                    or (item['expectationKnown'] and (not isinstance(item['expectedGestures'], list)
                        or any(g not in ('left-raise', 'right-raise') for g in item['expectedGestures'])))):
                raise UnsafePreflightError('Invalid frozen case/clock: ' + str(name))
            names.add(name)
        except (KeyError, TypeError, ZeroDivisionError) as error:
            raise UnsafePreflightError('Incomplete frozen case: ' + str(error)) from error
    check_pins(plan, repo)


def execution_failures(report, item, state):
    failures = []
    if state.get('modelClosed') is not True:
        failures.append('model-cleanup-unconfirmed')
    if report is None:
        return failures + ['pipeline-exception-before-report']
    rows, fixture = state['rows'], report.get('fixture', {})
    if len(rows) != item['frames'] or fixture.get('decodedFrames') != item['frames']:
        failures.append('incomplete-frozen-file')
    fps = fixture.get('fps')
    if (type(fps) not in (int, float) or not math.isfinite(fps) or fps <= 0
            or abs((item['frames'] - 1) * 1000 / fps - item['displayPtsMs'][-1]) > item['streamTickMs']):
        failures.append('decoded-fps-disagrees-with-frozen-pts')
    for row in rows:
        i = row.get('frame', -1)
        if type(i) is not int or not 0 <= i < item['frames']:
            failures.append('invalid-trace-frame-index'); break
        for key in ('atVideoMs', 'serviceObservationMs', 'deliveryAtVideoMs'):
            value = row.get(key)
            if (type(value) not in (int, float) or not math.isfinite(value)
                    or abs(value - item['displayPtsMs'][i]) > item['streamTickMs']):
                failures.append(key + '-disagrees-with-frozen-pts')
    for key in ('gameScoringMatches', 'gameAcknowledgmentMatches'):
        if report.get(key) is not True:
            failures.append(key + '-false')
    for key in ('physicalCameraOpens', 'savedOutputFrames', 'uploadedFrames'):
        if report.get(key) != 0:
            failures.append(key + '-not-zero')
    if state.get('cleanupError'):
        failures.append('cleanup-error')
    return list(dict.fromkeys(failures))


def execute_cohort(plan, out, run_case, *, repo=R, plan_sha=None):
    """Persist each attempted case before classifying failure; never erase partial rows."""
    validate_plan(plan, repo)
    out = Path(out); out.mkdir(exist_ok=False)
    summary, unsafe_reason = [], None
    for item in plan['cases']:
        try:
            check_pins(plan, repo)
        except UnsafePreflightError as error:
            unsafe_reason = str(error); break
        print(json.dumps({'case': item['caseId'], 'stage': 'starting', 'frames': item['frames']}), flush=True)
        state, report, exception = {'rows': [], 'modelClosed': None}, None, None
        started = time.perf_counter()
        try:
            report = run_case(item, state)
        except Exception as error:
            exception = {'type': type(error).__name__, 'message': str(error)}
            report = state.get('report')
            if isinstance(error, UnsafePreflightError):
                unsafe_reason = str(error)
        failures = execution_failures(report, item, state)
        if exception:
            failures.append('case-exception')
        try:
            check_pins(plan, repo)
        except UnsafePreflightError as error:
            unsafe_reason = str(error); failures.append('unsafe-pin-change')
        if state.get('modelClosed') is not True:
            unsafe_reason = unsafe_reason or 'Model cleanup unconfirmed; no second graph will start'
        if any(key + '-not-zero' in failures for key in
               ('physicalCameraOpens', 'savedOutputFrames', 'uploadedFrames')):
            unsafe_reason = unsafe_reason or 'Capture/pixel-output policy check failed; stopping cohort'
        record = dict(report) if report is not None else {
            'source': 'video', 'evidenceType': 'partial-execution-exception',
            'fixture': {'file': Path(item['video']).name, 'sha256': item['sha256'],
                        'expectedFrozenFrames': item['frames'], 'recordedObservationRows': len(state['rows'])},
            'events': None, 'game': None, 'acknowledgedSeq': None,
            'verificationOutcome': {'status': 'execution-failed', 'completeGoalVerified': False,
                                    'scope': 'partial execution; no scored counts claimed', 'liveUserVerified': False}}
        record.update(rows=state['rows'], modelClosed=state.get('modelClosed'),
                      modelInitializationMs=state.get('modelInitializationMs'),
                      caseWallSecondsIncludingInitialization=time.perf_counter() - started,
                      planSha256=plan_sha, annotationAuthorType='AI', humanConfirmed=False,
                      preliminaryDiagnosticOnly=True, exception=exception, cleanupError=state.get('cleanupError'),
                      validationFailures=failures, executionStatus='failed' if failures else 'completed',
                      completeFileProcessed=len(state['rows']) == item['frames'] == record.get('fixture', {}).get('decodedFrames'),
                      unsafeStopReason=unsafe_reason)
        path = out / (item['caseId'] + '.json')
        path.write_text(json.dumps(record, indent=2, allow_nan=False) + '\n')
        game = record.get('game') or {}
        row = {'caseId': item['caseId'], 'frames': len(state['rows']), 'events': record.get('events'),
               'score': game.get('count'), 'ack': record.get('acknowledgedSeq'),
               'expectationKnown': item['expectationKnown'], 'outcome': record.get('verificationOutcome'),
               'executionStatus': record['executionStatus'], 'validationFailures': failures,
               'inferenceMedianMs': record.get('inferenceMedianMs'), 'processingSeconds': record.get('processingSeconds'),
               'modelInitializationMs': record.get('modelInitializationMs'),
               'caseWallSecondsIncludingInitialization': record['caseWallSecondsIncludingInitialization'],
               'modelClosed': record['modelClosed'], 'resultSha256': digest(path)}
        summary.append(row)
        (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
        print(json.dumps(row), flush=True)
        if unsafe_reason:
            break
    status = {'status': 'unsafe-abort' if unsafe_reason else 'execution-completed',
              'unsafeStopReason': unsafe_reason, 'attemptedCases': len(summary), 'frozenCases': len(plan['cases']),
              'allCasesExecuted': len(summary) == len(plan['cases']),
              'allExecutionChecksPassed': not unsafe_reason and all(not row['validationFailures'] for row in summary)}
    (out / 'cohort-status.json').write_text(json.dumps(status, indent=2) + '\n')
    if not (out / 'summary.json').exists():
        (out / 'summary.json').write_text('[]\n')
    return status


def run_pipeline_case(item, state):
    rows = state['rows']
    pose = None
    class RecordingPose:
        def __init__(self):
            started = time.perf_counter()
            self.inner = MediaPipeFullPose()
            self.initialization_ms = (time.perf_counter() - started) * 1000
            self.closed = False

        def __getattr__(self, name):
            return getattr(self.inner, name)

        def infer(self, frame):
            obs, status, duration = self.inner.infer(frame)
            height, width = map(int, frame.shape[:2])
            working_width = min(width, 640)
            working_height = height if width <= 640 else max(1, int(height * 640 / width))
            row = {'frame': len(rows), 'plannedFrameMs': len(rows) * 1000 / item['fps'],
                   'sourceImageWidth': width, 'sourceImageHeight': height,
                   'inferenceImageWidth': working_width, 'inferenceImageHeight': working_height,
                   'sourceScaleFromInference': {'x': width / working_width, 'y': height / working_height},
                   'inferenceStatus': status, 'inferenceMs': duration,
                   'observationWorkingPixels': asdict(obs) if obs is not None else None,
                   'gate': wrist_gates(obs, Config())}
            if obs is not None:
                original = asdict(obs)
                for name in ('left_shoulder', 'right_shoulder', 'left_wrist', 'right_wrist'):
                    original[name]['x'] *= width / working_width
                    original[name]['y'] *= height / working_height
                row['derivedObservationSourcePixels'] = original
                ls, rs, lw, rw = [getattr(obs, n) for n in
                                  ('left_shoulder', 'right_shoulder', 'left_wrist', 'right_wrist')]
                span = math.hypot(ls.x - rs.x, ls.y - rs.y)
                row['shoulderSpanWorkingPixels'] = span
                row['leftQ'] = (ls.y - lw.y) / span if span else None
                row['rightQ'] = (rs.y - rw.y) / span if span else None
            rows.append(row)
            return obs, status, duration

        def close(self):
            self.inner.close()
            self.closed = self.inner.landmarker is None

    class RecordingService(MotionService):
        def observe(self, *args, **kwargs):
            actual_ms = self.clock()
            result = super().observe(*args, **kwargs)
            rows[-1].update(atVideoMs=actual_ms, serviceObservationMs=actual_ms,
                            actualVerifierFps=kwargs.get('fps', args[4] if len(args) > 4 else None))
            m = self.machine
            rows[-1]['classifier'] = {'status': m.status, 'armed': m.armed,
                                     'heldMs': m.held_ms, 'expected': m.expected,
                                     'neutralSince': m.neutral_since, 'holdSince': m.hold_since,
                                     'calibration': m.calibration}
            return result

        def poll(self, *args, **kwargs):
            packet = super().poll(*args, **kwargs)
            if rows and rows[-1].get('serviceObservationMs') == self.clock():
                rows[-1]['deliveryAtVideoMs'] = self.clock()
            return packet

    def blocked_socket(*args, **kwargs):
        raise UnsafePreflightError('Python networking prohibited during file verification')


    expected = item['expectedGestures'] if item['expectationKnown'] else None
    try:
        pose = RecordingPose()
        state['modelInitializationMs'] = pose.initialization_ms
        with mock.patch('verify_video.MotionService', RecordingService), \
                mock.patch.object(socket, 'socket', side_effect=blocked_socket), \
                mock.patch.object(socket, 'create_connection', side_effect=blocked_socket):
            report = verify(Path(item['video']), expected=expected, pose_backend='mediapipe-full', pose_factory=lambda: pose)
        state['report'] = report
        report['verificationOutcome'] = verification_outcome(report)
        report['osNetworkDenial'] = {'profileSha256': PROFILE_SHA, 'beforeSdkImport': True,
                                    'allNetworkingDeniedIncludingChildren': True, 'noUnsandboxedFallback': True,
                                    'telemetryDisabledClaim': False}
        report['pointSemantics'] = 'Working-image pixels; derived source pixels use separate X/Y scale. Scores=min(visibility,presence); raw components not intercepted. Global0.65 is task-admission lower bound.'
        report['testScope'] = 'Actual existing model/classifier/service/currentJS reducer and ACK; no browser rendering, native inference or live camera.'
        return report
    finally:
        if pose is not None:
            try:
                if not pose.closed:
                    pose.close()
            except Exception as error:
                state['cleanupError'] = {'type': type(error).__name__, 'message': str(error)}
            state['modelClosed'] = pose.closed


def main():
    # A trusted outer deny-all launcher must be active before sidecar/SDK imports.
    if digest(PROFILE) != PROFILE_SHA:
        raise UnsafePreflightError('OS network-denial profile changed')
    probe = None
    try:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        probe.connect(('192.0.2.1', 9))  # TEST-NET, no payload sent
    except PermissionError as error:
        if error.errno != 1:
            raise UnsafePreflightError('Unexpected network denial') from error
    else:
        raise UnsafePreflightError('OS network denial absent; refusing SDK import')
    finally:
        if probe is not None:
            probe.close()
    plan_bytes = (W / 'execution-plan.freeze.json').read_bytes()
    plan = json.loads(plan_bytes)
    validate_plan(plan)
    global MediaPipeFullPose, Config, MotionService, verify, verification_outcome, wrist_gates
    sys.path.insert(0, str(R / 'sidecar'))
    from mediapipe_full import MediaPipeFullPose
    from motion import Config
    from service import MotionService
    from verify_video import verify, verification_outcome
    from video_input import wrist_gates
    status = execute_cohort(plan, W / 'full-results', run_pipeline_case,
                            plan_sha=hashlib.sha256(plan_bytes).hexdigest())
    print(json.dumps(status), flush=True)
    if not status['allExecutionChecksPassed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
