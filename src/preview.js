import {snapshotContext, sameContext, readBoundedJson} from './motion.js';

const MAX_PACKET_BYTES = 220 * 1024;
const MAX_JPEG_CHARS = 205 * 1024;
const VISIBILITY_KEYS = ['leftShoulder', 'rightShoulder', 'leftWrist', 'rightWrist'];
const STATUSES = new Set(['ready', 'tracking', 'neutral', 'hold', 'no-person',
  'low-confidence', 'waiting', 'paused', 'camera-error', 'synthetic',
  'unauthorized', 'expired', 'stale', 'stopped']);
const finite = value => typeof value === 'number' && Number.isFinite(value);

function previewError(message) {
  const error = new Error(message);
  error.code = 'invalid-preview';
  return error;
}

function validatePreview(packet, context) {
  if (!packet || typeof packet !== 'object' || Array.isArray(packet) ||
      !['camera', 'synthetic', 'video'].includes(packet.source) ||
      typeof packet.available !== 'boolean' || !STATUSES.has(packet.status) ||
      !sameContext(context, packet)) {
    throw previewError('The local camera returned an invalid preview.');
  }
  if (!packet.available) {
    if (packet.jpeg !== undefined) throw previewError('An inactive preview included an image.');
    return packet;
  }
  if (!['camera', 'video'].includes(packet.source) || !context.active ||
      !Number.isInteger(packet.width) || packet.width < 1 || packet.width > 320 ||
      !Number.isInteger(packet.height) || packet.height < 1 || packet.height > 640 ||
      typeof packet.jpeg !== 'string' || packet.jpeg.length > MAX_JPEG_CHARS ||
      !/^data:image\/jpeg;base64,[A-Za-z0-9+/]+={0,2}$/.test(packet.jpeg) ||
      !packet.visibility || VISIBILITY_KEYS.some(key => typeof packet.visibility[key] !== 'boolean') ||
      !finite(packet.confidence) || packet.confidence < 0 || packet.confidence > 1 ||
      !((context.policy ?? 'strict') === 'activity' ? packet.expected === 'any' : ['left', 'right'].includes(packet.expected)) ||
      !finite(packet.heldMs) || packet.heldMs < 0 || packet.heldMs > 60000) {
    throw previewError('The local camera returned an invalid preview image.');
  }
  return packet;
}

/**
 * A view of the existing inference frame, never another camera owner. Polling
 * cannot activate capture or score rays. Images remain in memory/DOM only and
 * are cleared whenever activity or context changes, including late responses.
 */
export function createPreviewClient({getContext, onPreview, onClear = () => {},
  onError = () => {}, fetchImpl = globalThis.fetch, intervalMs = 250,
  requestTimeoutMs = 1200}) {
  if (typeof getContext !== 'function' || typeof onPreview !== 'function' ||
      typeof fetchImpl !== 'function') throw new TypeError('Preview client callbacks are required.');
  const interval = Math.max(200, Math.min(5000, Number(intervalMs) || 250));
  const timeout = Math.max(10, Math.min(5000, Number(requestTimeoutMs) || 1200));
  let running = false, timer = null, inFlight = null, controller = null, generation = 0;

  async function requestPreview(requestGeneration) {
    let requestController, timeoutHandle, context;
    try {
      context = snapshotContext(getContext);
      if (!context.active) {
        onClear('off');
        return null;
      }
      requestController = new AbortController();
      controller = requestController;
      const params = new URLSearchParams({...context, active: '1'});
      const timeoutPromise = new Promise((_, reject) => {
        timeoutHandle = setTimeout(() => {
          reject(previewError('The local camera preview timed out.'));
          requestController.abort();
        }, timeout);
      });
      const abortedPromise = new Promise((_, reject) => {
        requestController.signal.addEventListener('abort', () =>
          reject(previewError('Camera preview stopped.')), {once: true});
      });
      const responsePromise = Promise.resolve(fetchImpl(`/motion/preview?${params}`, {
        method: 'GET', headers: {Accept: 'application/json'}, cache: 'no-store',
        credentials: 'omit', redirect: 'error', signal: requestController.signal,
      })).then(response => readBoundedJson(response, MAX_PACKET_BYTES));
      const raw = await Promise.race([responsePromise, timeoutPromise, abortedPromise]);
      // A six-ray completion, pause, rerender, or new round invalidates this frame.
      if (requestGeneration !== generation || !sameContext(context, snapshotContext(getContext))) {
        if (requestGeneration === generation) onClear('off');
        return null;
      }
      const preview = validatePreview(raw, context);
      onPreview(preview);
      return preview;
    } catch (error) {
      if (requestGeneration === generation) {
        onClear('unavailable');
        if (!context || sameContext(context, snapshotContext(getContext))) onError(error);
      }
      return null;
    } finally {
      clearTimeout(timeoutHandle);
      if (controller === requestController) controller = null;
    }
  }

  function pollOnce() {
    if (!inFlight) {
      const pending = requestPreview(generation).finally(() => {
        if (inFlight === pending) inFlight = null;
      });
      inFlight = pending;
    }
    return inFlight;
  }

  function schedule(requestGeneration) {
    if (!running || requestGeneration !== generation || timer !== null) return;
    timer = setTimeout(async () => {
      timer = null;
      if (!snapshotContext(getContext).active) {
        stop('off');
        return;
      }
      await pollOnce();
      schedule(requestGeneration);
    }, interval);
  }

  function stop(reason = 'off') {
    running = false;
    clearTimeout(timer);
    timer = null;
    generation += 1;
    controller?.abort();
    onClear(reason);
  }

  return {
    start() {
      if (running || !snapshotContext(getContext).active) return;
      running = true;
      onClear('waiting');
      const requestGeneration = generation;
      void pollOnce().finally(() => schedule(requestGeneration));
    },
    stop,
    pollOnce,
  };
}
