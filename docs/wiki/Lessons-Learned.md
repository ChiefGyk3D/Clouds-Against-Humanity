# Lessons learned

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
