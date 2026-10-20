import json
import threading
import unittest
import urllib.error
import urllib.request
from urllib.parse import urlencode
from uuid import UUID

from motion import synthetic_observation
from service import MotionService, ProtocolError, make_server, parse_control

CLIENT = "12345678-0000-4000-8000-000000000001"
ROUND = "12345678-0000-4000-8000-000000000002"


def control(**kwargs):
    return {"clientId": CLIENT, "roundId": ROUND, "revision": 0, "active": True,
            "mode": "seated", "after": 0, **kwargs}


def target(item=None):
    data = dict(item or control())
    data["active"] = "1" if data["active"] else "0"
    return "/motion/events?" + urlencode(data)


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.now = 0
        self.service = MotionService({"opencv": "5.0.0", "verified": True}, "synthetic",
                                     clock=lambda: self.now)
        self.service.poll(control())

    def observe(self, side, duration):
        for _ in range(duration // 50 + 1):
            self.service.observe(self.service.token(), synthetic_observation(side), "tracking")
            self.now += 50
            self.service.poll(control())

    def emit_left(self):
        self.observe("neutral", 350)
        self.observe("left", 400)

    def test_events_labelled_sequenced_deduplicated_and_expire(self):
        self.emit_left()
        packet = self.service.poll(control())
        self.assertEqual(packet["source"], "synthetic")
        self.assertEqual(packet["runtime"]["source"], "synthetic")
        self.assertEqual(len(packet["events"]), 1)
        self.assertEqual(packet["events"][0]["gesture"], "left-raise")
        self.assertEqual(self.service.poll(control(after=packet["seq"]))["events"], [])
        self.now += 1501
        self.assertEqual(self.service.poll(control())["events"], [])

    def test_stale_revision_cannot_resume_paused_round(self):
        old_token = self.service.token()
        packet = self.service.poll(control(revision=1, active=False))
        self.assertEqual(packet["status"], "paused")
        with self.assertRaises(ProtocolError):
            self.service.poll(control())
        self.assertIsNone(self.service.observe(old_token, synthetic_observation("left"), "tracking"))
        self.assertIsNone(self.service.token())

    def test_pause_rolls_back_event_not_accepted_by_game(self):
        self.emit_left()
        self.assertEqual(self.service.machine.expected, "right")
        paused = self.service.poll(control(revision=1, active=False))
        self.assertEqual(paused["expected"], "left")
        self.assertEqual(paused["events"], [])
        resumed = self.service.poll(control(revision=2))
        self.assertEqual(resumed["expected"], "left")

    def test_ack_processed_before_pause_preserves_accepted_side(self):
        self.emit_left()
        seq = self.service.seq
        paused = self.service.poll(control(revision=1, active=False, after=seq))
        self.assertEqual(paused["expected"], "right")
        resumed = self.service.poll(control(revision=2, after=seq))
        self.assertEqual(resumed["expected"], "right")
        self.assertFalse(self.service.machine.armed)

    def test_expired_pending_event_rolls_back_side_and_partial_hold(self):
        self.emit_left()
        self.now += 1501
        packet = self.service.poll(control())
        self.assertEqual(packet["expected"], "left")
        self.assertEqual(packet["events"], [])
        self.assertFalse(self.service.machine.armed)

    def test_late_ack_after_worker_expiry_reconciles_from_bounded_ledger(self):
        self.emit_left()
        seq = self.service.seq
        self.now += 1501
        self.service._expire_pending(self.now)
        self.assertEqual(self.service.machine.expected, "left")
        packet = self.service.poll(control(after=seq))
        self.assertEqual(packet["expected"], "right")
        self.assertEqual(packet["events"], [])

    def test_new_stream_echoes_identity_even_if_old_after_above_seq(self):
        packet = self.service.poll(control(after=999))
        self.assertTrue(packet["streamId"])
        self.assertEqual(packet["seq"], 0)
        self.assertEqual(packet["events"], [])

    def test_same_revision_context_changes_rejected(self):
        for patch in ({"active": False}, {"mode": "standing"}, {"roundId": str(UUID(int=55))}):
            with self.subTest(patch=patch), self.assertRaises(ProtocolError):
                self.service.poll(control(**patch))

    def test_round_change_resets_expected_and_discards_old_inference(self):
        self.emit_left()
        old_token = self.service.token()
        new = control(roundId=str(UUID(int=99)), revision=1)
        packet = self.service.poll(new)
        self.assertEqual(packet["expected"], "left")
        self.assertEqual(packet["events"], [])
        self.assertIsNone(self.service.observe(old_token, synthetic_observation("left"), "tracking"))

    def test_lease_expiry_disables_inference(self):
        token = self.service.token()
        self.now += 1501
        self.assertIsNone(self.service.token())
        self.assertIsNone(self.service.observe(token, synthetic_observation("left"), "tracking"))

    def test_client_takeover_retires_old_client(self):
        next_client = str(UUID(int=7))
        with self.assertRaises(ProtocolError):
            self.service.poll(control(clientId=next_client))
        self.now += 1501
        self.service.poll(control(clientId=next_client))
        self.now += 2000
        with self.assertRaises(ProtocolError):
            self.service.poll(control())

    def test_queue_is_bounded_at64(self):
        for n in range(100):
            self.service.events.append({"seq": n, "roundId": ROUND, "gesture": "left-raise",
                                        "confidence": 1.0, "at": self.now})
        self.assertEqual(len(self.service.events), 64)

    def test_parse_rejects_unknown_duplicate_oversized_and_bad_values(self):
        good = target()
        self.assertEqual(parse_control(good), control())
        bad = [good + "&active=0", good + "&x=1", good.replace("active=1", "active=true"),
               good.replace("revision=0", "revision=9007199254740992"),
               good.replace("after=0", "after=-1"), good.replace("mode=seated", "mode=lying"),
               good.replace(CLIENT, "x"), good + "x" * 1024, "/upload", "https://other/" + good]
        for item in bad:
            with self.subTest(item=item[:120]), self.assertRaises(ProtocolError):
                parse_control(item)


class HTTPTests(unittest.TestCase):
    def setUp(self):
        self.service = MotionService({"opencv": "5.0.0", "verified": False}, "synthetic")
        self.server = make_server(self.service, 0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def test_loopback_json_and_no_store(self):
        with urllib.request.urlopen(self.base + target()) as response:
            self.assertEqual(response.headers["Cache-Control"], "no-store")
            self.assertEqual(json.load(response)["source"], "synthetic")

    def test_other_paths_methods_and_foreign_browser_origins_rejected(self):
        for path, method, headers, status in [
            ("/frame", "GET", {}, 404), (target(), "POST", {}, 405),
            (target(), "GET", {"Origin": "https://foreign.invalid"}, 403),
            (target(), "GET", {"Host": "foreign.invalid"}, 403),
            (target(), "GET", {"Sec-Fetch-Site": "cross-site"}, 403),
        ]:
            request = urllib.request.Request(self.base + path, method=method, headers=headers)
            with self.subTest(path=path[:30], method=method, headers=headers):
                with self.assertRaises(urllib.error.HTTPError) as caught:
                    urllib.request.urlopen(request)
                self.assertEqual(caught.exception.code, status)
                caught.exception.close()


if __name__ == "__main__":
    unittest.main()
