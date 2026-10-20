// Runtime identity only: verified is supplied by the local inference service.
// A valid descriptor does not establish device support or measured performance.
const object = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const semanticVersion = /^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*)(?:\.(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*))*)?(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$/;

export function validMotionRuntime(runtime) {
  if (!object(runtime) || typeof runtime.verified !== 'boolean') return false;
  if (Object.hasOwn(runtime, 'engine')) {
    return runtime.engine === 'litert' && runtime.platform === 'android' &&
      !Object.hasOwn(runtime, 'opencv') &&
      typeof runtime.engineVersion === 'string' && runtime.engineVersion.length <= 80 &&
      !/[\s\u0000-\u001f\u007f]/.test(runtime.engineVersion) && semanticVersion.test(runtime.engineVersion) &&
      typeof runtime.modelSha256 === 'string' && runtime.modelSha256.length === 64 &&
      /^[0-9a-f]{64}$/.test(runtime.modelSha256);
  }
  // Preserve legacy diagnostics and optional Full backend metadata. In
  // particular, an unavailable OpenCV runtime can still explain its error.
  return typeof runtime.opencv === 'string' && runtime.opencv.length <= 80 &&
    (!runtime.verified || /^5\./.test(runtime.opencv));
}
