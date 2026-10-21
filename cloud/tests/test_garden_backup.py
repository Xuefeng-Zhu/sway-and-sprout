import base64
import copy
import hashlib
import io
import json
from pathlib import Path
from unittest import TestCase, main
from unittest.mock import patch
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import garden_backup as api

GARDEN = "0f8d0d13-6d01-421e-8d61-7a53a18c4f01"
TOKEN = base64.urlsafe_b64encode(bytes(range(32))).decode().rstrip("=")
OTHER = base64.urlsafe_b64encode(bytes(reversed(range(32)))).decode().rstrip("=")
ORIGIN = "https://appassets.androidplatform.net"
NOW = 1800000000
GEN1 = "1446c590-a4d7-4f64-8013-3d8b31a748b1"
GEN2 = "277cf53d-2523-40cc-a20a-9925ec42120d"
GEN3 = "3f3cf1a1-ab50-4b15-8f22-bc8178f86262"


class MemoryStore:
    def __init__(self):
        self.items = {}
        self.calls = []

    def get(self, key):
        self.calls.append(("get", key))
        return copy.deepcopy(self.items.get(key))

    def put(self, item, previous, now):
        self.calls.append(("put", 0 if previous is None else previous["version"]))
        old = self.items.get(item["gardenId"])
        fields = ("generation", "version", "ownerHash", "expiresAt", "revoked")
        allowed = old is None if previous is None else (
            old is not None and all(old[key] == previous[key] for key in fields)
            and (old["expiresAt"] <= now) == (previous["expiresAt"] <= now))
        if not allowed:
            raise api.Conflict()
        self.items[item["gardenId"]] = copy.deepcopy(item)

def event(method="PUT", body=None, *, token=TOKEN, origin=ORIGIN, path=None, headers=None):
    result = {"version": "2.0", "rawPath": path or "/gardens/" + GARDEN,
              "rawQueryString": "", "headers": {"origin": origin,
              "authorization": "Bearer " + token, "content-type": "application/json"},
              "requestContext": {"http": {"method": method}}}
    if headers:
        result["headers"].update(headers)
    if body is not None:
        result["body"] = body if isinstance(body, str) else json.dumps(body)
    return result


def payload(version=0, completed=None, sessions=1, generation=GEN1):
    result = {"schemaVersion": 1, "expectedVersion": version,
              "progress": {"completed": ["wake"] if completed is None else completed, "sessions": sessions}}
    if version:
        result["expectedGeneration"] = generation
    return result


def etag(version=1, generation=GEN1):
    return '"' + generation + ':' + str(version) + '"'


class GardenBackupTests(TestCase):
    def setUp(self):
        self.store = MemoryStore()
        self.app = api.GardenBackup(self.store, api.allowed_origins([ORIGIN, "http://127.0.0.1:4173"]), lambda: NOW)
        generations = iter((GEN1, GEN2))
        self.app.generation_factory = lambda: next(generations)

    def call(self, request, status):
        response = self.app.handle(request)
        self.assertEqual(response["statusCode"], status, response)
        self.assertEqual(response["headers"]["cache-control"], "no-store")
        return json.loads(response["body"]) if response["body"] else None

    def create(self):
        return self.call(event(body=payload()), 201)

    def test_roundtrip_conditional_write_delete_and_no_secret_in_response(self):
        saved = self.create()
        self.assertEqual(saved, {"schemaVersion": 1, "generation": GEN1, "version": 1,
            "progress": {"completed": ["wake"], "sessions": 1},
            "updatedAt": "2027-01-15T08:00:00Z", "expiresAt": NOW + api.RETENTION_SECONDS})
        stored = self.store.items[GARDEN]
        self.assertEqual(stored["ownerHash"], hashlib.sha256(TOKEN.encode()).hexdigest())
        self.assertNotIn(TOKEN, json.dumps(stored))
        self.assertEqual(self.call(event("GET"), 200), saved)
        updated = self.call(event(body=payload(1, ["rain", "sun", "wake"], 2)), 200)
        self.assertEqual(updated["version"], 2)
        self.assertEqual(updated["progress"]["completed"], ["wake", "sun", "rain"])
        self.call(event("DELETE", headers={"if-match": etag(2)}), 204)
        self.assertTrue(self.store.items[GARDEN]["revoked"])
        self.assertNotIn("progress", self.store.items[GARDEN])

    def test_identical_create_and_update_retries_do_not_increment_version(self):
        saved = self.create()
        self.assertEqual(self.call(event(body=payload()), 200), saved)
        changed = self.call(event(body=payload(1, ["sun"], 7)), 200)
        self.assertEqual(self.call(event(body=payload(1, ["sun"], 7)), 200), changed)
        self.assertEqual(sum(call[0] == "put" for call in self.store.calls), 2)

    def test_stale_changed_write_and_delete_conflict(self):
        self.create()
        self.call(event(body=payload(0, ["sun"])), 409)
        self.call(event("DELETE", headers={"if-match": etag(2)}), 409)
        self.assertEqual(self.store.items[GARDEN]["progress"]["completed"], ["wake"])

    def test_unknown_and_other_owner_reads_writes_and_delete_are_not_found(self):
        self.call(event("GET"), 404)
        self.create()
        for request in (event("GET", token=OTHER), event(body=payload(), token=OTHER),
                        event("DELETE", token=OTHER, headers={"if-match": etag()})):
            self.assertEqual(self.call(request, 404), {"error": "not_found"})

    def test_expired_data_is_not_read_or_updated_before_background_ttl_deletion(self):
        self.create()
        self.store.items[GARDEN]["expiresAt"] = NOW
        self.call(event("GET"), 404)
        self.call(event(body=payload(1)), 404)
        self.call(event("DELETE", headers={"if-match": etag()}), 404)
        fresh = self.call(event(body=payload(0, ["rain"]), token=OTHER), 201)
        self.assertEqual(fresh["version"], 1)
        self.assertEqual(fresh["progress"]["completed"], ["rain"])

    def test_missing_malformed_and_noncanonical_capability_rejected_before_storage(self):
        for value in ("", "short", "x" * 44, TOKEN + ",other", TOKEN[:-1] + "B"):
            with self.subTest(token=value):
                self.call(event("GET", token=value), 401)
        self.assertEqual(self.store.calls, [])

    def test_disallowed_and_missing_origins_rejected_without_cors_or_storage(self):
        for value in ("https://evil.example", "null", "", ORIGIN + ".evil"):
            request = event("GET", origin=value)
            response = self.app.handle(request)
            self.assertEqual(response["statusCode"], 403)
            self.assertNotIn("access-control-allow-origin", response["headers"])
        self.assertEqual(self.store.calls, [])

    def test_preflight_no_capability_and_exact_origin_only(self):
        self.call(event("OPTIONS", token="", headers={"access-control-request-method": "PUT"}), 204)
        self.call(event("OPTIONS", headers={"access-control-request-method": "POST"}), 400)
        self.assertEqual(self.store.calls, [])

    def test_json_duplicate_keys_unknown_fields_and_wrong_types_rejected(self):
        cases = ["{", '{"schemaVersion":1,"schemaVersion":1,"expectedVersion":0,"progress":{"completed":[],"sessions":0}}',
                 payload() | {"frames": []}, payload() | {"schemaVersion": True}, payload() | {"expectedVersion": False},
                 payload() | {"expectedVersion": -1}, payload() | {"expectedVersion": api.MAX_VERSION},
                 payload(completed=["wake", "wake"]), payload(completed=["other"]), payload(completed=[0]),
                 payload(sessions=True), payload(sessions=-1), payload(sessions=1.5), payload(sessions=api.MAX_SAFE_INTEGER + 1),
                 payload() | {"progress": {"completed": [], "sessions": 0, "landmarks": []}}]
        for value in cases:
            with self.subTest(value=value):
                self.call(event(body=value), 400)
        self.assertEqual(self.store.calls, [])

    def test_nonfinite_numbers_and_nested_json_fail_closed(self):
        self.call(event(body='{"schemaVersion":1,"expectedVersion":0,"progress":{"completed":[],"sessions":NaN}}'), 400)
        self.call(event(body='[' * 1100), 400)

    def test_body_and_content_type_limits(self):
        self.call(event(body=" " * (api.MAX_BODY_BYTES + 1)), 400)
        self.call(event(body=payload(), headers={"content-type": "text/plain"}), 415)
        self.call(event("GET", body="{}"), 400)
        self.assertEqual(self.store.calls, [])

    def test_base64_payload_valid_and_invalid(self):
        request = event(body=base64.b64encode(json.dumps(payload()).encode()).decode())
        request["isBase64Encoded"] = True
        self.call(request, 201)
        bad = event(body="!!!!")
        bad["isBase64Encoded"] = True
        self.call(bad, 400)

    def test_delete_requires_quoted_current_version(self):
        self.create()
        for value in ("", "1", '"1"', etag(0), etag(-1), etag("01"), etag(9999999999), '*'):
            with self.subTest(value=value):
                self.call(event("DELETE", headers={"if-match": value}), 428)

    def test_unknown_paths_query_and_methods_do_not_touch_storage(self):
        for path in ("/gardens/../other", "/gardens/not-uuid", "/gardens/" + GARDEN.upper(), "/gardens/" + GARDEN + "/"):
            self.call(event("GET", path=path), 404)
        request = event("GET"); request["rawQueryString"] = "token=secret"
        self.call(request, 404)
        self.call(event("POST"), 405)
        self.assertEqual(self.store.calls, [])

    def test_invalid_gateway_event_or_duplicate_header_casing(self):
        self.call({"version": "1.0"}, 400)
        request = event("GET", headers={"Origin": ORIGIN})
        self.call(request, 400)

    def test_storage_failure_returns_stable_error_without_logging_request(self):
        with patch.object(self.store, "get", side_effect=RuntimeError("secret " + TOKEN)), patch("sys.stdout", new_callable=io.StringIO) as output:
            self.assertEqual(self.call(event("GET"), 503), {"error": "backup_unavailable"})
            self.assertEqual(output.getvalue(), "")

    def test_atomic_conflict_with_identical_winner_is_idempotent(self):
        def raced(item, previous, now):
            self.store.items[GARDEN] = copy.deepcopy(item)
            raise api.Conflict()
        with patch.object(self.store, "put", side_effect=raced):
            saved = self.call(event(body=payload()), 200)
        self.assertEqual(saved["version"], 1)

    def test_atomic_collision_with_other_owner_does_not_overwrite(self):
        def raced(item, previous, now):
            winner = copy.deepcopy(item); winner["ownerHash"] = hashlib.sha256(OTHER.encode()).hexdigest()
            self.store.items[GARDEN] = winner
            raise api.Conflict()
        with patch.object(self.store, "put", side_effect=raced):
            self.call(event(body=payload()), 404)
        self.assertEqual(self.store.items[GARDEN]["ownerHash"], hashlib.sha256(OTHER.encode()).hexdigest())

    def test_generation_required_only_for_updates(self):
        self.call(event(body=payload() | {"expectedGeneration": GEN1}), 400)
        self.create()
        for value in (None, "", "not-uuid", GEN1.upper()):
            self.call(event(body=payload(1) | {"expectedGeneration": value}), 400)
        missing = payload(1); del missing["expectedGeneration"]
        self.call(event(body=missing), 400)

    def test_same_owner_expiry_recreate_rejects_delayed_old_put_and_delete(self):
        first = self.create()
        self.store.items[GARDEN]["expiresAt"] = NOW
        second = self.call(event(body=payload(0, ["rain"], 2)), 201)
        self.assertEqual(second["version"], first["version"])
        self.assertNotEqual(second["generation"], first["generation"])
        before = copy.deepcopy(self.store.items[GARDEN])
        self.call(event(body=payload(1, ["sun"], generation=first["generation"])), 409)
        self.call(event("DELETE", headers={"if-match": etag(1, first["generation"])}), 409)
        self.assertEqual(self.store.items[GARDEN], before)

    def test_inflight_old_put_and_delete_cas_cannot_mutate_new_generation(self):
        for method in ("PUT", "DELETE"):
            with self.subTest(method=method):
                self.setUp(); self.create()
                winner = copy.deepcopy(self.store.items[GARDEN])
                winner.update(generation=GEN2, progress={"completed": ["rain"], "sessions": 9})
                original = self.store.put
                def raced(item, previous, now):
                    self.store.items[GARDEN] = copy.deepcopy(winner)
                    original(item, previous, now)
                request = event(body=payload(1, ["sun"])) if method == "PUT" else event("DELETE", headers={"if-match": etag()})
                with patch.object(self.store, "put", side_effect=raced):
                    self.call(request, 409)
                self.assertEqual(self.store.items[GARDEN], winner)

    def test_expired_recreate_cas_is_bound_to_exact_previous_incarnation(self):
        self.create(); self.store.items[GARDEN]["expiresAt"] = NOW - 1
        changed = copy.deepcopy(self.store.items[GARDEN]); changed["generation"] = GEN3
        original = self.store.put
        def raced(item, previous, now):
            self.store.items[GARDEN] = copy.deepcopy(changed)
            original(item, previous, now)
        with patch.object(self.store, "put", side_effect=raced):
            self.call(event(body=payload(0, ["rain"])), 404)
        self.assertEqual(self.store.items[GARDEN], changed)

    def test_progress_free_tombstone_blocks_delayed_creation_and_delete_retry_is_idempotent(self):
        self.create()
        self.call(event("DELETE", headers={"if-match": etag()}), 204)
        tombstone = copy.deepcopy(self.store.items[GARDEN])
        self.assertEqual(set(tombstone), {"gardenId", "ownerHash", "schemaVersion", "generation", "version", "revoked", "expiresAt"})
        self.call(event("GET"), 404)
        for version in (0, 1):
            self.assertEqual(self.call(event(body=payload(version)), 410), {"error": "backup_revoked"})
        self.app.clock = lambda: NOW + 60
        self.call(event("DELETE", headers={"if-match": etag()}), 204)
        self.assertEqual(self.store.items[GARDEN], tombstone)
        for request in (event("GET", token=OTHER), event(body=payload(), token=OTHER),
                        event("DELETE", token=OTHER, headers={"if-match": etag()})):
            self.call(request, 404)

    def test_tombstone_revocation_is_explicitly_bounded_by_retention(self):
        self.create(); self.call(event("DELETE", headers={"if-match": etag()}), 204)
        self.app.clock = lambda: NOW + api.RETENTION_SECONDS + 1
        recreated = self.call(event(body=payload(0, ["rain"], 2)), 201)
        self.assertEqual(recreated["generation"], GEN2)
        self.assertEqual(recreated["version"], 1)

    def test_request_hash_replay_never_bypasses_generation_check(self):
        self.create(); self.call(event(body=payload(1, ["sun"])), 200)
        self.store.items[GARDEN]["generation"] = GEN2
        before = copy.deepcopy(self.store.items[GARDEN])
        self.call(event(body=payload(1, ["sun"])), 409)
        self.assertEqual(self.store.items[GARDEN], before)

    def test_exact_origin_configuration_rejects_wildcards_paths_and_insecure_remote(self):
        for value in ("*", "https://*", "http://example.com", "https://x.test/", "https://u:p@x.test", "https://x.test?q=1", "https://x.test:bad", ""):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    api.allowed_origins([value])
        self.assertEqual(api.allowed_origins(["http://[::1]:4173"]), frozenset(["http://[::1]:4173"]))


class DynamoAdapterTests(TestCase):
    class Table:
        def __init__(self): self.calls = []
        def get_item(self, **kwargs):
            from decimal import Decimal
            self.calls.append(("get", kwargs))
            return {"Item": {"version": Decimal(2), "progress": {"sessions": Decimal(4), "completed": ["wake"]}}}
        def put_item(self, **kwargs): self.calls.append(("put", kwargs))

    def test_adapter_uses_consistent_reads_and_atomic_owner_version_expiry_conditions(self):
        table = self.Table(); store = api.DynamoStore(table)
        self.assertEqual(store.get(GARDEN)["progress"]["sessions"], 4)
        self.assertTrue(table.calls[0][1]["ConsistentRead"])
        store.put({"gardenId": GARDEN}, None, NOW)
        self.assertIn("attribute_not_exists", table.calls[-1][1]["ConditionExpression"])
        previous = {"generation": GEN1, "version": 2, "ownerHash": "owner", "expiresAt": NOW + 1, "revoked": False}
        store.put({"gardenId": GARDEN}, previous, NOW)
        for word in ("ownerHash", "#generation", "#version", "expiresAt", "revoked"):
            self.assertIn(word, table.calls[-1][1]["ConditionExpression"])
        self.assertEqual(table.calls[-1][1]["ExpressionAttributeValues"], {
            ":generation": GEN1, ":version": 2, ":owner": "owner", ":expiry": NOW + 1, ":revoked": False, ":now": NOW})

    def test_only_conditional_sdk_failure_is_translated(self):
        class ConditionalError(Exception):
            response = {"Error": {"Code": "ConditionalCheckFailedException"}}
        with self.assertRaises(api.Conflict):
            api.DynamoStore._conditional(lambda: (_ for _ in ()).throw(ConditionalError()))
        with self.assertRaises(RuntimeError):
            api.DynamoStore._conditional(lambda: (_ for _ in ()).throw(RuntimeError()))


if __name__ == "__main__":
    main()
