<!-- SPDX-License-Identifier: Apache-2.0 -->
# Stage 3: the state bucket (code only, never applied)

Design: [2026-10-11 stage 3 workloads](../superpowers/specs/2026-10-11-stage-3-workloads-design.md), section 3b (object storage) and section 7 (backups). Issue 113.

> **Status: unbuilt and unapproved.** Nothing on this page has been applied, planned against a real account, or tested against a real bucket. Stage 3 is a `planned` phase in `approved.json`; the current phase is still `stage-1`. The restore commands below are marked **untested** on purpose.

## 1. What exists in the repository

| Piece | Where | What it does |
|---|---|---|
| Module | `modules/spaces-bucket` | One `digitalocean_spaces_bucket`: `acl = "private"`, versioning on, `force_destroy = false`, a lifecycle rule that expires **noncurrent** versions after 90 days (default), and a rule that aborts unfinished uploads after 7 days. No bucket policy, no CORS rule, no access key. |
| Stack | `stacks/30-state` | The module call, behind `state_bucket_enabled`. **The flag defaults to false, so a plan creates nothing.** |
| Tests | `modules/spaces-bucket/tests`, `stacks/30-state/tests`, `tests/test_golden_state_bucket.py` | Mocked-provider `tofu test` runs (flag off creates nothing; flag on creates exactly one private, versioned bucket; a bad region is rejected) and a golden-address and shape test. |
| Spacelift entry | `.spacelift/config.yml`, stanza `cah-30-state` | Names the Doppler secrets the stack would request. The Spacelift stack itself does not exist yet. |

The bucket has its own stack, not the `30-workloads` stack the design draft sketches, so the workload droplet can be destroyed and rebuilt without a plan ever touching the versioned state. That is a change from the draft; the maintainer can fold it back into a workloads stack later (the module does not care).

The bucket name is `cah-<resource_key, or region>-state`, for example `cah-tor1-state`. Bucket names are unique per region across all of Spaces, so a taken name needs a `resource_key`. The key is immutable: a different name is a different, empty bucket.

## 2. Cost, and what the cost gate cannot do yet

The design prices the bucket at $5 flat a month (250 GiB stored and 1 TiB out, read 2026-10-11, see [cost](../cost.md#stage-3-estimate-not-approved)). Neither that figure nor the cost gate has changed in this work: `stacks/30-state/cost.json` lists no resources, so it adds $0 to the gate's total, which is true while the flag is off.

**The gate cannot see the bucket, and it fails closed because of it.** `python -I scripts/cost_check.py` stops on `modules/spaces-bucket/main.tf: digitalocean_spaces_bucket (the gate has no price model for it)`. What is missing, exactly:

1. `digitalocean_spaces_bucket` is neither in `FREE_TYPES` nor in `COSTED_TYPES` in `scripts/cost_check.py`.
2. `resource_cost` has no `spaces` manifest kind (it prices droplets only), and `docs/cost-prices.json` has no `spaces` price.
3. `docs/stages/approved.json` has no `allowed_sources` entry placing the type in `modules/spaces-bucket/main.tf`. Adding it, and raising the DigitalOcean `approved_monthly_total` from $12 to $17 for a manifest that lists the bucket, is the approval of stage 3 spend, so it is the maintainer's edit and was not made.
4. The gate has no rule for a flag. Its connector rule matches module blocks to manifest entries one for one and refuses `count`; the bucket is behind `count = var.state_bucket_enabled ? 1 : 0` on the module call. A rule is needed that says what a `count` of zero or one means for the manifest (the design's wording is a flat `spaces` entry; it does not say whether a switched-off bucket is priced at $0 or $5).
5. Tests for all of the above in `tests/test_cost_check*.py`, including the hostile cases.

Until that is done, the cost gate (and every test that runs it on the real repository) is red on this branch. Whether to model the bucket and approve the spend first, or to hold this code until then, is the maintainer's call.

## 3. Decisions that stay the maintainer's

- **Spaces ($5, inside the cost gate, one account) or a free-tier bucket at a second provider (B2 or R2, $0, a second account and a second set of keys, outside this repository).** The design recommends Spaces; the choice is not made here. The module is DigitalOcean-only and is useless if the answer is a second provider.
- **Approving stage 3** and its ceiling. Not done.
- **Keys in state or keys in Doppler.** This code takes the second option (the design's lean): no `digitalocean_spaces_key` anywhere. A test fails if one appears.

## 4. Access keys (documented, none created)

Keys are made by hand in the DigitalOcean control panel (Spaces, Access Keys) and stored in Doppler. They are never created by OpenTofu, never printed, and never in a variable, a tfvars file or state.

| Key | Used by | Doppler names | Scope |
|---|---|---|---|
| Stack key | the `cah-30-state` Spacelift run, so the provider can create and read the bucket | `SPACES_ACCESS_KEY_ID`, `SPACES_SECRET_ACCESS_KEY` (read by the DigitalOcean provider from the environment; `.spacelift/config.yml` requests them with `DIGITALOCEAN_TOKEN`) | Needs bucket management, so it is a broad key. Keep it out of the daemons. |
| One key per daemon | one daemon's `STATE_S3_*` settings | A name per daemon in that daemon's own Doppler config, chosen when the daemon is wired up | Read and write on the state bucket |

**UNVERIFIED, check before relying on it:** the design says each daemon's key reaches "its prefix only". As far as I know DigitalOcean's limited-access Spaces keys are scoped per bucket (read, read and write, or full access), not per prefix. I did not confirm this against DigitalOcean's current documentation. If it is per bucket, a daemon key can read and overwrite another daemon's state, and the choices are one bucket per daemon (more cost lines and more gate work) or accepting a shared bucket for five small daemons. This is a threat-model question for the maintainer.

**UNVERIFIED:** whether Token A (the API token in [Spacelift and Doppler](../spacelift-secrets.md#4a-digitalocean-token-scopes)) needs any scope for Spaces. Bucket calls go through the Spaces key, not the API token.

Rotation and expiry of the Spaces keys are not set anywhere yet (`docs/settings.json` marks them planned and the expiry UNVERIFIED).

## 5. Turning it on (not now)

Only after the maintainer approves stage 3 and the cost gate prices the bucket (section 2):

1. Create the Spacelift stack `cah-30-state` locked, with the `cah` label, root `stacks/30-state`, autodeploy off, as in [stage 2](02-telemetry.md) step 2. Put the stack key in Doppler first.
2. Set `state_bucket_enabled = true` (a `TF_VAR_state_bucket_enabled` stack variable) and, only if the name is taken, a `resource_key`.
3. Read the tracked plan. Expect exactly one create: `module.state_bucket[0].digitalocean_spaces_bucket.this`. Anything else is a stop.
4. Confirm. Then check the **untested** list in section 6.

Turning the flag off again plans a destroy. With `force_destroy = false` the destroy fails while the bucket holds any object or version, which is the intent; emptying a versioned bucket is a manual act and deletes the backups.

## 6. Restore procedure (all commands UNTESTED)

Written from the S3 API and the AWS CLI's documented options. **No command below has been run against a real bucket**, and DigitalOcean's coverage of each S3 call (`ListObjectVersions`, `CopyObject` with a version id, `DeleteObject` with a version id) is not confirmed. Run the dry steps first and read the output before any write. Use a key with the least access that works (a daemon's key can do all of this on its own prefix).

Setup (the keys come from Doppler at run time; nothing is typed or printed):

```sh
BUCKET=<bucket name>                     # for example cah-tor1-state
ENDPOINT=https://<region>.digitaloceanspaces.com   # the bucket module's endpoint output
# Credentials: AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY from Doppler, e.g.
#   doppler run -p <project> -c <config> -- <the commands below>
```

**6.1 List the versions of one object or one prefix** (read only):

```sh
aws s3api list-object-versions --endpoint-url "$ENDPOINT" --bucket "$BUCKET" \
  --prefix "<daemon>/youtube_state.json" \
  --query '{Versions: Versions[].[Key,VersionId,LastModified,IsLatest,Size], Markers: DeleteMarkers[].[Key,VersionId,LastModified,IsLatest]}'
```

A key with a delete marker that `IsLatest` has been deleted; its older versions are still there until the 90-day rule expires them.

**6.2 Restore one object to an earlier version.** Pick the `VersionId` from 6.1, then copy it over the current key. The copy becomes a new current version, so the bad version stays in history until it expires:

```sh
aws s3api copy-object --endpoint-url "$ENDPOINT" --bucket "$BUCKET" \
  --key "<daemon>/youtube_state.json" \
  --copy-source "$BUCKET/<daemon>/youtube_state.json?versionId=<VersionId>"
aws s3api head-object --endpoint-url "$ENDPOINT" --bucket "$BUCKET" --key "<daemon>/youtube_state.json"   # check size and time
```

**6.3 Undo a delete.** Remove the delete marker (its own `VersionId` from 6.1); the newest real version becomes current again:

```sh
aws s3api delete-object --endpoint-url "$ENDPOINT" --bucket "$BUCKET" \
  --key "<daemon>/youtube_state.json" --version-id <delete marker VersionId>
```

**6.4 Restore a whole prefix to how it was at a time.** For each key under the prefix, take the newest version at or before the chosen time, skip keys whose newest version at that time is a delete marker, and copy that version over the current key. Print the plan first and read it; only then run it:

```sh
PREFIX="<daemon>/"
AT="2026-01-01T00:00:00Z"   # the moment you want to go back to, UTC
aws s3api list-object-versions --endpoint-url "$ENDPOINT" --bucket "$BUCKET" --prefix "$PREFIX" --output json |
  jq -r --arg at "$AT" '
    [ (.Versions // [])[] | {Key, VersionId, LastModified, kind: "version"} ] +
    [ (.DeleteMarkers // [])[] | {Key, VersionId, LastModified, kind: "marker"} ]
    | map(select(.LastModified <= $at))
    | group_by(.Key) | map(max_by(.LastModified))
    | map(select(.kind == "version"))
    | .[] | "\(.Key)\t\(.VersionId)"' > "$SCRATCH/restore-plan.tsv"
cat "$SCRATCH/restore-plan.tsv"        # read it; stop here if it is not what you expect
while IFS="$(printf '\t')" read -r key vid; do
  aws s3api copy-object --endpoint-url "$ENDPOINT" --bucket "$BUCKET" --key "$key" \
    --copy-source "$BUCKET/$key?versionId=$vid" >/dev/null && echo "restored $key"
done < "$SCRATCH/restore-plan.tsv"
```

Known gaps in 6.4: it does not delete keys that were **created** after `AT` (they stay); it compares timestamps as strings, which is correct only while both are ISO 8601 UTC with the same precision; list-object-versions returns at most 1000 entries per call, and the command does not page, so a prefix with more than that needs `--max-items` and pagination added. Keys with a tab or newline in their name break the plan file. The daemons' state names do not have them.

**6.5 After any restore**, start the affected daemon and watch one cycle. If a state file went back past a post, a duplicate post is the expected cost (design section 7: a burst of duplicates for one cycle).

**6.6 A restore test is owed.** Before any daemon relies on the bucket: write a throwaway object under a `restore-test/` prefix, overwrite it, delete it, and run 6.1 to 6.4 on it. Record the result here, and correct whatever this section got wrong.

## 7. What this layer does not protect against

Versioning is layer 2 of the design's backup table. It does not protect against loss of the DigitalOcean account, a stolen token that deletes versions on purpose (anyone with a full-access Spaces key can delete a specific version), or a region failure. That is layer 3, a copy off the account, which does not exist yet.

## 8. Checks run for this change

`tofu fmt -check`, `tofu init -backend=false`, `tofu validate` and `tofu test` for `modules/spaces-bucket` and `stacks/30-state` with a mocked provider, and the Python tests. Nothing was planned or applied against a real account.
