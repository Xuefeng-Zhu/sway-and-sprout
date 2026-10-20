import {test} from 'node:test';
import assert from 'node:assert/strict';
import {acceptMotionEvent, createMotionClient, createMotionState} from '../src/motion.js';

const event = (seq = 1, overrides = {}) => ({seq, roundId: 'round-1', gesture: 'left-raise',
  confidence: 0.9, ageMs: 0, ...overrides});
const context = () => ({clientId: 'browser-1', roundId: 'round-1', revision: 1,
  active: true, mode: 'seated', after: 0});
const packet = (overrides = {}) => ({protocol: 1, runtime: {opencv: '5.0.0', verified: true},
  source: 'synthetic', clientId: 'browser-1', roundId: 'round-1', revision: 1,
  status: 'tracking', expected: 'left', heldMs: 0, seq: 1, events: [event()],
  metrics: {fps: 20, cameraReady: false}, ...overrides});
const response = value => new Response(JSON.stringify(value), {headers: {'content-type': 'application/json'}});
const deferred = () => {
  let resolve;
  const promise = new Promise(done => {resolve = done;});
  return {promise, resolve};
};

test('six alternating raises complete once and preserve manual progress shape', () => {
  let state = createMotionState('round-1');
  for (let seq = 1; seq <= 6; seq++) {
    state = acceptMotionEvent(state, event(seq, {gesture: seq % 2 ? 'left-raise' : 'right-raise'}), {active: true});
  }
  assert.equal(state.count, 6);
  assert.equal(state.completed, true);
  assert.equal(state.lastSeq, 6);
  assert.equal(state.expected, 'left');
  assert.equal(state.status, 'complete');
  assert.equal(acceptMotionEvent(state, event(7), {active: true}), state);
  assert.equal('frames' in state, false);
});

test('wrong side and low confidence consume sequence without counting or replay', () => {
  const initial = createMotionState('round-1');
  let state = acceptMotionEvent(initial, event(1, {gesture: 'right-raise'}), {active: true});
  assert.equal(state.count, 0);
  assert.equal(state.lastSeq, 1);
  state = acceptMotionEvent(state, event(2), {active: true});
  assert.equal(state.count, 1);
  assert.equal(acceptMotionEvent(state, event(1, {gesture: 'right-raise'}), {active: true}), state);
  state = acceptMotionEvent(state, event(3, {gesture: 'right-raise', confidence: 0.64}), {active: true});
  assert.equal(state.count, 1);
  assert.equal(state.lastSeq, 3);
});

test('pause, wrong round, duplicate, out of order, expiry and future age cannot count', () => {
  const state = acceptMotionEvent(createMotionState('round-1'), event(2), {active: true});
  for (const invalid of [event(3, {roundId: 'old-round'}), event(2), event(1),
    event(3, {ageMs: 1501}), event(3, {ageMs: -1}), event(3, {confidence: 1.01}),
    event(3, {confidence: NaN}), event(3, {seq: 2.5}), event(3, {gesture: 'Enter'}), null]) {
    assert.equal(acceptMotionEvent(state, invalid, {active: true}), state);
  }
  assert.equal(acceptMotionEvent(state, event(3, {gesture: 'right-raise'}), {active: false}), state);
});

test('local receipt age expires a queued event without cross-machine timestamps', () => {
  const state = createMotionState('round-1');
  assert.equal(acceptMotionEvent(state, event(1, {ageMs: 1000, receivedAt: 2000}), {active: true, now: 2501}), state);
  assert.equal(acceptMotionEvent(state, event(1, {receivedAt: 2000}), {active: true, now: 1999}), state);
  assert.equal(acceptMotionEvent(state, event(1, {ageMs: 1000, receivedAt: 2000}), {active: true, now: 2500}).count, 1);
});

test('single-flight client uses fixed same-origin route and preserves synthetic source', async () => {
  const pending = deferred();
  let calls = 0;
  let received;
  let options;
  const client = createMotionClient({getContext: context, onPacket: p => {received = p;},
    fetchImpl: (url, opts) => {
      calls++;
      assert.equal(new URL(url, 'https://app.togethermove.local').pathname, '/motion/events');
      assert.equal(new URL(url, 'https://app.togethermove.local').searchParams.get('active'), '1');
      options = opts;
      return pending.promise;
    }});
  const first = client.pollOnce();
  assert.equal(client.pollOnce(), first);
  pending.resolve(response(packet()));
  assert.equal((await first).source, 'synthetic');
  assert.equal(calls, 1);
  assert.equal(received.runtime.opencv, '5.0.0');
  assert.equal(options.credentials, 'omit');
  assert.equal(options.redirect, 'error');
  assert.ok(received.events[0].ageMs >= 0);
  assert.ok(received.events[0].receivedAt > 0);
  client.stop();
});

test('pause is sent to sidecar; no-person and low-confidence diagnostics survive', async () => {
  const current = {...context(), active: false};
  for (const status of ['no-person', 'low-confidence', 'paused', 'camera-error']) {
    const client = createMotionClient({getContext: () => current, onPacket: () => {},
      fetchImpl: async url => {
        assert.equal(new URL(url, 'https://local').searchParams.get('active'), '0');
        return response(packet({status, events: []}));
      }});
    const result = await client.pollOnce();
    assert.equal(result.status, status);
    assert.deepEqual(result.events, []);
    client.stop();
  }
});

test('arrival after pause, mode, revision or round change is discarded', async () => {
  for (const change of [{active: false}, {mode: 'standing'}, {revision: 2}, {roundId: 'round-2'}, {clientId: 'other'}]) {
    const current = context();
    const pending = deferred();
    let delivered = 0;
    const errors = [];
    const client = createMotionClient({getContext: () => current, onPacket: () => delivered++,
      onError: e => errors.push(e), fetchImpl: () => pending.promise});
    const result = client.pollOnce();
    Object.assign(current, change);
    pending.resolve(response(packet()));
    assert.equal(await result, null);
    assert.equal(delivered, 0);
    assert.equal(errors.length, 0);
    client.stop();
  }
});

test('invalid runtime, source, identity, sizes and events fail closed', async () => {
  const invalidPackets = [packet({runtime: {opencv: '4.13.0', verified: true}}),
    packet({source: 'unlabelled'}), packet({roundId: 'other'}), packet({revision: 2}),
    packet({heldMs: -1}), packet({seq: Infinity}), packet({events: Array(65).fill(event())}),
    packet({events: [event(2), event(1)], seq: 2}), packet({events: [event(1, {confidence: 1.1})]}),
    packet({events: [event(1, {ageMs: -1})]}), packet({events: [event(1, {roundId: 'other'})]}),
    packet({metrics: {path: 'private-file'}}), packet({status: 'unknown'})];
  for (const invalid of invalidPackets) {
    const errors = [];
    const client = createMotionClient({getContext: context, onPacket: () => assert.fail('invalid packet delivered'),
      onError: e => errors.push(e), fetchImpl: async () => response(invalid)});
    assert.equal(await client.pollOnce(), null);
    assert.equal(errors[0].code, 'invalid-response');
    client.stop();
  }
});

test('unverified runtime is delivered for diagnostic UI, with source intact', async () => {
  const client = createMotionClient({getContext: context, onPacket: () => {}, fetchImpl: async () =>
    response(packet({runtime: {opencv: 'unavailable', verified: false}, status: 'camera-error', events: []}))});
  const result = await client.pollOnce();
  assert.equal(result.runtime.verified, false);
  assert.equal(result.source, 'synthetic');
  client.stop();
});

test('body byte bound and malformed JSON are rejected', async () => {
  for (const body of ['{bad json', ' '.repeat(32769)]) {
    const errors = [];
    const client = createMotionClient({getContext: context, onPacket: () => assert.fail('oversized packet delivered'),
      onError: e => errors.push(e), fetchImpl: async () => new Response(body)});
    assert.equal(await client.pollOnce(), null);
    assert.equal(errors[0].code, 'invalid-response');
    client.stop();
  }
});

test('timeout releases single-flight slot, aborts fetch, and later reconnect works', async () => {
  let calls = 0;
  let signal;
  const errors = [];
  const client = createMotionClient({getContext: context, onPacket: () => {}, requestTimeoutMs: 10,
    onError: e => errors.push(e), fetchImpl: async (_url, options) => {
      calls++;
      signal = options.signal;
      if (calls === 1) return new Promise(() => {}); // Even a misbehaving fetch must time out.
      return response(packet({source: 'camera'}));
    }});
  assert.equal(await client.pollOnce(), null);
  assert.equal(errors[0].code, 'timeout');
  assert.equal(signal.aborted, true);
  assert.equal((await client.pollOnce()).source, 'camera');
  assert.equal(calls, 2);
  client.stop();
});

test('disconnect and HTTP failures report error, then next poll can recover', async () => {
  const errors = [];
  let calls = 0;
  const client = createMotionClient({getContext: context, onPacket: () => {}, onError: e => errors.push(e),
    fetchImpl: async () => {
      calls++;
      if (calls === 1) throw new Error('Connection refused');
      if (calls === 2) return new Response('', {status: 503});
      return response(packet({events: [], status: 'waiting'}));
    }});
  assert.equal(await client.pollOnce(), null);
  assert.equal(await client.pollOnce(), null);
  assert.equal((await client.pollOnce()).status, 'waiting');
  assert.equal(errors.length, 2);
  assert.equal(errors[1].code, 'disconnected');
  client.stop();
});

test('stop aborts in-flight request without surfacing a camera failure or late packet', async () => {
  const pending = deferred();
  const errors = [];
  let delivered = 0;
  const client = createMotionClient({getContext: context, onPacket: () => delivered++,
    onError: e => errors.push(e), fetchImpl: () => pending.promise});
  const result = client.pollOnce();
  client.stop();
  assert.equal(await result, null);
  pending.resolve(response(packet()));
  await Promise.resolve();
  assert.equal(delivered, 0);
  assert.equal(errors.length, 0);
});

test('invalid local context cannot initiate a request', async () => {
  let called = false;
  const errors = [];
  const client = createMotionClient({getContext: () => ({...context(), after: -1}),
    onPacket: () => {}, onError: e => errors.push(e), fetchImpl: () => {called = true;}});
  assert.equal(await client.pollOnce(), null);
  assert.equal(called, false);
  assert.equal(errors[0].code, 'invalid-context');
});
