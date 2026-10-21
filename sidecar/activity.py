"""Movement-first policy over synthetic or inferred landmarks; no image dependencies.

Constants are mirrored in ActivityMachine.java. These are provisional gameplay
settings, not calibrated recognition accuracy or an exercise prescription.
"""
import math


def synthetic_activity_observation(now_ms):
    """Small generated wrist motion, explicitly for the synthetic service only."""
    from motion import Landmark, Observation
    offset = .03 * math.sin(now_ms * 2 * math.pi / 800)
    return Observation(Landmark(.65, .4), Landmark(.35, .4),
                       Landmark(.65 + offset, .75), Landmark(.35, .75))


class ActivityMachine:
    MIN_CONFIDENCE = 0.65
    MAX_GAP_MS = 300
    WINDOW_MS = 1500
    COOLDOWN_MS = 1000
    MIN_MOVEMENT_MS = 250
    DEADBAND = 0.025
    PATH_REQUIRED = 0.20
    MAX_JUMP = 0.75

    def __init__(self):
        self.new_round()

    def new_round(self):
        self.last_emitted = -math.inf
        self.reset_temporal()

    def reset_temporal(self):
        self.expected = "any"
        self.status = "waiting"
        self.armed = False
        self.held_ms = 0
        self.last_observed = None
        self.channels = {}

    def lost(self, status="low-confidence"):
        self.reset_temporal()
        self.status = status

    @staticmethod
    def _valid(point):
        return point is not None and all(math.isfinite(v) for v in
            (point.x, point.y, point.confidence)) and ActivityMachine.MIN_CONFIDENCE <= point.confidence <= 1

    def _features(self, observation):
        if observation is None:
            return {}
        ls, rs = observation.left_shoulder, observation.right_shoulder
        if not self._valid(ls) or not self._valid(rs):
            return {}
        span = math.hypot(rs.x - ls.x, rs.y - ls.y)
        if span <= 1e-5:
            return {}
        confidence = min(ls.confidence, rs.confidence)
        features = {}
        for name, wrist, shoulder in (("left", observation.left_wrist, ls),
                                       ("right", observation.right_wrist, rs)):
            if self._valid(wrist):
                features[name] = ((wrist.x - shoulder.x) / span,
                                  (wrist.y - shoulder.y) / span,
                                  min(confidence, wrist.confidence))
        lh, rh = observation.left_hip, observation.right_hip
        if self._valid(lh) and self._valid(rh):
            features["torso"] = (((ls.x + rs.x) - (lh.x + rh.x)) / (2 * span),
                                  ((ls.y + rs.y) - (lh.y + rh.y)) / (2 * span),
                                  min(confidence, lh.confidence, rh.confidence))
        return features

    def update(self, observation, now_ms):
        if not math.isfinite(now_ms):
            raise ValueError("finite monotonic time required")
        previous = self.last_observed
        if previous is not None and now_ms < previous:
            raise ValueError("time must be monotonic")
        if previous is not None and now_ms - previous > self.MAX_GAP_MS:
            self.reset_temporal()
            previous = None
        features = self._features(observation)
        if not features:
            self.lost("no-person" if observation is None else "low-confidence")
            return None
        self.last_observed = now_ms
        self.status, self.armed = "tracking", True
        self.channels = {name: value for name, value in self.channels.items() if name in features}
        candidate = None
        for name, (x, y, confidence) in features.items():
            channel = self.channels.get(name)
            if channel is None:
                self.channels[name] = [x, y, x, y, now_ms, []]
                continue
            if previous == now_ms:
                continue
            if math.hypot(x - channel[0], y - channel[1]) > self.MAX_JUMP:
                self.channels[name] = [x, y, x, y, now_ms, []]
                continue
            alpha = min(1.0, (now_ms - channel[4]) / 100.0)
            channel[0] += alpha * (x - channel[0])
            channel[1] += alpha * (y - channel[1])
            channel[4] = now_ms
            distance = math.hypot(channel[0] - channel[2], channel[1] - channel[3])
            history = channel[5]
            history[:] = [row for row in history if now_ms - row[0] <= self.WINDOW_MS]
            if distance < self.DEADBAND:
                continue
            channel[2], channel[3] = channel[0], channel[1]
            history.append((now_ms, distance))
            if (len(history) >= 3 and now_ms - history[0][0] >= self.MIN_MOVEMENT_MS
                    and sum(row[1] for row in history) >= self.PATH_REQUIRED
                    and now_ms - self.last_emitted >= self.COOLDOWN_MS):
                candidate = max(candidate or 0, confidence)
        if candidate is None:
            return None
        self.last_emitted = now_ms
        for channel in self.channels.values():
            channel[5].clear()
        return {"gesture": "activity", "confidence": candidate}

    def calibration_snapshot(self, now_ms):
        age = None if self.last_observed is None else now_ms - self.last_observed
        return {"reason": "activity", "fresh": age is not None and 0 <= age <= self.MAX_GAP_MS,
                "ageMs": None if age is None else max(0, min(60000, age))}
