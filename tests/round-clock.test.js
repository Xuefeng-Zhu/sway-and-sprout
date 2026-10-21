import test from 'node:test';
import assert from 'node:assert/strict';
import {roundTickDelta} from '../src/round-clock.js';

test('ordinary frames credit the actual monotonic interval', () => {
  assert.deepEqual(roundTickDelta(100, 116), {wallMs:16, creditedMs:16, stalledMs:0});
  assert.deepEqual(roundTickDelta(100, 100), {wallMs:0, creditedMs:0, stalledMs:0});
});

test('a stalled animation exposes wall time instead of claiming a real-time countdown', () => {
  assert.deepEqual(roundTickDelta(100, 6100), {wallMs:6000, creditedMs:250, stalledMs:5750});
  const deltas = [0, 100, 6100, 6200].slice(1).map((now,i)=>roundTickDelta([0,100,6100][i], now));
  assert.equal(deltas.reduce((sum,x)=>sum+x.wallMs,0), 6200);
  assert.equal(deltas.reduce((sum,x)=>sum+x.creditedMs,0), 450);
});

test('resume establishes a fresh baseline and invalid clock values fail closed', () => {
  // render() resets the baseline on resume; paused wall time is never credited.
  assert.equal(roundTickDelta(10000,10016).creditedMs,16);
  for (const args of [[10,9],[NaN,10],[0,Infinity]]) {
    assert.throws(()=>roundTickDelta(...args), TypeError);
  }
});
