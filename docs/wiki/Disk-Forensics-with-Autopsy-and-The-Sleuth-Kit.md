# Disk forensics with Autopsy and The Sleuth Kit: images, deleted files, hash sets and a first finding

<!-- BEGIN GENERATED PAGE NAV top: rewritten from docs/wiki/_nav.yaml by scripts/gen_wiki_nav.py; edit the manifest, not this block -->
[Home](Home.md) > [Security tools and threat modeling](Contents.md#security-tools-and-threat-modeling) > Disk forensics with Autopsy and The Sleuth Kit
<!-- END GENERATED PAGE NAV top -->

<!-- BEGIN GENERATED PAGE CONTENTS: rewritten from the page's own headings by scripts/gen_wiki_nav.py; edit the headings, not this block -->
**On this page:**

- [What you will be able to do](#what-you-will-be-able-to-do)
- [What the wiki already says (and the gap)](#what-the-wiki-already-says-and-the-gap)
- [What The Sleuth Kit and Autopsy are, and how they relate](#what-the-sleuth-kit-and-autopsy-are-and-how-they-relate)
- [Who maintains them, and the current versions](#who-maintains-them-and-the-current-versions)
- [Install](#install)
- [Disk images, and hashing first](#disk-images-and-hashing-first)
- [File systems at concept level](#file-systems-at-concept-level)
- [Deleted files and carving](#deleted-files-and-carving)
- [Hash sets and the NSRL](#hash-sets-and-the-nsrl)
- [Keyword search](#keyword-search)
- [Timeline](#timeline)
- [Web and registry artifacts](#web-and-registry-artifacts)
- [Reports](#reports)
- [Limits: what these tools do not do](#limits-what-these-tools-do-not-do)
- [How the free tools compare with commercial ones](#how-the-free-tools-compare-with-commercial-ones)
- [Free path: a practice image, the command line, then Autopsy](#free-path-a-practice-image-the-command-line-then-autopsy)
- [Build, break, detect, evade, defend](#build-break-detect-evade-defend)
- [Checkpoint](#checkpoint)
- [Common mistakes](#common-mistakes)
- [Claims register](#claims-register)
<!-- END GENERATED PAGE CONTENTS -->

Side page to the security tools lessons. Read it when someone says "pull an image of the disk" or "run it through Autopsy" and you want to know what that means, or when you want to learn disk forensics without paying for a tool. It covers the free pair: The Sleuth Kit (a set of command-line tools) and Autopsy (a graphical program built on top of it). Sibling forensics lessons are being written alongside this one: foundations of forensics (#474), memory forensics (#476), network and log forensics (#477) and forensic toolkits (#478). They are not linked here because they may not exist yet; this page stands alone.

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

> **Status: unverified draft. The Sleuth Kit commands were run; Autopsy itself was not installed or started.** On **2026-11-07** I ran, on one Linux machine (Parrot Security 7.4, Debian-based) with Debian's `sleuthkit` package version 4.12.1: `sha256sum`, `sfdisk`, `mformat`, `mcopy`, `mdel`, `mmls`, `fls -r`, `fls -r -d`, `fsstat`, `istat`, `icat`, `tsk_recover` (with and without `-e`), `img_stat`, `strings`, `ewfacquire` and `ewfverify` (libewf 20140816), all against a 64 MB practice image I built in that session. **Not run:** Autopsy 4.x (every Autopsy step is written from the official documentation and marked **est.**), anything on Windows or macOS, NTFS and ext4 images, carving with PhotoRec or `foremost`, `mactime` timelines (my run printed zeroed dates, see the exercise), hash set lookups, the downloadable practice images, and any commercial tool. Version and license facts were read from the pages in the [claims register](#claims-register) on **2026-11-07**. Trust what your terminal prints over what this page says.

> **Prerequisites.** A terminal ([The terminal and your first script](Terminal-and-Your-First-Script.md)). A clear idea of what a hash is ([Hashing, encryption and keys](Hashing-Encryption-and-Keys.md)); you will verify one before anything else. A Linux machine or a Linux VM for the exercise ([Virtual machines and hypervisors](Virtual-Machines-Hypervisors-Desktop-and-Datacenter-Options.md)); a throwaway VM is the better place to run any tool on files you did not make. About 2 hours for the reading and the exercise (est.). Disk needed for the exercise: about 70 MB (measured: my lab folder, with the image, an E01 copy and the recovered files, was 66 MB by `du -sh`), plus Autopsy itself.

> **Where this runs, and the rule.** Everything here is local and read-only against an image you made yourself. No network is used after the downloads. **Examine only your own devices or data you are explicitly authorized to examine.** Imaging and searching someone else's computer, phone or account without authority can be a crime in many places; this page is not legal advice, and a real case has rules about chain of custody, authority and evidence handling that a learner exercise does not.

## What you will be able to do

- Say what The Sleuth Kit and Autopsy are, how they relate, and what each is for.
- Verify a disk image with a hash before you open it, and say why you work on a copy.
- Read a partition layout and a directory listing from the command line (`mmls`, `fsstat`, `fls`).
- Show a deleted file, read its metadata and get its contents back (`istat`, `icat`, `tsk_recover`).
- Explain, at concept level, how NTFS, ext4 and FAT differ for a person looking for deleted data.
- Say what carving is and when it is the only thing left.
- Explain hash sets (including the NSRL), keyword search, timeline, and the web and registry artifact modules.
- State what these free tools do not do, and compare them fairly with commercial suites.
- Write a four-line finding from a known image.

## What the wiki already says (and the gap)

| Idea | Where it is today | The gap this page fills |
|---|---|---|
| Hashes as fingerprints, detecting a changed file | [Hashing, encryption and keys](Hashing-Encryption-and-Keys.md) | Why a forensic examiner hashes first, and what the hash proves about an image. |
| A throwaway machine to run unfamiliar tools in | [Virtual machines and hypervisors](Virtual-Machines-Hypervisors-Desktop-and-Datacenter-Options.md) | Using one as an examination workstation. |
| Typing commands, pipes and exit codes | [The terminal and your first script](Terminal-and-Your-First-Script.md) | Nothing; this page assumes it. |
| File integrity monitoring on a live host | [File integrity and alerting](File-Integrity-and-Alerting-Tripwire-AIDE-Wazuh.md) | After-the-fact examination of a disk, rather than watching one. |

## What The Sleuth Kit and Autopsy are, and how they relate

**The Sleuth Kit (TSK)** describes itself as "a collection of command-line tools and a C library for analyzing disk images and recovering files" (sleuthkit.org, read 2026-11-07). Each tool does one small job, and you chain them. **Autopsy** is "a graphical interface to The Sleuth Kit and other open source digital forensics tools" (the project's GitHub README, read 2026-11-07). It adds a case database, a set of automatic checks that run over an image (**ingest modules**), viewers (file tree, timeline, search results), tagging and reports.

The relationship, in one picture:

```text
  disk image (raw, E01 ...)
          |
   The Sleuth Kit library  <-- also used by other open and commercial tools
     |                    |
 command-line tools     Autopsy (Java GUI)
 mmls fsstat fls        case database, ingest modules,
 istat icat blkls       keyword index, timeline, reports
 tsk_recover
```

Why learn the command line when the GUI exists: the commands show you what the GUI is doing, they script well, and they are how you check a result a second way. Why learn the GUI when the commands exist: a case has thousands of files, and a viewer that shows pictures, web history and a timeline together is faster than reading listings.

The tools you will use in this lesson, by the job they do:

| Tool | Job |
|---|---|
| `mmls` | Lists the partitions in a disk image, with start sector and length. |
| `fsstat` | Describes one file system: type, sizes, volume label. |
| `fls` | Lists files and directories, including deleted names (`-r` recurses, `-d` shows only deleted). |
| `istat` | Shows the metadata of one file by its number: times, size, which sectors. |
| `icat` | Writes a file's contents, found by its number, to standard output. |
| `tsk_recover` | Copies files out of a file system; `-e` includes deleted ones that can be found. |
| `blkls` | Dumps unallocated blocks, which you can then search or carve. |
| `mactime` | Turns a "body file" of times into a timeline. |

## Who maintains them, and the current versions

All of this was read on **2026-11-07**; versions move, so check the pages.

| Item | What I read |
|---|---|
| Autopsy, newest release | **4.23.1**, published 2026-05-07 (GitHub releases); the download page also shows 4.23.1 |
| The Sleuth Kit, newest release | **4.15.0**, published 2026-04-15 ("Bug fixes", sleuthkit.org) |
| Autopsy license | Apache License, Version 2, with some bundled libraries under other open source licenses (README) |
| The Sleuth Kit license | Core code under the IBM Public License or the Common Public License; other utilities carry their own non-copyleft licenses; a trimmed copy of GNU `strings` is GPL 2 and "standalone and not part of the library" (licenses page) |
| Who maintains them | Sleuth Kit Labs, per the autopsy.com home page and sleuthkit.org; Brian Carrier leads (copyright notice 2003-2026) |

A short history, from primary pages only. The Sleuth Kit's own about page says it began as TASK, "The @stake Sleuth Kit", based on The Coroner's Toolkit; Autopsy began in March 2001 as a graphical interface to that toolkit; Basis Technology largely funded Autopsy 3, a complete rewrite. Sleuth Kit Labs' about page says it "spun out of Basis Tech in October 2023 as its own company," with Carrier as CEO, and that it "continues to support both commercial and open source projects, such as Autopsy." Sleuth Kit Labs also sells a separate commercial product, Cyber Triage; it is not needed for anything here.

Two oddities I found, so you do not trip on them. First, the autopsy.com home page links documentation for version 4.19.3 while its download page offers 4.23.1; the docs I read for features were the 4.22.0 set (the newest user-doc folder I could read, **est.** that a 4.23.x set exists). Treat a feature as current only if your installed version has it. Second, the Autopsy README says the program is designed to be cross-platform but "the current version is fully functional and fully tested only on Windows"; the README also mentions Windows XP, so that sentence is old. The download page offers a Windows MSI and a ZIP "to run on Linux and macOS" (page read 2026-11-07), and the Linux route needs The Sleuth Kit's Java package and Java 17 (Autopsy's `Running_Linux_OSX.md`, read 2026-11-07). Expect more friction on Linux and macOS than on Windows (**est.**).

## Install

**The Sleuth Kit alone (enough for most of this lesson).** On Debian-family Linux: `sudo apt install sleuthkit`. I installed it this way and `fls -V` printed `The Sleuth Kit ver 4.12.1`, which is behind 4.15.0, so a distribution package lags the project. Windows: the project publishes `sleuthkit-4.15.0-win32.zip` on its GitHub release page. macOS: **est.** a package manager or a build from source; not read.

**Autopsy on Windows.** Download the 64-bit MSI from the download page and run it; the README says the installer bundles its dependencies. Verify the download first (next section). The release page also lists `.asc` signature files beside each download, which are PGP signatures you can check if you have the project's key (**est.**: I did not locate or check the key).

**Autopsy on Linux.** The download page says: download the ZIP, install The Sleuth Kit's Java Debian package (it names `sleuthkit-java_4.14.0-1_amd64.deb`), and follow `Running_Linux_OSX.md` for the rest. That file says Autopsy needs Java 17, gives a prerequisites script for Ubuntu (`linux_macos_install_scripts/install_prereqs_ubuntu.sh`), and an `install_application.sh` script that takes `-z` for the zip, `-i` for the install folder and `-j` for the Java home. It also says to add `--nosplash` on the first run, because a window can hide behind the splash screen and make the program look stalled. I did not run any of it.

**A trap on Debian-family systems.** Parrot's and Debian's repositories carry a package called `autopsy`, version 2.24 when I looked (2026-11-07), described as a "graphical interface to SleuthKit". That is the old web-browser front end, not Autopsy 4. If you want the program the current documentation describes, install from the project's release page.

## Disk images, and hashing first

A **disk image** is a file that holds the bytes of a whole drive or partition. Examiners work on images, not the original, for two reasons: reading the original changes it (a mounted file system updates access times), and you want to be able to start over.

| Format | What it is |
|---|---|
| Raw (`.dd`, `.img`, `.raw`) | The bytes, one for one, with nothing added. Simple, and every tool reads it. Size equals the disk's size. |
| E01 (EnCase evidence file, from the libewf family) | A container that stores the bytes compressed, with case notes and a hash stored inside. Often split into segments. |

Autopsy accepts raw (`.img`, `.dd`, `.raw`, `.bin`), raw split images (`.001`, `.aa`), EnCase E01, VMware VMDK and VHD or VHDX files (data source documentation, 4.22.0, read 2026-11-07).

**Hash before you look.** Compute a hash of the image the moment you have it and write it down. Later, recompute it; if it matches, the image has not changed since. A hash says "these bytes are the same bytes." It does not say the image came from the right drive, that the drive was not altered before imaging, or that nobody tampered with both the image and the written hash ([Hashing, encryption and keys](Hashing-Encryption-and-Keys.md) covers why). Use SHA-256; MD5 is still common in forensic reports for historical reasons (Autopsy's hash lookup uses MD5 for its set matching, below).

Two cautions from my run:

- **Make the original read-only.** For a real drive, a hardware write blocker is the standard answer; software read-only mounting is weaker. This page uses a file you built, so there is no original to protect (**est.** for the write-blocker statement, general practice).
- **E01 and TSK 4.12.1 on my machine.** I made an E01 with `ewfacquire` and checked it with `ewfverify` (it reported `SUCCESS` and matched MD5 `815c9131c04ccbf90a37233b5331104b`). Then `fls` pointed at the E01 crashed with a segmentation fault, rc 139, on Debian's `sleuthkit` 4.12.1 with libewf 20140816. Pointing `fls` at an E01 made with a second EWF format printed nothing. I did not diagnose it; an old libewf and a distribution package are my suspects (**est.**). The practical rule: if a tool dies on an E01, convert to raw (`ewfexport`, not run by me) or mount it with `ewfmount` (not run), and try again; do not trust a silent empty listing.

## File systems at concept level

You only need enough to know why a deleted file is findable on one and not on another. TSK supports "NTFS, FAT, ExFAT, APFS, UFS 1, UFS 2, EXT2FS, EXT3FS, Ext4, HFS, ISO 9660, and YAFFS2" and the partition schemes "DOS partitions, BSD partitions (disk labels), Mac partitions, Sun slices (Volume Table of Contents), and GPT disks" (sleuthkit.org file system page, read 2026-11-07).

| Question | FAT (and FAT32) | NTFS | ext4 |
|---|---|---|---|
| Where it is | USB sticks, cameras, SD cards, boot partitions | Windows system and data drives | Most Linux installs |
| Where a file's name and facts live | A directory entry; the first byte of the name is overwritten with a marker on delete | A record in the Master File Table, with times and attributes | An inode, separate from the directory entry that names it |
| What delete does (est.) | Marks the entry and frees the clusters; data stays until reused | Marks the MFT record unused; data and record often stay for a while | Frees the inode and blocks; ext4 may clear block pointers, which makes recovery harder |
| Times kept | Created, written, accessed (date only) | Four times in two attribute sets | Modified, accessed, changed, plus creation time on newer versions |

The statements in the "what delete does" row are general knowledge (**est.**) except the FAT one, which my run showed (below). Whether any one deleted file survives depends on how much was written since, and on SSD behavior I did not test.

What I saw on FAT32: after deleting `docs/oops.txt`, `fls` listed `* 22: _ops.txt`. The first character of the name was overwritten with a marker, so the file shows as `_ops.txt`, yet `icat` still printed its full contents. That marker byte is the whole of "FAT delete" for the name; the data was untouched.

## Deleted files and carving

There are two different situations, and mixing them up is the commonest beginner mistake.

1. **The file's record is still there.** The name and the pointer to the data are intact or partly intact. `fls -r -d` shows the name, `istat` shows the sectors, `icat` returns the contents. This is *recovering by metadata* and it is exact.
2. **The record is gone, but the data is still on the disk.** Nothing says where the file was. A **carver** scans unallocated space for the start-of-file signatures of known types (a JPEG begins with a known byte pattern) and cuts out what follows. This is *carving*. It finds pictures and documents without names, dates or folders, and it fails on a file that was split into pieces in different places on the disk.

Autopsy's carving is the **PhotoRec Carver Module**: it "carves files from unallocated space in the data source and sends the files found through the ingest processing chain." For it to run, "Process Unallocated Space" must be selected; custom signatures cannot be used with the "Carve only the specified types" option (documentation, read 2026-11-07). Recovered files appear under `$CarvedFiles` (**est.**, from a search summary, not a page I opened). One more limit from a search result: a source comment in an older version says the module worked on Windows only; I could not confirm the current state on Linux (**est.**).

I did not carve anything. My practice image holds text files, which the common carvers do not target, so a carving exercise needs a different image (for example the `nps-2009-canon2` camera set in the exercise section).

## Hash sets and the NSRL

A **hash set** is a list of file hashes with a meaning attached. Autopsy's Hash Lookup module "calculates MD5 hashes and checks them against hash sets" to label files; SHA-256 is also calculated but not used for set lookups (documentation, read 2026-11-07). Sets come in kinds:

- **Known** files "can be safely ignored", such as operating system and application files. Ignoring them "can greatly reduce image analysis time."
- **Notable** (known bad) files "should raise awareness", such as malware or contraband.
- **No change** files only tell you something about the system.

The **NSRL** (National Software Reference Library, run by NIST) is the standard "known" set. NIST describes its Reference Data Set as "a collection of digital signatures of known, traceable software applications," says it includes some hashes of applications that may be malicious (steganography tools, hacking scripts) and none for illicit data such as child abuse images; the page was updated 2026-07-31 (read 2026-11-07). Autopsy treats an NSRL match as "known", not "good": a hit means "this file is in a catalog of known software", not "this file is harmless." To use it, the documentation says to download the Autopsy-format NSRL index from the Autopsy SourceForge NSRL page, unzip it, then go to Tools, Options, Hash Sets, Import Database. I did not do this (**est.** that the steps still hold on 4.23.1).

## Keyword search

Autopsy's Keyword Search module indexes text and lets you search it. The documentation says each keyword is exact, substring or regular expression, and an index built with Solr "can significantly slow down the ingest speed for large data sources and cases"; the alternative, in-line search, roughly halves ingest time but needs every search term chosen before ingest and does not allow ad hoc search afterward. By default it looks for English text encoded as UTF-8 or UTF-16. For files it cannot parse, it falls back to extracting strings, which "will not extract text strings from encrypted files." OCR is optional and "the results are not perfect." Regular expressions "can potentially take a long time to complete."

On the command line the poor person's version is `strings -a -t d image | grep word`, which prints the byte offset of each hit. In my run it found `DELETED-MARKER` at byte offset 2087424. Divide by 512 to get sector 4077; subtract the partition's start (2048) to get sector 2029 inside the file system, which is the sector `istat` listed for the deleted file. That check lines up a keyword hit with a file.

## Timeline

Autopsy's Timeline turns artifacts into time-stamped events. Sources the documentation names: file system times (modified, accessed, created, changed), web activity (downloads, cookies, bookmarks, history, searches, form data) and miscellaneous events (messages, recent documents, installed programs, EXIF data, attached devices, registry data). It has a Counts view (a stacked bar chart of activity per period), a Details view (events clustered by description) and a List view. Since Autopsy 4.13 the events are built during ingest, so the relevant ingest modules must have run; opening Timeline during ingest shows incomplete data.

The command-line route is `fls -m / -r image > body.txt` then `mactime -b body.txt`. My run produced a body file and `mactime` printed lines, but every date came out as `0000-00-00`, so I cannot show you a working command-line timeline from this image (**not verified**; the cause could be my image's timestamps or my invocation, and I did not chase it).

Mind the limits of file times: a copy changes them, a program can set them, and a clock can be wrong. A time is a lead, not a fact.

## Web and registry artifacts

The **Recent Activity** ingest module "extracts user activity as saved by web browsers (including web searches)," covers installed programs and the operating system, and "runs Regripper on the Registry hive." The **registry** is Windows' settings database, stored in files called hives; it records things like installed programs, USB devices that were attached and recently opened files. The documentation's page for the module says results cover "the last seven days of usage" and does not name the browsers it supports. I read that as measured from the newest activity on the system, not from today, but I did not test it (**est.**). Check the module page for your version before you tell a report's reader what was covered.

None of this applies to my practice image, which has no operating system. These modules matter on an image of a Windows computer; the practice images named below include one (`nps-2009-ntfs1` is NTFS but is a file system test image, not a user's computer; I did not open it).

## Reports

Autopsy's Reports menu produces, per the documentation: an HTML report, an Excel report, a Files - Text list, Google Earth KML from GPS data, a TSK body file (for `mactime`), a CASE-UCO JSON file for one data source, and a Portable Case containing only tagged or interesting items. The HTML report can include all results or only tagged ones. The habit that makes a report worth reading is tagging as you go: tag the three or four items that matter, add a comment saying why, and report only those.

## Limits: what these tools do not do

- **They do not decrypt a locked disk.** Keyword search "will not extract text strings from encrypted files," and an encrypted volume looks like random bytes. Autopsy has an Encryption Detection module (4.22.0 docs) that flags it, not breaks it.
- **They do not read live memory or network traffic.** That is the job of the memory, network and log lessons in this series.
- **Large images are slow.** The documentation says a full-text index slows ingest on big data sources. Autopsy "builds an embedded database with an entry for each file," and the source "must remain accessible for the duration of the analysis." How slow, on what hardware, I did not measure (**est.** hours to days for terabyte drives).
- **Deleted does not mean recoverable.** Overwritten data is gone. On some media, the drive itself may discard freed blocks (**est.**, general knowledge for SSDs).
- **Mobile and cloud are partial.** The 4.22.0 documentation lists Android and iOS analyzer modules; I did not test what they extract.
- **Findings need a human.** A tool tells you a file exists, was opened, was deleted. It does not tell you who sat at the keyboard.
- **Platform support has been uneven** (see "Who maintains them").

## How the free tools compare with commercial ones

The paid suites (EnCase, FTK, X-Ways Forensics, Magnet AXIOM and others, **est.** names only; I did not read their pages) cover the same ground: images, file systems, search, timeline, reports. I am not recommending or rating any of them. What decides the choice is usually not the feature checklist:

- **Cost and licensing.** TSK and Autopsy are free and open source (licenses above). Commercial suites charge; I did not read their prices.
- **Court and customer expectations.** Some employers and jurisdictions expect a named tool or a tool tested by a recognized program. NIST's CFTT program tests forensic tools (its deleted-file-recovery work appears in the search results I read), but I did not check whether it has tested Autopsy or any other product (**not verified**).
- **Mobile, cloud and chat parsing.** Commercial suites compete on how many apps they parse. Whether Autopsy's modules match them is a question to test with your own data.
- **Speed on large cases.** Not measured by me.
- **Cross-checking.** The Sleuth Kit's library sits inside many other tools (Sleuth Kit Labs' about page says "many other commercial tools"). Running the same image through two tools and getting the same listing is a good habit regardless of price.

## Free path: a practice image, the command line, then Autopsy

Cost: $0. You work on an image you build yourself, so the contents are known. A freely licensed public image is an option; read its license first.

### Pick an image

**Option A (what I ran): build your own.** It takes a minute and has a deleted file whose contents you know.

**Option B: a public practice image.** I read two sources and did not download either image.

- **Digital Corpora** (digitalcorpora.org, read 2026-11-07). Its terms say original content "are made available under the CC0 license" and that material explicitly claiming a copyright, "including copyrighted software and other original materials located in disk images," is not covered. Its page for the NPS test images says "The NPS-created data in these images is public domain and free of any copyright restriction", and that some corpora include copyrighted Windows material. Entries I read, with descriptions from the page: `nps-2009-canon2` (camera images, "file recovery and carving tests"), `nps-2009-ntfs1` (NTFS with fragmented, compressed and encrypted files, key provided), `nps-2009-casper-rw` (an ext3 file system). The page gives no file sizes and I did not find a hash on it. The download hosts redirect, and I did not get a file listing, so file sizes and checksums are **unverified**. Some of the "real" corpora there need research approval; do not use those.
- **NIST CFReDS** (the deleted file recovery test images, DFR-01, on the CFReDS archive site). The archive page lists FAT, exFAT, NTFS, EXT and OS X images of "Recover one non-fragmented file", compressed with bzip2 (decompress with `bunzip2`), and says the images "are not for testing file carving tools." The archive page I read contained no license or terms text, and the live portal needs JavaScript, so I could not read its terms. Treat the license of those images as **unverified** until you read the current terms yourself.

If you use either, do the hash step on the downloaded file, compare to a hash the host publishes if there is one (if none, record yours and say so in your finding), and run everything below against that image instead.

### Exercise 1: build the practice image (Linux)

1. **Predict.** If you delete a file from a FAT disk, is its content gone from the image?
2. **Do.** The Debian packages are `sleuthkit`, `mtools`, `fdisk` (for `sfdisk`) and `libewf-tools`; I did not record each package name from my machine (**est.** for names).

   ```bash
   mkdir -p ~/forensics-lab && cd ~/forensics-lab
   truncate -s 64M lab.dd
   printf 'label: dos\nstart=2048, type=c\n' > part.txt
   sfdisk lab.dd < part.txt
   mformat -i lab.dd@@1048576 -F -v LABDISK ::
   echo "Meeting notes: the practice file is harmless." > notes.txt
   echo "DELETED-MARKER secret-looking but fake text, safe." > oops.txt
   head -c 3000 /dev/urandom | base64 > filler.txt
   mmd -i lab.dd@@1048576 ::docs
   mcopy -i lab.dd@@1048576 notes.txt ::docs/notes.txt
   mcopy -i lab.dd@@1048576 filler.txt ::filler.txt
   mcopy -i lab.dd@@1048576 oops.txt ::docs/oops.txt
   mdel -i lab.dd@@1048576 ::docs/oops.txt
   ```

3. **Check.** `ls -l lab.dd` shows 67108864 bytes. All of this ran on my machine with no error. A 32 MB image did not work for me: `mformat -F` (FAT32) produced no usable file system on a 32 MB image, so I used 64 MB. If you move to FAT16 or another size, the numbers below change.
4. **Undo.** `rm -r ~/forensics-lab` (and the `rec` folders you make later).

### Exercise 2: hash the image first

```bash
cd ~/forensics-lab
sha256sum lab.dd > lab.dd.sha256
cat lab.dd.sha256
sha256sum -c lab.dd.sha256
```

My run printed `86fd49c0f0e4c43b319bf5a81eab0b21a2241c6186409dad31e9cc1678fbfe99  lab.dd` and then `lab.dd: OK`. **Your hash will differ**: `mformat` stamps a volume ID and times from the moment you run it, so two builds of "the same" image hash differently. That is the point of the step: the hash belongs to your copy. From here on, run `sha256sum -c lab.dd.sha256` before and after your work; both should say OK, because every command below only reads.

### Exercise 3: the command line

1. **Predict.** How many partitions does the image have, and will the deleted file appear in a directory listing?
2. **Do.**

   ```bash
   mmls lab.dd
   fsstat -o 2048 lab.dd | head -8
   fls -r -o 2048 lab.dd
   fls -r -d -o 2048 lab.dd
   istat -o 2048 lab.dd 22
   icat -o 2048 lab.dd 22
   icat -o 2048 lab.dd 21
   mkdir rec && tsk_recover -o 2048 lab.dd rec
   find rec -type f
   strings -a -t d lab.dd | grep DELETED
   ```

3. **Check.** `-o 2048` is the partition's start sector from `mmls`. On my run (TSK 4.12.1): `mmls` showed one FAT32 partition starting at sector 2048 (`Win95 FAT32 (0x0c)`, length 129024 sectors). `fls -r` listed `d/d 4: docs`, `r/r 21: notes.txt`, `r/r * 22: _ops.txt`, `r/r 5: filler.txt`. The asterisk marks the deleted entry. `fls -r -d` printed only `r/r * 22: docs/_ops.txt`. `istat` printed `Not Allocated`, `Size: 51`, `Name: _ops.txt`, and sector 2029. `icat ... 22` printed `DELETED-MARKER secret-looking but fake text, safe.` and `icat ... 21` printed the notes line. `tsk_recover` without `-e` printed `Files Recovered: 1` and wrote `rec/docs/_ops.txt`; with `-e` it wrote all three files. `strings` found the marker at byte offset 2087424.
4. **Undo.** `rm -r rec`; nothing was changed in `lab.dd`. Run `sha256sum -c lab.dd.sha256` to prove it.

### Exercise 4: open it in Autopsy (written from reading, not run)

**est.** throughout. The documentation's steps, as I read them:

1. Install Autopsy (above). Start it and create a new case (a case name and a folder). A case "must be open before you add any data source."
2. Add Data Source, choose "Disk Image or VM File", pick `lab.dd`. Choose ingest modules: Hash Lookup, File Type Identification, Keyword Search and Recent Activity are enough for this image; PhotoRec Carver needs "Process Unallocated Space" selected. Run.
3. In the tree, open the data source, then the file system, and find `docs`. Deleted files should show in the Deleted Files section of the tree. Open the deleted file and read its content in the viewer.
4. Run a keyword search for `DELETED-MARKER` (an ad hoc search needs the text to be added to the Solr index at ingest, per the documentation).
5. Open Timeline and look at the file system events.
6. Tag the deleted file, then generate an HTML report with tagged results only.
7. Undo: close the case, delete the case folder. `lab.dd` is untouched; recheck its hash.

Compare what Autopsy says with what `fls` and `icat` said. A difference is a finding about the tools.

### Exercise 5: write the finding (four lines)

Use this shape and fill it from what you ran:

```text
Item:      lab.dd, sha256 <your hash>, built <date> on <OS and TSK version>.
Found:     deleted file docs/_ops.txt (directory entry 22), 51 bytes, still readable.
How:       fls -r -d, then icat; keyword hit at byte 2087424 matched sector 2029.
Limit:     name's first character lost on FAT delete; times and original name not recoverable beyond that.
```

Do not write that the user "hid" or "tried to destroy" anything; a deleted file is evidence that it was deleted, and the rest is inference.

## Build, break, detect, evade, defend

**Build.** The image and the hash. **Break.** Change one byte of a copy (`cp lab.dd lab2.dd`; use `printf '\x00' | dd of=lab2.dd bs=1 seek=100000 conv=notrunc`) and run `sha256sum lab2.dd`: the hash no longer matches `lab.dd.sha256`. Delete `lab2.dd` afterward; I did not run this break step (**est.**). **Detect.** A mismatch shows a changed image; `fls -r -d` shows deleted names. **Evade, in words only.** Someone trying to hide data can overwrite it, encrypt the disk, use a tool that wipes free space, or set false file times. This page shows no technique. **Defend.** If you want your own deleted files to be unrecoverable, delete them with the drive's full-disk encryption on and keys destroyed, or sanitize the media with a method suited to it; ordinary delete is not enough (**est.**).

### Flip the board

**The reviewer.** A report says: "Autopsy recovered 40 deleted files from the suspect's laptop. The laptop was imaged using Autopsy running on the suspect's laptop while it was powered on. The hash of the image was computed after the analysis." Find at least five problems.

<details>
<summary>What to find</summary>

1. Imaging a live system changes the original while you read it; a write-blocked or powered-off acquisition is the norm.
2. The hash was taken after analysis, so it proves nothing about the image at acquisition time.
3. Running Autopsy on the suspect's machine changes the evidence (files, logs, memory).
4. "Recovered" is not "was deleted by the user"; no statement of how many were system files or hash-known files.
5. No version of the tool, no command or module list, no second tool to cross-check.
6. No statement of authority to examine the laptop.
7. No chain of custody.

</details>

**The auditor.** A manager says "we only need to keep the Autopsy report, not the image." What do you lose? (The ability to re-run, to answer a question nobody asked yet, and to show the report matches the evidence; keep the image and its hash for as long as your policy and the law require.)

## Checkpoint

Without looking back: say how Autopsy and The Sleuth Kit relate; give the order of "hash, then examine"; say what the asterisk in `fls` means and what `icat` needs; explain the difference between recovering by metadata and carving; say what a "known" hash match means for the NSRL; name two things these tools do not do.

## Common mistakes

| Symptom or belief | What is really true | What to check |
|---|---|---|
| "I worked on the original drive, it's fine" | Reading it changed it, and you cannot show it did not | Image first, write blocker for real drives, hash |
| "The hash matches, so the evidence is good" | It proves the bytes did not change since the hash; not where they came from | State what the hash proves, no more |
| `fls` says "Cannot determine file system type" | Wrong offset or the image has a partition table | `mmls` first, then `-o <start sector>` |
| `fls` returns nothing or crashes on an E01 | A library or build problem is possible | Convert to raw, retry, compare |
| `apt install autopsy` gave me a web page | That is the old version 2 front end | Install Autopsy 4 from the release page |
| "A deleted file with a changed first letter is a different file" | On FAT only the first byte of the name is replaced | Look at `istat` and the contents |
| "No hits for the keyword, so it was never there" | The index may exclude that language, file type or encrypted data | Check settings; try `strings` |
| "A known-hash match means safe" | It means listed in a catalog of software | Read the set's description |
| Timeline dates are all zeros | A body-file or invocation problem (I hit it too) | Compare with `istat` times |

## Claims register

Retrieved 2026-11-07 with read-only requests unless stated. "Read" means I read the page text through a fetch tool that summarizes pages, so quoted wording comes from that summary; "Observed" means I ran it on my machine.

| Claim | Source | Status |
|---|---|---|
| Autopsy is the "premier end-to-end open source digital forensics platform", built by Sleuth Kit Labs, led by Brian Carrier | [autopsy.com](https://www.autopsy.com/) | Read |
| Newest Autopsy release 4.23.1, published 2026-05-07; Windows MSI and ZIP assets | [Autopsy releases on GitHub](https://github.com/sleuthkit/autopsy/releases) (via the GitHub API's latest-release record) | Read |
| Newest Sleuth Kit release 4.15.0, published 2026-04-15, Windows zip and source tarball | [Sleuth Kit releases on GitHub](https://github.com/sleuthkit/sleuthkit/releases), [sleuthkit.org](https://sleuthkit.org/) | Read |
| Download page: Windows MSI; ZIP for Linux and macOS; Linux needs `sleuthkit-java_4.14.0-1_amd64.deb`; no system requirements stated | [autopsy.com download](https://www.autopsy.com/download/) | Read |
| Autopsy README: Apache License 2; "graphical interface to The Sleuth Kit"; "fully tested only on Windows"; mentions JRE 17 | [Autopsy repository](https://github.com/sleuthkit/autopsy) | Read |
| Linux install: Java 17, prerequisites script, `install_application.sh -z -i -j`, `--nosplash` | [Running_Linux_OSX.md](https://github.com/sleuthkit/autopsy/blob/develop/Running_Linux_OSX.md) (develop branch) | Read |
| Sleuth Kit: command-line tools and C library; Brian Carrier named as maintainer in the repo README; tool list | [sleuthkit.org](https://sleuthkit.org/), [Sleuth Kit repository](https://github.com/sleuthkit/sleuthkit) | Read |
| TSK licenses: IBM Public License or Common Public License for core code; trimmed `strings` GPL 2 | [TSK licenses](https://sleuthkit.org/sleuthkit/licenses.php) | Read |
| TSK file systems and volume systems list | [TSK file systems](https://sleuthkit.org/sleuthkit/desc.php) | Read |
| History: TASK from @stake, Autopsy from March 2001, Basis funded version 3 | [sleuthkit.org about](https://sleuthkit.org/about.php) | Read |
| Sleuth Kit Labs spun out of Basis in October 2023; supports Autopsy; toolset in many commercial tools | [Sleuth Kit Labs about](https://www.cybertriage.com/about/) | Read |
| Supported image formats (raw, split, E01, VMDK, VHD/VHDX); data source must remain accessible | [Autopsy 4.22.0 data sources](https://sleuthkit.org/autopsy/docs/user-docs/4.22.0/ds_page.html) | Read |
| Hash lookup: MD5 for sets, SHA-256 computed, known / notable / no change; NSRL import steps | [Autopsy 4.22.0 hash databases](https://sleuthkit.org/autopsy/docs/user-docs/4.22.0/hash_db_page.html) | Read |
| NSRL contents description; page updated 2026-07-31 | [NIST NSRL](https://www.nist.gov/itl/ssd/software-quality-group/national-software-reference-library-nsrl) | Read |
| Keyword search: Solr versus in-line, languages, OCR, regex limits | [Autopsy 4.22.0 keyword search](https://sleuthkit.org/autopsy/docs/user-docs/4.22.0/keyword_search_page.html) | Read |
| Timeline sources, views, events built during ingest since 4.13 | [Autopsy 4.22.0 timeline](https://sleuthkit.org/autopsy/docs/user-docs/4.22.0/timeline_page.html) | Read |
| Recent Activity: web activity, installed programs, RegRipper on hives, "last seven days" | [Autopsy 4.22.0 Recent Activity](https://sleuthkit.org/autopsy/docs/user-docs/4.22.0/recent_activity_page.html) | Read |
| Report formats, tagged-only HTML reports | [Autopsy 4.22.0 reporting](https://sleuthkit.org/autopsy/docs/user-docs/4.22.0/reporting_page.html) | Read |
| PhotoRec Carver: carves unallocated space, needs "Process Unallocated Space", custom signature limit | [Autopsy 4.22.0 PhotoRec carver](https://sleuthkit.org/autopsy/docs/user-docs/4.22.0/photorec_carver_page.html) | Read |
| `$CarvedFiles` heading; older-version "Windows only" source comment | Search result summaries (4.7.0 docs, 4.9.1 source) | Search summary only, **est.** |
| Digital Corpora terms: original content CC0; copyrighted material in images excluded; NPS data public domain | [Digital Corpora terms](https://digitalcorpora.org/terms-of-use/), [disk images](https://digitalcorpora.org/corpora/disk-images/) | Read |
| CFReDS DFR-01 images: FAT, exFAT, NTFS, EXT, OS X; bzip2; "not for testing file carving tools"; no terms text on the archive page | [CFReDS archive DFR page](https://cfreds-archive.nist.gov/dfr-test-images.html) | Read; license unverified |
| Debian `autopsy` package version 2.24, "graphical interface to SleuthKit"; `sleuthkit` 4.12.1 | `apt-cache show autopsy`, `dpkg -l` on my machine | Observed |
| TSK commands, outputs and offsets in the exercise; FAT delete shows `_ops.txt`; `icat` returns the content | My run on the Parrot machine, 2026-11-07 | Observed |
| `ewfverify` success on my E01; `fls` segmentation fault on it | My run | Observed |
| Imaging with a write blocker is standard; commercial tool names; SSD behavior; file system delete behavior row | General knowledge | **est.** |

Not verified, plainly: Autopsy running on any platform; the Linux install steps; NTFS and ext4 behavior; carving; the NSRL import; any Windows or macOS step; the public practice images (not downloaded, sizes and hashes unknown, CFReDS license unread); commercial tool features; and everything marked **est.**

Next: continue on the [Reading order](Reading-Order.md) page.

<!-- BEGIN GENERATED PAGE NAV bottom: rewritten from docs/wiki/_nav.yaml by scripts/gen_wiki_nav.py; edit the manifest, not this block -->
Where you are: [Home](Home.md) > [Security tools and threat modeling](Contents.md#security-tools-and-threat-modeling) > Disk forensics with Autopsy and The Sleuth Kit

In this group: [Security tools and threat modeling](Contents.md#security-tools-and-threat-modeling), 8 pages

- Also here: [Threats in plain words](Threats-in-Plain-Words.md) / [Security tools: Nmap, OpenVAS, Burp, Metasploit](Security-Tools-Basics-Nmap-OpenVAS-Burp-Metasploit.md) / [Email security](Email-Security-DNS-Gateways-and-API-Driven-Protection.md) / [Threat model exercise](Threat-Model-Exercise.md) / [Threat Dragon exercise](Threat-Dragon-Exercise.md) / [Threat frameworks: STRIDE, ATT&CK, ATLAS](Threat-Frameworks-STRIDE-ATTACK-ATLAS.md)
- Digital forensics: [Memory forensics with Volatility 3](Memory-Forensics-Acquiring-RAM-and-Analyzing-It-with-Volatility-3.md) / **Disk forensics with Autopsy and The Sleuth Kit**

Related pages:

- [Memory forensics with Volatility 3](Memory-Forensics-Acquiring-RAM-and-Analyzing-It-with-Volatility-3.md)
- [Threat frameworks: STRIDE, ATT&CK, ATLAS](Threat-Frameworks-STRIDE-ATTACK-ATLAS.md)
- [Threat Dragon exercise](Threat-Dragon-Exercise.md)
- [Threat model exercise](Threat-Model-Exercise.md)
<!-- END GENERATED PAGE NAV bottom -->
