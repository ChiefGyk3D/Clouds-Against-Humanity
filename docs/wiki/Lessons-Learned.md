# Lessons learned

> Prerequisites: none strictly. The stories make more sense after [Spacelift](Spacelift.md) and [CI, tests and the cost gate](CI-Tests-and-Cost-Gate.md), which is where the core path puts this page.

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

Things that broke during the build (and a few traps the guides warn about), what was really going on, and what fixed it. These are the parts most tutorials leave out, and the parts most likely to save you an evening.

## 1. `curl | bash` reported success and installed nothing useful

**Symptom.** The first build installed the connector with Twingate's `setup.sh`, piped into bash. Both droplets came up with the `twingate-connector` package installed, no `/etc/twingate/connector.conf`, and a service that never started. The cloud-init log said the install succeeded.

**What was going on.** Two separate problems:

- A script piped into `bash` is read as it arrives. Anything in it that reads standard input (apt's package configuration can) may consume the rest of the script, so later lines silently never run. This is the leading explanation, not a proven one.
- The pipeline's exit status was that of the last command, which exited 0, so "succeeded" was logged regardless.

**Fix.** Stop piping installers into a shell. Cloud-init now writes the config file itself, adds Twingate's apt repository after checking its signing key against a pinned fingerprint, installs the package, enables the service, and counts an attempt as successful only if `systemctl is-active` says so. It runs under `bash -o pipefail` and retries 10 times, 30 seconds apart.

**Lesson.** "The command exited 0" and "the thing works" are different claims. Check the end state, not the exit code.

## 2. Connector-to-connector SSH timed out, twice

**Symptom.** SSH through Twingate to connector a's own address worked. SSH to connector b's address timed out during the banner exchange, intermittently.

**What was going on.** Twingate can route a session for b's address through connector a. Connector a then opens TCP 22 to b inside the VPC, and DigitalOcean firewalls filter VPC-internal traffic too. With zero inbound rules, b dropped it.

**First fix (incomplete).** Add an inbound rule on the connector firewall: TCP 22 from the connector tag. Still timed out.

**Why.** DigitalOcean firewalls are stateful for replies, but a *new* outbound connection needs an outbound rule. The connector firewall allowed outbound 443, 80, 53, the relay range and UDP, but not TCP 22, so connector a could not even send the SYN.

**Real fix.** A matching outbound rule: TCP 22 to the connector tag. Both rules name the tag, never an address.

**Lesson.** When a cloud firewall filters east-west traffic, think about both ends of every connection: the sender needs permission to send, the receiver needs permission to accept. And read the vendor's guidance on redundancy: Twingate says every connector in a remote network needs identical reach to every resource ([connector best practices](https://www.twingate.com/docs/connector-best-practices)).

## 3. The SSH key that already existed

**Symptom.** Apply failed with a 422 "SSH Key is already in use".

**What was going on.** The stack tried to register the admin public key, but the same key was already on the DigitalOcean account, and the API refuses duplicates.

**Fix.** Look the key up by name with a `data` source instead of creating it. The stack never owns the key, so destroying the stack leaves it in place.

**Lesson.** Not everything in your infrastructure should be created by the code that uses it. Shared, long-lived things are better referenced than owned.

## 4. A hand-made Twingate site collides with the code

**The trap.** The stack now creates the Twingate remote network itself. If a site with the same name was made by hand earlier, the apply fails or leaves a duplicate.

**Fix.** Delete or rename the hand-made `access-<region>` site before the apply. The bootstrap steps now say so.

**Lesson.** When you move something from clicks to code, remove the clicked version first, or you get two of them.

## 5. First boot races Ubuntu for the dpkg lock

**Symptom.** Intermittent package install failures on first boot.

**What was going on.** Ubuntu's own `apt-daily` and `unattended-upgrades` timers start on first boot too, and hold the dpkg lock.

**Fix.** `DPkg::Lock::Timeout "300";` in an apt config drop-in, so apt waits up to five minutes for the lock instead of failing.

## 6. Doppler names are uppercase, OpenTofu variables are not

**The trap.** A variable exported under the wrong case is not an error; OpenTofu just never sees it. OpenTofu reads a variable `foo` only from the exact environment variable `TF_VAR_foo`. Doppler only allows uppercase names, so `TF_VAR_FOO` would never match.

**Fix.** The hook accepts `TF_VAR_foo=FOO`: fetch `FOO` from Doppler, export it as `TF_VAR_foo`.

## 7. The plan said "no OIDC"

**Symptom.** The plan was for Spacelift to authenticate to Doppler with a short-lived OIDC token, so no long-lived secret would sit in Spacelift.

**What was going on.** The run identity token is not issued on this Spacelift plan. Checked directly with a task run: the variable simply was not there.

**Fix (compromise).** A read-only Doppler service token, one config, 90-day expiry, write-only in the Spacelift context. Documented as a known limit, with the one-line change needed if OIDC becomes available.

**Lesson.** Verify a platform feature exists on *your* plan before designing around it, and write the fallback down as a fallback, not as the design.

## 8. "Masked in logs" needs to be proven, not assumed

Spacelift documents `::add-mask` for redacting values, but not whether the mask command line itself is hidden. So the first tracked run comes with a check: search the log for the Doppler token prefix and confirm it never appears. Trust, then verify, then write down that you verified.

## 9. A rebuilt account: nothing you assumed is still true

The DigitalOcean account was rebuilt and everything was redeployed. Four things that worked the first time did not, and each one was only visible on the real API.

**Token scopes are proven by a run, not by a table.** The first plan failed with `403 You are not authorized to perform this operation` while reading SSH keys. The documented scope list said `ssh_key: read`, but the new token had been made without it, and DigitalOcean tokens cannot be edited after creation, only replaced. Read the error, not the symptom: it said 403 (a scope), not "key not found".

**The cheap droplet size is not offered everywhere.** `422 Size is not available in this region`. The plain `s-1vcpu-1gb` ($6) was missing from nyc3 on the new account. Ask the API before you design around a size: `GET /v2/sizes` lists the regions each size is offered in, and `GET /v2/regions` lists the sizes each region offers. On this account the newer US sites (Atlanta, Richmond, Kansas City, Memphis) started at about $18 for 1 GB, so the answer was Toronto at $6, not a closer region.

**A default VPC cannot be deleted, and VPC ranges cannot overlap anywhere in the account.** Changing the region replaces the VPC, which fails with `403 Can not delete default VPCs` because the first VPC in a region becomes its default. The plan had shown `default = true`; that field is the warning. The fix was `tofu state rm` for that VPC (forget it, do not delete it) and a new range, because creating the Toronto VPC at the same range failed with `422 This range/size overlaps with another VPC network in your account`, even across regions. The orphaned VPC is empty and free.

**A stack dependency starts its own run.** When foundation finished, Spacelift started a run on the access stack by itself. Triggering another one by hand queued a duplicate behind it. Check the stack's runs before you trigger.

**Lesson.** On a new account, plan for the first apply to find the account's real limits, and make each failure cheap: keep stages small, have nothing billing until the last stage.

## 10. A red check from a run that could never pass

**Symptom.** A pull request that changed only the wiki and the README got a red `spacelift/cah-10-access` check. Every GitHub Actions job was green, including the `CI green` gate that branch protection requires, so the pull request could still merge. It just looked broken.

**What was going on.** Spacelift started a proposed run for the pull request and posted its result back to GitHub. In this repository a proposed run gets no credentials by design (the secrets hook skips it), so its plan fails at the provider every time. The run was not testing anything; it could only fail. Earlier pull requests had no such check, so something on the Spacelift side changed which pull requests it proposed runs for. That part was not visible from the repository.

**Fix.** A Spacelift push policy, `.spacelift/policies/push.rego`, that never proposes a run and starts a tracked run only when a merge to `main` changes the stack, a shared module, the secrets hook or the Spacelift configuration. Pull requests are covered by `tofu test` with mocked providers in GitHub Actions, which needs no credential. The policy has its own tests, and the job that runs them went into git-your-ship-together's `tofu-ci.yml` rather than into this repository, alongside the `tofu test` loop this repository used to carry by hand. Spacelift reads policies from its own store, not from the repository, so the policy takes effect only once it is created there (runbook section 9).

**Then a second surprise.** The Policies menu was not where the guide said, and Spacelift's documentation explained why: push policies are a paid feature. On the free plan, the control that is left is each stack's project root and project globs, which Spacelift's built-in behavior already uses to decide what a change touches. Narrowing those stops docs-only pull requests from reaching a stack; it cannot stop a pull request that changes a stack from getting a proposed run.

**Lessons.**

- A check that can only fail is worse than no check. People learn to ignore red, and the next red that matters gets ignored too. If a check cannot pass by design, stop it from running rather than explaining it every time.
- Check that a feature exists on your plan before building on it. This is lesson 7 again, about OIDC, learned a second time.
- Prove the mitigation, not just the policy. The tests include a docs-only pull request (must start nothing) and a merge that arrives with its pull request attached (must still deploy), because getting the second one wrong would have silently stopped every deployment.
- When a fix is a job every similar repository would need, put it in the shared library first. A copy in one repository is a copy that drifts.

Next: [Roadmap](Roadmap.md), step 21 of the core path on the [Reading order](Reading-Order.md) page.
