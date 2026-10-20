"""Deterministic single-player gestures. No camera, image or network dependencies."""

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Landmark:
    x: float
    y: float
    confidence: float = 1.0


@dataclass(frozen=True)
class Observation:
    """Anatomical sides, in unmirrored camera coordinates; pixels or normalized units."""

    left_shoulder: Landmark
    right_shoulder: Landmark
    left_wrist: Landmark
    right_wrist: Landmark
    confidence: float = 1.0


@dataclass(frozen=True)
class Config:
    hold_ms: int = 350
    neutral_ms: int = 300
    cooldown_ms: int = 500
    min_confidence: float = 0.65
    max_frame_gap_ms: int = 300
    raise_margin: float = 0.30
    neutral_margin: float = 0.20


class GestureMachine:
    def __init__(self, config=Config()):
        self.config = config
        self.expected = "left"
        self.last_emitted = -math.inf
        self.last_observed = None
        self.reset_temporal()

    def reset_temporal(self):
        """A pause, loss or round transition must never preserve a partial hold."""
        self.armed = False
        self.neutral_since = None
        self.hold_since = None
        self.held_ms = 0
        self.status = "waiting"
        self.last_observed = None
        self._feedback("waiting")

    def _feedback(self, reason, gates=None, minimum=0.0, low_confidence=(), neutral_ms=0):
        """Bounded last-frame explanation; never coordinates, images or a new clock."""
        self.calibration = {
            "reason": reason,
            "neutralMs": max(0, min(self.config.neutral_ms, int(neutral_ms))),
            "requiredNeutralMs": self.config.neutral_ms,
            "holdMs": max(0, min(self.config.hold_ms, self.held_ms)),
            "requiredHoldMs": self.config.hold_ms,
            "gates": dict(zip(("left", "right"), gates or ("unknown", "unknown"))),
            "lowConfidence": list(low_confidence),
            "minimumConfidence": round(float(minimum), 3),
        }

    def calibration_snapshot(self, now_ms):
        """A stale frame cannot advertise readiness; polling never arms the machine."""
        age = None if self.last_observed is None else now_ms - self.last_observed
        fresh = age is not None and 0 <= age <= self.config.max_frame_gap_ms
        snapshot = {**self.calibration, "gates": dict(self.calibration["gates"]),
                    "lowConfidence": list(self.calibration["lowConfidence"]),
                    "fresh": fresh,
                    "ageMs": None if age is None else max(0, min(60000, int(age)))}
        if age is not None and not fresh:
            snapshot.update(reason="stale", neutralMs=0, holdMs=0,
                            gates={"left": "unknown", "right": "unknown"},
                            lowConfidence=[], minimumConfidence=0.0)
        return snapshot

    def new_round(self):
        self.expected = "left"
        self.last_emitted = -math.inf
        self.reset_temporal()

    def lost(self, status="low-confidence"):
        self.reset_temporal()
        self.status = status
        self._feedback(status if status in ("no-person", "low-confidence", "paused", "camera-error")
                       else "waiting")

    def update(self, observation, now_ms):
        if not math.isfinite(now_ms):
            raise ValueError("finite monotonic time required")
        if self.last_observed is not None:
            gap = now_ms - self.last_observed
            if gap < 0:
                raise ValueError("time must be monotonic")
            if gap > self.config.max_frame_gap_ms:
                self.reset_temporal()
        self.last_observed = now_ms
        if observation is None:
            self.lost("no-person")
            return None
        points = (observation.left_shoulder, observation.right_shoulder,
                  observation.left_wrist, observation.right_wrist)
        values = [observation.confidence] + [p.confidence for p in points]
        if (any(not math.isfinite(v) or v < self.config.min_confidence or v > 1
                for v in values) or
                any(not math.isfinite(v) for p in points for v in (p.x, p.y))):
            self.lost("low-confidence")
            names = ("person", "leftShoulder", "rightShoulder", "leftWrist", "rightWrist")
            weak = [name for name, value in zip(names, values)
                    if not math.isfinite(value) or not self.config.min_confidence <= value <= 1]
            weak.extend(name for name, point in zip(names[1:], points)
                        if name not in weak and not all(math.isfinite(v) for v in (point.x, point.y)))
            minimum = min(values) if all(math.isfinite(v) and 0 <= v <= 1 for v in values) else 0
            self._feedback("low-confidence", minimum=minimum, low_confidence=weak)
            return None
        ls, rs, lw, rw = points
        width = math.hypot(ls.x - rs.x, ls.y - rs.y)
        if width <= 0.00001:
            self.lost("low-confidence")
            return None
        left_up = lw.y < ls.y - width * self.config.raise_margin
        right_up = rw.y < rs.y - width * self.config.raise_margin
        left_down = lw.y > ls.y + width * self.config.neutral_margin
        right_down = rw.y > rs.y + width * self.config.neutral_margin
        gates = ("up" if left_up else "down" if left_down else "transition",
                 "up" if right_up else "down" if right_down else "transition")
        minimum = min(values)
        if left_down and right_down:
            self.hold_since = None
            self.held_ms = 0
            if self.neutral_since is None:
                self.neutral_since = now_ms
            if now_ms - self.neutral_since >= self.config.neutral_ms:
                self.armed = True
            self.status = "tracking" if self.armed else "neutral"
            self._feedback("ready" if self.armed else "settling-neutral", gates, minimum,
                           neutral_ms=now_ms - self.neutral_since)
            return None
        self.neutral_since = None
        correct = ((left_up and right_down) if self.expected == "left"
                   else (right_up and left_down))
        if not correct:
            # After neutral, the expected wrist can pass through shoulder height
            # while the other stays down. This never arms a new gesture or
            # preserves partial hold time. Other ambiguous poses need neutral.
            transitioning = ((not left_up and not left_down and right_down)
                             if self.expected == "left" else
                             (not right_up and not right_down and left_down))
            if not transitioning:
                self.armed = False
            self.hold_since = None
            self.held_ms = 0
            self.status = "neutral"
            wrong_side = right_up and left_down if self.expected == "left" else left_up and right_down
            reason = ("both-raised" if left_up and right_up else "wrong-side" if wrong_side
                      else "ready" if transitioning and self.armed else "needs-neutral" if transitioning
                      else "ambiguous")
            self._feedback(reason, gates, minimum)
            return None
        if not self.armed or now_ms - self.last_emitted < self.config.cooldown_ms:
            self.hold_since = None
            self.held_ms = 0
            self.status = "neutral"
            self._feedback("needs-neutral" if not self.armed else "cooldown", gates, minimum)
            return None
        if self.hold_since is None:
            self.hold_since = now_ms
        self.held_ms = max(0, int(now_ms - self.hold_since))
        self.status = "hold"
        self._feedback("holding", gates, minimum)
        if self.held_ms < self.config.hold_ms:
            return None
        gesture = self.expected + "-raise"
        self.expected = "right" if self.expected == "left" else "left"
        self.last_emitted = now_ms
        self.reset_temporal()
        self.status = "neutral"
        self._feedback("return-to-neutral", gates, minimum)
        return {"gesture": gesture, "confidence": min(values)}


def synthetic_observation(side="neutral", confidence=1.0):
    """Explicit deterministic fixture. Never represents camera verification."""
    return Observation(
        Landmark(0.65, 0.40, confidence), Landmark(0.35, 0.40, confidence),
        Landmark(0.65, 0.15 if side in ("left", "both") else 0.75, confidence),
        Landmark(0.35, 0.15 if side in ("right", "both") else 0.75, confidence),
        confidence,
    )
