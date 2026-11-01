# Radio and off-grid communication: what still works when the internet and the power do not

<!-- BEGIN GENERATED PAGE NAV top: rewritten from docs/wiki/_nav.yaml by scripts/gen_wiki_nav.py; edit the manifest, not this block -->
[Home](Home.md) > [Track 3: Privacy, anonymity and cryptocurrency](Contents.md#track-3-privacy-anonymity-and-cryptocurrency) > Radio and off-grid communication

Previous: [Running Monero properly](Running-Monero-Properly-Hardware-Wallet-Qubes-and-Whonix-Offline-Wallet-and-PiNodeXMR.md)
<!-- END GENERATED PAGE NAV top -->

<!-- BEGIN GENERATED PAGE CONTENTS: rewritten from the page's own headings by scripts/gen_wiki_nav.py; edit the headings, not this block -->
**On this page:**

- [What you will be able to do](#what-you-will-be-able-to-do)
- [What the wiki already says (and the gap)](#what-the-wiki-already-says-and-the-gap)
- [When the internet and the power go out: what still works](#when-the-internet-and-the-power-go-out-what-still-works)
- [Wi-Fi, and why it is not the only radio](#wi-fi-and-why-it-is-not-the-only-radio)
- [LoRa, Meshtastic, MeshCore and Reticulum](#lora-meshtastic-meshcore-and-reticulum)
- [Wi-Fi HaLow (IEEE 802.11ah) next to LoRa](#wi-fi-halow-ieee-80211ah-next-to-lora)
- [Amateur (ham) radio](#amateur-ham-radio)
- [GMRS and FRS](#gmrs-and-frs)
- [Citizens band (CB)](#citizens-band-cb)
- [Signals intelligence (SIGINT): a careful overview](#signals-intelligence-sigint-a-careful-overview)
- [Why radio is a common hobby among security people](#why-radio-is-a-common-hobby-among-security-people)
- [Radio in a continuity plan for this project](#radio-in-a-continuity-plan-for-this-project)
- [Free exercises: offline, listen-only and simulation](#free-exercises-offline-listen-only-and-simulation)
- [Checkpoint](#checkpoint)
- [Common mistakes](#common-mistakes)
- [Where to next](#where-to-next)
- [Claims register](#claims-register)
<!-- END GENERATED PAGE CONTENTS -->

Side page to the continuity pages. Read it after [Business continuity and disaster recovery](Business-Continuity-and-Disaster-Recovery-BCP-and-DR.md), which asks what must keep working, who does what and in what order it comes back, and after [The CIA triad](The-CIA-Triad-Confidentiality-Integrity-Availability.md), because everything here is about availability and about what a listener can learn. That lesson's contact tree has a hole in it: every channel on it usually needs the internet. This page is about the channels that do not. It covers wifi and the other radios beside it, LoRa mesh systems (Meshtastic, MeshCore and Reticulum), Wi-Fi HaLow (the sub-1-GHz Wi-Fi that competes with LoRa for some jobs), amateur radio, GMRS and FRS, CB, a careful overview of signals intelligence (SIGINT) with the legal rules first, and what a radio fallback could and could not do for this project. For what a key is and how it is lost, read [Hashing, encryption and keys](Hashing-Encryption-and-Keys.md); the [cryptography lesson](Cryptography-Fundamentals-Symmetric-Asymmetric-Hashing-Certificates-and-Keys.md) (issue 360) goes deeper.

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

> **Status: unverified draft. Written from reading; no transmitter was keyed and no radio was configured, for this page or in writing it.** On **2026-10-31** I read the project pages, the regulator text and the legal text listed in the [claims register](#claims-register), and I ran exactly one thing: the arithmetic script in [Exercise 2](#exercise-2-run-the-script-and-compare-it-with-your-prediction), which does sums and nothing else. **Not run:** every radio, every firmware and app, every setting in any config shown, a real link or range test, any live emergency procedure, and a tabletop with other people. **Not read:** the FCC's own web pages (they refused a plain download, see the register) and the NSA's SIGINT page (same). The United States rules come from the Code of Federal Regulations as published by eCFR, edition **2026-10-29**, and from the United States Code as published by Cornell's Legal Information Institute, both read on 2026-10-31. Rules change; read the current text before you act. The [Wi-Fi HaLow section](#wi-fi-halow-ieee-80211ah-next-to-lora) was added on **2026-11-01** from the sources the claims register dates that day; I keyed no transmitter and ran nothing for it either. **Not read for HaLow:** the text of the IEEE 802.11ah amendment (only the standard's abstract page), the FCC's own pages, any HaLow product's FCC grant, and any list of HaLow bands outside the United States. The maintainer's own experience beyond the license class and the five services named below is not stated on this page. This is education and not legal advice, and a lawyer or your regulator has the last word.

> **Prerequisites.** [Business continuity and disaster recovery](Business-Continuity-and-Disaster-Recovery-BCP-and-DR.md) for RTO, RPO and a contact tree, and [Networking basics for this project](Networking-Basics-for-This-Project.md) for what a link and a hop are. The exercises need a computer with Python 3 and a pencil. No radio, no account, no cost. About 2 hours (est.).

> **Where this runs and what it will never do.** On paper and on your own computer. **Nothing here transmits.** No exercise keys a transmitter, configures a live radio, flashes firmware or opens a connection. Never key a transmitter, or configure a live radio, from this page: a drill is not an emergency and an example is not an authorization. Every callsign is the placeholder **N0CALL** or **N0TST** and every grid square is **FN31pr**; if you have a real one, keep it out of your notes, your issues and your commits, as the [Give feedback](Give-Feedback-and-Open-an-Issue.md) page also asks. Any live step is for a qualified, licensed operator who has checked the current rules for their own country, band and equipment.

## What you will be able to do

- Say which communication paths still work when the internet is down, which also survive a power cut, and what each one needs.
- Say what LoRa is, and what Meshtastic, MeshCore and Reticulum each are, how their routing differs, and what they can and cannot carry.
- Say what Wi-Fi HaLow (IEEE 802.11ah) is, how it differs from LoRa and from ordinary Wi-Fi, and when each fits an off-grid job, with the rules read first.
- Work out the time on air of a LoRa packet and what that does to capacity, with a small script you can read.
- Name the United States amateur license classes and what a General class license adds, say what emergency communications means in the amateur service, and say where amateur radio does not fit a business.
- Tell GMRS, FRS and CB apart by license, power and use.
- State, legal rules first, what receive-only radio monitoring is generally allowed in the United States, where the law stops, and why encryption and good habits still matter.
- Say why radio is a common hobby among security people, and say honestly what this project has for a radio fallback (nothing yet).
- Draw a communications tree for a three day outage on paper.

## What the wiki already says (and the gap)

| Idea | Where it is today | The gap this page fills |
|---|---|---|
| Contact trees, out-of-band communication, holding statements | [Business continuity and disaster recovery](Business-Continuity-and-Disaster-Recovery-BCP-and-DR.md#runbooks-contact-trees-roles-and-communications) | A contact tree whose second channel needs neither the internet nor the mains. |
| Availability as one of three properties; confidentiality of what is sent | [The CIA triad](The-CIA-Triad-Confidentiality-Integrity-Availability.md) | What an over-the-air message gives away to anyone with a receiver. |
| Limiting what one failure can reach, and assuming a breach | The lesson on planning for failure (blast radius and assuming breach), named here in plain text | A radio is a shared medium: anyone in range is inside the "blast radius" of what you transmit. |
| Keys, hashes and encryption in general | [Hashing, encryption and keys](Hashing-Encryption-and-Keys.md) | Which radio systems encrypt what, and where the rules forbid encryption. |
| This project's public edge design carries Reticulum and a Meshtastic MQTT broker over the internet | [The DMZ and hardening a host that faces the internet](The-DMZ-and-Hardening-a-Host-That-Faces-the-Internet.md) | That design is about internet hosts, not radio hardware. This page says what it does and does not give a radio fallback. |
| Remote access that depends on a connector and an identity service | [Zero trust at home: two connectors and failover](Zero-Trust-at-Home-Two-Connectors-and-Failover.md) | What remains when the connector's internet is gone. |

## When the internet and the power go out: what still works

Ready.gov's power outage page (read 2026-10-31, shown as last updated 06/04/2026) says an outage may disrupt communications, and tells you to find out whether your home phone works without power and how long its battery backup lasts. That is the right first question for every row below: **what does it need that the outage takes away?**

| Option | Needs the internet? | Needs mains power at your site? | Typical reach | Status |
|---|---|---|---|---|
| Wifi inside a building | No, for traffic that stays on the local network | Yes, for the router or access point | One building | General knowledge |
| Cell phone | No for calls and texts, but it needs the carrier's network | Your phone, no. The tower, yes, and I did not read how long towers keep running | The tower's coverage | General knowledge; **est.** |
| Home phone | Depends on the line type | Depends: Ready.gov says to check it and its battery backup | The line | Read (Ready.gov) |
| Battery-powered AM or FM broadcast receiver | No | No | The broadcaster's coverage; one way only | General knowledge |
| FRS or GMRS handheld radio | No | No (batteries); a GMRS repeater needs power | Short; line of sight | Rules Read, reach General knowledge |
| CB | No | A vehicle or base supply | Short; line of sight | Rules Read, reach General knowledge |
| Amateur radio | No | Batteries or a generator | VHF and UHF local; HF regional to worldwide | Read (ARRL says it can work independently of the internet and phone systems) |
| LoRa mesh (Meshtastic, MeshCore, Reticulum over LoRa) | No | Small batteries or solar | Kilometers, with caveats below | Read (project docs) |
| Wi-Fi HaLow (sub-1-GHz Wi-Fi) | No, for traffic that stays on the local network | Yes, for a normal access point (General knowledge) | About 1 km, a Wi-Fi Alliance figure; see the HaLow section | Read (Wi-Fi Alliance, IEEE); hardware is newer and less common |

Satellite messengers and satellite phones also exist. I did not read about any, so this page does not cover them.

## Wi-Fi, and why it is not the only radio

Wifi is a radio. It is an unlicensed one: 47 CFR 15.247 (read 2026-10-31) covers frequency-hopping and digitally modulated devices in the 902 to 928 MHz, 2400 to 2483.5 MHz and 5725 to 5850 MHz bands, and 2.4 GHz is where much wifi lives (General knowledge for the link to wifi). Three things follow, and none needs a license to understand.

1. **Wifi without the internet still works** for devices on the same router: printers, a local server, a chat app you host yourself. What stops is anything that goes out through the uplink, such as your cloud accounts, your identity service and your DNS (General knowledge).
2. **Wifi is short range and needs mains power** in the router. It is a good last meter and a poor fallback for a neighborhood.
3. **Every other radio on this page makes a different trade.** Lower frequencies go farther and through more; narrower, slower signals reach farther per watt; licensed services give you rules and sometimes protection from interference; unlicensed ones give you freedom and give up that protection. LoRa and the licensed services below are how people get kilometers on a battery. Wi-Fi HaLow is a fourth trade: still Wi-Fi, but in the sub-gigahertz band, with the [HaLow section](#wi-fi-halow-ieee-80211ah-next-to-lora) comparing it with LoRa.

The Meshtastic documentation says Meshtastic uses the radio spectrum designated to LoRa in each region, and that it is not LoRaWAN, Helium or TheThingsNetwork (read 2026-10-31). A LoRaWAN gateway needs an internet backhaul; a Meshtastic mesh does not.

## LoRa, Meshtastic, MeshCore and Reticulum

**LoRa** is a radio modulation (chirp spread spectrum) made for long range, low power and low data rates. Meshtastic's overview describes it as sweeping a chirp across the set bandwidth, with the **spreading factor** (SF) deciding how many symbol values exist and how long each lasts: a higher SF gives more range and reliability and a lower data rate. Three settings set the shape of a LoRa link: SF, bandwidth (BW) and coding rate (CR, the amount of error correction). Two radios hear each other only if these match (read 2026-10-31).

The three systems below are not radios. They are software that sits on LoRa radios (and, for Reticulum, on many other links) and decides how a message gets from one node to another.

### Meshtastic

**What it is.** Open-source firmware that carries text messages and position reports across a mesh of nodes over LoRa, with no internet or cellular service (Meshtastic overview, version 2.8 documentation, read 2026-10-31).

**How its routing works.** Managed flooding. A node that hears a packet it has not seen waits a short random delay, weighted by the signal-to-noise ratio so that distant nodes tend to go first, and rebroadcasts unless it heard a neighbor already do so. Each relay lowers the packet's hop limit; at zero the packet stops. The hop limit defaults to 3 and cannot exceed 7. Since version 2.6 a direct message learns a next-hop relay and is sent only through that one node, falling back to flooding if the relay does not answer. Nodes in the router roles relay even when they heard a neighbor do it (Mesh Broadcast Algorithm page, LoRa configuration page, read 2026-10-31).

**What it carries.** A packet has a 16-byte cleartext header and a payload of at most 239 bytes; clients limit a message to about 200 bytes. A node must have its region set or it will not transmit. The US region is 902 to 928 MHz with a 30 dBm ceiling and no duty cycle limit in the firmware; EU_868 is 10 percent (LoRa configuration page). That 30 dBm figure is the firmware's ceiling, **not** a statement about what your hardware is certified for or what your national rules allow.

**Presets.** The default is Long Fast: SF11, 250 kHz, coding rate 4/5, a published 1.07 kbps and a link budget of 153 dB (assuming 22 dBm out and a 0 dB antenna). The nine general presets run from Short Turbo at 21.88 kbps to Long Moderate at 0.34 kbps (Radio Settings page). Both pages carry a "Last updated by dependabot[bot]" line and no date I could use, so the claims below say "read 2026-10-31" and nothing more.

### MeshCore

**What it is.** MeshCore's repository calls it "a lightweight, portable C++ library that enables multi-hop packet routing for embedded projects using LoRa and other packet radios", and the website presents it as a messaging system with end-to-end encrypted chat, public and private channels, and solar repeaters (GitHub README and meshcore.io, read 2026-10-31). The README says most of it is MIT licensed; its FAQ says everything is open source except the T-Deck firmware and some mobile apps (FAQ question 5.7).

**How its routing differs.** Companion (client) nodes do **not** repeat; only repeaters and room servers do, if set to (FAQ 5.2). A first message floods; the destination returns a delivery report listing the repeaters the message crossed; later messages carry that path and only matching repeaters retransmit (FAQ 5.4). Group (channel) messages always flood, and a repeater's administrator can refuse flood traffic past a hop count (FAQ 5.5). The firmware's hop limit is 64 (FAQ 2.5). Compare with Meshtastic, where every node may relay.

**Frequencies and settings.** The FAQ says it supports the 868 MHz range in the UK and EU and the 915 MHz range in New Zealand, Australia and the USA, and says that as of October 2025 many regions moved to a narrower setting, for example a recommended USA and Canada preset of SF7, BW 62.5 kHz, CR5 (FAQ 2.3). A community-recommended preset is advice, not a legal ruling.

### Reticulum

**What it is.** "A cryptography-based networking stack for building both local and wide-area networks with readily available hardware, that can continue to operate under adverse conditions, such as extremely low bandwidth and very high latency" (Reticulum manual 1.5.5, read 2026-10-31). It does not need IP. It runs over practically any medium that gives a half-duplex channel of at least 5 bits per second and a 500-byte MTU: LoRa through its RNode interface, packet radio TNCs, serial lines, wifi, Ethernet, or TCP over the internet.

**How its routing differs.** Every node can be a Reticulum instance; some are also **transport nodes**, which forward traffic. No single node knows the whole path; each knows only the way to get a packet one hop closer. Destinations make themselves known by **announces**, which are signed, forwarded with a hop count and limited by default to 2 percent of an interface's bandwidth. Link setup costs 3 packets totaling 297 bytes (Understanding Reticulum, What is Reticulum?).

**License and status.** The manual says the reference implementation is licensed under the "Reticulum License" and that the protocol was dedicated to the public domain in 2016. Read the license before you build on it.

### Side by side

| Aspect | Meshtastic | MeshCore | Reticulum |
|---|---|---|---|
| What it is | Firmware and apps for LoRa devices | A C++ routing library with ready firmware and apps | A networking stack, many media |
| Routing | Managed flooding; next-hop for direct messages since 2.6 | Clients do not repeat; flood to learn a path, then direct | Transport nodes with path tables; announces |
| Typical message | About 200 bytes of text, positions | Short text, rooms, sensor data | Anything, from a few bytes to large files, if the link allows |
| Hop limit | 3 by default, 7 at most | 64 in the firmware | 128 hops in the manual's convergence example |
| Needs LoRa? | Yes (also 2.4 GHz LoRa on some hardware) | Yes | No |
| Source | meshtastic.org | github.com/meshcore-dev | reticulum.network |

### Capacity and range realities

A LoRa link is **slow** and **shared**. Slow: Long Fast's raw rate is about one kilobit per second, before headers, retries and relaying. Shared: everyone on that preset and frequency slot takes turns on the same air. Meshtastic itself handles this by stretching position and telemetry intervals once more than 40 nodes are online, and its own worked example turns a one hour interval into about 168 minutes for 62 nodes on Long Fast (Mesh Broadcast Algorithm page). The script in Exercise 2 reproduces that number from the formula on the page.

**Time on air** is the thing to compute. It comes from the symbol time (2 to the power SF, divided by the bandwidth), the preamble, and the number of coded symbols for the payload. The script uses RadioLib's published implementation of the Semtech formula (the `getNumSymbols` function in `PhysicalLayer.cpp`, read 2026-10-31), which cites the SX1268 datasheet's section 6.1.4; I could not download the Semtech document itself. It also checks its own bit-rate formula against all nine published Meshtastic presets.

**Range** is a different kind of number. A link budget is how many dB of loss the link can take (transmit power minus receiver sensitivity, plus antenna gains). Free-space loss grows with distance and frequency, so a 153 dB budget is 1,176 km in free space, which no real path gets. Everything between a transmitter and a receiver (hills, trees, walls, a low antenna, the Earth's curve, a noisy neighbor) is taken out of the budget. The script prints how fast the free-space number collapses as you subtract an allowance. Treat the horizon and free-space formulas as illustrations (General knowledge): they are not in the sources I read.

| What the numbers tell you | What they do not |
|---|---|
| Rough order of magnitude for airtime and messages an hour | Whether your hill, your antenna and your neighbor's interference let a given hop work |
| That a 1 MiB file is hours of airtime on a shared channel, and a log stream is most of the channel | That a shared channel has a ceiling, and Meshtastic's firmware slows its own reports as a mesh grows | That a mesh scales to any size |
| That each step up in SF doubles airtime and adds about 2.5 dB of budget (Radio Settings page) | Any promise of range; the manual and the project pages promise none |

### Encryption and privacy caveats

| System | Encrypted | In the clear | Caveats (all Read 2026-10-31) |
|---|---|---|---|
| Meshtastic | Payload of every packet: channel messages with the channel's AES key (CTR mode, or AES-CCM with AEAD from firmware 2.8.1); direct messages with a key from X25519 and AES-256-CCM | The 16-byte header: sender and destination node numbers, packet ID, hop fields, channel hash | The default channel key `AQ==` is published, so default-channel traffic is public. No forward secrecy: a recorded message can be read later if the key leaks ("harvest now, decrypt later"). Plain AES-CTR does not detect tampering. An unsigned broadcast's sender is a claim, not a proof. Do not put a private key on an unattended node. Position sharing, node info and MQTT upload are separate settings that reveal more |
| MeshCore | Messages are described as end-to-end encrypted (meshcore.io) | The packet header and the path of repeater hashes; version 1 packets use 1-byte source and destination hashes and a 2-byte MAC (Packet Format page) | The FAQ publishes the default public channel's key, so that channel is public. Group text and data packets are marked "unverified" in the packet format. I did not read a cryptographic specification, so I make no claim about its algorithms |
| Reticulum | Everything by default: X25519 and Ed25519 keys, AES-256-CBC with an HMAC-SHA256 token; links have forward secrecy; a per-destination ratchet option adds it to single packets | Announces (destination hash, public key and any application data, signed) | No source address on packets and initiator anonymity are design goals. Announces still tell the network a destination exists. An interface passphrase (an IFAC) signs packets to keep strangers off an interface |
| Amateur radio | **Not allowed**: no message encoded to obscure its meaning (47 CFR 97.113(a)(4)) | Everything, including the callsign you must send | Meshtastic's docs say that in its amateur regions encryption is not permitted and the callsign must be sent, and that licensed mode sends everything unencrypted |
| GMRS and FRS | Not allowed on GMRS: no coded messages or hidden meanings (95.1733(a)(3)); voice scrambling cannot be certified in new Personal Radio Services transmitters (95.381) | Voice | "10 codes" are permitted on GMRS |

The lesson of the table is the same one the [CIA triad](The-CIA-Triad-Confidentiality-Integrity-Availability.md) makes about confidentiality: **encryption protects the content, not the fact that you transmitted.** A radio shouts. Anyone in range can record the shout and, with a direction-finding antenna, point at you (General knowledge).

## Wi-Fi HaLow (IEEE 802.11ah) next to LoRa

The wifi section above compared LoRa with ordinary wifi in a line. There is a third thing between them: **Wi-Fi HaLow**, wifi's own answer to "long range, low power, many devices". Someone who has met LoRa will meet it next, so this section is a comparison and an option, not a how-to. Nothing here transmits and nothing is a setup instruction. Every range and rate figure carries its source and a marker: **vendor figure** (a company or trade group says so), **design goal** (a standard says what it aims for) or **theoretical** (a calculation). All sources were read on 2026-11-01 and are listed in the [claims register](#claims-register).

### What HaLow is, and what it is not

**What it is.** IEEE 802.11ah-2016 is an amendment to the 802.11 wireless LAN standard. IEEE's page for it (read 2026-11-01) says it defines changes to both the physical layer and the medium access control layer "to enable operation of license-exempt IEEE 802.11 wireless networks in frequency bands below 1 GHz, excluding the television (TV) White Space bands, with a transmission range up to 1 km and a minimum data rate of at least 100 Kb/s". Those two numbers are IEEE design goals, not measurements. The page shows it as published 2017-05-05 and marks it "Superseded Standard"; I did not read why, and the amendment's text is behind a subscription, so I did not read it.

The Wi-Fi Alliance, the trade group that certifies wifi products, calls the technology Wi-Fi HaLow (its page, read 2026-11-01; I did not see the phrase "Wi-Fi CERTIFIED HaLow" on it). It says HaLow was introduced in 2017 and "operates in sub-1 GHz spectrum to deliver approximately 1 km range, strong wall penetration, and low-power connectivity for IoT sensors and wearables across industrial, agricultural, smart building, and smart city environments". It lists multi-vendor interoperability, "months-to-years of coin cell battery life" and no proprietary hubs or gateways as benefits, and names narrow band OFDM channels, several power saving modes, native IP support and "latest Wi-Fi security" as the features behind them. These are Alliance claims about the technology, a **vendor figure** and a marketing list, not a test result.

In plain words: it is the same family as the wifi in your laptop, so a HaLow device joins a network, gets an IP address and speaks ordinary internet protocols. What changes is the band. Sub-1-GHz means below 1 GHz, so the signal goes farther and through more, and the channels are narrow, so it carries less. That is the same trade the wifi section above describes, pushed toward range. In the United States, 47 CFR 15.247 covers digitally modulated devices in the 902 to 928 MHz band (see the legal part below), which is the same band Meshtastic's US region uses. That two systems share a band follows from the two sources; how they affect each other in practice I did not measure (**est.**).

**What it is not.**

- **Not LoRa and not LoRaWAN.** It does not use chirp spread spectrum, and a HaLow radio and a LoRa radio cannot talk to each other (General knowledge).
- **Not a message mesh like Meshtastic.** Normal wifi has an access point and stations (General knowledge). Whether a given HaLow product can relay through other stations, I did not read, so I make no claim.
- **Not a promise of 1 km.** The Alliance's figure is a **vendor figure** and IEEE's is a **design goal**. Walls, trees, antennas and neighbors take it apart, as they do a LoRa link budget.
- **Not fast.** Neither page gives a top speed. The IEEE figure is the minimum rate the amendment aims for, not what you will see. I read no throughput figure for any product.
- **Not exempt from rules.** "License-exempt" means no individual license; the device must still meet the regulator's technical rules (legal part below).
- **Not the 6 GHz wifi of Wi-Fi 6E and 7.** Those are different bands and different uses.

### HaLow compared with LoRa and the other radios on this page

Two tables, because eight columns do not fit one. Every cell says where it comes from; "above" means a section of this page. The Meshtastic rate is the published raw rate of the default preset, **not** what a message gets after headers, relaying and sharing.

| Technology | What it is | Range, as the source states it | Throughput | Power | Topology |
|---|---|---|---|---|---|
| Wi-Fi HaLow | IEEE 802.11ah, sub-1-GHz Wi-Fi | About 1 km (Wi-Fi Alliance, **vendor figure**); up to 1 km (IEEE, **design goal**) | At least 100 kb/s as the amendment's minimum (IEEE, **design goal**); top rate not read | Months to years on a coin cell (Wi-Fi Alliance, **vendor figure**) | Access point and stations on an IP network (General knowledge); relay modes not read |
| LoRa (physical layer) | A modulation, not a network | Link budget 153 dB for Long Fast (Meshtastic, published); no range promised | 0.34 to 21.88 kbps across the nine Meshtastic presets (published, raw) | Small batteries or solar (above) | None: other systems sit on it |
| LoRaWAN | LoRa Alliance specification that connects LoRa devices to an IP network | Up to 15 km in rural areas (LoRa Alliance, alliance figure) | Not read | 10 or more years of battery life (LoRa Alliance, alliance figure) | Star of stars: devices, gateways, a network server over IP; a gateway needs an internet backhaul (above and LoRa Alliance) |
| Meshtastic | Open-source LoRa mesh firmware (above) | Kilometers with caveats; none promised (above) | Long Fast 1.07 kbps raw; about 200 bytes a message (above) | Small batteries or solar (above) | Managed-flooding mesh, hop limit 3 by default (above) |
| MeshCore | LoRa routing library and firmware (above) | No figure read | Not read | Solar repeaters are described (meshcore.io, above) | Clients do not repeat; repeaters flood to learn a path, then send directly (above) |
| Wi-Fi at 2.4 and 5 GHz | Ordinary wifi | About one building (above, General knowledge) | The Alliance describes Wi-Fi 5 as multi-gigabit class (**vendor figure**) | Needs mains power at the router (above); the Alliance lists power saving features | Access point and stations |
| Amateur radio | Licensed service (above) | VHF and UHF local; HF regional to worldwide (above) | Not covered in the sections read | Batteries or a generator (above) | Direct, repeaters, or HF skip; no infrastructure needed |
| GMRS and FRS | Short-range voice services (above) | Short; line of sight (above) | Voice; brief data only (above) | Batteries; a GMRS repeater needs power (above) | Direct, plus GMRS repeaters |
| CB | License-free 27 MHz voice (above) | Short; line of sight (above) | Voice | Vehicle or base supply (above) | Direct |

| Technology | Licensing and legal status | Encryption and security model | Typical uses | Equipment cost class (qualitative, no prices) |
|---|---|---|---|---|
| Wi-Fi HaLow | License-exempt by design (IEEE); the United States technical rules are in 47 CFR Part 15 (legal part below); other regions differ | The Alliance says "latest Wi-Fi security"; its security page says WPA3 is mandatory for Wi-Fi CERTIFIED devices; which mode a given HaLow product uses I did not verify. Clients authenticate to an access point | IoT sensors and wearables in industrial, agricultural, smart building and smart city settings (Wi-Fi Alliance); cameras are a common idea but not on the page I read (General knowledge) | Newer and less common than ordinary wifi (**est.**) |
| LoRa (physical layer) | License-exempt in ISM bands, with regional power and duty cycle rules (above) | None: the layer above decides | Whatever the system on top carries | Hobby and industrial parts both exist (**est.**) |
| LoRaWAN | Unlicensed bands (LoRa Alliance) | The Alliance says "end-to-end security" and "robust encryption protocols"; I read no specification | Metering, building and parking sensors (LoRa Alliance) | Gateways and a network server add infrastructure (**est.**) |
| Meshtastic | Region rules apply; amateur regions need a license and forbid encryption (above) | Channel keys, shared by everyone on the channel; header in the clear (above) | Short text messages, positions and telemetry (above) | Hobby class, widely available (**est.**) |
| MeshCore | Region rules apply (above) | Described as end-to-end encrypted; no specification read (above) | Short text, rooms, sensor data (above) | Hobby class (**est.**) |
| Wi-Fi at 2.4 and 5 GHz | License-exempt (47 CFR 15.247 above) | WPA3 is mandatory for Wi-Fi CERTIFIED devices (Wi-Fi Alliance security page) | Everything on a local network | Mass-market (**est.**) |
| Amateur radio | License required; no encryption; no business use (above) | None allowed (above) | Emergency communications, long-distance contact (above) | Wide range of hobby and professional gear (**est.**) |
| GMRS and FRS | GMRS: individual license; FRS: license by rule (above) | No coded messages on GMRS (above) | Short-range voice (above) | Consumer class (**est.**) |
| CB | License by rule (above) | Not covered in the sections read; plain language is the plan | Short-range voice in vehicles (above) | Consumer class (**est.**) |

What the second table says in a sentence: the security models are different in kind. A HaLow network has an access point that decides who may join, as ordinary wifi does; a Meshtastic channel has one key that everyone on it holds, and the licensed voice services allow no encryption at all. Neither is better by itself. The question is who you need to keep out and who you need to reach. The "cost class" column is a qualitative note, labeled **est.** because I read no price or market-share comparison, and the page names no prices on purpose.

### Which to choose for off-grid and continuity use

This table answers which tool fits a job, not which one wins. All of it is a reading of the tables above, so treat it as a place to start a tabletop, not a design.

| Need | Better fit | Why | Caveat |
|---|---|---|---|
| Short text and position messages between people across a town or a trail, on batteries, with no infrastructure | LoRa mesh (Meshtastic or MeshCore) | Built for short messages; no access point; relays | Slow and shared, as the time on air numbers above show |
| An IP application (a sensor feed, a camera, a small web service) across a farm, campus or site that has power | Wi-Fi HaLow, if the hardware and rules fit | Native IP and a normal network model (Wi-Fi Alliance) | The access point needs power; hardware is newer; top speed not read; camera use is General knowledge |
| Low-power sensors that report to the internet | LoRaWAN or HaLow | Both target low-power IoT | LoRaWAN needs a gateway with an internet backhaul; this page does not compare them further |
| Voice or data over regional or worldwide distance, by a licensed person | Amateur HF | Needs no infrastructure | A license, no encryption, no business use |
| Short voice between a few people | GMRS, FRS or CB | Simple; handhelds | Short range; GMRS needs an individual license |
| Devices inside one building with power on | Ordinary 2.4 and 5 GHz wifi | Fast and everywhere | Needs mains power and, for the internet, an uplink |
| Coordination when the internet **and** the mains are gone | LoRa mesh, voice radios, amateur radio | Run from batteries (above) | HaLow on its own is a local-network option: a normal access point needs power, so it helps an outage plan only if that power is planned (**est.**) |

**HaLow hardware is newer and less common.** The Alliance's page quotes ABI Research for 24 million HaLow chipset shipments in 2026, beside 3.8 billion Wi-Fi device shipments in the same year. Those are different units (chips and finished devices), so no precise ratio follows, but the gap is large (**est.**). That is a **vendor figure** from a trade group's page and I did not check it.

**Open-source and vendor support, as read on the day.** One chip vendor publishes a Linux driver for its HaLow parts as an open repository (MorseMicro/morse_driver on GitHub): the API showed a GPL-2.0 license and a last push on 2026-10-24. That shows one vendor ships driver code in the open. It does not show which boards run it, whether Linux itself or OpenWrt support HaLow out of the box (the OpenWrt wiki page I opened had no HaLow content), or what other vendors publish. I did not check whether Meshtastic or MeshCore support HaLow and I make no claim. No vendor is ranked here, and naming one repository as an example is not a recommendation.

### HaLow rules: legal first

This is the United States only, it is education and not legal advice, and the page's existing rule applies: check the current text yourself and keep every live step with a qualified person.

- **The band text I read.** 47 CFR 15.247 (eCFR, current text read 2026-11-01) covers frequency-hopping and digitally modulated devices in 902 to 928 MHz. For digital modulation in that band it says the minimum 6 dB bandwidth must be at least 500 kHz ((a)(2)), the maximum peak conducted output power is 1 watt ((b)(3)), a transmitting antenna with more than 6 dBi of directional gain means the output power must be reduced dB for dB ((b)(4)), and the power spectral density must not exceed 8 dBm in any 3 kHz band ((e)). Its note says these systems share the band on a noninterference basis with Government systems. I quote these only to show that the rules are technical and specific; they are not a statement about any HaLow product.
- **What I could not read.** Which Part 15 provision a given HaLow product is certified under (15.247 or another) I did not read. The product's FCC equipment authorization, its grant, is what says what that unit may do, and I read none. The FCC's own pages I did not read (they refused a plain download on 2026-10-31, see the register).
- **Rules in other regions differ.** Sub-1-GHz license-exempt bands differ from country to country, and so do the power and duty cycle rules. IEEE's abstract says only "below 1 GHz" and I read no regional list. The 10 percent duty cycle quoted above for EU_868 is a rule about LoRa in that region and says nothing about HaLow. Check your own regulator's current text.
- **No steps here.** Nothing on this page tells you how to operate or change a radio. A live test belongs to the person who owns the equipment, after reading the product's documentation and the current rules. Callsigns and grids stay the placeholders N0CALL, N0TST and FN31pr; none is needed here.

## Amateur (ham) radio

The maintainer of this project holds an amateur radio General class license and runs Meshtastic, MeshCore, Reticulum, ham radio and GMRS (his answers, 2026-10-31). That is all this page says about his setup. His callsign and location are not here and never will be.

### License classes in the United States

The Code of Federal Regulations lists the operator classes as Novice, Technician, General, Advanced and Amateur Extra (47 CFR 97.9(a)). **No new Novice or Advanced license is issued** (97.17(a)), so a new operator starts with one of three:

| Class | Exam elements | Read from |
|---|---|---|
| Technician | Element 2 | 47 CFR 97.501(c) |
| General | Elements 2 and 3 | 97.501(b) |
| Amateur Extra | Elements 2, 3 and 4 | 97.501(a) |

Exams are given by volunteer examiners, who hold a General class license or higher (ARRL licensing page, read 2026-10-31). The ARRL page that day also said exams may be taken remotely by video and gave a $35 FCC application fee for new licenses; fees and question pools change, so read the current page. The ARRL page also noted that the Technician question pool was due to be updated in 2026. A station must be under the physical control of a person named on a license grant (97.5(a)), and the licensee designates the control operator (97.103(b)).

### What a General class can do

By the frequency tables in 47 CFR 97.301 a General class control operator may use the VHF and UHF bands that Technicians have, plus a large part of every HF band from 160 meters to 10 meters; some segments of the HF bands are kept for Amateur Extra operators (for example, on 20 meters the General segments are 14.025 to 14.150 MHz and 14.225 to 14.350 MHz). Technician and Novice class operators have limited HF segments on 80, 40, 15 and 10 meters. The most power any station may use is 1.5 kW PEP (97.313(b)), and every station must use the minimum necessary (97.313(a)). HF is the part that matters for continuity: it can reach hundreds or thousands of kilometers with no repeater and no infrastructure, which is why it is the amateur service's long-distance emergency tool (General knowledge for the physics; the bands are Read).

What a license does **not** give you is the right to do anything with the radio. Four rules from the same regulation matter most for a continuity plan:

- **Identify.** Send your call sign at the end of each communication and at least every 10 minutes during one (97.119(a)).
- **No encryption.** "Messages encoded for the purpose of obscuring their meaning" are prohibited (97.113(a)(4)).
- **No business use.** No communications for hire, and none in which the licensee has a pecuniary interest, including on behalf of an employer, except a narrow exception for emergency preparedness or disaster readiness tests and drills, limited to the duration and scope of the drill, and, if not government-sponsored, to one hour a week (with two periods of up to 72 hours a year) (97.113(a)(2) and (3)). Communications that could regularly be furnished through another radio service are also prohibited (97.113(a)(5)).
- **No broadcasting** and no automatic retransmission except through repeaters and the like (97.113(b), (d)).

So a company cannot make amateur radio its own business continuity network. Individuals who volunteer, on their own time, in a served-agency program are a different thing, and the rules for drills are narrow. Ask the regulator or a lawyer before planning anything that mixes the two.

### Emergency communications basics

The regulation states that the amateur service's purpose includes "providing emergency communications" (97.1(a)). Three separate things are easy to mix up:

- **A general rule.** "No provision of these rules prevents the use by an amateur station of any means of radiocommunication at its disposal to provide essential communication needs in connection with the immediate safety of human life and immediate protection of property when normal communication systems are not available" (97.403). It is about a licensed station, and I am not a lawyer; read it in full and do not treat it as permission for anyone to transmit on anything.
- **ARES**, the Amateur Radio Emergency Service. ARRL's page (read 2026-10-31) says it consists of licensed amateurs who have registered their qualifications and equipment with local leadership for public-service communications when a disaster strikes, that only licensed amateurs may join, and that volunteers should be trained, bring a "Go Kit" suited to the job, and may sign a memorandum of understanding with a government or non-government agency.
- **RACES**, the Radio Amateur Civil Emergency Service (97.407). A station can transmit in RACES only if it is registered with a civil defense organization, and the communications must be specifically authorized by that organization. RACES drills are limited to one hour a week unless the state approves longer.

**The practical habits** of emergency communications are the ones a continuity plan already has, with a radio on the end: a trained person, a written net or check-in schedule, short messages in plain language, a log, and a plan for power. ARRL's page puts training first in its list of what a volunteer needs.

### Other countries

Everything above is the United States. Other countries have different classes, bands, power limits, rules on encryption and rules on business use. Meshtastic's own region table lists regional limits that differ from the United States (for example 10 percent duty cycle in EU_868, and amateur regions by ITU region), and says "check your national band plan before transmitting". Check your own regulator, and use the regulator's current published text, not a forum post and not this page.

## GMRS and FRS

Both share the 462 and 467 MHz channels and both are voice-first. The sources are 47 CFR Part 95 from eCFR (2026-10-29 edition, read 2026-10-31).

| Topic | FRS (Family Radio Service) | GMRS (General Mobile Radio Service) |
|---|---|---|
| License | None: the FCC does not require or accept applications for most Personal Radio Services (95.305) | An individual license is required (95.1705); a new one only for an individual at least 18 years old; the license covers the licensee's immediate family (95.1705(c)); normal term ten years; fees apply |
| Exam | None | I found none in the sections I read |
| Channels | 22, all shared with GMRS (95.563) | 30: 8 main 462 MHz, 7 interstitial 462 MHz, 8 main 467 MHz, 7 interstitial 467 MHz (95.1763) |
| Power | ERP 2 W on channels 1 to 7 and 15 to 22; 0.5 W on 8 to 14 (95.567) | 50 W transmitter output for mobile, repeater and base stations on the main channels; 5 W ERP on 462 interstitial; 0.5 W ERP on 467 interstitial (95.1767) |
| Antenna | Non-removable, no more than a half-wave dipole (95.587(b)) | Not limited in the sections I read |
| Repeaters | Not covered by the sections I read | Allowed, with the licensee deciding who may use theirs (95.1705(d)) |
| Data | Brief digital bursts under one second, at most one per 30 seconds, for location or short text; **no store-and-forward packet mode** (95.587(c), (d)) | Handhelds may send location data or a brief text message (95.1731(d)) |
| Identification | None in the sections I read | Call sign at the end of transmissions and every 15 minutes (95.1751) |
| Use | Short-distance voice; one-way only for emergency, traveler assistance, voice pages or brief tests (95.531) | Plain-language voice about personal or business activities, emergency priority on every channel (95.1731) |
| Not allowed | Interference, deception, advertising program material, illegal use (95.333) | Also coded messages, music, advertising, calls to amateur stations except in an emergency, phone connections (95.1733, 95.1749) |

Three consequences for a plan. FRS cannot be made into a digital mesh, because the rules forbid store-and-forward packet operation. A GMRS license belongs to a person, not to a company, so a business that wants a GMRS license for itself needs to read 95.1705 and the grandfathering rule in paragraph (g) carefully. And both services are voice: they carry a person's words a few kilometers, which is exactly what a continuity plan needs from them and nothing more.

## Citizens band (CB)

The rules are in 47 CFR Part 95, in the Citizens Band Radio Service subpart. Its section titles abbreviate that as "CBRS", which is not the Citizens Broadband Radio Service of Part 96. Read 2026-10-31:

- **No license.** Operation is authorized by rule (95.305), and the authority is voided by a violation of the operating rules (95.905).
- **40 channels** from 26.965 MHz to 27.405 MHz (95.963).
- **Power.** 4 W carrier for AM or FM voice and 12 W PEP for single sideband (95.967). No external RF power amplifier, with no exceptions (95.939).
- **Antenna height.** No higher than 18.3 meters (60 feet) above ground, or 6.1 meters (20 feet) above the building or tree it is on, whichever is higher (95.941).
- **Channel 9** may be used only for emergency communications or traveler assistance (95.931(a)(2)). Emergency communications take priority on every channel.
- **Not allowed:** advertising, contact with stations in other countries (with an exception for Canada's General Radio Service), music or sound effects, and the other items in 95.933. Conversations are limited to five minutes, then one minute off the channel, except in an emergency or to assist a traveler (95.957).

For continuity, CB is a cheap, license-free, short-range voice channel that a vehicle can carry. Its reach, quality and who is listening vary by region and are not something I measured.

## Signals intelligence (SIGINT): a careful overview

Radio monitoring is a legitimate hobby, a professional field and, in the hands of states, an intelligence discipline. The legal rules come first because the line between "listening" and "a crime" is drawn by law, not by what the radio can physically do.

### The legal rules first

**This is the United States only, and it is not legal advice.** You must check your own jurisdiction before you listen to anything beyond a broadcast station, and check your state and local laws too; I did not read any. The statute text below was read on 2026-10-31 from Cornell's Legal Information Institute, and I did not read the penalty sections.

1. **The default is "do not intercept".** 18 U.S.C. 2511(1)(a) makes it an offense to intentionally intercept any wire, oral or electronic communication, "except as otherwise specifically provided". "Intercept" means the aural or other acquisition of the contents through a device (18 U.S.C. 2510(4)).
2. **The exceptions that matter to a hobbyist** are in 2511(2)(g). It is not unlawful to intercept an electronic communication on a system "readily accessible to the general public", or a radio communication transmitted by a station for the use of the general public, relating to ships, aircraft, vehicles or persons in distress, by a governmental, law enforcement, civil defense, private land mobile or public safety system that is itself readily accessible to the general public, **by a station operating within the bands allocated to the amateur, citizens band or general mobile radio services**, or by a marine or aeronautical system. In plain words: broadcast stations, ham, CB, GMRS, aircraft and ships are, under the statute's text, ones you may listen to. I did not work out how that wording maps onto FRS.
3. **"Readily accessible to the general public" has a definition** (2510(16)), and a radio communication is **not** readily accessible if it is **scrambled or encrypted**, uses modulation whose parameters were withheld to preserve privacy, is on a subcarrier, or is carried over a common carrier's system (with a tone-only paging exception). Encrypting is therefore a legal line as well as a technical one: an encrypted public-safety channel falls outside the exceptions above.
4. **Hearing is not the same as using or repeating.** 47 U.S.C. 605(a) bars divulging or publishing what you intercepted, or using it for your own benefit or another's, with exceptions for stations used by the general public, distress traffic and **amateur and citizens band** operators. GMRS is not named in that last sentence of 605(a). I do not know how courts apply that, and I do not claim to; if you want to publish what you hear on a channel that is not clearly covered, ask a lawyer.
5. **Transmitting is not monitoring.** Deliberate interference with another station's communications is prohibited for the Personal Radio Services (95.333(d)), a false or deceptive message is prohibited in the amateur service (97.113(a)(4)), and an unlicensed amateur transmission is a license problem before it is anything else. Jamming and spoofing are not "advanced listening".

What the statutes leave open is a good test of whether you should stop and ask: is the traffic on an ISM band with a **published** shared key, such as a default Meshtastic channel, "encrypted"? I found no source that answers it, so the page does not.

### What SIGINT is

The US Intelligence Community's own site (intelligence.gov, "How the IC works", read 2026-10-31) lists SIGINT as one of six kinds of intelligence collection and defines it as "the interception of signals, whether between people, between machines, or a combination of both." The same page says all collection methods "must be lawful" and are subject to oversight. SIGINT is usually split into **communications intelligence** (what people say), **electronic intelligence** (what machines emit) and the **analysis** of who talks to whom, how often and from where, which does not need the content (General knowledge for the split; the NSA's own page refused my download, so it is not cited).

**Receive-only monitoring as a hobby** is the same skills at the smallest scale: a scanner or a software-defined radio, an antenna, a band plan and a notebook. The legal rules above are why listening to the listed services is, by the statute's text, not an interception offense, and why recording and rebroadcasting are a separate question. I did not research whether owning or using a particular scanner or receiver is regulated.

### Why encryption and good practice matter

- **Assume every transmission is recorded.** A receiver is cheap and does not announce itself. Meshtastic's documentation warns that anything sent on a channel can be stored and decrypted later by anyone who gets the key.
- **Content is not the only leak.** The packet header, the node numbers, the timing, the location settings and the fact of a transmission are visible without a key. Meshtastic's header is in the clear on purpose, so nodes can relay what they cannot read.
- **A published key is not a secret.** Do not put anything private on a default channel.
- **Where encryption is forbidden, send nothing you would not say on a loudspeaker.** On the amateur bands, GMRS, and by default CB, the plan is plain language.
- **Check who you are talking to.** An unsigned message's claimed sender can be forged by anyone with the channel key; confirm identity another way (Meshtastic's docs say to confirm a recipient's public key with them by another route).
- **Do not let a continuity radio replace your secrets handling.** Tokens, passwords and backups do not go over a mesh. See [Hashing, encryption and keys](Hashing-Encryption-and-Keys.md) and the cryptography lesson (issue 360).

## Why radio is a common hobby among security people

I have no survey that says how common it is, so this is a list of reasons with the evidence I read, not a statistic.

- **Radio is a layer you were told to ignore.** Most security work starts above the wire. Radio is layer 1 for a large share of the devices around us, and the people who know how it behaves find bugs others do not.
- **The community says so.** DEF CON's Ham Radio Village states its mission: delivering "high-quality and innovative amateur radio related educational content, hands-on experiences, and license testing sessions", and its belief that "the more people know about amateur radio, the more safe, secure, functional, and innovative our wireless products, services, and experiments will be" (hamvillage.org, read 2026-10-31).
- **It is a hands-on way to learn protocols**: antennas, link budgets, interference, packet formats, key management, and what happens when a network is not there.
- **It is a continuity skill.** The same reason this page sits next to the continuity lesson.
- **The maintainer is an example, not a proof.** He holds a General class license and runs Meshtastic, MeshCore, Reticulum, ham radio and GMRS.

## Radio in a continuity plan for this project

This project **has no radio code and no radio hardware.** Nothing in the repository receives or transmits RF. The public edge design does mention Reticulum and a Meshtastic MQTT broker, but it carries them **over the internet** (TCP 4242 and 8883 through a Cloud Firewall), as a design, with the switch off, not approved and not applied. A Reticulum transport node on a droplet is an internet host; it does not make a radio link. If the internet is down, that host is as unreachable as every other.

In the table, a **None** in the file column means I looked and found no document, code or test for a radio path to that piece. Columns follow the question in [Business continuity and disaster recovery](Business-Continuity-and-Disaster-Recovery-BCP-and-DR.md): can I still operate it when the internet or the mains is gone?

| Item | Needs the internet? | Needs power at your site? | Could a radio carry it? | File or procedure | Status |
|---|---|---|---|---|---|
| The repository (code, issues, project board) | Yes, to push, pull requests and issues; a clone works offline (General knowledge) | Your own computer | A one-line "pause" message, not the repository | None. No radio path and no offline copy of the issues | None |
| The secret store (Doppler) | Yes | Your computer | No: secrets must never go over a radio mesh | None | None |
| Spacelift (plans and applies) | Yes | Your computer | No | None | None |
| Twingate (the only way in to the droplets) | Yes | Your computer and the home connector | No. No public SSH and no console password by design | None. The stage 1 guide says the droplet console is not an option: `docs/stages/01-access.md` | None |
| The connectors and other droplets | They run in the cloud; they keep running if the provider is up, and you cannot reach them | None at your site | A status text, not a login | None | None |
| The wiki | To read the published copy | Your computer | No | `scripts/gen-wiki.sh`, `.github/workflows/wiki.yml` | Built; a local clone or a printed copy of the pages you need is a recommendation, not built |
| The home logging server (Wazuh and Grafana) | Yes: the connectors ship to it over Twingate | Yes, at home | No: a continuous log stream does not fit a LoRa link | `docs/stages/02-telemetry.md`, `docs/wiki/Stage-2-Home-Side-Runbook.md` (shipping, not outage behavior) | Outage behavior: None; whether the agent buffers events is not checked |
| The public edge host (design only) | Yes | None at your site | No: it is an internet host | `docs/superpowers/specs/2026-10-19-edge-dmz-design.md`, `stacks/50-edge/main.tf` | Design, built, not applied |
| A radio gateway or any radio hardware | n/a | n/a | n/a | None | None |
| A radio channel in the contact tree | n/a | n/a | n/a | None. The contact tree guidance is in the continuity lesson, with no radio row | None |
| A power plan for the home side (batteries, a generator) | n/a | n/a | n/a | None | None |
| A drill of any radio path | n/a | n/a | n/a | None | None |

**What a radio fallback could carry.** A short human message: "site A is down", "restore started", "call me on the backup phone", "stop, do not apply". The limit is hard numbers. Meshtastic's payload ceiling is 239 bytes and clients keep to about 200; Reticulum is designed for links as slow as 5 bits per second with a 500-byte MTU; Long Fast's raw rate is about 1 kbps. The script shows a 40-byte status text takes under a second on air and a 1 MiB file takes hours of airtime on a shared channel.

**What it could not carry.** Logs. A continuous log stream, backups, restores, SSH or any remote administration, secrets, and the Twingate and Spacelift sessions, which need the internet end to end. A radio is a second path for **people to coordinate**, not for moving data.

**Honest summary.** Today the project's answer to "the internet is down" is that the cloud machines keep running and you cannot reach them. The control plane (Spacelift, Doppler, Twingate and GitHub) needs the internet, the home logging side stops receiving, and no radio path exists, so a three day outage at your site leaves you able to run **nothing** but your local computer. The cheapest fix is on paper: add a no-internet, no-mains row to the contact tree and print the runbooks for the piece you would least afford to lose, as the continuity lesson's exercises ask. A radio for that row is optional, belongs to a person who holds the right license, and would live outside the cost gate, which models cloud bills (I did not find radio hardware in any cost file).

## Free exercises: offline, listen-only and simulation

Every exercise follows four steps: **predict**, **do**, **check**, **undo**. **No exercise transmits.** The words *offline*, *listen-only* and *paper* tell you which kind each one is. Nothing here asks you to configure a radio, flash firmware or open a port.

### Exercise 1: read a config and predict (paper)

**Predict.** Here are two settings blocks from the sources, shown as data. Do not enter them into any device. First the Meshtastic setting names and defaults (LoRa configuration page); second an RNode interface from the Reticulum manual, which uses a frequency in a European-style band that is not the United States 902 to 928 MHz range.

```text
lora.region          US
lora.modem_preset    LONG_FAST
lora.hop_limit       3
lora.tx_power        0
```

```text
type = RNodeInterface
frequency = 867200000
bandwidth = 125000
txpower = 7
spreadingfactor = 8
codingrate = 5
```

Answer on paper before you run anything. For the first block: which SF, BW and CR does Long Fast use (the Meshtastic section above gives them)? Is it a longer or shorter range preset than Medium Fast, and what does it cost in speed? For the second: is it faster or slower than Long Fast, by roughly how much? Which of the two would you expect to send a 100-byte packet quicker?

**Do.** Move on to Exercise 2 and compare.

**Check.** The Reticulum block has a `txpower` of 7 dBm. The manual's own comment says that is 5 mW. Does a lower transmit power change airtime, or range, or both?

**Undo.** Nothing was changed.

### Exercise 2: run the script and compare it with your prediction

**Do.** Save this as `lora_budget.py` and run `python3 -I lora_budget.py`. It does arithmetic only: no radio, no network, no files.

```python
#!/usr/bin/env python3
# lora_budget.py - LoRa bit rate, time on air, link budget and capacity. Pure arithmetic: no radio, no network, no files.
# Usage: python3 -I lora_budget.py            (the full report)
#        python3 -I lora_budget.py --sf 8 --bw 125 --cr 5 --payload 100   (one packet, your own numbers)
import argparse
import math

HEADER = 16  # Meshtastic's over-the-air header, in bytes (Mesh Broadcast Algorithm page)
PREAMBLE = 16  # symbols; Meshtastic sub-GHz (Mesh Broadcast Algorithm page)
FREQ_MHZ = 906.875  # Meshtastic's US default LongFast slot center (Radio Settings page)

# name: (spreading factor, bandwidth kHz, coding rate denominator, published kbps, published link budget dB)
PRESETS = {
    "Short Turbo": (7, 500, 5, 21.88, 140),
    "Short Fast": (7, 250, 5, 10.94, 143),
    "Short Slow": (8, 250, 5, 6.25, 145.5),
    "Medium Turbo": (9, 500, 5, 7.03, 145),
    "Medium Fast": (9, 250, 5, 3.52, 148),
    "Medium Slow": (10, 250, 5, 1.95, 150.5),
    "Long Turbo": (11, 500, 8, 1.34, 150),
    "Long Fast": (11, 250, 5, 1.07, 153),
    "Long Moderate": (11, 125, 8, 0.34, 156),
}


def bit_rate(sf, bw_khz, cr):
    return sf * (bw_khz * 1000 / 2**sf) * (4 / cr)


def airtime_ms(sf, bw_khz, cr, total_bytes, preamble=PREAMBLE):
    """Time on air for a LoRa packet with an explicit header and a payload CRC (port of RadioLib's getNumSymbols)."""
    t_sym = 2**sf / (bw_khz * 1000)
    ldro = t_sym > 0.016
    divisor = 4 * (sf - 2) if ldro else 4 * sf
    bits = max(8 * total_bytes + 16 - 4 * sf + 8 + 20, 0)
    coded = -(-bits // divisor)
    symbols = preamble + 8 + 4.25 + coded * cr
    return symbols * t_sym * 1000


def fspl_km(budget_db, margin_db, mhz):
    return 10 ** ((budget_db - margin_db - 32.44 - 20 * math.log10(mhz)) / 20)


def horizon_km(h1_m, h2_m):
    return 4.12 * (math.sqrt(h1_m) + math.sqrt(h2_m))


def report():
    print("== 1. Bit rate from SF, BW and CR against the published table ==")
    print("preset         SF  BW kHz  CR   computed kbps  published kbps  match")
    for name, (sf, bw, cr, pub, _) in PRESETS.items():
        got = bit_rate(sf, bw, cr) / 1000
        print(f"{name:<14} {sf:>2}  {bw:>6}  4/{cr}  {got:>13.2f}  {pub:>14.2f}  {'yes' if abs(got - pub) < 0.01 else 'NO'}")
    print()
    print(f"== 2. Time on air in ms, {HEADER}-byte header + payload, preamble {PREAMBLE}, CRC on ==")
    sizes = (20, 100, 239)
    print("preset          " + "".join(f"{s:>4} B payload  " for s in sizes))
    for name in ("Short Fast", "Medium Fast", "Long Fast", "Long Moderate"):
        sf, bw, cr, _, _ = PRESETS[name]
        print(f"{name:<14}  " + "".join(f"{airtime_ms(sf, bw, cr, HEADER + s):>12.0f}   " for s in sizes))
    print()
    sf, bw, cr, _, budget = PRESETS["Long Fast"]
    print(f"== 3. Long Fast link budget {budget} dB at {FREQ_MHZ} MHz: free-space range as the allowance for real life grows ==")
    print("allowance dB   free-space range km")
    for margin in (0, 20, 40, 60, 80):
        print(f"{margin:>12}   {fspl_km(budget, margin, FREQ_MHZ):>19.2f}")
    print("line-of-sight limit, antenna heights in meters (4.12 * (sqrt(h1) + sqrt(h2))):")
    for h1, h2 in ((2, 2), (2, 30), (10, 100)):
        print(f"  {h1:>3} m and {h2:>3} m: {horizon_km(h1, h2):>5.1f} km")
    print()
    print("== 4. Capacity on Long Fast ==")
    a100 = airtime_ms(sf, bw, cr, HEADER + 100) / 1000
    print(f"one 100-byte message: {a100:.2f} s on air")
    print(f"upper bound for the whole channel at 100% use, one hop: {3600 / a100:.0f} messages an hour")
    print(f"one node held to a 10% duty cycle (the EU_868 rule): {360 / a100:.0f} messages an hour")
    scaled = 60 * (1.0 + (62 - 40) * 2**sf / (bw * 100))
    print(f"Meshtastic stretches a 60 minute interval to {scaled:.0f} minutes with 62 nodes online (their page says about 168)")
    print()
    print("== 5. What this project would ask of a Long Fast link ==")
    alert = airtime_ms(sf, bw, cr, HEADER + 40) / 1000
    print(f"one 40-byte status text: {alert:.2f} s on air")
    chunk = 239
    size = 1024 * 1024
    packets = -(-size // chunk)
    each = airtime_ms(sf, bw, cr, HEADER + chunk) / 1000
    print(f"one 1 MiB file in {chunk}-byte packets: {packets} packets, {packets * each / 3600:.1f} hours of airtime, one hop, no retries")
    stream = 4 * 1024 * 8 / 60
    print(f"a 4 KiB a minute log stream is {stream:.0f} bits per second; the link's raw rate is {bit_rate(sf, bw, cr):.0f}")
    per_min = 4096 / chunk
    print(f"as packets that is {per_min * each:.1f} s of airtime per minute, {per_min * each / 60 * 100:.0f}% of the channel before any other user")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sf", type=int)
    ap.add_argument("--bw", type=int, help="bandwidth in kHz")
    ap.add_argument("--cr", type=int, help="coding rate denominator, 5 to 8")
    ap.add_argument("--payload", type=int, help="total bytes on air, header included")
    a = ap.parse_args()
    if a.sf is None:
        report()
        return
    if not (a.bw and a.cr and a.payload):
        ap.error("--sf needs --bw, --cr and --payload")
    print(f"SF{a.sf} BW{a.bw} CR4/{a.cr}, {a.payload} bytes: {airtime_ms(a.sf, a.bw, a.cr, a.payload):.0f} ms on air, raw rate {bit_rate(a.sf, a.bw, a.cr):.0f} bps")


main()
```

On 2026-10-31, with Python 3.13.5 on Linux, as an ordinary user, the full report printed this (the lesson's test runs the script and compares it with this block):

```text
== 1. Bit rate from SF, BW and CR against the published table ==
preset         SF  BW kHz  CR   computed kbps  published kbps  match
Short Turbo     7     500  4/5          21.88           21.88  yes
Short Fast      7     250  4/5          10.94           10.94  yes
Short Slow      8     250  4/5           6.25            6.25  yes
Medium Turbo    9     500  4/5           7.03            7.03  yes
Medium Fast     9     250  4/5           3.52            3.52  yes
Medium Slow    10     250  4/5           1.95            1.95  yes
Long Turbo     11     500  4/8           1.34            1.34  yes
Long Fast      11     250  4/5           1.07            1.07  yes
Long Moderate  11     125  4/8           0.34            0.34  yes

== 2. Time on air in ms, 16-byte header + payload, preamble 16, CRC on ==
preset            20 B payload   100 B payload   239 B payload  
Short Fast                43            102            204   
Medium Fast              150            324            642   
Long Fast                518           1133           2157   
Long Moderate           1511           3871           7934   

== 3. Long Fast link budget 153 dB at 906.875 MHz: free-space range as the allowance for real life grows ==
allowance dB   free-space range km
           0               1176.12
          20                117.61
          40                 11.76
          60                  1.18
          80                  0.12
line-of-sight limit, antenna heights in meters (4.12 * (sqrt(h1) + sqrt(h2))):
    2 m and   2 m:  11.7 km
    2 m and  30 m:  28.4 km
   10 m and 100 m:  54.2 km

== 4. Capacity on Long Fast ==
one 100-byte message: 1.13 s on air
upper bound for the whole channel at 100% use, one hop: 3179 messages an hour
one node held to a 10% duty cycle (the EU_868 rule): 318 messages an hour
Meshtastic stretches a 60 minute interval to 168 minutes with 62 nodes online (their page says about 168)

== 5. What this project would ask of a Long Fast link ==
one 40-byte status text: 0.68 s on air
one 1 MiB file in 239-byte packets: 4388 packets, 2.6 hours of airtime, one hop, no retries
a 4 KiB a minute log stream is 546 bits per second; the link's raw rate is 1074
as packets that is 37.0 s of airtime per minute, 62% of the channel before any other user
```

The Reticulum example from Exercise 1, run as `python3 -I lora_budget.py --sf 8 --bw 125 --cr 5 --payload 100`, printed:

```text
SF8 BW125 CR4/5, 100 bytes: 324 ms on air, raw rate 3125 bps
```

The same 100 bytes on Long Fast, run as `python3 -I lora_budget.py --sf 11 --bw 250 --cr 5 --payload 100`, printed:

```text
SF11 BW250 CR4/5, 100 bytes: 1010 ms on air, raw rate 1074 bps
```

**Check.** Section 1 must say `yes` on every row: that is the bit-rate formula agreeing with Meshtastic's published table. Compare the two one-packet lines: Long Fast needs about three times the air time of the Reticulum example for the same bytes, which is the price of its range. Then read what each section says about this project: a status text is under a second, a 1 MiB file is hours, and a modest log stream is most of the channel.

**Undo.** Nothing to undo. The script writes nothing, and the test checks that.

**What the script does not know.** It does not know the exact size of a Meshtastic protocol-buffer wrapper, so it takes the on-air payload as an input; it ignores retries, relaying, collisions and the random back-off before a transmit; it assumes the preamble and coding rate shown; and it assumes the low data rate optimization turns on when a symbol lasts more than 16 ms, which is the usual Semtech guidance (General knowledge, not checked in this session). Every row is a floor on the time, not a forecast.

### Exercise 3: a communications tree for a three day outage (paper)

**Predict.** A three person team in two towns (call them A and B) loses the internet and the mains at the same moment for three days. Before you fill anything in, guess how many of the six links between the three people still work.

**Do.** Copy this table and fill it in for a team you know. Use invented names and placeholders only. A **second** channel must need neither the internet nor mains power.

| Who | Job | First channel (needs the internet) | Second channel (needs neither) | Needs a license? | Check-in times |
|---|---|---|---|---|---|
| Person 1 (town A) | Incident lead | Chat app | Landline with a battery backup, or a GMRS handheld | GMRS: an individual license | Top of every 4th hour |
| Person 2 (town A) | Technical lead | Chat app | Same GMRS channel as Person 1 | GMRS: an individual license | Top of every 4th hour |
| Person 3 (town B) | Communications lead | Chat app | A licensed amateur with the placeholder call sign N0CALL, on a pre-agreed schedule | Amateur: a General or Technician license for the band | Twice a day at agreed times |

Then check the tree against four questions: Can the lead reach each person with the internet **and** the mains both gone? Is there a second route between A and B, and what carries it? Who holds the printed copy of the runbooks, and where is it? What is the battery plan for each radio and for the phone chargers (Ready.gov says to plan batteries and alternative power)?

**Check.** Write down at most three findings, each with an owner and a date, as the continuity lesson's tabletop does. The example table above has a built-in finding: Person 3's channel depends on one amateur, who is a single point of failure.

**Undo.** Nothing to undo. Keep the findings.

### Exercise 4: legal line drawing (paper, United States, from the statute text)

**Predict.** For each case write "allowed", "not allowed" or "ask a lawyer", then check the section in the legal rules above.

1. You listen to a local amateur radio repeater with a scanner. (Under 18 U.S.C. 2511(2)(g)(ii)(III), a station on an authorized frequency in the amateur, CB or GMRS bands is on the list. Local and state rules were not checked.)
2. You try to record an encrypted public-safety channel. (Encrypted communications are not "readily accessible to the general public", so the exceptions do not cover them. Do not.)
3. You post a recording of two people on a GMRS channel online. (Listening is covered; publishing is the 47 U.S.C. 605(a) question, and the sentence listing exceptions names amateur and CB but not GMRS. Ask a lawyer.)
4. You read the default Meshtastic channel with a node you own. (The text I read does not answer it. Ask.)
5. You turn on a transmitter to drown out a neighbor's FRS radios. (Not allowed: 47 CFR 95.333(d), and it is the opposite of monitoring.)
6. You send encrypted messages on an amateur band. (Not allowed: 47 CFR 97.113(a)(4); Meshtastic's own docs say encryption is not permitted in its amateur regions.)

**Check.** Write the section number beside each answer. If the text does not answer a case, "I do not know" is a correct answer.

**Undo.** Nothing to undo.

### Exercise 5 (optional): listen-only, no radio needed

**Do.** With a battery-powered AM or FM broadcast receiver, listen for ten minutes with the power to your computer off. Write down every piece of information you would need to run a response (what is happening, where, what to do) and who said it. This is the one-way channel in the table at the top: a broadcast station is a "station for the use of the general public", which the statute above treats as lawful to receive. I did not run this exercise.

**Check.** What did you miss because you could not answer back? That gap is what the two-way rows of the tree are for.

**Undo.** Nothing to undo.

### For a licensed operator: what going live would take (not part of any exercise)

Nothing below is something this page, or a script on it, will do. It is a checklist for a **qualified, licensed operator** who has decided, with the current rules in hand, to run a live test. Each step is marked **LIVE** and belongs to the operator.

- **LIVE, operator only:** confirm your jurisdiction, your license class and its privileges for the band, and your equipment's certification. Read the current regulator text for each, not this page.
- **LIVE, operator only:** set the device's region and power for your location; a Meshtastic node with no region set does not transmit. Use the least power that does the job (97.313(a)).
- **LIVE, operator only:** on an amateur band, identify by call sign and send no encrypted traffic. On GMRS, identify every 15 minutes. On every service, keep test transmissions brief and off channels reserved for emergencies.
- **LIVE, operator only:** keep a written log, tell any served agency or net control what you are doing, and stop at the first sign of interference.
- **LIVE, operator only:** a drill is not an emergency. Do not announce an emergency, and do not test on channels people rely on for help.
- **Fail-safe checks to ask the operator about (from the engineering side):** what the device does on a crash, a stuck transmit key, a lost GPS fix, a full buffer or a repeated message; whether duty cycle or an airtime limit applies; and what the emergency procedure is. I checked none of these on real equipment.

## Checkpoint

You are done when you can answer these without looking:

1. Name two things in the continuity lesson's contact tree that a no-internet, no-mains outage removes.
2. What three LoRa settings must match for two radios to hear each other?
3. How does MeshCore's routing differ from Meshtastic's flooding, and how does Reticulum's differ from both?
4. Why can a 1 MiB file not sensibly go over a 1 kbps shared link?
5. What does a General class license add over Technician on HF, and what is the most power any amateur station may use?
6. Why can a business not use amateur radio as its own continuity network?
7. Which of GMRS, FRS and CB needs an individual license, and which forbids store-and-forward packet operation?
8. Under the statutes you read, name two kinds of radio traffic a hobbyist may receive and one that the exceptions do not cover.
9. Why is an encrypted mesh message still leaking information, and what does the Meshtastic documentation call recording it now to read it later?
10. What does this project have for a radio fallback today?
11. Name two ways Wi-Fi HaLow differs from LoRa, and say why a HaLow access point makes it a poor outage plan on its own.

## Common mistakes

- **Treating a radio as a replacement for the internet.** It is a second path for people to coordinate.
- **Believing a published range.** Every range figure comes with conditions; the numbers on this page are floors and illustrations. The 1 km for Wi-Fi HaLow is a vendor figure and an IEEE design goal.
- **Sending secrets over a mesh** because it is "encrypted". Keys leak, headers do not hide, and the default key is public.
- **Encrypting on a service that forbids it**, or broadcasting from a service that is not a broadcaster.
- **Assuming "listening" and "using what I heard" have the same rules.**
- **Using a business license-free channel as a plan**, instead of writing down who may transmit and under which license.
- **Testing live as if it were a simulation.** A drill that transmits is a live action and needs the operator.
- **Forgetting the batteries.** Radios fail on power first.

## Where to next

- [Business continuity and disaster recovery](Business-Continuity-and-Disaster-Recovery-BCP-and-DR.md): put a no-internet row in your own contact tree.
- [Backups, recovery and patching](Backups-Recovery-and-Patching.md) and the [backups deep dive](Backups-Deep-Dive-3-2-1-1-0-Immutability-and-Restore-Testing.md): what you will be restoring when the internet comes back.
- [The DMZ and hardening a host that faces the internet](The-DMZ-and-Hardening-a-Host-That-Faces-the-Internet.md): this project's internet-side Reticulum and MQTT design.
- [Careers, roles and what to learn next](Careers-Roles-and-What-to-Learn-Next.md).

## Claims register

Every source claim on this page, with where it was read. Statuses: **Read** means I read the passage on 2026-10-31, **Observed** means I ran it, **Not read** means the page refused or I did not open it, **Not run** and **est.** mean neither, and **General knowledge** means I did not look it up for this page. The United States rules are the eCFR edition dated 2026-10-29.

| Claim | Source | Status |
|---|---|---|
| Meshtastic overview: mesh, channels (up to eight), default channel key `AQ==`, rebroadcast delay weighted by SNR, hop limit, 16-byte header, payload at most 239 bytes, direct messages and retransmits | [Meshtastic, Overview](https://meshtastic.org/docs/overview/) (version 2.8; no page date) | Read 2026-10-31 |
| Managed flooding, next-hop since 2.6, preamble 16, header layout and flags, default NodeInfo every 3 hours, interval scaling above 40 nodes with the 62-node example | [Meshtastic, Mesh Broadcast Algorithm](https://meshtastic.org/docs/overview/mesh-algo/) (no page date) | Read 2026-10-31 |
| Encryption: AES-CTR channel keys, AEAD from 2.8.1, X25519 and AES-256-CCM direct messages, signed broadcasts, no forward secrecy, harvest now decrypt later, unattended nodes, unsigned sender is a claim | [Meshtastic, Encryption](https://meshtastic.org/docs/overview/encryption/) (no page date) | Read 2026-10-31 |
| Regions and power, EU duty cycles, hop limit default 3 and maximum 7, ham regions need licensed mode, no encryption, call sign required, presets and Long Fast default, node does not transmit until region is set | [Meshtastic, LoRa Configuration](https://meshtastic.org/docs/configuration/radio/lora/) (no page date) | Read 2026-10-31 |
| Nine presets: data rates, SF, BW, CR and link budgets; 22 dBm and 0 dB antenna assumption; each SF step doubles airtime; US LongFast slot 906.875 MHz; not LoRaWAN | [Meshtastic, Radio Settings](https://meshtastic.org/docs/overview/radio-settings/) (no page date) | Read 2026-10-31 |
| Project status, experimental devices, not tested by regulators | [Meshtastic, Legal](https://meshtastic.org/docs/legal/) | Read 2026-10-31 |
| MeshCore: what it is, clients do not repeat, path learning, group channels flood, hop limit 64, frequencies, October 2025 narrow presets, open-source status, public channel key is published | [MeshCore README](https://github.com/meshcore-dev/MeshCore) and [FAQ](https://github.com/meshcore-dev/MeshCore/blob/main/docs/faq.md) (raw files; no page date) | Read 2026-10-31 |
| MeshCore: end-to-end encrypted messages, public and private channels, solar repeaters | [meshcore.io](https://meshcore.io/) | Read 2026-10-31 |
| MeshCore packet format: header, route types, payload types, v1 uses 1-byte hashes and a 2-byte MAC, group text "unverified" | [MeshCore, Packet Format](https://github.com/meshcore-dev/MeshCore/blob/main/docs/packet_format.md) (firmware v1.12.0 described) | Read 2026-10-31; no cryptographic specification read |
| Reticulum: what it is, 5 bps and 500-byte MTU, RNode, X25519, Ed25519, AES-256-CBC, HMAC-SHA256, forward secrecy, no source addresses, license wording, public-domain dedication in 2016 | [Reticulum manual 1.5.5, What is Reticulum?](https://reticulum.network/manual/whatis.html) (copyright 2025) | Read 2026-10-31 |
| Reticulum: transport nodes, announces limited to 2 percent of bandwidth by default, link setup 3 packets and 297 bytes, keep-alive about 0.45 bits per second, no packet priority | [Reticulum manual, Understanding Reticulum](https://reticulum.network/manual/understanding.html) | Read 2026-10-31; the What is page says 0.44 bits per second, so the figure is approximate |
| RNode LoRa interface example, spectrum is legally controlled, AX.25 KISS identifies with a call sign, airtime limits | [Reticulum manual, Supported Interfaces](https://reticulum.network/manual/interfaces.html) | Read 2026-10-31 |
| LoRa time on air: the symbol-count formula implemented in RadioLib | [RadioLib, `PhysicalLayer.cpp`](https://github.com/jgromes/RadioLib/blob/master/src/protocols/PhysicalLayer/PhysicalLayer.cpp) (`getNumSymbols`, `calculateTimeOnAir`) | Read 2026-10-31; the Semtech datasheet page it cites could not be downloaded (the address returned a "Document Has Moved" page) |
| Free-space path loss, line-of-sight limit, symbol-time rule for low data rate optimization | None | General knowledge; **est.** |
| Operator classes, Novice and Advanced no longer issued, exam elements, frequency tables, power limit, prohibited transmissions, call sign timing, safety of life, RACES, station license | [47 CFR Part 97 (eCFR)](https://www.ecfr.gov/current/title-47/part-97): sections 97.1, 97.5, 97.9, 97.17, 97.103, 97.113, 97.119, 97.301, 97.313, 97.403, 97.407, 97.501 | Read 2026-10-31, edition 2026-10-29 |
| GMRS, FRS and CB: license by rule, individual GMRS license, channels, power, antenna, data, identification, prohibited uses, CB channel 9, height, amplifiers, conversation limits | [47 CFR Part 95 (eCFR)](https://www.ecfr.gov/current/title-47/part-95): sections 95.305, 95.333, 95.381, 95.531, 95.563, 95.567, 95.587, 95.905, 95.931, 95.933, 95.939, 95.941, 95.957, 95.963, 95.967, 95.1705, 95.1731, 95.1733, 95.1749, 95.1751, 95.1763, 95.1767 | Read 2026-10-31, edition 2026-10-29 |
| Unlicensed bands named for digital devices | [47 CFR 15.247 (eCFR)](https://www.ecfr.gov/current/title-47/section-15.247) | Read 2026-10-31, edition 2026-10-29 |
| HaLow: what 802.11ah defines (sub-1-GHz license-exempt operation, up to 1 km and at least 100 kb/s as design goals), published 2017-05-05, marked superseded | [IEEE SA, IEEE 802.11ah-2016](https://standards.ieee.org/ieee/802.11ah/4960/) (abstract page only; the first address I tried returned a "removed or temporarily unavailable" page) | Read 2026-11-01; the amendment text is behind a subscription and was not read |
| HaLow: introduced 2017, sub-1-GHz, about 1 km, wall penetration, coin cell battery life, features, 24 million HaLow chipsets shipped in 2026 against 3.8 billion Wi-Fi devices (ABI Research, quoted by the Alliance) | [Wi-Fi Alliance, Wi-Fi (MAC/PHY)](https://www.wi-fi.org/wi-fi-macphy) (HaLow section; the address `discover-wi-fi/wi-fi-halow` redirects there; page copyright 2026) | Read 2026-11-01; vendor figures, not checked |
| WPA3 is mandatory for Wi-Fi CERTIFIED devices | [Wi-Fi Alliance, Security](https://www.wi-fi.org/security) | Read 2026-11-01; whether a given HaLow product uses WPA3 not verified |
| LoRaWAN: unlicensed bands, up to 15 km in rural areas, 10 or more years of battery life, star-of-stars architecture, gateways over IP, security wording | [LoRa Alliance, About LoRaWAN](https://lora-alliance.org/about-lorawan/) (no page date) | Read 2026-11-01; alliance figures; no specification read |
| HaLow: 47 CFR 15.247 for digital modulation in 902 to 928 MHz: (a)(2), (b)(3), (b)(4), (e), the noninterference note | [47 CFR 15.247 (eCFR)](https://www.ecfr.gov/current/title-47/section-15.247) | Read 2026-11-01, current text; I did not re-check the edition date |
| HaLow: one vendor's open Linux driver repository, GPL-2.0, last push 2026-10-24 | GitHub API for MorseMicro/morse_driver | Read 2026-11-01; no vendor ranked; mainline Linux and OpenWrt support not shown |
| HaLow: access point and station topology, cameras as a use, WPA3 session keys, cost class, band sharing with LoRa, no LoRa interoperability | None | General knowledge; **est.** |
| HaLow: the amendment text, throughput figures, relay or mesh modes, regional band lists, any product's FCC grant, FCC web pages, Meshtastic or MeshCore support for HaLow | None | Not read |
| Volunteer examiners, remote exams, $35 application fee, Technician pool update in 2026 | [ARRL, Licensing, Education and Training](https://www.arrl.org/licensing-education-training) (copyright 2026; no page date) | Read 2026-10-31 |
| ARES, training and go kits, RACES, memoranda of understanding, independence from the internet and phone systems | [ARRL, ARES](https://www.arrl.org/ares) (copyright 2026; no page date) | Read 2026-10-31 |
| Interception offense, definitions, "readily accessible to the general public" | [18 U.S.C. 2511](https://www.law.cornell.edu/uscode/text/18/2511) and [2510](https://www.law.cornell.edu/uscode/text/18/2510) | Read 2026-10-31; penalty sections not read |
| Divulging and use of intercepted radio communications, and the exceptions | [47 U.S.C. 605](https://www.law.cornell.edu/uscode/text/47/605) | Read 2026-10-31; how courts apply the GMRS gap not researched |
| Power outages may disrupt communications; check the home phone and its backup; plan batteries | [Ready.gov, Power Outages](https://www.ready.gov/power-outages) | Read 2026-10-31; page showed "Last Updated: 06/04/2026" |
| Family communication plan questions | [Ready.gov, Make a Plan](https://www.ready.gov/make-a-plan) | Read 2026-10-31; page showed "Last Updated: 09/01/2026" |
| SIGINT definition and lawful, overseen collection | [intelligence.gov, How the IC works](https://www.intelligence.gov/how-the-ic-works) | Read 2026-10-31 (no page date) |
| Ham Radio Village mission | [hamvillage.org](https://hamvillage.org/) | Read 2026-10-31 |
| FCC amateur, GMRS, FRS and CB web pages | fcc.gov (the four pages for each service) | Not read: each returned "Access Denied" (HTTP 403) to a plain download on 2026-10-31, and I did not try to get around it; the rules are from eCFR instead |
| NSA SIGINT page | nsa.gov | Not read: "Access Denied" (HTTP 403) to a plain download on 2026-10-31; intelligence.gov used instead |
| Cell tower backup power, wifi on 6 GHz, direction finding of transmitters, satellite messengers | None | General knowledge or **not covered**; no source read |
| State and local law on scanners and radio monitoring, and the rules of any country other than the United States | None | Not read |
| This project has no radio code or hardware; the edge design carries Reticulum and MQTT over TCP | [`docs/superpowers/specs/2026-10-19-edge-dmz-design.md`](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/superpowers/specs/2026-10-19-edge-dmz-design.md), `stacks/50-edge/main.tf`, `docs/stages/05-edge.md` | Read 2026-10-31 in this repository; a search of the wiki and docs for radio terms found only these designs |
| No console password and no break-glass; connectors stateless | `docs/stages/01-access.md` | Read 2026-10-31 in this repository (also read for the continuity lesson) |
| Log shipping uses Twingate to a home manager; agent buffering not checked | `docs/stages/02-telemetry.md`, `docs/wiki/Stage-2-Home-Side-Runbook.md` | Read 2026-10-31 in this repository |
| The script and its two outputs | This page, Exercise 2 | Observed 2026-10-31, Python 3.13.5 |
| Maintainer facts: General class license; runs Meshtastic, MeshCore, Reticulum, ham radio and GMRS | The maintainer's own answers, 2026-10-31 | Stated by the maintainer; nothing else about his gear or experience is claimed |

<!-- BEGIN GENERATED PAGE NAV bottom: rewritten from docs/wiki/_nav.yaml by scripts/gen_wiki_nav.py; edit the manifest, not this block -->
Where you are: [Home](Home.md) > [Track 3: Privacy, anonymity and cryptocurrency](Contents.md#track-3-privacy-anonymity-and-cryptocurrency) > Radio and off-grid communication

Previous: [Running Monero properly](Running-Monero-Properly-Hardware-Wallet-Qubes-and-Whonix-Offline-Wallet-and-PiNodeXMR.md)

In this track: [Track 3: Privacy, anonymity and cryptocurrency](Contents.md#track-3-privacy-anonymity-and-cryptocurrency), 18 pages

- Cryptography and privacy: [Cryptography fundamentals](Cryptography-Fundamentals-Symmetric-Asymmetric-Hashing-Certificates-and-Keys.md) / [Privacy, security and anonymity](Privacy-Security-and-Anonymity-Three-Different-Things-and-Why-There-Is-No-Silver-Bullet.md) / [Privacy versus security](Privacy-vs-Security-Blinds-and-Locks-Physical-Security-and-Monero.md)
- Tor, I2P, VPN and browsing: [Tor, I2P and the darknet without the myths](Tor-I2P-and-the-Darknet-Without-the-Myths.md) / [How a VPN works](How-a-VPN-Works-Tunnels-What-It-Hides-What-It-Does-Not-and-What-an-Audit-Proves.md) / [How Tor works in depth](How-Tor-Works-in-Depth-Circuits-Relays-Directory-Authorities-and-Onion-Services.md) / [How I2P works](How-I2P-Works-Tunnels-Garlic-Routing-and-the-Network-Database.md) / [The browsing setups compared](The-Browsing-Setups-Compared-Tor-Browser-Brave-Whonix-Tails-and-Qubes-with-Whonix.md) / [OPSEC for Tor and I2P](OPSEC-for-Tor-and-I2P-That-Holds-Up-Identities-Layers-Metadata-and-Habits.md) / [The darknet landscape: markets, OPSEC and layering](The-Darknet-Landscape-Markets-OPSEC-Clearnet-and-Layering-Tor-I2P-and-VPN.md) / [Lab: publish a web server as an onion service and an I2P site](Lab-Publish-a-Web-Server-as-a-Tor-Onion-Service-and-an-I2P-Site-Time-Boxed-and-Defensive.md)
- Cryptocurrency: [Blockchain fundamentals](Blockchain-Fundamentals-Hashes-Blocks-Nodes-Consensus-and-Forks.md) / [How Bitcoin works](How-Bitcoin-Works-Keys-UTXOs-Mining-and-Why-It-Is-Pseudonymous-and-Traceable.md) / [How Monero works](How-Monero-Works-Compared-with-Bitcoin-and-Ethereum-DeFi-Mixers-Swaps-and-Ransomware.md) / [Wallets and key custody](Wallets-and-Key-Custody-Hot-and-Cold-Hardware-Wallets-Recovery-Shamir-and-Multisig.md) / [Paper wallets and offline key generation](Paper-Wallets-Generators-and-Offline-Key-Generation-Tails-Electrum-and-Monero.md) / [Running Monero properly](Running-Monero-Properly-Hardware-Wallet-Qubes-and-Whonix-Offline-Wallet-and-PiNodeXMR.md)
- Radio and off-grid: **Radio and off-grid communication**

Related pages:

- [Business continuity and disaster recovery](Business-Continuity-and-Disaster-Recovery-BCP-and-DR.md)
- [The CIA triad](The-CIA-Triad-Confidentiality-Integrity-Availability.md)
- [Backups, recovery and patching](Backups-Recovery-and-Patching.md)
- [Backups deep dive](Backups-Deep-Dive-3-2-1-1-0-Immutability-and-Restore-Testing.md)
- [The DMZ and hardening an internet-facing host](The-DMZ-and-Hardening-a-Host-That-Faces-the-Internet.md)
- [Zero trust at home: two connectors and failover](Zero-Trust-at-Home-Two-Connectors-and-Failover.md)
<!-- END GENERATED PAGE NAV bottom -->
