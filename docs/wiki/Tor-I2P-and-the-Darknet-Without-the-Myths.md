# Tor, I2P and the darknet without the myths: Tails, Whonix, Qubes and a Monero node

Side page to the start-from-zero pages. Read it when "Tor", "I2P", "the dark web" or "onion service" are only scary words to you, or when you keep hearing "use Tails" or "use Whonix" and want to know what each tool is for and what it cannot do. It explains how the two networks work in plain words, who uses them and why, how the three privacy operating systems differ, and then uses a Monero node as the worked example of where privacy and security overlap and where they come apart. It sits beside [Threats in plain words](Threats-in-Plain-Words.md), which covers the clearnet threats this page keeps pointing at. Two lessons it builds toward are named here in plain text because they are not written yet: the lesson on privacy versus security and the lesson on cryptography (issues 359 and 360).

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

> **Status: unverified draft, written from reading. Nothing on this page was run.** On **2026-10-31** I downloaded and read the pages named in the [claims register](#claims-register): the Tor Project's support and community pages, the I2P project's documentation, the Tails, Whonix and Qubes sites, the Monero project's anonymity-networks document and Tor wallet guide, and the PiNodeXMR repository, its wiki and its public history. **Not run:** Tor Browser, Tor, I2P, Tails, Whonix, Qubes OS, `monerod`, PiNodeXMR, and every command shown (the commands are quoted from the Monero document so you can read them; they are not tested here). Nothing on this page was checked against a live network. A claim I could not read on a project's own page is marked **est.** Where a project's page and this page disagree, trust the project's page and tell us.

> **Prerequisites.** [How a web request works](How-a-Web-Request-Works.md) for what a client, a server and an IP address are, and [Hashing, encryption and keys](Hashing-Encryption-and-Keys.md) for what a public key is. [The CIA triad](The-CIA-Triad-Confidentiality-Integrity-Availability.md) helps for the privacy-versus-security part. No account, no install and no network are needed: this page is reading only. About 75 minutes (est.).

> **Where this runs, and the rule.** Nowhere: it is a reading lesson. Do not run Tor, I2P or any tool named here as a way to "see what is out there" on a work or school network, and check the law where you live before you do ([the law, in one paragraph](#the-law-in-one-paragraph)). There are no marketplace walkthroughs on this page and there will not be.

## What you will be able to do

- Say what Tor and I2P are, and explain onion routing and garlic routing in plain words.
- Say what an onion service (also called a hidden service) is and what it gives you that an ordinary website does not.
- Give an honest, calm account of the "darknet": legitimate uses, illegitimate uses, and why fear marketing misleads.
- Say what Tor Browser, Tails, Whonix and Qubes OS are each for, how they differ, and when each is the wrong tool.
- List what these tools do not protect against.
- Explain, with a Monero node as the example, the difference between hiding where something came from (privacy) and keeping a machine safe (security).
- Read PiNodeXMR's own documentation for what it does over Tor and I2P, and say what that documentation does not claim.

## What the wiki already says (and the gap)

| Idea | Where it is today | The gap this page fills |
|---|---|---|
| Who attacks, and how | [Threats in plain words](Threats-in-Plain-Words.md), [Threat model](Threat-Model.md) | The clearnet is where most of it happens; this page puts the "dark" networks in proportion. |
| A VPN, and a connector that dials out | [Zero trust at home: VPN versus ZTNA](Zero-Trust-at-Home-Two-Connectors-and-Failover.md#vpn-versus-ztna-under-real-residential-conditions) | How Tor differs from a VPN, and what a home VPN to your own node is for. |
| Keys, hashes and encryption | [Hashing, encryption and keys](Hashing-Encryption-and-Keys.md) | Why an onion address is a public key. |
| Confidentiality, integrity, availability | [The CIA triad](The-CIA-Triad-Confidentiality-Integrity-Availability.md) | Privacy is not one of the three; where it fits. |
| Using a throwaway virtual machine | [Virtual machines and hypervisors](Virtual-Machines-Hypervisors-Desktop-and-Datacenter-Options.md) | Whonix and Qubes are built from virtual machines. |
| Law and ethics of poking at things | [Deception and honeypots: safety and law](Deception-and-Honeypots-Safety-and-Law.md) | Where Tor and I2P sit legally is a separate question; this page only says to check. |

## The calm version first

The "darknet" is not a dark corner of the internet where everything is dangerous. It is a set of networks that run on top of the ordinary internet and hide who is talking to whom. Hiding who is talking to whom is useful to a journalist protecting a source, to a person living under censorship, to a researcher who does not want a target to see their address, and to an ordinary person who does not want to be tracked across websites. It is also useful to criminals, as is every widely available tool.

Three points, in order of importance:

1. **The Tor Project says it plainly.** Its support page on criminal use states that Tor's mission is to advance human rights and defend against mass surveillance and censorship, that the project condemns criminal misuse, and that "criminal intent lies with the individuals and not the tools they use." It adds that taking Tor away would be unlikely to stop criminals, who have other options, and that Tor and other privacy measures can help fight identity theft and stalking and can be used by law enforcement. (Read 2026-10-31.)
2. **The clearnet holds far more danger than the darknet.** That is the maintainer's position as written in the issue behind this lesson, and it matches what the wiki already teaches: phishing, stolen passwords, ransomware and exposed servers happen on ordinary websites, ordinary email and ordinary cloud accounts, which is where [Threats in plain words](Threats-in-Plain-Words.md) and the [attack surface](Attack-Surface-List-Shrink-Measure.md) pages spend their time. I have not counted anything to compare the two, so treat "far more" as the maintainer's stated view and general knowledge, not a measured figure (**est.**).
3. **A lot of darknet scare content is exaggeration or invention.** Videos and articles sell fear because fear sells. Some describe things that cannot be checked, some repeat each other, and some are made up. A good rule for any frightening claim about these networks: ask for a source you can open yourself, and ask whether the story would still be frightening if you replaced the word "darknet" with "the internet."

None of this makes the networks magic or risk-free. Using them badly can hurt you, and the rest of this page is about how.

## Tor in plain words

**Tor** is a program that sends your traffic through a chain of relays run by volunteers, so that the website does not learn where you are and someone watching your connection does not learn which sites you visit. The Tor Project's support page says exactly this (read 2026-10-31). The same page says most people use Tor through **Tor Browser**, "a version of Firefox that fixes many privacy issues", and that the Tor Project is a nonprofit that maintains the software.

**Onion routing** is the idea underneath. Your computer wraps the message in several layers of encryption, one per relay, like the layers of an onion. Each relay can peel off only its own layer, so it learns only where the message came from and where to hand it next. The Tor Project's history page dates the idea to 1995, to researchers at the U.S. Naval Research Laboratory, and describes it as routing "traffic through multiple servers" and encrypting "it each step of the way" (read 2026-10-31).

In Tor's usual circuit there are three relays. The Tails project describes what each can see: the first relay knows where you come from but not where you are going, the third knows where you are going but not where you come from, and no single relay knows both (read 2026-10-31). Trust is spread across relays run by different people and organizations; the Tor Project says this distributed trust is more secure than a one-hop proxy.

```text
  You --[layer 3 + 2 + 1]--> relay 1 --[layer 3 + 2]--> relay 2 --[layer 3]--> relay 3 ---> website
        knows you,                 knows relay 1               knows relay 2         knows the website,
        not the website            and relay 3 only            and the website       not you
```

This picture is simplified: it shows the idea from the Tor and Tails pages, not the protocol. Two honest limits come with it, both stated by the Tor Project:

- **Your internet provider still sees that you use Tor.** What it cannot see is which sites you visit. A bridge can hide even that you use Tor (Tails warnings page, read 2026-10-31).
- **Tor does not defend against an observer who sees both ends.** The Tor Project's page on remaining attacks says that an observer who can see both you and the destination, or you and the exit relay, can correlate the timing of traffic going in and coming out, "Tor does not defend against such a threat model."

**How this differs from a VPN.** A VPN is one hop: you trust one company, which can see both who you are and where you go. Tor spreads that knowledge across several independent relays. Tails' warnings page makes the same comparison for fast traffic like web browsing (VPNs are "less secure than Tor, because they do not use 3 independent relays"). A VPN has a different job, which is also useful: making a private network reachable from outside, as in [Zero trust at home](Zero-Trust-at-Home-Two-Connectors-and-Failover.md#vpn-versus-ztna-under-real-residential-conditions).

## I2P and garlic routing in plain words

**I2P** (the Invisible Internet Project) is a separate network with the same goal. Its introduction says it is a layer on which anonymity-minded applications such as web hosting, chat, mail and file sharing can run (page updated 2025-01, accurate for release 0.9.65, read 2026-10-31).

Three differences matter to a beginner:

- **One-way tunnels.** In I2P each party builds an outbound tunnel and an inbound tunnel, so a message and its reply need four tunnels in all. A tunnel is a path through a chosen list of routers with layered encryption, and each router can decrypt only one layer. (I2P garlic routing page, updated 2025-10, read 2026-10-31.)
- **Hidden inside the network.** I2P's design is mainly for services and users inside I2P. The introduction page says that the fact that you run I2P is usually not a secret; what is hidden is what you are doing, and which router a given destination is connected to.
- **"Garlic."** I2P's own page says that "garlic routing" as a general concept is identical to onion routing, and that I2P uses the word in a looser way for two more things: bundling several messages together into one wrapped message (each message is a "clove", the bundle a "garlic message"), and a form of end-to-end encryption. The page warns that I2P's own use of the term "has not always been precise." So the plain-words version is: **garlic is onion routing plus the ability to bundle several messages in one wrapper.**

Which is better? I2P's own anonymity-network comparison is not something I read for this page, so I do not rank them. The Monero project, in a document I did read, says I2P "has a smaller set of users (less cover traffic) and academic reviews" than Tor, "so there is a trade off" (read 2026-10-31).

## Onion services

An **onion service** (the older name is hidden service) is a server that can only be reached over Tor. The Tor Project's community page (read 2026-10-31) lists what you get:

- **Location hiding.** The server's IP address is protected; the address people use is not an IP address at all but, in the page's words, "the identity public key of the Onion Service."
- **End-to-end authentication.** Because the address is the key, the client can check that what it reaches really belongs to that address.
- **End-to-end encryption** from client to service.
- **No open inbound port.** The service only makes outgoing connections, so it can sit behind a firewall or a home router.

In short: the service picks a few relays as introduction points, publishes a signed description of itself, and the client and service meet at a relay the client picks (the rendezvous point). The whole connection uses six relays, three chosen by the client and three by the service. The same page uses a newspaper's tip line (SecureDrop) as its example, which is the use most people never hear about.

Note what an onion service is **not**: it is not a hiding place for the person who runs it, unless they also protect themselves everywhere else (see [what none of these protect against](#what-none-of-these-protect-against)). It is a way to reach a service without either side learning the other's network location.

## Who uses these networks

The tools' own pages are the best evidence for who they are built for, so these are quoted as the projects' claims, not measured:

- **Journalists and sources, dissidents, activists, researchers.** The Whonix overview names investigators and whistleblowers, researchers and officials who may be espionage targets, journalists reporting on organized crime, political activists, and "average computer users in a repressive or censored environment." The Qubes introduction says it supports "journalists, activists, whistleblowers, and researchers." The Tor Project's history page credits Tor with a role during the Arab Spring from late 2010. (All read 2026-10-31.)
- **Ordinary people.** The Whonix overview also lists "average computer users who simply don't want all or some aspect of their private lives uploaded, saved and analyzed." Tails' page makes the same point: Tor stops trackers "from one website to another."
- **People who are not harmless.** The Tor Project's own page says some people use Tor "for nefarious purposes." Law enforcement can and does investigate crime that involves these networks. Whether a given use is legal depends on where you are and what you do (see [the law](#the-law-in-one-paragraph)).

## The tools and what each is for

| Tool | What it is | Built for | Wrong tool when |
|---|---|---|---|
| **Tor Browser** | A hardened Firefox that sends its traffic over Tor. | Anyone who wants private browsing without installing a whole operating system. | You need every application, not only the browser, to go over Tor; or the machine itself is not trustworthy. |
| **Tails** | A live operating system you start from a USB stick. It "never writes anything to the hard disk", runs from memory, forgets everything at shutdown, and sends everything it does over Tor. | A person on the move who borrows or finds a machine, and does not want to leave a trace on it. | Your own machine, every day, always the same hardware (below). |
| **Whonix** | Two virtual machines on a host: a Gateway that runs Tor and a Workstation that runs your applications on a network that only reaches the Gateway. | Someone who wants a full desktop where every connection goes over Tor and a leak is hard. | You cannot run virtual machines, or you need a disposable, leave-no-trace session on someone else's machine. |
| **Qubes OS** | A general-purpose desktop built from isolated virtual machines ("qubes") on the Xen hypervisor. Whonix can run inside it. | A person who wants to keep risky and valuable activities apart on one computer, as a daily system. | You want something to try in an afternoon; the project says prior Linux experience helps. |

Sources: Tor Browser, Tor Project support page; Tails, the Tails "How Tails works" page; Whonix, the Whonix overview; Qubes, the Qubes introduction (all read 2026-10-31).

### Tails, and why "which hardware" changes everything

Tails describes itself with a tent: carry it anywhere, and it leaves no trace when you leave. Its page says you can "stay safe while using the computer of somebody else" and that it "always starts from the same clean state." Its Persistent Storage is optional and encrypted, and you choose what persists.

The point of Tails, then, is **amnesia on hardware you do not control**: a library computer, a borrowed laptop, a machine you will never see again. The clean start protects you from what is on that machine, and the shutdown protects that machine from keeping what you did.

If you use Tails on your **own** computer, always the same one, the threat model changes. The "leave no trace on the hardware" benefit counts for less, because the hardware is yours and returns to you. Meanwhile the things Tails cannot fix are still there: the Tails warnings page says it cannot always protect you if you install it from an infected computer or run it on a machine with compromised firmware, or a physical keylogger. That reasoning is the maintainer's framing, stated in the issue, and I have not seen a Tails page that says "do not use this at home" (the Tails page in fact says you can turn your own computer into a secure machine temporarily), so treat it as a judgment about fit, not a rule from the project. The conclusion for this lesson: for an everyday, always-on, same-hardware setup Tails is the wrong tool, and it is mostly a beginner experiment there. Whonix on a host you maintain, or Qubes, are built for the daily case.

### Whonix, Qubes and how they differ

- **Whonix** is about *network* safety. Because the Workstation only reaches the Gateway, the Whonix overview says "DNS leaks are impossible" and that malware with root privileges inside the Workstation "cannot discover the user's real IP address." Those are the project's claims about its design; I did not test them. Whonix runs on top of a normal host OS (it names VirtualBox and KVM) or inside Qubes.
- **Qubes OS** is about *containment*. Its introduction says it is designed "under the assumption" that software bugs will be exploited, so it tries to "confine, control, and contain the damage" by running different activities in different virtual machines, with disposable qubes that vanish when closed. It integrates Whonix as the way to "run Tor securely system-wide."
- **Tails** is about *leaving nothing behind*, with Tor for everything.

Put plainly: Tails forgets, Whonix keeps your network path inside Tor, and Qubes keeps your activities apart. They solve different problems and can be combined (Whonix inside Qubes). The Whonix site publishes its own comparison of itself with Tails and Tor Browser; it is the project's view of itself, I did not rely on it here, and you should read it as one side.

## What none of these protect against

Every project above says some version of this; the lists agree.

- **A compromised endpoint.** If malware or a physical keylogger is on the computer, anonymity does not matter. The Tails warnings page says no operating system can protect against firmware or hardware attacks and that Tails cannot always protect you on a compromised machine or when installed from one. Qubes' answer is containment, not immunity.
- **Behavior and correlation mistakes.** The Tails warnings page names the common ones: files that carry metadata such as date, time, location and device information; using one Tails session for several purposes so that an adversary can link them (it advises restarting between activities); and logging into different accounts on the same site in one session. Logging in to an account that is yours, with your real name, over Tor tells the website who you are, whatever Tor hides.
- **Logins and habits that identify you.** Anything you type or upload that points to you does. This is true of every tool on this page.
- **A watcher at both ends.** Timing and traffic-shape correlation, from the Tor Project's and Tails' pages above. Tails says it knows of no actual use of this against Tails users but that no anonymity network for fast traffic can protect fully.
- **The exit relay, for unencrypted traffic.** The Tails warnings page says the last relay can see traffic that is not encrypted, so use HTTPS wherever the site offers it.
- **Being noticed using Tor.** Your provider, a network or a country that blocks Tor can see or block it; websites can tell you use Tor because exit relays are public; many sites show a CAPTCHA or block Tor (Tails warnings page).
- **Mistakes of your own.** Qubes says outright that it is designed "with the understanding that people make mistakes", and no tool replaces care.

None of this means "do not bother." It means these tools answer a narrow question, who can see where this traffic comes from and goes, and say nothing about whether the machine is clean, whether your habits give you away, or whether the thing you are doing is wise.

## Worked example: a Monero node over Tor and I2P

Monero is a cryptocurrency that is designed around privacy. It is a good place to see privacy and security side by side, because running a node involves both: *privacy* (can someone tell that this transaction came from my address?) and *security* (can someone get into my node, or my wallet?). The lesson on privacy versus security, not yet written, will treat the difference in general; this section shows one concrete case.

> **Whose words.** The issue behind this lesson says the maintainer has run a Monero node over Tor and has contributed to the PiNodeXMR project. That is repeated here as his own statement from the issue, with nothing added. Everything below about how Monero and PiNodeXMR work comes from those projects' own documents, read on 2026-10-31.

### What the Monero project says a node can do over Tor and I2P

The Monero project's `ANONYMITY_NETWORKS.md` (the file in its main repository, read 2026-10-31) says:

- **Only Tor and I2P are integrated, and the use is still "experimental".** The document says there are "a few pessimistic cases where privacy is leaked."
- **The point is hiding where a transaction was first sent from.** The design is "to maximize privacy of the source of a transaction by broadcasting it over an anonymity network," while using ordinary IPv4 connections for the remaining traffic, to make surrounding-node attacks (sybil attacks) harder.
- **A transaction your own wallet sends to your node is relayed only over the anonymity network** when one is enabled (the document says broadcast transactions that did not come from a peer connection "will only be sent to peers on anonymity networks"), and if none is available the transaction waits.
- **Syncing the blockchain is not done over onion or I2P services.** It uses IPv4, which can go through a SOCKS proxy; the document says exclusive hidden-service operation "is not currently supported."
- **Your provider may still see something.** The document's example for relaying over Tor while syncing over the clearnet notes that this reveals to your ISP that you run a Monero node; a different example, with sync also sent through Tor, says your ISP "will see that you are running Tor, but not Monerod."

Here is the document's own example for relaying transactions over Tor (quoted, not tested):

```bash
monerod --tx-proxy tor,127.0.0.1:9050,10
```

It names its own privacy limits. In summary, from the document: the node's timestamps in peer messages can help link an onion connection to an ordinary one; a node that is switched on only to send a transaction and then quits can be linked by a provider to that transaction; an attacker shaping bandwidth might try to find the source; and reusing one stream for several transactions can let the service operator connect them. The document's advice for people who send transactions often is that Tor or I2P "will improve privacy from ISPs and other common adversaries, but still have some metadata leakages to unknown hidden service operators." That is a calm, honest statement of exactly what the tool buys you.

### A private node used like a VPN to your own wallet

The second use is different: not hiding a broadcast, but reaching your own node from your own wallet. The Monero project's Tor wallet guide (read 2026-10-31; it says it was tested with Monero v0.15.0.1, so it is old) describes running a daemon at home or on a server and connecting a wallet on another computer to it **over a Tor hidden service**. Its stated benefits: the daemon can stay on all the time while the wallet connects when needed; the hidden service provides encryption and authentication, so RPC credentials are not sent in the clear; and Tor "solves problems often seen on home servers related to port-forwarding, IP addresses changing", and obscures the fact that you are connecting to a remote Monero node. The guide also warns that using the graphical wallet through `torsocks` "may leak info" and not to rely on it "if your life depends on maintaining anonymity."

That is the same shape as a VPN back to your own network: a private path to your own machine, no public port. It is not a VPN; it is an onion service, with the properties in [the onion services section](#onion-services).

### What PiNodeXMR documents

PiNodeXMR is an open-source suite that sets up a Monero node on a small computer. Facts below come from its own repository and wiki, read on 2026-10-31. The repository I read was the upstream project (owned by its original author, not the maintainer of this wiki), at commit `c0c80f1` dated 2026-10-18; its wiki, at commit `fb2a6d5` dated 2025-05-20. The license shown on the repository is GPL-3.0.

- **The README** says PiNode-XMR "can provide a Full or Pruned Monero Node and optional integration with tor/I2P", with extra tools such as a block explorer, and that normal interaction is through a web interface reachable from any device on the local network. It is built on Ubuntu Server LTS.
- **Tor mode.** The wiki page "How PiNode-XMR implements tor usage" says Tor is installed from the setup menu, that it creates a hidden service for the node, and that the node's start command sends outgoing transactions through Tor with `--tx-proxy` and accepts inbound connections at the onion address with `--anonymous-inbound`. The Node Control page text in the repository says these Tor and I2P modes run as a private node (RPC login required), "broadcasting your transactions exclusively over an anonymity network," that this "can assist in obscuring the origin" of a transaction "if used correctly", and that the node still uses the IPv4 clearnet to sync the blockchain. The wiki says you can connect a Tor-wrapped wallet to the node's onion address on port 18081 with the RPC username and password.
- **A caution the project itself writes.** The wiki's Tor page says that once a transaction is in the node's memory pool it "requires good tor peer connections in order to broadcast," and that finding a working seed peer "took me a while." So it works, but it can need patience.
- **Tor is not installed by default.** The Manual says Tor is no longer included by default "due to censorship, political or legal restriction of users host country," and is installed on request. That sentence is the project's own version of this page's law paragraph.
- **I2P mode.** The wiki page "i2p Setup" says I2P became available as an optional anonymity network from v4.x.x, is not installed by default, and starts with "Please do your research for if you think this tool is suitable for usage and needs." You install the full I2P package, create a hidden service and a SOCKS tunnel in the I2P console, enter their values in the Node Control page, start the "I2P: Private Bridging Node", and if you see no I2P connections after about 20 minutes, try another seed node. The start script in the repository passes the matching `--anonymous-inbound` and `--tx-proxy i2p,...` options.
- **VPN access.** The setup menu offers PiVPN, installed from the PiVPN project, and the Manual describes it as a tool "enabling you to run your own home VPN." In its section on connecting a wallet from outside your home, the Manual lists a VPN as one option, saying you "may be able to connect your mobile device to your home network so your wallet connects as though you are still at home," that it "may be the preferable method for privacy," and, in the author's words, "I have not used this method", with a note asking for community input. That is as far as the project documents it; I read no PiVPN setup walkthrough and do not describe one.

What the project's documents do **not** say: they do not claim PiNodeXMR makes you anonymous, and nothing I read describes testing that the Tor or I2P modes hide a broadcast from a real adversary. I did not evaluate PiNodeXMR's own security and do not claim anything about it.

### The maintainer's contributions, from public history only

I looked at the public history of the upstream repository on 2026-10-31, using read-only GitHub queries for the handle `ChiefGyk3D`:

- The commit list of the upstream repository's default branch, which has about 958 commits, shows **no commits attributed to that handle**. (GitHub attributes a commit to a handle by the author's email address, so this tells you about attribution, not about whether the work exists.)
- The repository's public pull request list shows **pull requests opened under that handle from a fork**, going back to 2020 and including recent ones in 2026. One body of recent work is a security review. This page says nothing further about it.

I describe contributions this way, in general terms and without names or titles, at the maintainer's request.

### Where privacy and security overlap and differ

| Question | Privacy | Security |
|---|---|---|
| What is it about? | Who can learn where a transaction came from, or that you use Monero at all. | Whether someone can get into the node, read the wallet or change something. |
| What does Tor or I2P do here? | Hides the network origin of a broadcast. | Nothing about the node's patch level, passwords or the machine it runs on. |
| What does a private RPC login do? | Little for anonymity. | Stops strangers using your node. |
| What does an onion address for RPC do? | Hides where the node is. | Gives encryption and authentication on the path, per the Monero guide. |
| What breaks it? | Timing, reuse, running the node only when you transact, logins that identify you. | Unpatched software, weak credentials, an exposed port, a compromised machine. |

In CIA triad terms ([the CIA triad](The-CIA-Triad-Confidentiality-Integrity-Availability.md)), privacy is a form of *confidentiality about who you are and what you do*; hiding it does not make the *integrity* or *availability* of your node any better. A node that is anonymous and unpatched is still a compromised node. A node that is patched and has an identifying IP is still a node whose origin is known. You need both, and the later lesson on privacy versus security takes that further.

## The law in one paragraph

Laws differ by country, and sometimes by state or by network (a school, a company, a hotel). In many places using Tor or I2P is legal, in some it is restricted, and in some it is blocked or risky; what you do through them is judged by the law of the place you are in, as it would be anywhere else. PiNodeXMR's own Manual makes the same point about its Tor feature. I have not checked any country's rules for this page. **Check your own jurisdiction, and your employer's or school's rules, before you install or run any of these tools.** Nothing here is legal advice.

## Exercises (reading only, nothing to install)

1. **Read a threat model.** For one person you can picture (a journalist with a source, a student on a school network, you), write three lines: who might watch, what they could learn, and which tool above changes that. Then write one thing the tool does not change. Use [Threat model](Threat-Model.md) for the vocabulary.
2. **Spot the leak.** A person uses Tor Browser to log in to a social media account under their real name. What did Tor hide, and what did the login reveal? (Answer: it hid the network location; the login identified the person.)
3. **Match the tool.** For each, name the tool from the table: a borrowed laptop in a library; a daily desktop where a risky link must not reach your banking; a browser for one afternoon of reading. (Answers: Tails; Qubes; Tor Browser.)
4. **Test a scary claim.** Find one frightening claim about "the dark web" and decide whether it gives a source you can open yourself. Write down what you could and could not check.

## Not verified, plainly

- Nothing was run (see the banner). In particular I did not test that a PiNodeXMR Tor or I2P mode hides a broadcast.
- The Tor Browser manual page I fetched held only a menu, so Tor Browser's security levels and its other features are not described here from that manual; the Tor Browser row rests on the Tor support page and the Tails pages.
- I did not read I2P's own comparison with Tor, Qubes' threat model page, Whonix's pages on host security or Monero's general "what is Monero" pages, so the page makes no claims on those.
- The remark that the clearnet holds far more danger than the darknet is the maintainer's view, not something I measured.
- No country's law was checked.
- GitHub attribution of commits depends on author email addresses, so "no commits attributed to the handle" is about attribution only.

## Claims register

Every row carries a status: **Read** means the sentence is on the page named, read on **2026-10-31**; **General knowledge** means common knowledge I did not source; **est.** means I could not read it on a project page.

| Claim | Source | Status |
|---|---|---|
| Tor is a program that routes traffic through volunteer relays so sites do not learn your location and watchers do not learn the sites you visit; most people use it through Tor Browser, a Firefox version | Tor Project, [What is Tor?](https://support.torproject.org/about/what-is-tor/) | Read 2026-10-31 |
| Tor routes through more than one relay so no single relay learns what you are doing; distributed trust beats a one-hop proxy | Tor Project, [Protections Tor provides](https://support.torproject.org/about/protections/) | Read 2026-10-31 |
| Tor does not defend against an observer who sees both ends and correlates timing | Tor Project, [Remaining attacks](https://support.torproject.org/about/attacks-on-onion-routing/) | Read 2026-10-31 |
| "Criminal intent lies with the individuals and not the tools they use"; Tor can help fight identity theft and stalking and be used by law enforcement | Tor Project, [Doesn't Tor enable criminals?](https://support.torproject.org/abuse/what-about-criminals/) | Read 2026-10-31 |
| Onion routing dates from 1995 at the U.S. Naval Research Laboratory; Tor Browser began in 2008; Tor was used during the Arab Spring from late 2010; thousands of relays | Tor Project, [History](https://www.torproject.org/about/history/) | Read 2026-10-31 |
| Onion service: location hiding, end-to-end authentication and encryption, no open inbound port, six relays in all, address is a public key | Tor Project, [Onion services overview](https://community.torproject.org/onion-services/overview/) | Read 2026-10-31 |
| In a three-relay circuit, the first relay knows where you come from and the third knows where you go; your provider sees that you use Tor; exit relays can see unencrypted traffic; VPNs are less secure than Tor for fast traffic | Tails, [Warnings](https://tails.net/doc/about/warnings/index.en.html) | Read 2026-10-31 |
| Tails starts empty from the same clean state, never writes to the hard disk, runs from memory, sends everything over Tor, has an optional encrypted Persistent Storage, and can be used on your own or someone else's computer | Tails, [How Tails works](https://tails.net/about/index.en.html) | Read 2026-10-31 |
| Tails cannot always protect you if installed from an infected computer, or on a machine with compromised firmware or a keylogger; metadata and using one session for several purposes can link your activities | Tails, [Warnings](https://tails.net/doc/about/warnings/index.en.html) | Read 2026-10-31 |
| Using Tails on your own always-the-same machine changes the threat model, so it is the wrong tool for an everyday setup | The maintainer's framing in issue 358 | Read in the issue; a judgment, not a Tails statement (**est.**) |
| I2P: tunnels are one-way, so a round trip needs four; garlic routing as a concept is identical to onion routing; garlic also means bundling messages ("cloves") and a form of end-to-end encryption; the term has been used loosely | I2P, [Garlic routing](https://geti2p.net/en/docs/how/garlic-routing) (updated 2025-10) | Read 2026-10-31 |
| I2P hides what a user does and which router a destination is connected to, not usually the fact that someone runs I2P | I2P, [Introduction](https://geti2p.net/en/about/intro) (updated 2025-01, accurate for 0.9.65) | Read 2026-10-31 |
| Whonix is two virtual machines (Gateway runs Tor; Workstation is isolated), runs on a host OS or in Qubes, and its stated user groups include journalists, whistleblowers and ordinary users | Whonix, [Overview](https://www.whonix.org/wiki/About) | Read 2026-10-31 |
| Whonix "DNS leaks are impossible" and malware with root cannot discover the real IP | Whonix, [Overview](https://www.whonix.org/wiki/About) | Read 2026-10-31 (the project's claim; not tested) |
| Qubes OS is a Xen-based system of isolated qubes (virtual machines), assumes bugs will be exploited, aims to confine and contain damage, integrates Whonix, is aimed at journalists, activists, whistleblowers and researchers, and says Linux experience can help | Qubes OS, [Introduction](https://doc.qubes-os.org/en/latest/introduction/intro.html) (docs 4.3.2, page last edited 2026-04-22) | Read 2026-10-31 |
| Only Tor and I2P are integrated in Monero and use is experimental; the design hides the source of a transaction by broadcasting over an anonymity network while syncing over IPv4; the listed privacy limits | Monero project, [`ANONYMITY_NETWORKS.md`](https://raw.githubusercontent.com/monero-project/monero/master/docs/ANONYMITY_NETWORKS.md) (main branch, as of the read date) | Read 2026-10-31 |
| Connect a wallet to your own daemon over a Tor hidden service; benefits and the `torsocks` warning; tested with Monero v0.15.0.1 | Monero project, [Connecting your local wallet to your own daemon over Tor](https://www.getmonero.org/resources/user-guides/tor_wallet.html) | Read 2026-10-31 |
| PiNodeXMR README: full or pruned node, optional tor/I2P integration, web interface on the local network, Ubuntu Server LTS base | [shermand100/PiNodeXMR](https://github.com/shermand100/PiNodeXMR) `README.md` at commit `c0c80f1` (2026-10-18) | Read 2026-10-31 |
| PiNodeXMR license is GPL-3.0 | GitHub repository metadata for the same repository | Read 2026-10-31 |
| PiNodeXMR Tor mode: installed from the setup menu, hidden service, `--tx-proxy` and `--anonymous-inbound`, RPC on the onion address port 18081; broadcast can need good seed peers | PiNodeXMR wiki, "How PiNode-XMR implements tor usage", at wiki commit `fb2a6d5` (2025-05-20) | Read 2026-10-31 |
| PiNodeXMR Node Control text: Tor and I2P modes are private nodes that broadcast over an anonymity network and still sync over IPv4 clearnet | PiNodeXMR repository, `HTML/nodeControl.html` at commit `c0c80f1` | Read 2026-10-31 |
| PiNodeXMR Tor is not installed by default, because of restrictions in some countries | PiNodeXMR wiki, "Manual", at wiki commit `fb2a6d5` | Read 2026-10-31 |
| PiNodeXMR I2P mode is optional, not installed by default, uses the full I2P package, needs a hidden service and a SOCKS tunnel made by the user | PiNodeXMR wiki, "i2p Setup", at wiki commit `fb2a6d5`; start script `home/pinodexmr/execScripts/moneroI2PPrivate.sh` at commit `c0c80f1` | Read 2026-10-31 |
| PiNodeXMR offers PiVPN (OpenVPN) from its setup menu; the Manual lists a VPN as one option for outside access and says the author has not used the method | PiNodeXMR wiki "Manual" at wiki commit `fb2a6d5`; `home/pinodexmr/setupMenuScripts/setup-PiVPN.sh` at commit `c0c80f1` | Read 2026-10-31 |
| The upstream commit list shows no commits attributed to the handle ChiefGyk3D; pull requests from the handle's fork exist, from 2020 and 2026 | GitHub API, commits and pull requests of the upstream repository | Observed 2026-10-31 |
| The maintainer has run a Monero node over Tor and contributed to PiNodeXMR | Issue 358 (the maintainer's statement) | Read in the issue; not otherwise checked |
| The clearnet holds more danger than the darknet; much darknet scare content is exaggerated | The maintainer's framing in issue 358 and general knowledge | General knowledge (**est.**; not measured) |
| Laws on using Tor and I2P differ by place | General knowledge | General knowledge; no country checked |

## Maintainer notes to add

Questions I could not answer from public sources. Answer any you like and the page can be updated.

1. Which of PiNodeXMR's Tor and I2P modes do you run, on what hardware, and for how long? The issue says you ran a node over Tor; the page adds nothing beyond that.
2. How do you want your PiNodeXMR contributions described? The page says only that you contribute with pull requests, including recent ones, and that one body of work is a security review. I could not tell what is public about that work, so I added nothing more; say if you want it described further.
3. The upstream commit list shows no commits attributed to your handle. Is that expected? The page states only the attribution fact.
4. Do you want the "wrong tool for an everyday, always-on setup" Tails position stated more strongly, softened, or tied to a particular example of your own?
5. Do you use a VPN to your own node in addition to or instead of Tor? PiNodeXMR's Manual says its author has not used the VPN method; the page documents it only as the project does.
6. Do you want a Whonix or Qubes hands-on exercise, or should this stay a reading lesson?
7. Which jurisdiction(s) do you want named as examples in the law paragraph, if any? I named none.
8. Should I2P's own comparison with Tor and Qubes' threat-model page be added to the sources? I did not read them.
