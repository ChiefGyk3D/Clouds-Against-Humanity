# Screenshots policy: what may be pictured and how

This page is for anyone adding a picture to the wiki. Pictures help a learner see what a page describes, and they are the easiest way to leak something by accident. The rules below are checked by tests where a test can check them (`tests/test_wiki_images.py`), and by the reviewer where it cannot.

## What may be screenshotted

Only a public tool showing this repository's own synthetic models or data. Today that means:

- OWASP Threat Dragon (the hosted demo in Local Session, or a copy you run yourself) showing the models in `docs/threat-model/`.
- The MITRE ATT&CK Navigator showing `docs/threat-model/attack-navigator-layer.json`.
- Synthetic demo dashboards built for the lessons, never a real monitoring system.
- A terminal or editor showing only repository files and made-up values.

A caption under each picture says the tool, its version, the date, and that the model or data is the repository's own synthetic one.

## What must never be screenshotted

- A real console (a cloud provider, Spacelift, Doppler, Twingate, GitHub settings) showing a tenant or organisation name, an account id, an IP address, an email address, a token, a secret value, a recovery code or a billing figure.
- Anything from a maintainer's or contributor's home or lab network: hostnames, addresses, dashboards, device lists.
- A browser window with other tabs, bookmarks, profile pictures or extensions visible.
- Terminal output you have not read line by line. Prompts, paths and environment dumps carry usernames and machine names.

If you are unsure, do not capture it. Use a placeholder (below) instead.

## How to redact

Redact by not capturing, then by cropping, and only last by drawing over. If you draw a solid box over text, save a flattened PNG so no layer under the box survives; never rely on a layer that can be toggled off. Prefer to capture from a clean account, crop to the panel, and re-capture if anything private shows. Never blur: blur can sometimes be reversed for short strings. After saving, run the metadata stripper below, then open the final file and read every pixel of it once.

## How to capture

- **Headless, fixed viewport.** Use a headless browser with a viewport of 1440 by 900 for a normal page. A larger viewport (up to 2400 pixels wide) is fine for a wide diagram or matrix; say so in the caption.
- **Prefer the tool's own export** for a diagram (Threat Dragon's Export, PNG gives the whole diagram regardless of window size).
- **Light mode** unless the lesson is about dark mode. Do not mix light and dark pictures on one page.
- Do not run a graphical tool on a maintainer's own desktop just to take a picture. Headless only.

## Where files go and what they look like

- Store under `docs/wiki/images/NAME.png`, lowercase words joined by dashes, for example `threat-dragon-stride-diagram.png`. **PNG only.** JPEG is not accepted: it can carry EXIF, XMP, IPTC and comment segments anywhere in the file, and a screenshot has no need of it. Only regular files: a symlink, a subdirectory or any other file type in the images directory fails the build.
- Reference from a page with ordinary Markdown image syntax and nothing else: an exclamation mark, the alt text in square brackets, then the path `images/NAME.png` in round brackets, with no title. Raw HTML image tags (`<img>`, `<picture>`, `<source>`, `<video>`), reference-style images, the wiki's double-bracket image syntax and any remote or `data:` image address are rejected by a test, because a remote image is a tracking pixel. The wiki generator copies the files to the flat wiki and rewrites the path to the raw URL the wiki serves, outside code blocks only; see [CI, tests and the cost gate](CI-Tests-and-Cost-Gate.md) for how pages are checked.
- Every file must be used by at least one page, and every referenced file must exist.

### Alt text

Describe what a learner should see, not "screenshot". At least 10 characters, and in practice a sentence: what is on screen and which part matters. Do not put any private value in alt text either.

### Keep files small

At most 600 KB each and at most 2400 pixels wide. Crop to the part that teaches. For flat user-interface pictures, reduce to a palette (64 to 128 colours) with an image tool; a diagram that was 350 KB as a full-colour PNG is about 80 KB as a palette PNG with no visible change.

### Strip metadata

Screenshots can carry text chunks, EXIF data, timestamps and colour-profile text. Strip them before committing:

```bash
python3 scripts/strip_png_metadata.py docs/wiki/images/NAME.png
```

The stripper uses an allowlist, not a blocklist: only `IHDR`, `PLTE`, `IDAT`, `IEND`, `tRNS` (transparency) and the colour chunks `gAMA`, `cHRM` and `sRGB` survive, and a test fails the build if a committed PNG has any other chunk, a bad checksum, bytes after the end marker, a missing end marker, or is animated (APNG, which is refused rather than flattened). The embedded colour profile (`iCCP`) is removed on purpose: a profile carries free text such as device and software names, and a browser screenshot is plain sRGB. Metadata stripping removes nothing that is drawn in the pixels, so it does not replace the review below.

## Manual review checklist (required for every screenshot)

No test can read pixels. Every pull request that adds or changes a picture must state in its description that the author opened the final stripped file at full size and checked each item, and the reviewer repeats it:

- [ ] Browser address bar and tab strip are cropped out or clean: no address, **query string**, session or tenant name, no other **tabs**, no **bookmarks** bar, no **extensions** icons.
- [ ] No **tenant**, organisation, **project name**, team or workspace name.
- [ ] No **username**, display name, **avatar** or profile control.
- [ ] No **local path**, home directory, **hostname**, machine name or serial.
- [ ] No **account id**, subscription id, billing figure or card detail.
- [ ] No **email** address, phone number or callsign.
- [ ] No **IP address**, CIDR range or VPN address.
- [ ] No **token**, key, secret value, recovery code or one-time password, including one shown once in a dialog.
- [ ] No **notification** pop-up, toast or system tray item at the screen edges.
- [ ] The edges were inspected, and a thumbnail of the picture was looked at as well.
- [ ] The model text in a diagram (names, descriptions, threats) was read and is generic.

## Placeholders for consoles you cannot capture safely

Some lessons describe a vendor console that cannot be pictured safely here. Where a picture would help, the page carries a callout asking the learner to take the screenshot themselves, in their own account, for their own notes. Every callout has exactly these parts:

```markdown
> **Screenshot to take yourself:** one line saying which screen.
> Capture: what to put in frame.
> Look for: what the picture should show you.
> Redact: what to remove before you keep or share it.
```

A test fails if a callout is missing "Capture:", "Look for:" or "Redact:". Do not turn a placeholder into a real picture unless the picture meets every rule on this page.

## Links

[Threat Dragon exercise](Threat-Dragon-Exercise.md), [Threat frameworks](Threat-Frameworks-STRIDE-ATTACK-ATLAS.md) and [Threat model exercise](Threat-Model-Exercise.md) carry the first real captures.
