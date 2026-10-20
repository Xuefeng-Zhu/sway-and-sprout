// This event client handles semantic motion only. The optional local preview
// uses its own bounded route and never contributes events or scoring.
import {sanitizeCalibration} from './calibration.js';

const MAX_EVENT_AGE_MS = 1500;
const MAX_PACKET_BYTES = 32 * 1024;
const MAX_EVENTS = 64;
const STATUSES = new Set(['ready', 'tracking', 'neutral', 'hold', 'no-person',
  'low-confidence', 'waiting', 'paused', 'camera-error']);
const finite = value => typeof value === 'number' && Number.isFinite(value);
const sequence = value => Number.isSafeInteger(value) && value >= 0;
const identifier = value => typeof value === 'string' && value.length > 0 &&
  value.length <= 128 && !/[\u0000-\u001f\u007f]/.test(value);
const object = value => value !== null && typeof value === 'object' && !Array.isArray(value);

export function createMotionState(roundId) {
  if (!identifier(roundId)) throw new TypeError('A bounded round ID is required.');
  return {roundId, count: 0, target: 6, expected: 'left', lastSeq: 0,
    completed: false, lastGesture: null, status: 'waiting'};
}

function validEvent(event) {
  return object(event) && sequence(event.seq) && event.seq > 0 &&
    identifier(event.roundId) && ['left-raise', 'right-raise'].includes(event.gesture) &&
    finite(event.confidence) && event.confidence >= 0 && event.confidence <= 1 &&
    finite(event.ageMs) && event.ageMs >= 0;
}

/**
 * Reduce a fresh semantic event, never a keypress. A fresh, well-formed event in
 * this active round consumes its sequence even when its side/confidence fails.
 * This prevents replaying an earlier right raise after accepting a later left.
 * receivedAt is an optional LOCAL receipt timestamp, not a camera clock.
 */
export function acceptMotionEvent(state, event, {active, now = Date.now()} = {}) {
  if (!active || state.completed || !validEvent(event) || event.roundId !== state.roundId ||
      event.seq <= state.lastSeq) return state;
  let age = event.ageMs;
  if (event.receivedAt !== undefined) {
    if (!finite(event.receivedAt) || !finite(now) || now < event.receivedAt) return state;
    age += now - event.receivedAt;
  }
  if (age > MAX_EVENT_AGE_MS) return state;
  const consumed = {...state, lastSeq: event.seq};
  if (event.confidence < 0.65 || event.gesture !== `${state.expected}-raise`) return consumed;
  const count = Math.min(state.count + 1, state.target);
  return {...consumed, count, expected: state.expected === 'left' ? 'right' : 'left',
    completed: count === state.target, lastGesture: event.gesture,
    status: count === state.target ? 'complete' : 'tracking'};
}

function motionError(code, message) {
  const error = new Error(message);
  error.code = code;
  return error;
}

export function snapshotContext(getContext) {
  const context = getContext();
  if (!object(context) || !identifier(context.clientId) || !identifier(context.roundId) ||
      !sequence(context.revision) || typeof context.active !== 'boolean' ||
      !['seated', 'standing'].includes(context.mode) || !sequence(context.after)) {
    throw motionError('invalid-context', 'Motion context is incomplete.');
  }
  return {clientId: context.clientId, roundId: context.roundId, revision: context.revision,
    active: context.active, mode: context.mode, after: context.after};
}

export function sameContext(first, current) {
  return first.clientId === current.clientId && first.roundId === current.roundId &&
    first.revision === current.revision && first.active === current.active && first.mode === current.mode;
}

function validatePacket(packet, context) {
  const runtime = packet?.runtime;
  const metrics = packet?.metrics ?? {};
  if (!object(packet) || packet.protocol !== 1 || !object(runtime) ||
      typeof runtime.opencv !== 'string' || runtime.opencv.length > 80 ||
      typeof runtime.verified !== 'boolean' || (runtime.verified && !/^5\./.test(runtime.opencv)) ||
      !['synthetic', 'camera', 'video'].includes(packet.source) ||
      (runtime.source !== undefined && runtime.source !== packet.source) ||
      packet.clientId !== context.clientId || packet.roundId !== context.roundId ||
      packet.revision !== context.revision || !STATUSES.has(packet.status) ||
      !['left', 'right'].includes(packet.expected) || !finite(packet.heldMs) ||
      packet.heldMs < 0 || packet.heldMs > 60000 || !sequence(packet.seq) ||
      !Array.isArray(packet.events) || packet.events.length > MAX_EVENTS ||
      !object(metrics) || Object.keys(metrics).length > 32 ||
      Object.entries(metrics).some(([key, value]) => key.length > 64 ||
        (key !== 'calibration' && !(finite(value) || typeof value === 'boolean' || value === null)))) {
    throw motionError('invalid-response', 'Motion service returned an invalid packet.');
  }
  let previous = 0;
  for (const event of packet.events) {
    if (!validEvent(event) || event.roundId !== context.roundId ||
        event.seq <= previous || event.seq > packet.seq || event.receivedAt !== undefined) {
      throw motionError('invalid-response', 'Motion service returned invalid events.');
    }
    previous = event.seq;
  }
  // Older services omit calibration. Invalid optional diagnostics cannot break
  // valid semantic events, and unbounded nested data never reaches the view.
  const cleanMetrics=Object.fromEntries(Object.entries(metrics).filter(([key])=>key!=='calibration'));
  const calibration=sanitizeCalibration(metrics.calibration);
  if(Object.hasOwn(metrics,'calibration'))cleanMetrics.calibration=calibration;
  return {...packet, metrics:cleanMetrics};
}

export async function readBoundedJson(response, maxBytes = MAX_PACKET_BYTES) {
  if (!response.ok) throw motionError('disconnected', `Motion service HTTP ${response.status}.`);
  const declaredLength = Number(response.headers?.get?.('content-length'));
  if (declaredLength > maxBytes) {
    throw motionError('invalid-response', 'Motion packet exceeds the size limit.');
  }
  let text;
  if (response.body?.getReader) {
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let bytes = 0;
    text = '';
    try {
      while (true) {
        const {value, done} = await reader.read();
        if (done) break;
        bytes += value.byteLength;
        if (bytes > maxBytes) {
          await reader.cancel();
          throw motionError('invalid-response', 'Motion packet exceeds the size limit.');
        }
        text += decoder.decode(value, {stream: true});
      }
      text += decoder.decode();
    } finally {
      reader.releaseLock();
    }
  } else {
    text = await response.text();
    if (new TextEncoder().encode(text).byteLength > maxBytes) {
      throw motionError('invalid-response', 'Motion packet exceeds the size limit.');
    }
  }
  try { return JSON.parse(text); }
  catch { throw motionError('invalid-response', 'Motion service returned invalid JSON.'); }
}

/**
 * Bounded, single-flight same-origin polling. Keep polling while active=false so
 * the sidecar observes pauses and resets its hold/neutral state. Only camera
 * input mode should start this client; switching back to manual must stop it.
 * Unverified runtime packets are diagnostic only: the caller MUST NOT consume
 * their events. source is preserved so synthetic mode stays visibly labelled.
 */
export function createMotionClient({getContext, onPacket, onError = () => {},
  fetchImpl = globalThis.fetch, intervalMs = 200, requestTimeoutMs = 1200}) {
  if (typeof getContext !== 'function' || typeof onPacket !== 'function' ||
      typeof fetchImpl !== 'function') throw new TypeError('Motion client callbacks are required.');
  const interval = Math.max(80, Math.min(5000, Number(intervalMs) || 200));
  const timeout = Math.max(10, Math.min(5000, Number(requestTimeoutMs) || 1200));
  let running = false;
  let timer = null;
  let inFlight = null;
  let controller = null;
  let generation = 0;

  async function requestPacket(requestGeneration) {
    let timeoutHandle;
    let requestController;
    try {
      const context = snapshotContext(getContext);
      const params = new URLSearchParams({...context, active: context.active ? '1' : '0'});
      requestController = new AbortController();
      controller = requestController;
      const startedAt = Date.now();
      const timeoutPromise = new Promise((_, reject) => {
        timeoutHandle = setTimeout(() => {
          reject(motionError('timeout', 'Motion service timed out.'));
          requestController.abort();
        }, timeout);
      });
      const abortedPromise = new Promise((_, reject) => {
        requestController.signal.addEventListener('abort', () =>
          reject(motionError('aborted', 'Motion request stopped.')), {once: true});
      });
      const responsePromise = Promise.resolve(fetchImpl(`/motion/events?${params}`, {
        method: 'GET', headers: {Accept: 'application/json'}, cache: 'no-store',
        credentials: 'omit', redirect: 'error', signal: requestController.signal,
      })).then(readBoundedJson);
      const rawPacket = await Promise.race([responsePromise, timeoutPromise, abortedPromise]);
      if (requestGeneration !== generation || !sameContext(context, snapshotContext(getContext))) return null;
      const packet = validatePacket(rawPacket, context);
      const receivedAt = Date.now();
      // Conservative transport allowance, using only this browser's clock.
      const transitMs = Math.max(0, receivedAt - startedAt);
      packet.events = packet.events.map(event => ({...event, ageMs: event.ageMs + transitMs, receivedAt}));
      onPacket(packet);
      return packet;
    } catch (error) {
      if (requestGeneration === generation) onError(error);
      return null;
    } finally {
      clearTimeout(timeoutHandle);
      if (controller === requestController) controller = null;
    }
  }

  function pollOnce() {
    if (!inFlight) {
      inFlight = requestPacket(generation).finally(() => { inFlight = null; });
    }
    return inFlight;
  }

  function schedule() {
    if (!running || timer !== null) return;
    timer = setTimeout(async () => {
      timer = null;
      await pollOnce();
      schedule();
    }, interval);
  }

  return {
    start() {
      if (running) return;
      running = true;
      void pollOnce().finally(schedule);
    },
    stop() {
      running = false;
      clearTimeout(timer);
      timer = null;
      generation += 1;
      controller?.abort();
    },
    pollOnce,
  };
}
