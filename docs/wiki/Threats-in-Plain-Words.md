# Threats in plain words: vulnerabilities, exploits, phishing, malware and compliance

Side page to the start-from-zero pages. Read it at core step 11 ([Why ZTNA and not a VPN](Why-ZTNA-Not-a-VPN.md)) if "CVE-2018-13379" or "exploited" reads like noise, or at any point you meet these words and want each one told apart, with a real, dated case. Next: [Threat model](Threat-Model.md).

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

> **Status: written from public sources read on 2026-10-22; the Bash exercises were run once on Linux on that date; the PowerShell lines were not run.** Every real case below names the page it came from and the date I read it, in the claims register at the end. Anything I could not read is marked **est.** (estimate) and is a guess to check; the one source I could not open is named in the register. Trust what your terminal prints over what this page says: public lists such as the CISA catalog change every few days, so your counts will differ from mine. Cost: $0. There is no hands-on path that uses your own cloud account, hardware or provider bill; the reading and the exercises are free and always will be. This page never asks you to run an exploit, build malware or touch a computer you do not own. The project's real spending lives on the [cost page](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/cost.md).

> **Prerequisites.** Core step 11 helps, because that is where the CVE number below first shows up, but it is not required. You can open a terminal ([Git from zero](Git-From-Zero.md#what-a-terminal-is) shows how) and have `python3` and `curl` (Bash) or PowerShell 7 for the exercises. For the detection side of every threat here, read [Logs, SIEM and detection basics](Logs-SIEM-and-Detection-Basics.md) first; [Cloud telemetry: what and why](Cloud-Telemetry-What-and-Why.md) and [Build your own mini SOC](Build-Your-Own-Mini-SOC.md) go further. About 90 minutes for the reading and the four exercises (est.).

## What you will be able to do

- Say in one sentence what a vulnerability, an exploit, a patch, a zero-day, phishing, malware, ransomware and lateral movement are, and give one real, dated case for each.
- Read a CVE record field by field, and explain what the sentence "Fortinet FortiOS SSL VPN, CVE-2018-13379" from core step 11 is telling you.
- Say what a CVSS score measures, what it leaves out, and why two honest scorers can give one CVE two different numbers.
- Say what the CISA Known Exploited Vulnerabilities catalog (KEV) adds that a score does not.
- Say what SOC 2, ISO 27001 and the NIST frameworks are for, and why holding none of them does not make a company insecure, and holding one is evidence about a stated scope, not proof of security.
- Take a made-up list of your own devices and check it against a public list of exploited vulnerabilities, then decide which entries need a human to read the record.
- Map each word to the [STRIDE and ATT&CK](Threat-Frameworks-STRIDE-ATTACK-ATLAS.md) vocabulary, and to the threats in this project's [threat model](Threat-Model.md).

## The eight words, with one real case each

The cases are all public, dated and from a primary source (a government advisory, a vendor's own post or a vendor's security bulletin). They are here to show how each word looks in a real report, not to teach anyone how to do any of it. Where a case is a long, messy incident, I use one sentence from the source and link the rest.

### Vulnerability

**A vulnerability is a weakness in software, hardware or a procedure that someone could use to do something the owner did not intend.** NIST's glossary words it as a weakness in a system, its security procedures, internal controls or implementation that could be exploited or triggered by a threat source.

Case: **CVE-2018-13379**, in Fortinet's FortiOS (the operating system of a family of firewalls and VPN gateways). The U.S. National Vulnerability Database (NVD) record, first published on 2019-06-04, says a path traversal flaw in the SSL VPN web portal lets an unauthenticated attacker download system files through specially crafted web requests. "Path traversal" means a program that was meant to serve files from one folder can be tricked into serving files from other folders. "Unauthenticated" means no login was needed. This is the same CVE core step 11 cites; the section [Reading a CVE record](#reading-a-cve-record-the-one-from-core-step-11) goes through it line by line. Source: [NVD record](https://nvd.nist.gov/vuln/detail/CVE-2018-13379), read 2026-10-22.

Note what the word does *not* say. A vulnerability is a possibility, not an event. Some vulnerabilities are used against real targets and many are never seen exploited (est.); the useful questions are which are being used now, and whether you run the affected thing (see [KEV](#kev-the-list-of-what-is-being-exploited-now)).

### Exploit

**An exploit is the code, data or technique that turns a vulnerability into an actual effect.** The vulnerability is the unlocked window; the exploit is climbing through it. (I wrote this definition in plain words; NIST's glossary did not return a separate entry for the word when I looked, so the sentence is mine and marked **est.** as a definition, while the case is read from sources.)

Case: in an advisory last revised on 2020-10-24, the U.S. Cybersecurity and Infrastructure Security Agency (CISA) reported "multiple cases" where the same CVE-2018-13379 "has been exploited to gain access to networks". After the first foothold, the same advisory says, the actors exploited a second flaw, CVE-2020-1472, to compromise all the Active Directory identity services in the victim network. Source: [CISA advisory AA20-283A](https://www.cisa.gov/news-events/cybersecurity-advisories/aa20-283a), read 2026-10-22. In 2021, a joint advisory from the FBI, CISA and others again told readers to patch CVE-2018-13379: [AA21-321A](https://www.cisa.gov/news-events/cybersecurity-advisories/aa21-321a), last revised 2021-11-19, read 2026-10-22.

### Patch

**A patch (also called a fix or an update) is a change from the maker that removes a vulnerability.** The gap between the patch being published and your copy of the software actually receiving it is where most real damage happens, which is why the next case matters.

Case: Fortinet's own advisory for CVE-2018-13379, number FG-IR-18-384, shows a published date of 2019-05-24 and says to upgrade to FortiOS 5.4.13, 5.6.8, 6.0.5 or 6.2.0 and above. As a temporary workaround it says the only option is to disable the SSL VPN service entirely. CISA did not add the CVE to its catalog of known-exploited vulnerabilities until 2021-11-03, more than two years after that advisory. The date CISA adds an entry is when it had reliable evidence, not necessarily when the first attack happened, so read it as "at least by then". Source: [Fortinet PSIRT advisory FG-IR-18-384](https://fortiguard.com/psirt/FG-IR-18-384), read 2026-10-22; the KEV date comes from the [CISA catalog data](https://www.cisa.gov/known-exploited-vulnerabilities-catalog), version 2026.10.21, read 2026-10-22. (The advisory page also carries a "Known Exploited: No" field as I read it; I did not find out how Fortinet fills that field and I do not rely on it. The CISA record is the evidence cited here.)

### Zero-day

**A zero-day is a vulnerability that is being used against targets before the maker has a patch, or before the maker knew it existed ("zero days" to prepare).** NIST's glossary defines a zero-day attack as one that exploits a previously unknown hardware, firmware or software vulnerability. The word is about the *attack timing*, not about how serious the flaw is.

Case: CISA and the FBI wrote that, beginning on 2023-05-27, the CL0P ransomware gang "began exploiting a previously unknown SQL injection vulnerability" (CVE-2023-34362) in Progress Software's MOVEit Transfer, a managed file-transfer product, and, through internet-facing MOVEit servers infected with a web shell, stole data from the databases behind them. "SQL injection" means input meant to be data is read as database commands; a "web shell" is a small program that lets someone run commands on a server through web requests. The advisory adds that the same group ran zero-day campaigns against two other file-transfer products in 2020 to 2021 and in early 2023. CISA added the MOVEit CVE to its catalog on 2023-06-02. Source: [CISA advisory AA23-158A](https://www.cisa.gov/news-events/cybersecurity-advisories/aa23-158a), June 2023, updated 2023-06-16, read 2026-10-22.

### Phishing

**Phishing is a message that pretends to be someone you trust in order to get you to hand over a secret or run something.** NIST's glossary (from its digital identity guidelines) describes it as a technique for acquiring sensitive data through a fraudulent solicitation in email or on a web site, in which the sender masquerades as a legitimate business or reputable person. The same trick over text messages is sometimes called smishing, and over the phone vishing.

Case: on 2022-08-04, Twilio, a communications company, learned of unauthorized access to some customer accounts. Its own report says employees received text messages that looked like they came from the IT department, saying a password had expired or a schedule had changed, with a link to a page that imitated Twilio's sign-in page; some employees entered their credentials and the attackers used them to reach internal systems and some customer data. Twilio also noted that the attackers seemed able to match employee names with phone numbers. Source: [Twilio incident report](https://www.twilio.com/en-us/blog/august-2022-social-engineering-attack), read 2026-10-22 (the page has been revised since; I read the current version). For why a typed code does not stop this and a security key tied to the real site's name does, read [Enterprise identity: SSO, SAML and OIDC](Enterprise-Identity-SSO-SAML-OIDC.md).

The email-specific attacks (business email compromise, look-alike domains, consent phishing, thread hijacking), the DNS records that make forging your domain harder, and a triage workflow are in [Email security: DNS records, gateways, API-driven protection, and running your own server](Email-Security-DNS-Gateways-and-API-Driven-Protection.md).

### Malware

**Malware is software built to do something unauthorized that harms the confidentiality, integrity or availability of a system.** NIST's glossary lists a virus, a worm, a Trojan horse and other code-based entities that infect a host, and notes that spyware and some adware count too.

Case: the SolarWinds Orion compromise that CISA described in alert AA20-352A (last revised 2021-04-15). CISA calls it a supply chain compromise of a library file (a DLL) in several versions of SolarWinds Orion, a network-management product: malicious code arrived inside what customers installed as a legitimate update. The malware in that file is named SUNBURST in CISA's analysis reports. CISA says the compromises began at least as early as March 2020. Source: [CISA alert AA20-352A](https://www.cisa.gov/news-events/cybersecurity-advisories/aa20-352a), read 2026-10-22. It is also a supply chain case (the Glossary has a row for the term): the customer's only "mistake" was installing a vendor's update.

### Ransomware

**Ransomware is malware that makes your files or systems unusable, usually by encrypting them, and then demands payment for the way back; many gangs also steal the data first and threaten to publish it.** CISA's definition is almost word for word that: malware designed to encrypt files on a device, so the files and the systems relying on them are unusable, with a demand for ransom in exchange for decryption, and a threat to sell or leak stolen data if the demand is not met. Source: [CISA Ransomware 101](https://www.cisa.gov/stopransomware/ransomware-101), read 2026-10-22.

Case 1: on 2021-05-11 (first version), CISA and the FBI wrote about a ransomware attack on a pipeline company in the United States, where criminals deployed DarkSide ransomware on the company's IT network. The advisory says there was no indication at that time that the operational-technology (OT) networks that run the physical pipeline had been directly affected, and describes DarkSide as ransomware-as-a-service: the developers take a share of the proceeds from "affiliates" who run the attacks. Source: [CISA advisory AA21-131A](https://www.cisa.gov/news-events/cybersecurity-advisories/aa21-131a), last revised 2021-07-08, read 2026-10-22.

Case 2, with a patch that existed first: the WannaCry ransomware spread in May 2017 through a Windows file-sharing (SMB) flaw. Microsoft had published the security update, bulletin MS17-010, on 2017-03-14, two months before. CISA's alert from 2017-05-12 says Microsoft released that update on March 14, 2017, and extra patches for older Windows versions on May 13, 2017. One of the bulletin's CVEs, CVE-2017-0144, is today in the CISA catalog with "known ransomware campaign use". Sources: [Microsoft bulletin MS17-010](https://learn.microsoft.com/en-us/security-updates/securitybulletins/2017/ms17-010) and [CISA alert on WannaCry](https://www.cisa.gov/news-events/alerts/2017/05/12/indicators-associated-wannacry-ransomware) (an archived page, last revised 2018-06-07), both read 2026-10-22. I did not read a source that says which specific CVE WannaCry used, so I do not claim it; I only report that the bulletin lists CVE-2017-0144 and that CISA's catalog marks that CVE as used in ransomware campaigns.

### Lateral movement

**Lateral movement is an attacker already inside one system moving to others on the same network to reach what they actually want.** MITRE ATT&CK, a public catalog of attacker behavior, describes it as the techniques adversaries use to enter and control remote systems on a network, often needing to explore the network and pivot through multiple systems and accounts. They might install their own remote-access tools or use legitimate credentials with native network tools, which is why it can look like normal administration. Source: [MITRE ATT&CK, Lateral Movement tactic](https://attack.mitre.org/tactics/TA0008/), read 2026-10-22.

Case: in the SolarWinds alert above, CISA says the adversary was heavily leveraging compromised or spoofed tokens for accounts for lateral movement, and that because valid accounts were in use, detecting it takes noticing actions outside a user's normal duties (the alert's example: an HR account has no reason to read the threat-intelligence database). That is the detection lesson of the whole page: lateral movement is hard to see by looking for "bad" software, because it often uses good tools and valid accounts. Source: [CISA alert AA20-352A](https://www.cisa.gov/news-events/cybersecurity-advisories/aa20-352a), read 2026-10-22. This project's own version of the same worry is threat T12 in the [threat model](Threat-Model.md#threats-controls-residual-risk), and its answer is segmentation: [DigitalOcean network and firewalls](DigitalOcean-Network-and-Firewalls.md).

## How the words connect

Real incidents chain these words. The chain below is the shape of the incidents in the cases above, not a recipe; every step has a defender-side question beside it.

| Stage | Word | What happened, in plain words | Question a defender asks |
|---|---|---|---|
| 1 | Phishing, or an exploit of an internet-facing service | The attacker gets a first foothold: a stolen password, or a flaw in a gateway | Is anything of mine reachable from the internet that should not be? Is sign-in tied to the real site? |
| 2 | Malware, or a web shell | Something the attacker controls now runs on a machine of yours | Would I notice a new program, a new scheduled job, a new outbound connection? |
| 3 | Lateral movement | The attacker looks for what is valuable and moves toward it | If this one machine fell, what else could it reach? |
| 4 | Ransomware, or data theft | The attacker uses the access to encrypt, steal and demand payment | Can I restore from a copy the attacker could not touch? |

The vulnerabilities and patches sit underneath this: they are why stage 1 and 3 are cheap for the attacker when something is unpatched.

Rough mapping to the frameworks on [Threat frameworks: STRIDE, ATT&CK and ATLAS](Threat-Frameworks-STRIDE-ATTACK-ATLAS.md). This table is my own teaching map, not an official one, so treat it as **est.**; the technique names were read on the MITRE site on 2026-10-22.

| Word | ATT&CK (tactic or technique) | STRIDE letter it most often lands on (est.) |
|---|---|---|
| Phishing | Initial Access tactic, Phishing technique | Spoofing (pretending to be someone) |
| Exploit of an exposed service | Initial Access, technique Exploit Public-Facing Application | Elevation of privilege, or Tampering |
| Exploit of an internal service | Lateral Movement, technique Exploitation of Remote Services | Elevation of privilege |
| Lateral movement | The Lateral Movement tactic | Elevation of privilege |
| Ransomware | Impact, technique Data Encrypted for Impact | Denial of service (and Tampering) |
| Zero-day, patch, vulnerability | Not techniques: they describe the flaw and its timing | Any |

## Reading a CVE record: the one from core step 11

[Why ZTNA and not a VPN](Why-ZTNA-Not-a-VPN.md#the-internet-facing-gateway-problem-is-not-hypothetical) says: "Fortinet FortiOS SSL VPN. CVE-2018-13379, a path traversal that read credential files off the device." Here is what each part of that sentence points at.

**CVE** stands for Common Vulnerabilities and Exposures. It is a numbering system: one flaw, one ID, so that a vendor, a scanner and a government list can all talk about the same thing. The ID has a year and a number (`CVE-2018-13379`: the year is when the ID was reserved or assigned, not necessarily when the flaw was found or fixed). An ID is handed out by an organization called a CNA (CVE Numbering Authority); for this one it was Fortinet itself, which the record shows. The CVE list says *that* a flaw exists and gives a short description. It is not a score, not a patch and not a statement that anyone exploited it.

**NVD** is the U.S. National Vulnerability Database. It takes each CVE and adds analysis: scores, the weakness type, and a list of affected products. Two organizations, then, can describe the same CVE and not agree on all the details, which Exercises 1 and 2 make visible.

Here are the fields in the NVD record for this CVE, as I read it on 2026-10-22.

| Field | What it said | How to read it |
|---|---|---|
| ID | CVE-2018-13379 | The shared name |
| Published | 2019-06-04 | When the public record appeared. The vendor's advisory was earlier, 2019-05-24 |
| Description | Path traversal in FortiOS SSL VPN web portal, affecting FortiOS 6.0.0 to 6.0.4, 5.6.3 to 5.6.7 and 5.4.6 to 5.4.12 and some FortiProxy versions; unauthenticated attacker; downloads system files with crafted web requests | The most useful part. "Affected versions" is how you decide whether *you* are touched. "Unauthenticated" and "web portal" tell you it can be reached from anywhere the portal is reachable |
| Weakness (CWE) | CWE-22 | The type of mistake. CWE is the Common Weakness Enumeration, a catalog of kinds of software flaw. CWE-22 is path traversal. Many different CVEs share one CWE |
| CVSS (NVD) | 9.8, vector `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H` | A severity score; see the next section |
| CVSS (Fortinet) | 9.1, vector `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:H` | The vendor's own score for the same flaw |
| CVSS version 2 (NVD) | 5.0, "Medium" | An older scoring system; shown for old CVEs and easy to misread as current |
| References | A Fortinet advisory (tagged Mitigation and Vendor Advisory), a second Fortinet advisory, and a pointer to the CISA catalog | The vendor advisory is where the fixed versions are. Go there before trusting a summary, including this one |
| CISA catalog fields | Added 2021-11-03; action due 2022-05-03; "Apply updates per vendor instructions" | Evidence the flaw was exploited in the wild; see KEV below |

The CVE Program's own JSON for the same ID (from `cveawg.mitre.org`, which I read on 2026-10-22) shows the assigner as `fortinet` and the state as published, with a "date reserved" of 2018-07-06. That is why the ID says 2018 though the public record is from 2019: the ID was reserved a year before it went public.

So, what core step 11 is telling you: a very old, very well known flaw in a product that sits on the edge of a network was used for years to steal credentials from devices whose owners had not installed a fix that existed from May 2019. The lesson there is about where such a gateway sits (open to the whole internet); the lesson on this page is how to read the record behind the sentence.

## CVSS: what it says, and what it does not

CVSS is the Common Vulnerability Scoring System, maintained by FIRST (a nonprofit forum of response teams). It turns a vulnerability's characteristics into a number from 0 to 10 and a text vector like `AV:N/AC:L/...` that spells out each input: attack vector (network, adjacent, local, physical), attack complexity, privileges required, user interaction, scope, and the impact on confidentiality, integrity and availability.

What the score is for: a shared, rough way to say how bad a flaw is in the abstract, so a team can sort a list of hundreds of findings.

What it is not, in FIRST's own words: CVSS Base scores "are designed to measure the severity of a vulnerability and should not be used alone to assess risk." (From FIRST's CVSS v4.0 user guide, read 2026-10-22.) The base score is independent of whether anyone is attacking it and of whether the affected thing exists in your environment. FIRST adds optional Threat and Environmental metrics for that.

Three things the CVE above shows:

- **Different scorers, different numbers.** NVD scored CVE-2018-13379 at 9.8; the vendor scored it 9.1. The only difference in the vectors is Integrity: NVD says High, Fortinet says None. Both are "Critical" under the usual bands. Exercise 2 finds that single letter.
- **Score is not exposure.** A 9.8 on a product you do not run does not matter to you. A 6.5 on the one internet-facing thing you do run may matter more.
- **Score is not "being attacked."** That is what the next two signals try to say. EPSS (Exploit Prediction Scoring System, also from FIRST) is a model that estimates the probability that a published CVE will be exploited in the wild in the next 30 days, published daily for every CVE. It is a prediction. KEV is a record of things that were exploited.

## KEV: the list of what is being exploited now

The Known Exploited Vulnerabilities catalog is a list kept by CISA of vulnerabilities for which it has reliable evidence of exploitation in the wild, which also have a CVE ID and clear remediation guidance. It is published as a web page and as a JSON file, with fields such as the date added, a required action, a due date for U.S. federal civilian agencies, and whether the CVE is "known" to be used in ransomware campaigns. CISA's page says it "strongly recommends all organizations" review the catalog and prioritize fixing what is on it, and that organizations should use it as one input to their own prioritization. As I read it, the page said the federal due dates are now set under a directive numbered BOD 26-04 (issued 2026-06-10), which carries forward the criteria of the earlier BOD 22-01; I did not read the directive itself. Source: [CISA Known Exploited Vulnerabilities page](https://www.cisa.gov/known-exploited-vulnerabilities) and [catalog data](https://www.cisa.gov/known-exploited-vulnerabilities-catalog), read 2026-10-22; the data file said version 2026.10.21 and 1,754 entries.

How to use it, and how not to:

- A KEV match is a strong reason to look *today*. Absence from KEV is not a clean bill of health: the list needs evidence, a CVE ID and a fix, and CISA says on its own page that exploitation evidence is only one of its criteria.
- A KEV entry names a product, not your version. Fifteen entries for "FortiOS" (the count on the day I tried) does not mean you are affected by fifteen; each is a record with its own affected versions.
- The "known ransomware use" field is a flag on the CVE, not a measure of how likely you are to be hit.

## What SOC 2, ISO 27001 and the NIST frameworks are for

These get called "compliance". **Compliance** means meeting a rule or standard that someone else can check. It is a different idea from security, which is how hard the system is to attack and how well you recover. They overlap, and they are not the same.

| Name | What it is | Who produces it | What it tells a reader |
|---|---|---|---|
| **SOC 2** | An audit report on the controls of a service organization (a company that holds other people's data or runs a service for them). The auditing standards belong to the AICPA, the U.S. professional body of CPAs. The criteria are the Trust Services Criteria for security, availability, processing integrity, confidentiality and privacy | A licensed CPA firm, for the company, after an examination | That an independent auditor looked at stated controls, over a stated scope and period, and what they found. It is often how one company asks another to prove its homework |
| **ISO/IEC 27001** | An international standard for running an information security management system: a repeatable process for finding risks, picking controls and improving. A company can be certified against it by an external certification body (**est.**; I could not open ISO's page) | ISO and IEC publish it; accredited bodies certify | That the company runs a managed process that an outside body checked, for a stated scope |
| **NIST Cybersecurity Framework (CSF) 2.0** | A U.S. government guide that sorts security work into outcomes (govern, identify, protect, detect, respond, recover) usable by any size of organization. NIST says the CSF does not prescribe how to achieve those outcomes | NIST, free to read | A common vocabulary for planning, no certificate |
| **NIST SP 800-53** | A catalog of security and privacy controls for information systems and organizations | NIST, free to read | A detailed menu of controls to pick from, not a pass or fail |

Sources (read 2026-10-22): the AICPA's [SOC suite of services page](https://www.aicpa-cima.com/resources/landing/system-and-organization-controls-soc-suite-of-services) and its [Trust Services Criteria page](https://www.aicpa-cima.com/resources/download/2017-trust-services-criteria-with-revised-points-of-focus-2022); [NIST CSWP 29, the CSF 2.0 document](https://nvlpubs.nist.gov/nistpubs/CSWP/NIST.CSWP.29.pdf) (the six-function list is from my reading of that document's structure and is **est.** until you check it); and [NIST SP 800-53 Rev. 5](https://csrc.nist.gov/pubs/sp/800/53/r5/upd1/final). ISO's own page for the standard returned an access-denied response to my tool, so the ISO row is general knowledge and marked **est.**

What to take from this, without absolutes:

- **Holding one does not make a company secure.** A report or certificate is evidence about a defined scope, controls and period. A flaw outside the scope, or something that changed after the audit, can still hurt you. The AICPA's own SOC page, as I read it on 2026-10-22, carried headlines about the credibility of "fast and easy" SOC engagements and about SOC 2 risks that peer reviewers are being told to address. That is the body that owns the standard saying quality varies, which is a good reason to read the report's scope and exceptions, not just ask whether it exists.
- **Holding none does not make a company insecure.** A small team can run strong controls and never pay for an audit, and a big company with every certificate can be breached. The absence of a report tells you "I cannot tell from this", and that is all it says.
- **Frameworks are a way to ask better questions.** "Which of the CSF's functions do we have nothing for?" is a useful question. "We are 'NIST compliant'" is usually a sentence to ask about: which framework, which version, which scope, assessed by whom, when?
- **For this project:** it follows no framework formally. It uses STRIDE and ATT&CK to think ([Threat frameworks](Threat-Frameworks-STRIDE-ATTACK-ATLAS.md)) and the NIST zero trust architecture document as a design reference ([Why ZTNA and not a VPN](Why-ZTNA-Not-a-VPN.md#how-this-repository-maps-to-nist-sp-800-207)). Nobody has audited it.

## Hands-on, free path: read public sources and your own made-up list

Nothing here exploits, scans or touches a computer you do not own. Exercises 1 and 3 read two public files: the NVD's record for one CVE, and CISA's catalog. Reading public data is not an attack on its publisher, but be polite: run each download once, keep the file, and work from your copy. Exercise 2 and the link-reading exercise are fully offline, and Exercise 4 asks you to read two web pages in a browser. The inventory is made up, built at run time and never committed.

Tools: `curl` and `python3` (Bash), or PowerShell 7 (`Invoke-RestMethod`, which is also built into Windows PowerShell 5.1 with slightly different defaults, **est.**). I ran every Bash command with Python 3.13 on Linux on 2026-10-22. PowerShell lines are written from the documentation and marked **not run**.

### Setup (Bash, once)

```bash
LAB="$(mktemp -d)" && cd "$LAB"   # a fresh scratch folder, remembered in $LAB
```

PowerShell (**not run**):

```powershell
$d = Join-Path ([IO.Path]::GetTempPath()) ("f11lab-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $d -ErrorAction Stop | Out-Null
Set-Location $d
```

### Exercise 1: read a CVE record

**Predict.** Before you look: will the record say who is affected, how severe it is, and where the fix is? Which of those three do you think the record itself actually contains?

**Do.** Download the NVD record once, then read it from your copy.

```bash
curl -s "https://services.nvd.nist.gov/rest/json/cves/2.0?cveId=CVE-2018-13379" -o cve.json
cat > read_cve.py <<'PY'
import json, sys
rec = json.load(open(sys.argv[1]))["vulnerabilities"][0]["cve"]
en = next(d["value"] for d in rec["descriptions"] if d["lang"] == "en")
print("id          :", rec["id"])
print("published   :", rec["published"][:10])
print("description :", en[:150] + "...")
for m in rec["metrics"].get("cvssMetricV31", []):
    print("CVSS 3.1    :", m["source"], m["type"], m["cvssData"]["baseScore"], m["cvssData"]["vectorString"])
print("weakness    :", [d["value"] for w in rec.get("weaknesses", []) for d in w["description"]][:1])
print("KEV added   :", rec.get("cisaExploitAdd", "not in KEV"))
print("references  :", len(rec["references"]), "(look for the tag Vendor Advisory)")
PY
python3 -I read_cve.py cve.json
```

PowerShell (**not run**):

```powershell
$r = Invoke-RestMethod "https://services.nvd.nist.gov/rest/json/cves/2.0?cveId=CVE-2018-13379"
$c = $r.vulnerabilities[0].cve
"id          : " + $c.id
"published   : " + $c.published.Substring(0,10)
"description : " + (($c.descriptions | Where-Object lang -eq "en").value.Substring(0,150)) + "..."
$c.metrics.cvssMetricV31 | ForEach-Object { "CVSS 3.1    : $($_.source) $($_.type) $($_.cvssData.baseScore) $($_.cvssData.vectorString)" }
"weakness    : " + $c.weaknesses[0].description[0].value
"KEV added   : " + $c.cisaExploitAdd
"references  : " + $c.references.Count
```

**Check.** On 2026-10-22 the Bash version printed the id, a published date of `2019-06-04`, the start of the description, two CVSS 3.1 lines (one from `psirt@fortinet.com`, scored 9.1, and one from `nvd@nist.gov`, scored 9.8), weakness `['CWE-22']`, a KEV date of `2021-11-03` and five references. NVD records are updated over time (this one's last-modified date was in June 2026), so a field may differ for you; the structure should not. The record says *what* is affected and *how bad* in the abstract. It does not say *where the fix is* in so many words: that is in the vendor advisory under References. Note that the record has no sentence about whether you are affected.

**Undo.** Nothing to undo; you only read a file. If the download fails with a rate-limit error, wait a minute and retry once.

### Exercise 2: decode two CVSS vectors and find the one letter that differs

**Predict.** The record gave two vectors for the same CVE, scored 9.8 and 9.1. Which metric do you expect to differ: how it is reached (attack vector), or what it breaks (impact)?

**Do.**

```bash
cat > vec.py <<'PY'
import sys
NAMES = {"AV": "attack vector", "AC": "attack complexity", "PR": "privileges required",
         "UI": "user interaction", "S": "scope", "C": "confidentiality",
         "I": "integrity", "A": "availability"}
def parse(v):
    return dict(p.split(":") for p in v.split("/")[1:])
a, b = parse(sys.argv[1]), parse(sys.argv[2])
for k, n in NAMES.items():
    note = "   <-- differs" if a[k] != b[k] else ""
    print(f"{n:22} {a[k]}  {b[k]}{note}")
PY
python3 -I vec.py "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:H" "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"
```

PowerShell (**not run**):

```powershell
$a = "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:H"; $b = "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"
$pa = $a.Split("/")[1..8]; $pb = $b.Split("/")[1..8]
for ($i = 0; $i -lt 8; $i++) { $note = if ($pa[$i] -ne $pb[$i]) { "   <-- differs" } else { "" }; "$($pa[$i])  $($pb[$i])$note" }
```

**Check.** Eight lines; only `integrity` differs (`N` in the first, `H` in the second). The two scorers agreed on everything about *how* it is reached (over the network, low complexity, no login, no user clicking) and disagreed on one impact. That one letter moves the score from 9.8 to 9.1, and both are "Critical". Lesson: the number is the output of judgments; the vector shows the judgments. The legend (`N` = network or none, `L` = low, `H` = high, `U` = unchanged) is in the [FIRST CVSS 3.1 specification](https://www.first.org/cvss/specification-document), **not read** for this page, so check the legend there before you rely on my letters.

**Undo.** Nothing.

### Exercise 3: check a made-up list of your own devices against CISA's catalog

This is the lesson's defender exercise: *which of my things does a known-exploited list touch?* The devices are invented; replace them with a few of your own once you see the shape.

**Predict.** For each made-up device below, will the catalog list any entries for its vendor and product? Then: if it does, does that mean this device is vulnerable?

**Do.** Download the catalog once, build the list, and match.

```bash
curl -s "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json" -o kev.json
cat > inventory.csv <<'CSV'
asset,vendor,product,version,internet_facing
lab-vpn-box,Fortinet,FortiOS,6.0.4,yes
file-share,Microsoft,Windows,10,no
log-viewer,Apache,Log4j2,2.14.1,no
travel-router,ExampleCorp,ExampleOS,1.0,yes
CSV
cat > match_kev.py <<'PY'
import csv, json, sys
kev = json.load(open(sys.argv[1]))["vulnerabilities"]
with open(sys.argv[2], newline="") as f:
    assets = list(csv.DictReader(f))
for a in assets:
    hits = [v for v in kev
            if a["vendor"].lower() in v["vendorProject"].lower()
            and a["product"].lower() in v["product"].lower()]
    print(f'{a["asset"]:14} facing={a["internet_facing"]:3}  KEV entries for {a["vendor"]} {a["product"]}: {len(hits)}')
    for v in sorted(hits, key=lambda v: v["dateAdded"], reverse=True)[:2]:
        print(f'    {v["cveID"]}  added {v["dateAdded"]}  ransomware={v["knownRansomwareCampaignUse"]}  {v["vulnerabilityName"][:60]}')
PY
python3 -I match_kev.py kev.json inventory.csv
```

PowerShell (**not run**):

```powershell
Invoke-WebRequest "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json" -OutFile kev.json
@"
asset,vendor,product,version,internet_facing
lab-vpn-box,Fortinet,FortiOS,6.0.4,yes
file-share,Microsoft,Windows,10,no
log-viewer,Apache,Log4j2,2.14.1,no
travel-router,ExampleCorp,ExampleOS,1.0,yes
"@ | Set-Content inventory.csv
$kev = (Get-Content kev.json -Raw | ConvertFrom-Json).vulnerabilities
foreach ($a in Import-Csv inventory.csv) {
  $hits = $kev | Where-Object { $_.vendorProject -like "*$($a.vendor)*" -and $_.product -like "*$($a.product)*" }
  "{0,-14} facing={1,-3}  KEV entries for {2} {3}: {4}" -f $a.asset, $a.internet_facing, $a.vendor, $a.product, @($hits).Count
  $hits | Sort-Object dateAdded -Descending | Select-Object -First 2 | ForEach-Object { "    $($_.cveID)  added $($_.dateAdded)  ransomware=$($_.knownRansomwareCampaignUse)  $($_.vulnerabilityName)" }
}
```

If the download is blocked where you are, make a three-row stand-in by hand with `cveID`, `vendorProject`, `product`, `dateAdded`, `knownRansomwareCampaignUse` and `vulnerabilityName` fields in a `vulnerabilities` list; the script only needs those.

**Check.** On 2026-10-22 (catalog version 2026.10.21), the first three devices each had entries (15 for Fortinet FortiOS, 178 for Microsoft Windows and 2 for Apache Log4j2) and the fourth had none, which is what you should get for a vendor and product that do not exist. Your counts will differ because the catalog grows. The answer to the second question is **no**: a match is a name match. `Microsoft Windows` matches every Windows entry for every version. It tells you where a human must read, not that the device is affected.

**Undo.** Nothing outside the scratch folder.

### Exercise 4: decide which assets the CVE touches (by hand, then write it down)

This exercise uses the lab from Exercise 3 and the CVE from Exercise 1.

**Predict.** The made-up device `lab-vpn-box` is FortiOS 6.0.4 and internet-facing. Does CVE-2018-13379 touch it? Does it touch `file-share` (Windows 10, no internet exposure)?

**Do.** Open the NVD record's description (Exercise 1) and the Fortinet advisory ([FG-IR-18-384](https://fortiguard.com/psirt/FG-IR-18-384)). Write one line per asset in a text file, in this form: asset, affected (yes, no or cannot tell), because, next step, due date. Work out `lab-vpn-box` against "FortiOS 6.0.0 to 6.0.4" and the upgrade target "6.0.5 or above".

**Check.** `lab-vpn-box` at 6.0.4 sits inside the affected range ("6.0.0 to 6.0.4"), the flaw is in the SSL VPN web portal, and the advisory says the product is affected only if the SSL VPN service is enabled, so the honest line is "affected if SSL VPN is on; upgrade to 6.0.5 or above, or turn the service off if you do not use it; do it now because it is internet-facing and on a known-exploited list". `file-share` does not run FortiOS, so this CVE does not touch it, though the Windows entries from Exercise 3 are a different question. If a device's vendor or version is not written down, the line is "cannot tell", and the next step is to find out; that is a real and common answer. The advisory says upgrade; it also says the only workaround is to disable the service, so do not invent a middle option like a firewall rule unless you have read a source that says it works.

**Undo.** Delete the scratch folder (below).

### Clean up

```bash
cd ~ && rm -r -- "$LAB"
```

`$LAB` is the scratch folder from the setup. If you opened a new terminal, `$LAB` is empty: do not run the line; delete the folder by hand. In PowerShell: `Set-Location ~; Remove-Item -Recurse $d` (not run).

## Spot the phishing lure (offline, no clicking)

You do not need an exercise that touches a real site to learn the habit. The one skill worth practicing is finding the real host a link goes to. This runs locally on a file of made-up addresses; nothing is opened or fetched.

**Predict.** Of these four made-up links, which ones really go to a company's own `example.com`?

**Do.**

```bash
cat > links.txt <<'TXT'
https://sso.example.com/login
https://sso.example.com.login-check.example.net/reset
https://example.com@login-check.example.net/reset
https://sso.examp1e.test/login
TXT
cat > real_host.py <<'PY'
import sys
from urllib.parse import urlsplit
for line in open(sys.argv[1]):
    url = line.strip()
    if not url:
        continue
    host = urlsplit(url).hostname
    print(f"{url}\n    real host: {host}   (last two labels: {'.'.join(host.split('.')[-2:])})")
PY
python3 -I real_host.py links.txt
```

PowerShell (**not run**):

```powershell
@("https://sso.example.com/login","https://sso.example.com.login-check.example.net/reset","https://example.com@login-check.example.net/reset","https://sso.examp1e.test/login") | ForEach-Object { $u = [uri]$_; "$_`n    real host: $($u.Host)" }
```

**Check.** Only the first goes to `example.com`. The second's real host ends in `example.net`: reading left to right misleads, the registered name sits at the *right-hand end* of the host, before the first single slash. The third hides the real host after an `@` (text before `@` is a username field, not the destination). The fourth swaps a digit `1` for the letter `l`. "Last two labels" is a teaching shortcut: in names like `example.co.uk` the registered name is the last three, so use it only as a first look (**est.**; the public suffix list is the real answer and I did not read it). The habit this builds is reading the host, which beats "does it look right?". It does not replace tying sign-in to the real site's name with a security key (see the identity page linked in the Phishing section).

**Undo.** Nothing; delete the folder with the rest.

## Build it, break it, detect it, evade it, defend it

The same loop as the [labs](Labs-Break-It-on-Purpose.md), at concept level only. No step below is an attack on anything real.

- **Build.** A one-page asset list for your home or lab: each device, its maker and product, the version, and whether it is reachable from the internet (the `inventory.csv` from Exercise 3 is that page). You cannot defend what you cannot list.
- **Break.** Add a device with old firmware to the list: a made-up router on a version years behind. You have not touched a real device; you have written down a row that, if it were real, would be the weakest one.
- **Detect.** Look the product up in a public list (Exercise 3), read the record (Exercise 1) and decide whether it touches you (Exercise 4). For a real network, detection also means logs and alerts that show someone *using* a flaw: see [Logs, SIEM and detection basics](Logs-SIEM-and-Detection-Basics.md), then [Cloud telemetry: what and why](Cloud-Telemetry-What-and-Why.md) and [Build your own mini SOC](Build-Your-Own-Mini-SOC.md).
- **Evade.** In words only: an attacker prefers the unpatched, internet-facing device because the work was already done. A known flaw has a public write-up and often public tools, so one method works against many owners at once, and it is far cheaper than finding a new flaw (the cases above show campaigns against many organizations that shared one product). They also prefer quiet: stolen valid credentials and ordinary admin tools, as in the lateral movement case, give a defender little that looks "bad" to catch. This page gives no working steps and none are needed to understand the economics. Defenders are tempted to hide a service, for example by moving SSH to another port, which is security through obscurity and fails for the same reason: see [What does not count as protection](Plan-for-Failure-Blast-Radius-and-Assuming-Breach.md#what-does-not-count-as-protection).
- **Defend.** A patch plan with owners and dates (who patches what, how fast for something on a known-exploited list, and what you do if there is no fix: turn the feature off, remove the device, or limit who can reach it); an exposure review (what is reachable from the internet, and whether it needs to be: this project's answer is [zero public inbound ports behind a zero trust gateway](Why-ZTNA-Not-a-VPN.md)); segmentation so one fallen machine does not reach the rest; a restore you have tested from a copy an attacker could not alter (see [Enterprise infrastructure differences](Enterprise-Infrastructure-Differences.md#high-availability-disaster-recovery-and-backups)); and sign-in that resists phishing.

**Flip the board.** You are now the person who must decide what to patch this week with time for five items out of five hundred. You have the CVSS score, the EPSS estimate, the KEV flag, whether the product is internet-facing, and what lives on the machine. Write down which two signals you would weight most and why, and what you would still not know. Then flip again: you are the vendor's incident team, and a researcher reports a flaw in a product with a customer base you cannot contact directly. What is the first thing a customer needs from you (an advisory with fixed versions, a workaround and a date), and what would make them miss it?

## Checkpoint

- Give one sentence each for vulnerability, exploit, patch, zero-day, phishing, malware, ransomware and lateral movement, without looking.
- Explain which word is about timing (zero-day), which is about the flaw (vulnerability), which is about the tool (exploit) and which is about the repair (patch).
- Read the fields of a CVE record aloud: ID, published, description, affected versions, weakness, scores, references. Say which one tells you whether *you* are affected.
- Explain why NVD and Fortinet scored the same CVE 9.8 and 9.1, and what CVSS does not tell you.
- Say what KEV adds to a score, and one thing it does not promise.
- Say what SOC 2, ISO 27001 and the NIST frameworks are for, and one reason a company with none is not automatically insecure and one reason a company with one is not automatically secure.

Answers are in the sections above.

## Claims register

Read 2026-10-22 with read-only requests to public pages (no logins), or run locally as stated. Items marked **est.** were not read.

| Claim | Source | Status |
|---|---|---|
| CVE-2018-13379: path traversal in FortiOS SSL VPN web portal; affected versions listed; unauthenticated; NVD published 2019-06-04; CWE-22; CVSS 3.1 of 9.8 (NVD) and 9.1 (Fortinet); CVSS 2.0 of 5.0; CISA fields added 2021-11-03, due 2022-05-03 | [NVD record](https://nvd.nist.gov/vuln/detail/CVE-2018-13379) via the NVD CVE API | Read; Exercise 1 run |
| CVE ID assigned by Fortinet, reserved 2018-07-06 | CVE Program record for the ID (`cveawg.mitre.org`) | Read |
| Fortinet advisory FG-IR-18-384, published 2019-05-24; fixed in FortiOS 5.4.13, 5.6.8, 6.0.5, 6.2.0 and above; only workaround is to disable SSL VPN; affected only if SSL VPN is enabled | [Fortinet PSIRT](https://fortiguard.com/psirt/FG-IR-18-384) | Read |
| CVE-2018-13379, CVE-2017-0144 and CVE-2023-34362 in CISA's catalog with dates added (2021-11-03, 2022-02-10, 2023-06-02), and the first two flagged as known ransomware use; catalog version 2026.10.21 with 1,754 entries | [CISA catalog JSON](https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json), downloaded in Exercise 3 | Read; Exercise 3 run |
| KEV criteria (reliable evidence, CVE ID, remediation guidance); CISA recommends prioritizing it; federal due dates under BOD 26-04 | [CISA KEV page](https://www.cisa.gov/known-exploited-vulnerabilities) | Read; the directive itself not read |
| CVE-2018-13379 exploited to gain access; second flaw CVE-2020-1472 then used against Active Directory (advisory last revised 2020-10-24) | [CISA AA20-283A](https://www.cisa.gov/news-events/cybersecurity-advisories/aa20-283a) | Read |
| Patch CVE-2018-13379 among the actions to take (advisory last revised 2021-11-19) | [CISA AA21-321A](https://www.cisa.gov/news-events/cybersecurity-advisories/aa21-321a) | Read |
| MOVEit: exploitation from 2023-05-27 of a previously unknown SQL injection (CVE-2023-34362), web shell, data theft; earlier zero-day campaigns by the same group | [CISA AA23-158A](https://www.cisa.gov/news-events/cybersecurity-advisories/aa23-158a) | Read |
| Twilio: 2022-08-04, SMS lure imitating an IT department and a sign-in page, stolen employee credentials | [Twilio incident report](https://www.twilio.com/en-us/blog/august-2022-social-engineering-attack) | Read (current revision) |
| SolarWinds Orion: supply chain compromise of a DLL, begun at least as early as March 2020; SUNBURST analysis report; compromised or spoofed tokens used for lateral movement | [CISA AA20-352A](https://www.cisa.gov/news-events/cybersecurity-advisories/aa20-352a) | Read |
| DarkSide ransomware on a pipeline company's IT network; no indication OT directly affected at that time; ransomware-as-a-service | [CISA AA21-131A](https://www.cisa.gov/news-events/cybersecurity-advisories/aa21-131a) | Read |
| WannaCry: update MS17-010 published 2017-03-14; extra patches 2017-05-13 | [Microsoft MS17-010](https://learn.microsoft.com/en-us/security-updates/securitybulletins/2017/ms17-010) and [CISA alert](https://www.cisa.gov/news-events/alerts/2017/05/12/indicators-associated-wannacry-ransomware) | Read; which CVE WannaCry used was not read, so not claimed |
| Ransomware definition | [CISA Ransomware 101](https://www.cisa.gov/stopransomware/ransomware-101) | Read |
| Vulnerability, malware, zero-day attack, phishing definitions | NIST glossary: [vulnerability](https://csrc.nist.gov/glossary/term/vulnerability), [malware](https://csrc.nist.gov/glossary/term/malware), [zero-day attack](https://csrc.nist.gov/glossary/term/zero_day_attack), [phishing](https://csrc.nist.gov/glossary/term/phishing) | Read |
| Exploit and patch, as defined in this page | My wording; NIST's glossary has a patch entry that I read but did not quote | Plain-words definitions, **est.** |
| Lateral movement definition; the Phishing, Exploit Public-Facing Application, Exploitation of Remote Services and Data Encrypted for Impact techniques, and the Initial Access, Lateral Movement and Impact tactics | MITRE ATT&CK pages: [Lateral Movement](https://attack.mitre.org/tactics/TA0008/), [Phishing](https://attack.mitre.org/techniques/T1566/), [Exploit Public-Facing Application](https://attack.mitre.org/techniques/T1190/), [Exploitation of Remote Services](https://attack.mitre.org/techniques/T1210/), [Data Encrypted for Impact](https://attack.mitre.org/techniques/T1486/) | Read |
| STRIDE letters per word | My own teaching map | **est.** |
| CVSS base score measures severity, not risk; has Base, Threat, Environmental and Supplemental groups | [FIRST CVSS v4.0 user guide](https://www.first.org/cvss/user-guide) | Read |
| CVSS 3.1 vector letter legend | [FIRST CVSS 3.1 specification](https://www.first.org/cvss/specification-document) | Not read; **est.** |
| EPSS estimates the probability a published CVE will be exploited in the next 30 days, published daily | [FIRST EPSS](https://www.first.org/epss/) | Read |
| SOC 2: a CPA-provided report on controls of a service organization; five Trust Services Criteria categories; AICPA headlines on "fast and easy" SOC credibility | AICPA [SOC suite page](https://www.aicpa-cima.com/resources/landing/system-and-organization-controls-soc-suite-of-services) and [Trust Services Criteria](https://www.aicpa-cima.com/resources/download/2017-trust-services-criteria-with-revised-points-of-focus-2022) | Read (headlines, not the articles) |
| ISO/IEC 27001 is a standard for an information security management system, certifiable by an external body | [ISO page](https://www.iso.org/standard/27001) | Not read: access denied (HTTP 403) on 2026-10-22; **est.** |
| NIST CSF 2.0 outcomes; "does not prescribe how outcomes should be achieved" | [NIST CSWP 29](https://nvlpubs.nist.gov/nistpubs/CSWP/NIST.CSWP.29.pdf) | Read the quoted sentence; the six-function list is **est.** |
| NIST SP 800-53 is a catalog of security and privacy controls | [NIST SP 800-53 Rev. 5](https://csrc.nist.gov/pubs/sp/800/53/r5/upd1/final) | Abstract read |
| PowerShell lines and Windows PowerShell 5.1 differences | Tool documentation | **Not run**; **est.** |
| Exercises 1 to 3 and the link-reading exercise in Bash: outputs described | Run on Linux with Python 3.13 on 2026-10-22 | Run 2026-10-22 |

Next: [Threat model](Threat-Model.md), step 19 of the core path on the [Reading order](Reading-Order.md) page.
