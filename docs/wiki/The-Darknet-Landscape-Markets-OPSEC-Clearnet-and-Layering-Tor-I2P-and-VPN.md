# The darknet landscape: markets as an OPSEC case study, clearnet versus darknet, and layering Tor, I2P and a VPN

<!-- BEGIN GENERATED PAGE CONTENTS: rewritten from the page's own headings by scripts/gen_wiki_nav.py; edit the headings, not this block -->
**On this page:**

- [What you will be able to do](#what-you-will-be-able-to-do)
- [What the wiki already says (and the gap)](#what-the-wiki-already-says-and-the-gap)
- [What a darknet market is](#what-a-darknet-market-is)
- [The documented history, in dates](#the-documented-history-in-dates)
- [Why most of them fail](#why-most-of-them-fail)
- [The Darknet Market Bible and what kind of document it is](#the-darknet-market-bible-and-what-kind-of-document-it-is)
- [The OPSEC trap: perfect technique without a threat model](#the-opsec-trap-perfect-technique-without-a-threat-model)
- [The kinds of services on the darknet](#the-kinds-of-services-on-the-darknet)
- [Clearnet versus darknet: how the connection differs](#clearnet-versus-darknet-how-the-connection-differs)
- [Layering Tor, I2P and a VPN](#layering-tor-i2p-and-a-vpn)
- [What law enforcement can and cannot do, in public cases](#what-law-enforcement-can-and-cannot-do-in-public-cases)
- [The law in general terms](#the-law-in-general-terms)
- [Free exercises (reading only, nothing to install)](#free-exercises-reading-only-nothing-to-install)
- [Not verified, plainly](#not-verified-plainly)
- [Claims register](#claims-register)
<!-- END GENERATED PAGE CONTENTS -->

Side page to [Tor, I2P and the darknet without the myths](Tor-I2P-and-the-Darknet-Without-the-Myths.md). Read that one first: it explains how Tor and I2P work, who uses them and why the "government backdoor" story does not hold up, and this page does not repeat it. This page is about what is on these networks besides the legitimate uses, told through documented public cases: what a darknet market is, how the best-known ones ended, why most fail, what the real harms were, what the cases teach about operational security (OPSEC), and what happens when you combine Tor, I2P and a VPN. It is an educational and defensive page. It teaches you to read the evidence and to ask the right question first (what am I protecting, and from whom). It does not teach anyone to buy or sell anything.

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

> **Status: unverified draft, written from reading. Nothing on this page was run.** On **2026-11-01** I downloaded and read the pages named in the [claims register](#claims-register): Justice Department and Europol releases (some through the Internet Archive's saved copy, because the live pages block automated downloads), a federal appeals court opinion, a Wired article, an academic paper's abstract, the Tor Project's, Tails', Whonix's and I2P's own pages, and Wikipedia where a primary source could not be read. **Not run:** Tor, Tor Browser, I2P, any VPN, Tails, Whonix, and every setup described below. Nothing here was checked against a live network, and no onion or I2P service was visited. A claim I could not read on the page named is marked **est.** or **secondary**. Where a source and this page disagree, trust the source and tell us.

> **Prerequisites.** [Tor, I2P and the darknet without the myths](Tor-I2P-and-the-Darknet-Without-the-Myths.md) for what an onion service, an exit relay and a bridge are. [Threat model](Threat-Model.md) for the words "asset", "adversary" and "accepted risk". [Privacy versus security](Privacy-vs-Security-Blinds-and-Locks-Physical-Security-and-Monero.md) and [Cryptography fundamentals](Cryptography-Fundamentals-Symmetric-Asymmetric-Hashing-Certificates-and-Keys.md) help but are not required. No account, no install and no network are needed: this page is reading only. About 90 minutes (est.).

> **Where this runs, and the rule.** Nowhere: it is a reading lesson. Do not install or run Tor, I2P or anything named here to "go and look" on a work or school network, and check the law where you live first ([the law, in general terms](#the-law-in-general-terms)). There are no marketplace walkthroughs on this page and there will not be: no addresses of any market or forum, no buyer or vendor how-to, and no instructions for avoiding investigators. The cases are used the way a safety investigator uses an accident report: to see what went wrong.

## What you will be able to do

- Say what a darknet market is, and tell the story of Silk Road, AlphaBay and Hansa, and a few later cases, with dates and with sources you can open yourself.
- Explain why most markets end badly (a law enforcement operation, an exit scam, a scam on buyers, or an operator's mistake) and name the real harms.
- Say what kind of document the "Darknet Market Bible" is, what this page can and cannot say about it, and which general OPSEC ideas the public cases illustrate.
- Explain the OPSEC trap: effort spent on perfect technique, with no threat model, can cost a lot and still leave the real weakness untouched.
- Name the kinds of services found on the darknet, say how to find a legitimate service's official onion address from its own clearnet page, and say why copied link lists rot and mislead.
- Explain how a clearnet site and an onion service differ, what an exit node is, and what can leak between the two worlds.
- Compare Tor alone, a VPN before Tor, a VPN after Tor, and Tor next to I2P, with each side's argument from the projects' own pages, and say why the honest answer is "it depends on the threat model".
- Say what law enforcement did in public cases, what it did not do, and why those two lists are not a guarantee either way.

## What the wiki already says (and the gap)

| Idea | Where it is today | The gap this page fills |
|---|---|---|
| How Tor and I2P work, who uses them, tools, the government-funding myth | [Tor, I2P and the darknet without the myths](Tor-I2P-and-the-Darknet-Without-the-Myths.md) | The other side of the same networks: the markets, their history and what the cases teach. |
| Who attacks, and how | [Threats in plain words](Threats-in-Plain-Words.md) | Dated public cases of a different kind: operators and buyers, not victims of malware. |
| Assets, adversaries, accepted risk | [Threat model](Threat-Model.md), [Threat model exercise](Threat-Model-Exercise.md) | The same vocabulary applied to a person, not a cloud lab. |
| Hiding versus protecting | [Privacy versus security](Privacy-vs-Security-Blinds-and-Locks-Physical-Security-and-Monero.md) | Why perfect hiding is the wrong goal without a threat model. |
| Keys, signatures and hashes | [Cryptography fundamentals](Cryptography-Fundamentals-Symmetric-Asymmetric-Hashing-Certificates-and-Keys.md) | Why an onion address that is a public key cannot be "looked up", and why a lookalike is a different key. |

## What a darknet market is

A **darknet market** is a website that runs as an onion service on Tor (some have also used I2P) and lists goods and services for sale, usually paid in cryptocurrency. The first one to become famous was Silk Road. The Justice Department's 2014 indictment announcement describes it as "a hidden website designed to enable its users to buy and sell illegal drugs and other unlawful goods and services anonymously and beyond the reach of law enforcement", run on Tor with a Bitcoin payment system (press release dated 2014-02-04). Calling it a "market" is the operators' framing: the same release says almost all of its listings were illegal drugs, with hacking tools, stolen accounts and forged identity documents listed beside them.

The academic study quoted below describes the design that later markets copied: Tor hidden services to hide the location of both sides, a Bitcoin payment system, a feedback system to rate vendors and buyers, and a middleman service that held payment until the transaction was complete (Soska and Christin, USENIX Security 2015, abstract and introduction). That design is the cause of most of what follows. A market holds the money, so its operator becomes a target for police and for thieves, and for the operator's own temptation.

Two cautions before the history:

1. **This is about what is documented in court papers and official releases.** Law enforcement releases are written to announce a success. I quote their numbers as their claims, with the date, and where a number differs between two official sources I say so.
2. **Illegal does not mean exciting.** The documented picture is mostly boring, sad and avoidable: fraud, theft, overdoses and prison sentences. It is the opposite of the glamour that scare videos and "how it works" videos both sell.

## The documented history, in dates

| Date | What happened | Source (all read 2026-11-01) |
|---|---|---|
| about January 2011 | Silk Road created, according to the Justice Department. | DOJ release, 2014-02-04 |
| 2013-09-23 | Silk Road had nearly 13,000 listings for controlled substances, plus hundreds of listings for hacking services, digital goods such as malware and stolen accounts, and forged documents. | DOJ release, 2014-02-04 |
| 2013-10-01 | Ross Ulbricht arrested in a San Francisco public library; Silk Road shut down in October 2013. | DOJ release, 2014-02-04; Second Circuit opinion, 2017-05-31 |
| 2015-02-04 | Ulbricht found guilty on all seven counts by a jury. | FBI release, 2015-02-05 |
| 2015-03-18 | Wired reports Evolution, then the top market, stopped withdrawals and vanished, with rumors its administrators stole users' funds (not confirmed at the time). | Wired, 2015-03-18 |
| 2015-08 | Academic study of 16 markets over 2013 to 2015: the Silk Road shutdown spawned a whole ecosystem rather than ending the trade. | Soska and Christin, USENIX Security 2015 |
| 2017-05-31 | Second Circuit court of appeals affirms the conviction and life sentence. | Second Circuit opinion |
| 2017-06-20 | Dutch police take over the Hansa market under judicial authorization and covertly watch it. | Europol, 2017-07-20 |
| 2017-07-05 | AlphaBay's alleged creator and administrator arrested in Thailand; he died in custody on 2017-07-12. | DOJ release, 2017-07-20 |
| 2017-07-20 | AlphaBay and Hansa taken down together. | DOJ and Europol releases, 2017-07-20 |
| 2020-11-03 | Law enforcement seizes bitcoin later valued at over $1 billion, traced to a 2012 to 2013 theft from Silk Road. | DOJ release, 2020-11-05 (archived copy) |
| 2021-01-12 | DarkMarket servers seized and its alleged operator arrested, as reported from Europol. | The Verge, 2021-01-12 (archived copy) |
| 2021-10-26 | Operation Dark HunTor: 150 arrests across several countries, built on evidence from the DarkMarket takedown. | DOJ release, 2021-10-26 (archived copy) |
| 2022-04-05 | German and U.S. authorities announce the seizure of Hydra's servers (secondary source only). | Wikipedia, Darknet market |
| 2024-03 | Incognito Market's operator closes it by stealing users' deposits and trying to extort them. | DOJ release, 2026-02-03 (archived copy) |

Three cases in a little more detail.

### Silk Road, 2011 to 2013

The Justice Department says Ross Ulbricht created Silk Road around January 2011 under the name "Dread Pirate Roberts", ran it until it was shut down in October 2013, and that law enforcement agents made more than 100 undercover purchases from it between November 2011 and September 2013 (release dated 2014-02-04). The same release says about 173,991 bitcoins (worth over $150 million at the time) were seized, mostly from Ulbricht's own computer hardware. A federal jury found him guilty on all seven counts on 2015-02-04 (FBI release dated 2015-02-05). The Second Circuit affirmed the conviction and life sentence on 2017-05-31.

A second official source gives a different number for the same thing: the AlphaBay release says Silk Road "had reportedly approximately 14,000 listings" at the time of seizure, against the indictment release's "nearly 13,000" for controlled substances alone on 2013-09-23. They are not necessarily in conflict (one counts drugs, one counts everything and says "reportedly"), but it is a reminder to check what a number counts.

A later chapter shows how long these cases run. On 2020-11-05 the Justice Department announced a civil forfeiture complaint for thousands of bitcoins, valued at over $1 billion, seized on 2020-11-03. The release says investigators used a third-party bitcoin analysis company in 2020 to identify 54 previously unnoticed transactions, traced to a bitcoin address connected to a person it calls "Individual X", who had hacked the funds from Silk Road around 2012 and 2013.

### AlphaBay and Hansa, July 2017

The Justice Department says AlphaBay "operated for over two years" and was the largest criminal marketplace on the internet, with over 250,000 listings for illegal drugs and toxic chemicals and over 100,000 for stolen and fraudulent identification documents, counterfeit goods, malware and other items. Its alleged creator, Alexandre Cazes, a Canadian citizen living in Thailand, was arrested by Thai authorities on 2017-07-05 and died in custody on 2017-07-12; the release says he "apparently took his own life". The release also says investigators attributed multiple overdose deaths to purchases on the site and names two complaints in which an overdose death was traced to drugs bought on it (release dated 2017-07-20). Charges in an indictment are allegations, as the release itself says.

Europol's release of the same day describes a second, linked operation. Dutch police, with Europol, took over the Hansa market on 2017-06-20 under Dutch judicial authorization and for a month monitored what users did without their knowledge, while the AlphaBay action was prepared. Europol says that after AlphaBay went down, new members of Hansa rose eight-fold as people looked for a replacement, and that the Dutch police passed about 10,000 foreign buyer addresses to Europol. It also says more than 38,000 transactions were identified and intelligence went to partners in 37 countries. Europol calls this a strategy to "magnify the disruptive impact": the lesson for a defender is that an operation can be designed to use the exact thing people do when a site disappears.

### Incognito Market, 2020 to 2026

The Justice Department release of 2026-02-03 says Rui-Siang Lin, who ran Incognito Market under the name "Pharaoh", was sentenced to 30 years in prison. It says the market sold more than $105 million of narcotics between October 2020 and its closure in March 2024, and had more than 400,000 buyer accounts and more than 1,800 vendors. It also says Lin closed the market in March 2024 by stealing at least $1 million that users had on deposit, and then demanded that buyers and vendors pay him or he would publish their user history and cryptocurrency addresses. It describes a death on 2022-09-13 of a 27-year-old who took pills bought on the market as "oxycodone" that contained fentanyl, and says tablets bought by an undercover agent in November 2023 as "oxycodone" tested as fentanyl.

## Why most of them fail

The sources above, taken together, show four ways a market ends. Most end by more than one at once.

1. **A law enforcement operation.** Silk Road (arrest and seizure, 2013), AlphaBay and Hansa (2017), DarkMarket (2021) and Hydra (2022, secondary source) were all taken down by police. Operations also reach beyond the market: Operation Dark HunTor's release says it built on evidence from the DarkMarket takedown to identify vendors and buyers, ending in 150 arrests and the seizure of over $31 million in cash and virtual currency and 45 firearms, and says some of the vendor accounts it identified were on markets that had already closed.
2. **An exit scam.** The operators simply stop and keep the money held on the site. Wired described Evolution's disappearance on 2015-03-18, noting it was then only rumored, and a court record confirms the Incognito case. The reason it keeps happening is structural: the site holds users' money, users cannot get it back, and no one can complain to anyone.
3. **A scam on buyers or the site's own users.** Beyond the operator, an anonymous vendor can take payment and never deliver, a fake copy of a site can steal logins, and in the Incognito case the threat to publish buyers' records shows what a site that logged everything can do with it. The Wikipedia article on darknet markets says phishing and scam sites are "often maliciously or accidentally referenced" in the lists people use to find markets (secondary source, read 2026-11-01).
4. **Operational mistakes.** The public court record of the best-documented case is in the next section. Another, from a secondary source, is that a moderator of Wall Street Market reportedly posted the market's hidden IP address on a forum in May 2019 (Wikipedia's Dread article, citing a news report that I did not read).

The study in the table above measured the effect of all this over two years and found that the shutdowns did not shrink the trade for long: "Far from causing the demise of this novel form of commerce, the Silk Road take-down spawned an entire, dynamic, online anonymous marketplace ecosystem." That is the academic finding for 2013 to 2015, not a prediction. It also means a "dark web is dead" headline is as unreliable as a "dark web is booming" one.

### The real harms

The sources name harms that do not depend on your view of drug policy:

- **Deaths and poisoning.** The AlphaBay and Incognito releases above say overdose deaths were attributed to purchases, and the Incognito release says pills sold as a pharmaceutical contained fentanyl. A buyer cannot test what an anonymous seller ships.
- **Theft and extortion of the market's own users.** Evolution (reported), Incognito (court record).
- **Exposure of buyers.** The Hansa takeover collected buyer addresses; Operation Dark HunTor identified buyers and vendors from seized evidence. Buyers risk arrest, not only vendors: the Justice Department's October 2021 release says agencies identified darknet drug vendors and buyers after the DarkMarket takedown.
- **A hostile environment for everyone else.** Fraud, stolen data, malware and forged documents were sold on these sites, so the victims are often people who never touched them.
- **Cost to the operators.** Sentences in the sources include life (Silk Road) and 30 years (Incognito), and one operator's death in custody.

## The Darknet Market Bible and what kind of document it is

The maintainer's issue for this page names the **Darknet Market Bible** as a well-known community document about operational security for people who use these markets. **Partly read, Introduction page only:** I searched for a reputable page that describes it (a news article, a court filing or a research paper) and found none that I could read. I then read the document's Introduction page, in the Internet Archive's saved copy captured on 2024-12-29 (the capture date shown in the saved copy's address). I did not use the live site, because it failed a certificate check. I read no other page, and I will not describe its procedures, its other contents, its authors, its length or its dates.

What that one page says, at the level of principles:

- It presents itself as a complete guide for buyers on darknet markets, built on operational security practice.
- It says there is never 100 percent security, and claims that following it exactly makes an arrest hard.
- It says the setup takes hours to learn, that it is not for everyone, and that people with little computer experience should stay away from these markets or risk legal trouble.
- The site's host describes itself as "hosting, for research and archival purposes, an historical document created on the darknet by anonymous authors", and says it does not recommend, support, endorse, participate in or earn money from the activities described.

The maintainer's own account, **unsourced beyond his word:** he first found the document years ago on Dread or some other darknet site and does not remember which, so it circulated on the darknet before the clearnet site, and he read it again on that site. Dread is named here only as the kind of forum where such a document is found, with no address. The host's wording above is consistent with that, but I found no source that says where or when the document first appeared, and this page makes no other claim about that.

Two things are worth taking from that, neither of which needs the document:

- **It is a kind of document, and the kind has a risk.** A checklist written by a community, for a community, is advice about that community's threats as its authors saw them at one time. A checklist does not know who you are. A long checklist read as a recipe gives the sense that following it makes you safe. That is the trap in the next section. This page does not summarize its procedures, and a lesson that did would be a how-to for the very trade the cases above describe.
- **The general principles that any OPSEC guide teaches can be seen in public cases without it.** The four that matter most are listed below, each with a source I did read.

### Four general principles, seen in public cases

| Principle | What it means | A case in the sources |
|---|---|---|
| **Threat modeling** | Decide who you are protecting against and what they can do, before choosing tools. | The Second Circuit opinion describes a defendant who used Tor and Bitcoin and was identified anyway, by an adversary (federal investigators with legal process, undercover accounts and the power to seize devices) that is a very different adversary from "a stranger who wants to find my IP address". Tools chosen against one adversary say little about another. |
| **Compartmentalization** | Keep separate activities and identities from touching each other. | Tails' warnings page says using one session for several purposes lets an adversary link them, and that logging in to different accounts on the same site in one session does the same. Qubes' introduction (read for the Tor lesson on 2026-10-31, not re-read here) describes isolating activities in separate virtual machines. See [the Tor lesson's section on what these tools do not protect against](Tor-I2P-and-the-Darknet-Without-the-Myths.md#what-none-of-these-protect-against). |
| **Metadata** | Data about a thing (when, where, who, how often) can identify you when the content cannot. | Tails' warnings page lists date, time, location and device information in files. In the Second Circuit opinion, travel plans that the defendant discussed in chat matched his own email itinerary and a social media photo album; the court also describes bitcoin transaction history on his laptop being traced to the site's servers. |
| **Reuse of identities** | The same username, address, key or habit in two places joins the two places. | The Second Circuit opinion says the same private PGP key signed the administrator's posts for the site's whole life, and it was found on his laptop; it also says a Gmail account whose address included his full name held the itinerary above. Wikipedia (secondary) says an early public post promoting the site, from an account that later led to his personal email address, was the first thing an investigator found; I did not read that primary source. |

Notice the shape: in none of these was the cause a broken Tor protocol. It is the same pattern as the documented Tor attacks in [the Tor lesson](Tor-I2P-and-the-Darknet-Without-the-Myths.md#documented-de-anonymizations-what-actually-broke): the weak link is a browser, a hosting service, a relay or a person.

## The OPSEC trap: perfect technique without a threat model

OPSEC (operational security) started as a military habit: look at your own activity as an adversary would, and find what gives you away. Done well, it begins with a threat model, as in [Threat model](Threat-Model.md): what is worth protecting, who is after it, what they can do. The trap is to skip that and go straight to the tools and the rules.

What the trap costs, from sources I read:

- **Effort and fragility.** The Whonix community page on combining Tor with other tunnels says of one rare setup that "very few people are likely to configure it, reducing the Tor Browser user pool to a far smaller subset" and recommends against it because of the fingerprinting harm. A setup chosen to be safer made the user easier to pick out.
- **False confidence.** Tails' warnings page says Tails cannot always protect you if you install it from an infected computer or run it on compromised firmware or a physical keylogger, and the Tor Project's support page says the combination of Tor with a VPN can "reduce anonymity or break Tor's protections if not configured correctly". The more layers, the more places for a misconfiguration to hide, and the more reason to believe you are covered.
- **Attention on the wrong layer.** In the Second Circuit case the court record lists strong tools (Tor, PGP, Bitcoin) and weak habits (a real-name email address, travel plans that matched, one long-lived key on one laptop). Effort spent on the first layer did not protect the second.

The order that avoids the trap, and the only advice this page gives:

1. **Threat model first.** Who might want what you have or want to know what you do? What can they do (read your network traffic, ask a company for records, seize a device, bribe an insider)? What happens if they succeed?
2. **Then the smallest set of measures that answers that.** For most people the answer is not "more layers"; it is a password manager, a second factor and updates, as in [Secrets from day one](Secrets-From-Day-One.md) and [Threats in plain words](Threats-in-Plain-Words.md).
3. **Then check your habits, not only your tools.** Reuse, metadata and mixing are habits.
4. **Accept what you cannot cover, and write it down.** That is what "accepted risk" means in the repository's own [Threat model](Threat-Model.md).

None of this says the people in the cases deserved sympathy for being "unlucky with their tools". They ran the criminal businesses the court records describe. It says that reading their mistakes is useful for a defender.

The same ideas for an ordinary person browsing over Tor or I2P, and not for a market's operators, are on [OPSEC for Tor and I2P that holds up](OPSEC-for-Tor-and-I2P-That-Holds-Up-Identities-Layers-Metadata-and-Habits.md): the four layers of an identity (device, network, account, behavior), the Tor Project's own browsing rules with their reasons, a three-question test for OPSEC theater, and separate checklists for a beginner and for someone at risk. That page does not retell the cases here.

## The kinds of services on the darknet

Everything below is named as what it is, with no addresses. I opened none of these services. Where a category comes from Wikipedia's navigation box for Tor onion services (read 2026-11-01), it is a secondary listing.

- **Forums.** Wikipedia describes **Dread** as a Reddit-like dark web forum, launched in 2018, that became a place to discuss markets, law enforcement activity and scams after Reddit banned its darknet market communities (secondary; it cites news reports). A forum is where claims about a market appear, and its posts are claims by anonymous people, which is exactly why scams live there too.
- **Link directories.** Pages or sites that list addresses, such as **dark.fail** (named in the maintainer's issue; I did not open it) and the historical **Hidden Wiki** (named in Wikipedia's box). Another kind was the news and links site **DeepDotWeb**, which Wikipedia says was seized in May 2019 for conspiring with the markets (secondary; I did not read the release).
- **Search engines.** Wikipedia's box lists search engines such as Ahmia, DuckDuckGo, Kagi and MetaGer.
- **Email and messaging.** The same box lists Proton Mail and Riseup among services that also keep an ordinary website.
- **News.** The box lists BBC News, ProPublica, The Guardian, The Intercept, Deutsche Welle, Bellingcat and The New York Times, among others. The Tor lesson dates several of these and reads the organizations' own announcements: [who relies on it](Tor-I2P-and-the-Darknet-Without-the-Myths.md#who-relies-on-it-news-organizations-and-securedrop).
- **Libraries and archives.** The box lists the Internet Archive.
- **Operating systems and tools.** Tails, Whonix and Qubes OS, and the SecureDrop whistleblower system, appear in the box.
- **Markets and forums for crime.** The rest of that box (Silk Road, AlphaBay, Hansa, Hydra and others) is historical, with most of them marked as offline or discontinued.

The box's own legend marks which services also keep a presence on the ordinary web and which are offline or discontinued. That is the useful signal: the legitimate services in it are mostly the ones with a normal website too, and the dead ones are mostly the markets.

### How to find the official address of a legitimate service

Go to the service's own website, over HTTPS, the way you would anyway. The Tor Project documents a mechanism called **Onion-Location** for exactly this: a site's operator adds a header (or a page tag) that advertises the site's onion address, and Tor Browser then shows a purple pill in its address bar so a visitor can switch. The Tor Project's page lists three conditions for the header to be valid: the value must be a valid URL with a .onion hostname, the page that sets it must be served over HTTPS, and that page must not itself be an onion site (read 2026-11-01). The trust comes from the HTTPS site you already reached through its own domain name, not from a list.

For news organizations and SecureDrop, the same rule applies: use the organization's own page. This page prints no onion address, for markets or for anything else.

### Why copied link lists rot and mislead

- **They go stale.** Sites close, are seized or exit-scam, as the cases above show, and the list entries stay.
- **They are poisoned.** Wikipedia's article says phishing and scam copies are often listed by accident or on purpose (secondary), and the Tor Project's design makes an onion address a public key, so a lookalike address is a different, attacker-controlled service. Nothing in the address tells you whose it is.
- **A directory is itself a target and a weak point.** DeepDotWeb (above) was seized, according to Wikipedia, and a directory that once checked its entries stops doing so when it vanishes.
- **A key that leaks is a key that can be taken over.** Wikipedia's Dread article says that in October 2026 the forum's main onion service key was leaked and the old address hijacked by a third party (secondary; unconfirmed here). If that account is accurate, an address you saved last month could belong to someone else today.

## Clearnet versus darknet: how the connection differs

- **Clearnet.** A website with a normal domain name and a public server address. Your connection to it is ordinary internet traffic, protected (or not) by HTTPS. If you use Tor to reach it, your traffic leaves Tor at a relay called the **exit node**, which makes the last connection to the site.
- **Onion service.** A server whose address is its public key, reached through Tor without an exit node: Tor's own overview says the client and the service meet at a relay in the network, using six relays in all, and the server needs no public IP address or open inbound port ([the Tor lesson, onion services](Tor-I2P-and-the-Darknet-Without-the-Myths.md#onion-services)).

What the Tails warnings page (read 2026-11-01) says about the exit node on the clearnet side:

- The exit node makes the actual connection to the destination. That last step can be unencrypted (plain HTTP), in which case the exit node can read it.
- A malicious exit node can pretend to be the destination (a machine-in-the-middle attack), which is why browser security warnings matter more over Tor.
- The sites you visit can know you use Tor, because the list of exit nodes is public; many ask for a CAPTCHA or block it.
- Your ISP and local network can see that you connect to Tor, but not which sites you visit. A bridge hides even that.

What can leak between the two worlds, all from sources I read:

| Leak | What happens | Source |
|---|---|---|
| Unencrypted clearnet traffic | The exit node sees it. | Tails warnings |
| An identity you carry across | Logging in to the same account, or using one session for several purposes, links activities. | Tails warnings |
| A mistake outside Tor | The 2013 Freedom Hosting malware sent the computer's hardware address and hostname to a server outside Tor. | See the [Tor lesson](Tor-I2P-and-the-Darknet-Without-the-Myths.md#documented-de-anonymizations-what-actually-broke) |
| Metadata in what you share | Files carry date, time, location and device details. | Tails warnings |
| A clearnet footprint of an onion operator | A real-name account, travel plans and a long-lived key connected an onion service administrator to a person. | Second Circuit opinion |
| Watching both ends | An adversary who sees traffic go in and come out can correlate timing; no network for fast traffic can fully protect against it. The Tails page says it knows of no actual use of this against Tails users. | Tails warnings; Tor Project |
| The address itself | Someone who reaches the clearnet page that advertises an onion address can see both. That is on purpose for a legitimate service. | Tor Project, Onion-Location |

So the simple rule from the sources is: an onion service avoids the exit-node risks, but nothing about it protects what you bring with you.

## Layering Tor, I2P and a VPN

People often ask whether adding a VPN, or running I2P as well as Tor, makes them safer. The projects' own pages say, in short: not automatically, and sometimes the reverse. Each argument below is the source's, with a date, and the Whonix page is explicitly a community-supported page that labels the anonymity effects of these combinations as "disputed".

| Combination | The case for it | The case against it |
|---|---|---|
| **Tor alone** | The default design: three independent relays so no single one learns both who you are and where you go (Tor Project, protections page, read 2026-11-01). Tails: VPNs "are less secure than Tor, because they do not use 3 independent relays" for rapid connections. | Your ISP sees that you use Tor (Tails); correlation at both ends remains possible. |
| **VPN, then Tor** (you connect to the VPN first) | Whonix lists these use cases: you must use a VPN or proxy to reach the internet; your ISP blocks Tor and Tor bridges but not the VPN; concern about attacks on the Tor network. The ISP then sees VPN traffic, not Tor. | A VPN that knows who you are may be "more willing and able" to harm your privacy than an ISP; if the VPN drops, traffic can go through the ISP unprotected; the page says it is "questionable" this adds protection, and a bridge is a simpler fix for a blocked Tor. The Tor Project's support page: it can "reduce anonymity or break Tor's protections if not configured correctly". |
| **Tor, then VPN** (traffic leaves Tor into the VPN) | Whonix: the destination sees a VPN address rather than a Tor exit, which can help with sites that ban exit nodes. | Onion services cannot be reached; per-tab circuit separation is lost; the VPN provider becomes the one trusted party and a point where traffic can be watched; the browser's fingerprint can worsen; payments and logs at the VPN can identify you. |
| **VPN without Tor** | A different job: encrypts the path to a network you trust, hides traffic from a local network. See [VPN versus ZTNA](Zero-Trust-at-Home-Two-Connectors-and-Failover.md#vpn-versus-ztna-under-real-residential-conditions). | Not an anonymity network: the provider can see who you are and where you go (this wiki's own earlier comparison; Tails agrees). |
| **Tor and I2P, each for its own purpose** | The I2P project's own comparison page (updated 2025-10) says I2P is built for services inside its own network, with exits to the regular internet "limited (discouraged)", while Tor's focus is clearnet access through exits. Using each for what it is built for follows from that. | That page is the I2P project's view of itself. The Monero project's document, read earlier in the Tor lesson, says I2P has fewer users and less cover traffic. I read no project guidance on chaining one through the other, so this page gives no verdict on that. |

The Tor Project's own summary (support page, read 2026-11-01) is the most cautious: combining a VPN with Tor might seem to add privacy, but "in practice it can reduce anonymity or break Tor's protections if not configured correctly", and the project does not recommend it "unless you're an advanced user who knows how to configure both in a way that doesn't compromise your privacy". I could not read the Tor Project's longer wiki page on Tor plus VPN, which the support page points to, so I do not summarize it.

**The honest conclusion: it depends on the threat model.** A person whose ISP blocks Tor has a different problem from a person worried about a site that bans exit nodes, who has a different problem from a person watched by a state that can see both ends. Each added layer adds a party to trust, a setting that can fail and a pattern that can make you stand out. The right number of layers is the smallest that covers the threat you wrote down, which is the same order as in [the OPSEC trap](#the-opsec-trap-perfect-technique-without-a-threat-model).

## What law enforcement can and cannot do, in public cases

Read as documented history, not as a promise either way.

**What the public record shows they have done:**

- **Arrest an operator while logged in.** In the Silk Road case, agents watched Ulbricht enter a public library, an undercover administrator account started a chat that led him to log in as the site's administrator, and he was arrested on 2013-10-01 (Second Circuit opinion). The opinion says his laptop held, among other items, the private key that signed his posts, chat logs and journal entries.
- **Trace money.** Bitcoin transactions were traced on a public ledger in the Silk Road cases (the opinion's 89 percent figure; the 2020 forfeiture), and AlphaBay's release says investigators froze and preserved millions of dollars in cryptocurrency and seized luxury assets in several countries.
- **Seize servers and use what is on them.** The DarkMarket servers, per Europol as reported, and the Hansa takeover under court authorization (Europol).
- **Cooperate across borders.** Europol says 12 agencies agreed one strategy for AlphaBay and Hansa; the AlphaBay release lists agencies in seven countries and Europol.
- **Follow the physical world.** The Dark HunTor release quotes a postal inspector saying criminals ship goods through the mail and private carriers, so the mail is another place investigators look.
- **Ask a court, with limits.** The Second Circuit held that collecting IP address routing information, without contents, did not need a warrant in that case (court summary).

**What I did not find, and what is disputed:**

- **I read no case in which Tor's encryption itself was broken.** The documented attacks on Tor in the Tor lesson were on a browser, a hosting service and relays, and each was fixed. That is a statement about what I read, not a proof that it has never happened or never will.
- **Methods are not always public.** The FBI said it found Silk Road's server through a leak from the site's CAPTCHA, and security experts have doubted that account (Wikipedia, secondary; I did not read the original reports). A claim in an official release is a claim.
- **A release is not a verdict.** The AlphaBay release says charges are "merely allegations". The DEA head is quoted there as saying "the so-called anonymity of the dark web is illusory"; that is an official's statement, written to deter, not evidence of capability.
- **Not everything is solved.** Evolution disappeared and the sources I read describe no arrest. The Soska and Christin study found the ecosystem recovered after the shutdowns it measured.

For a defender or learner the useful reading is the one in [the OPSEC section](#the-opsec-trap-perfect-technique-without-a-threat-model): in the cases above, the investigators' route to a person ran through money, accounts, devices, habits and people, not through defeating the anonymity network.

## The law in general terms

Laws differ by country, state and network. In many places running Tor or I2P as a user is lawful and what you do over them is judged by the same law as anywhere else; some places restrict or block these tools. The cases above were prosecuted as things like conspiracy to distribute narcotics, money laundering, trafficking in fraudulent identification documents, computer hacking and operating a continuing criminal enterprise (Silk Road, Second Circuit opinion and DOJ releases), and buying is charged too (Dark HunTor). Operating a market, selling on one, buying from one and laundering the proceeds are crimes in the cases cited. A reader is expected to treat this page as the history of those cases, not as a guide to what is lawful for them. **Check your own jurisdiction, and your employer's or school's rules, before you install or run any of these tools.** Nothing here is legal advice.

## Free exercises (reading only, nothing to install)

1. **Threat-model three imaginary people.** For each, write four lines: what they are protecting, who the adversary is and what it can do, which measures from this wiki matter, and which tools in this lesson would not help. Then compare with the last section.
   - **Sam**, a nurse in a country that blocks a news site, who wants to read it on a home laptop.
   - **Priya**, a graduate student who is tired of being followed around the web by advertising trackers.
   - **Lee**, who runs a small online forum and is worried that someone who is angry with them will find their home address.

   A short worked answer for Sam: the asset is the ability to read and not to be identified as a reader; the adversary is the network operator or the state, which can block and log; what matters is a way around the block and keeping HTTPS on, and a bridge if Tor itself is blocked; what does not help is layering a VPN on Tor "to be safe", since the Tor Project says that can reduce anonymity. Write your own for Priya and Lee before reading anyone else's.
2. **Read a public case and list the mistakes.** Open one of the primary sources in the [claims register](#claims-register): the Second Circuit opinion in the Silk Road case, or the Justice Department's AlphaBay or Incognito release. List every thing that, by the document's own account, connected the operator to the site or to the money. Put each in one of five boxes: identity reuse, money, devices, habits, people. Then write, in one sentence each, which threat the operator seems not to have modeled. Do not look for a way to avoid these; look for what the investigators actually used.
3. **Test a scary claim.** Take a "dark web" claim from a video or article and ask the Tor lesson's question: can I open the source myself? Then ask this lesson's question: what does it say happened, on what date, in what document?
4. **Stale and poisoned lists.** Find one article that offers a ranked list of onion sites to visit. Without opening any of them, write down which of the four problems under [why copied link lists rot and mislead](#why-copied-link-lists-rot-and-mislead) it has, and how the site's own clearnet page would solve it.

## Not verified, plainly

- Nothing was run (see the banner). No onion or I2P service, VPN or network was touched.
- **The Darknet Market Bible:** I found no reputable page describing it. I read its Introduction page only, in the Internet Archive's copy captured on 2024-12-29, because the live site failed a certificate check. I read no other page and describe no procedures. Where it first appeared is the maintainer's account alone (unsourced beyond his word).
- **dark.fail, the Hidden Wiki and Dread:** I did not open any of them. Dread and DeepDotWeb facts come from Wikipedia, which cites news reports I did not read. The October 2026 Dread incident is from Wikipedia alone.
- **Hydra (2022), Wall Street Market (2019) and the DeepDotWeb seizure (2019)** are secondary only. The Justice Department's and Europol's own releases for them were not read.
- **Live pages that block automated downloads.** The Justice Department's own pages blocked my download. The AlphaBay, Silk Road indictment, Silk Road forfeiture, FBI conviction and Dark HunTor texts, and the Incognito release, were read in the Internet Archive's saved copies; the Second Circuit opinion was read in an archived copy of a legal publisher's page. I have not checked those against the live pages. The Europol and The Verge releases are also archived copies.
- **Not read:** the Silk Road criminal complaint, the AlphaBay forfeiture complaint (linked from the release), the full text of the Soska and Christin paper beyond its abstract and introduction, and the Tor Project's long "Tor plus VPN" wiki page.
- **Layering:** I read no guidance on running one anonymity network through the other (Tor over I2P, I2P over Tor). Whonix's page says Tor over Tor is discouraged and lists such a setup only by name.
- **Numbers** are the releases' claims with their dates. Two differ (Silk Road listings) and are shown side by side.
- **No country's law was checked.** The list of charges is from the cited cases only.
- **The Whonix tunnels page** is community-supported and calls its own anonymity conclusions disputed; I did not test any combination, so nothing here is advice to use one.
- Attribution of an early forum post to Ulbricht's personal email address is from Wikipedia alone.

## Claims register

Every row carries a status: **Read** means the sentence is on the page named, read on the date shown; **Secondary** means a Wikipedia statement I could not trace to a primary source I read; **General knowledge** means common knowledge I did not source; **est.** means I could not read it on a project page. Archived copies are marked.

| Claim | Source | Status |
|---|---|---|
| Silk Road created about January 2011; shut down October 2013; nearly 13,000 controlled-substance listings on 2013-09-23; more than 100 undercover purchases November 2011 to September 2013; 173,991 bitcoins seized; hacking, malware and forged-document listings | Justice Department, [Manhattan U.S. Attorney announces the indictment of Ross Ulbricht](https://web.archive.org/web/2015/https://www.justice.gov/usao-sdny/pr/manhattan-us-attorney-announces-indictment-ross-ulbricht-creator-and-owner-silk-road) (2014-02-04; archived copy) | Read 2026-11-01 (the department's claims) |
| Ulbricht found guilty on all seven counts on 2015-02-04 | FBI New York, [Ross Ulbricht found guilty](https://web.archive.org/web/2016/https://www.fbi.gov/contact-us/field-offices/newyork/news/press-releases/ross-ulbricht-the-creator-and-owner-of-the-silk-road-website-found-guilty-in-manhattan-federal-court-on-all-counts) (2015-02-05; archived copy) | Read 2026-11-01 |
| Arrest in a public library on 2013-10-01 after agents watched him enter and the administrator account came online; the private PGP key, chat logs and journal were on the laptop; one key signed posts for the site's life; Gmail address with his full name held a travel itinerary matching the administrator's chat; 89 percent of bitcoins on the laptop traced to the site's servers; conviction and life sentence affirmed 2017-05-31; IP address routing information needed no warrant in that case | Second Circuit, [United States v. Ulbricht, No. 15-1815](https://web.archive.org/web/2018/https://law.justia.com/cases/federal/appellate-courts/ca2/15-1815/15-1815-2017-05-31.html) (decided 2017-05-31; archived copy of a legal publisher's page) | Read 2026-11-01 |
| Silk Road had "reportedly approximately 14,000 listings" at seizure; AlphaBay over 250,000 drug and chemical listings and over 100,000 other listings; creator arrested in Thailand 2017-07-05 and died in custody 2017-07-12; overdose deaths attributed to purchases; "merely allegations"; DEA head's "illusory" quote; agencies from seven countries plus Europol | Justice Department, [AlphaBay, the largest online dark market, shut down](https://web.archive.org/web/2017/https://www.justice.gov/opa/pr/alphabay-largest-online-dark-market-shut-down) (2017-07-20; archived copy) | Read 2026-11-01 (the department's claims) |
| Hansa taken over 2017-06-20 under Dutch judicial authorization and covertly monitored until 2017-07-20; about 10,000 foreign buyer addresses passed to Europol; new Hansa members rose eight-fold after AlphaBay went down; more than 38,000 transactions and 37 countries; 12 agencies agreed one strategy; creator described as living a luxurious life in Thailand | Europol, [Massive blow to criminal Dark Web activities](https://web.archive.org/web/20200923012843/https://www.europol.europa.eu/newsroom/news/massive-blow-to-criminal-dark-web-activities-after-globally-coordinated-operation) (2017-07-20; archived copy) | Read 2026-11-01 |
| Over $1 billion in bitcoin seized 2020-11-03, traced to a 2012 to 2013 theft from Silk Road; 54 previously unnoticed transactions found with a third-party analysis company; "Individual X" | Justice Department, [United States files civil action to forfeit cryptocurrency valued over one billion](https://web.archive.org/web/20201115082457/https://www.justice.gov/usao-ndca/pr/united-states-files-civil-action-forfeit-cryptocurrency-valued-over-one-billion-us) (2020-11-05; archived copy) | Read 2026-11-01 (allegations in a civil complaint) |
| Evolution halted withdrawals and vanished; rumors the administrators stole users' funds; not confirmed then | Wired, [The Dark Web's Top Drug Market, Evolution, Just Vanished](https://web.archive.org/web/20150705173147/http://www.wired.com/2015/03/evolution-disappeared-bitcoin-scam-dark-web/) (2015-03-18; archived copy) | Read 2026-11-01 (reporting, unconfirmed at the time) |
| Study of 16 markets over 2013 to 2015; the Silk Road shutdown "spawned an entire, dynamic, online anonymous marketplace ecosystem"; the market design of hidden services, Bitcoin, feedback and a payment-holding service | Soska and Christin, [Measuring the Longitudinal Evolution of the Online Anonymous Marketplace Ecosystem](https://www.usenix.org/system/files/conference/usenixsecurity15/sec15-paper-soska-updated.pdf) (USENIX Security 2015-08) | Read 2026-11-01 (abstract and introduction only) |
| DarkMarket servers seized, alleged operator arrested; about 500,000 users and over 320,000 transactions; about 140 million euros traded | The Verge, [DarkMarket shutdown](https://web.archive.org/web/20210113015853/https://www.theverge.com/2021/1/12/22227929/darkmarket-shutdown-europol-worlds-largest-illegal-marketplace) (2021-01-12; archived copy; reports Europol's figures) | Read 2026-11-01 |
| Operation Dark HunTor: 150 arrests, over $31 million seized, 45 firearms, vendors and buyers identified following the DarkMarket takedown; a postal inspector on mail shipping | Justice Department, [International law enforcement operation targeting opioid traffickers on the darknet](https://web.archive.org/web/20240124004021/https://www.justice.gov/opa/pr/international-law-enforcement-operation-targeting-opioid-traffickers-darknet-results-150) (2021-10-26; archived copy) | Read 2026-11-01 (the department's claims) |
| Incognito Market: more than $105 million in sales, 400,000 buyer accounts, 1,800 vendors; operator sentenced to 30 years; March 2024 theft of at least $1 million and extortion demand; fentanyl pills sold as oxycodone; a death on 2022-09-13 | Justice Department, [Incognito Market owner sentenced to 30 years](https://web.archive.org/web/2026/https://www.justice.gov/usao-sdny/pr/incognito-market-owner-sentenced-30-years-operating-one-worlds-largest-online) (2026-02-03; archived copy) | Read 2026-11-01 (the department's account of the evidence at sentencing) |
| Darknet markets use Tor and Bitcoin or Monero, hold buyers' funds; exit scams (Evolution, Wall Street Market named); phishing and scam sites often listed; Operation Onymous 2014; Hydra seizure announced 2022-04-05; DeepDotWeb seized 2019 | Wikipedia, [Darknet market](https://en.wikipedia.org/wiki/Darknet_market) | Secondary, read 2026-11-01 |
| Dread is a Reddit-like dark web forum launched in 2018; a Wall Street Market moderator posted the market's hidden IP address in May 2019; the October 2026 key leak and hijack; the box listing services (search engines, news, email, archives, operating systems) and whether each keeps a presence on the ordinary web | Wikipedia, [Dread (forum)](https://en.wikipedia.org/wiki/Dread_(forum)) (page last edited 2026-10-27) | Secondary, read 2026-11-01 |
| Early forum post that led to Ulbricht's personal email; FBI's CAPTCHA-leak claim doubted by experts | Wikipedia, [Silk Road (marketplace)](https://en.wikipedia.org/wiki/Silk_Road_(marketplace)) | Secondary, read 2026-11-01 |
| Do not combine a VPN with Tor unless an advanced user; it "can reduce anonymity or break Tor's protections if not configured correctly" | Tor Project, [Using Tor Browser with a VPN](https://support.torproject.org/faq/faq-5/) | Read 2026-11-01 |
| Three relays, distributed trust, no single relay learns who you are and what you do | Tor Project, [What protections does Tor provide?](https://support.torproject.org/about/protections/) | Read 2026-11-01 |
| Exit node can read unencrypted traffic and can impersonate the destination; sites can know you use Tor; ISP sees Tor but not sites; bridges; correlation at both ends and no known actual use against Tails users; VPNs less secure than Tor for fast traffic; separate sessions for separate purposes; file metadata | Tails, [Warnings](https://tails.net/doc/about/warnings/index.en.html) | Read 2026-11-01 |
| Combinations of Tor with a VPN or proxy: use cases, risks, anonymity effects "disputed", community-supported page; Tor over Tor discouraged; onion services unreachable after a post-Tor VPN; stream isolation and fingerprint effects | Whonix, [Tunnels: Introduction](https://www.whonix.org/wiki/Tunnels/Introduction) | Read 2026-11-01 (community-supported) |
| I2P is built for in-network services; exits to the regular internet limited and discouraged; Tor's focus is clearnet access via exits | I2P, [I2P vs other privacy networks](https://geti2p.net/en/comparison/tor) (updated 2025-10) | Read 2026-11-01 (the project's view of itself) |
| Onion-Location header: how a site advertises its onion address; valid only on an HTTPS page that is not itself an onion site; Tor Browser shows a purple pill | Tor Project, [Onion-Location](https://community.torproject.org/onion-services/advanced/onion-location/) | Read 2026-11-01 |
| Onion service structure, six relays, address is a key | [Tor, I2P and the darknet without the myths](Tor-I2P-and-the-Darknet-Without-the-Myths.md) (this wiki), from the Tor Project's own overview | Read 2026-10-31 on that page; not re-read here |
| The "Darknet Market Bible" is a well-known community OPSEC document | The maintainer's issue 381 | Read in the issue; no other source found (**est.**) |
| The Bible's Introduction page: a guide for buyers built on operational security, no complete security, hours to learn, not for everyone; the host's "research and archival purposes" statement | The Introduction page of the Darknet Market Bible, cited in plain text and not linked: the Internet Archive's saved copy captured 2024-12-29 (issue 423); the live site failed a certificate check and was not used | Read 2026-11-01 (Introduction page only; no other page read) |
| The document circulated on the darknet first, and the clearnet site is an archival copy | The maintainer's account in issue 423: found on Dread or some other darknet site years ago, site not remembered | Unsourced beyond his word; the host's own "historical document created on the darknet" wording is consistent but is not a source for where or when it first appeared (**est.**) |
| dark.fail is an example of a link directory | The maintainer's issue 381 | Read in the issue; not opened (**est.**) |
| Laws on these tools and on the trades in the cases differ by place | General knowledge | General knowledge; no country checked |
