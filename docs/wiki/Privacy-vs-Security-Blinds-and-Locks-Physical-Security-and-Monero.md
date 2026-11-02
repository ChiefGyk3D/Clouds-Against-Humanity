# Privacy versus security: blinds and locks, with physical security and Monero as the example

<!-- BEGIN GENERATED PAGE NAV top: rewritten from docs/wiki/_nav.yaml by scripts/gen_wiki_nav.py; edit the manifest, not this block -->
[Home](Home.md) > [Track 3: Privacy, anonymity and cryptocurrency](Contents.md#track-3-privacy-anonymity-and-cryptocurrency) > Privacy versus security

Previous: [Privacy, security and anonymity](Privacy-Security-and-Anonymity-Three-Different-Things-and-Why-There-Is-No-Silver-Bullet.md) / Next: [Tor, I2P and the darknet without the myths](Tor-I2P-and-the-Darknet-Without-the-Myths.md)
<!-- END GENERATED PAGE NAV top -->

Side page to the start-from-zero pages. Read it after [The CIA triad](The-CIA-Triad-Confidentiality-Integrity-Availability.md) and [Threat model](Threat-Model.md), or at any point you have caught yourself saying "it is private, so it is secure" (or the other way round). It sets out one picture, blinds and drapes against locks and alarms, and uses it three ways: the overlap and the differences, Monero as a worked example, and the physical side of security, where a door, a drive in a drawer and a badge are all part of the system. It does not repeat the pages it points at. Next: the [lesson on Tor and I2P](Tor-I2P-and-the-Darknet-Without-the-Myths.md) and the [lesson on cryptography](Cryptography-Fundamentals-Symmetric-Asymmetric-Hashing-Certificates-and-Keys.md) (issues 358 and 360).

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

> **Status: unverified draft. Nothing on this page was run; everything was read.** On **2026-10-31** I downloaded and read the pages listed with their URLs in the [claims register](#claims-register): the Monero project's own pages, the European Commission's pages on the GDPR, the NIST security controls catalog (SP 800-53 Rev. 5, as published in NIST's machine-readable form), NIST's media sanitization guide (SP 800-88 Rev. 2), and two lockpicking-hobby pages. **Not read:** the text of the GDPR itself (its official site returned an empty response to my download), any court case or statute other than the ones those pages quote, the Locksport International pages (the site did not answer), and the Monero research papers. **Not run:** nothing, because the page has no script; the exercise is done by eye in your own room. **I touched no lock, no wallet and no network.** Nothing here is legal advice.

> **Prerequisites.** [The CIA triad](The-CIA-Triad-Confidentiality-Integrity-Availability.md) for the three properties, and [Hashing, encryption and keys](Hashing-Encryption-and-Keys.md) for what a key is. [Threat model](Threat-Model.md) helps. No account, no tools, no money. About 90 minutes with the exercise (est.).

> **Where this runs.** On paper and in your own room. The exercise looks at your own desk and your own accounts and changes nothing unless you decide to. Nothing on this page scans, probes, picks or attacks anything.

## What you will be able to do

- Say the difference between privacy and security in two sentences, using the blinds-and-locks picture, and give an example of each without the other.
- Name three places where the two overlap (encryption, access control, data minimization) and three where they pull apart.
- Explain why anonymity and accountability are in tension, and why a log can be both a lock and a window.
- Use Monero as an example: say what its privacy features are described as hiding by the project itself, and name the security properties its users still need (key custody, node trust, wallet and device security), without claiming more than the project's own pages say.
- Name the principles of the GDPR that bear on this lesson (purpose limitation, data minimization, storage limitation, integrity and confidentiality) and say where to look for your own jurisdiction.
- List the physical controls that protect a system (locks and key control, doors and access control, alarms, cameras, visitors, secure disposal, a clean desk), and the privacy cost of each.
- Explain why lockpicking is a common hobby in the field, and what the rules are before anyone touches a lock.
- Audit your own room or desk and sort each item into blind, lock or both.

## What the wiki already says (and the gap)

| Idea | Where it is today | The gap this page fills |
|---|---|---|
| Confidentiality, integrity, availability | [The CIA triad](The-CIA-Triad-Confidentiality-Integrity-Availability.md) quotes NIST's definition of confidentiality, which includes "means for protecting personal privacy". | Privacy and confidentiality are cousins, not twins. This page separates them. |
| What we protect and from whom | [Threat model](Threat-Model.md) and [Threat model exercise](Threat-Model-Exercise.md). The exercise lists "physical, legal and availability risks" as out of scope. | The physical side: what it is, and why a cloud lab can still care. |
| Keys and secrets | [Hashing, encryption and keys](Hashing-Encryption-and-Keys.md) and [Secrets from day one](Secrets-From-Day-One.md) | Key custody as a lock and as a privacy tool at once, in the Monero example. |
| Watching a system | [Detection and monitoring](Detection-and-Monitoring-Wazuh-and-the-Landscape.md) and [Telemetry crosses the trust boundary](Telemetry-Crosses-the-Trust-Boundary.md) | The privacy cost of watching: logs and cameras see people. |
| What you may and may not do | [Deception safety and law](Deception-and-Honeypots-Safety-and-Law.md) | The same "check your own law" habit, applied to lockpicking and personal data. |
| Hiding the network path | [Tor, I2P and the darknet without the myths](Tor-I2P-and-the-Darknet-Without-the-Myths.md) (issue 358). | Pointed to only; this page does not teach it. |

## Blinds and locks: the picture

Think of a house.

- **Privacy is the blinds and drapes.** It controls who can see in: what is known about you, who knows it and what they may do with it.
- **Security is the locks, the deadbolts, the bars on the windows and the alarm system.** It controls who can get in and what they can do once they are in.

Both protect the people inside. They are not the same job, and a house can have one without the other.

| Point | Privacy (blinds) | Security (locks and alarm) |
|---|---|---|
| The question | Who can see into my life, and what do they learn? | Who can get in, change things or break things? |
| What a failure looks like | Someone knows what you did, where you were, who you talk to | Someone is in your account, your files or your building and can act |
| Typical controls | Fewer data collected, shorter retention, pseudonyms, encryption of content, a screen filter, curtains | Locks, strong authentication, patches, firewalls, alarms, backups |
| Who decides | Often you, and often law (see below) | The owner of the system, sometimes a regulator |
| A system can fail it while | doing everything right on security (it is locked and everyone can see through the glass) | doing everything right on privacy (it is hidden and the door is unlocked) |

Two things follow.

**A locked house with no curtains is secure and not private.** A company can have excellent access control on its customer database and still collect far more about each customer than it needs, keep it for years and hand it to others. Nobody broke in. Nobody needed to.

**A house with curtains and an unlocked door is private and not secure.** A pseudonymous account whose password is `password1` hides who you are and lets anyone become you. A service that promises not to know who its users are but never signs its software updates is the same shape.

The CIA triad in the previous lesson is about the second half: lock confidentiality, integrity and availability. Privacy asks a further question, about people: even when the lock holds, what should be collected in the first place, and who is allowed to know?

## Where they overlap

Three controls serve both, and each one is also a place to be careful.

1. **Encryption.** It is a lock: without the key, a thief who steals the disk gets noise. It is also a blind: the people who carry the data across a network cannot read it. NIST's own definition of confidentiality includes "means for protecting personal privacy and proprietary information" ([NIST glossary: confidentiality](https://csrc.nist.gov/glossary/term/confidentiality), read 2026-10-31). The catch: encryption hides content, not always the fact that two parties talked, when and how much. That is "metadata", and it is often what a watcher wants. [Cross-tenant data flows](Cross-Tenant-Data-Governance-Retention-and-DLP.md) describes the same point for an access-only product: it sees who connected to what, when and how many bytes, and not the content.
2. **Access control.** "Only these people may open this" is a lock. It is also a blind: a file that only three people can read is a file the other thousand cannot see. But the list of who may enter, and the log of who did, is itself personal data, which a later section returns to.
3. **Data minimization.** Collect only what you need, keep it only as long as you need it. This is the quietest overlap and often the cheapest. Data you never collected cannot leak, cannot be subpoenaed or sold, and cannot be stolen. It protects privacy (less is known) and security (less is there to breach) with one decision.

## Where they pull apart

| Tension | Plain example | Why it pulls |
|---|---|---|
| **A lock with no blind** | A building with badge readers, cameras and guards that records every person who enters and keeps the video for a year | Strong security, and a pile of records about people. The security control is the privacy risk. |
| **A blind with no lock** | An anonymous forum with a trivial admin password, or a private notes app with no backup | Nobody knows who the users are, and anybody can deface it or lose it. |
| **Anonymity against accountability** | A service where nobody has to say who they are, set against a system where every change must be traceable to a person | Accountability needs a name behind each action (logs, signed commits, badges). Anonymity removes the name. Neither is wrong; they are different goals. |
| **Logging** | You need logs to detect an intruder; the logs hold usernames, addresses and times | A log is a window into the system for the defender and into the people for anyone who reads it. Protect it, shorten it, collect less. |
| **Verification** | Proving someone is who they say they are (an ID check) | The stronger the check, the more you learn about the person. |

NIST's catalog builds this tension into its own physical controls. One control requires visitor access records; an enhancement says to "limit personally identifiable information contained in visitor access records" to what the privacy risk assessment allows, noting that doing so "helps reduce the level of privacy risk created by a system" (NIST SP 800-53 Rev. 5, control PE-8 and enhancement PE-8(3), read 2026-10-31). The catalog asks for the record and asks you not to over-collect it, in the same place.

A short test to carry around: **name the person who could be hurt if this data were read by a stranger, and name the person who could be hurt if nobody could tell who did this.** If you can name both, you have a privacy question and an accountability question, and no setting makes both vanish.

## Monero: a worked example of both

Monero is a cryptocurrency whose project describes privacy as its main goal. It is a good example here for one reason: the project itself writes both a privacy story (what is hidden) and, in other pages, security warnings (what the user must still do). All the claims below are the Monero project's own, read on **2026-10-31** from getmonero.org, and are given as the project's claims. **This lesson makes no claim about what Monero can or cannot defeat, who can or cannot trace it, or how it compares with other currencies.** I read the project's user-facing pages only, not its research papers, and not any outside analysis.

### What the privacy features are described as hiding

The project's "What is Monero?" page says that "the sender, receiver, and amount of every single transaction are hidden through the use of three important technologies: Stealth Addresses, Ring Signatures, and RingCT" ([What is Monero?](https://www.getmonero.org/get-started/what-is-monero/), read 2026-10-31). Its Moneropedia glossary explains two of them:

| Feature | What the Monero project says it is for | Page |
|---|---|---|
| **Stealth addresses** | The sender creates a random one-time address for each transaction on the recipient's behalf, so the recipient can publish one address and incoming payments go to unique addresses "where they cannot be linked back to either the recipient's published address or any other transactions' addresses." | [Stealth address](https://www.getmonero.org/resources/moneropedia/stealthaddress.html) |
| **Ring signatures** | A transaction is signed in a way that, in the project's words, makes "no way an outside observer can tell which of the possible signers in a signature group belongs to your account." | [Ring signature](https://www.getmonero.org/resources/moneropedia/ringsignatures.html) |
| **RingCT** | Named on the "What is Monero?" page as the third technology that hides the amount. I did not read a page that explains it: the Moneropedia address I tried for it returned "not found". | the "What is Monero?" page above |

These are blinds. They are described as hiding who paid whom and how much, from people looking at the public record. A blind does not make a door lock.

### What security properties the user still needs

The same project's pages describe things the user must do or trust, and each is a lock, not a blind.

| Property | What the project's pages say | Blind or lock |
|---|---|---|
| **Key custody** (the seed) | The mnemonic seed is "a 16 or 25 word phrase used to backup and restore a Monero wallet", which "has all the information needed to view and spend funds", and "sharing this 16 or 25 word key is the equivalent of allowing another person complete access to your funds." The same page advises against keeping more in a "hot wallet" (one that is or has ever been connected to the internet) than you want to lose, and suggests a cold or paper wallet. That page is marked deprecated in favor of the project's newer docs, which I did not read. ([Mnemonic seed](https://www.getmonero.org/resources/moneropedia/mnemonicseed.html), read 2026-10-31) | Lock. Whoever holds the seed holds the funds, however well the transactions are hidden. It is also availability: lose it and the funds are gone, a point the [backups lesson](Backups-Deep-Dive-3-2-1-1-0-Immutability-and-Restore-Testing.md) makes about any key. |
| **The view key** | Each address has a private view key that can be shared; "by sharing a viewkey, a person is allowing access to view every incoming transaction for that address." The project adds that outgoing transactions "cannot be reliably viewed as of June 2017", so a balance shown that way "should not be relied upon". The project calls Monero "private, optionally transparent". ([View key](https://www.getmonero.org/resources/moneropedia/viewkey.html), read 2026-10-31) | A privacy dial you set: you decide who may see in. Sharing it is a choice about blinds, and it cannot spend. |
| **Node trust** | A node is a machine with a full copy of the blockchain. A "remote node" is one that does not run on the same machine as your wallet. The project says "using an open node will allow to make a transaction instantaneously ... but at the cost of the control over your privacy", and "node operators can link transactions to IP addresses." It recommends running your own node. Its wallet guide adds that "there are publicly advertised remote nodes which are run by malicious actors with the sole purpose of deanonymizing users" and recommends your own node or a trusted one. ([Remote node](https://www.getmonero.org/resources/moneropedia/remote-node.html), [Connect to a remote node](https://www.getmonero.org/resources/user-guides/remote_node_gui.html), both read 2026-10-31) | Both. Whom you ask for the blockchain is a trust decision (a lock on who you let help you) and decides what that party can see about you (a blind). The convenience trade is named by the project itself. |
| **Wallet and device security** | The seed page's warning about hot wallets, above. | Lock. A blind on the transactions does nothing for malware on the device that holds the keys. This line is my reading, not a sentence on the page. |
| **Software integrity** | The project's user guide index lists guides on verifying that the CLI and GUI software is safe, on offline backups, on view-only wallets and on connecting over Tor or I2P. I read the titles in that index, not the guides. ([User guides](https://www.getmonero.org/resources/user-guides/), read 2026-10-31) | Lock. Running a tampered wallet is an integrity failure, whatever the chain hides. |

### What to take from it

A privacy feature is not a security control and a security control is not a privacy feature, even inside one product. Monero's own pages describe both lists, and the second one is as long as the first. The way to read any "private" product is the same: ask what is hidden, from whom, then ask who holds the keys, whom you must trust to use it, what runs on your device and who checks the software. A hidden record does not stop a stolen seed. A strong lock does not hide what the record says.

The [lesson on Tor and I2P](Tor-I2P-and-the-Darknet-Without-the-Myths.md) (issue 358) covers hiding the network path, which the Monero pages above mention as one way to reduce what a node can learn. The [lesson on cryptography](Cryptography-Fundamentals-Symmetric-Asymmetric-Hashing-Certificates-and-Keys.md) (issue 360) covers the primitives underneath.

## Privacy law basics, at a high level

Not legal advice, and not a summary of your law. Laws differ by country, by state and by what kind of data and organization you are. **Check your own jurisdiction**; if it matters, ask a lawyer or the regulator.

The best-known example is the EU's General Data Protection Regulation (GDPR, Regulation (EU) 2016/679). The European Commission's page says it sets out "7 key principles" for processing personal data: lawfulness, fairness and transparency; purpose limitation; data minimization; storage limitation; accuracy; integrity and confidentiality; accountability ([Overview of the principles](https://commission.europa.eu/law/law-topic/data-protection/rules-business-and-organisations/principles-gdpr_en), read 2026-10-31, citing Article 5 and Recital 39). Three bear on this lesson.

- **Purpose limitation.** An organization "may collect and otherwise process personal data only for a specific purpose, which must be indicated to individuals when obtaining their personal data." Data collected for one reason is not free for any other.
- **Data minimization.** It "must collect and process only the personal data that is necessary to fulfil that purpose." This is the overlap point above, written as a rule.
- **Storage limitation.** Data is kept "for no longer than necessary for the purposes for which it was collected." This is retention. [Cross-tenant data governance](Cross-Tenant-Data-Governance-Retention-and-DLP.md) covers the engineering side.

The seventh item matters most to a security learner: **integrity and confidentiality** is itself one of the seven principles. The Commission page puts it as: "appropriate technical and organisational measures to ensure the security of the personal data, including protection against unauthorised or unlawful processing and against accidental loss, destruction or damage." So in this law, security is one of the ways you meet your privacy duty. The two are tied together by statute and still not the same thing, which is the point of the blinds and locks.

Three facts from the Commission's overview page ([Data protection explained](https://commission.europa.eu/law/law-topic/data-protection/data-protection-explained_en), read 2026-10-31) bear on the physical half of this lesson. It lists "video recording (CCTV)" and "storing IP addresses or MAC addresses" among examples of personal data processing, says the rules cover data "through video surveillance, or on paper", and lists "shredding documents containing personal data" as processing. It also says the GDPR does not apply to data processed by an individual for purely personal reasons or home activities with no professional or commercial link. Whether a given camera on a given doorstep is covered depends on facts and law I have not read; that is a question for your regulator.

I tried to read the Information Commissioner's Office guidance on the UK version and the regulation's official text. Neither download worked (the first answered with a gateway error, the second with an empty response), so neither is cited. Other places have their own laws; this page names none of them.

## The physical side of security

Cybersecurity easily reaches the physical world, and the other way round. The server sits in a building. The drive sits in a drawer. The badge opens the door to the server room. The best firewall does nothing for a laptop that walks out of a coffee shop. A cloud account hides the building (the provider runs it, see [What is the cloud](What-Is-the-Cloud.md)), but your own laptop, phone, security key and the paper next to your desk are still yours to protect. The [threat model exercise](Threat-Model-Exercise.md) puts physical risks out of scope for this project's lab; this lesson is the reason that is an explicit choice, not an oversight.

NIST's control catalog has a whole family on this (Physical and Environmental Protection, PE). The rows below take the ideas from it, with the control number, and add the privacy cost the catalog sometimes names and sometimes leaves out.

| Control idea | Plain words | NIST SP 800-53 Rev. 5 | Privacy cost |
|---|---|---|---|
| **Locks and key control** | "Secure keys, combinations, and other physical access devices", keep an inventory, and change keys and combinations when "keys are lost, combinations are compromised, or when individuals possessing the keys or combinations are transferred or terminated." | PE-3 | Low, until a key log names people. |
| **Doors and access control** | Keep a list of who is authorized, issue credentials, check them at the door, remove people when they no longer need access, keep access logs. | PE-2, PE-3 | The list and the log are personal data. |
| **Tailgating and piggybacking** | One person follows another through a controlled door. The catalog describes an "access control vestibule" (two interlocking doors) built to "prevent unauthorized individuals from following authorized individuals into facilities with controlled access", and names the activity "piggybacking or tailgating". | PE-3(8) | Some. The space is monitored. The other half of the fix is a person: politely asking who someone is. |
| **Alarms** | "Physical intrusion alarms can be employed to alert security personnel when unauthorized access to the facility is attempted", working "in conjunction with physical barriers, physical access control systems, and security guards." Sensors named include motion, contact and broken glass sensors. | PE-6(1) | Low, unless it also records who is inside. |
| **Cameras** | Video surveillance "focuses on recording activity in specified areas for the purposes of subsequent review"; "monitoring the surveillance video is not required". The catalog adds: "there may be legal considerations when performing and retaining video surveillance, especially if such surveillance is in a public location." | PE-6(3) | High. A camera is a lock for the building and a window into everyone who passes it. Decide the field of view, the retention and who may watch before buying one. |
| **Visitors** | Escort visitors, control what they do, keep records, review the records. | PE-3, PE-8 | Visitor logs hold names; the catalog says to limit that information (PE-8(3)). |
| **Printers and output** | Control who can pick up printed output so unauthorized people cannot collect it. | PE-5 | Low. |
| **Secure disposal of drives and paper** | See the next section. | MP-6, NIST SP 800-88 Rev. 2 | Disposal is a privacy duty as much as a security one. |
| **Clean desk** | Nothing sensitive left in view or unlocked when you walk away: papers, sticky notes with passwords, an unlocked screen. | Not read in the catalog sections I extracted. | A blind and a lock at once (see the exercise). From general knowledge, **est.** |

Two observations. **Every physical lock is also a delay.** A door, a fence and a padlock slow someone down and make noise or leave marks; a determined person with time and no witnesses may get through. That is why the catalog pairs barriers with alarms and a response, not barriers alone. This is my reading, not a sentence from the catalog. And **the human is the weakest and strongest part**: tailgating works because people are polite, and stops because someone asks.

### Secure disposal of drives and paper

NIST's media sanitization guide defines sanitization as "a process that renders access to target data on the media infeasible for a given level of effort" ([NIST SP 800-88 Rev. 2](https://csrc.nist.gov/pubs/sp/800/88/r2/final), published September 2025, read 2026-10-31). The previous edition, Rev. 1, was withdrawn on September 26, 2025, and superseded by Rev. 2, so check which edition any older article cites. The guide covers two kinds of media:

- **Hard copy**, "typically paper printouts, film, microfiche"; it notes that hard copy "that leave[s] an organization without effective sanitization expose[s] a significant vulnerability to 'dumpster divers' and overcurious employees."
- **Information storage media**, "hard disk drives (HDDs), solid state drives (SSDs), random access memory ... optical disks, magnetic tape, flash memory ... phones, mobile computing devices", and so on.

It defines three sanitization methods: **clear**, **purge** and **destroy**. For storage that you do not physically hold (cloud storage), it says "cryptographic erase may be the only viable purge sanitization technique option" ([PDF](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-88r2.pdf), section 3.1, read 2026-10-31). The guide says cryptographic erase "is based on the sanitization of keys used to encrypt data or to prevent access to the keys that encrypt data" (section 3.2), under conditions it lists and I did not study. It ties disposal back to key custody: destroy the key and the data is gone, which is the Monero seed above in reverse. I did not read the technique details, so this page does not recommend a method for any particular drive. For a drive you own, the practical rule is: pick a method from the guide or the maker's documentation for that kind of drive, and keep a note of what you did. I did not find a normal delete or a quick format described as a sanitization method in the parts I read; check the guide before you rely on either (**est.**).

Paper is the cheapest to forget. A shredder is a blind and a lock for a page.

## Why lockpicking is a common hobby in the field

Many people in security pick locks as a hobby ("locksport"). The reasons are plain: a lock is a small, honest model of a security control. Learning how a mechanism can fail teaches you how to choose, test and replace one. TOOOL, a US nonprofit lockpicking group (the name is an acronym on its own site), puts its purpose as "advancing the general public knowledge about locks and lock picking through teaching, research, and competition" ([TOOOL home page](https://toool.us/), read 2026-10-31). It quotes A.C. Hobbs (1853): "If a lock is not so inviolable as it has hitherto been deemed to be, surely it is to the interest of honest persons to know this fact, because the dishonest are... certain to apply the knowledge practically", and a 2005 conference talk: "exposing bad security is what protects us all."

**The rules come before anything else.**

1. **Only locks you own, or locks the owner has said you may open, in writing.** Locksport's commonly stated ethics, as summarized in the English Wikipedia article on locksport (a secondary source; the archived original ethics page it cites was not read, and the Locksport International site did not answer), are: do not open a lock that is in use; open only locks that belong to you, and for others get the owner's express consent; and preserve the security needs of others (read 2026-10-31).
2. **Check your local law.** TOOOL's page on lockpicking laws says that people who claim picks are illegal where they live are "very often" wrong ("Very often, this statement is false."), and that "We are not lawyers and this page is not offering legal advice." It adds that many municipalities have laws that differ from state law, and that some regions have separate laws for bump keys and other specialized tools ([Lock Picking Laws in the United States](https://toool.us/lockpicking-laws/), read 2026-10-31). The statutes it quotes for the states I read mostly concern possession of burglary tools with intent to commit a crime, and the page labels states from "legal - must show intent" to "no specific laws". It is about the United States only; this page names no other country's rule. Look yours up, and when in doubt, ask.
3. **Never on a lock that protects something someone else relies on**, never to get into a place, and never to show off to a stranger. Carrying picks near a door that is not yours is the wrong picture in any jurisdiction.

**What this lesson will not do.** It gives no step-by-step technique and no bypass guide for any specific commercial lock or product. If you want to learn, go to the people who teach it with the rules in the room: a local locksport group or a TOOOL chapter, a village at a security conference, or a hobby community that publishes its own rules. The organizations' own pages are the place to start: the TOOOL pages above, and the Locksport International site (which I could not reach on 2026-10-31).

**What the hobby teaches defenders.** That a lock rated for a purpose is not magic, so layer it (a door, a lock, an alarm, a camera, a person). That a cheap lock is a label, not a barrier. That "a key is also a secret": key control matters (see the table above). That a vendor who hides how a product fails is not making it safer. That is the same lesson as a pen test, a code review and an incident postmortem, with a small steel lock in your hand.

## Free exercise: audit your own room or desk

You will list what protects your room, desk and devices, and sort each item into **blind** (it limits who can see), **lock** (it limits who can get in or do something) or **both**. Cost: nothing. Time: about 45 minutes. Everything is on your own things; touch nothing that belongs to someone else.

**Predict first.** Before you start, write down how many items you expect to find in each column, and which column you expect to be longest.

**Do.** Walk the space once with a pen. Write each protective thing as a row in the table below. Include the physical (the door lock, the curtains, a drawer that locks, a shredder, a privacy filter on the screen, a cable lock), the digital (screen lock, disk encryption, password manager, multi-factor authentication on your main email, backup, social media privacy settings, the router's admin password) and the paper (bills, notes, passwords on sticky notes). For each, write what it stops, who it does *not* stop, and the gap.

| Item | Where | What it protects | Blind, lock or both | Who it stops | Who it does not stop | Gap or fix |
|---|---|---|---|---|---|---|
| Curtains (worked example) | Bedroom window | Keeps passersby from seeing the desk | Blind | Anyone outside, in the daytime | Anyone inside the room; anyone with a light behind them at night | Fine for the purpose. Not a lock. |
| Door lock (worked example) | Bedroom door | A casual walk-in | Lock | A visitor who is not supposed to be in | Someone with a key; a flatmate who has the spare | Who holds spares? Is the key inventory written down? |
| Screen lock with a short timeout (worked example) | Laptop | Someone using it while you are away | Both (it stops use, and it hides what is on screen) | A passerby | Someone who knows your passcode | Is the passcode on a note taped to the laptop? |
| | | | | | | |
| | | | | | | |
| | | | | | | |
| | | | | | | |
| | | | | | | |
| | | | | | | |

**Check.**

- Count the three columns. Which is longest? Was your prediction right?
- Pick the three rows with the weakest "who it does not stop" and write one cheap fix for each.
- Find one thing that is a lock with a privacy cost (a camera, a webcam left on, a shared location app) and one thing that is a blind with no lock (an app with a private profile and a reused password). If you find neither, look again.
- Find one item you own that holds data and will one day be thrown away or sold (a drive, a phone, a pile of old bills). Write how you will sanitize it, by looking at the maker's documentation or NIST's guide for that kind of media, not by guessing.

**Undo.** Nothing was changed. If you changed something, write it down so you can change it back.

### A script-free checklist

Use it once a quarter, or when you move.

- [ ] **Doors and windows.** Every door that should lock, does. Spare keys are accounted for and the list is written down.
- [ ] **Visitors.** You know who has been in the room. Anyone who works on your devices is watched while they do.
- [ ] **Devices.** Every laptop and phone has a screen lock and an encrypted disk. Nothing is left logged in and unattended.
- [ ] **Paper.** Papers with account numbers, passwords or addresses go in a locked drawer or a shredder, not the bin.
- [ ] **Passwords and keys.** Recovery codes and seed phrases for anything valuable are written down offline, stored apart from the device, and known to a second trusted person or place (see [the backups lesson](Backups-Deep-Dive-3-2-1-1-0-Immutability-and-Restore-Testing.md)).
- [ ] **Cameras and sensors.** Every camera, microphone and smart-home device that you have is one you chose; each has a changed default password and a known field of view.
- [ ] **Accounts and settings.** Public profiles show only what you mean to show. Location sharing is off unless you use it.
- [ ] **Disposal.** Anything leaving the house with storage (a phone, a drive, a printer with a hard disk) has been sanitized by a method suited to it.
- [ ] **Law.** If you pick locks, you own the lock or hold written permission, and you checked your local law.

### Build, break, detect, evade, defend (on paper)

**Build.** From your table, list the three things you would most hate to lose or to have read. **Break (shown, not run).** For each, write in one sentence how an honest mistake could expose it and in one how a person with bad intent could. **Detect.** Name what would tell you: a door log, an alert on login, a camera you actually review. If nothing would, that is a gap. **Evade.** The tempting move is to hide the thing (obscure the location, rename the file). Hiding changes what a casual observer sees; it adds no lock. **Defend.** Add the cheapest control that closes the highest gap, then write what it costs in the other column: a camera adds a lock and a privacy cost.

**Flip the board.** You are the one trying to learn about someone. Do you try the blinds (watch from outside) or the locks (get in)? Why is the answer so often "whichever the defender has not worked on"?

## Checkpoint

- Say the difference between privacy and security in two sentences, with the house picture.
- Give an example of a house with a lock and no blind, and one with a blind and no lock.
- Name three overlaps and say what each one costs.
- Why can a security log be a privacy problem? Which NIST control tells you to limit what the log holds?
- Name two things a Monero user still needs even when the transactions are hidden, and say whether each is a lock or a blind.
- Which GDPR principle is itself about security?
- Why is a camera both a lock and a window? Name two decisions to make before installing one.
- What are the three sanitization methods in NIST's media guide, and which edition is current?
- What is tailgating, and which two kinds of fix does it need?
- Before picking any lock, what two rules apply?

## Common mistakes

| Symptom | Most likely cause | What to check |
|---|---|---|
| "It is encrypted, so nobody can see anything" | Treating content privacy as the whole of privacy | Metadata: who, when, how much. Encryption hides content, not always the pattern. |
| "It is anonymous, so it is safe" | A blind with no lock | Who can change it, who can impersonate, what happens if the key is lost |
| "We are secure, we log everything" | A lock with no care for the people in the logs | What is logged, for how long and who may read it |
| A camera installed without thinking about retention | Security chosen, privacy ignored | Field of view, retention time, who can view, and what your law says |
| A password on a sticky note on the monitor | Clean desk skipped | Move it to a password manager; shred the note |
| A drive sold after a quick format | Deleting read as sanitizing | The maker's or NIST's method for that kind of drive |
| "Lockpicks are illegal everywhere" or "they are legal everywhere" | One claim taken for all places | Your own local law; TOOOL says it is not legal advice and is about the United States |
| Picking a lock "to see if I can" on something not yours | Missing consent | Own it, or have the owner's written permission, or do not touch it |
| Calling the GDPR "the privacy law" for everyone | One regime taken as the rule | Where the data's subjects and the organization are; your own regulator |

## Claims register

Pages were downloaded and read on **2026-10-31**. Status words: **Read** means I read the passage, **est.** means from general knowledge or my own reading of the sources, **Not read** means I did not get it.

| Claim | Source | Status |
|---|---|---|
| Confidentiality includes "means for protecting personal privacy and proprietary information" | [NIST glossary: confidentiality](https://csrc.nist.gov/glossary/term/confidentiality) | Read 2026-10-31 (quoted in the CIA triad lesson, which read it the same day; not re-opened for this page) |
| Monero: "the sender, receiver, and amount of every single transaction are hidden" through stealth addresses, ring signatures and RingCT (the project's own claim) | [What is Monero?](https://www.getmonero.org/get-started/what-is-monero/) | Read 2026-10-31 |
| Stealth addresses: one-time addresses per transaction | [Stealth address](https://www.getmonero.org/resources/moneropedia/stealthaddress.html) | Read 2026-10-31 |
| Ring signatures: an observer cannot tell which possible signer is yours (the project's claim) | [Ring signature](https://www.getmonero.org/resources/moneropedia/ringsignatures.html) | Read 2026-10-31 |
| A RingCT explanation page | The Moneropedia address I tried returned "not found" | Not read |
| The seed gives full control; hot-wallet warning; page marked deprecated | [Mnemonic seed](https://www.getmonero.org/resources/moneropedia/mnemonicseed.html) | Read 2026-10-31; the successor docs were not read |
| View key: shows incoming transactions; outgoing "cannot be reliably viewed as of June 2017" | [View key](https://www.getmonero.org/resources/moneropedia/viewkey.html) | Read 2026-10-31; the "as of June 2017" is the page's own date and may be out of date |
| Remote nodes: privacy cost, operators can link transactions to IP addresses; run your own node | [Remote node](https://www.getmonero.org/resources/moneropedia/remote-node.html), [Node](https://www.getmonero.org/resources/moneropedia/node.html) | Read 2026-10-31 |
| Malicious publicly advertised nodes exist, trusted or own node recommended | [Connect to a remote node](https://www.getmonero.org/resources/user-guides/remote_node_gui.html) | Read 2026-10-31 |
| The guide index lists software-verification, offline backup, view-only wallet, Tor and I2P guides | [User guides](https://www.getmonero.org/resources/user-guides/) | Read the index titles 2026-10-31; the guides were not read |
| What Monero can or cannot defeat, or how it compares with other currencies | | Not claimed; research papers and outside analysis **Not read** |
| The GDPR's seven principles; purpose limitation, data minimization, storage limitation and integrity and confidentiality as quoted | [European Commission: Overview of the principles](https://commission.europa.eu/law/law-topic/data-protection/rules-business-and-organisations/principles-gdpr_en) (cites Article 5 and Recital 39) | Read 2026-10-31 |
| CCTV and IP addresses as examples of personal data; paper and video are covered; the personal and household exception | [European Commission: Data protection explained](https://commission.europa.eu/law/law-topic/data-protection/data-protection-explained_en) | Read 2026-10-31 |
| The official text of the GDPR (Regulation (EU) 2016/679) | EUR-Lex | Not read (the download returned an empty response) |
| The UK regulator's principles guidance | Information Commissioner's Office | Not read (the download returned an error) |
| PE-2, PE-3, PE-3(8), PE-5, PE-6, PE-6(1), PE-6(3), PE-8, PE-8(3) text: keys, access, vestibules, alarms, video, visitors, limiting personal data in visitor records | [NIST SP 800-53 Rev. 5 catalog (OSCAL JSON, version 5.2.0)](https://raw.githubusercontent.com/usnistgov/oscal-content/main/nist.gov/SP800-53/rev5/json/NIST_SP-800-53_rev5_catalog.json) | Read 2026-10-31 (text extracted by a script I ran; quotes copied from the output) |
| Sanitization defined; hard copy and storage media; clear, purge, destroy; cryptographic erase may be the only purge option for cloud storage | [NIST SP 800-88 Rev. 2](https://csrc.nist.gov/pubs/sp/800/88/r2/final) and its [PDF](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-88r2.pdf), published September 2025 | Read the abstract page and the sections quoted 2026-10-31; the technique details were not read |
| Rev. 1 withdrawn September 26, 2025, superseded by Rev. 2 | [NIST SP 800-88 Rev. 1](https://csrc.nist.gov/pubs/sp/800/88/r1/final) | Read 2026-10-31 |
| TOOOL's purpose, the Hobbs and conference quotes | [TOOOL](https://toool.us/) | Read 2026-10-31 |
| US lockpick laws mostly need intent; not legal advice; municipalities differ; the page is US only | [TOOOL: Lock Picking Laws in the United States](https://toool.us/lockpicking-laws/) | Read the opening, the notes and the first states 2026-10-31; not every state's text |
| Locksport ethics rules (own locks or consent; not in use) | [English Wikipedia: Locksport](https://en.wikipedia.org/wiki/Locksport), Ethics section | Read 2026-10-31; secondary source, original ethics page not read |
| Locksport International's own legal and ethics pages | the site | Not read (the site did not answer) |
| A lock is a delay, not a wall; the human is the weakest and strongest part; the hobby teaches layering | My reading | **est.**, not a source claim |
| A clean desk policy | General practice | **est.**, not read in a standard |
| No script appears on this page | | Nothing run |

<!-- BEGIN GENERATED PAGE NAV bottom: rewritten from docs/wiki/_nav.yaml by scripts/gen_wiki_nav.py; edit the manifest, not this block -->
Where you are: [Home](Home.md) > [Track 3: Privacy, anonymity and cryptocurrency](Contents.md#track-3-privacy-anonymity-and-cryptocurrency) > Privacy versus security

Previous: [Privacy, security and anonymity](Privacy-Security-and-Anonymity-Three-Different-Things-and-Why-There-Is-No-Silver-Bullet.md) / Next: [Tor, I2P and the darknet without the myths](Tor-I2P-and-the-Darknet-Without-the-Myths.md)

In this track: [Track 3: Privacy, anonymity and cryptocurrency](Contents.md#track-3-privacy-anonymity-and-cryptocurrency), 19 pages

- Cryptography and privacy: [Cryptography fundamentals](Cryptography-Fundamentals-Symmetric-Asymmetric-Hashing-Certificates-and-Keys.md) / [Privacy, security and anonymity](Privacy-Security-and-Anonymity-Three-Different-Things-and-Why-There-Is-No-Silver-Bullet.md) / **Privacy versus security**
- Tor, I2P, VPN and browsing: [Tor, I2P and the darknet without the myths](Tor-I2P-and-the-Darknet-Without-the-Myths.md) / [How a VPN works](How-a-VPN-Works-Tunnels-What-It-Hides-What-It-Does-Not-and-What-an-Audit-Proves.md) / [How Tor works in depth](How-Tor-Works-in-Depth-Circuits-Relays-Directory-Authorities-and-Onion-Services.md) / [How I2P works](How-I2P-Works-Tunnels-Garlic-Routing-and-the-Network-Database.md) / [The browsing setups compared](The-Browsing-Setups-Compared-Tor-Browser-Brave-Whonix-Tails-and-Qubes-with-Whonix.md) / [OPSEC for Tor and I2P](OPSEC-for-Tor-and-I2P-That-Holds-Up-Identities-Layers-Metadata-and-Habits.md) / [Hands-on Whonix and Qubes OS](Hands-On-Whonix-and-Qubes-OS-Gateway-Split-Compartments-Disposables-and-Policy-Prompts.md) / [The darknet landscape: markets, OPSEC and layering](The-Darknet-Landscape-Markets-OPSEC-Clearnet-and-Layering-Tor-I2P-and-VPN.md) / [Lab: publish a web server as an onion service and an I2P site](Lab-Publish-a-Web-Server-as-a-Tor-Onion-Service-and-an-I2P-Site-Time-Boxed-and-Defensive.md)
- Cryptocurrency: [Blockchain fundamentals](Blockchain-Fundamentals-Hashes-Blocks-Nodes-Consensus-and-Forks.md) / [How Bitcoin works](How-Bitcoin-Works-Keys-UTXOs-Mining-and-Why-It-Is-Pseudonymous-and-Traceable.md) / [How Monero works](How-Monero-Works-Compared-with-Bitcoin-and-Ethereum-DeFi-Mixers-Swaps-and-Ransomware.md) / [Wallets and key custody](Wallets-and-Key-Custody-Hot-and-Cold-Hardware-Wallets-Recovery-Shamir-and-Multisig.md) / [Paper wallets and offline key generation](Paper-Wallets-Generators-and-Offline-Key-Generation-Tails-Electrum-and-Monero.md) / [Running Monero properly](Running-Monero-Properly-Hardware-Wallet-Qubes-and-Whonix-Offline-Wallet-and-PiNodeXMR.md)
- Radio and off-grid: [Radio and off-grid communication](Radio-Off-Grid-Communication-LoRa-Meshtastic-Reticulum-Ham-and-SIGINT.md)

Related pages:

- [Threat model](Threat-Model.md)
- [The CIA triad](The-CIA-Triad-Confidentiality-Integrity-Availability.md)
- [Cross-tenant data flows, governance, retention and DLP](Cross-Tenant-Data-Governance-Retention-and-DLP.md)
- [Backups deep dive](Backups-Deep-Dive-3-2-1-1-0-Immutability-and-Restore-Testing.md)
- [US privacy law and the patchwork](US-Privacy-Law-No-General-Right-the-Patchwork-Data-Brokers-Social-Security-Numbers-and-License-Plate-Readers.md)
- [Secrets from day one](Secrets-From-Day-One.md)
<!-- END GENERATED PAGE NAV bottom -->
