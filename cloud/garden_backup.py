"""Optional garden-summary backup API. No frames, pose data, or AWS calls on import.

The pure application accepts an injected store for local tests. The Lambda entry
point creates its DynamoDB adapter lazily; invalid requests do not read/write it. This is
an undeployed component; HTTP origin checks supplement, never replace, the
per-garden random capability.
"""
from dataclasses import dataclass
import base64
import binascii
import datetime
import hashlib
import hmac
import json
import os
import re
import time
import uuid
from urllib.parse import urlsplit

SCHEMA_VERSION = 1
MAX_BODY_BYTES = 2048
MAX_SAFE_INTEGER = 9007199254740991
MAX_VERSION = 2147483647
RETENTION_SECONDS = 30 * 24 * 60 * 60
GARDEN_PATH = re.compile(r"^/gardens/([0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12})$")
GENERATION = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
CAPABILITY = re.compile(r"^[A-Za-z0-9_-]{43}$")
MOMENTS = ("wake", "sun", "rain")


class Conflict(Exception):
    """An atomic storage condition did not hold."""


class InvalidRequest(Exception):
    pass


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise InvalidRequest("duplicate_json_key")
        result[key] = value
    return result


def _safe_int(value, maximum):
    return type(value) is int and 0 <= value <= maximum


def _progress(value):
    if type(value) is not dict or set(value) != {"completed", "sessions"}:
        raise InvalidRequest("invalid_progress")
    completed = value["completed"]
    if (type(completed) is not list or len(completed) > 3
            or any(type(item) is not str or item not in MOMENTS for item in completed)
            or len(set(completed)) != len(completed)
            or not _safe_int(value["sessions"], MAX_SAFE_INTEGER)):
        raise InvalidRequest("invalid_progress")
    return {"completed": [item for item in MOMENTS if item in completed],
            "sessions": value["sessions"]}


def _body(event):
    value = event.get("body")
    if type(value) is not str:
        raise InvalidRequest("invalid_body")
    try:
        raw = value.encode("utf-8")
        if len(raw) > MAX_BODY_BYTES * 2:
            raise InvalidRequest("body_too_large")
        if event.get("isBase64Encoded") is True:
            raw = base64.b64decode(raw, validate=True)
        elif event.get("isBase64Encoded") not in (None, False):
            raise InvalidRequest("invalid_encoding")
        if len(raw) > MAX_BODY_BYTES:
            raise InvalidRequest("body_too_large")
        result = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object,
                            parse_constant=lambda _: (_ for _ in ()).throw(InvalidRequest("invalid_number")))
    except (UnicodeError, ValueError, binascii.Error, RecursionError) as error:
        raise InvalidRequest("invalid_json") from error
    if type(result) is not dict or not {"schemaVersion", "expectedVersion", "progress"}.issubset(result):
        raise InvalidRequest("invalid_body")
    if (type(result["schemaVersion"]) is not int or result["schemaVersion"] != SCHEMA_VERSION
            or not _safe_int(result["expectedVersion"], MAX_VERSION - 1)):
        raise InvalidRequest("invalid_version")
    expected = result["expectedVersion"]
    fields = {"schemaVersion", "expectedVersion", "progress"}
    if expected:
        fields.add("expectedGeneration")
    if set(result) != fields:
        raise InvalidRequest("invalid_body")
    generation = result.get("expectedGeneration")
    if expected and (type(generation) is not str or not GENERATION.fullmatch(generation)):
        raise InvalidRequest("invalid_generation")
    return expected, generation, _progress(result["progress"])


def _origin(value):
    if (type(value) is not str or len(value) > 256 or "*" in value or "\\" in value
            or any(char.isspace() or ord(char) < 32 for char in value)):
        raise ValueError("invalid allowed origin")
    parsed = urlsplit(value)
    if (parsed.scheme not in ("https", "http") or not parsed.hostname
            or parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment
            or parsed.netloc != parsed.netloc.lower()
            or (parsed.scheme == "http" and parsed.hostname not in ("127.0.0.1", "localhost", "::1"))):
        raise ValueError("allowed origins must be exact HTTPS origins or local HTTP origins")
    # Reject malformed ports; urlsplit defers validation until this attribute.
    _ = parsed.port
    return value


def allowed_origins(raw):
    values = raw.split(",") if type(raw) is str else raw
    if not isinstance(values, (list, tuple, set, frozenset)) or not 1 <= len(values) <= 8:
        raise ValueError("one to eight exact allowed origins required")
    return frozenset(_origin(value) for value in values)


def _response(status, value=None, origin=None):
    headers = {"content-type": "application/json", "cache-control": "no-store",
               "x-content-type-options": "nosniff", "vary": "Origin"}
    if origin is not None:
        headers.update({"access-control-allow-origin": origin,
                        "access-control-allow-methods": "GET, PUT, DELETE, OPTIONS",
                        "access-control-allow-headers": "authorization, content-type, if-match",
                        "access-control-max-age": "300"})
    return {"statusCode": status, "headers": headers,
            "body": "" if value is None else json.dumps(value, separators=(",", ":")),
            "isBase64Encoded": False}


def _public(item):
    return {key: item[key] for key in ("schemaVersion", "generation", "version", "progress", "updatedAt", "expiresAt")}


def _owned(item, owner_hash, now):
    return (item is not None and item["expiresAt"] > now
            and hmac.compare_digest(item["ownerHash"], owner_hash))


@dataclass
class GardenBackup:
    store: object
    origins: frozenset
    clock: object = time.time
    generation_factory: object = uuid.uuid4

    def handle(self, event):
        """Handle API Gateway HTTP API payload 2.0 without logging request data."""
        origin = None
        try:
            if type(event) is not dict or event.get("version") != "2.0":
                return _response(400, {"error": "invalid_request"})
            incoming = event.get("headers")
            if type(incoming) is not dict or any(type(k) is not str or type(v) is not str for k, v in incoming.items()):
                return _response(400, {"error": "invalid_headers"})
            headers = {key.lower(): value for key, value in incoming.items()}
            if len(headers) != len(incoming):
                return _response(400, {"error": "invalid_headers"})
            if headers.get("origin") not in self.origins:
                return _response(403, {"error": "origin_not_allowed"})
            origin = headers["origin"]
            context = event.get("requestContext", {}).get("http", {})
            method, path = context.get("method"), event.get("rawPath")
            match = GARDEN_PATH.fullmatch(path) if type(path) is str else None
            if match is None or event.get("rawQueryString", "") != "":
                return _response(404, {"error": "not_found"}, origin)
            if method == "OPTIONS":
                if headers.get("access-control-request-method") not in ("GET", "PUT", "DELETE"):
                    return _response(400, {"error": "invalid_preflight"}, origin)
                return _response(204, origin=origin)
            if method not in ("GET", "PUT", "DELETE"):
                return _response(405, {"error": "method_not_allowed"}, origin)
            auth = headers.get("authorization", "")
            token = auth[7:] if auth.startswith("Bearer ") else ""
            if not CAPABILITY.fullmatch(token):
                return _response(401, {"error": "capability_required"}, origin)
            # Canonical encoding ensures 32 random bytes, not arbitrary short input.
            if base64.urlsafe_b64encode(base64.urlsafe_b64decode(token + "=")).decode().rstrip("=") != token:
                return _response(401, {"error": "capability_required"}, origin)
            owner_hash = hashlib.sha256(token.encode()).hexdigest()
            garden_id, now = match.group(1), int(self.clock())
            if method == "PUT":
                content_type = headers.get("content-type", "").lower().replace(" ", "")
                if content_type not in ("application/json", "application/json;charset=utf-8"):
                    return _response(415, {"error": "json_required"}, origin)
                expected, generation, progress = _body(event)
                fingerprint = hashlib.sha256(json.dumps([expected, generation, progress], sort_keys=True, separators=(",", ":")).encode()).hexdigest()
                current = self.store.get(garden_id)
                active = current is not None and current["expiresAt"] > now
                if active and not _owned(current, owner_hash, now):
                    return _response(404, {"error": "not_found"}, origin)
                if active and current["revoked"]:
                    return _response(410, {"error": "backup_revoked"}, origin)
                if active and expected and generation != current["generation"]:
                    return _response(409, {"error": "version_conflict"}, origin)
                if active and current["requestHash"] == fingerprint:
                    return _response(200, _public(current), origin)
                if (active and expected != current["version"]) or (not active and expected != 0):
                    return _response(409 if active else 404, {"error": "version_conflict" if active else "not_found"}, origin)
                item = {"gardenId": garden_id, "ownerHash": owner_hash, "schemaVersion": 1, "revoked": False,
                        "generation": current["generation"] if active else str(self.generation_factory()),
                        "version": expected + 1, "progress": progress, "requestHash": fingerprint,
                        "updatedAt": datetime.datetime.fromtimestamp(now, datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
                        "expiresAt": now + RETENTION_SECONDS}
                try:
                    self.store.put(item, current, now)
                except Conflict:
                    # A concurrent identical retry may have won the conditional write.
                    latest = self.store.get(garden_id)
                    if not _owned(latest, owner_hash, now):
                        return _response(404, {"error": "not_found"}, origin)
                    if latest["revoked"]:
                        return _response(410, {"error": "backup_revoked"}, origin)
                    if latest["requestHash"] == fingerprint and (generation is None or generation == latest["generation"]):
                        return _response(200, _public(latest), origin)
                    return _response(409, {"error": "version_conflict"}, origin)
                return _response(201 if not active else 200, _public(item), origin)
            if event.get("body") not in (None, ""):
                return _response(400, {"error": "body_not_allowed"}, origin)
            current = self.store.get(garden_id)
            if not _owned(current, owner_hash, now):
                return _response(404, {"error": "not_found"}, origin)
            if method == "GET":
                if current["revoked"]:
                    return _response(404, {"error": "not_found"}, origin)
                return _response(200, _public(current), origin)
            tag = re.fullmatch(r'"([0-9a-f-]{36}):([1-9][0-9]{0,9})"', headers.get("if-match", ""))
            if not tag or not GENERATION.fullmatch(tag[1]) or int(tag[2]) > MAX_VERSION:
                return _response(428, {"error": "version_required"}, origin)
            if tag[1] != current["generation"] or int(tag[2]) != current["version"]:
                return _response(409, {"error": "version_conflict"}, origin)
            if current["revoked"]:
                return _response(204, origin=origin)
            tombstone = {key: current[key] for key in ("gardenId", "ownerHash", "schemaVersion", "generation", "version")}
            tombstone.update(revoked=True, expiresAt=now + RETENTION_SECONDS)
            try:
                self.store.put(tombstone, current, now)
            except Conflict:
                return _response(409, {"error": "version_conflict"}, origin)
            return _response(204, origin=origin)
        except InvalidRequest as error:
            return _response(400, {"error": str(error)}, origin)
        except Exception:
            # Do not serialize SDK exceptions, request bodies, IDs or capabilities.
            return _response(503, {"error": "backup_unavailable"}, origin)


class DynamoStore:
    def __init__(self, table):
        self.table = table

    def get(self, garden_id):
        from decimal import Decimal
        def normal(value):
            if isinstance(value, Decimal):
                return int(value)
            if isinstance(value, dict):
                return {key: normal(item) for key, item in value.items()}
            if isinstance(value, list):
                return [normal(item) for item in value]
            return value
        response = self.table.get_item(Key={"gardenId": garden_id}, ConsistentRead=True)
        return normal(response.get("Item"))

    def put(self, item, previous, now):
        if previous is None:
            kwargs = {"Item": item, "ConditionExpression": "attribute_not_exists(gardenId)"}
        else:
            # Bind the exact old incarnation even for an expired-row replacement.
            # A delayed PUT/DELETE must never mutate a newer generation at version 1.
            condition = ("#generation = :generation AND #version = :version AND ownerHash = :owner "
                         "AND expiresAt = :expiry AND revoked = :revoked AND expiresAt "
                         + ("<= :now" if previous["expiresAt"] <= now else "> :now"))
            kwargs = {"Item": item, "ConditionExpression": condition,
                      "ExpressionAttributeNames": {"#generation": "generation", "#version": "version"},
                      "ExpressionAttributeValues": {":generation": previous["generation"], ":version": previous["version"],
                          ":owner": previous["ownerHash"], ":expiry": previous["expiresAt"],
                          ":revoked": previous["revoked"], ":now": now}}
        self._conditional(self.table.put_item, **kwargs)

    @staticmethod
    def _conditional(operation, **kwargs):
        try:
            operation(**kwargs)
        except Exception as error:
            if getattr(error, "response", {}).get("Error", {}).get("Code") == "ConditionalCheckFailedException":
                raise Conflict() from None
            raise


_application = None


def lambda_handler(event, context):
    """AWS entry point; not used by local tests and never invoked on import."""
    global _application
    if _application is None:
        try:
            origins = allowed_origins(os.environ.get("ALLOWED_ORIGINS", ""))
            table_name = os.environ["GARDEN_TABLE"]
            import boto3  # Included by the selected AWS Lambda runtime; no local dependency.
            from botocore.config import Config
            client_config = Config(connect_timeout=1, read_timeout=1, retries={"total_max_attempts": 1})
            _application = GardenBackup(DynamoStore(boto3.resource("dynamodb", config=client_config).Table(table_name)), origins)
        except Exception:
            return _response(503, {"error": "backup_unavailable"})
    return _application.handle(event)
