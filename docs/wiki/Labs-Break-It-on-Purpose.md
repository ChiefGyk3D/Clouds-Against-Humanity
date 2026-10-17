# Labs: break it on purpose

> Needs no cloud account and costs nothing. You need Git, a clone of the repository, an internet connection (OpenTofu downloads provider plugins when you initialise, and lab 4 downloads a tool), OpenTofu 1.8 or newer for the first two labs, `curl` and `sha256sum` for lab 4, Python 3.12 or newer with `pytest` installed for the last, and about 15 minutes per lab. Read [What is infrastructure as code](What-Is-Infrastructure-as-Code.md) first if `tofu test` is new to you.

Reading that a control exists is not the same as knowing it works. The way to find out is to break the thing it protects and watch the control object. Each lab here removes or weakens one safety property of this project, on your own computer, and asks you to **predict which check will notice** before you run anything.

That prediction is the lesson. If you were right, you understood the design. If you were wrong, the gap between your prediction and the output is exactly the thing you did not know, which is the most useful thing to find out while it costs nothing.

## Ground rules

- **Work on a throwaway branch.** `git switch -c lab` before you start. Every lab ends with `git restore <file>` so nothing you break survives.
- **Write your prediction down first**, on paper or in a comment. It is easy to convince yourself afterwards that you knew.
- **These checks run in CI on every pull request.** The point of each lab is to see the check that would have stopped a bad change from being merged.
- The outputs shown were captured from real runs on the repository as of 2026-10-16. Yours may differ in wording or timing, but the shape should match.

## Lab 1: open the firewall

**What it teaches:** a "no inbound" claim is only a claim until a test would fail if it stopped being true.

**Setup.** From the repository root:

```bash
cd modules/firewall
tofu init -backend=false
tofu test
```

You should see `Success! 12 passed, 0 failed.` That is your baseline.

**Predict.** Open `main.tf`. Above the `dynamic "inbound_rule"` block, add one inbound rule for SSH from the whole internet:

```hcl
inbound_rule {
  protocol         = "tcp"
  port_range       = "22"
  source_addresses = ["0.0.0.0/0", "::/0"]
}
```

Before you run the tests: which test will fail, which assertion in it, and will the other eleven tests still run?

**Run it** (`tofu test`) and compare.

**What really happens.** The first test does fail, but not where most people expect:

```text
  run "denies_all_inbound"... fail
│ Error: Invalid function argument
│   on outputs.tf line 28, in output "inbound_rules":
│   28:     "${r.protocol}/${r.port_range}/${join(",", sort(tolist(r.source_tags)))}"
│     │ r.source_tags is null
Failure! 0 passed, 1 failed, 11 skipped.
```

The tests never reached the assertion that says "zero inbound rules". The module's own output code assumes every inbound rule names a source tag, and an address-based rule breaks it. Eleven tests are skipped, because a failing test stops the rest of the file. So the control did stop you, by accident of how the output is written, and the message points at the wrong thing.

**Now make it fail the way the author intended.** Replace the rule with one that *does* use a tag:

```hcl
inbound_rule {
  protocol    = "tcp"
  port_range  = "22"
  source_tags = [var.tag]
}
```

Run again. This time:

```text
│ Error: Test assertion failed
│   13:     condition     = length(digitalocean_firewall.this.inbound_rule) == 0
│     │ digitalocean_firewall.this.inbound_rule is set of object with 1 element
│ The baseline firewall must have zero inbound rules.
│ ...
│   17:     condition     = output.inbound_rule_count == 0
│     │ output.inbound_rule_count is 1
```

Two independent assertions catch it, and the message is the one the author wrote on purpose.

**What to take away.**

- A test can fail for the wrong reason and still protect you. Read the error, do not just look for red.
- The tag-based rule is allowed by the design (`inbound_from_tag_rules`, for connector-to-connector SSH) but only through the variable. Write down why a rule added directly in the resource is different from one that arrives through a variable with a validation.
- **Stretch:** in `tests/firewall.tftest.hcl`, find the test that proves an unknown protocol is rejected. What input would you give to make the variable's own validation fire?

**Restore:** `git restore main.tf`.

## Lab 2: let a private network be public

**What it teaches:** validation at the edge. A bad value rejected when it is given is cheaper than one discovered after it is deployed.

**Setup.** `cd modules/vpc && tofu init -backend=false && tofu test`. The baseline passes.

**Predict.** `variables.tf` limits `ip_range` to private address space with a regular expression. The test `rejects_public_range` gives it `8.8.8.0/24` and expects a failure. If you delete the regular-expression half of the validation condition, what do you expect `tofu test` to say, and which test reports it?

**Do it.** In `variables.tf`, change the `condition` so it keeps only `can(cidrnetmask(var.ip_range))` and drops the `&& can(regex(...))` part.

**What really happens.**

```text
  run "name_follows_layer_region_role"... pass
  run "rejects_public_range"... fail
│ Error: Missing expected failure
│   26:   expect_failures = [var.ip_range]
│ The checkable object, var.ip_range, was expected to report an error but did
│ not.
  run "rejects_malformed_range"... skip
Failure! 1 passed, 1 failed, 1 skipped.
```

Notice the wording. Nothing failed in the module; a test that *expects* a failure didn't get one. That is the shape of a test for a guard: it succeeds when the bad thing is refused.

**What to take away.**

- `rejects_malformed_range` was skipped, not passed. It would still have been fine, but the run stopped before it. When a test run shows `skip`, read it as "not checked", never as "fine".
- The guard exists because a VPC range that overlaps a network you connect to is expensive to fix later (see [the demo-values table](Fork-Private-Stacks-and-the-Pipeline.md#step-2-which-values-are-demo-values)). A stronger guard would also reject ranges that overlap your own networks. Why can the module not do that by itself?

**Restore:** `git restore variables.tf`.

## Lab 3: sneak in something that costs money

**What it teaches:** a cost gate that fails closed. Anything it does not recognise is refused.

**Setup.** From the repository root, `python -I scripts/cost_check.py --root .` should print `cost-check: digitalocean: planned $12.00/mo, approved $12.00, active` followed by `cost-check: shared ceiling $30.00` and exit 0.

**Predict.** Append this to `stacks/10-access/main.tf`:

```hcl
resource "digitalocean_loadbalancer" "lab" {
  name   = "lab"
  region = var.region
}
```

A load balancer is a billable resource. The gate has no price for it. Will the gate pass because the planned total did not change, or fail? What would the message say?

**Run it** and compare.

**What really happens.**

```text
cost-check: resource type not on the free list, not approved, or outside its allowed file: stacks/10-access/main.tf: digitalocean_loadbalancer (the gate has no price model for it)
cost-check: digitalocean: planned $12.00/mo, approved $12.00, active
cost-check: shared ceiling $30.00
exit 1
```

(The summary lines and the failure line are written to different output streams, so the failure line may appear above or below them on your terminal.)

The total is still `$12.00`, because the gate has no price for the load balancer, yet it fails. That is the point: the gate does not subtract what it does not understand from the bill. An unknown resource type is a failure, not a zero.

**Part 2: the two numbers.** Restore the file. In `stacks/10-access/main.tf` copy the `connector_b` module block and rename the copy `connector_c`. Run the gate. Predict the message, then read it. Then add a third entry to `stacks/10-access/cost.json` and run again. The two runs fail for *different* reasons, and neither one is "the ceiling". Which rule did each trip? Open `scripts/cost_check.py` only after you have an answer.

**What to take away.**

- A fail-closed allow-list is a design choice: it makes adding a new resource type a deliberate act (a pull request that edits the allow-list, which someone reads) instead of a silent one.
- The gate only knows *fixed* prices. It cannot see data transfer or anything created outside the repository. Read [How money works in the cloud](How-Money-Works-in-the-Cloud.md) with that in mind.

**Restore:** `git restore stacks/10-access/main.tf stacks/10-access/cost.json`.

## Lab 4: let a pull request start a run

**What it teaches:** policy as code, and why the absence of a rule can be the rule.

**Setup.** This lab needs the Open Policy Agent (OPA) command line. CI pins version 1.21.0. On Linux x86-64:

```bash
curl -fsSL -o opa https://github.com/open-policy-agent/opa/releases/download/v1.21.0/opa_linux_amd64_static
curl -fsSL -o opa.sha256 https://github.com/open-policy-agent/opa/releases/download/v1.21.0/opa_linux_amd64_static.sha256
sha256sum opa            # compare with the hash in opa.sha256 before you run it
chmod +x opa
./opa test .spacelift/policies
```

Comparing the checksum before running a downloaded program is the habit from [Git, GitHub and pull requests](Git-GitHub-and-Pull-Requests.md#github-actions-and-the-supply-chain-problem), applied by hand. You should see `PASS: 16/16`.

**Predict.** `push.rego` deliberately has no `propose` rule: it never starts a run for a pull request. Add one to the end of the file:

```rego
propose if {
	input.pull_request
}
```

How many of the 16 tests do you expect to fail, and which behaviours do they describe?

**Run it** with `./opa test .spacelift/policies -v` and compare.

**What really happens.** Three tests fail:

```text
test_pull_request_touching_the_stack_is_not_proposed: FAIL
test_docs_only_pull_request_starts_nothing: FAIL
test_push_to_another_branch_starts_nothing: FAIL
```

The third is the interesting one. You added a rule about pull requests and a test about *another branch* failed. Read the `event` helper at the top of `push_test.rego`: every test input carries `"pull_request": null`. In Rego an expression is only false when it is `false` or undefined, and `null` is neither, so `input.pull_request` is satisfied even when there is no pull request. Your rule fires for every event. A natural-looking rule has a quiet bug, and only the tests said so. (The policy's header explains a related trap: why it never tests `input.pull_request` to decide anything.)

**What to take away.**

- The tests state the policy in plain language. If a future change makes one fail, the name of the test says what behaviour was lost.
- The policy's own header explains why leaving `propose` out is the protection: with it, a pull request's code would run in Spacelift beside the secrets context. Read [Push policies: paid plan versus free plan](Spacelift.md#push-policies-paid-plan-versus-free-plan) and the runbook's section 9 for what happens on a plan without push policies, and whether this lab's protection even applies to you.

**Restore:** `git restore .spacelift/policies/push.rego`.

## Lab 5: let the secrets hook run on the wrong branch

**What it teaches:** a security control tested from the outside, with fake secrets.

**Setup.** From the repository root, in a Python 3.12+ environment with `pytest` installed:

```bash
python -I -m pytest tests/test_doppler_env.py -q
```

You should see `31 passed`. The tests run the hook against a sandbox with a fake Doppler, so no real secret is involved.

**Predict.** `scripts/spacelift/doppler-env.sh` loads secrets only on a tracked or destroy run **from `main`**. The check is a single `if [ "$_branch" != "main" ]` near line 89. If you change it to `if false; then`, so the branch is never checked, which test names will fail, and what does the failing assertion show?

**Run it** and compare.

**What really happens.** Three parametrized cases of `test_non_main_branch_gets_nothing` fail (branch `feature/x`, branch `mainline`, and an empty branch name), and the assertion shows the sandbox's fake token being handed to a branch that should get nothing:

```text
assert 'TOKEN=unset' in '...loaded DIGITALOCEAN_TOKEN as DIGITALOCEAN_TOKEN\nrc=0\nTOKEN=dp_test_SECRET_VALUE_123\n'
```

The cases include `mainline`, a name that *starts with* `main`, which is exactly what a sloppy prefix check would wrongly accept.

**What to take away.**

- A security control needs a test whose job is to fail when the control disappears. Without one, nobody notices a refactor that quietly removes it.
- The honest limit, written in the runbook: this check is a script that arrives with the code. Anyone who can change the branch the stack tracks can change the script. It stops mistakes. Who can push remains the real boundary.

**Restore:** `git restore scripts/spacelift/doppler-env.sh`.

## After the labs

- Run `git status`. It should be clean. If it is not, restore what is listed.
- Pick the lab where your prediction was most wrong. Write one sentence on what you misunderstood. That sentence is worth more than the passing tests.
- Take any control in the [Threat model](Threat-Model.md) and design a lab like these for it: what would you break, which check should object, and what would you predict? If you cannot name the check, you have found a gap. Open an issue.

Next: [Build it: from zero accounts to stage 1](Build-It-From-Zero-Accounts-to-Stage-1.md), step 3 of the build track. If you came for security rather than a build, the security track starts at the [Threat model exercise](Threat-Model-Exercise.md).
