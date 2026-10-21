"""In-memory policy/ACK/heartbeat integration; no HTTP or capture."""
import unittest
from urllib.parse import urlencode

from service import MotionService, ProtocolError, parse_control
from test_activity import traces

CLIENT = "12345678-0000-4000-8000-000000000001"
ROUND = "12345678-0000-4000-8000-000000000002"


def control(**changes):
    return {"clientId":CLIENT, "roundId":ROUND, "revision":0, "active":True,
            "mode":"seated", "after":0, "policy":"activity", **changes}


class ActivityServiceTests(unittest.TestCase):
    def setUp(self):
        self.now = 0
        self.service = MotionService({"opencv":"5.0.0", "verified":True}, "synthetic", clock=lambda:self.now)

    def test_activity_events_ack_without_anatomical_order(self):
        after = 0
        emitted = []
        for now, observation in traces()["small-left"]:
            self.now = now
            self.service.poll(control(after=after))
            self.service.observe(self.service.token(), observation, "tracking")
            packet = self.service.poll(control(after=after))
            self.assertEqual(packet["expected"], "any")
            self.assertEqual(packet["policy"], "activity")
            for event in packet["events"]:
                self.assertEqual(event["gesture"], "activity")
                self.assertGreater(event["seq"], after)
                self.assertGreaterEqual(event["confidence"], .65)
                emitted.append(event)
                after = event["seq"]
            self.assertEqual(self.service.poll(control(after=after))["events"], [])
        self.assertGreaterEqual(len(emitted), 2)
        self.assertEqual(self.service.ack_seq, after)

    def test_policy_binding_and_legacy_strict(self):
        self.service.poll(control())
        with self.assertRaises(ProtocolError):
            self.service.poll(control(policy="strict", revision=1))
        with self.assertRaises(ProtocolError):
            self.service.poll(control(policy="strict", roundId=CLIENT))
        packet = self.service.poll(control(policy="strict", roundId=CLIENT, revision=1))
        self.assertEqual(packet["expected"], "left")
        legacy = {k:v for k,v in control().items() if k != "policy"}
        other = MotionService({"verified":True}, "synthetic")
        self.assertEqual(other.poll(legacy)["policy"], "strict")

    def test_pause_and_expired_heartbeat_reject_inflight_work_but_healthy_long_work_is_accepted(self):
        _, observation = traces()["static"][0]
        self.service.poll(control())
        token = self.service.token()
        for now in range(200, 6001, 200):
            self.now = now
            self.service.poll(control())
        self.service.observe(token, observation, "tracking")
        self.assertEqual(self.service.metrics["frames"], 1)
        stale = self.service.token()
        self.now += 1501
        self.assertIsNone(self.service.observe(stale, observation, "tracking"))
        self.assertEqual(self.service.metrics["frames"], 1)
        self.service.poll(control())
        self.assertNotEqual(self.service.token(), stale)
        current = self.service.token()
        self.service.observe(current, observation, "tracking")
        self.assertEqual(self.service.metrics["frames"], 2)
        self.service.poll(control(active=False, revision=1))
        self.assertIsNone(self.service.observe(current, observation, "tracking"))

    def test_optional_policy_parser_rejects_unknown_and_duplicate_fields(self):
        item = control();item["active"] = "1"
        target = "/motion/events?" + urlencode(item)
        self.assertEqual(parse_control(target)["policy"], "activity")
        for malformed in (target + "&policy=strict", target.replace("policy=activity", "policy=anything")):
            with self.assertRaises(ProtocolError):
                parse_control(malformed)


if __name__ == "__main__":
    unittest.main()
