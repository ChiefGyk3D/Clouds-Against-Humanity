# Backups deep dive: 3-2-1-1-0, immutable copies, key custody and restore testing

Side page to the start-from-zero pages. Read it after [Backups, recovery and patching](Backups-Recovery-and-Patching.md), which teaches snapshot versus backup, RPO and RTO, the plain 3-2-1 rule and a first timed restore, and after [The CIA triad](The-CIA-Triad-Confidentiality-Integrity-Availability.md), because availability is the property all of this protects. This page does not repeat them. It takes up what they leave open: the two extra digits of 3-2-1-1-0, what an immutable copy really protects against, who holds the key to an encrypted backup, backing up the backup system itself, how often to test a restore, how long to keep copies, the ransomware angle, the traps in cloud backups, and what this project would have to back up. Next: the lesson on business continuity and disaster recovery, which covers how the work carries on and how the systems come back; it is named here in plain text, and this page does not depend on it.

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

> **Status: unverified draft. One local script was run; everything else was read, not run.** On **2026-10-31** I ran the Bash script in the free path on a Debian-based Linux machine (GNU bash 5.2.37, GNU coreutils 9.7, GNU tar 1.35, OpenSSL 3.5.7, as an ordinary user) and pasted its output. **Not run:** the script on macOS or Windows, any PowerShell version (none is given), every cloud command shown or named (`aws s3api`, `rclone`, `doppler`, `terraform state pull`, `git clone --mirror`), the restore of anything real in this project, and every control in the project table (I read the files; I applied no stack and called no provider). The standards and vendor pages were downloaded and read on **2026-10-31** and sit in the [claims register](#claims-register) with their URLs and the date each page shows. A time interval or a test frequency that is my own suggestion is marked **est.**; the standards I read do not set one.

> **Prerequisites.** [Backups, recovery and patching](Backups-Recovery-and-Patching.md) first, then [Hashing, encryption and keys](Hashing-Encryption-and-Keys.md) for what a key is and [The terminal and your first script](Terminal-and-Your-First-Script.md) for running a script. The free path needs a Linux machine or WSL 2 with `bash`, GNU `tar`, `sha256sum`, `openssl` and `dd` (stock macOS lacks the GNU forms, so it is not written for macOS). No cloud account, no network, no installs. About 90 minutes with the exercise (est.).

> **Where this runs.** Everything in the free path happens in one folder the script creates with `mktemp -d` and deletes at the end. It reads nothing else on your machine, opens no connection, and the "key" it makes is a random string written inside that folder and deleted with it. Nothing here attacks anything: the ransomware part is in words, and the one deliberate "damage" is a few bytes written into a copy the script itself made.

## What you will be able to do

- Say what each digit of 3-2-1-1-0 asks for, who added the last two, and what the rule still does not cover.
- Tell a full, an incremental and a differential backup apart, and say what each one costs you at restore time.
- Say what an immutable copy stops, and name four things it does not stop.
- Explain why an encrypted backup has a second thing to lose, and say where the key should and should not live.
- List what a backup system needs backed up besides the data.
- Write a restore-test schedule with timings you measured, and compare the total with your RTO.
- Set a retention period against a realistic time to notice an intruder, and say how a legal hold changes it.
- Read this project's table of things to back up and find the rows that say **None**.
- Run a free restore drill: a full and an incremental backup, an encrypted copy opened with and without its key, a damaged copy caught by a checksum, and a retention period that is too short.

## What the wiki already says (and the gap)

| Idea | Where it is today | The gap this page fills |
|---|---|---|
| Snapshot, backup, replica, archive; RPO and RTO; the plain 3-2-1 rule; a first timed restore | [Backups, recovery and patching](Backups-Recovery-and-Patching.md) | What 3-2-1 leaves open once ransomware, key loss and a provider account are in the picture. |
| Retention schedules, legal holds, S3 Object Lock in one paragraph | [Cross-tenant data flows, governance, retention and DLP](Cross-Tenant-Data-Governance-Retention-and-DLP.md) | Retention as a backup question: how long is long enough, and what a lock does and does not buy. |
| Why availability matters, and the key-versus-availability trade-off | [The CIA triad](The-CIA-Triad-Confidentiality-Integrity-Availability.md) | The key-custody half in depth. |
| State, locking, and a lost-state exercise | [Plans, state, drift and recovery](Plans-State-Drift-and-Recovery.md) | Where this project's state would have to be copied from, and what exists today. |
| What a key is and how it is lost | [Hashing, encryption and keys](Hashing-Encryption-and-Keys.md) | What losing the key to a backup costs, and how to hold it. |

## From 3-2-1 to 3-2-1-1-0

The plain rule is on the [Backups page](Backups-Recovery-and-Patching.md#the-3-2-1-rule-and-what-it-leaves-open): three copies, two media, one offsite. Who first said it is less clear than people write. The CISA paper that page cites is undated. Veeam's explainer says the rule originated "in the early 2000s" and Backblaze's says it was "first introduced in the late aughts" (both read 2026-10-31), and the name usually given for it is the photographer Peter Krogh. I could not find a page I could read that says so, so treat that attribution as **est.**

The two extra digits have a clear owner. Veeam, a backup software vendor, wrote in its article *What is the 3-2-1 Backup Rule?* (by Julia Furst Morgado; published February 5, 2024, updated July 3, 2026; read 2026-10-31): "At Veeam, we extended the rule to 3-2-1-1-0. It adds one immutable copy, and results in zero recovery errors." Its FAQ spells the last digit out as "a requirement for zero backup errors through automated integrity checks and regular restore testing." Read it as a vendor's rule: it is sensible, and the author sells software that checks it.

| Digit | Asks for | What it protects against | What it still leaves open |
|---|---|---|---|
| **3** | Three copies of the data (the original and two more) | One copy lost or damaged | Three copies that one mistake can reach are one copy |
| **2** | Two kinds of media or storage | One kind of failure taking all copies | Two clouds in one provider account are still one account |
| **1** | One copy offsite | A fire, a flood, a stolen laptop | An offsite copy the same login can delete |
| **1** (the first extra) | One copy that is immutable or offline | An attacker or a mistake that deletes or overwrites every copy it can reach | A copy made from data that was already bad; a copy anyone can read |
| **0** | Zero errors when you verify and restore | A copy that was never readable | A test that is not run often enough, or checks less than a real restore needs |

Two things the rule does not say at all. It never says **how old** the newest good copy is, which is the RPO. And it never says **who holds the key** to an encrypted copy, or **who can find the backups at 3 a.m.** The sections below take those up.

## Backup types: full, incremental, differential

NIST's contingency planning guide (SP 800-34 Rev. 1, May 2010, which describes tape and disk media and is old, but whose definitions have not changed) names "three common methods for performing system backups". In its words, paraphrased:

- **Full.** Captures all the files you selected. Locating a file is simple because everything is in one set. The backup can take long, and keeping many full copies of files that rarely change wastes storage.
- **Incremental.** Captures files created or changed since the last backup of any type. It is quick and small. To restore, "media from different backup operations may be required": the last full and every incremental after it, in order.
- **Differential.** Captures files created or changed since the last **full** backup. Each differential grows until the next full. Restoring needs only the full and the last differential, so fewer pieces than an incremental chain, and each backup is slower than an incremental one.

The trade is **backup time and space against restore complexity**. A chain of fifty incrementals is cheap to write and fifty chances for one missing link to spoil the restore. The drill below makes this concrete: restoring the incremental alone gives two files, not all of them.

### Snapshot versus backup, once more

The Backups page already says a snapshot is a point-in-time image that is often kept next to the original. The short reason a snapshot on the same disk is not a backup: **it shares the disk's fate.** If the disk dies, the volume is deleted, or the account is closed, the snapshot goes with it. Veeam's own list of ways to reach 3-2-1 includes "storage snapshots" with the note "caution on separate media from production". A snapshot is a fast way to make a restore point (DigitalOcean's automated backups are built by taking one and copying it off the disk, as the Backups page shows). It becomes part of a backup plan only when a copy lives somewhere the original's failure does not reach.

## Immutable and offline copies

**Immutable** means a stored copy cannot be changed or deleted until a date, by anyone with credentials, the owner included. The usual name is WORM, write once read many. **Offline** or **air-gapped** means the copy is not reachable from the machine being attacked: a drive in a drawer, a tape on a shelf, a vault with no standing network path.

The cloud version is concrete enough to read. Amazon S3 Object Lock "uses a write-once-read-many (WORM) model" and has two retention modes (AWS S3 user guide, read 2026-10-31):

- **Compliance mode.** "A protected object version can't be overwritten or deleted by any user, including the root user in your AWS account," its retention mode can't be changed and its period can't be shortened. The page adds that the only way to delete such an object early "is to delete the associated AWS account."
- **Governance mode.** Most users cannot overwrite or delete, but users who hold a special permission and send a bypass header can. It is useful for testing a retention setting before committing to compliance mode.

### What immutability protects against, and what it does not

| Event | Does a locked copy survive? | Why |
|---|---|---|
| An attacker with your admin credentials tries to delete every backup | **Yes, until the retention date** | The lock does not care whose credentials asked (compliance mode, per the AWS page). |
| The attacker closes or deletes the whole cloud account | **Not reliably** | The same page says deleting the account is the one way out of compliance mode. Immutability lives inside an account, so the account is still one failure domain. |
| The data was already encrypted or corrupted when it was copied | **No** | The lock preserves exactly what was written. A locked bad copy is a bad copy you cannot remove. |
| Someone copies the data out and threatens to publish it | **No** | Immutability is not secrecy. Encryption and access rules are, and a locked copy is still readable by anyone allowed to read it. |
| The retention period ends | **No** | After it, the version "can be overwritten or deleted". |
| A new version of the same name is written | The old one is kept; the new one is covered only if its own lock or a bucket default applies | A lock protects one version; per the AWS page, "retention periods and legal holds don't prevent new versions of the object from being created, or delete markers to be added on top of the object." |
| You set a long period in compliance mode by mistake | **Yes, and you cannot undo it** | The period cannot be shortened. CISA warns that immutable storage "does not meet compliance criteria for certain regulations and misconfiguration can impose significant cost." |

Notice that **versioning is not immutability.** DigitalOcean's Spaces versioning page (read 2026-10-31) says versioning "allows you to restore a previous version of an object if a user or application overwrites or deletes it", and a few paragraphs later walks through "Permanently Delete a Specific Version" using the same Spaces API key you use to manage the bucket. Anyone holding that key can delete the old versions too. I found no mention of Object Lock or any write-once feature on DigitalOcean's Spaces features and limits pages (read 2026-10-31); an absence on two pages is not proof, so check before relying on either way. This project's bucket module turns on versioning and expires old versions after 90 days by default (`modules/spaces-bucket/main.tf`, `modules/spaces-bucket/variables.tf`), which is a good first layer and not an immutable one.

A cheap offline copy is a drive that is **unplugged** except while it is being written. It protects only while unplugged, and it makes the restore slower by however long it takes to fetch it. That is a trade, not a flaw: write it down next to the RTO.

On Linux a root user can set the immutable attribute on a file with `chattr +i`, which stops even the file's owner from changing it until root clears it (general knowledge, **est.**; not run for this page). It protects against an attacker who is not root and against accidents. It does not protect against root, which is who ransomware wants to be.

## Encryption and key custody

An unencrypted backup is a second copy of everything an attacker wants. So backups are usually encrypted, and CISA's guide says to "maintain offline, encrypted backups". The cost is the one the CIA page named: an encrypted backup has **two things to keep**, the data and the key, and losing the key loses the data.

restic, a free backup program, says it plainly (restic 0.19.1 documentation, read 2026-10-31): "Knowledge of your password is required to access the repository. Losing your password means that your data is irrecoverably lost." The same page notes a repository "can hold multiple keys that can all be used to access the repository", which is the mechanism for giving two people a way in.

NIST's guide says the same thing about tape in 2010: "A solid key management process must be established so encrypted data is available as needed", and keys "should be stored separate from, but accessible to, the primary encrypted backup data." Two rules in one sentence: **separate** (not on the machine or in the folder whose loss you are planning for) and **accessible** (reachable on the worst day, by someone who is awake).

| Where the key lives | What goes wrong |
|---|---|
| Next to the backup, on the same disk | Anyone who takes the backup takes the key. The encryption bought nothing. |
| Only on the server being backed up | The server dies and takes the key with it. The backup is noise. |
| Only in the head or password manager of one person | That person is unreachable, has left, or lost the manager. A key with one holder is a single point of failure. |
| In the secret store the whole system depends on | If the secret store is the thing that failed, you need the key to restore the secret store. A circle. |
| Two holders, in two places (for example a password manager and a sealed paper copy somewhere else), tested | Survives most single losses. It costs a little effort, and you have to check it still opens a real backup. |

**The test that matters:** restore from an encrypted copy onto an empty machine, using only what you wrote down as the recovery kit. If you had to use something that is not in the kit, the kit is incomplete. The drill below does the first half on a small scale: it opens the encrypted copy with the right key and fails to open it with another.

## Backing up the backup system itself

A backup is made by software, on a schedule, with credentials, onto storage. Each of those is a thing that can be lost, and the recovery depends on them:

- **The configuration:** what is backed up, where, how often, how long it is kept.
- **The catalog or index** some tools keep. Without it you may be able to read the data but not find what you need in it.
- **The repository password or key**, covered above.
- **The credentials** the job uses to reach the storage (see [the ransomware angle](#the-ransomware-angle): they should add copies, not delete them).
- **The scripts and the schedule** that run it. CISA says to "use infrastructure as code (IaC) to deploy and update cloud resources and keep backups of template files offline".
- **The written steps to restore,** kept somewhere that does not need the lost system to open. CISA also says to "ensure a hard copy of the plan and an offline version is available" for the incident response plan, and the same logic holds for a restore runbook.
- **The software to read it.** NIST warns that when offsite data is encrypted, "media readers" must be available at the alternate site. For a modern tool this means keeping the tool's installer or a known-good version, not only the data it wrote.

If a third party runs your backups, CISA says to "ensure they are following the applicable best practices" and to put the requirements in the contract.

## Restore testing

The "0" in 3-2-1-1-0 is the one that costs effort. NIST's contingency guide lists "Test backup information to verify media reliability and information integrity" as a control for moderate- and high-impact systems and not required for low-impact ones, and says the planner should use the organization's resilience policy and business impact analysis "to assist in determining how often backup media should be tested". So the standard I read gives you the question, not an interval. Mine is a suggestion (**est.**):

| Test | What it proves | How often (est.) |
|---|---|---|
| A checksum of the stored copy against the one recorded when it was written | The bytes did not rot or get touched | Every backup, automatically |
| A restore of a small sample into a fresh place, compared with a manifest | The archive opens and the sample is right | Monthly |
| A full restore on an empty machine, with only the recovery kit, timed from the moment you start | The whole path works and fits the RTO | Once a year, and after any change to the tool, the storage or the key |
| An alert when any of these fails or does not run | You find out | Always on |

Time each step, not just the copy. The Backups page already said the copy is only one part; the rest is noticing, deciding, finding the backup, reaching the key and credentials, starting the service and checking it. Make a table and fill it in at the drill:

| Step | Who | Minutes |
|---|---|---|
| Notice and decide to restore | | |
| Find the right copy | | |
| Get the key and credentials | | |
| Copy the data back | | |
| Start the service | | |
| Check it against a record made earlier | | |
| **Total, to compare with the RTO** | | |

The only row a script can fill in for you is "copy the data back" and "check", as in the drill. Every other row is a person. A restore test that finds the key is missing, the runbook is out of date or the copy is nine months old has done its job.

## Retention and legal holds

**Retention** is how long you keep copies. Two pressures pull it in opposite directions.

- **Long enough to survive a slow discovery.** An intruder who has been inside for three weeks has been copied into every backup of those three weeks. If you keep only the last three copies, none is clean. The drill shows this with five days and a keep-three rule. A realistic retention is longer than the time you would take to notice, and the time to notice is an estimate you should be honest about (**est.**; I did not read a dwell-time figure for this page).
- **Short enough to honor deletion.** Data you promised to delete, or must delete, still sits in old backups until they expire. That is a reason for a retention limit, not only for a minimum. The [cross-tenant lesson](Cross-Tenant-Data-Governance-Retention-and-DLP.md#retention-and-purge) covers the schedule side.

The Backups page already notes that DigitalOcean keeps weekly backups for four weeks and snapshots until deleted. A weekly plan kept four weeks gives you at best the last four weekly states, so it protects against a problem you find within about a month and no longer.

A **legal hold** is the override: while one is on, the data must be kept whatever the schedule says. AWS describes it as providing "the same protection as a retention period, but it has no expiration date. Instead, a legal hold remains in place until you explicitly remove it", independent of any retention period and placed on individual object versions. Whether a hold applies, to what, and for how long is a question for the organization's lawyers; a backup tool only carries it out. This page is not legal advice, and I did not read a statute or a regulator's retention rule for it.

A **retention schedule** for a backup set is a table with the kind of data, the minimum and maximum time, who decides and who can lift a hold.

## The ransomware angle

CISA's #StopRansomware Guide (September 2023 edition; read 2026-10-31) gives the reason in one sentence: "It is important that backups are maintained offline, as many ransomware variants attempt to find and subsequently delete or encrypt accessible backups to make restoration impossible unless the ransom is paid." The same guide says to "regularly test the availability and integrity of backups in a disaster recovery scenario". Four things follow:

- **Reach is the attack.** The backup is lost when the account that was taken over can reach it. Immutable or offline copies break that reach; so does a backup credential that can add but not delete.
- **Tampering with recovery is a known step.** Among the signs of an intrusion, CISA lists "endpoint modifications that may impair backups, shadow copy, disk journaling, or boot configurations", and names anomalous use of Windows tools such as `vssadmin.exe` and `wbadmin.exe`, calling misuse of them "a common ransomware technique to inhibit system recovery". A backup system deserves an alert on its own deletes.
- **Restoring can restore the problem.** The guide warns that dropper malware must be identified "before rebuilding from backups to prevent continuing compromises". That is where retention and a clean-copy check matter.
- **A backup does not un-publish data.** Where an attacker also copied the data out first, a restore fixes availability and does nothing for confidentiality, as the CIA page's table shows. Detection and a decision made in advance are separate work.

## Cloud traps

Provider backups look like a finished plan and often are one copy.

| Trap | Evidence | What to do |
|---|---|---|
| The backup lives in the same datacenter as the thing it protects | DigitalOcean: "We store backups in the same datacenter as the corresponding Droplet." (backups features, last verified 9 Dec 2025, read 2026-10-31) | Count it as one copy in one failure domain. Add one somewhere else. |
| The backup is not encrypted at rest | DigitalOcean: "Backups are not encrypted at rest, but they are not externally accessible." (backups limits, last verified 17 Jun 2025) | Do not treat it as a confidentiality control. Keep sensitive data out of what it holds, or encrypt before the data reaches the disk. |
| The backup does not cover everything | DigitalOcean's automated backups "do not include volumes", and are crash-consistent: memory and cache not flushed to disk are lost | Know what is not in it. A database needs its own dump. |
| It is in the same account as the original | An attacker with the account's token, or a billing lockout, reaches both. CISA suggests "a multi-cloud solution ... in case all accounts under the same vendor are impacted". | One copy under a different account, ideally a different provider, with credentials that are not the same. |
| Versioning is mistaken for immutability | Spaces versioning page above | See the immutability section. |
| Lifecycle rules quietly delete the oldest copies | This project's bucket expires noncurrent versions after 90 days by default (`modules/spaces-bucket/variables.tf`) | The retention period is a setting; read it as such. |
| A managed service is the backup system | If you cannot export from it, the backup is only as available as the vendor | Check the export path before you need it. |
| Locks cost money to get wrong | CISA: misconfiguration of immutable storage "can impose significant cost" | Test the lock on throwaway data first. |

## Where this shows up in this project

The question for each row is the Backups page's: if this vanished tonight, what would you restore it from? "None" is a finding. A row says **Built** only for a file I read in the repository and did not run; **vendor page** means the way to back it up comes from the vendor's documentation, which I read, and not from anything this repository does.

| Item | Where it lives today | File or procedure in this repository | Status |
|---|---|---|---|
| The repository: code, stack definitions, policies, tests, and the wiki source in `docs/wiki/` | GitHub, plus every clone (the clones are accidental copies, not a plan) | None. GitHub's own backup page says to run `git clone --mirror` and archive the result (vendor page); nothing in the repository schedules or stores one | None |
| The published wiki | A derived copy, overwritten from `docs/wiki/` on every publish | `.github/workflows/wiki.yml`, `scripts/gen-wiki.sh` | Built; the rebuild is the publish workflow, not run for this page |
| Issues, pull request threads and comments | GitHub only | None. GitHub's migration-archive page says archives do not hold everything and that there is "no supported, documented way to restore" one (vendor page) | None |
| The board's layout (fields, options, views) | Defined in a file; the cards themselves live in GitHub's project | `board.yaml` | Layout: Built. Cards: None |
| OpenTofu state for the stacks that have been applied (stages 0 and 1) | Spacelift holds it ([Spacelift](Spacelift.md)); the vendor says non-current versions are kept for 30 days and that a task can run `terraform state pull` to export it when external state access is enabled | None. No export task or off-Spacelift copy is in the repository | None |
| Stage 3 daemon state | A Spaces bucket, versioned, noncurrent versions expire after 90 days by default | `modules/spaces-bucket/main.tf`, `modules/spaces-bucket/README.md` | Written, off by default; the restore commands in the README say they have not been run |
| A copy of the bucket off the DigitalOcean account | Designed as a nightly `rclone sync` | None built. The design is in `docs/superpowers/specs/2026-10-11-stage-3-workloads-design.md` section 7, layer 3 | None |
| The secret store (Doppler `prd`) | Doppler only. The names and owners of the stage 0 to 2 secrets are listed; values are not written anywhere | `docs/spacelift-secrets.md` (an inventory of names, not an export) | Inventory: Built. Export or second copy: None |
| Twingate configuration | Resources, groups, service accounts and the remote network are code. The account, the identity provider link, users, and anything made by hand are not | `stacks/10-access/main.tf`, `stacks/20-telemetry/main.tf`, [Teardown checklist](Teardown-Checklist.md#2-what-survives-a-destroy) | Code: Built, not applied for this page. Account-level settings: None |
| Droplets | Rebuilt from code; droplet backups are `false` on purpose | `modules/twingate-connector/main.tf` | Built; the rebuild path is not run here |
| The backup system itself: schedule, credentials, key, recovery kit | Does not exist yet for the items marked None above | None | None |
| A timed restore of any of the above | Never run | None | None |

Four honest notes from filling in the table.

- **What is protected today is code and not data.** Stages 0 and 1, the only ones applied so far, hold no data worth a backup, and rebuilding from code is the recovery. That is a good design for a lab, and it makes the code and the secrets the only things whose loss would hurt.
- **The weakest row is the secret store.** Doppler is the one place the values live. The inventory in `docs/spacelift-secrets.md` lists tokens that can be re-issued at their provider (I did not check each one, **est.**), so losing the store costs a day of re-issuing and not data. Doppler's documentation says: "We strongly recommend against downloading secrets in plain text to the file system." (read 2026-10-31). Any export of the store is itself a full set of secrets, so it must be encrypted before it is written, with a key held apart. The drill's encrypted copy is a tiny version of that.
- **Repository and board are one account.** GitHub holds the code, the issues, the wiki and the cards. That is one account and one failure domain for the whole project's knowledge. A mirror of the repository to a place that account's login cannot reach is the smallest fix, and it is not built.
- **Against 3-2-1-1-0, the repository scores:** copies, yes in practice (GitHub and clones); media and offsite, plausible; immutable, no; zero errors, no restore of a clone is documented. A reading, not a measurement.

## Free path: a restore drill on your own computer

Every exercise follows four steps: **predict**, **do**, **check**, **undo**. This one script runs the whole drill in a throwaway folder. Save it as `backup_drill.sh`.

```bash
#!/usr/bin/env bash
# backup_drill.sh - a restore drill in one throwaway folder. Touches nothing outside the folder it makes.
set -eu
lab=$(mktemp -d)
cd "$lab"
mkdir data keys copy-a copy-b

# The pretend important data: 40 small notes and one 256 KiB binary file.
for i in $(seq 1 40); do printf 'note %s\n' "$i" > "data/note-$i.txt"; done
head -c 262144 /dev/urandom > data/blob.bin
find data -type f -exec touch -d '2020-01-01 00:00:00' {} +
sums() { (cd "$1" && find data -type f | sort | xargs sha256sum); }
sums . > manifest-1.sha256

echo "== Backup types: one full, then one incremental"
tar --listed-incremental=state.snar -czf full.tgz data
printf 'note 41\n' > data/note-41.txt
printf 'changed\n' > data/note-1.txt
sums . > manifest-2.sha256
tar --listed-incremental=state.snar -czf incr.tgz data
echo "the full backup holds $(tar -tzf full.tgz | grep -vc '/$') files; the incremental holds $(tar -tzf incr.tgz | grep -vc '/$')"
mkdir only-incr chain
tar --listed-incremental=/dev/null -xzf incr.tgz -C only-incr
echo "restoring the incremental alone gives $(find only-incr -type f | wc -l) files, not $(wc -l < manifest-2.sha256)"
tar --listed-incremental=/dev/null -xzf full.tgz -C chain
tar --listed-incremental=/dev/null -xzf incr.tgz -C chain
if sums chain | diff -q manifest-2.sha256 - >/dev/null; then echo "full then incremental, in order: all $(wc -l < manifest-2.sha256) files match"; else echo "chain restore FAILED"; fi

echo "== Copies: one archive, two more places"
tar -czf backup.tgz data
sha256sum backup.tgz > backup.sha256
cp backup.tgz copy-a/backup.tgz
head -c 32 /dev/urandom | base64 > keys/backup.key
openssl enc -aes-256-cbc -pbkdf2 -salt -in backup.tgz -out copy-b/backup.tgz.enc -pass file:keys/backup.key
echo "copy A is plain, copy B is encrypted; all of it is on one disk, so this is a drill and not a 3-2-1-1-0 plan"
sed 's#backup.tgz#copy-a/backup.tgz#' backup.sha256 | sha256sum -c -

echo "== Key custody: the encrypted copy with the key, and without it"
head -c 32 /dev/urandom | base64 > keys/other.key
if openssl enc -d -aes-256-cbc -pbkdf2 -in copy-b/backup.tgz.enc -out wrong.tgz -pass file:keys/other.key 2>/dev/null && tar -tzf wrong.tgz >/dev/null 2>&1; then
  echo "opened with the wrong key (this should never print)"
else
  echo "the wrong key did not open copy B: without the right key it is just noise"
fi

echo "== Restore test: from the encrypted copy, timed, compared with the manifest"
start=$(date +%s%N)
mkdir restore
openssl enc -d -aes-256-cbc -pbkdf2 -in copy-b/backup.tgz.enc -pass file:keys/backup.key | tar -xzf - -C restore
bad=$(sums restore | diff manifest-2.sha256 - | grep -c '^[<>]' || true)
end=$(date +%s%N)
echo "restore and check took $(( (end - start) / 1000000 )) ms; $(find restore -type f | wc -l) files restored, $bad mismatches"

echo "== A damaged copy is found by the check, and the other copy still works"
printf 'XXXXXXXX' | dd of=copy-a/backup.tgz bs=1 seek=3000 conv=notrunc status=none
if sed 's#backup.tgz#copy-a/backup.tgz#' backup.sha256 | sha256sum -c - >/dev/null 2>&1; then echo "copy A is fine"; else echo "copy A FAILED its checksum"; fi
echo "copy B was restored above with $bad mismatches, so one good copy survived"

echo "== Retention: an intruder is present from day 3 and we keep only 3 daily copies"
mkdir ret
for d in 1 2 3 4 5; do if [ "$d" -ge 3 ]; then echo damaged; else echo clean; fi > "ret/day-$d"; done
ls ret | sort | head -n -3 | while read -r f; do rm "ret/$f"; done
echo "kept: $(ls ret | tr '\n' ' ')"
if grep -q clean ret/*; then echo "a clean copy is left"; else echo "no clean copy is left"; fi

cd /
rm -r "$lab"
echo "done: the lab folder is gone"
```

**Predict first.** Before you run it, write down: (a) how many files the incremental backup will hold, and whether restoring it alone gives you your data; (b) whether the wrong key will open the encrypted copy, and what you would see; (c) whether opening an encrypted copy will add noticeable time to the restore of a folder this small; (d) which of the five daily copies survive a keep-three rule, and whether any of them is clean.

```bash
bash backup_drill.sh
```

Output from my run (GNU bash 5.2.37, coreutils 9.7, tar 1.35, OpenSSL 3.5.7, Linux, 2026-10-31). The restore time is the one line that will differ on your machine:

```text
== Backup types: one full, then one incremental
the full backup holds 41 files; the incremental holds 2
restoring the incremental alone gives 2 files, not 42
full then incremental, in order: all 42 files match
== Copies: one archive, two more places
copy A is plain, copy B is encrypted; all of it is on one disk, so this is a drill and not a 3-2-1-1-0 plan
copy-a/backup.tgz: OK
== Key custody: the encrypted copy with the key, and without it
the wrong key did not open copy B: without the right key it is just noise
== Restore test: from the encrypted copy, timed, compared with the manifest
restore and check took 228 ms; 42 files restored, 0 mismatches
== A damaged copy is found by the check, and the other copy still works
copy A FAILED its checksum
copy B was restored above with 0 mismatches, so one good copy survived
== Retention: an intruder is present from day 3 and we keep only 3 daily copies
kept: day-3 day-4 day-5 
no clean copy is left
done: the lab folder is gone
```

How to read it:

- **Types.** The full backup holds 41 files (40 notes and the binary file). One note changed and one was added, so the incremental holds two. Restoring it alone gives two files and not the 42 you had. Only the full backup, then the incremental, in order, gives them all back and matches the manifest written earlier. A differential would have held the same two files here and the same two again the next day.
- **Copies and the checksum.** The checksum was written when the archive was made and kept apart from the copies. After a few bytes were overwritten in copy A, the check said FAILED. Without that earlier record you would have found out when you needed the copy.
- **Key custody.** A random key was made in `keys/`, and a second, wrong one. The wrong key could not open copy B. The right key could. The "0 mismatches" line is the only claim that counts: the restored tree was compared with a manifest written before the backup, not trusted because no error appeared.
- **Timing.** The restore and check took a fraction of a second here because the data is 256 KiB on a local disk. The Backups page showed that time grows with the data. Add the other rows of the timing table above, which no script can fill in.
- **Retention.** Day 3 is when the intruder arrived. Keeping three copies keeps days 3, 4 and 5, all damaged. The two clean copies were pruned first. A longer retention, or a copy kept separately, would have saved day 2.
- **What the drill is not.** Everything lives on one disk in one folder, so it meets none of the digits of 3-2-1-1-0 except as a model. Immutability is not in it, because making a file immutable normally needs privileges and a filesystem feature; the script would have to touch the system to show it.

**Check.** Did the incremental surprise you? If you added a third incremental the next day, how many pieces would a restore from scratch need? What would you change first if the restore had to be ten times faster: the size of the data, the number of pieces in the chain, or where the copy lives?

**Undo.** The script deletes its own folder. If it is stopped early, the folder is a directory named `tmp.` followed by random characters under `$TMPDIR` (or `/tmp`); delete only that one, after reading its name.

### Build, break, detect, evade, defend (on paper, on top of the drill)

**Build.** List the three things in your own setup you would least like to lose. For each, name where the copies are, who can delete them and where the key is.

**Break (words only).** For the one at the top, say in one sentence how an honest mistake loses every copy, and in one how an attacker with one stolen password does.

**Detect.** Name the one check that would show you: a checksum for a rotted copy, an alert on a delete for a tampered store, a failed restore test for a bad key.

**Evade.** The tempting move is to keep the backups secret and call that protection. Hiding a location slows a casual attacker and not one who already holds your credentials.

**Defend.** Add the cheapest control that moves the highest risk: a second copy under a different login, a write-only credential, a recovery kit with two holders, or a calendar entry for a restore test.

### Flip the board

**The reviewer.** A colleague says: "We have 3-2-1-1-0. Three copies, two clouds, one in another region, one with Object Lock, zero errors on the dashboard." Find at least four questions that would make you unsure. Examples: Are both clouds in one account? Who can change the lock mode or the retention? When did anyone last restore with only the recovery kit? What does "zero errors" count, a job's exit code or a restored and compared tree? Where is the key, and who else holds it?

**The responder.** It is a bad day and the newest backup might include the intruder. List in order what you do before restoring: find when the damage began, pick the newest copy older than that, check the copy against a record, and restore into a fresh place and not over the only copy. Say which of those the project table could support today.

## Checkpoint

- Say what each digit of 3-2-1-1-0 asks for, and who added the last two.
- A full backup on Sunday and an incremental each night. It is Thursday. How many pieces does a restore need? With differentials instead?
- Name three things an immutable copy does not protect against.
- Why is versioning not immutability?
- Your encrypted backup is fine and the key is on the dead server. What have you got?
- Name five things, besides the data, that a backup system needs backed up.
- Why can a retention of three copies fail when the backup job never fails once?
- What does a legal hold do to a retention schedule, and who decides if one applies?
- Name two rows of this project's table that say **None** and the question each leaves open.

## Common mistakes

| Symptom | Most likely cause | What to check |
|---|---|---|
| "We have 3-2-1" and one login can delete all three copies | The copies share a credential | Who can delete each copy, and with which login |
| Versioning is on, so "they cannot delete it" | Versioning mistaken for a lock | Whether the same key can permanently delete a version |
| The immutable copy restores corrupted data | It was made from damaged data | The check you ran before the copy was locked |
| Encrypted backup, key stored with it | Encryption without custody | A restore using only the recovery kit |
| A restore test that "passes" and the data is wrong | Nothing compared the result with an earlier record | A manifest or checksum made before the disaster |
| The incremental chain will not restore | One link is missing or out of order | Restore the full first, then each piece in order; test the whole chain |
| Backups kept three days, found the problem on day six | Retention shorter than time to notice | The retention against a realistic time to notice |
| The provider's backup is the only copy | Same datacenter, same account, not encrypted | The vendor page's limits, not the product name |
| A lock set for ten years by mistake | Compliance mode cannot be shortened | Test on throwaway data and read the retention setting twice |
| Nobody knows how long a restore takes | It was never timed end to end | The timing table, once, with a stopwatch |

## Claims register

Standards and vendor pages were downloaded and read on **2026-10-31**; repository files were read in the worktree this page was written in on the same day. Status words: **Read** means I read the passage, **Observed** means I ran it, **Not run** and **est.** mean neither, and **General knowledge** means I did not look it up.

| Claim | Source | Status |
|---|---|---|
| Veeam extended 3-2-1 to 3-2-1-1-0: one immutable copy and zero recovery errors; zero means automated integrity checks and regular restore testing; the rule dates from the early 2000s; storage snapshots on non-separate media need caution | [Veeam, *What is the 3-2-1 Backup Rule?*](https://www.veeam.com/blog/321-backup-rule.html), by Julia Furst Morgado, February 5, 2024, updated July 3, 2026 | Read 2026-10-31 |
| 3-2-1 was "first introduced in the late aughts" | [Backblaze, *The 3-2-1 Backup Strategy*](https://www.backblaze.com/blog/the-3-2-1-backup-strategy/) (no date read on the page) | Read 2026-10-31 |
| The 3-2-1 rule, three copies, two media, one offsite | [CISA, *Data Backup Options*](https://www.cisa.gov/sites/default/files/publications/data_backup_options.pdf) | Read for the Backups page on 2026-10-22; not re-read for this one |
| Peter Krogh is the usual attribution for 3-2-1 | General knowledge | **est.**; [his site](https://thedambook.com/) was read 2026-10-31 and does not mention the rule |
| Full, incremental and differential backups, and how each restores; encrypted offsite data needs media readers and a key process with keys "separate from, but accessible to" the backup; backup testing is a control for moderate and high impact systems; test frequency is decided from the resilience policy and BIA | [NIST SP 800-34 Rev. 1, May 2010](https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-34r1.pdf) (PDF text extracted; the guide describes tape and disk media) | Read 2026-10-31 |
| Offline, encrypted backups; test availability and integrity; ransomware seeks accessible backups; immutable storage with caution (compliance criteria, cost of misconfiguration); multi-cloud for cloud-to-cloud backups; IaC templates kept offline; third parties holding backups; dropper malware before rebuilding; `vssadmin` and `wbadmin` misuse as a sign | [CISA #StopRansomware Guide, September 2023 edition](https://www.cisa.gov/stopransomware/ransomware-guide) | Read 2026-10-31 |
| S3 Object Lock: WORM; retention periods and legal holds; compliance mode blocks every user including root, with deletion of the account the only way out; governance mode can be bypassed with permission; a lock covers one version and not new versions or delete markers; works only with versioning | [AWS, Locking objects with Object Lock](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html) (no date read on the page) | Read 2026-10-31; not run |
| Spaces versioning is off by default; it lets you restore a previous version; the same key can permanently delete a version | [DigitalOcean, Spaces versioning](https://docs.digitalocean.com/products/spaces/how-to/enable-versioning/) | Read 2026-10-31; not run |
| No mention of Object Lock, WORM or immutability on the Spaces features and limits pages | [features](https://docs.digitalocean.com/products/spaces/details/features/) (last verified 13 Jul 2026), [limits](https://docs.digitalocean.com/products/spaces/details/limits/) (last verified 3 Sep 2026) | Read 2026-10-31 (a search of the page text for lock, immutable and WORM); absence is not proof |
| Droplet backups are in the same datacenter, not encrypted at rest, exclude volumes, crash-consistent | [features](https://docs.digitalocean.com/products/backups/details/features/) (last verified 9 Dec 2025), [limits](https://docs.digitalocean.com/products/backups/details/limits/) (last verified 17 Jun 2025) | Read 2026-10-31 |
| restic: losing the password loses the data; a repository can hold multiple keys | [restic 0.19.1, Preparing a new repository](https://restic.readthedocs.io/en/stable/030_preparing_a_new_repo.html) | Read 2026-10-31; not run |
| Spacelift state: non-current versions kept 30 days; export by running `terraform state pull` in a task with external state access enabled | [Spacelift, state management](https://docs.spacelift.io/vendors/terraform/state-management) (no date read on the page) | Read 2026-10-31; not run |
| Doppler recommends against downloading secrets in plain text to the file system; `doppler secrets download` exists | [Doppler, accessing secrets](https://docs.doppler.com/docs/accessing-secrets) | Read 2026-10-31; not run |
| GitHub: back up a repository and a wiki with a mirror clone; migration archives do not include everything and have no supported restore | [GitHub, backing up a repository](https://docs.github.com/en/repositories/archiving-a-github-repository/backing-up-a-repository) | Read 2026-10-31; not run |
| `chattr +i` makes a file immutable for non-root users | General knowledge | **est.**; not run |
| The recommended test intervals, the retention advice, and the "knowledge of the key has one holder" reading are my suggestions | None | **est.** |
| The spaces-bucket module turns on versioning, `force_destroy = false`, and expires noncurrent versions after 90 days by default; off by default | `modules/spaces-bucket/main.tf`, `modules/spaces-bucket/variables.tf`, `modules/spaces-bucket/README.md` | Read 2026-10-31 |
| The wiki is published from `docs/wiki/` by a workflow and replaces the wiki's pages | `.github/workflows/wiki.yml`, `scripts/gen-wiki.sh` | Read 2026-10-31; not run |
| The board layout is defined in a file | `board.yaml` | Read 2026-10-31 |
| Stage 3 design layer 3, a nightly `rclone sync` off the account | `docs/superpowers/specs/2026-10-11-stage-3-workloads-design.md`, section 7; a search of `modules`, `stacks` and `scripts` found no `rclone` | Read 2026-10-31; the search is Observed |
| Secrets are listed by name and owner; values are not written | `docs/spacelift-secrets.md` | Read 2026-10-31 |
| Twingate resources, groups and service accounts are defined in code | `stacks/10-access/main.tf`, `stacks/20-telemetry/main.tf` | Read 2026-10-31; not applied |
| Droplet backups are `false` in the connector module | `modules/twingate-connector/main.tf` | Read 2026-10-31 |
| The Bash script and its output | The free path | **Observed** 2026-10-31, GNU bash 5.2.37, coreutils 9.7, tar 1.35, OpenSSL 3.5.7, Linux |
| The script on macOS, or under another shell | | **Not run** |
