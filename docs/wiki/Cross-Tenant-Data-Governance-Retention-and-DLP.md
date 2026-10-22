# Cross-tenant data flows, data governance and retention, and DLP

Side page to the enterprise pages. Read it after [Telemetry crosses the trust boundary](Telemetry-Crosses-the-Trust-Boundary.md) and [Backups, recovery and patching](Backups-Recovery-and-Patching.md) if "tenant", "retention", "purge" or "DLP" are only words to you, or any time you meet them at work. It moves data between two accounts that belong to different owners, makes it disappear on a schedule, and then builds a toy scanner that looks inside files for things that should not leave. Next: [Enterprise identity and secrets at scale](Enterprise-Identity-and-Secrets-at-Scale.md).

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

> **Status: the free local lab was run once on Linux; vendor claims were read on 2026-10-22; nothing was run against a real cloud account.** On **2026-10-22** the author ran every Bash command in the free path on a Debian-based Linux machine with Python 3.13.5, `moto` 5.2.4, `boto3` 1.43.118 and `rclone` v1.60.1, as an ordinary user, and pasted trimmed output from those runs. **Not run:** the PowerShell commands (no Windows machine; written from Microsoft's documentation, marked **est.**), anything against AWS or DigitalOcean (the own-account section is a pointer, never applied), and anything on Zscaler or Twingate products (there was no tenant of either; their sections are written from their public documentation as read). The lab's "tenants" are two local `moto` servers. `moto` is a test double: its own documentation says it applies only simple bucket-policy statements, so the policy checking you see is a teaching toy in this repository, not what AWS does. The lab data is invented. Every vendor claim is in the [claims register](#claims-register) with a URL and the date it was read. This page is **not** the real-world process it was inspired by; see the next box.

> **Where the idea comes from.** The maintainer asked for this lesson on 2026-10-22. His words, kept for their substance: "We haven't really covered cross tenant situations like an S3 bucket sync for data governance reasons with data retention, like when I used to automatically process DLP rules with PII processed from Data governance that was purged within 24 hours of transfer, done once a month, more than enough time to process it or get an error and then manually process it as the monthly task, as an example for Email DLP and Network DLP with Zscaler. This is one of those things that Twingate doesn't have compared to Zscaler that are valuable to enterprise." He added that the repetitive parts of a task like that should be automated as far as is safe. That is his experience and his statement. This page gives no detail of any real company, team, tenant or process, and none of it is a description of one.

> **Prerequisites.** [Enterprise identity and secrets at scale](Enterprise-Identity-and-Secrets-at-Scale.md) for roles, service accounts and why a long-lived key is a liability, [Backups, recovery and patching](Backups-Recovery-and-Patching.md) for what a copy is, [Twingate](Twingate.md) and [Why ZTNA and not a VPN](Why-ZTNA-Not-a-VPN.md) for what an access-only product does, and [The terminal and your first script](Terminal-and-Your-First-Script.md). The free path needs Linux, macOS or WSL 2 with `python3` (3.10 or newer, est.; the author ran 3.13.5) and internet access once, to install two Python packages from PyPI. `rclone` is used in one exercise and is optional. About three hours for the reading and the free exercises (est.). No account and no card.

> **Where this runs.** Both "tenants" listen on the loopback address `127.0.0.1` only, so nothing on your network can reach them, and they hold invented data. The lab never mounts a container socket and never touches a real cloud. The scanner reads only the folder you point it at. Do not point any tool on this page at data that is not yours, and never load real personal data into the lab.

## What you will be able to do

- Say what a tenant, an account and an organization are, and why data crossing between two of them is a different problem from data moving inside one.
- Explain why data crosses a boundary (governance, analytics, partners, backups, acquisitions) and who owns the data, the copy and the key in each case.
- Say what pull and push mean for a transfer and which side holds the power.
- Design a least-privilege transfer role and read a cross-account bucket policy.
- Explain what S3 Lifecycle expiration does and does **not** promise, and what "purged within 24 hours" actually takes.
- Describe a monthly batch with a verify step, an error path, a manual fallback and evidence, and say what to automate and what to leave to a person.
- Explain data loss prevention (DLP) in plain words: email DLP, network DLP, dictionaries, patterns, exact data match, false positives, and what an access-only product does not inspect.
- Run a two-tenant lab and a toy DLP scanner on invented data, tune a false positive, and say what the toy cannot do.

## What the wiki already says (and the gap)

| Idea | Where it is today | The gap this page fills |
|---|---|---|
| A trust boundary | [Telemetry crosses the trust boundary](Telemetry-Crosses-the-Trust-Boundary.md) draws one between the cloud site and the home site, with pull for metrics and push for logs. | The same questions between two *owners*: who holds the key, who may delete, what is kept and for how long. |
| The planned Spaces bucket | The [stage 3 design](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/superpowers/specs/2026-10-11-stage-3-workloads-design.md) (section 3b) plans one bucket, versioning on, a 90-day noncurrent-version lifecycle rule, and one key per daemon scoped to its prefix. | A second account on the other side. One account is where this project stops; this page is the next step. |
| Copies and backups | [Backups, recovery and patching](Backups-Recovery-and-Patching.md) covers keeping copies. | Deleting on purpose, and proving it. |
| DLP | [Why I picked these tools](Why-I-Picked-These-Tools.md) says Twingate is access control and not DLP, and names the three places DLP works. | What DLP is made of, a toy you can run, and an honest read of what each vendor documents. |
| Tenant | The Glossary defines it for one hosting setup. | The cloud meaning: an account or organization with its own owner and bill. |

## A boundary is an owner

A **tenant** is one customer, one team or one organization in a shared system; the [Glossary](Glossary.md) has the short form. Cloud providers draw the line in different places and with different names. In AWS the line is the **account**: a container for resources with its own owner, its own bill and its own identities, optionally grouped under an **organization**. (Azure uses "tenant" for the identity directory and "subscription" for the billing container; Google Cloud uses "organization" and "project". The names differ and the idea is the same, so check the vendor's words. [Why the clouds differ](Why-the-Clouds-Differ.md) does this for other terms.) In a software-as-a-service product, a tenant is one customer's slice of the product. In a security service such as a web gateway, your tenant is your company's configuration inside the vendor's shared platform.

What matters is what a boundary gives you. Inside one account, a mistake and an attack look alike from far away. Between two accounts, **neither side can reach the other unless both say yes**. That double yes is the whole design:

- The owner of the data says "this other identity may read or write here".
- The other side says "this identity of mine may use that permission".

AWS documents exactly this for buckets: a bucket owner can grant another account permissions, and the other account must then delegate them to its own users or roles; its walkthrough says granting to roles is the better practice than granting to individual users. See the claims register. The consequence is that a cross-account transfer has **two places to get wrong** and two places to look when it breaks.

## Why data crosses a boundary

| Reason | Example, in the abstract | The question that decides the design |
|---|---|---|
| Governance | A team that owns a system of record sends a monthly extract to another team that applies policy (classification, review). | Who is allowed to see raw data, and for how long? |
| Analytics | Production data feeds a separate analytics account so a heavy query cannot hurt production. | Does the analytics side need the identifying fields at all? |
| Partners and vendors | A supplier sends you a file; you send a report to an auditor. | What happens to the copy when the contract ends? |
| Backups | A copy goes to a second account so that one stolen key cannot delete both. This project's stage 3 design does the same idea with a nightly copy off the account. | Can the account being backed up delete the backup? |
| Acquisitions and reorganizations | Two companies become one and their accounts merge slowly. | Whose rules apply during the years in the middle? |
| Telemetry | Logs from one site go to a SIEM in another. [Telemetry crosses the trust boundary](Telemetry-Crosses-the-Trust-Boundary.md) is this case. | What leaves with the log line? |

Every row is a **copy** of data under someone else's control. A cross-tenant flow is a decision to make a copy, so the copy needs an owner, a purpose and an end date, written down before the first byte moves.

## Pull or push, and who owns the key

Two questions settle most of a transfer's security.

**Who starts it?** In a **push**, the source account's job reaches into the destination and writes. In a **pull**, the destination reaches into the source and reads. Neither is safer by nature; they differ in whose credentials leave home. A push means the source holds a credential valid in the destination (so a compromise of the source can write there). A pull means the destination holds one valid in the source (so a compromise of the destination can read there). Pick the direction so the credential that crosses the line can do the *least*: a write-only role for a push, a read-only role scoped to one prefix for a pull. The same idea appears on the telemetry page as "pull for metrics, push for logs".

**Who holds the encryption key?** Object storage can encrypt data at rest with a key. If the *source* account's key encrypts the object, the destination must be allowed to use that key to read it; AWS documents that cross-account use of a KMS key needs permission in **both** the key policy and an identity policy in the other account, and that cross-account permission works only for a short list of operations (cryptographic operations and a few key-management reads), not for administration. If the *destination* encrypts with its own key on arrival, the source never needs the key and cannot decrypt the copy later. For a governance flow that ends in a purge, the destination's key has a useful side effect (deleting a key can make every copy it protected unreadable), but key deletion is a heavy, mostly irreversible tool and is a different thing from deleting data; do not treat it as a purge unless your policy says so (est.).

## Least privilege for a transfer

A transfer role should do one job. Compare the two policies the lab prints:

```text
narrow:  one role from account A may only put and tag objects under one
         prefix of one bucket in account B (write-only); a separate processing
         role INSIDE account B may read and delete under that prefix.
broad:   Principal "*", Action "s3:*", the whole bucket.
```

The narrow one answers four questions: **who** (a named role in a named account), **what** (two write actions for the transfer role; read and delete go to a different role that lives in the destination account, so a stolen transfer credential can add data but cannot read or destroy it; no listing of other keys, no policy changes), **where** (one prefix), **when** (add a condition, such as a source address or a required encryption header; the lab's toy ignores conditions, so read the AWS page for them). The broad one is what an urgent Friday fix leaves behind: it also lets any other principal read the batch. A wildcard principal on a bucket that holds personal data is a finding in any audit.

Two habits help. Use a **role** the job assumes for a short time rather than a user with a long-lived key (see [Enterprise identity and secrets at scale](Enterprise-Identity-and-Secrets-at-Scale.md)). And write the policy so the *destination* owner reviews it: the people who will hold the copy should agree to what can land there.

## Encryption in transit and at rest

**In transit** means while it moves: HTTPS between the job and each bucket. Check that your tool uses it; the lab uses plain HTTP on loopback because nothing leaves the machine, which is a reason it is a lab and not a template. **At rest** means on the provider's disks. Both AWS and DigitalOcean encrypt in some form (the details differ by service and setting; read the vendor's page for the one you use rather than assume). Encryption does not stop a permitted reader from copying data out, so it is a layer under access control, not a substitute for it. See [Hashing, encryption and keys](Hashing-Encryption-and-Keys.md).

## Retention and purge

**Data retention** is the rule for how long data is kept and what happens at the end. A **retention schedule** lists each kind of data with a period, a reason and an owner. Three different things hide inside the word "delete".

1. **Expire**: a rule says the object should go after N days.
2. **Purge**: someone runs a job that removes it, then checks it is gone.
3. **Hold**: someone stops all deletion because there is a legal or audit reason to keep it.

### What S3 Lifecycle does and does not promise

An S3 **lifecycle rule** is a bucket setting that tells S3 to act on objects by age or other filters. The expiration action's timing, as AWS documents it (read 2026-10-22):

- Rules are written in **days**. S3 computes the date by adding the days to the object's creation time and **rounding up to the next day at midnight UTC**. A rule of one day means "eligible some time between about one and two days later", not "24 hours after upload".
- Expiration is **asynchronous**. AWS says there is a delay between a rule being satisfied and the action completing, that objects may stay "days or even weeks later", and that "S3 Lifecycle doesn't guarantee a completion time for transition or expiration actions".
- In a bucket without versioning, S3 queues the object for removal. In a versioned bucket, expiring the current version adds a **delete marker** and keeps the old version as noncurrent; you need a second rule (noncurrent-version expiration) to remove it.
- You can monitor it. AWS documents lifecycle event notifications and says to wait for one to confirm an expiration.

So a lifecycle rule alone **cannot give a 24-hour guarantee**. It is a good **backstop**: the thing that eventually cleans up when everything else failed. (The stage 3 design uses a lifecycle rule in exactly that role for old versions.) DigitalOcean documents lifecycle rules for Spaces too, with time-based expiration and removal of incomplete multipart uploads supported and tag-based rules not supported; the exact timing semantics there I did not read, so assume nothing stronger than for S3 (est.).

### What "purged within 24 hours of transfer" takes

An explicit **purge job**, run by you, that: deletes the transferred copy after processing (or after a fixed time), **verifies** the delete by listing the prefix and expecting it empty, writes **evidence** (counts, times, no content), and **alerts** when anything fails or when an object is older than its deadline. The lifecycle rule stays as the backstop and the alert is the thing that tells a human the job did not do its work. In the lab, every transferred object carries a `purge-after` timestamp (transfer time plus 24 hours), and a sweep command finds anything past it.

### Hold versus purge, and proof of deletion

A **legal hold** is a stop sign: while it is in place the data must not be deleted, whatever the schedule says. In S3, **Object Lock** can make an object version immutable for a retention period, in *governance* mode (privileged users can override) or *compliance* mode (no one can, including the account's root user, until the period ends), and a legal hold is a separate flag with no expiry that stays until removed. AWS documents all three. Object Lock needs versioning and is aimed at keeping data, so it **conflicts** with a purge: you decide per dataset which one wins, and the answer belongs to your legal and compliance people, not to the person writing the script. The job should check for a hold *before* it purges and stop and alert if it finds one.

**Proof of deletion** is evidence, not a feeling. What you can show: the log line that says the job ran, a listing that came back empty, a record of the delete requests in the provider's audit log (S3 data events in CloudTrail can record object-level calls, if enabled, and billed separately (est.); server access logs are delivered on a best-effort basis, as AWS documents). What you cannot show: that the provider's backups and replicas of the bytes are gone; provider documentation and contracts cover that (est.).

## The monthly batch

Here is the pattern from the maintainer's experience, in general terms. A flow runs **once a month**. The data is **sensitive** and is **purged within 24 hours of the transfer**. A month is a long time, so there is room to retry, and the design assumes it will sometimes fail: the job either finishes or raises an error, and when it raises an error a person handles it **manually as a documented monthly task**. The steps:

1. **Extract** the batch in the source account.
2. **Transfer** it (push or pull, with the narrow role).
3. **Verify**: every object arrived and its hash matches.
4. **Process** it on the destination side (for example, run DLP rules, the subject of the second half of this page).
5. **Purge** the destination copy, **verify** it is gone.
6. **Report** and keep **evidence**.
7. On any failure: **stop, alert, do not purge unverified data**, and hand over to the manual runbook.

### Automate the repetitive, keep a person for the exceptions

The maintainer's rule is to automate as much of the repetitive work as is safe. Here is a way to sort it.

| Automate (repetitive, checkable) | Keep manual (judgment, authority) |
|---|---|
| Extract, transfer, hash verify, purge, empty-listing verify, evidence file, report | Approving the first run and any change to the job |
| The alert on failure and on an overdue object | Investigating why a run failed |
| The dry run that shows what would happen | Placing or lifting a legal hold |
| Rotating the credentials the job uses (see [Doppler and secrets](Doppler-and-Secrets.md)) | Deciding that an empty month is fine, or that a mismatch is acceptable |

The cost of automation is real, and a lesson that only sells it is incomplete. An automated job needs **monitoring** (a job nobody watches is a job that fails silently for months), an **owner** (a named person or team, not "whoever wrote it"), **change control** like any production system (see [Enterprise change management for beginners](Enterprise-Change-Management-for-Beginners.md)), and a **practiced manual path**, because the day automation breaks is the day nobody remembers the manual steps. The most dangerous failure of a purge job is silence: it did not run, it ran and deleted nothing, or it deleted the wrong thing and reported success. The lab's job therefore fails *loudly* and checks its own result.

The lab script has a `--dry-run` flag, a verify step, an injected-error option, an alert log and an evidence file; Exercise 5 runs all of them.

## PII, classification and minimization

**PII** is personally identifiable information: data that identifies a person alone or combined with other data (a name with an address, a government ID, a card number). Which data counts, and the rules that go with it, depend on law and contract and differ by country and industry; this page does not give legal advice (est.). Three habits are universal:

- **Classify** data into a few named levels (for example public, internal, confidential, restricted), with a rule for what each level may do. A classification nobody applies is decoration.
- **Minimize**: send the destination only the fields it needs. The cheapest way to protect a field is not to copy it. If analytics needs a count per customer, send a pseudonym (a stable made-up identifier) and keep the lookup table in the source account.
- **Know where it is**. You cannot purge what you cannot find, which is part of why DLP scanning exists.

## DLP in plain words

**Data loss prevention (DLP)** is software and policy that looks at data as it is stored, moves or is sent, and acts when the content matches a rule that says "this should not leave here". DLP is about the *content* and the policy, not about one particular packet technique. It answers a question that access control does not: access control asks "may this person reach that system"; DLP asks "what is in the thing they are sending".

### Where DLP looks

| Place | What it watches | Plain example |
|---|---|---|
| **Email DLP** | Outbound (sometimes inbound) mail: subject, body and attachments | A message to an outside address contains a spreadsheet of card numbers |
| **Network DLP** (inline, web) | Traffic through a proxy or gateway: uploads to web mail, cloud storage, social sites | A file upload to a personal storage site contains a customer list |
| **Endpoint DLP** | Files, clipboard, USB and uploads on the laptop itself | Copying a restricted file to a USB drive |
| **Data at rest** (SaaS and cloud scanning) | What is already stored and shared in an app or a bucket | A shared folder holds an old export of personal data |

[Why I picked these tools](Why-I-Picked-These-Tools.md) lists the first three places in the same terms. Each catches things the others miss.

### What a rule is made of

- A **dictionary** is a set of things to look for: keywords and phrases, or patterns.
- A **pattern** is usually a **regular expression** (regex), a compact way to describe a shape, such as "two letters, six digits, two letters".
- A **validator** reduces false alarms: a card number has a checksum (the Luhn algorithm), so a 16-digit string that fails it is probably not a card.
- A **threshold** says how many matches count: one email address in a file is normal; five hundred is a list.
- **Exact data match (EDM)** compares against *your own* real records (indexed in a form that is not the raw data) instead of guessing from a shape. It finds "this specific customer's number" and ignores a similar-looking number that belongs to nobody.
- **Fingerprinting** (Zscaler calls it Indexed Document Match, IDM) indexes whole documents so that a full or partial copy of a protected form is recognized, without searching for keywords.
- An **engine** combines dictionaries and thresholds into the thing a policy rule uses (Zscaler's term).
- The **action** is what happens on a match: allow and log, alert, **quarantine** (hold for review), or block.

### The hard part is false positives

A **false positive** is an alarm about something harmless; a **false negative** is a miss. They trade off: tighten a rule and you miss more, loosen it and reviewers drown. Real programs have a **review queue** of humans who decide on quarantined items, and they spend most of their time tuning the rules, not writing them. The lab shows the three standard tuning moves: a validator, a threshold and an allowlist.

### TLS inspection and its privacy cost

Most web traffic is encrypted with TLS ([How a web request works](How-a-Web-Request-Works.md)), which means a gateway cannot read an upload unless it **terminates and re-establishes the encryption** on the user's behalf, using a certificate the company's devices have been told to trust. That is TLS inspection. It is what makes network DLP possible for web traffic, and it has costs (est., general practice; I did not read a vendor page for this): the gateway can read banking, medical and personal traffic unless you exclude those categories; the inspection point becomes a high-value target; some applications break; and employees must be told. Many organizations exclude sensitive categories, and in some countries employee-monitoring law limits what can be inspected. Anyone building this should read their own legal and works-council requirements first.

## Zscaler as a worked example

Zscaler is a secure web gateway and cloud security product. The maintainer administers it in his work and has used its DLP. This section is from Zscaler's public help site, read on **2026-10-22**; the help site loads its pages through JavaScript, so I read the articles through the JSON endpoint that the site's own page uses, and each claim below is in the register. I had no tenant and ran nothing.

What the documentation says:

- **Inline DLP.** A DLP policy rule applies DLP **engines** (made of dictionaries) to outbound web content, with actions to monitor or block, and it can forward information about matching transactions to a third-party DLP product over ICAP (the Internet Content Adaptation Protocol). It says the service does not take ICAP responses back from that product; it only forwards.
- **Dictionaries.** Predefined dictionaries you can modify or clone, and custom dictionaries built from patterns, phrases or exact data match.
- **Outbound Email DLP.** Your mail system (Gmail, Microsoft Exchange, or a secure email gateway) is configured to send outbound mail to a Zscaler **smart host** over SMTP; Zscaler inspects subject, body and attachments, adds **headers** that carry the DLP verdict, and your mail system enforces the action from those headers. It describes granular enforcement, such as blocking a message for one recipient and allowing it for another.
- **EDM and IDM.** You create index templates in the **Index Tool**, then apply them to custom dictionaries and engines. For EDM, the page says you can have up to 64 templates, and it recommends designing a template so records need indexing once and re-indexing is avoided.
- **Data at rest.** SaaS Security scans of stored content are configured with scan schedules.

### The Index Tool, and automating it

The Index Tool is a virtual machine (an `.ova` image) that you host on AWS, Azure or on premises. As documented, you browse to its address with your admin credentials, **upload a CSV file**, choose a data type for each field (the credit card type gets a Luhn check), mark one or two **primary** fields, and submit; the template then appears in the admin console. The documentation says the service updates the tool automatically and it is unavailable for about an hour during an upgrade, and that the template size drives how much memory the VM needs.

**What I did not find.** The pages I read describe a web interface. They do not describe a command-line mode, an API for creating or refreshing a template, or a scheduled run of the Index Tool. The maintainer says there are ways to automate the Zscaler indexing as an automated task; I take that as his experience, and I cannot confirm from the documents I read how it is done, so I make no claim about the mechanism (est.). Zscaler also publishes API documentation at `automate.zscaler.com`; I fetched its overview page but did not read it, so whether it covers this task is unverified. If your tenant has an automation route, ask your vendor contact or read that documentation, then apply the safe-automation checklist below to whatever route you find. If you only have the web interface, the same checklist applies to the *preparation* around it (producing and staging the CSV, cleaning up afterward, tracking that the monthly refresh happened).

### Safe automation of a recurring indexing task

Whatever the mechanism, a monthly indexing job is a copy of sensitive records moving into a security tool, so it gets the full treatment:

1. **Schedule it** with something that records runs: cron, a systemd timer, or a CI scheduled workflow. Do not rely on a person remembering.
2. **Make it idempotent**: running it twice leaves the same result as running it once (check "template already current" before re-indexing, since re-indexing has a cost).
3. **Secrets come from a secrets manager**, not the script or the scheduler's plain environment. This project's version is [Doppler and secrets](Doppler-and-Secrets.md).
4. **Stage the source data in one controlled location** (restricted permissions, encrypted volume, not a shared drive) and **purge it after the run**, then verify. The extract is the dangerous artifact, not the index.
5. **Log every run** (what, when, counts, outcome), never the content.
6. **Alert on failure and on silence**: a missing run is a failure.
7. **Write a runbook** for the manual error path, test it, and keep it next to the job.
8. **Keep evidence of completion** (a dated record a reviewer can read).
9. **Put the job under change control**: reviewed changes, a named owner, and a record of who may edit it.

The lab's monthly job is a small instance of items 1 to 8.

## Twingate and Zscaler: a different category, not a competition

Twingate is a zero trust network **access** product: it decides who can reach which resource, and its tunnels are encrypted end to end between its clients and connectors. [Twingate](Twingate.md) and [Why ZTNA and not a VPN](Why-ZTNA-Not-a-VPN.md) explain this project's use of it. What I read on **2026-10-22** in Twingate's documentation: pages on access, devices, connectors, audit logs and network events, an "Internet Security" section that documents DNS filtering and DNS-over-HTTPS, and a page on syncing audit, network and DNS-filtering logs to a customer's S3 bucket (Business and Enterprise plans only, as that page states). The encryption page says traffic between clients and connectors is encrypted so that no third party, **including Twingate**, can decrypt it. I searched the documentation's navigation and read the pages above and **found no page about DLP or content inspection**. That is "the pages I read describe access control and do not describe DLP", not proof that nothing exists; Twingate adds features, and you should check its current documentation.

The maintainer's statement, attributed to him: this is one of the things Twingate does not have compared to Zscaler, and it is valuable to enterprises. That is a fair reading of the categories. Twingate is an access product, DLP is a different kind of product, and a secure web gateway with DLP is not what Twingate sells. **This project uses Twingate for access and does not claim it replaces a secure web gateway with DLP.** An organization that must stop a customer list leaving in an upload needs a content-aware control somewhere, whichever vendor supplies it. For the same reason, in the loop below, the access-only layer cannot be the one that catches exfiltration of data a permitted user is allowed to reach.

An access-only product sees *who connected to what, when, and how many bytes*. It does not look inside the bytes. That is a design choice with a privacy upside (a vendor that cannot read your content cannot leak or be compelled to hand it over) and a coverage downside (no content-based block).

## Where this shows up in this project

- **Stage 3 bucket (#113).** The design plans one DigitalOcean Spaces bucket in one account, with versioning, a 90-day noncurrent-version lifecycle rule, and a key per daemon scoped to a prefix. It is **planned, not built**. A second account (an off-account copy, or a partner) is the cross-tenant step, and the design already names it as the third backup layer.
- **Telemetry.** Logs and metrics already cross a boundary over Twingate; [Telemetry crosses the trust boundary](Telemetry-Crosses-the-Trust-Boundary.md) is the access half. This page is the content half: what is in the log lines, and how long the receiver keeps them.
- **No DLP here.** The repository does not run a DLP product. The lab scanner is a teaching toy, not a control this project depends on.

## Free path: a lab on your own computer

Every exercise follows four steps: **predict** (write down what you expect), **do**, **check**, **undo**. The code lives in [`labs/cross-tenant-dlp`](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/tree/main/labs/cross-tenant-dlp) in the repository. Copy that folder to your machine, `cd` into it, and set a work folder.

**Keep the work folder private.** It holds a Python environment the lab runs and files the lab uses to stop its own servers. A predictable folder in a shared place such as `/tmp` can be created ahead of you by another user on the same machine, who could then plant code you will run. So the lab uses a folder under your own account, and its scripts create it with mode 700 and **refuse to continue** if it already exists and is not yours, is a symbolic link, or is writable by group or others. Do not point `LAB_WORK` at a shared folder.

```bash
export LAB_WORK="${XDG_RUNTIME_DIR:-$HOME/.cache}/cah-xtenant-lab"
```

```powershell
# est.: not run. PowerShell 7 on Windows, with Python 3 installed. LOCALAPPDATA is per user.
$env:LAB_WORK = "$env:LOCALAPPDATA\cah-xtenant-lab"
New-Item -ItemType Directory -Force $env:LAB_WORK | Out-Null
```

The Bash start script (next exercise) creates the folder for you. The PowerShell route creates it above, in your own profile, which other users cannot write to by default (est.).

Why `moto`? The obvious local S3 server, MinIO, was archived: on **2026-10-22** its repository README says it is no longer maintained and the community edition is distributed as source only, under the AGPL v3 license. The same README says no pre-compiled binaries are provided for the community edition. So the lab uses [`moto`](https://docs.getmoto.org/) (Apache-2.0, from PyPI), which implements the S3 calls the lab needs. It is a test double, not a storage product: it accepts any credentials, keeps data in memory, and applies bucket policies only in a limited way, which is why the lab's policy check is a separate toy.

### Exercise 1: start two tenants on loopback

**Predict.** Two servers on two different ports: can the one on port 5101 see a bucket you create on port 5102?

**Do.**

```bash
chmod +x start_tenants.sh
./start_tenants.sh up
```

```powershell
# est.: not run. The script is Bash; on Windows run it from WSL 2, or start the servers by hand:
python -m venv "$env:LAB_WORK\venv"
& "$env:LAB_WORK\venv\Scripts\pip" install -r requirements.txt
Start-Process "$env:LAB_WORK\venv\Scripts\python" -ArgumentList "-m","moto.server","-H","127.0.0.1","-p","5101" -WindowStyle Hidden
Start-Process "$env:LAB_WORK\venv\Scripts\python" -ArgumentList "-m","moto.server","-H","127.0.0.1","-p","5102" -WindowStyle Hidden
```

**Check.** The script prints:

```text
tenant a: up on http://127.0.0.1:5101
tenant b: up on http://127.0.0.1:5102
```

Tenant A plays the governance team (the source of record). Tenant B plays the analytics side (processing). They share nothing: separate server, separate data.

**Undo.** `./start_tenants.sh down` at the end of the page.

### Exercise 2: invented data, and two policies

**Predict.** A narrow policy and a broad one: which lets a stranger read the batch?

**Do.** Build the fake data (made at run time; no card number is typed anywhere in the repository) and print the policy comparison:

```bash
PY="$LAB_WORK/venv/bin/python"
"$PY" make_fake_data.py --out "$LAB_WORK/fake"
"$PY" tenants_setup.py --check-policies
```

```powershell
# est.: not run.
$PY = "$env:LAB_WORK\venv\Scripts\python.exe"
& $PY make_fake_data.py --out "$env:LAB_WORK\fake"
& $PY tenants_setup.py --check-policies
```

**Check.** Output from the author's run:

```text
narrow
  transfer role puts under the prefix : True
  transfer role puts outside it       : False
  a stranger account reads the batch  : False
  transfer role reads or deletes      : False False
  processor role reads and deletes    : True True
broad
  transfer role puts under the prefix : True
  transfer role puts outside it       : True
  a stranger account reads the batch  : True
  transfer role reads or deletes      : True True
  processor role reads and deletes    : True True
```

The same JSON a real bucket policy uses was evaluated by a 30-line toy. The broad policy also gives the stranger the batch, which is the mistake in the loop below.

**Undo.** Nothing to undo; the fake data is in your work folder.

### Exercise 3: set the boundary and the backstop

**Predict.** After you attach a policy and a lifecycle rule to tenant B's bucket and read them back, has anything been deleted?

**Do.**

```bash
"$PY" tenants_setup.py --data "$LAB_WORK/fake"
```

```powershell
# est.: not run.
& $PY tenants_setup.py --data "$env:LAB_WORK\fake"
```

**Check.**

```text
tenants ready: governance-extracts (A) and analytics-inbox (B)
policy and lifecycle read back from B:
 policy statements: 1
 lifecycle rule   : backstop-expire-inbound-after-1-day
```

Nothing is deleted. The lifecycle rule is *stored*; I did not observe `moto` running expiration, and it would not prove anything about AWS's timing if it did. The lesson is above: on a real bucket this rule is a backstop that runs when S3 gets to it.

**Undo.** None needed.

### Exercise 4: a push with rclone (optional)

**Predict.** `rclone check` compares by size and hash; what does it report after a clean copy?

**Do.** `rclone` reads its remotes from environment variables here, so no config file is written (the values are labels, not secrets, and `moto` ignores them):

```bash
export RCLONE_CONFIG_TA_TYPE=s3 RCLONE_CONFIG_TA_PROVIDER=Other RCLONE_CONFIG_TA_ENDPOINT=http://127.0.0.1:5101 RCLONE_CONFIG_TA_ACCESS_KEY_ID=lab-a RCLONE_CONFIG_TA_SECRET_ACCESS_KEY=lab-a-label RCLONE_CONFIG_TA_REGION=us-east-1
export RCLONE_CONFIG_TB_TYPE=s3 RCLONE_CONFIG_TB_PROVIDER=Other RCLONE_CONFIG_TB_ENDPOINT=http://127.0.0.1:5102 RCLONE_CONFIG_TB_ACCESS_KEY_ID=lab-b RCLONE_CONFIG_TB_SECRET_ACCESS_KEY=lab-b-label RCLONE_CONFIG_TB_REGION=us-east-1
rclone copy --dry-run ta:governance-extracts/batch/2026-10/ tb:analytics-inbox/batch/2026-10/
rclone copy ta:governance-extracts/batch/2026-10/ tb:analytics-inbox/batch/2026-10/
rclone check ta:governance-extracts/batch/2026-10/ tb:analytics-inbox/batch/2026-10/
```

```powershell
# est.: not run. Same variables, set with $env:NAME = "value"; the rclone commands are identical.
$env:RCLONE_CONFIG_TA_TYPE="s3"; $env:RCLONE_CONFIG_TA_PROVIDER="Other"; $env:RCLONE_CONFIG_TA_ENDPOINT="http://127.0.0.1:5101"
$env:RCLONE_CONFIG_TA_ACCESS_KEY_ID="lab-a"; $env:RCLONE_CONFIG_TA_SECRET_ACCESS_KEY="lab-a-label"; $env:RCLONE_CONFIG_TA_REGION="us-east-1"
# repeat for TB with port 5102, then run the three rclone commands above.
```

**Check.** The author's run printed `Transferred: 5 / 5, 100%` for the copy and `0 differences found` and `5 matching files` for the check. (`rclone mirror` does not exist; `copy` and `sync` do. `sync` makes the destination identical, which **deletes** extra files there, so use `copy` unless you mean it. `mc mirror` is the MinIO client's equivalent; it was not installed on the author's machine and was not run.)

**Undo.** `rclone delete tb:analytics-inbox/batch/2026-10/` and confirm `rclone lsf tb:analytics-inbox/batch/2026-10/` is empty (it was, in the author's run).

### Exercise 5: the monthly job, a dry run, an error and the manual path

**Predict.** If the verify step finds a mismatch, should the job still purge? What should it do instead?

**Do.** Run each in order. The job exits 0 on success and 2 on failure.

```bash
J="$PY monthly_job.py --work $LAB_WORK/job"
$J --dry-run
$J --inject-error verify;  echo "exit=$?"
$J --inject-error purge;   echo "exit=$?"
$J --sweep --dry-run
$J --sweep --force
$J;                        echo "exit=$?"
```

```powershell
# est.: not run.
function J { & $PY monthly_job.py --work "$env:LAB_WORK\job" @args }
J --dry-run
J --inject-error verify;  "exit=$LASTEXITCODE"
J --inject-error purge;   "exit=$LASTEXITCODE"
J --sweep --dry-run
J --sweep --force
J;                        "exit=$LASTEXITCODE"
```

**Check.** From the author's run (times trimmed):

```text
DRY RUN: would copy 5 object(s) to analytics-inbox, verify, scan, purge
ALERT monthly job failed: verify: 1 object(s) differ; NOT purging, data stays for a human     exit=2
ALERT monthly job failed: purge: simulated outage while deleting from tenant B                exit=2
sweep done, 5 object(s) remain in tenant B                          (the dry sweep)
ALERT sweep purged 5 overdue object(s); find out why the job did not
sweep done, 0 object(s) remain in tenant B
outcome: ok {... "verify": {"checked": 5, "mismatches": 0}, "scan": {"findings": 2}, "purge": {"remaining": 0}}     exit=0
```

Read it as the monthly story. The first failure keeps the data, because deleting after a failed verify destroys the evidence. The second failure leaves five sensitive objects in tenant B past their working day; the alert fired, and a human (you) runs the documented manual path: `--sweep --dry-run` to see, `--sweep --force` to purge, then investigate. The last run is the next scheduled attempt succeeding. `evidence.jsonl` in the work folder has one line per run with counts and times only. The `--force` flag is deliberately a human decision, because forcing past a legal hold is not something a script should decide.

What the script does **not** do, and a production job must: send the alert somewhere a person sees it (it writes a file), check for a legal hold before purging, use a real transfer role, and run under a scheduler. A cron line to run it monthly would be `0 3 1 * * ...` (shown, not installed); on Windows, Task Scheduler (est.).

**Undo.** `rm -rf "$LAB_WORK/job"` and `rm -rf "$LAB_WORK/fake"` (check `echo "$LAB_WORK"` first so the path is yours).

### Exercise 6: a toy DLP scanner

**Predict.** The fake data holds Luhn-valid card numbers, one near miss that fails the checksum, a part number shaped like the fake ID, and a fake mailbox. Which findings do you expect at the default threshold?

**Do.**

```bash
"$PY" dlp_scan.py "$LAB_WORK/fake"; echo "exit=$?"
```

```powershell
# est.: not run.
& $PY dlp_scan.py "$env:LAB_WORK\fake"; "exit=$LASTEXITCODE"
```

**Check.** The author's run (the numbers are masked, only the last two characters survive):

```text
FINDING batch/parts.txt:1: fake_member_id=**********ZZ
FINDING batch/payments.txt:1: card_candidate=**************97
FINDING batch/payments.txt:2: card_candidate=*****************10
FINDING mail/outbox.mbox#msg2: fake_member_id=**********ZZ, card_candidate=**************58
FINDING mail/outbox.mbox#msg4: fake_member_id=**********ZZ, fake_member_id=**********ZZ, fake_member_id=**********ZZ
5 finding(s)
exit=1
```

The "tracking number" line with the failed checksum was not reported: that is the **validator**. The CSV rows each contain one fake ID and an email, and did not match: one hit is below the **threshold** of 2. `parts.txt` is a **false positive**: a catalog part number plus the dictionary word "card" tripped the rule. Mail is read per message (`.mbox`), the way a real email DLP reads a message and not a line.

**Undo.** None; the scanner only reads.

### Exercise 7: tune a false positive, and break the threshold

**Predict.** Lowering the threshold to 1: more findings or fewer? Adding an allowlist entry for the part number: what changes?

**Do.**

```bash
"$PY" dlp_scan.py "$LAB_WORK/fake" --threshold 1 | tail -1
"$PY" dlp_scan.py "$LAB_WORK/fake" --threshold 1 --allow QX-123456-ZZ | tail -1
"$PY" dlp_scan.py "$LAB_WORK/fake" --allow QX-123456-ZZ | tail -1
```

```powershell
# est.: not run.
& $PY dlp_scan.py "$env:LAB_WORK\fake" --threshold 1 | Select-Object -Last 1
& $PY dlp_scan.py "$env:LAB_WORK\fake" --threshold 1 --allow QX-123456-ZZ | Select-Object -Last 1
& $PY dlp_scan.py "$env:LAB_WORK\fake" --allow QX-123456-ZZ | Select-Object -Last 1
```

**Check.** The author's run: `17 finding(s)`, then `16 finding(s)`, then `4 finding(s)`. A threshold of 1 flags every CSV row (17 findings, mostly noise: a reviewer would stop reading); the allowlist removes the known harmless part number; the default threshold plus the allowlist leaves the four real ones. That is tuning: each knob trades misses against noise. An allowlist is also an attack surface: a value on it is **never** reported, so each entry needs an owner and a reason.

**Undo.** None.

### Stop the lab

```bash
./start_tenants.sh down
```

```powershell
# est.: not run.
Get-Process python | Where-Object { $_.Path -like "$env:LAB_WORK*" } | Stop-Process
```

## Optional: your own cloud accounts (a pointer, with cost first)

This section is a pointer, not a walkthrough: I did not build it, and this project takes no AWS action here. It uses **your own** accounts and **your own** provider bill. The reading and the free path above are free and always will be.

> **Cost box. Read this before you create anything.**
>
> **What is estimated.** Nothing here is priced from this repository's tables. [`docs/cost-prices/aws.json`](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/cost-prices/aws.json) (retrieved 2026-10-16, region `us-east-1`) prices instances, public IPv4 addresses and EBS volumes, and says in its own words it does not price "data transfer, logging, snapshots, anything created outside OpenTofu". It has **no S3, KMS, CloudTrail or replication prices**, so I give none. DigitalOcean Spaces, as the project's [cost page](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/cost.md) records (read 2026-10-11): $5 a month for 250 GiB stored and 1 TiB outbound transfer per account, then $0.02 per GiB stored and $0.01 per GiB out. Read your provider's current pricing page before you build.
>
> **If you forget it.** The Spaces figure is the only one I can state: about **$0.17 a day** ($5 divided by 30, est.) and **$5 a month** per account at the base plan, per the cost page, and, I expect, a Space is charged while it exists whether or not it holds data (est.; I did not read that). For AWS I cannot give a figure; read the S3, KMS and CloudTrail pricing pages, and note that data events and replication are billed features.
>
> **Not covered by this estimate.** Request charges, replication, KMS key and request charges, CloudTrail data events, cross-region or internet transfer, and anything you create by hand.
>
> **A spend alert is not a spending cap.** It sends an email; it does not stop anything. Set one first: [How money works in the cloud](How-Money-Works-in-the-Cloud.md#1-a-billing-alert-before-anything-else).
>
> **Teardown first.** Empty, then delete, each bucket (a versioned bucket must have every version and delete marker removed), delete the roles and keys, then check the billing page the next day. Destroy in reverse of the build order below.
>
> **You can stop at any piece.** The free local lab covers the same ideas for $0.

| Piece | Depends on | Cost | Build order | Destroy order | Teardown proof |
|---|---|---|---|---|---|
| Account B (destination) with its own billing alert | none | $0 to open (est.) | 1 | 6 | Account closed or billing page shows no active resources |
| Destination bucket, encryption on, no public access | account B | not priced here | 2 | 4 | `aws s3api head-bucket` returns not found (est.) |
| Transfer role in account A, write-only, one prefix | account A | $0 (est.) | 3 | 3 | `aws iam get-role` returns NoSuchEntity (est.) |
| Cross-account bucket policy on the destination | bucket, role | $0 (est.) | 4 | 2 | Policy removed with the bucket |
| Lifecycle backstop rule | bucket | not priced here | 5 | 1 | Gone with the bucket |
| Audit trail for data events | bucket | not priced here | 6 | 5 | Trail deleted |

Prices from `docs/cost-prices/aws.json`, retrieved 2026-10-16, which lists none of these pieces; the rows say so instead of guessing. The AWS walkthrough for the cross-account policy is the page in the register. Do this only in **personal** accounts you own, never an employer's, and never with real personal data: use the fake data from Exercise 2.

## Build, break, detect, evade, defend

The same loop as the [labs](Labs-Break-It-on-Purpose.md), applied to a cross-account flow. Reason through the break and the evade on paper or in the free lab; none of it needs a real target.

- **Build.** A transfer role that can write one prefix, a destination policy that names only that role, a purge job that verifies and alerts, a lifecycle rule as backstop (Exercises 2 to 5).
- **Break.** Someone "fixes" a failing transfer by granting `Principal: "*"` and `s3:*` on the destination (the broad policy in Exercise 2). Any account can now read the batch, and the policy looks like a normal one in a long list.
- **Detect.** Look in the places that record requests: the provider's audit log (on AWS, CloudTrail data events for object-level calls, if enabled), the bucket's server access logs (best effort, per AWS), and a periodic review of policies for wildcard principals. Alert on a read from an account that is not on the list, and on any change to the bucket policy. The [mini SOC](Build-Your-Own-Mini-SOC.md) page shows how to turn a log line into an alert.
- **Evade.** Someone with legitimate access to the data takes it out in pieces: small files, compressed archives, base64-encoded or lightly changed text, so a pattern like the lab's no longer matches. The toy scanner sees only plain text; it would miss all of these. This is why DLP vendors invest in decoding, file-type detection and exact data match, and why none of them catch everything (est.).
- **Defend.** Layers, because each fails differently: least-privilege roles and no wildcards (so there is less to take), DLP on the egress paths that carry the data (email and web, with the false-positive tuning above), egress controls (the destination can only reach what it must), short retention (less to take next month), alerts on policy changes and on unusual volume, and a review queue where a human decides.

### Flip the board

Now defend from the other seat. You are the reviewer who gets the monthly job's pull request. Ask: Does the role name a prefix or a whole bucket? Is there a wildcard principal anywhere? Where does the failure alert go, and who reads it? What happens if the job *succeeds* but deletes nothing? Is there a legal-hold check? Who owns the allowlist entries? Then switch to the person trying to leak: which of your tools would see a base64-encoded CSV, and which would see nothing? The answers are your work list.

## Threat model

A short model in the style of the [Threat model](Threat-Model.md) page. Assets: the batch (sensitive), the transfer credentials, the policies, the purge evidence. Trust boundary: between the two accounts, and between the job and its scheduler.

| Threat | Likelihood and impact (est.) | Control | How to verify |
|---|---|---|---|
| Overly broad cross-account policy exposes the batch | Medium, high | Named role, one prefix, no wildcard principal; policy review in change control | Read the policy; toy evaluator in Exercise 2; periodic audit |
| Transfer credential stolen | Medium, high | Short-lived role session, secrets manager, write-only scope | Credential age and last-used review |
| Purge fails silently, data kept past its deadline | Medium, high | Explicit job with verify, alert on failure and on silence, lifecycle as backstop, overdue sweep | Fail the job on purpose (Exercise 5); alert reaches a person |
| Purge deletes data under a legal hold | Low, high | Hold check before purge; Object Lock or hold flag; approval for override | Test with a held object |
| Data exfiltrated in encoded or chunked form | Medium, high | DLP on egress, exact data match, egress controls, volume alerts | Red-team the rule with encoded fake data you made |
| Staged extract left on disk | Medium, medium | One controlled location, purge after run, verify | Listing of the staging path after a run |
| Allowlist abused to hide a leak | Low, medium | Owner and reason per entry, review | Diff of the allowlist in change control |
| Key deleted by mistake, copies unreadable | Low, high | Key deletion waiting period and approval (est.) | Read the key's deletion policy |

**Residual risk.** A permitted insider with a good reason to touch the data can still copy it in a way a rule does not recognize; DLP reduces and records that risk, it does not remove it. Provider-held backups and replicas of deleted data are outside your control and covered only by contract (est.).

## Checkpoint

You are done when you can say, without looking:

- What a cross-account permission needs on both sides, and why that is two places to check.
- Why a one-day lifecycle rule is not a 24-hour purge, and what you would build instead.
- What a legal hold does to a purge job.
- What each of dictionary, validator, threshold, exact data match and allowlist is for, and what each costs in misses or noise.
- What Twingate documents (access control) and does not document (DLP), who said it matters to enterprises, and why that is a category difference and not an insult.

## Common mistakes

- Setting a lifecycle rule and calling the data "purged within a day".
- Granting `Principal: "*"` to stop a transfer failing on a Friday.
- Purging after a failed verify, which destroys the only evidence.
- A job that logs "done" without checking the listing is empty.
- An alert that writes to a file nobody reads.
- Loading real personal data into a lab "just to test".
- Treating a DLP tool as finished when it is installed; the tuning is the work.

## Claims register

All read-only requests; retrieved **2026-10-22** unless stated. "Read" means I read the page text that day. Zscaler's help site renders through JavaScript, so those pages were read from the JSON the site itself fetches (`https://help.zscaler.com/zapi/fetch-data?url_alias=/zia/<page>`), which carries the same article text.

| Claim | Source | Status |
|---|---|---|
| A bucket owner can grant another account permissions; the other account can delegate to its users; granting to roles is the better practice | [AWS, Example 2: Bucket owner granting cross-account bucket permissions](https://docs.aws.amazon.com/AmazonS3/latest/userguide/example-walkthroughs-managing-access-example2.html) | Read |
| Replication copies objects asynchronously across buckets, in the same or different accounts; S3 RTC targets 99.99 percent of new objects within 15 minutes | [AWS, Replicating objects](https://docs.aws.amazon.com/AmazonS3/latest/userguide/replication.html) | Read |
| Lifecycle days are added to the creation time and rounded up to the next midnight UTC; expiration is queued and processed asynchronously; no completion-time guarantee; delay of days or weeks possible; versioned buckets get a delete marker | [AWS, Expiring objects](https://docs.aws.amazon.com/AmazonS3/latest/userguide/lifecycle-expire-general-considerations.html), [Transitioning objects](https://docs.aws.amazon.com/AmazonS3/latest/userguide/lifecycle-transition-general-considerations.html), [Setting a lifecycle configuration (the delay section)](https://docs.aws.amazon.com/AmazonS3/latest/userguide/how-to-set-lifecycle-configuration-intro.html) | Read |
| Lifecycle event notifications exist and are the reliable way to confirm an expiration | [AWS, Expiring objects](https://docs.aws.amazon.com/AmazonS3/latest/userguide/lifecycle-expire-general-considerations.html) | Read |
| Object Lock: retention periods in governance or compliance mode, and legal holds with no expiry; compliance mode cannot be overridden by any user including root | [AWS, Object Lock](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html) | Read |
| Cross-account use of a KMS key needs the key policy and an IAM policy in the other account; effective only for cryptographic operations and a few key reads | [AWS KMS, Allowing users in other accounts to use a KMS key](https://docs.aws.amazon.com/kms/latest/developerguide/key-policy-modifying-external-accounts.html) | Read |
| Server access logs are delivered on a best-effort basis | [AWS, Logging requests with server access logging](https://docs.aws.amazon.com/AmazonS3/latest/userguide/ServerLogs.html) | Read (heading and summary) |
| CloudTrail can log S3 data events | [AWS, Logging with CloudTrail](https://docs.aws.amazon.com/AmazonS3/latest/userguide/cloudtrail-logging.html) | Page fetched; the specific data-events passage not re-read, general statement est. |
| DataSync transfers data between AWS storage services and other locations | [AWS DataSync, What is DataSync](https://docs.aws.amazon.com/datasync/latest/userguide/what-is-datasync.html) | Read (overview only; not used in the lab) |
| Spaces lifecycle: time-based expiration and incomplete multipart upload removal supported, tag-based rules not; S3-compatible; bucket policies page exists | [DigitalOcean Spaces, S3 compatibility](https://docs.digitalocean.com/products/spaces/reference/s3-compatibility/), [Configure lifecycle rules](https://docs.digitalocean.com/products/spaces/how-to/configure-lifecycle-rules/) (last verified 13 Jul 2026 per the page) | Compatibility page read; lifecycle page header read, timing semantics not read |
| Spaces $5 a month for 250 GiB and 1 TiB out, then $0.02 per GiB and $0.01 per GiB | [`docs/cost.md`](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/cost.md) (prices read 2026-10-11) | Read in this repository |
| AWS price table has no S3 or KMS prices and does not price data transfer or logging | [`docs/cost-prices/aws.json`](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/cost-prices/aws.json) (retrieved 2026-10-16) | Read in this repository |
| MinIO repository: no longer maintained; AGPL v3; community edition is source only | [MinIO README](https://github.com/minio/minio/blob/master/README.md); GitHub API showed the repository archived, AGPL-3.0 | Read |
| `moto` is Apache-2.0, version 5.2.4; its S3 policy enforcement is basic, takes only `Principal: *` statements and ignores conditions; implements lifecycle, policy, Object Lock and legal-hold calls | [PyPI moto](https://pypi.org/project/moto/), [moto S3 docs](https://docs.getmoto.org/en/latest/docs/services/s3.html) | Read; the lab ran against 5.2.4 |
| Zscaler DLP: policy with engines; monitor or block; forwards to third-party DLP over ICAP and does not take ICAP responses | [About Data Loss Prevention](https://help.zscaler.com/zia/about-data-loss-prevention) | Read |
| Zscaler dictionaries: predefined (modifiable, clonable) and custom (patterns, phrases, exact data match) | [About DLP Dictionaries](https://help.zscaler.com/zia/about-dlp-dictionaries) | Read |
| Zscaler Outbound Email DLP: mail routed over SMTP to a smart host; inspects subject, body, attachments; adds headers; the mail system enforces | [What Is Zscaler Outbound Email DLP?](https://help.zscaler.com/zia/what-zscaler-outbound-email-dlp) | Read |
| Zscaler Index Tool: a VM (AWS, Azure or on premises) used to create EDM and IDM index templates; automatically updated; about one hour unavailable per upgrade | [About the Index Tool](https://help.zscaler.com/zia/about-index-tool) | Read |
| EDM: templates from a CSV in the Index Tool, up to 64 templates, cell counts affect VM memory, apply to custom dictionaries and engines | [About Exact Data Match](https://help.zscaler.com/zia/about-exact-data-match), [Creating an Exact Data Match Template](https://help.zscaler.com/zia/creating-exact-data-match-template) | Read |
| EDM creation steps (browse to the VM, log in with admin credentials, drag in a CSV, set data types, one or two primary fields); card type gets a Luhn check | [Creating an Exact Data Match Template](https://help.zscaler.com/zia/creating-exact-data-match-template) | Read |
| Zscaler recommends designing EDM templates so records are indexed once and re-indexing is avoided | [Understanding Exact Data Match Index Templates](https://help.zscaler.com/zia/understanding-edm-index-templates) | Read |
| IDM fingerprints documents so complete or partial copies are matched | [About Indexed Document Match](https://help.zscaler.com/zia/about-indexed-document-match) | Read |
| No command-line, API or scheduled-run mode for the Index Tool was found in the pages above | Same pages | Absence in the pages I read only; the maintainer's statement that automation is possible is his, unverified here (**est.**) |
| Zscaler API documentation exists | [automate.zscaler.com](https://automate.zscaler.com/docs/api-reference-and-guides/overview) | Page fetched, **not read**; whether it covers index automation is unverified |
| Twingate: access-control product; docs list DNS filtering and DoH under Internet Security; encryption between clients and connectors such that no third party, including Twingate, can decrypt | [Internet Security Overview](https://www.twingate.com/docs/internet-security), [Encryption in Twingate](https://www.twingate.com/docs/how-encryption-works-in-twingate) | Read |
| Twingate can sync audit, network and DNS-filtering logs to a customer's S3 bucket every 5 minutes, Business and Enterprise plans only | [Syncing Data to AWS S3](https://www.twingate.com/docs/syncing-data-to-s3) | Read |
| No DLP or content-inspection page found in Twingate's documentation | The docs navigation and pages above | Absence in the pages I read; check current docs |
| "Twingate does not have it, and enterprises value it" | The maintainer, 2026-10-22 | His statement |
| TLS inspection mechanics and privacy costs | General practice | **est.**, no vendor page read |
| `rclone` v1.60.1 copy and check against S3-compatible servers using environment-variable remotes | Ran on 2026-10-22 | Observed |

## Where to next

[Enterprise identity and secrets at scale](Enterprise-Identity-and-Secrets-at-Scale.md) is the next step: the roles and secrets this page used without building. For the access half of a cross-boundary flow, [Telemetry crosses the trust boundary](Telemetry-Crosses-the-Trust-Boundary.md).
