# Optional garden backup — local implementation, undeployed

This component backs up an explicitly confirmed garden summary. Pose inference
and movement feedback stay local. Its payload contains only the three possible
completed moment IDs and a bounded session count. It accepts no image, video,
landmark, medical or account data. Backup does not certify that movement occurred.

The browser client is opt-in and disabled without a configured endpoint. The
current Android host's network policy and release permissions are unchanged;
native TV cloud backup is not enabled by this work.

The proposed AWS path is API Gateway HTTP API → Python Lambda → DynamoDB. This
is meaningful product state storage/restore, not an inference offload. The code
and local tests do not satisfy the competition's requirement to **run** a
meaningful component on AWS: no stack has been deployed or invoked.

## API contract

`GET`, `PUT` and `DELETE /gardens/{gardenId}` use a lowercase UUIDv4 identifier
and `Authorization: Bearer <capability>`. The browser generates 32 random bytes
and encodes them as canonical unpadded base64url (43 characters). The backend
stores only the token's SHA-256 digest. There is no credential in the URL, code
or function environment. Losing this application capability means losing access
to that backup; it does not affect local play.

PUT accepts exactly this JSON shape, at most 2,048 UTF-8 bytes:

```json
{
  "schemaVersion": 1,
  "expectedVersion": 0,
  "progress": {"completed": ["wake", "sun"], "sessions": 1}
}
```

`expectedVersion: 0` conditionally creates a new/expired record. Later writes
must additionally include `expectedGeneration` with the server-issued UUID from
the response, and match the current version. Initial creation must omit that
field. A new incarnation always gets a new generation even if its UUID,
capability and version number happen to be reused. A delayed request from an
old incarnation cannot update or delete a new one.

The last identical PUT retry returns its existing generation, version and result
without another write. A changed stale write returns 409; the service never
silently overwrites newer progress. Successful PUT returns 200 or 201, GET
returns 200, and DELETE requires `If-Match: "generation:version"` and returns 204.
The success body is:

```json
{
  "schemaVersion": 1,
  "generation": "1446c590-a4d7-4f64-8013-3d8b31a748b1",
  "version": 1,
  "progress": {"completed": ["wake", "sun"], "sessions": 1},
  "updatedAt": "2026-10-21T20:00:00Z",
  "expiresAt": 1795291200
}
```

The example is illustrative, not an actual AWS result. The response never
includes the owner digest or capability. Missing, expired and differently owned
records return the same 404. Invalid capabilities return 401. Unknown fields,
duplicate JSON keys, nonfinite numbers, duplicate/unknown IDs and invalid counts
are rejected before storage. Backend errors return a generic 503 without
request content or SDK exception details.

Only exact configured origins are accepted; no wildcard or remote plain HTTP.
Local HTTP origins are allowed for development. API Gateway CORS and the handler
use the same allowlist. Origin checks are not authentication: ownership is the
random capability, and nonbrowser callers can forge an Origin header.

Backups expire 30 days after the last new successful write. Idempotent retries
and reads do not extend expiry. The handler refuses expired records immediately,
even while DynamoDB's asynchronous TTL deletion is pending. DELETE requires the
same owner capability, generation and current version. It immediately removes
the progress and replaces it with a small revocation tombstone. That tombstone
contains only the ID, capability digest, generation/version and expiry metadata;
it blocks delayed PUTs, including old creation requests, for 30 days. Its GET
result is 404. An owned PUT returns 410 `backup_revoked`; a matching repeated
DELETE returns 204 without extending retention. Other owners still receive 404.

Revocation is bounded: after tombstone retention expires and metadata is purged,
the server cannot distinguish a very old creation request from a new one. The
client must retire that identity and generate a fresh ID/capability after delete
or known expiry. This is not a permanent revocation ledger. Atomic storage checks
bind the exact prior generation, version, owner, expiry and revocation flag even
when replacing an expired row.

Stack deletion would delete its table
and logs; it must never be aimed at an unrelated/shared stack.

## Local checks and proposed infrastructure

No AWS credentials, CLI, emulator, camera or server are needed:

```sh
python3 -B -m unittest discover -s cloud/tests -v
python3 -B cloud/build_template.py --output /tmp/sway-garden-proposed-stack.json
```

The output path must be new; the builder refuses to overwrite files. It uses
only the standard library, injects the exact handler into Lambda `Code.ZipFile`,
sets `index.lambda_handler`, and records the source SHA-256. No S3 bucket or
packaging upload is needed. The resource base is not a standalone deployable
template until built. Tests inspect the generated template; no CloudFormation
service validation or real DynamoDB operation has happened.

Proposed settings: Python 3.13/ARM64, 128 MiB, 3-second Lambda timeout, reserved
concurrency 2; HTTP API throttle 1 request/second with burst 2; DynamoDB on-demand
maximum 5 read and 5 write request units/second; TTL; seven-day function logs.
The table uses DynamoDB's default AWS-owned-key encryption. No custom KMS key,
VPC, NAT, EC2, layer, model, media storage, stream or index is proposed.

The future role is limited to GetItem/PutItem on this one table and
log-stream writes to its pre-created function log group. API invocation is scoped
to the one API/account/garden route. Application code does not log requests,
bodies, garden IDs or capabilities; API request/access logging is not enabled.

Lambda provides Boto3 in the selected runtime. Local tests inject a memory store
and do not import or use it. The runtime's SDK can change; a future deployment
must record the exact runtime/SDK version and rerun adapter integration tests.
These sources do not claim a newly pinned SDK or a verified cloud build.

## Approval still required

Before any AWS action, obtain explicit approval for the account/region, the
concrete resources and IAM role, approved browser origins, test data, duration,
cleanup, and a proposed **24-hour pilot budget of up to US$1 total**, followed
by teardown. Continuing service would need separate **US$5/month** approval or
another owner-chosen amount. These are proposals, not existing spending
authority or hard billing limits. Current pricing and the workload estimate belong in the deployment
review; no free-tier or zero-cost assumption is made here.

Public conditional creation is anonymous, protected only by validation and
throttles. A nonbrowser caller can create its own capabilities and consume
requests. Throttling, reserved concurrency and DynamoDB throughput limits reduce
rate but do not impose a total spend cap or total record quota. A budget alert
does not instantly stop charges. Before exposing a live demo, agree monitoring
and a shutdown/stack-deletion plan and decide whether an additional creation
quota is necessary. No live API address exists in the committed client.

## Official references checked

- [HTTP API payload format 2.0](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-develop-integrations-lambda.html)
- [Exact-origin HTTP API CORS](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-cors.html)
- [Lambda runtimes](https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtimes.html)
- [Inline Python and runtime-included Boto3](https://docs.aws.amazon.com/lambda/latest/dg/python-package.html)
- [DynamoDB on-demand maximum throughput](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-properties-dynamodb-table-ondemandthroughput.html)
- [DynamoDB default encryption](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-properties-dynamodb-table-ssespecification.html)
- [TTL deletion timing](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/TTL.html)
- [HTTP API throttle properties](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-properties-apigatewayv2-stage-routesettings.html)
