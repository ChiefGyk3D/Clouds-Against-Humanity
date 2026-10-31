# Static against dynamic: Hugo and WordPress that look the same, and how to tell them apart

Side page to the web pages. Read it after [WordPress and PHP security, WAFs and static sites](WordPress-and-PHP-Security-WAF-and-Static-Sites.md) (which argues why a static site often wins) and beside [Security tools basics](Security-Tools-Basics-Nmap-OpenVAS-Burp-Metasploit.md) (which has the rules for using any recon tool). The WordPress lab it points to is [WordPress at scale: CDN, WAF, caching and CI](WordPress-at-Scale-CDN-WAF-and-CI.md). The red and blue tools track is issue [#221](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/221). Next: [Attack surface: list, shrink, measure](Attack-Surface-List-Shrink-Measure.md).

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

> **Status: unverified draft. One script was run on Linux; every real Hugo and WordPress claim was read, not run.** On **2026-10-31** I ran the stand-in script below with Python 3.13, `curl` 8.21.0 and WhatWeb 0.5.5 on Linux, only against `127.0.0.1`, and pasted trimmed output. **The two "sites" in that script are small stand-ins, not real Hugo and not real WordPress.** They copy the outward signs a visitor can see. I did **not** build a real Hugo site and I did **not** run the real WordPress lab, so everything said about those two products comes from their own documentation and from the existing WordPress page in this wiki, with the page and date in the [claims register](#claims-register). The TLS, certificate and DNS commands are written from reading and were not run. I could not read the InfoSecMap site (see the career section). **The career section is the maintainer's opinion in his words, and he has not yet reviewed this page.** Nothing here costs money.

> **Prerequisites.** You can use a terminal ([The terminal and your first script](Terminal-and-Your-First-Script.md)) and know what a web request looks like ([How a web request works](How-a-Web-Request-Works.md)). Python 3.11 or newer and `curl`; WhatWeb is optional. About 60 minutes (est.).

> **Where this runs, and the rule.** Recon tools are used **only against sites you own, or sites where the owner has given you written permission to test**. "It was public" is not permission. The full rules are in [Security tools basics](Security-Tools-Basics-Nmap-OpenVAS-Burp-Metasploit.md#authorization-and-scope-come-first). Everything run on this page goes to `127.0.0.1`, which never leaves your computer. The only other address named is `example.com`, which is reserved for documentation: read the commands, and run them against your own domain, not against someone else's.

## What you will be able to do

- Say what runs on a server for a static site and for a WordPress site, and what an attacker can reach in each.
- Tell the two apart from outside using response headers, page source, generator tags, well-known paths and `robots.txt`, and say why each sign is evidence and never proof.
- Use `curl` and WhatWeb (and say what a browser extension such as Wappalyzer does) to do the same fast.
- Read what a site leaks, and name the one change that removes each leak.
- Compare the two for attack surface, patching, login pages, cost and speed, without inventing numbers.
- Say why a public body of work (a GitHub profile, a blog) helps in a job search, and where to meet people.

## In plain words

A **static** site is a folder of finished files. A program such as [Hugo](https://gohugo.io/) builds them once, on your computer or in a pipeline, and a file server hands them out as they are. A **dynamic** site builds each page when the visitor asks: [WordPress](https://wordpress.org/) runs PHP code, reads a database and assembles the page on every request. A visitor often cannot tell. The same theme, the same words and the same pictures can come from either.

The difference is not on the screen. It is in what runs on the server, what a stranger can reach, and what you have to patch. That is why a web designer or a tester looks past the page, at the headers, the source and the paths. This page teaches that look, on a pair of sites you can run yourself.

## What is different underneath

The first table is the existing comparison on the [WordPress and PHP page](WordPress-and-PHP-Security-WAF-and-Static-Sites.md#why-static-sites-win-so-often), shortened. I have not changed its claims.

| Question | WordPress (dynamic) | Hugo output (static) |
|---|---|---|
| Code that runs when a visitor arrives | PHP, WordPress core, every plugin and theme | None; the server reads a file and sends it |
| Database | Yes, holding users and content | None at runtime |
| Login page on the internet | `wp-login.php` and `xmlrpc.php` | None |
| Things to patch | PHP, the web server, the database, WordPress, each plugin, each theme | The web server or the hosting service |
| Uploads from visitors | Possible | None |
| Where the risk moved | n/a | To the build chain: the generator, its themes and packages, and whoever can push to the repository |

Two rows deserve a second look.

- **Plugins.** That page says plugins and themes carry most of a WordPress site's risk and gives the numbers and whose numbers they are ([what the numbers say](WordPress-and-PHP-Security-WAF-and-Static-Sites.md#what-the-numbers-say-and-whose-numbers-they-are)). I do not repeat them here. The point for this lesson: every plugin is a stranger's code that runs with your site's powers, and each one has its own update schedule.
- **Patching.** On a dynamic site, a critical flaw in PHP or a plugin is a race you run on the day it is published. On a static site that serves only files, the race moves to the build tools and the host, and nothing in the request path runs your code. A static site is not automatically safe: a leaked deploy token or a compromised theme package is still a way in.

**Cost and speed.** I did not measure either. What the existing page supports is structural: a static host only reads and sends files, so it needs no PHP workers and no database, and it can sit behind a cache easily. A dynamic site needs a server that runs code and a database, which is more to rent, more to patch and, without caching, more work per request. The [cost lesson](How-Money-Works-in-the-Cloud.md) and the free hosting limits on the WordPress page are the places to get real figures, and the limits there change, so read the current page before you depend on one. The [WordPress at scale lab](WordPress-at-Scale-CDN-WAF-and-CI.md) is where the caching, CDN and WAF side is built.

## Telling them apart from outside

Everything below is what any visitor's browser already receives. A tester just reads it on purpose. Each sign is **evidence, not proof**: a site owner can remove any of them, and a site can fake them.

| Sign | Where you look | Points to dynamic WordPress | Points to a Hugo build | How it is hidden or faked |
|---|---|---|---|---|
| Generator tag | Page source, in the `<head>` | `<meta name="generator" content="WordPress ...">` | `<meta name="generator" content="Hugo ...">` | A theme may leave it out; a plugin or a line of code can remove it; anyone can write a false one |
| REST API pointer | Response header `Link` and a `<link>` in the head | `rel="https://api.w.org/"` and a `/wp-json/` address | Absent | A hardening plugin can remove it |
| Login page | Request `/wp-login.php` | `200` and a login form | `404` | Moved or blocked by a plugin or a firewall rule; moving it hides it and shrinks nothing (see [the port-move rule](Attack-Surface-List-Shrink-Measure.md#the-port-move-rule)) |
| Asset paths | Source: where the CSS and scripts load from | `/wp-content/` and `/wp-includes/` | Whatever the theme chose, often `/css/` or a hashed file name | A CDN or an optimizer can rewrite them |
| `X-Powered-By` header | Response headers | May name PHP and its version | Absent | Easy to turn off |
| `Server` header | Response headers | A web server name, often with a version | A web server or a hosting service | Same on both; **it does not tell them apart**, but it can tell you the software to look up |
| `robots.txt` | Request `/robots.txt` | May list `/wp-admin/` | Often a short allow list, or absent | See below |
| Query forms | Links such as `?p=12` or `?s=term` | Common | Rare | Pretty links hide it |

(The first two rows rest on the products' own documentation, in the claims register. The others are my reading of how the products behave and are marked **est.** there.)

**What `robots.txt` is, and is not.** It is a file at the top of a site that asks well-behaved crawlers to skip some paths. The standard that defines it says "These rules are not a form of access authorization" ([RFC 9309](https://www.rfc-editor.org/rfc/rfc9309), read 2026-10-31). So a `Disallow` line is a request to polite robots, and it also tells a tester which paths the owner considers interesting. Do not put a secret path in it.

## The tools

All of these only send ordinary requests (WhatWeb can be told to send more; see below) and read the answers.

- **Your browser.** Use "view source" and the network panel. This is the first tool and the one every designer already has.
- **`curl`.** Prints headers (`curl -I`), the source (`curl -s`) and status codes (`curl -s -o /dev/null -w "%{http_code}"`). Scriptable, and the same request every time.
- **WhatWeb.** A command-line fingerprinter. Its README says it "identifies websites", recognises content management systems, web servers and more, and has over 1800 plugins (the README says 1824 at the time I read it, 2026-10-31). Its default aggression level, "stealthy", makes the fewest requests; higher levels "interrogate" the site more, which is more noise in the owner's logs and needs the same permission. Use level 1 on this page. Its README names version 0.6.4 as the latest release (April 3, 2026); the copy I ran was 0.5.5 from my distribution, so my output may differ from yours.
- **Wappalyzer and similar browser extensions.** They do the same fingerprinting inside the browser and show the result as icons. I did not install or read the current terms of any of them, and I name them only so you know the category. Check a tool's current licence before you rely on it.
- **TLS and certificates.** `openssl s_client -connect example.com:443 -servername example.com` opens a TLS connection and prints the certificate chain. It tells you who issued the certificate, for which names and until when. Written from reading, not run; point it at your own domain.
- **DNS.** `dig example.com`, `dig example.com MX`, `dig example.com TXT` ask for address, mail and text records. The text records show which hosting or mail services a site uses. Written from reading, not run. See [DNS, Cloudflare and hosting your own website](DNS-Cloudflare-and-Hosting-Your-Own-Website.md).

## What a site leaks, and the one change that removes it

| Leak | What it tells a stranger | The change |
|---|---|---|
| Generator tag with a version | The product and the version, so which known flaws to try | Remove the tag, and patch (hiding it does not fix the flaw) |
| `X-Powered-By` with a PHP version | The runtime and version | Turn the header off, and keep PHP supported |
| Plugin and theme paths in the source | Which plugins you run, which is the list of what to look up | Fewer plugins; keep each one patched |
| `wp-login.php` open to everyone | Where to guess passwords | Two-factor or passkeys, rate limits, a block by address or by country at the edge |
| `/wp-json/` open | A list of users and content routes on some setups (est.; check yours) | Review what it exposes before changing it |
| Comments in source, old test pages, backup files | Whatever the author forgot | Do not ship them; a static build makes this a build check |
| `robots.txt` listing private paths | The paths | List nothing private; protect the path itself |

Removing the sign slows a casual look. It does not patch anything, which is the lesson of [Security tools basics, Exercise 8](Security-Tools-Basics-Nmap-OpenVAS-Burp-Metasploit.md#exercise-8-build-it-then-scan-it).

## Free path: two look-alike sites on your own computer

The reading above is free. This exercise is optional and costs nothing: no account, no install beyond Python 3 and `curl`.

Save this as `siteduo.py` in an empty folder. It starts two stand-in sites on loopback. They serve the same page, the same CSS and the same words. Only the outward signs differ. The **Server** header is the same on both on purpose, so you have to use the other signs. **These are stand-ins that copy the signs described above. They are not real Hugo or real WordPress.**

```python
#!/usr/bin/env python3
# siteduo.py - two look-alike stand-in sites on LOOPBACK ONLY: "static" (Hugo-style) and "dynamic" (WordPress-style).
# They are small stand-ins that copy the outward signs of the two kinds of site. Neither is real Hugo or real WordPress.
# Same page, same style sheet, same words. Only how each is "built" shows in the headers, the source and the paths.
import argparse
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BODY = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Example Notes</title>
{head}
</head><body><h1>Example Notes</h1><p>A small blog about learning security. Nothing here is real.</p>
<p><a href="/">Home</a></p></body></html>
"""
CSS = "body{font-family:sans-serif;max-width:40em;margin:2em auto}h1{color:#234}"
STATIC_HEAD = '<meta name="generator" content="Hugo 0.169.0">\n<link rel="stylesheet" href="/style.css">'
DYNAMIC_HEAD = (
    '<meta name="generator" content="WordPress 6.8">\n'
    '<link rel="https://api.w.org/" href="http://127.0.0.1:{port}/wp-json/">\n'
    '<link rel="stylesheet" href="/wp-content/themes/notes/style.css?ver=6.8">'
)


def make_handler(kind, port):
    dynamic = kind == "dynamic"

    class H(BaseHTTPRequestHandler):
        server_version = "Apache/2.4"  # the same on both stand-ins, so the Server header does not tell them apart
        sys_version = ""

        def log_message(self, *args):
            pass

        def reply(self, code, ctype, body, extra=()):
            data = body.encode()
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            for k, v in extra:
                self.send_header(k, v)
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(data)

        def do_GET(self):
            path = self.path.split("?", 1)[0]
            extra = [("X-Powered-By", "PHP/8.3"), ("Link", f'<http://127.0.0.1:{port}/wp-json/>; rel="https://api.w.org/"')] if dynamic else []
            if path == "/":
                head = DYNAMIC_HEAD.format(port=port) if dynamic else STATIC_HEAD
                self.reply(200, "text/html", BODY.format(head=head), extra)
            elif path == ("/wp-content/themes/notes/style.css" if dynamic else "/style.css"):
                self.reply(200, "text/css", CSS)
            elif path == "/robots.txt":
                txt = "User-agent: *\nDisallow: /wp-admin/\nAllow: /wp-admin/admin-ajax.php\n" if dynamic else "User-agent: *\nAllow: /\n"
                self.reply(200, "text/plain", txt)
            elif dynamic and path == "/wp-login.php":
                self.reply(200, "text/html", "<html><body><form method='post'>Username <input name='log'> Password <input name='pwd' type='password'></form></body></html>")
            elif dynamic and path == "/wp-json/":
                self.reply(200, "application/json", json.dumps({"name": "Example Notes", "namespaces": ["wp/v2"]}))
            else:
                self.reply(404, "text/plain", "not found\n")

        do_HEAD = do_GET

    return H


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-port", type=int, default=18480)
    a = ap.parse_args()
    for kind, port in (("static", a.base_port), ("dynamic", a.base_port + 1)):
        srv = ThreadingHTTPServer(("127.0.0.1", port), make_handler(kind, port))
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        print(f"{kind} site on http://127.0.0.1:{port}/", flush=True)
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
```

### Exercise: which one is the WordPress site?

**Predict.** Both sites show the same page. Open both in a browser: do they look different? Then write down which of the signs in the table above you expect to differ, and whether the `Server` header will be one of them.

**Do.** In one terminal:

```bash
python3 -I siteduo.py
```

In a second terminal, first prove where it listens (a habit before any test), then compare headers, source and paths for both ports, 18480 and 18481:

```bash
ss -ltn | grep -E ':1848[01] '
for p in 18480 18481; do
  echo "=== $p"
  curl -sI http://127.0.0.1:$p/
  curl -s http://127.0.0.1:$p/ | grep -iE "generator|api.w.org|stylesheet"
  for u in /wp-login.php /wp-json/ /robots.txt; do
    curl -s -o /dev/null -w "$u %{http_code}\n" http://127.0.0.1:$p$u
  done
done
```

Then the same question with WhatWeb at the stealthy level (skip this if you do not have it):

```bash
whatweb --color=never -a 1 http://127.0.0.1:18480/ http://127.0.0.1:18481/
```

**Check.** `ss` shows both ports on `127.0.0.1`. The comparison, trimmed, from the run on 2026-10-31:

```text
=== 18480
HTTP/1.0 200 OK
Server: Apache/2.4
Content-Type: text/html

<meta name="generator" content="Hugo 0.169.0">
<link rel="stylesheet" href="/style.css">
/wp-login.php 404
/wp-json/ 404
/robots.txt 200
=== 18481
HTTP/1.0 200 OK
Server: Apache/2.4
Content-Type: text/html
X-Powered-By: PHP/8.3
Link: <http://127.0.0.1:18481/wp-json/>; rel="https://api.w.org/"

<meta name="generator" content="WordPress 6.8">
<link rel="https://api.w.org/" href="http://127.0.0.1:18481/wp-json/">
<link rel="stylesheet" href="/wp-content/themes/notes/style.css?ver=6.8">
/wp-login.php 200
/wp-json/ 200
/robots.txt 200
```

(`Date` and `Content-Length` lines are cut for space.) The `Server` header is identical, as designed. The generator tag, the `Link` header, `X-Powered-By`, the asset path, the login page and the API route all separate the two. WhatWeb read the same hints and named them (trimmed):

```text
http://127.0.0.1:18480/ [200 OK] ... MetaGenerator[Hugo 0.169.0], Title[Example Notes]
http://127.0.0.1:18481/ [200 OK] ... MetaGenerator[WordPress 6.8], PHP[8.3], UncommonHeaders[link], WordPress[6.8], X-Powered-By[PHP/8.3]
```

Now the part that matters. Edit `DYNAMIC_HEAD` to take out the generator line, restart, and run the comparison again. The tag is gone, the `Link` header and `/wp-login.php` are not. That is the lesson: removing one sign hides a little and fixes nothing, and several independent signs agree. The honest answer to "is it WordPress?" is "very likely, here is the evidence", not "proven".

**Undo.** Ctrl-C stops both servers. Delete the folder.

### Going further (optional, not run)

The real version of this exercise is to build a small Hugo site and a small WordPress site with the same theme, pages and words, then run the comparison above on both, on your own machines only. The WordPress side can use the loopback WordPress lab described in [WordPress and PHP security, Exercise 3](WordPress-and-PHP-Security-WAF-and-Static-Sites.md#exercise-3-a-loopback-only-wordpress-container-est-not-run) and the larger one in [WordPress at scale](WordPress-at-Scale-CDN-WAF-and-CI.md). I have not built either pair. Hugo's own documentation is the place to start for the static side; mind that a theme may or may not print the generator tag, since the tag comes from a template function (`hugo.Generator`), not from Hugo by itself.

## Why keep a blog, and a note on getting work

The maintainer asked for this section and has not reviewed it yet. Everything in it is his stated experience, in his words as given on 2026-10-30. It is opinion about careers, not research.

- **Put your effort where it pays.** A lot of people put all of it into LinkedIn. His experience is that it does not pay off the way a body of public work does.
- **A public GitHub profile can do the job a blog would do.** It shows how you think and what you build. He has been given more opportunities because of his GitHub. The two sites on this page are for people who want a blog of their own, and a blog is a fine way to show your work. A profile with real projects and clear write-ups is the same thing in another format.
- **Go where people are.** Conferences such as DEF CON and BSides, and local events. He points to InfoSecMap as a place to find them: <https://infosecmap.com/>. **I could not verify that site or what it lists.** When I tried to read it on 2026-10-31 it returned a bot-check page (HTTP 403, "Just a moment"), not its content. Check it yourself, and check each event's own page for dates and prices before you plan around it.
- **Join the community.** The maintainer runs a Discord server ([discord.chiefgyk3d.com](https://discord.chiefgyk3d.com)) and a Matrix server ([matrix-invite.chiefgyk3d.com](https://matrix-invite.chiefgyk3d.com)). Those are the addresses this repository's README and Home page already list.
- **A resume writer is worth considering.**
- **Start in IT.** If you are asking which certification comes next instead of which lesson comes next, the priorities are the wrong way round. The maintainer has no four-year degree and holds only a CISSP, and he became a Senior Cybersecurity Engineer. A four-year degree is not required. [Careers, roles and what to learn next](Careers-Roles-and-What-to-Learn-Next.md) maps the roles.

This section names no employer and makes no promise about your path. His is one path.

## Checkpoint

1. Name three things that run on a WordPress server for each visit that do not run on a static host.
2. Which two signs in the stand-in comparison are published in the products' own documentation, and what does each look like?
3. Why does the identical `Server` header not settle the question?
4. You remove the generator tag from the dynamic stand-in. What still shows it is WordPress, and what has the removal fixed?
5. Why is a `Disallow` line in `robots.txt` not protection?
6. What must you have before you run WhatWeb or `curl` against a site?
7. Which row of the leak table is fixed by patching and not by hiding?

Answers: (1) PHP code, the WordPress core and its plugins, and the database (also the login page). (2) The generator meta tag (`hugo.Generator` for Hugo) and the `Link` header or `<link>` element with `rel="https://api.w.org/"` for WordPress. (3) Both sites can run the same web server software, so it names the server, not the site builder. (4) The `Link` header, `X-Powered-By`, the asset paths, `/wp-login.php` and `/wp-json/`; nothing was fixed, a casual look is just a little slower. (5) The standard says the rules are not access authorization, and the file names the paths. (6) That the site is yours, or the owner's written permission. (7) The generator tag and the PHP version: the flaw is in the software, so patch it.

## Common mistakes

- **Treating one sign as proof.** Say "very likely" and list the signs that agree.
- **Running a recon tool at a site you do not own.** Ownership or written permission first, every time.
- **Hiding the version and calling the site patched.** Hiding slows a look; only an update removes the flaw.
- **Calling a static site "secure".** It moves the risk to the build chain and the repository; it does not remove it.
- **Believing the stand-in is WordPress.** It copies a few signs. A real site has many more, and some are removed on purpose.
- **Scanning with a high WhatWeb aggression level.** More requests, more noise, and the same permission needed.
- **Putting a secret path in `robots.txt`.**

## Claims register

Pages read on 2026-10-30 and 2026-10-31 (UTC dates vary by a day). "Run" means I ran it that day.

| Claim | Source | Status |
|---|---|---|
| Hugo's `hugo.Generator` returns an HTML meta element identifying the software that generated the site, for example `<meta name="generator" content="Hugo 0.169.0">` | [gohugo.io, hugo.Generator](https://gohugo.io/functions/hugo/generator/), read 2026-10-30 | Read. Whether a given theme prints it was not checked |
| WordPress adds a `Link` header with `rel="https://api.w.org/"` to front-end pages and an equivalent `<link>` in the head | [REST API handbook, discovery](https://developer.wordpress.org/rest-api/using-the-rest-api/discovery/), read 2026-10-30 | Read; real WordPress not run |
| WordPress prints a generator tag through `wp_generator()` on the `wp_head` hook, filterable | [wp_generator](https://developer.wordpress.org/reference/functions/wp_generator/) and [the_generator](https://developer.wordpress.org/reference/functions/the_generator/), read 2026-10-31 | Read. The exact text of the real tag, `WordPress 6.8` in the stand-in, is an example and not read from a real site |
| `robots.txt` rules "are not a form of access authorization" | [RFC 9309](https://www.rfc-editor.org/rfc/rfc9309), read 2026-10-31 | Read |
| WhatWeb identifies websites, recognises CMSs and web servers, has over 1800 plugins (README badge 1824), default aggression "stealthy", latest release 0.6.4 dated April 3, 2026, GPLv2 | [WhatWeb README](https://github.com/urbanadventurer/WhatWeb), read 2026-10-30 and 2026-10-31 | Read. Ran version 0.5.5 from the distribution, not 0.6.4 |
| The comparison table of what runs, the database, login pages, patching, uploads and the build-chain risk | [WordPress and PHP security, why static sites win](WordPress-and-PHP-Security-WAF-and-Static-Sites.md#why-static-sites-win-so-often) | Read in this wiki, itself a draft |
| `X-Powered-By`, `Server`, `wp-content` paths, `?p=` and `robots.txt` contents as signs of WordPress | General knowledge of the products | **Est.**; not checked against a live install |
| `/wp-json/` may list users on some setups | General knowledge | **Est.**; not checked |
| `openssl s_client` and `dig` commands | General knowledge of the tools | **Est.**; not run |
| Wappalyzer and similar extensions fingerprint a site in the browser | General knowledge | **Est.**; not installed, terms not read |
| The stand-in output and the WhatWeb output | Run once 2026-10-31, Python 3.13, curl 8.21.0, WhatWeb 0.5.5, loopback only | Run |
| The career section: LinkedIn against a body of public work, GitHub as a blog, more opportunities from GitHub, go where people are, resume writer, start in IT, certification against lesson, no four-year degree, CISSP only, Senior Cybersecurity Engineer | Maintainer, 2026-10-30 (issue 317) | His words, as given. Not yet reviewed by him on this page |
| The InfoSecMap address `https://infosecmap.com/` | Given by the maintainer, 2026-10-31 | **Unverified.** The site returned HTTP 403 with a bot-check page when fetched with `curl` on 2026-10-31, so what it lists was not read |
| Discord and Matrix addresses | README.md and docs/wiki/Home.md in this repository | Read |

Not verified, plainly: any real Hugo or WordPress site (none built); the real WordPress lab (not run); every `openssl` and `dig` command; Wappalyzer; whether InfoSecMap lists what the maintainer says; cost and speed figures (none measured); WhatWeb 0.6.4 behavior; anything on Windows or macOS.

Next: [Attack surface: list, shrink, measure](Attack-Surface-List-Shrink-Measure.md).
