# spaces-bucket

A private, versioned DigitalOcean Spaces bucket for the daemons' state. DigitalOcean only: this module is not part of
the provider module contract ([design section 5](../../docs/superpowers/specs/2026-10-16-multicloud-design.md)),
and it has not been applied anywhere.

| What | Setting |
|---|---|
| Access | `acl = "private"`; no bucket policy, no CORS rule |
| Versioning | on |
| Lifecycle | noncurrent versions expire after `noncurrent_version_days` (default 90); unfinished multipart uploads abort after `abort_incomplete_upload_days` (default 7); current versions never expire |
| Deletion | `force_destroy = false`: a bucket that still holds objects or versions cannot be destroyed by a plan |
| Keys | none created here; see [the operator guide](../../docs/stages/03-state-bucket.md) |

Name: `<layer>-<resource_key, or region>-<purpose>`, for example `state-tor1-state`. A different name is a different bucket.

Outputs: `name`, `region`, `urn`, `endpoint` (`https://<region>.digitaloceanspaces.com`, for `STATE_S3_ENDPOINT`).

## Provider extensions

None. Not a contract role.
