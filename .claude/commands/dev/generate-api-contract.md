---
description: Generate OpenAPI 3.0 contract for an AssetCore API module
---

Generate the **OpenAPI 3.0 contract** for: `$ARGUMENTS`

**Output:**

**1. OpenAPI YAML** — complete paths, parameters, request bodies, response schemas using `$ref` components.

**2. Frappe Envelope Note** — all whitelist responses wrapped as `{ "message": <actual_response> }`.

**3. Authentication** — `Cookie: sid=<session>` or `Authorization: token <api_key>:<api_secret>`

**4. Error Code Table**

| Code | HTTP | Meaning |
| --- | --- | --- |
| NOT_FOUND | 404 | Record does not exist |
| FORBIDDEN | 403 | Insufficient role |
| VALIDATION_ERROR | 422 | Business rule violation |
| INVALID_STATE | 409 | Wrong workflow state |
| INVALID_DATA | 400 | Malformed request body |

**5. curl Examples** — one per endpoint with real field names.

**Output file:** `docs/api/<module>_openapi.yaml`
