#!/usr/bin/env python3
"""Deterministic landmark -> classifier/service -> actual JS reducer verification.

No video decoding, DNN pose inference, physical camera, HTTP server, or private
progress is used. Output must never be described as human/video pose verification.
"""
import argparse
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import socket
import subprocess
import sys
from unittest import mock


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--sidecar', type=Path, help='Optional staged Python source directory')
    parser.add_argument('--scorer', type=Path)
    parser.add_argument('--output', type=Path, help='Optional scalar JSON result path')
    parser.add_argument('--packets-out', type=Path, help='Optional semantic packets, no coordinates/images')
    args = parser.parse_args()
    project = args.project.resolve()
    scorer = args.scorer or Path(__file__).resolve().parents[1] / 'scripts/score-motion-fixture.mjs'
    sys.path.insert(0, str(project / 'sidecar'))
    if args.sidecar:
        sys.path.insert(0, str(args.sidecar.resolve()))
    from motion import synthetic_observation
    from service import MotionService, ProtocolError

    client = '12345678-0000-4000-8000-000000000001'
    first_round = '12345678-0000-4000-8000-000000000002'
    second_round = '12345678-0000-4000-8000-000000000003'

    def score_packets(packets, round_id):
        payload = dict(source='synthetic', roundId=round_id, packets=packets, nowMs=0)
        command = ['node', str(scorer.resolve()), '--module', str(project / 'src/motion.js')]
        output = subprocess.run(command, input=json.dumps(payload), text=True,
                                capture_output=True, check=True)
        return payload, json.loads(output.stdout)

    class Driver:
        def __init__(self, auto_ack=True):
            self.now, self.after, self.auto_ack = 0, 0, auto_ack
            self.control = dict(clientId=client, roundId=first_round, revision=0,
                                active=True, mode='seated', after=0)
            # This metadata is a protocol fixture, not a claim that a DNN ran.
            runtime = dict(opencv='5.0.0-fixture', verified=True,
                           verification='synthetic protocol fixture; DNN not executed')
            self.service = MotionService(runtime, 'synthetic', clock=lambda: self.now)
            self.packets = []
            self.poll()

        def poll(self):
            self.control['after'] = self.after
            packet = self.service.poll(self.control)
            self.packets.append(deepcopy(packet))
            if self.auto_ack and packet['events']:
                # ACK the actual JS reducer's consumed sequence, not an assumed score.
                _, state = score_packets(self.packets, self.control['roundId'])
                self.after = state['lastSeq']
            return packet

        def step(self, side='neutral', confidence=1.0, observation=None, status='tracking'):
            self.poll()
            self.service.observe(self.service.token(), observation or synthetic_observation(side, confidence), status)
            packet = self.poll()
            self.now += 50
            return packet

        def frames(self, side, count, confidence=1.0):
            for _ in range(count):
                self.step(side, confidence)

        def neutral(self):
            # Also clear the500ms inter-event cooldown before the next hold.
            self.frames('neutral', 11)  # samples at0..500ms

        def raise_arm(self, side):
            self.frames(side, 8)  # samples at0..350ms

    results = []
    exported = []

    def check(name, expected, observed, **extra):
        results.append(dict(name=name, expected=expected, observed=observed,
                            passed=expected == observed, **extra))

    def game(name, driver=None, packets=None, round_id=first_round, expected_count=0,
             expected_gestures=None):
        packets = driver.packets if packets is None else packets
        payload, summary = score_packets(packets, round_id)
        check(name, expected_count, summary['count'], scoring=summary)
        if expected_gestures is not None:
            check(name + ':accepted-sides', expected_gestures, summary['acceptedGestures'])
        exported.append(dict(name=name, input=payload, observed=summary))
        return summary

    with mock.patch.object(socket.socket, 'bind', side_effect=AssertionError('Offline: server forbidden')):
        d = Driver()
        d.frames('neutral', 6)
        check('calibration-before300ms', False, d.service.machine.armed)
        d.step('neutral')
        check('calibration-at300ms', True, d.service.machine.armed)
        d.frames('left', 7)
        check('hold-before350ms', 0, d.service.seq)
        d.step('left')
        check('hold-at350ms', 1, d.service.seq)
        game('one-left-raise', d, expected_count=1, expected_gestures=['left-raise'])

        d = Driver()
        for side in ('left', 'right') * 3:
            d.neutral()
            d.raise_arm(side)
        d.poll()
        check('six-classifier-events', 6, d.service.seq)
        check('six-game-acknowledgments', 6, d.service.ack_seq)
        summary = game('six-alternating-rays', d, expected_count=6,
                       expected_gestures=['left-raise', 'right-raise'] * 3)
        check('six-rays-complete', True, summary['completed'])

        d = Driver()
        for side in ('left', 'right'):
            d.neutral()
            fixture = synthetic_observation()
            for height in (.60, .50, .44, .40, .36, .32, .28, .20, .15):
                wrist = 'left_wrist' if side == 'left' else 'right_wrist'
                observation = replace(fixture, **{wrist: replace(getattr(fixture, wrist), y=height)})
                d.step(observation=observation)
            d.raise_arm(side)
        check('gradual-transition-classifier-events', 2, d.service.seq)
        game('gradual-transition-rays', d, expected_count=2,
             expected_gestures=['left-raise', 'right-raise'])

        d = Driver()
        d.neutral()
        d.raise_arm('left')
        first_event_packet = next(deepcopy(p) for p in d.packets if p['events'])
        d.frames('left', 25)
        check('sustained-arm-emits-once', 1, d.service.seq)
        game('duplicate-packet-prevention', packets=[first_event_packet] * 10,
             expected_count=1, expected_gestures=['left-raise'])

        d = Driver()
        d.neutral()
        d.frames('left', 4)
        d.step('left', .4)
        check('low-confidence-clears-arming', False, d.service.machine.armed)
        d.frames('left', 15)
        check('low-confidence-cannot-complete-old-hold', 0, d.service.seq)
        d.neutral()
        d.raise_arm('left')
        game('fresh-neutral-after-low-confidence', d, expected_count=1)

        d = Driver()
        d.neutral()
        d.frames('left', 4)
        old_token = d.service.token()
        d.control.update(revision=1, active=False)
        d.poll()
        before = d.service.metrics['frames']
        d.service.observe(old_token, synthetic_observation('left'), 'tracking')
        check('late-inference-after-pause-dropped', before, d.service.metrics['frames'])
        try:
            d.service.poll({**d.control, 'revision': 0, 'active': True})
            stale_revision_rejected = False
        except ProtocolError:
            stale_revision_rejected = True
        check('stale-control-revision-rejected', True, stale_revision_rejected)
        d.control.update(revision=2, active=True)
        d.poll()
        d.frames('left', 15)
        check('resume-requires-fresh-neutral', 0, d.service.seq)
        d.neutral()
        d.raise_arm('left')
        game('pause-resume-fresh-calibration-rays', d, expected_count=1)

        d = Driver(auto_ack=False)
        d.neutral()
        d.raise_arm('left')
        held_packet = d.packets.pop()
        d.control.update(revision=1, active=False)
        paused = d.poll()
        held_packet['currentContext'] = dict(d.control)
        check('unacknowledged-pause-rolls-back-side', 'left', d.service.machine.expected)
        game('late-packet-after-pause-dropped', packets=[held_packet, paused], expected_count=0)

        d = Driver()
        d.neutral()
        d.frames('left', 4)
        d.now += 301
        d.frames('left', 12)
        check('long-frame-gap-clears-hold', 0, d.service.seq)
        d.neutral()
        d.raise_arm('left')
        game('fresh-neutral-after-gap-rays', d, expected_count=1)

        d = Driver()
        old_token = d.service.token()
        d.now += 1501
        check('lease-expired-before-renewal', None, d.service.token())
        before = d.service.metrics['frames']
        d.service.observe(old_token, synthetic_observation(), 'tracking')
        check('expired-lease-frame-dropped', before, d.service.metrics['frames'])
        d.poll()
        d.service.observe(old_token, synthetic_observation(), 'tracking')
        check('renewed-lease-rejects-old-inference', before, d.service.metrics['frames'],
              note='A token from before lease expiry must not enter the renewed epoch.')

        d = Driver()
        d.neutral()
        d.raise_arm('left')
        d.control.update(roundId=second_round, revision=1)
        d.after = 0
        d.poll()
        check('new-round-calibration-reset', False, d.service.machine.armed)
        d.neutral()
        d.raise_arm('left')
        game('old-round-packets-cannot-score-new-round', d, round_id=second_round, expected_count=1)

        for name, change in (
                ('wrong-round-event', {'roundId': second_round}),
                ('expired-event', {'ageMs': 1501}),
                ('low-confidence-event', {'confidence': .64}),
                ('wrong-side-event', {'gesture': 'right-raise'})):
            bad = deepcopy(first_event_packet)
            bad['events'] = [{**bad['events'][0], **change}]
            packets = [bad]
            if name in ('low-confidence-event', 'wrong-side-event'):
                packets.append(first_event_packet)  # Consumed sequence cannot be replayed as valid.
            game('game-rejects-' + name, packets=packets, expected_count=0)

    summary = dict(source='synthetic', evidenceType='synthetic-landmark-fixtures',
                   acknowledgmentMethod='Actual JS reducer lastSeq fed back into service after',
                   videoPoseInferenceVerified=False, realUserVerified=False,
                   physicalCameraUsed=False, serviceOpened=False, privateProgressSaved=False,
                   passed=all(row['passed'] for row in results), checksRun=len(results),
                   checksPassed=sum(row['passed'] for row in results), results=results)
    if args.output:
        args.output.write_text(json.dumps(summary, indent=2) + '\n')
    if args.packets_out:
        args.packets_out.write_text(json.dumps(exported, indent=2) + '\n')
    print(json.dumps(summary, indent=2))
    return 0 if summary['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
