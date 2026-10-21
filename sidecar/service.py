"""Loopback-only events and an active-session, ephemeral local JPEG preview."""

from collections import deque
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import math
import re
import threading
import time
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

from motion import GestureMachine

MAX_SAFE = 2**53 - 1
LEASE_MS = 1500
EVENT_TTL_MS = 1500
PREVIEW_TTL_MS = 500
MAX_PREVIEW_JPEG_BYTES = 150 * 1024
MAX_RESPONSE_BYTES = 220 * 1024
PREVIEW_VISIBILITY = {"leftShoulder", "rightShoulder", "leftWrist", "rightWrist"}
UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
FIELDS = {"clientId", "roundId", "revision", "active", "mode", "after"}
POLICIES = ("strict", "activity")


class ProtocolError(ValueError):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def parse_control(target):
    if len(target) > 1024:
        raise ProtocolError("Request too long", 414)
    parsed = urlsplit(target)
    if parsed.path not in ("/motion/events", "/motion/preview") or parsed.scheme or parsed.netloc or parsed.fragment:
        raise ProtocolError("Unknown endpoint", 404)
    try:
        query = parse_qs(parsed.query, strict_parsing=True, keep_blank_values=True,
                         max_num_fields=7)
    except ValueError as exc:
        raise ProtocolError("Malformed query") from exc
    if (set(query) not in (FIELDS, FIELDS | {"policy"})
            or any(len(values) != 1 for values in query.values())):
        raise ProtocolError("Six unique control fields and an optional policy required")
    item = {key: value[0] for key, value in query.items()}
    if not UUID.fullmatch(item["clientId"]) or not UUID.fullmatch(item["roundId"]):
        raise ProtocolError("Canonical lowercase UUIDs required")
    for key in ("revision", "after"):
        if not re.fullmatch(r"0|[1-9][0-9]{0,15}", item[key]):
            raise ProtocolError("Non-negative safe integers required")
        item[key] = int(item[key])
        if item[key] > MAX_SAFE:
            raise ProtocolError("Unsafe integer")
    if item["active"] not in ("0", "1") or item["mode"] not in ("seated", "standing"):
        raise ProtocolError("Invalid activity or mode")
    if item.get("policy", "strict") not in POLICIES:
        raise ProtocolError("Unknown motion policy")
    item["active"] = item["active"] == "1"
    return item


class MotionService:
    def __init__(self, runtime, source, clock=None):
        if source not in ("camera", "synthetic", "video"):
            raise ValueError("Explicit camera, synthetic, or video source required")
        self.runtime = dict(runtime, source=source)
        self.source = source
        self.stream_id = str(uuid4())
        self.clock = clock or (lambda: time.monotonic() * 1000)
        self.lock = threading.RLock()
        self.machine = GestureMachine()
        self.policy = "strict"
        self.events = deque(maxlen=64)
        self.history = deque(maxlen=64)  # Semantic ACK ledger only; never landmarks or frames.
        self.seq = 0
        self.ack_seq = 0
        self.ack_expected = "left"
        self.context = None
        self.last_poll = -math.inf
        self.retired_clients = set()
        self.latest_preview = None
        self.stopped = False
        self._capture_epoch = 0
        self.metrics = {"inferenceMs": 0.0, "fps": 0.0, "frames": 0}
        self.message = "Synthetic landmarks only; no camera" if source == "synthetic" else "Waiting for an active camera round"

    def token(self):
        with self.lock:
            if not self._active(self.clock()):
                self.latest_preview = None
                return None
            return (self.context["clientId"], self.context["roundId"], self.context["revision"], self._capture_epoch)

    def _active(self, now):
        return bool(not self.stopped and self.context and self.context["active"]
                    and now - self.last_poll <= LEASE_MS)

    def _reset_temporal(self):
        self._capture_epoch += 1
        # Only gestures acknowledged by the game survive a transport reset.
        # A queued event may have been discarded by a pause/revision race.
        if self.policy == "strict":
            self.machine.expected = self.ack_expected
        self.machine.reset_temporal()
        self.events.clear()
        self.latest_preview = None

    def _acknowledge(self, after):
        if after < self.ack_seq or after > self.seq:
            return  # Old request, or first request following a new sidecar stream.
        if self.policy == "strict":
            for event in self.history:
                if self.ack_seq < event["seq"] <= after:
                    self.ack_expected = "right" if event["gesture"] == "left-raise" else "left"
        while self.events and self.events[0]["seq"] <= after:
            self.events.popleft()
        self.ack_seq = after
        if self.policy == "activity":
            return  # Activity credit has no anatomical ordering to reconcile.
        expected = self.ack_expected
        for event in self.events:
            if event["gesture"] != expected + "-raise":
                self._reset_temporal()
                return
            expected = "right" if expected == "left" else "left"
        if self.machine.expected != expected:
            self.machine.reset_temporal()
            self.machine.expected = expected

    def _expire_pending(self, now):
        if self.events and now - self.events[0]["at"] > EVENT_TTL_MS:
            # Expired credit must not survive a transport reset in either policy.
            self._reset_temporal()

    def _new_round(self, policy):
        if policy != self.policy:
            if policy == "activity":
                from activity import ActivityMachine
                self.machine = ActivityMachine()
            else:
                self.machine = GestureMachine()
            self.policy = policy
        self.machine.new_round()
        self.latest_preview = None
        self.events.clear()
        self.history.clear()
        self.ack_expected, self.ack_seq = self.machine.expected, 0

    @staticmethod
    def _policy_control(control):
        policy = control.get("policy", "strict")
        if policy not in POLICIES:
            raise ProtocolError("Unknown motion policy")
        return dict(control, policy=policy)

    def poll(self, control):
        control = self._policy_control(control)
        now = self.clock()
        with self.lock:
            old = self.context
            if old and old["roundId"] == control["roundId"] and old["policy"] != control["policy"]:
                raise ProtocolError("Changing motion policy requires a new round", 409)
            if control["clientId"] in self.retired_clients:
                raise ProtocolError("Client retired; create a new client ID", 409)
            if old and old["clientId"] != control["clientId"]:
                if now - self.last_poll <= LEASE_MS:
                    raise ProtocolError("Another local player owns this session", 409)
                if len(self.retired_clients) >= 32:
                    raise ProtocolError("Client bound reached; restart sidecar", 409)
                self.retired_clients.add(old["clientId"])
                old = None
            if old:
                if control["revision"] < old["revision"]:
                    raise ProtocolError("Stale control revision", 409)
                changed = any(control[k] != old[k] for k in ("roundId", "active", "mode", "policy"))
                if control["revision"] == old["revision"] and changed:
                    raise ProtocolError("Changed context requires a newer revision", 409)
                if control["roundId"] != old["roundId"]:
                    self._new_round(control["policy"])
                else:
                    # ACK before clearing a previous control epoch's pending data.
                    self._acknowledge(control["after"])
                    if control["revision"] != old["revision"] or now - self.last_poll > LEASE_MS:
                        self._reset_temporal()
            else:
                self._new_round(control["policy"])
            self.context = {k: v for k, v in control.items() if k != "after"}
            self.last_poll = now
            if not control["active"]:
                self.latest_preview = None
                self.machine.lost("paused")
            self._expire_pending(now)
            events = [dict(seq=e["seq"], roundId=e["roundId"], gesture=e["gesture"],
                           confidence=e["confidence"], ageMs=max(0, round(now - e["at"], 2)))
                      for e in self.events if e["seq"] > control["after"]]
            calibration = self.machine.calibration_snapshot(now)
            return {"protocol": 1, "source": self.source, "streamId": self.stream_id, "runtime": self.runtime,
                    **self.context, "status": self.machine.status,
                    "expected": self.machine.expected, "heldMs": self.machine.held_ms,
                    "seq": self.seq, "events": events,
                    "metrics": {**self.metrics,
                                "armed": self.machine.armed and calibration["fresh"],
                                "calibration": calibration},
                    "message": self.message}

    def publish_preview(self, token, image, captured_at):
        """Replace one in-memory JPEG only if its original capture is still active."""
        with self.lock:
            now = self.clock()
            if (self.source not in ("camera", "video") or token is None or token != self.token()
                    or not math.isfinite(captured_at) or not 0 <= now - captured_at <= PREVIEW_TTL_MS):
                return False
            jpeg = image.get("jpeg", "")
            width, height = image.get("width"), image.get("height")
            visibility, confidence = image.get("visibility"), image.get("confidence")
            # Encoder output is bounded before caching; coordinates never enter this channel.
            max_data_url = 23 + 4 * ((MAX_PREVIEW_JPEG_BYTES + 2) // 3)
            if (not isinstance(jpeg, str) or not jpeg.startswith("data:image/jpeg;base64,")
                    or len(jpeg) > max_data_url or len(jpeg) <= 23
                    or type(width) is not int or type(height) is not int
                    or not 0 < width <= 320 or not 0 < height <= 640
                    or not isinstance(visibility, dict) or set(visibility) != PREVIEW_VISIBILITY
                    or any(type(value) is not bool for value in visibility.values())
                    or type(confidence) not in (int, float) or not math.isfinite(confidence)
                    or not 0 <= confidence <= 1):
                return False
            self.latest_preview = {"token": token, "capturedAt": captured_at,
                                   "jpeg": jpeg, "width": width, "height": height,
                                   "visibility": dict(visibility), "confidence": confidence}
            return True

    def preview(self, control):
        """Read without polling, acknowledging, extending leases, or opening capture."""
        control = self._policy_control(control)
        with self.lock:
            now = self.clock()
            response = {"source": self.source, "available": False,
                        **{key: control[key] for key in ("clientId", "roundId", "revision", "active", "mode", "policy")},
                        "expected": self.machine.expected, "heldMs": self.machine.held_ms}
            if self.source not in ("camera", "video"):
                return dict(response, status="synthetic")
            if not self._active(now):
                self.latest_preview = None
                status = "stopped" if self.stopped else "expired" if self.context and self.context["active"] else "paused"
                return dict(response, status=status)
            if not control["active"]:
                return dict(response, status="paused")
            if any(control[key] != self.context[key]
                   for key in ("clientId", "roundId", "revision", "active", "mode", "policy")):
                return dict(response, status="unauthorized")
            image = self.latest_preview
            if image is None:
                return dict(response, status="camera-error" if self.machine.status == "camera-error" else "waiting")
            if image["token"] != self.token() or not 0 <= now - image["capturedAt"] <= PREVIEW_TTL_MS:
                self.latest_preview = None
                return dict(response, status="stale")
            return dict(response, available=True, status=self.machine.status,
                        **{key: image[key] for key in ("jpeg", "width", "height", "visibility", "confidence")})

    def observe(self, token, observation, status, inference_ms=0.0, fps=0.0):
        now = self.clock()
        with self.lock:
            if token is None or token != self.token():
                return None
            self._expire_pending(now)
            if len(self.events) >= 64:
                self._reset_temporal()
            if token != self.token():
                return None  # A reset during expiry invalidated this captured frame.
            self.metrics = {"inferenceMs": round(inference_ms, 3), "fps": round(fps, 2),
                            "frames": self.metrics["frames"] + 1}
            if status != "tracking":
                self.machine.lost(status)
                return None
            event = self.machine.update(observation, now)
            if event:
                self.seq += 1
                self.events.append({**event, "seq": self.seq,
                                    "roundId": self.context["roundId"], "at": now})
                self.history.append(self.events[-1])
                return self.seq
            return None

    def idle(self):
        with self.lock:
            self._reset_temporal()
            self.machine.status = "paused" if self.context else "waiting"

    def camera_error(self, message):
        with self.lock:
            self.latest_preview = None
            self.machine.lost("camera-error")
            self.message = str(message)[:240]

    def close(self):
        with self.lock:
            self.stopped = True
            self.latest_preview = None


def make_server(service, port=8765):
    class Handler(BaseHTTPRequestHandler):
        server_version = "TogetherMoveLocal/1"

        def log_message(self, *_):
            pass  # No request, image or landmark logging.

        def _send(self, status, payload):
            data = json.dumps(payload, allow_nan=False, separators=(",", ":")).encode()
            if len(data) > MAX_RESPONSE_BYTES:
                status = 500
                data = b'{"error":"Local response exceeds size limit"}'
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            try:
                if self.client_address[0] != "127.0.0.1":
                    raise ProtocolError("Loopback clients only", 403)
                if self.headers.get("Host") not in (f"127.0.0.1:{self.server.server_port}",
                                                      f"localhost:{self.server.server_port}",
                                                      f"10.0.2.2:{self.server.server_port}"):
                    raise ProtocolError("Invalid local host", 403)
                # The browser uses its same-origin dev proxy; Android uses native HTTP.
                origin = self.headers.get("Origin")
                if origin and origin not in ("http://127.0.0.1:4173", "http://localhost:4173",
                                              "http://127.0.0.1:4174", "http://localhost:4174"):
                    raise ProtocolError("Untrusted browser origin", 403)
                if self.headers.get("Sec-Fetch-Site") == "cross-site":
                    raise ProtocolError("Cross-site controls not allowed", 403)
                if self.headers.get("Content-Length", "0") != "0" or self.headers.get("Transfer-Encoding"):
                    raise ProtocolError("Request bodies not supported")
                control = parse_control(self.path)
                payload = (service.preview(control) if urlsplit(self.path).path == "/motion/preview"
                           else service.poll(control))
                self._send(200, payload)
            except ProtocolError as exc:
                self._send(exc.status, {"error": str(exc), "protocol": 1, "source": service.source})

        def do_POST(self):
            self._send(405, {"error": "GET local polling only"})

        do_PUT = do_DELETE = do_PATCH = do_OPTIONS = do_POST

    class LocalServer(HTTPServer):
        request_queue_size = 8

        def get_request(self):
            connection, address = super().get_request()
            connection.settimeout(2)
            return connection, address

    return LocalServer(("127.0.0.1", port), Handler)
