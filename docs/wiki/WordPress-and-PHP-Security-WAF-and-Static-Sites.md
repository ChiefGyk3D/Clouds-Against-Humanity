# WordPress and PHP security, WAFs, and why static sites win so often

Side page to [Droplet hardening](Droplet-Hardening.md), and lesson 2 of a four-lesson web-hosting track. Read it when you have a LAMP or LEMP stack (or are about to run one) and want to know what makes it risky, what to harden, what a web application firewall (WAF) really does, and why a plain folder of files is so often the better answer. Next: [Threat model](Threat-Model.md).

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

> **Status: written from vendor and project documentation read on 2026-10-22; three of the five exercises were run once on Linux that day; the PowerShell lines and the two container exercises were not run.** Exercises 1, 2 and 5 (Bash) and the small memory-safety demo were run on Linux with PHP 8.4.26, Python 3.13 and rustc 1.99.0, and the output shown is trimmed from those runs. Exercise 3 (a WordPress container) and Exercise 4 (ModSecurity with the Core Rule Set) need container images that I could not pull in my environment, so they are written from the image documentation and marked **est.** (estimate): run them expecting to fix something. Every figure and quotation names the page it came from in the claims register at the end. Vendor statistics are the vendor's own and the vendors sell products in this area; the register says so. Cost: $0. The reading and every exercise on this page run on your own computer, are free and always will be, and use only the loopback address (`127.0.0.1`), which no other machine can reach. Nothing here asks you to scan, probe or attack anything you do not own. There is no working exploit code on this page; attack classes are named so you can defend against them. The project's real spending lives on the [cost page](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/cost.md).

> **Prerequisites.** A terminal ([Git from zero](Git-From-Zero.md#what-a-terminal-is) shows how to open one), `php` (version 8.2 or newer) and `curl` for Exercises 1 and 2, `python3` for Exercise 5, and Docker or Podman only for the two optional container exercises ([Containers and Docker basics](Containers-and-Docker-Basics.md) explains them). It helps to have read [How a web request works](How-a-Web-Request-Works.md) and [Threats in plain words](Threats-in-Plain-Words.md), because this page uses the words request, header, vulnerability, exploit, patch and CVE without stopping to define them again. About 3 hours for the reading and the free exercises (est.).

> **The four-lesson web-hosting track.** This is lesson 2. The others are written at the same time as this one, so their links may not resolve until they are merged, and for that reason none of them is in the closing line of the introduction above. Lesson 1: [LAMP and LEMP from zero](LAMP-and-LEMP-From-Zero.md). Lesson 3: [DNS, Cloudflare and hosting your own website](DNS-Cloudflare-and-Hosting-Your-Own-Website.md). Lesson 4: [WordPress at scale: CDN, WAF and CI](WordPress-at-Scale-CDN-WAF-and-CI.md). You can read this page without them.

## What you will be able to do

- Say in plain words what LAMP, LEMP, PHP, a plugin, a SAPI, PHP-FPM, a WAF and a static site are, and where each one sits in a request.
- Explain, with dated figures, why a WordPress site's risk is mostly its plugins and themes and not WordPress core.
- Separate three kinds of PHP-related flaw: bugs in the PHP runtime (a C program), bugs in PHP application code, and bugs in plugins.
- Read the October 2026 PHP security release for what it is: two critical flaws in the runtime, far from the first and not the last, and say what a defender does about them.
- Say what "memory safe" means, why C and C++ programs keep producing memory flaws, what Rust guarantees and what it does not.
- Harden a PHP configuration with the real setting names (`expose_php`, `display_errors`, `disable_functions`, `open_basedir`, upload and session settings) and prove the change took effect.
- Harden a WordPress site: accounts and two-factor, `xmlrpc.php`, login rate limiting, file editing off, updates, a least-privilege database user, TLS and security headers.
- Say what a WAF does and does not do, run ModSecurity with the OWASP Core Rule Set in detection-only mode against your own loopback site, read its audit log and tune a false positive.
- Say what a static site gives up and how to get it back, and compare the attack surface of the two in a table.
- Write a short threat model of a WordPress site with assets, trust boundaries, a STRIDE table, mitigations and residual risk.

## Where this project already touches these ideas (and the gaps)

I searched the wiki before writing this page.

| Idea | Where it is used or defined today | The gap this page fills |
|---|---|---|
| Hardening a server | [Droplet hardening](Droplet-Hardening.md) hardens the operating system and firewall of this project's droplets. | Nothing about an application layer: PHP, a CMS, plugins. |
| Patching and CVEs | [Backups, recovery and patching](Backups-Recovery-and-Patching.md) covers cadence and how to read a CVE entry. [Threats in plain words](Threats-in-Plain-Words.md) covers the words. | No worked case of a runtime that is itself the vulnerable part, and no plugin ecosystem. |
| Reverse proxy, WAF | The Glossary defines reverse proxy and CDN. | No explanation of what a WAF inspects, how rules score a request, or what a false positive costs. |
| STRIDE | [Threat frameworks: STRIDE, ATT&CK and ATLAS](Threat-Frameworks-STRIDE-ATTACK-ATLAS.md) applies it to this project's pipeline. | No example on a public website. |
| Zero public inbound ports | [Why ZTNA and not a VPN](Why-ZTNA-Not-a-VPN.md) shows this project exposing nothing. | A public website is the opposite case on purpose; this page is about doing that case carefully. |

## First, the words

- **LAMP and LEMP.** A stack of four pieces: **L**inux (the operating system), **A**pache or **E**nginx (the web server, said "engine-x", which gives the E in LEMP), **M**ySQL or MariaDB (the database) and **P**HP (the language the application is written in). [Lesson 1](LAMP-and-LEMP-From-Zero.md) builds one from zero.
- **PHP.** A programming language that runs on the server. When you ask for a page, the web server hands the request to PHP, PHP runs the site's code, talks to the database, and returns HTML.
- **SAPI.** Server API: the way PHP is connected to a web server. The main ones are **mod_php** (PHP runs inside the Apache process), **PHP-FPM** (FastCGI Process Manager: a separate pool of PHP worker processes that Nginx or Apache sends requests to over a socket) and **php-cgi**. The choice changes what an attacker can reach, as the October 2026 case below shows.
- **CMS and WordPress.** A content management system lets non-developers edit a site. WordPress is the most widely used one and is written in PHP. A **theme** controls the look. A **plugin** adds features; a typical site has many, from many authors.
- **Attack surface.** The sum of everything an outsider can send a request to. Every URL, every script, every login form and every plugin is part of it. Less surface means fewer places to be wrong.
- **WAF.** Web application firewall: software that reads each HTTP request (and sometimes the response) and decides to allow it, log it or block it, using rules. It works at the level of the web request, not at the level of ports like a network firewall ([Subnets, NAT and firewalls by hand](Subnets-NAT-and-Firewalls-By-Hand.md)).
- **Static site.** A site made only of finished files (HTML, CSS, images, JavaScript) that a server hands out as they are. Nothing runs on the server when a visitor arrives.

## Why this stack is a large attack surface

Think of a house. A static site is a house with one door and no rooms behind it: the server hands out files and that is all it does. A WordPress site is a house with a front door, a back office, a garage full of tools that other people installed, a master key kept in a drawer, and a stream of deliveries from strangers (the plugin authors) who each carry a key to something. Most break-ins use a door someone forgot, not the main one.

### What the numbers say (and whose numbers they are)

Patchstack, a company that sells WordPress vulnerability protection, publishes a yearly report. Its "State of WordPress Security in 2026" (page dated 25 February 2026, about 2025) says, read on 2026-10-22:

| Figure from the report | What it says |
|---|---|
| 11,334 new vulnerabilities in the WordPress ecosystem in 2025 | A 42 percent rise on 2024. |
| 91 percent in plugins, 9 percent in themes, 6 in WordPress core | The core was not where the problems were; the add-ons were. |
| 1,966 (17 percent) rated high severity, "likely to be exploited in automated mass-scale attacks" | The vendor's own severity rating, not a standard score. |
| 46 percent had no fix from the developer when they were disclosed | Updating cannot help when there is no update. |
| Median time to mass exploitation for heavily exploited vulnerabilities: 5 hours | A weighted figure for the most-attacked flaws, not for all of them. |
| "Broken Access Control" was the most exploited class | In the report's words these are hard for traditional WAFs to catch "as the exploits look like normal authenticated traffic with no obvious injection patterns". |
| Two 2025 tests: defenses at hosting companies blocked 12 percent, then 26 percent, of the attacks tried | Run by the same vendor, which sells a different approach; read it as a warning, not a measurement of every WAF. |

Take three lessons. First, **the add-ons are the risk**: the safest edit you can make to a WordPress site is to delete a plugin you do not use. Second, **time is short**: when exploitation can begin within hours of publication, a weekly patch day is a gamble, and you want updates to be automatic and your backups tested ([Backups, recovery and patching](Backups-Recovery-and-Patching.md)). Third, **a WAF is one layer, not a cure**, which is the reason it gets its own section below.

I could not read two other yearly sources. Wordfence's pages answered with a bot challenge (HTTP 202) and WPScan's statistics page rendered its figures with JavaScript, so I quote neither.

### Three layers where the bugs live

Keep these separate in your head, because the fix is different for each.

| Layer | What it is | Typical flaw classes (named, not demonstrated) | Who fixes it |
|---|---|---|---|
| **The PHP runtime** | The interpreter itself, written in C, plus its extensions and the way it is connected to the web server | Memory errors (use-after-free, buffer overflow), argument-handling mistakes in the CGI path | The PHP project; you apply the new version |
| **Application code** | WordPress core and any PHP somebody wrote | SQL injection, cross-site scripting (XSS), cross-site request forgery (CSRF), path traversal and file inclusion, unsafe file upload, insecure deserialization, broken access control | The application's authors; you apply updates |
| **Plugins and themes** | Third-party application code, often small and lightly reviewed | The same classes as above; Patchstack's top exploited list for 2025 names unauthenticated stored XSS, authorization bypass, arbitrary file upload, privilege escalation and PHP object injection | The plugin author, if they answer; otherwise you remove the plugin |

The [OWASP Top 10:2025](https://top10.owasp.org/2025/) is a handy map of these: A01 Broken Access Control, A02 Security Misconfiguration, A03 Software Supply Chain Failures, A05 Injection and A07 Authentication Failures each show up on a WordPress site. A plugin is a supply chain item: you run code you did not write and did not read.

## The PHP runtime: versions, support and the October 2026 case

### Which versions are supported

PHP's [supported versions page](https://www.php.net/supported-versions.php) (read 2026-10-22) says each branch gets two years of active support, then two more years of fixes for critical security issues only, then it is end of life. On that date it listed:

| Branch | Initial release | Active support until | Security support until |
|---|---|---|---|
| 8.2 | 8 Dec 2022 | 31 Dec 2024 | 31 Dec 2026 |
| 8.3 | 23 Nov 2023 | 31 Dec 2025 | 31 Dec 2027 |
| 8.4 | 21 Nov 2024 | 31 Dec 2026 | 31 Dec 2028 |
| 8.5 | 20 Nov 2025 | 31 Dec 2027 | 31 Dec 2029 |

Anything older is end of life: no fixes from the PHP project. Two practical points. A shared host or an old distribution may still run an end-of-life branch, and "we have PHP 7.4" or "8.1" is a finding, not a detail. And a Linux distribution may backport fixes to an older version it ships; the PHP project's own notice (below) says exactly that, and tells you to ask your vendor.

### The October 2026 PHP release: two critical flaws

On 2026-10-22 the php.net front page carried a banner, "Security advisory: Critical remote code execution vulnerabilities, update now". It says PHP **8.5.12, 8.4.27, 8.3.36 and 8.2.35** "fix two critical vulnerabilities that can allow unauthenticated remote code execution", that the risk is highest for mod_php, "with a demonstrated exploit where an unauthenticated request can trigger the attack before any application code runs", and that the affected installations include PHP-FPM, Apache with mod_php, php-cgi, FrankenPHP and LiteSpeed. (Remote code execution, RCE, means an outsider makes your server run code of their choosing. Unauthenticated means they did not need to log in first.) The 8.5.12 entry in the [PHP 8 changelog](https://www.php.net/ChangeLog-8.php) is dated 22 October 2026.

The two advisories, both published on GitHub on 21 October 2026 (read 2026-10-22), each rated Critical with a CVSS v4 score of 9.2 (vector: network, attack complexity high, attack requirements present, no privileges, no user interaction, high impact on confidentiality, integrity and availability). Affected: anything older than 8.2.35, 8.3.36, 8.4.27 or 8.5.12.

| Item | [GHSA-w8hw-w9fx-j79w](https://github.com/php/php-src/security/advisories/GHSA-w8hw-w9fx-j79w) | [GHSA-6wmf-4rv5-p3rp](https://github.com/php/php-src/security/advisories/GHSA-6wmf-4rv5-p3rp) |
|---|---|---|
| Title | RCE via OOM corruption | RCE via stale global state |
| CVE | CVE-2026-109618 | CVE-2026-109619 |
| The advisory's own summary, trimmed | PHP "uses longjmp() for out-of-memory (OOM) errors to exit the current context". If an allocation fails while request memory is "reachable before it is fully initialized", PHP "leaves the request memory in an invalid state" and "the request shutdown procedure may then read or branch on it". | Global state "retained by a worker" points to memory owned by one request; some operations "inadvertently access stale state not reset by the previous request ... causing a use after free". |
| Where it bites | Apache mod_php "unconditionally invokes the request shutdown procedure", so it is the highest risk. For PHP-FPM, source analysis "supports FPM as a susceptible" SAPI, "though no complete FPM exploit has been demonstrated". FrankenPHP is "likely susceptible". | Needs a "producer" request and a "consumer" request handled by the same worker. Remote code execution was validated against mod_php and PHP-FPM. |
| What the advisory says fixes it | The patch removes `longjmp()` for OOM. "Updating to a PHP release containing the patch ... is the only complete mitigation." | "Updating to a release containing the complete state reset patch is the only reliable mitigation. There is no complete generic configuration mitigation." |

**This is far from the first PHP runtime flaw of its kind, and it will not be the last.** Three earlier ones, from the National Vulnerability Database records read 2026-10-22 (each is also in CISA's Known Exploited Vulnerabilities catalog; see [Threats in plain words](Threats-in-Plain-Words.md#kev-the-list-of-what-is-being-exploited-now) if KEV is new):

| CVE | NVD published | What the record says | Weakness (CWE) | Added to CISA KEV |
|---|---|---|---|---|
| [CVE-2012-1823](https://nvd.nist.gov/vuln/detail/CVE-2012-1823) | 2012-05-11 | PHP before 5.3.12 and 5.4.x before 5.4.2, configured as CGI, "does not properly handle query strings that lack an = (equals sign)", letting remote attackers run code by "placing command-line options in the query string". | CWE-77 (command injection) | 2022-03-25 |
| [CVE-2019-11043](https://nvd.nist.gov/vuln/detail/CVE-2019-11043) | 2019-10-28 | In "certain configurations of FPM setup" PHP-FPM can "write past allocated buffers", "opening the possibility of remote code execution". | CWE-120 and CWE-787 (buffer overflow, out-of-bounds write) | 2022-03-25 |
| [CVE-2024-4577](https://nvd.nist.gov/vuln/detail/CVE-2024-4577) | 2024-06-09 | With Apache and PHP-CGI on Windows, certain code pages make Windows "Best-Fit" character replacement, so PHP-CGI "may misinterpret those characters as PHP options", which may let an attacker "run arbitrary PHP code on the server". | CWE-78 (OS command injection) | 2024-06-12 |

Those are three I checked, not a count. They show the pattern: the PHP runtime and the glue around it (CGI, FPM, character handling) have produced network-reachable code execution flaws in 2012, 2019, 2024 and now 2026. Notice also that they are not all the same kind: two are argument-handling mistakes in the CGI path, one is a memory error. Which brings up the maintainer's question.

**Are the October 2026 flaws memory-safety flaws?** What I could confirm from the advisory pages: both list CWE-416 (Use After Free) and CWE-824 (Access of Uninitialized Pointer) among their weaknesses, alongside CWE-755 (Improper Handling of Exceptional Conditions), CWE-1325 and CWE-1419. The stale-state advisory says in its summary "causing a use after free". The OOM advisory describes request memory left "in an invalid state" that shutdown then reads. Use after free and use of an uninitialized pointer are two textbook members of the memory-safety family, so yes, on the advisories' own classification, both are memory-safety flaws in the C engine. What I could not confirm: the exact line of C code or the patch (I read the advisories, not the source), and which of the impact paragraphs on each page belongs to which advisory, because each page repeats the other's section under a cross-reference and I did not untangle them. I quote only the summaries, the weakness lists, the mitigations and the CVSS data.

What a defender does, in the advisories' own words and mine:

1. **Update the runtime.** To 8.5.12, 8.4.27, 8.3.36 or 8.2.35, or a vendor build that carries the fix. The PHP notice says "Linux distributions and LTS vendors received the patches in advance, so check your vendor for updated packages", that 8.1 and older no longer get updates from the project, and that the PHP security team provided minimal source backports for 7.4, 8.0 and 8.1. This is the patching cadence from [Backups, recovery and patching](Backups-Recovery-and-Patching.md) in action: a critical, network-reachable, unauthenticated flaw in a component that faces the internet is an emergency change, not a Tuesday item. Check what you run with `php -v` (the Exercise 1 section shows how to tell which build you have).
2. **Know your shape.** mod_php is the highest-risk shape because the exploit runs before any application code. PHP-FPM behind Nginx is not immune. A container running Apache with mod_php is the same shape as a server doing so.
3. **Use the advisories' interim mitigations only as a bridge.** For the OOM flaw: setting `memory_limit=-1` "is the primary configuration mitigation. It removes the predictable per-request limit that enables the confirmed exploit", and "is not a complete mitigation"; keep `post_max_size` conservative and enforce the decoded request size at the frontend; if the application does not use multipart form data, block such requests before they reach PHP. Note the surprise: this is the opposite of the usual advice to cap memory, and the same advisory warns against `RLIMIT_AS` or `RLIMIT_DATA` because they trigger the vulnerable path. For the stale-state flaw on PHP 8.5: `fatal_error_backtraces=0` and `session.upload_progress.enabled=0`, then restart every worker. The advisory says it "might be prudent" to leave session upload progress off if you do not need it, even after patching. These are the project's words about a stopgap; the advisory says the update is the only complete answer.
4. **Do not count on recycling or error-hiding.** The advisory says multiple workers and recycling "reduce success per request but do not remove the condition", and that changing `error_reporting`, using `@`, or turning `display_errors` or `log_errors` off "does not protect against this vulnerability". It does list `pm.max_requests=1` as a measure "if performance is not a factor". The php.ini hardening later on this page is still worth doing, but it is not the fix for this class of flaw.
5. **A WAF is a weak answer here.** The advisory describes frontend size limits and blocking multipart bodies, which a reverse proxy can do. I read no statement from any WAF vendor about these two flaws, so whether a given WAF rule set stops them is **est.**, and the safe assumption is that a WAF may not stop a corner case in how PHP parses a request body. Patch first.
6. **Watch for the aftermath.** If you ran a vulnerable version on a public site, treat the patch as the start: review logs for unexplained errors and for new files, and see [Logs, SIEM and detection basics](Logs-SIEM-and-Detection-Basics.md). The advisory lists what to look for in logs (repeated core errors before target scripts run, fatal errors, "Maximum execution time exceeded") and warns that "absence of an error in logs is not proof of safety".

## Side discussion: memory safety, and why Rust keeps getting adopted

*This section is a side road. Skip it and nothing later breaks. It explains the idea behind the word "memory-safety" that kept appearing above.*

**What "memory unsafe" means.** A program keeps its data in memory, in numbered slots. Languages like C and C++ let the developer reach any slot by number (a **pointer**) and leave it to the developer to keep track of which slots are still theirs. The classic ways to get that wrong:

- **Buffer overflow (out-of-bounds write or read).** Writing or reading past the end of a block you were given, into a neighbor's data.
- **Use after free.** Giving a block back, then using it anyway. By then the memory may belong to something else.
- **Double free.** Giving the same block back twice, which can corrupt the bookkeeping that hands out memory.
- **Type confusion.** Treating a block as one kind of thing when it holds another.
- **Use of uninitialized memory.** Reading a block before anything was put in it, so you read whatever was left there.

The danger is that an attacker who can steer these mistakes can make the program read secrets or run their code. The mistakes are easy to make in C: the language has no built-in check, the code base is huge, and a very careful developer still ends up with one wrong line in millions.

**Why C and C++ runtimes keep producing them.** PHP's engine, the Linux kernel, browsers and most database servers are written in C or C++ because those languages are fast and give control over memory. That control is the same property that makes these bugs possible. A fix can remove one bug but the next change may add another, which is why the same project shows up in the news for the same class of flaw year after year.

**What "memory safe language" means.** A language where the compiler, the runtime, or both stop you from doing the things in the list above in ordinary code. Python, Java, Go, JavaScript and Rust are examples; so is PHP itself when you write PHP. In a safe language, going past the end of a list raises an error instead of reading the neighbor's data.

**What the guidance and the data say.** Here is what I read, with dates:

| Source | What it says |
|---|---|
| CISA, ["The Case for Memory Safe Roadmaps"](https://www.cisa.gov/resources-tools/resources/case-memory-safe-roadmaps) (page dated 6 Dec 2023) | Guidance for software makers on moving to memory safe languages and publishing a roadmap. I read the page summary, not the PDF. |
| CISA and NSA, ["Memory Safe Languages: Reducing Vulnerabilities in Modern Software Development"](https://www.cisa.gov/resources-tools/resources/memory-safe-languages-reducing-vulnerabilities-modern-software-development) (page dated 24 Jun 2025) | A joint guide on the obstacles to adopting memory safe languages and practical ways past them. I read the page summary, not the PDF. |
| Chromium project, ["Memory safety"](https://www.chromium.org/Home/chromium-security/memory-safety/) | "Around 70% of our high severity security bugs are memory unsafety problems". Half of those are use-after-free bugs. Based on 912 high or critical bugs since 2015. |
| Google Security Blog, ["Memory Safe Languages in Android 13"](https://security.googleblog.com/2022/12/memory-safe-languages-in-android-13.html) (Dec 2022) | Memory-safety flaws "have consistently represented more than 65% of vulnerabilities" across products for over a decade; in Android they fell from 76 percent (2019) to 35 percent (2022); in 2022 they were 36 percent of the bulletin but 86 percent of critical-severity flaws; about 21 percent of new native code in Android 13 was Rust. |
| Google Security Blog, ["Eliminating Memory Safety Vulnerabilities at the Source"](https://security.googleblog.com/2024/09/eliminating-memory-safety-vulnerabilities-Android.html) (Sep 2024) | 76 percent of Android vulnerabilities in 2019, 24 percent in 2024, "well below the 70% industry norm". |
| [Rust for Linux](https://rust-for-linux.com/) | The project adding Rust support to the Linux kernel; its page lists drivers already in mainline. |

I also tried to read Microsoft's Security Response Center statement about memory safety share and the White House ONCD report; the pages I could reach did not show it, so I cite neither figure. Treat the "about 70 percent" number as established for Chromium (their analysis) and for Android before its shift, and as a rough industry figure, not a law.

**What Rust guarantees, and what it does not.** The Rust book says that code outside `unsafe` blocks has Rust's memory safety guarantees, and "any errors related to memory safety must be within an unsafe block". Rust checks ownership at compile time instead of at run time, so the use-after-free in the demo below is refused when you build. What Rust does **not** do:

- **It does not make `unsafe` blocks safe.** The book says `unsafe` does not turn off the borrow checker, but inside it the compiler trusts you again. Systems code (kernels, drivers) needs some.
- **It does not remove logic bugs.** A program can be memory safe and still check the wrong password, forget an access check or leak data in an error message. Most WordPress plugin flaws above are of this kind, in a memory safe language already (PHP).
- **It does not fix the supply chain.** A Rust program still pulls in other people's libraries.
- **It does not rewrite itself.** Moving a large project from C is slow. Whether a given project, PHP included, will move is not something I read an answer to; do not infer one.

**A safe PHP point.** Userland PHP code (the PHP you or a plugin write) does not use pointers and cannot make these mistakes directly. The October 2026 flaws live in the C engine underneath. So the memory flaw class sits below your application, and no amount of careful PHP removes it. (In the same way, Python code is memory safe, while the interpreter under it is a C program: a general fact, not something I looked up.)

**A small demo you can run (Bash, harmless).** The same mistake in three languages. The C program is a standard textbook bug that only reads memory it no longer owns; nothing here is an exploit. You need `gcc` (with AddressSanitizer), `rustc` and `python3`; install what you lack or read my output.

```bash
mkdir -p ~/w2-lab/mem && cd ~/w2-lab/mem
cat > uaf.c <<'EOF'
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void) {
    char *note = malloc(16);
    if (!note) return 1;
    strcpy(note, "hello");
    free(note);              /* the memory is given back ...             */
    printf("%s\n", note);    /* ... and then used anyway: use-after-free */
    return 0;
}
EOF
cat > uaf.rs <<'EOF'
fn main() {
    let note = String::from("hello");
    drop(note);               // the memory is given back ...
    println!("{}", note);     // ... and then used anyway: refused at compile time
}
EOF
printf 'letters = ["a", "b", "c"]\nprint(letters[5])\n' > oob.py

gcc -o uaf_plain uaf.c && ./uaf_plain; echo "exit=$?"      # plain C
gcc -fsanitize=address -g -o uaf uaf.c && ./uaf 2>&1 | head -4   # C with a checker
rustc uaf.rs 2>&1 | head -4                                      # Rust
python3 -I oob.py 2>&1 | tail -1                                 # Python
```

What I got on 2026-10-22: plain C printed garbage bytes (it can print `hello`; the result is undefined) and exited 0, so **nothing told me anything was wrong**. With AddressSanitizer (a debugging tool, not something you ship) it stopped with `ERROR: AddressSanitizer: heap-use-after-free` and exit 1. `rustc` refused to build: `error[E0382]: borrow of moved value: note`. Python raised `IndexError: list index out of range`. Same idea, four outcomes: silent, caught by a tool you must remember to run, refused at build, refused at run. PowerShell users can run the same files in WSL; there is no PowerShell version (est.). Delete `~/w2-lab/mem` when you are done.

## Hardening PHP

### php.ini: the settings that matter, with the real names

`php.ini` is PHP's main configuration file. The PHP manual lists every setting and where it may be changed (the "changeable" column: `php.ini only`, `INI_SYSTEM`, `INI_PERDIR` or `INI_ALL`). These are the ones to know; defaults are from the [manual's ini list](https://www.php.net/manual/en/ini.list.php), read 2026-10-22.

| Setting | Built-in default | What it does | Hardened value and why |
|---|---|---|---|
| `expose_php` | `1` | Adds PHP's version to an `X-Powered-By` response header. | `Off`. Hiding a version does not fix anything, but it stops advertising which known flaws to try. |
| `display_errors` | `1` | Prints errors into the page. The manual says it "should never be used on production systems". | `Off`. Error text shows file paths and sometimes queries. |
| `log_errors` | `0` | Sends errors to the log instead. The manual: "strongly advised to use error logging in place of error displaying". | `On`, with `error_log` set to a file or `syslog`. |
| `disable_functions` | empty | Removes named built-in functions. `php.ini` only. The manual warns it "can be circumvented and should not be considered a sufficient security measure for shared hosting environments". | A list such as `exec,passthru,shell_exec,system,proc_open,popen,pcntl_exec`. Defense in depth: it makes a successful code-injection less useful. Some plugins (backup, image tools) need some of them, so test. |
| `open_basedir` | none | Limits which directory tree PHP may read and write. Symlinks are resolved. | The site root plus the temp directory. A script that is tricked into reading `/etc/passwd` is refused. |
| `allow_url_include` | `0` | Lets `include` and `require` fetch URLs. Needs `allow_url_fopen`. | Keep `Off`. (Deprecated since 7.4.) |
| `allow_url_fopen` | `1` | Lets file functions open URLs. | Consider `Off` if nothing needs it; WordPress uses its own HTTP code, but some plugins do not. Test. |
| `file_uploads` | `1` | Turns HTTP file upload on. | `Off` on a site that never accepts uploads. |
| `upload_max_filesize`, `post_max_size`, `max_file_uploads` | `2M`, `8M`, `20` | Caps on one file, a whole request body, and files per request. | As small as the site needs. The manual says a large `post_max_size` or `upload_max_filesize` "for a complete server" may raise risk because PHP must parse oversize bodies; set bigger limits only for the one path that needs them. `post_max_size` must be larger than `upload_max_filesize`. |
| `session.use_strict_mode` | `0` | Rejects session IDs the server did not issue. The manual: "mandatory for general session security". | `1`. |
| `session.use_only_cookies` | `1` | Session IDs only in cookies, not in the URL. | Keep `1`. |
| `session.cookie_httponly` | `0` | JavaScript cannot read the session cookie. | `1`. Reduces what a cross-site scripting flaw can steal. |
| `session.cookie_secure` | `0` | Cookie only sent over HTTPS. | `1` once the site is HTTPS only. |
| `session.cookie_samesite` | empty | Tells browsers not to send the cookie on cross-site requests. | `Lax` (or `Strict`). |

Two notes. WordPress does not use PHP sessions for its own logins (it sets its own cookies), so the `session.*` lines matter for plugins and other PHP apps; I include them because other PHP apps will be on your server one day. And remember what the October 2026 advisory said: hiding errors does not protect against that flaw. These settings reduce what a flaw can do and what a visitor learns; they do not replace patching.

### PHP-FPM pools, users and file permissions

With PHP-FPM (the manual's [FPM configuration page](https://www.php.net/manual/en/install.fpm.configuration.php), read 2026-10-22), each **pool** is a group of workers with its own settings, started as a Unix `user` and `group`. The use of this is isolation:

- **One pool, one user, per site.** If two sites share a pool and one is compromised, the attacker is the same Unix user on the other. Separate pools running as separate users mean one broken site does not read the other's files.
- **The web server is not the PHP user.** Files that PHP only reads (core, plugins, themes) should be owned by a different account from the one PHP runs as, so a compromised PHP worker cannot rewrite its own code. WordPress's [hardening guide](https://developer.wordpress.org/advanced-administration/security/hardening/) says the same: everything writable only by your user account, except `wp-content` (uploads and similar) which must also be writable by the web server process; directories 755, files 644; `wp-config.php` readable by you and the server only, 400 or 440.
- **Do not expose the FastCGI socket.** The manual warns "An exposed FastCGI endpoint allows arbitrary code execution." Use a Unix socket when the web server is on the same host, restrict who may connect with `listen.owner`, `listen.group` and `listen.mode`, and for a TCP socket set `listen.allowed_clients` (unset it accepts any address). In containers do not publish the FPM port on the host. The WordPress image documentation warns the same about its `fpm` variant.
- **Per-pool PHP settings** go in the pool file with `php_admin_value[...]` and `php_admin_flag[...]`: the manual says these cannot be overridden by the application with `ini_set()`. It also says `security.limit_extensions` limits which files FPM will run (default `.php .phar`), and `clear_env` (default yes) keeps arbitrary environment variables away from workers.
- **Never let the web server pass `PHP_VALUE` from untrusted places.** The manual warns that settings sent as FastCGI parameters mean "php-fpm should not be bound to a worldwide accessible address". The October 2026 stale-state advisory also advises preferring startup configuration (php.ini, FPM pool, server configuration) over per-request overrides.

## Hardening WordPress

All of these are from the WordPress [hardening guide](https://developer.wordpress.org/advanced-administration/security/hardening/) and [brute-force guide](https://developer.wordpress.org/advanced-administration/security/brute-force/) (both read 2026-10-22) unless noted.

| Area | What to do | Notes |
|---|---|---|
| **Accounts** | Few administrators; a unique strong password for each; no account literally named `admin`. | The guide: "A hacker who gains access to your administrator account is able to install malicious scripts that can potentially compromise your entire server." |
| **Two-factor** | Turn on two-factor authentication for every administrator. | The brute-force guide says WordPress core does not include 2FA; use a plugin or your identity provider. It also describes passkeys and says to enroll at least two authenticators per admin. See [Enterprise identity](Enterprise-Identity-SSO-SAML-OIDC.md) for why phishing-resistant factors matter. |
| **`xmlrpc.php`** | If you do not use it, disable it. If you do (Jetpack, some mobile apps), restrict and rate-limit it. | The guide calls it "a frequent brute-force target (especially the `system.multicall` method)". |
| **`wp-login.php`** | Rate-limit at the edge or web server rather than only in a plugin. | The guide notes plugin-based limiting still runs inside PHP and uses resources under heavy attack; it shows an Nginx `limit_req` example. |
| **File editing** | In `wp-config.php`: `define( 'DISALLOW_FILE_EDIT', true );` | The guide: the dashboard's plugin and theme editor is "often the first tool an attacker will use if able to login, since it allows code execution". It will not stop uploads of malicious files. |
| **Install and update from the dashboard** | `define( 'DISALLOW_FILE_MODS', true );` blocks installs and updates (and the file editor) from the admin area. | A trade-off: it also blocks the update button, so use it only when updates arrive another way (deploy pipeline, [lesson 4](WordPress-at-Scale-CDN-WAF-and-CI.md)). |
| **Updates** | Keep core, plugins and themes current. Automatic updates exist since WordPress 3.7; `WP_AUTO_UPDATE_CORE` accepts `false`, `true` or `'minor'` (minor releases, the default). | The `wp-config` reference documents the constants. Plugin and theme auto-update is a setting in the dashboard. A plugin you do not use is attack surface: delete it. |
| **Trusted sources** | Plugins and themes only from the WordPress.org repository or well-known companies. | The guide's words. The Patchstack figures above are the reason. |
| **Database user** | Give WordPress its own database and its own user. | See the next section. |
| **Secrets** | Keep `wp-config.php` readable only by you and the web server; consider moving it one directory above the web root. | The guide says opinions differ on the benefit. Generate the keys and salts at install time; never paste real ones into a repository. |
| **Backups** | Back up files and database on a schedule, keep copies away from the server, and test a restore. | The guide: a backup can be tampered with, so consider read-only media. Full detail in [Backups, recovery and patching](Backups-Recovery-and-Patching.md). |
| **Logs and monitoring** | Keep web server, PHP and database logs; watch for changed files. | The guide suggests file integrity monitoring and a host-based tool such as OSSEC. This project's equivalent is in [Detection and monitoring](Detection-and-Monitoring-Wazuh-and-the-Landscape.md). |

### Database least privilege

The hardening guide says that for normal operations (posting, uploading media, comments, new users, installing plugins) the database user "only needs data read and data write privileges: SELECT, INSERT, UPDATE and DELETE", so other privileges such as DROP, ALTER and GRANT can be revoked. It then gives a warning worth keeping: some plugins and major updates change the database structure, attempts without those privileges "can cause problems", and revoking is "NOT recommended" unless you have a solid backup plan. So the honest version: the database account must never be the database's root account, must be limited to one database, and must be unreachable from the internet (not published on a public port). Whether to also strip structure-changing rights is a trade-off you decide with a tested backup in hand. The same idea runs through [Identity, secrets and zero trust basics](Identity-Secrets-and-Zero-Trust-Basics.md).

### TLS and security headers

**TLS** encrypts the connection and proves the site's name; [How a web request works](How-a-Web-Request-Works.md) explains certificates. For WordPress: serve everything over HTTPS, redirect HTTP to HTTPS, and set `define( 'FORCE_SSL_ADMIN', true );` so logins and the admin area are never sent in the clear (the `wp-config` reference). [Lesson 3](DNS-Cloudflare-and-Hosting-Your-Own-Website.md) covers certificates and DNS.

**Security headers** are instructions your server sends to the browser. MDN documents each (read 2026-10-22):

| Header | What it tells the browser |
|---|---|
| `Strict-Transport-Security` (HSTS) | Only use HTTPS for this host for `max-age` seconds; optional `includeSubDomains` and `preload`. Also blocks click-through on certificate errors. Get HTTPS working first, then raise the time slowly. |
| `Content-Security-Policy` | Which sources may load scripts, styles and images. "Helps guard against cross-site scripting attacks." Start in report-only mode; WordPress themes and plugins often inline code and break a strict policy. |
| `X-Content-Type-Options: nosniff` | Respect the declared type; do not guess. |
| `Referrer-Policy` | How much of the previous page's address is sent along. |
| `X-Frame-Options` | Whether other sites may put yours in a frame (clickjacking). MDN notes the `frame-ancestors` directive of a Content Security Policy gives more control. |
| `Permissions-Policy` | Which browser features (camera, location) the page may use. |

None of these fixes a bug in the server. They shrink what a bug in the page can do to a visitor.

## WAFs: what they do, what they cannot

A **WAF** sits in front of the site (as a reverse proxy, a module in the web server, or a plugin) and judges each request against rules. Three jobs: **block** known-bad patterns, **log** suspicious ones so you can see them, and **rate-limit** floods. Its strength is cheap, fast, general protection: it can drop obvious junk before PHP runs and give you visibility into what is hitting the site. Its limits are as important:

- **It sees patterns, not intent.** A request that is a normal-looking authenticated action but abuses a plugin's missing permission check carries no attack pattern. Patchstack's report says as much for broken access control.
- **Signatures lag and can be dodged.** A new flaw has no rule on day one, and an attacker can re-encode a request in ways a rule does not expect. (Concept only; this page gives no technique.)
- **It can block the legitimate.** A **false positive** is a harmless request flagged as an attack. Too many and the team turns the WAF off.
- **It can be the only layer and fail alone.** A WAF in front of an unpatched plugin is a delay, not a repair. It is a layer in the stack, not a replacement for [patching](Backups-Recovery-and-Patching.md).
- **It adds a place to be wrong.** Another system to patch, configure and watch.

### ModSecurity and the OWASP Core Rule Set (the self-run example)

**ModSecurity** is an open source WAF engine for Apache, Nginx and IIS. The **OWASP Core Rule Set (CRS)** is a free set of generic attack-detection rules for it; the OWASP page says it aims to protect "from a wide range of attacks, including the OWASP Top Ten, with a minimum of false alerts". The CRS install page (read 2026-10-22) named v4.25.0 as the latest release and offers official containers (`owasp/modsecurity-crs`, Apache and Nginx editions) that act as a **reverse proxy** in front of your site.

How CRS decides, from its [anomaly scoring page](https://coreruleset.org/docs/2-how-crs-works/2-1-anomaly_scoring/): each matching rule adds to a running **anomaly score** and no single rule blocks by itself; when request rules have run, a request at or above the inbound threshold (5 by default) is denied; response rules then do the same with an outbound threshold (4 by default). The page warns that raising the threshold above the defaults "will allow a substantial number of attacks to bypass CRS" and should be "only ever" a temporary step during tuning. **Paranoia levels** 1 to 4 control how many rules are on: level 1 is "baseline security with a minimal need to tune away false positives"; higher levels bring "lots of false positives" ([paranoia levels page](https://coreruleset.org/docs/2-how-crs-works/2-2-paranoia_levels/)). The two ideas are separate: paranoia changes which rules exist, the threshold changes how many must fire.

**Detection-only mode first.** The engine setting `SecRuleEngine` has three values: `On`, `Off` and `DetectionOnly`. With the container, the environment variable is `MODSEC_RULE_ENGINE` and it accepts `On`, `Off`, `DetectionOnly`. In `DetectionOnly` the rules run and log but nothing is blocked. That is how you start on a real site: watch what it would have blocked, fix the false positives, then switch to blocking. CRS's own install page uses `DetectionOnly` in its container example, and says that new detections bring "a certain risk of false alarms" so you should "test first before going live".

**Tuning a false positive.** From the [false positives and tuning page](https://coreruleset.org/docs/2-how-crs-works/2-3-false-positives-and-tuning/): a false positive is a genuine transaction that triggers a rule, and you fix it with a **rule exclusion**. It can be as coarse as removing a rule (`SecRuleRemoveById`) or as precise as removing one request parameter from one rule's inspection (`SecRuleUpdateTargetById`, with an example for a WordPress post field). Prefer the precise form. Placement matters: an exclusion that removes a rule must come after the CRS rules are loaded; one that modifies a rule must come before. The CRS ships two example files for that (`REQUEST-900-EXCLUSION-RULES-BEFORE-CRS.conf.example` and `RESPONSE-999-EXCLUSION-RULES-AFTER-CRS.conf.example`). The CRS 4 install page notes that application-specific exclusion packages were replaced by a plugin system; check the CRS plugin registry for a WordPress one rather than relying on a package I did not install.

### Cloudflare's WAF (the managed example)

A managed WAF runs at the provider's edge and sits in front of your site as a reverse proxy: your DNS points at them and they forward the traffic ([lesson 3](DNS-Cloudflare-and-Hosting-Your-Own-Website.md) shows the DNS side, and [lesson 4](WordPress-at-Scale-CDN-WAF-and-CI.md) the production side). I have no affiliation with Cloudflare; it is the example because it is the one many beginners meet. From Cloudflare's documentation, read 2026-10-22, for the **Free** plan:

| Feature | Free plan, as the docs state | Source page |
|---|---|---|
| Managed rules | The **Free Managed Ruleset** is available on all plans: "protection against high-impact and widely exploited vulnerabilities". The full Cloudflare Managed Ruleset and the Cloudflare OWASP Core Ruleset are shown as not available on Free (available from Pro up). | [Managed rules](https://developers.cloudflare.com/waf/managed-rules/) |
| Custom rules | 5 rules per zone; all actions except Log; no regular expressions (regex support starts on Business). | [Custom rules](https://developers.cloudflare.com/waf/custom-rules/) |
| Rate limiting rules | 1 rule; the rule can use only the path and verified-bot fields; it counts by IP; counting period 10 seconds; mitigation timeout 10 seconds. | [Rate limiting rules](https://developers.cloudflare.com/waf/rate-limiting-rules/) |
| Request body inspected | Managed rules inspect up to a maximum body size, 1 MB on Free; larger content "may not be fully analyzed". | Managed rules page |

Read together with what you learned above: on the free tier you get a baseline ruleset, five hand-written rules and one small rate limit. That is a real improvement for a hobby site and no replacement for patching. Plans, prices and limits change; check the page before you rely on a number. The CRS project has a view on how some vendors set CRS thresholds; I do not repeat it because I did not test a Cloudflare site.

## Why static sites win so often

A **static site** is built once (on your computer or in a pipeline) from content files, and the output is plain files that any file server can hand out. Compare what an attacker meets:

| Question | WordPress on LAMP/LEMP | Static files |
|---|---|---|
| Code that runs when a visitor arrives | PHP, WordPress core, every plugin and theme | None; the server reads a file and sends it |
| Database | Yes, holding users and content | None at runtime |
| Login page on the internet | `wp-login.php` and `xmlrpc.php` | None |
| Things to patch weekly | PHP, web server, database, WordPress, each plugin, each theme | The web server or the hosting service |
| Uploads from visitors | Possible | None |
| What a break-in gets | A server running your code, your database | Usually nothing the visitor could not already download |
| Where the risk moved | n/a | To the build chain: the generator, its themes and packages, and whoever can push to the repository (a supply chain, not a server) |

The last row is the honest part. A static site does not remove risk, it moves it: from a public server running code on every visit to a build you control and a repository access list. That is easier to defend, because you decide when new code runs and can review it. Fewer moving parts also means fewer things to be wrong at 3 a.m.

**What you give up.** Anything that needs the server to compute something at the time of the request:

| Feature | How you get it back |
|---|---|
| Contact and signup forms | Send the form to a separate form-handling service, or a small function you run elsewhere. That service has its own security and terms; read them. |
| Comments | A hosted comments service, or a discussion system on a platform you choose, loaded on the page. |
| Search | Build a search index at build time and search it in the visitor's browser. |
| Preview of unpublished work | Run the site generator locally, or use the host's preview deployments. |
| Many editors who do not use Git | A headless CMS or an editor UI that commits to the repository. |
| Accounts, shopping carts, personalization | Not a good fit; use a service built for it. |

Each of those add-ons is a separate service with its own account, its own cost and its own risks. The point is that the risk is *separate and small*, not folded into one server that runs everything.

**Free hosting options, with the terms I read (2026-10-22):**

- **GitHub Pages** ([limits page](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits)): "not intended for or allowed to be used as a free web-hosting service to run your online business, e-commerce site, or any other website that is primarily directed at either facilitating commercial transactions or providing commercial software as a service (SaaS)"; sites should not be used for sensitive transactions such as sending passwords or credit card numbers. Limits: published site no more than 1 GB; a soft bandwidth limit of 100 GB per month; a soft limit of 10 builds per hour, which "does not apply if you build and publish your site with a custom GitHub Actions workflow"; deployments time out after 10 minutes.
- **Cloudflare Pages** ([limits page](https://developers.cloudflare.com/pages/platform/limits/)): the Free plan allows up to 20,000 files per site, a maximum single file of 25 MiB, 500 builds per month, 1 build at a time, a build timeout of 20 minutes, 100 custom domains per project and 100 projects per account.

Both change their terms from time to time. Read the current page before building anything you depend on, and keep the source in a Git repository so that moving hosts is a re-deploy.

For a personal site, a documentation site, a portfolio or a blog, a static site is very often enough. It is the wrong choice when the heart of the site is accounts, payments or user-generated content, and then you want a managed platform or a framework with a security team, not a hand-patched plugin collection.

## A threat model of a WordPress site

This is the exercise from [Threat model: exercise](Threat-Model-Exercise.md) applied to a public WordPress site on one server. Use the same method on your own site.

**Assets (what is worth protecting).** The administrator session and password. The database (user records, content, comments). The secrets in `wp-config.php` (database login, authentication keys and salts). The uploads folder. The site's integrity and reputation (defacement, spam links, redirects). The server itself, as a foothold for something worse. The visitors, who may be sent malware from a hacked page.

**Trust boundaries (where the rules change).**

1. Internet to the edge (CDN or WAF), and edge to the web server.
2. Web server to PHP (a FastCGI socket or, with mod_php, inside one process).
3. PHP to the database.
4. The administrator's browser to `wp-admin`.
5. Each plugin or theme author to your server, through the update channel. This is a boundary people forget: you let a stranger's code run with your site's powers.
6. The server to its backups.

**STRIDE** ([Threat frameworks](Threat-Frameworks-STRIDE-ATTACK-ATLAS.md) explains the letters), with mitigation and residual risk:

| Threat (STRIDE letter) | Example for this site | Mitigation | Residual risk |
|---|---|---|---|
| **S**poofing | Someone logs in as an administrator with a guessed, reused or phished password, or steals a session cookie. | Two-factor or passkeys for admins; rate-limit `wp-login.php` and `xmlrpc.php`; `session.cookie_httponly`, HTTPS only; few admins. | A phished one-time code or a stolen device is still a way in. |
| **T**ampering | An attacker with admin access edits a plugin file, or a flawed plugin lets an upload land in the web root. | `DISALLOW_FILE_EDIT`; plugin files not writable by the PHP user; do not run PHP from the uploads folder; file integrity monitoring. | A plugin flaw that writes where it should not can still win once; monitoring finds it after the fact. |
| **R**epudiation | Nobody can say who changed what or when. | Keep web, PHP and database logs; ship them off the server ([Logs, SIEM and detection basics](Logs-SIEM-and-Detection-Basics.md)); an activity log plugin. | Logs on the compromised server are only as trustworthy as the server. |
| **I**nformation disclosure | Error pages show file paths; a database dump or backup file sits in the web root; SQL injection reads the user table. | `display_errors` Off; backups outside the web root; database user limited to one database; `open_basedir`. | A SQL injection in a plugin reads what the database user can read. |
| **D**enial of service | A flood of login attempts or oversized multipart bodies; a heavy plugin query. | Edge rate limits; `post_max_size` and related caps; page caching; a CDN. | A large enough flood beats a small server; the CDN absorbs most but not all. |
| **E**levation of privilege | A broken access check turns a subscriber into an administrator; a PHP runtime flaw gives code execution as the web user; a compromised pool user reads other sites. | Few plugins, updated fast; one pool and user per site; least-privilege database user; patch the PHP runtime the day a critical fix ships. | The window between a flaw's publication and your patch; zero-days. |

**Residual risk, in words.** After all of this you still depend on strangers' code (plugins), on the PHP project's patch cadence, and on your own speed to apply updates. A static site changes which of these remain: no runtime to patch weekly, no database, no login page. The choice is not "secure or insecure" but "which risks do I carry, and can I afford them".

## Hands-on, free path: your own computer only

Every exercise follows four steps: **predict**, **do**, **check**, **undo**. Everything binds to `127.0.0.1`, which only your own machine can reach. Use a port number of your choice if one below is taken (`ss -ltn` in Bash shows the ones in use). The lab directory is `~/w2-lab` (Bash) or `$HOME\w2-lab` (PowerShell). Do not point anything on this page at a computer you do not own.

> **Screenshot to take yourself:** your terminal after Exercise 1.
> Capture: the side-by-side listing of the PHP settings before and after.
> Look for: `expose_php`, `display_errors` and `disable_functions` changed.
> Redact: your username and home directory path.

### Exercise 1: harden PHP's configuration and compare before and after

**Predict.** With `php -n` (no configuration file) PHP uses its built-in defaults. Which of the settings in the table above do you expect to differ once a hardening file is loaded? Which will stay the same?

**Do (Bash).** This writes a small PHP script that prints the settings, and a hardening file with your lab path filled in at run time.

```bash
set -eu
LAB="$HOME/w2-lab"; mkdir -p "$LAB/site" "$LAB/tmp"; LAB="$(cd "$LAB" && pwd -P)"
cat > "$LAB/show-ini.php" <<'EOF'
<?php
$keys = ['expose_php', 'display_errors', 'log_errors', 'allow_url_fopen', 'allow_url_include',
         'disable_functions', 'open_basedir', 'file_uploads', 'upload_max_filesize', 'post_max_size',
         'max_file_uploads', 'session.use_strict_mode', 'session.use_only_cookies',
         'session.cookie_httponly', 'session.cookie_secure', 'session.cookie_samesite'];
foreach ($keys as $k) {
    $v = ini_get($k);
    printf("%-26s %s\n", $k, ($v === '' || $v === false) ? '(empty)' : $v);
}
EOF
cat > "$LAB/hardening.ini" <<EOF
; Lab file for lesson W2 (Apache-2.0). Each name is in the PHP manual's ini list.
expose_php = Off
display_errors = Off
display_startup_errors = Off
log_errors = On
allow_url_include = Off
disable_functions = exec,passthru,shell_exec,system,proc_open,popen,pcntl_exec
open_basedir = $LAB/site:$LAB/tmp
upload_max_filesize = 8M
post_max_size = 10M
max_file_uploads = 5
session.use_strict_mode = 1
session.use_only_cookies = 1
session.cookie_httponly = 1
session.cookie_secure = 1
session.cookie_samesite = Lax
EOF
php -n "$LAB/show-ini.php" > "$LAB/before.txt"
php -n -c "$LAB/hardening.ini" "$LAB/show-ini.php" > "$LAB/after.txt"
diff -y "$LAB/before.txt" "$LAB/after.txt" || true
php --ini | head -n 3
```

**Do (PowerShell 7, est.: not run).**

```powershell
$lab = Join-Path $HOME 'w2-lab'
New-Item -ItemType Directory -Force -Path (Join-Path $lab 'site'), (Join-Path $lab 'tmp') | Out-Null
$lab = (Resolve-Path $lab).Path
@'
<?php
$keys = ['expose_php', 'display_errors', 'log_errors', 'allow_url_fopen', 'allow_url_include',
         'disable_functions', 'open_basedir', 'file_uploads', 'upload_max_filesize', 'post_max_size',
         'max_file_uploads', 'session.use_strict_mode', 'session.use_only_cookies',
         'session.cookie_httponly', 'session.cookie_secure', 'session.cookie_samesite'];
foreach ($keys as $k) {
    $v = ini_get($k);
    printf("%-26s %s\n", $k, ($v === '' || $v === false) ? '(empty)' : $v);
}
'@ | Set-Content (Join-Path $lab 'show-ini.php')
@"
expose_php = Off
display_errors = Off
display_startup_errors = Off
log_errors = On
allow_url_include = Off
disable_functions = exec,passthru,shell_exec,system,proc_open,popen,pcntl_exec
open_basedir = $lab\site;$lab\tmp
upload_max_filesize = 8M
post_max_size = 10M
max_file_uploads = 5
session.use_strict_mode = 1
session.use_only_cookies = 1
session.cookie_httponly = 1
session.cookie_secure = 1
session.cookie_samesite = Lax
"@ | Set-Content (Join-Path $lab 'hardening.ini')
$before = php -n (Join-Path $lab 'show-ini.php')
$after  = php -n -c (Join-Path $lab 'hardening.ini') (Join-Path $lab 'show-ini.php')
Compare-Object $before $after
```

(On Windows `open_basedir` separates directories with a semicolon, as the manual says; on other systems a colon.)

**Check.** I got this on 2026-10-22 (PHP 8.4.26, Linux), shown trimmed with `diff -y` and the long lines cut. `(empty)` means the setting is off or unset.

```text
expose_php                 1              |  expose_php                 (empty)
display_errors             1              |  display_errors             (empty)
log_errors                 0              |  log_errors                 1
allow_url_include          0              |  allow_url_include          (empty)
disable_functions          (empty)        |  disable_functions          exec,passthru,shell_exec,system,pr...
open_basedir               (empty)        |  open_basedir               <your lab path>/site:<your lab path>/tmp
upload_max_filesize        2M             |  upload_max_filesize        8M
post_max_size              8M             |  post_max_size              10M
max_file_uploads           20             |  max_file_uploads           5
session.use_strict_mode    0              |  session.use_strict_mode    1
session.cookie_httponly    0              |  session.cookie_httponly    1
session.cookie_secure      0              |  session.cookie_secure      1
session.cookie_samesite    (empty)        |  session.cookie_samesite    Lax
```

`allow_url_fopen`, `file_uploads` and `session.use_only_cookies` were unchanged (all `1`), because their defaults were already what the table recommends or the site needs. `php --ini` shows which configuration file PHP loaded: on my machine the first run named a system `php.ini` and `php -n --ini` showed `(none)`, which is the point of `-n`. Two warnings. The upload limits went **up** here because this is a teaching file; set them to what your site needs. And the version in the first line of `php -v` matters: compare it against the table of fixed versions earlier on this page. When I ran this my machine's PHP was 8.4.26, one patch release below the fixed 8.4.27: an affected build, which is a good reason to run `php -v` on yours and update (I did not update it as part of writing this page).

**Undo.** `rm -rf ~/w2-lab` (Bash) or `Remove-Item -Recurse -Force $HOME\w2-lab` (PowerShell) when you finish all the exercises; nothing outside that folder was changed.

### Exercise 2: see the difference from a browser's point of view

**Predict.** Serve a tiny PHP page with the built-in development server twice: once with defaults, once with the hardening file. Which response headers and page text change? The manual says this server "should not be used on a public network", so it is bound to loopback only.

**Do (Bash).** Run Exercise 1 first.

```bash
set -eu
LAB="$(cd "$HOME/w2-lab" && pwd -P)"
cat > "$LAB/site/index.php" <<'EOF'
<?php
header('Content-Type: text/plain');
echo "system() exists:      ", var_export(function_exists('system'), true), "\n";
echo "can read /etc/passwd: ", var_export(is_readable('/etc/passwd'), true), "\n";
if (isset($_GET['oops'])) { echo $not_defined['x']; }
EOF
probe () {   # $1 = label, rest = extra php arguments
  label="$1"; shift
  php "$@" -S 127.0.0.1:18081 -t "$LAB/site" > "$LAB/$label.server.log" 2>&1 &
  pid=$!
  echo "=== $label"
  curl -s --retry 5 --retry-connrefused --retry-delay 1 -D - http://127.0.0.1:18081/index.php | grep -i -E '^(x-powered-by|system|can read)' || true
  echo "--- a page that raises a warning:"
  curl -s 'http://127.0.0.1:18081/index.php?oops=1' | tail -n +3 | head -n 3
  kill "$pid"; wait "$pid" 2>/dev/null || true
}
probe before -n
probe after -n -c "$LAB/hardening.ini"
echo "=== what the AFTER server wrote to its log instead:"
grep "Warning" "$LAB/after.server.log" | head -n 2
```

**Do (PowerShell 7, est.: not run).**

```powershell
$lab = (Resolve-Path (Join-Path $HOME 'w2-lab')).Path
@'
<?php
header('Content-Type: text/plain');
echo "system() exists:      ", var_export(function_exists('system'), true), "\n";
echo "can read /etc/passwd: ", var_export(is_readable('/etc/passwd'), true), "\n";
if (isset($_GET['oops'])) { echo $not_defined['x']; }
'@ | Set-Content (Join-Path $lab 'site\index.php')
function Probe($label, [string[]]$phpArgs) {
  $p = Start-Process php -PassThru -WindowStyle Hidden -RedirectStandardError (Join-Path $lab "$label.server.log") `
       -ArgumentList ($phpArgs + @('-S','127.0.0.1:18081','-t',(Join-Path $lab 'site')))
  Start-Sleep 2
  "=== $label"
  (Invoke-WebRequest http://127.0.0.1:18081/index.php).Headers.Keys | Where-Object { $_ -match 'Powered' }
  (Invoke-WebRequest http://127.0.0.1:18081/index.php).Content
  Stop-Process $p
}
Probe 'before' @('-n')
Probe 'after'  @('-n','-c',(Join-Path $lab 'hardening.ini'))
```

(`Invoke-WebRequest` raises an error on a response it considers failed; the warning page returns HTTP 200, so it should not. Windows has no `/etc/passwd`, so that line reads `false` in both runs; read it as an example of a path outside `open_basedir`.)

**Check.** My run:

```text
=== before
X-Powered-By: PHP/8.4.26
system() exists:      true
can read /etc/passwd: true
--- a page that raises a warning:
<br />
<b>Warning</b>:  Undefined variable $not_defined in <b>.../w2-lab/site/index.php</b> on line <b>5</b><br />
=== after
system() exists:      false
can read /etc/passwd: false
--- a page that raises a warning:
=== what the AFTER server wrote to its log instead:
```

The "before" page advertised the PHP version in a header and printed the full file path of the script into the page when a warning happened. The "after" page sent no `X-Powered-By`, showed nothing on error, and the warning text went to the server log instead (the last command printed those log lines; I trimmed them above). `system()` was gone and a file outside the allowed directories was unreadable, which is what `disable_functions` and `open_basedir` are for. A reminder of the limits: this does not stop the October 2026 flaws or any plugin's logic bug.

**Undo.** If a server is still running, find it with `ss -ltnp | grep 18081` and stop it by its process id with `kill PID`. Do not use `pkill -f`, which can match your own shell. Nothing else persists.

### Exercise 3: a loopback-only WordPress container (est.: not run)

**Why est.** My environment could not pull container images, so this exercise is written from the official image documentation (the [docker-library WordPress page](https://github.com/docker-library/docs/blob/master/wordpress/README.md), read 2026-10-22) and has not been run. The environment variables and the tag family come from that page. Expect to fix something. Everything binds to `127.0.0.1`, the database has no published port, no Docker socket is mounted, and no credential is stored in this page: the database password is generated at run time into a local `.env` file.

**Predict.** The image runs PHP with defaults. After mounting your hardening file into its `conf.d` directory and restarting, which of the values in `php -i` change? Will the site still work with `disable_functions` and `open_basedir` set?

**Do (Bash).**

```bash
set -eu
D="$HOME/w2-lab/wp"; mkdir -p "$D"; cd "$D"
umask 077
printf 'DB_PASSWORD=%s\n' "$(openssl rand -hex 16)" > .env          # generated now, never typed or committed
cat > compose.yaml <<'EOF'
# Apache-2.0. Loopback-only WordPress lab for lesson W2. No credential literals: .env is made at run time.
services:
  db:
    image: mysql:8.0
    environment:
      MYSQL_DATABASE: wplab
      MYSQL_USER: wplab
      MYSQL_PASSWORD: ${DB_PASSWORD}
      MYSQL_RANDOM_ROOT_PASSWORD: "1"
    volumes: ["db:/var/lib/mysql"]            # no ports: published
  wordpress:
    image: wordpress:php8.4-apache
    depends_on: [db]
    ports: ["127.0.0.1:8080:80"]              # loopback only
    environment:
      WORDPRESS_DB_HOST: db
      WORDPRESS_DB_USER: wplab
      WORDPRESS_DB_PASSWORD: ${DB_PASSWORD}
      WORDPRESS_DB_NAME: wplab
      WORDPRESS_CONFIG_EXTRA: |
        define( 'DISALLOW_FILE_EDIT', true );
    volumes: ["wp:/var/www/html"]
volumes: { db: {}, wp: {} }
EOF
docker compose up -d
sleep 20
curl -sI http://127.0.0.1:8080/ | grep -i -E '^(HTTP|x-powered-by|server)'
docker compose exec wordpress php -i | grep -E '^(expose_php|display_errors|disable_functions|open_basedir) ' > before-ini.txt
cat before-ini.txt
```

Now add the hardening file as a second mount. Make `hardening-container.ini` from the one in Exercise 1, changing the `open_basedir` line to `open_basedir = /var/www/html:/tmp`, then add this line under `volumes` for the `wordpress` service and re-create it. (The path `/usr/local/etc/php/conf.d` is where the image documentation says to put extra `.ini` files, as `$PHP_INI_DIR/conf.d/`; confirm with `docker compose exec wordpress php --ini`.)

```yaml
    volumes:
      - wp:/var/www/html
      - ./hardening-container.ini:/usr/local/etc/php/conf.d/zz-hardening.ini:ro
```

```bash
docker compose up -d --force-recreate wordpress
sleep 10
curl -sI http://127.0.0.1:8080/ | grep -i -E '^(HTTP|x-powered-by|server)'
docker compose exec wordpress php -i | grep -E '^(expose_php|display_errors|disable_functions|open_basedir) ' > after-ini.txt
diff before-ini.txt after-ini.txt || true
```

**Do (PowerShell 7, est.).** Create `.env` with `Set-Content -Path .env -Value ('DB_PASSWORD=' + [Convert]::ToHexString([System.Security.Cryptography.RandomNumberGenerator]::GetBytes(16)).ToLower())`, write the same `compose.yaml` with a here-string, use the same `docker compose` commands, and replace `grep -E` with `Select-String -Pattern '^(expose_php|display_errors|disable_functions|open_basedir) '`.

**Check.** Expected (est.): before, `X-Powered-By: PHP/8.4.x` in the headers and the four settings at their defaults; after, no `X-Powered-By`, `display_errors` off, a `disable_functions` list and an `open_basedir` value. Finish the WordPress install in a browser at `http://127.0.0.1:8080/`: choose a username that is not `admin`, a long unique password, and generate the password in your password manager; do not reuse any other. If an image upload or an update fails, the likely cause is `open_basedir` or `disable_functions`; remove one at a time to find which, which is exactly the testing a real site needs.

> **Screenshot to take yourself:** the WordPress login page on `http://127.0.0.1:8080/`.
> Capture: the page and the address bar showing the loopback address.
> Look for: nothing about your hostname or network.
> Redact: nothing should need it; check the browser tabs and bookmarks bar.

**Undo (teardown first, before anything else).**

```bash
cd "$HOME/w2-lab/wp" && docker compose down -v      # removes containers, network and volumes
docker image rm wordpress:php8.4-apache mysql:8.0   # optional, frees disk
```

PowerShell: `Set-Location $HOME\w2-lab\wp; docker compose down -v`. Then delete the folder. Prove it is gone: `docker ps -a` shows no `wp-` containers.

### Exercise 4: ModSecurity with the Core Rule Set in detection-only mode (est.: not run)

**Why est.** Same reason as Exercise 3: written from the project's container documentation (the [modsecurity-crs-docker README](https://github.com/coreruleset/modsecurity-crs-docker), read 2026-10-22), not run. The image name, the variable names (`BACKEND`, `MODSEC_RULE_ENGINE`, `MODSEC_AUDIT_ENGINE`, `BLOCKING_PARANOIA`) and the default port 8080 come from it. The tag `nginx` is the one I am least sure of; the README mentions both `owasp/modsecurity-crs:apache` and versioned nginx tags, so check the list on the registry page.

You will protect **your own** local page from Exercise 5 (run that first, or put any `index.html` in `~/w2-lab/static`). The only request patterns you send are CRS's own documented test: the install page shows `curl 'https://www.example.com/?foo=/etc/passwd&bar=/bin/sh'` as the way to check the rules are active. You send the same to your loopback address. The pattern is a harmless query string against a file server that ignores it; there is nothing here to exploit and nothing leaves your computer.

**Predict.** In `DetectionOnly` mode, what status will the documented probe get? What will be in the log that was not there before? If you switch the engine to `On`, what changes?

**Do (Bash).**

```bash
set -eu
D="$HOME/w2-lab/waf"; mkdir -p "$D"; cd "$D"
cat > compose.yaml <<'EOF'
# Apache-2.0. ModSecurity + OWASP CRS in front of a static folder, detection only. Loopback only.
services:
  backend:
    image: nginx:stable-alpine
    volumes: ["../static:/usr/share/nginx/html:ro"]       # no published port
  waf:
    image: owasp/modsecurity-crs:nginx
    depends_on: [backend]
    ports: ["127.0.0.1:8088:8080"]                        # loopback only
    environment:
      BACKEND: http://backend:80
      MODSEC_RULE_ENGINE: DetectionOnly
      MODSEC_AUDIT_ENGINE: "On"
      BLOCKING_PARANOIA: "1"
EOF
docker compose up -d
sleep 10
curl -s -o /dev/null -w 'normal page:   %{http_code}\n' http://127.0.0.1:8088/
curl -s -o /dev/null -w 'documented probe: %{http_code}\n' 'http://127.0.0.1:8088/?foo=/etc/passwd&bar=/bin/sh'
docker compose logs waf | grep -i -E 'anomaly|passwd' | head -n 5
```

PowerShell 7 (est.): use `curl.exe` for the two requests (PowerShell's `curl` is an alias for `Invoke-WebRequest`) and `docker compose logs waf | Select-String -Pattern 'anomaly|passwd' | Select-Object -First 5`.

**Check.** Expected (est.): both requests return `200` (nothing is blocked in `DetectionOnly`) and the log shows the probe with one or more matched rules and an anomaly score at or above 5. The audit log is JSON by default (the README lists JSON as the default `MODSEC_AUDIT_LOG_FORMAT`, written to the container's standard output): find the rule `id` values, their `msg` text and the scoring. Then edit the compose file to `MODSEC_RULE_ENGINE: "On"`, recreate the `waf` container, repeat the probe, and expect `403`, as the CRS install page says ("If you use blocking mode, you should receive an Error 403"). Put it back to `DetectionOnly` afterwards.

**Tune a false positive.** Pretend you run a Linux tutorial blog and a reader searches for `what is in /etc/passwd`. That is a harmless request that looks like the probe.

```bash
curl -s -o /dev/null -w 'reader search: %{http_code}\n' 'http://127.0.0.1:8088/?s=what+is+in+/etc/passwd'
docker compose logs waf | grep -i 'passwd' | tail -n 3        # note the rule id(s) and the matched argument name: s
```

Expected (est.): it is flagged, because it contains the same text. The precise fix removes the argument `s` from the inspection of that one rule, not the rule itself. Write an exclusion file (replace `RULE_ID` with the number from your log; CRS's own example for a WordPress field uses this exact form with another rule and argument):

```bash
printf 'SecRuleUpdateTargetById RULE_ID "!ARGS:s"\n' > RESPONSE-999-EXCLUSION-RULES-AFTER-CRS.conf
```

Mount it into the `waf` service at `/etc/modsecurity.d/owasp-crs/rules/RESPONSE-999-EXCLUSION-RULES-AFTER-CRS.conf` (the README's volume example uses that path), recreate the container and repeat both requests. Expected (est.): the search no longer scores, the documented probe on `foo` and `bar` still does. If your tuning removed too much, the probe will go quiet: that is the danger of exclusions, and why you check the probe after every change.

**Undo (teardown).** `cd "$HOME/w2-lab/waf" && docker compose down -v`. PowerShell: `Set-Location $HOME\w2-lab\waf; docker compose down -v`. Confirm with `docker ps -a`.

### Exercise 5: build a tiny static site and compare attack surface

**Predict.** A static site has no PHP and no database. When you ask it for `/wp-login.php` what comes back? When you send it the documented CRS probe query string, does the answer change?

**Do (Bash).** Plain files and Python's built-in file server (`-I` runs Python in isolated mode):

```bash
set -eu
SITE="$HOME/w2-lab/static"
mkdir -p "$SITE"
cat > "$SITE/index.html" <<'EOF'
<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Example static site</title>
<link rel="stylesheet" href="style.css"></head>
<body><h1>Example static site</h1><p>Built once. Served as files. See <a href="about.html">about</a>.</p></body></html>
EOF
cat > "$SITE/about.html" <<'EOF'
<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>About</title></head>
<body><h1>About</h1><p>No PHP and no database run when you read this page.</p></body></html>
EOF
printf 'body { font-family: sans-serif; max-width: 40rem; margin: 2rem auto; }\n' > "$SITE/style.css"
python3 -I -m http.server 18082 --bind 127.0.0.1 --directory "$SITE" > "$SITE/../static.server.log" 2>&1 &
pid=$!
for i in 1 2 3 4 5; do curl -s -o /dev/null http://127.0.0.1:18082/ && break; sleep 1; done
echo "--- a normal page:";            curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:18082/about.html
echo "--- a WordPress login URL:";    curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:18082/wp-login.php
echo "--- the CRS documented probe (query string is ignored; same page comes back):"
curl -s -o /dev/null -w '%{http_code} %{size_download} bytes\n' 'http://127.0.0.1:18082/?foo=/etc/passwd&bar=/bin/sh'
curl -s -o /dev/null -w '%{http_code} %{size_download} bytes (plain /)\n' http://127.0.0.1:18082/
kill "$pid"; wait "$pid" 2>/dev/null || true
echo "--- files you would have to protect:"; find "$SITE" -type f | wc -l
```

**Do (PowerShell 7, est.: not run).** Create the same three files with here-strings in `$HOME\w2-lab\static`, start `python -I -m http.server 18082 --bind 127.0.0.1 --directory $site` with `Start-Process -PassThru`, use `curl.exe -s -o NUL -w '%{http_code}\n' URL` for the requests, stop the process with `Stop-Process`, and count with `(Get-ChildItem $site -Recurse -File).Count`.

**Check.** My run: the normal page `200`; `/wp-login.php` `404`; the probe `200 263 bytes` and the plain `/` `200 263 bytes` (the same page, because the server ignores the query string); `3` files. There was nothing to inject into. For a real static site you do not run this server in production; you give the folder to a host or a plain web server (see the hosting options above). The file server's response headers (it names itself) are not what a real host sends, so do not copy them.

If you have Hugo installed you can build the same kind of site from content files; the [Hugo quick start](https://gohugo.io/getting-started/quick-start/) (read 2026-10-22) shows `hugo new project`, adding a theme as a Git submodule, `hugo server`, and `hugo` to write the finished files to `public`. I did not run it (Hugo is not installed on my machine, and I did not install it for this page). Notice that a theme added as a Git submodule is third-party code your build trusts: that is the static site's version of the plugin problem, small but real. Pin it to a commit you reviewed.

**The comparison to fill in.** Copy this table and fill it for the WordPress container (Exercise 3, or from the diagram in your head) and the static folder (Exercise 5):

| Question | WordPress on LAMP/LEMP | Static folder |
|---|---|---|
| How many programs run when a visitor arrives? | | |
| How many places take input from a visitor (forms, logins, uploads, query strings)? | | |
| What must be patched, and how often? | | |
| What file or login, if stolen, gives control of the site? | | |
| What does a successful break-in give? | | |
| What are you trusting from outsiders (plugins, themes, build tools)? | | |

**Undo.** Delete `~/w2-lab` when finished.

### Optional: on a real server of your own

Everything above is local. To harden and watch a real public WordPress server you need your own cloud account, which uses your own provider bill. [Lesson 1](LAMP-and-LEMP-From-Zero.md) builds the stack on a droplet and carries the cost and teardown section for that, and [lesson 3](DNS-Cloudflare-and-Hosting-Your-Own-Website.md) covers the domain, DNS and certificate. Read their cost and teardown parts before you start, and apply this page's hardening to what you build there. This page adds no cost figures of its own.

## Build it, break it, detect it, evade it, defend it

The same loop as the [labs](Labs-Break-It-on-Purpose.md), at concept level and on your own loopback only.

- **Build.** A loopback site with a hardening file (Exercises 1 and 2), and a static copy of it (Exercise 5). You can see what is exposed because you built it.
- **Break.** On your own loopback, send the documented CRS test string (Exercise 4) and read what a WAF thinks of it. On paper, ask what an outsider could do with a plugin that is missing a permission check, with a PHP runtime flaw like the October 2026 pair, and with a login page that has no rate limit. Do not try any of these on a computer you do not own, and do not look for working exploit code to run: the lesson is the *class*, not the recipe.
- **Detect.** The PHP error log (Exercise 2), the WAF audit log (Exercise 4), web server access logs, and a file-change monitor. Ship them off the box ([Logs, SIEM and detection basics](Logs-SIEM-and-Detection-Basics.md); [Detection and monitoring](Detection-and-Monitoring-Wazuh-and-the-Landscape.md)). A decoy login page or a planted fake credentials file that nobody legitimate would touch is a cheap high-quality alert: see [Deception and honeypots: start here](Deception-and-Honeypots-Start-Here.md).
- **Evade.** In words only. An attacker picks the one unpatched plugin on the internet-facing server because that is the cheapest way in; the Patchstack figures above are the reason the first hours after a disclosure matter. They try a low, slow request rate to stay under a rate limit, vary the encoding of a request so a pattern rule does not recognize it, and use stolen valid logins so nothing looks like an attack. None of that is shown here; the defender's takeaway is that rules and thresholds are not enough alone.
- **Defend.** Few plugins, updated fast; the PHP runtime patched the day a critical fix ships; hardened configuration; a least-privilege database user; two-factor on admins; a rate limit at the edge; a WAF started in detection mode and tuned before blocking; logs shipped away; tested backups; and, wherever the site does not need to compute anything per visit, no server code at all.

**Flip the board.** First, you are the owner of a ten-page personal site, and a friend says "just put WordPress on it". Write down the five things you would have to patch and watch that a static folder would not need, then decide, with your reasons. Second, you are the maintainer of a small WordPress plugin who gets a vulnerability report on a Friday evening. Write down what you need to do (reproduce, fix, release, tell users which version is safe), noting that Patchstack's figure says 46 percent of vulnerabilities had no fix at the time of disclosure, and what that means for the people who installed your plugin. Third, you run the hosting platform and a critical PHP fix lands: your customers' sites run on three PHP branches. Order what you do in the first hour, including which customers use mod_php and who is on an end-of-life branch.

## Checkpoint

You are done when you can say, without looking:

- Which of the three layers (runtime, application, plugin) a given flaw lives in, and who fixes it.
- Why the PHP runtime flaws of October 2026 are called memory-safety flaws, and what you could and could not confirm from the advisories.
- Three PHP settings that reduce what a flaw can do, and one that the October advisory says does not help against it.
- What a WAF can see, what it cannot, and why you start it in `DetectionOnly`.
- What a false positive is, and why a precise exclusion beats removing a rule.
- Two things you give up with a static site and one way to get each back.
- Which risk a static site moves instead of removing.

Answers are in the sections above.

## Common mistakes

- **Treating a WAF as a patch.** It is a layer, and for the October 2026 flaws I found no vendor statement that any WAF stops them.
- **Hiding the PHP version and calling it fixed.** `expose_php` stops advertising; it does not remove a flaw.
- **Putting the whole site in one PHP pool, as one user.** One compromised site becomes all of them.
- **Raising the CRS threshold to make the noise stop.** CRS's own page says to do that only temporarily during tuning.
- **Skipping the restore test.** [Backups, recovery and patching](Backups-Recovery-and-Patching.md).
- **Running an end-of-life PHP because "it works".** It works until the next advisory.
- **Leaving unused plugins and themes installed.** Deleted code cannot be exploited.
- **Following a hardening guide without testing a plugin afterwards.** `disable_functions` and `open_basedir` can break things; find out in a test copy.

## Claims register

Read 2026-10-22 with read-only requests to public pages (no logins), or run locally as stated. Items marked **est.** were not read or not run.

| Claim | Source | Status |
|---|---|---|
| WordPress ecosystem figures (11,334 new vulnerabilities in 2025, +42 percent; 91 percent plugins, 9 percent themes, 6 core; 1,966 high; 46 percent unfixed at disclosure; 5-hour weighted median to mass exploitation; Broken Access Control most exploited and hard for traditional WAFs; hosting defenses blocked 12 and 26 percent in two tests; top exploited list) | [Patchstack, State of WordPress Security in 2026](https://patchstack.com/whitepaper/state-of-wordpress-security-in-2026/), "Date updated 25.02.2026" | Read. A vendor's own figures; Patchstack sells protection, so read the WAF test results as the vendor's claim |
| Wordfence and WPScan yearly figures | wordfence.com pages, wpscan.com/statistics | **Not read**: Wordfence answered HTTP 202 (bot challenge), WPScan figures load by JavaScript. Not cited |
| PHP supported versions table and the support model | [php.net supported versions](https://www.php.net/supported-versions.php) | Read |
| php.net banner and notice: 8.5.12, 8.4.27, 8.3.36, 8.2.35 fix two critical flaws allowing unauthenticated RCE; risk highest for mod_php; vendors received patches in advance; 8.1 and older unsupported; minimal backports for 7.4, 8.0, 8.1 | [php.net front page](https://www.php.net/) | Read |
| 8.5.12 dated 22 October 2026, "Fixed GHSA-w8hw-w9fx-j79w, GHSA-6wmf-4rv5-p3rp (Avoid state corruption via bailout)" | [PHP 8 changelog](https://www.php.net/ChangeLog-8.php) | Read |
| GHSA-w8hw-w9fx-j79w (CVE-2026-109618, "RCE via OOM corruption") and GHSA-6wmf-4rv5-p3rp (CVE-2026-109619, "RCE via stale global state"): published Oct 21, 2026; affected < 8.2.35, < 8.3.36, < 8.4.27, < 8.5.12; CVSS v4 9.2 Critical, vector as shown; CWE-416, CWE-755, CWE-824, CWE-1325, CWE-1419; summaries, susceptibility by SAPI, mitigations, and the statements about `memory_limit=-1`, `RLIMIT_AS`, `fatal_error_backtraces`, `session.upload_progress.enabled`, `pm.max_requests=1`, recycling and error settings | The two [GitHub advisories](https://github.com/php/php-src/security/advisories/GHSA-w8hw-w9fx-j79w) and [its sibling](https://github.com/php/php-src/security/advisories/GHSA-6wmf-4rv5-p3rp) | Read. Each page repeats the other's impact paragraph under a cross-reference; I quote only the summaries, weakness lists, mitigations and CVSS data. The source code and the patch were not read |
| Whether any WAF stops these two flaws | none | **est.**: no WAF vendor statement read |
| CVE-2012-1823, CVE-2019-11043, CVE-2024-4577: published dates, descriptions, CWEs, CISA KEV dates | [NVD records](https://nvd.nist.gov/vuln/detail/CVE-2019-11043), read through the NVD CVE API 2.0 | Read |
| php.ini defaults and descriptions: `expose_php`, `display_errors`, `log_errors`, `disable_functions`, `open_basedir`, `allow_url_fopen`, `allow_url_include`, `file_uploads`, `upload_max_filesize`, `post_max_size`, `max_file_uploads`, session settings; the warning on large upload limits | PHP manual: [ini list](https://www.php.net/manual/en/ini.list.php), [core ini](https://www.php.net/manual/en/ini.core.php), [error handling](https://www.php.net/manual/en/errorfunc.configuration.php), [sessions](https://www.php.net/manual/en/session.configuration.php), [file uploads](https://www.php.net/manual/en/features.file-upload.common-pitfalls.php) | Read |
| Built-in web server "should not be used on a public network" | [PHP manual, built-in web server](https://www.php.net/manual/en/features.commandline.webserver.php) | Read |
| FPM pool settings, socket warnings, `php_admin_value`, `clear_env`, `security.limit_extensions` | [PHP manual, FPM configuration](https://www.php.net/manual/en/install.fpm.configuration.php) | Read |
| WordPress hardening: file permissions, `DISALLOW_FILE_EDIT`, database privileges, 2FA, backups, logging; brute-force guide: `xmlrpc.php`, 2FA not in core, rate limiting | [Hardening WordPress](https://developer.wordpress.org/advanced-administration/security/hardening/) (last updated October 14, 2026) and [Brute force attacks](https://developer.wordpress.org/advanced-administration/security/brute-force/) | Read |
| `DISALLOW_FILE_MODS`, `FORCE_SSL_ADMIN`, `WP_AUTO_UPDATE_CORE` values | [Editing wp-config.php](https://developer.wordpress.org/advanced-administration/wordpress/wp-config/) | Read |
| WordPress image: variables, tags (`php8.4-apache` family), `conf.d` for extra ini files, FPM warning, `mysql:8.0` in the compose example | [docker-library WordPress README](https://github.com/docker-library/docs/blob/master/wordpress/README.md) and [PHP image README](https://github.com/docker-library/docs/blob/master/php/README.md) | Read |
| CRS: anomaly scoring (thresholds 5 and 4), paranoia levels, false positives and exclusions, install page (v4.25.0, container example, `DetectionOnly`, documented test request, 403 in blocking mode, plugins replace exclusion packages) | [Anomaly scoring](https://coreruleset.org/docs/2-how-crs-works/2-1-anomaly_scoring/), [paranoia levels](https://coreruleset.org/docs/2-how-crs-works/2-2-paranoia_levels/), [false positives and tuning](https://coreruleset.org/docs/2-how-crs-works/2-3-false-positives-and-tuning/), [installation](https://coreruleset.org/docs/1-getting-started/1-1-crs-installation/) | Read |
| CRS container: image, variables (`BACKEND`, `MODSEC_RULE_ENGINE` values, audit variables, default JSON audit log to stdout, default port 8080), exclusion file path | [modsecurity-crs-docker README](https://github.com/coreruleset/modsecurity-crs-docker) | Read. The `nginx` tag name and the whole exercise **est.**: not run |
| What CRS is for | [OWASP CRS project page](https://owasp.org/www-project-modsecurity-core-rule-set/) | Read |
| Cloudflare Free plan: Free Managed Ruleset, custom rules (5, no regex), rate limiting (1 rule, 10-second periods), body inspection size | Cloudflare docs: [managed rules](https://developers.cloudflare.com/waf/managed-rules/), [custom rules](https://developers.cloudflare.com/waf/custom-rules/), [rate limiting rules](https://developers.cloudflare.com/waf/rate-limiting-rules/) | Read. Plans change; no affiliation |
| GitHub Pages terms and limits | [GitHub Pages limits](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits) | Read |
| Cloudflare Pages Free plan limits | [Pages limits](https://developers.cloudflare.com/pages/platform/limits/) | Read |
| Hugo quick start commands | [gohugo.io quick start](https://gohugo.io/getting-started/quick-start/) | Read; not run |
| Security header descriptions | MDN: [Strict-Transport-Security](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Strict-Transport-Security), [Content-Security-Policy](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy), [X-Content-Type-Options](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/X-Content-Type-Options), [Referrer-Policy](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Referrer-Policy), [X-Frame-Options](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/X-Frame-Options), [Permissions-Policy](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Permissions-Policy) | Read (first paragraphs) |
| OWASP Top 10:2025 category names | [top10.owasp.org/2025](https://top10.owasp.org/2025/) | Read |
| Memory safety data: Chromium 70 percent; Android 76 to 35 to 24 percent; more than 65 percent industry; 86 percent of critical in 2022; 21 percent of new native code in Rust | [Chromium memory safety](https://www.chromium.org/Home/chromium-security/memory-safety/), Google Security Blog posts of [Dec 2022](https://security.googleblog.com/2022/12/memory-safe-languages-in-android-13.html) and [Sep 2024](https://security.googleblog.com/2024/09/eliminating-memory-safety-vulnerabilities-Android.html) | Read; post dates are from the URLs |
| CISA memory-safety guidance | [Case for Memory Safe Roadmaps](https://www.cisa.gov/resources-tools/resources/case-memory-safe-roadmaps) (6 Dec 2023), [CISA and NSA Memory Safe Languages](https://www.cisa.gov/resources-tools/resources/memory-safe-languages-reducing-vulnerabilities-modern-software-development) (24 Jun 2025) | Page summaries read; the PDFs were not |
| Microsoft MSRC memory-safety share; White House ONCD report | none | **Not read**: the MSRC pages I reached did not show the statement; ONCD not fetched. Not cited |
| Rust: memory safety guarantees outside `unsafe`; `unsafe` does not turn off the borrow checker | [The Rust Book, Unsafe Rust](https://doc.rust-lang.org/book/ch20-01-unsafe-rust.html) | Read |
| Rust for Linux exists and lists in-mainline drivers | [rust-for-linux.com](https://rust-for-linux.com/) | Read (hub page) |
| Python's interpreter is written in C; C has no built-in bounds checking | General knowledge | **est.**, not looked up |
| Exercises 1, 2 and 5 in Bash, and the memory demo: outputs shown | Run on Linux with PHP 8.4.26 (CLI and built-in server), Python 3.13, gcc with AddressSanitizer, rustc 1.99.0 on 2026-10-22 | Run 2026-10-22 |
| Exercises 3 and 4; every PowerShell block; Hugo | Image and tool documentation | **Not run**; **est.** |
| STRIDE table, residual-risk wording, static-vs-WordPress comparison table | My own teaching map | **est.** |

Next: [Threat model](Threat-Model.md), step 19 of the core path on the [Reading order](Reading-Order.md) page.
