# Windows, Active Directory and macOS in the enterprise

Side page to the start-from-zero pages. Read it after [The terminal and your first script](Terminal-and-Your-First-Script.md) and [Enterprise identity: SSO, SAML and OIDC](Enterprise-Identity-SSO-SAML-OIDC.md) if your first job (or the job you want) is helpdesk, desktop support or systems administration, where the machines are Windows laptops and a domain, not Linux droplets. It sits beside [Linux for enterprise beginners](Linux-for-Enterprise-Beginners.md), which covers the other half of the fleet. This project itself builds Linux machines in the cloud and does not run a Windows domain, so this page is about the skills around the project, not about the project. Next: [Enterprise identity and secrets at scale](Enterprise-Identity-and-Secrets-at-Scale.md).

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

> **Status: vendor facts read on 2026-10-22; the fake-data exercise was run once on Linux; everything that touches Windows or macOS was not run.** On **2026-10-22** I read the Microsoft, Apple and MITRE pages named in the [claims register](#claims-register) with read-only requests, including Microsoft's evaluation download pages. I ran the Bash commands of Exercise 7 on Linux against fake data and pasted what came back. I did **not** run any PowerShell (there is no PowerShell and no Windows machine in my environment), and I did not run anything on a Mac. Every Windows or macOS command below is written from Microsoft's or Apple's documentation or general knowledge and marked **est.** (estimate) where I am least sure; trust what your own terminal prints over this page. I could **not** read the evaluation license terms (the agreement you accept at download or install), so whether an evaluation copy may be used for anything beyond testing and learning is **unverified** here; read the terms before you rely on it for anything else. No price appears on this page.

> **Prerequisites.** [The terminal and your first script](Terminal-and-Your-First-Script.md) (what a shell, a pipe and an exit code are) and [Enterprise identity: SSO, SAML and OIDC](Enterprise-Identity-SSO-SAML-OIDC.md) (what a directory, a group and single sign-on are). [Hashing, encryption and keys](Hashing-Encryption-and-Keys.md) helps for one exercise. About four hours for the reading and the free exercises (est.); the optional virtual-machine path adds about three hours (est.). The reading and the exercises are free and always will be. The optional path uses your own computer and a free evaluation download (checked below), not a cloud bill.

## What you will be able to do

- Say why so many organizations run Windows on the desktop and a Windows directory behind it, without needing a market-share number.
- Explain **domain**, **domain controller**, **user**, **group**, **organizational unit (OU)** and **Group Policy** in plain words, and say what **Active Directory** and **Microsoft Entra ID** each are and how they differ.
- Say, at concept level, what **Kerberos** and **NTLM** do and why an administrator wants the first and fewer of the second.
- Do the five everyday PowerShell actions of a Windows administrator, read-only: list users, check a service, read the event log, check the firewall, and hash a file. Know the Mac or Linux equivalent of each.
- Say what a Mac does for device management (enrollment, configuration profiles, the keychain) and where it differs from Windows and Linux.
- Explain why a shared local administrator account is a risk, what tiering and least privilege mean for a directory, and which events a defender watches.
- Run a build, break, detect, evade, defend loop on a fake group-membership report, and know how to do it in a disposable evaluation virtual machine.

## Why most enterprises are Windows-first

The honest answer is history and ecosystem, not that Windows is better. I do not give a market-share figure because I did not read a primary source for one (**est.**: Windows is the common desktop operating system at large organizations, which you will confirm on your first day at work). Four reasons stack up:

1. **The directory came with it.** Microsoft introduced Active Directory Domain Services in Windows 2000, so that an organization could manage many systems with one identity per user (Microsoft's own comparison page says this). Once a company has one account that opens the laptop, the file share, the printer and the email, moving away from it is expensive.
2. **Central management is built in.** Group Policy (below) lets one administrator set a rule once and have thousands of computers follow it. That is the feature that made large fleets affordable to run.
3. **Software and habits.** Office suites, line-of-business applications, and decades of vendor tools target Windows first (**est.**). People are trained on it.
4. **One vendor, one support contract.** Operating system, directory, email, device management and endpoint security can come from one supplier (**est.**; this is a business reason, not a technical one).

None of that makes Windows-first the right choice for every company. Startups often skip the domain and run on cloud identity and Macs; engineering teams run Linux. Expect a mix, and expect the Windows part to be the part nobody documented well.

## First, the words

A **workgroup** is the default for a home computer: each machine keeps its own list of users, and there is no central boss. A **domain** is the other model: a group of computers and users that share one central directory and one set of rules, run by administrators. A computer **joins** a domain, and after that a person can sign in to it with a domain account that the central directory vouches for.

| Word | Plain meaning |
|---|---|
| **Active Directory Domain Services (AD DS)**, usually just "Active Directory" or "AD" | Microsoft's directory service. Microsoft describes it as making network resource data available to authorized network users and administrators, and as integrating security through sign-in authentication and access control to objects in the directory. |
| **Domain controller (DC)** | A server that runs AD DS and answers sign-in requests. Microsoft says that all domain controllers in a domain replicate and hold a complete copy of the directory data for that domain, and that a change on one is copied to the others. An organization runs more than one so that a single failure does not lock everyone out (**est.**). |
| **Domain** | The boundary of one directory: its users, groups and computers, with a name such as `corp.example.com` (a made-up name; `example.com` is reserved for documentation). |
| **Forest** | A group of one or more domains that share a schema and trust each other. A forest is the real security boundary in AD, not the domain (**est.**; I could not read Microsoft's definition for this page). |
| **User, computer, group** | The common **objects** in the directory. A computer has an account in the directory too, which is why a machine can be "trusted". A **group** is a named set of accounts; permissions are given to groups, not to people one at a time ([Groups, roles and mapping people to access](Enterprise-Identity-SSO-SAML-OIDC.md#groups-roles-and-mapping-people-to-access)). |
| **Organizational unit (OU)** | A folder inside the directory for organizing users and computers. Microsoft's Group Policy page calls an OU "the lowest-level AD container to which you can assign Group Policy settings", which is why OUs are designed around who needs which policy. |
| **Group Policy Object (GPO)** | A named bundle of settings that can be linked to a site, a domain or an OU. Microsoft describes it as a virtual collection of policy settings, security permissions and scope of management that you can apply to users and computers in AD. |
| **Kerberos** and **NTLM** | The two ways Windows proves who you are to a service on the network. Both are explained below. |
| **Microsoft Entra ID** | Microsoft's cloud identity service (see the comparison below). It is a different tool with a different job, not a copy of Active Directory running in the cloud. |

A picture of a small domain, in words:

```text
corp.example.com                      (one domain, made-up name)
  Domain controllers: DC-A, DC-B      (copy the directory to each other)
  OU: Staff
      OU: Sales        <- GPO "Sales desktop rules" is linked here
      OU: Engineering
  OU: Servers
  OU: Admin accounts   <- people's separate privileged accounts live here
  Groups: Domain Admins (powerful), Sales, Engineering, Helpdesk
```

A new hire, in practice: an administrator creates the user in the right OU, adds the user to groups, and the laptop (a computer object in a laptop OU) picks up the matching Group Policy the next time it starts. The joiner, mover and leaver steps are the same ones in [The identity lifecycle](Enterprise-Identity-SSO-SAML-OIDC.md#the-identity-lifecycle-joiner-mover-leaver).

DNS is the quiet dependency: domain computers find a domain controller by looking up names in DNS, so a broken DNS server can look exactly like a broken domain (**est.**; this is the single most common helpdesk surprise). The basics are in [How a web request works](How-a-Web-Request-Works.md).

## Group Policy: one rule, many computers

Group Policy settings live in a GPO, and a GPO has no effect until it is **linked** to a place in the directory. Microsoft's processing page gives the order: the local GPO first, then GPOs linked to sites, then GPOs linked to the domain, then GPOs linked to OUs, with parent OUs before child OUs. Where two settings conflict, the later one wins by default. Two exceptions you will see: an OU can **block inheritance**, and a link can be marked **enforced**, which takes precedence over a block. Computer settings are applied when the computer starts, and user settings when the user signs in; there is also a background refresh while the machine is running (Microsoft's pages say each of these).

What administrators use it for (**est.**, from general practice): password and lockout rules, which software may run, firewall settings, mapped drives, screen-lock timers, and turning on the audit policy that makes the event log useful.

The diagnosis tool you will use most is **gpresult**, which shows the policy that actually applied to a machine and user (Microsoft documents its `/r` option). `gpupdate` asks a machine to fetch policy now, instead of waiting for the refresh (**est.**). The first is read-only; the second changes state, so it is not in the free exercises.

## Kerberos and NTLM at concept level

Both exist to answer "is this person who they say they are?" without sending a password across the network every time.

**Kerberos** works with tickets and a trusted middle party. Microsoft's overview names the three parties: the client acting for a person, the service the person wants to reach, and the **Key Distribution Center (KDC)** that both trust. In an AD domain, the domain controller plays the KDC. You prove yourself once, at sign-in, and receive a ticket that is good for a while; to reach a file server, the client asks for a ticket for that server and shows it, and the server does not have to call the domain controller each time. Microsoft's overview also says AD DS is required for the default Kerberos implementation in a domain or forest, and that before Kerberos, NTLM required the server to contact a domain controller to authenticate every client. A picture to hold: a wristband from the box office. You show your ID once at the box office, and every door after that checks the wristband, not your ID. Kerberos tickets depend on the clocks of the machines agreeing within a few minutes (**est.**), the same reason [time sync matters on Linux](Linux-for-Enterprise-Beginners.md#time-sync).

**NTLM** is the older challenge-and-response method. The server sends a random challenge, the client answers using a secret derived from the password, and the answer is checked. Microsoft's NTLM overview says it is used for workgroups and for local sign-in on computers that are not domain controllers, that Kerberos version 5 is the preferred method in AD environments, and that applications may still use NTLM. It is mostly a compatibility story now (**est.**), and cutting back NTLM needs a list of which applications still depend on it, which Microsoft's page says takes knowledge of the deployed applications.

Why an administrator cares: both leave behind material that an attacker with enough access to a machine can try to reuse, and the defenses in the [security section](#the-security-view-why-active-directory-is-the-usual-target) are largely about limiting where that material ends up. This page names those attack classes; it does not teach them.

## Entra ID, hybrid identity and single sign-on

Microsoft's comparison page calls Entra ID "the next evolution" of identity and access management for the cloud, an identity-as-a-service offering for applications across cloud and on-premises. The two are different tools for different jobs:

| Aspect | Active Directory (AD DS) | Microsoft Entra ID |
|---|---|---|
| Where it runs | On servers you own (domain controllers) | In Microsoft's cloud |
| How apps ask it who you are | Kerberos, NTLM, LDAP (Microsoft's comparison page lists these for on-premises apps) | SAML, OAuth 2.0, OpenID Connect and similar web protocols (the same page says it supports SaaS apps through these) |
| Group Policy | Yes, for domain-joined computers | No. Cloud-managed devices use a device-management service instead (**est.**) |
| Typical device | A laptop joined to the domain | A laptop joined to Entra ID, or both (**est.**) |

Most real companies are **hybrid**: they keep the on-premises directory and also use the cloud one. Microsoft defines hybrid identity as a common user identity for authentication and authorization both on-premises and in the cloud, accomplished through **provisioning** and **synchronization**, the second being how on-premises users and groups are matched to the cloud. Microsoft's tool for that has been Microsoft Entra Connect (the hybrid page names it). That is why a person's password change at the helpdesk may take a short while to show up in the cloud (**est.**).

For the sign-in itself, the cloud directory is the **identity provider** in the single sign-on story: the application trusts it, you sign in there, and a SAML assertion or an OIDC ID token tells the application who you are. All of that is in [Enterprise identity](Enterprise-Identity-SSO-SAML-OIDC.md#directory-identity-provider-single-sign-on-one-picture), and the point about identity being the new perimeter is in [Why identity is the new perimeter](Enterprise-Identity-SSO-SAML-OIDC.md#why-identity-is-the-new-perimeter-and-how-ztna-uses-the-idp). The ZTNA product in this project, Twingate, takes its sign-in from an identity provider the same way; Zscaler is another example of a ZTNA product that does so (**est.** for how any one vendor is configured).

## The Windows registry, services and the event log

**The registry** is, in Microsoft's words, a system-defined database in which applications and system components store and retrieve configuration data. It is organized as a tree of **keys** (like folders) holding **values**. Microsoft's structure page shows one top-level key, `HKEY_LOCAL_MACHINE`, with subkeys `HARDWARE`, `SAM`, `SECURITY`, `SOFTWARE` and `SYSTEM`. In plain terms: `HKEY_LOCAL_MACHINE` holds settings for the whole computer, and `HKEY_CURRENT_USER` holds the signed-in person's settings (**est.**). Group Policy settings are, for the most part, written into the registry on each computer (**est.**). Two habits: read it freely with PowerShell, and do not edit it by hand on a machine you cannot rebuild, because there is no undo and no review. It is the closest Windows has to the `/etc` directory on Linux, with the difference that it is one structured database and not a folder of text files ([Linux: where things live](Linux-for-Enterprise-Beginners.md#where-things-live)).

**Services** are programs that run in the background without a person signed in, the Windows counterpart of Linux services under systemd ([Services with systemd](Linux-for-Enterprise-Beginners.md#services-with-systemd)). Each has a name, a state (running or stopped), a start type (automatic, manual, disabled; **est.**) and an account it runs as. The Services console is `services.msc` (**est.**), and PowerShell's `Get-Service` lists them (Microsoft's reference says it returns running and stopped services). The account a service runs as is a security question: a service running as an over-privileged account is a gift to an attacker ([Service accounts](Enterprise-Identity-SSO-SAML-OIDC.md#service-accounts-and-non-human-identities)).

**The event log** is where Windows writes what happened. Event Viewer shows several logs; the three to know are **Application**, **System** and **Security** (**est.**). The Security log records sign-ins and account changes, but only for the things the audit policy is set to record, and reading it needs administrator rights (**est.**). Each event has an **Event ID**, a number you look up. The ones this page uses, each from Microsoft's security-event documentation unless marked:

| Event ID | Meaning (from Microsoft's page title) | Why a defender cares |
|---|---|---|
| 4624 | An account was successfully logged on | The **logon type** field says how: 2 is interactive (at the keyboard), 3 is over the network (Microsoft's table) |
| 4625 | An account failed to log on | A burst of these for one account is worth a look |
| 4672 | Special privileges assigned to new logon | A privileged account signed in; compare against who should be |
| 4720 | A user account was created | New accounts are how an intruder keeps a way back (MITRE ATT&CK lists Create Account as a technique) |
| 4732 | A member was added to a security-enabled local group | Microsoft's own monitoring recommendations for this event say you may need to watch additions to local or domain security groups |
| 4728 | A member was added to a security-enabled global group (**est.**; I could not read this event's page at the address I tried) | The same, for domain groups such as Domain Admins |
| 4740 | A user account was locked out | Lockouts are the visible side of guessing |
| 4768 | A Kerberos authentication ticket (TGT) was requested | Part of the Kerberos trail on a domain controller |
| 1102 | The audit log was cleared | Rarely innocent on a production machine (**est.**; and a case where the log you need is the one being erased, see [Evade](#build-it-break-it-detect-it-evade-it-defend-it)) |

Shipping these to a central place, so a compromised machine cannot erase its own evidence, is the Windows version of what [Cloud telemetry: what and why](Cloud-Telemetry-What-and-Why.md) and [Detection and monitoring](Detection-and-Monitoring-Wazuh-and-the-Landscape.md) describe for Linux.

## PowerShell: the Windows administrator's tool

You met the basics in [The terminal and your first script](Terminal-and-Your-First-Script.md): commands are **cmdlets** named `Verb-Noun`, and PowerShell passes **objects**, not text. Microsoft's overview says that unlike shells that only accept and return text, PowerShell accepts and returns .NET objects, which is why `Select-Object Name` selects a property and you do not cut columns. The built-in version is Windows PowerShell 5.1; the newer, cross-platform one is PowerShell 7 (`pwsh`), which also runs on macOS and Linux (**est.**).

For a domain, the extra pieces are the **ActiveDirectory** module (with cmdlets such as `Get-ADUser` and `Get-ADGroupMember`) and the **Remote Server Administration Tools (RSAT)**, which Microsoft documents as the way to install the AD DS management tools on a workstation. Most helpdesk work is done through those two things plus a console called Active Directory Users and Computers (**est.**).

The five tasks of this lesson, with the closest equivalent on the other systems. Windows lines are marked **est.** because I did not run them.

| Task | PowerShell (Windows) | macOS (Terminal) | Linux (Bash) |
|---|---|---|---|
| List local users | `Get-LocalUser` (est.) | `dscl . -list /Users` (est.) | `getent passwd` or `cut -d: -f1 /etc/passwd` |
| Who is in the local admin group | `Get-LocalGroupMember -Group Administrators` (est.) | `dscl . -read /Groups/admin GroupMembership` (est.) | `getent group sudo` or `getent group wheel` |
| List and check services | `Get-Service` (and `Get-Service -Name <name>`) | `launchctl list` (est.) | `systemctl list-units --type=service` |
| Read the event log | `Get-WinEvent -LogName System -MaxEvents 10` | `log show --last 10m` (est.) | `journalctl -n 20` |
| Check the firewall | `Get-NetFirewallProfile` (est.) | `/usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate` (est.) | `sudo ufw status` or `firewall-cmd --list-all` |
| Hash a file | `Get-FileHash <file>` (SHA-256 by default) | `shasum -a 256 <file>` | `sha256sum <file>` |
| Who am I and which groups | `whoami /groups` | `id` | `id` |
| Which policy applied | `gpresult /r` | `profiles list` (est.) | n/a |

`Get-WinEvent` can filter at the source with `-FilterHashtable`, which is much faster than fetching everything and filtering afterward (Microsoft's reference shows the pattern with `LogName`, `Level` and `StartTime`). The `Get-FileHash` reference says SHA-256 is the default algorithm, and what a hash is for is in [Hashing: a fingerprint, not a lock](Hashing-Encryption-and-Keys.md#hashing-a-fingerprint-not-a-lock).

A safety habit that carries over from the terminal lesson: many cmdlets that change things accept `-WhatIf`, which prints what would happen and does nothing, but support depends on the individual cmdlet (**est.**), so check with `Get-Help <cmdlet> -Parameter WhatIf` or the cmdlet's reference page before you rely on it. Where it is supported, use it first on anything that deletes or modifies.

## macOS in the enterprise

A Mac at work is usually managed by a **mobile device management (MDM)** service, not by a domain, though a few shops still bind Macs to a directory (**est.**). Apple's deployment guide describes the idea: a device management service lets an IT team securely and remotely configure devices by sending configurations, profiles and commands, whether the user or the organization owns the device. Some terms:

- **Enrollment.** The step that makes a Mac answer to the MDM service. Apple's guide describes an enrollment profile that lets the service send commands and further profiles, and says that when a user removes an enrollment profile, every configuration, setting and managed app based on it is removed too. Apple lists several enrollment methods (User Enrollment, Device Enrollment, and Automated Device Enrollment appear in the guide's table of contents).
- **Configuration profile.** A bundle of settings pushed to the Mac: Wi-Fi, password rules, a certificate, restrictions. Apple's guide says a legacy configuration profile is an XML file ending in `.mobileconfig`, and that newer **declarative device management** uses JSON payloads created by the management service.
- **Supervision.** A stronger level of management available to organization-owned devices; the guide has a page on it (**est.** for what it permits).
- **Apple's business portal.** Apple Business Manager is now called Apple Business, which Apple's page says combines what Apple Business Manager, Apple Business Essentials and Apple Business Connect did. This is where an organization ties devices it bought to its MDM service, so a new Mac enrolls itself the first time it connects (**est.** for the exact flow).
- **The keychain.** macOS's store for passwords, certificates and keys. Apple's platform security guide has a "Keychain data protection" page, which describes protection classes that depend on whether the device is unlocked, locked, or past first unlock. In practice a person's saved passwords and some enterprise certificates live there, and an enterprise profile can place certificates into it (**est.**).
- **FileVault.** Apple's disk encryption; the security guide has a chapter on it. Enterprises typically require it and escrow the recovery key with the MDM service (**est.**).

How the three compare, as a beginner's map. Every cell marked **est.** is general knowledge I did not read from a vendor page.

| Aspect | Linux | Windows (domain) | macOS (MDM) |
|---|---|---|---|
| Central sign-in | Often none per machine; SSO via a directory or SSH keys | Active Directory, with Kerberos | A local account or a cloud identity provider signs the person in; MDM is the separate plane that enrolls and configures the device (**est.**) |
| Central configuration | A configuration-management tool or cloud-init ([What is infrastructure as code](What-Is-Infrastructure-as-Code.md)) | Group Policy | Configuration profiles and declarative management |
| Where settings live | Text files under `/etc` | The registry | Property list (`.plist`) files and profiles (**est.**) |
| Software installs | Package manager (`apt`, `dnf`) | Installers, plus a management tool that deploys them (**est.**) | App Store, installers, and MDM-deployed apps (**est.**) |
| Logs | `journalctl`, `/var/log` | Event Viewer, `Get-WinEvent` | The unified log, `log show` (**est.**) |
| Shell | Bash | PowerShell | zsh by default ([terminal lesson](Terminal-and-Your-First-Script.md)) |
| Admin elevation | `sudo` | Run as administrator, or a separate admin account | `sudo` or an admin prompt (**est.**) |

The cultural difference: Linux administrators reach machines over SSH and treat them as disposable; Windows administrators manage a domain of long-lived machines through policy; Mac administrators manage individually owned devices that travel, so the MDM service and the disk encryption carry more of the weight (**est.**).

## The security view: why Active Directory is the usual target

A directory decides who may do what to almost everything. Whoever controls the domain controllers, or an account with full rights over the directory, controls the sign-in for every computer in it. That is why defenders and attackers both focus there. Microsoft's guidance on securing Active Directory describes credential theft as an attacker gaining privileged access to a computer on the network and extracting credentials from the sessions of accounts that are currently signed in, and lists the accounts credential thieves usually go after: permanently privileged accounts, VIP accounts, privilege-attached AD accounts, domain controllers, and other infrastructure that affects identity, access and configuration, such as certificate and systems-management servers.

The **attack classes** you will hear named, with a pointer to each in MITRE ATT&CK (the framework is introduced in [Threat frameworks](Threat-Frameworks-STRIDE-ATTACK-ATLAS.md)). These are names to recognize in an alert or an interview, **not** instructions:

- Use of valid accounts, specifically domain accounts ([Valid Accounts: Domain Accounts](https://attack.mitre.org/techniques/T1078/002/)): the intruder signs in as someone legitimate.
- [OS credential dumping](https://attack.mitre.org/techniques/T1003/), including the sub-technique that imitates a domain controller to pull directory data ([DCSync](https://attack.mitre.org/techniques/T1003/006/)).
- Stealing or forging Kerberos tickets, including [Kerberoasting](https://attack.mitre.org/techniques/T1558/003/) and [Golden Ticket](https://attack.mitre.org/techniques/T1558/001/).
- Reusing authentication material instead of a password, such as [Pass the Hash](https://attack.mitre.org/techniques/T1550/002/).
- Changing policy to spread: [Group Policy Modification](https://attack.mitre.org/techniques/T1484/001/).
- Creating accounts to stay in ([Create Account](https://attack.mitre.org/techniques/T1136/)).

What the defensive side looks like, in the order I would explain it to a new hire:

1. **Least privilege.** Fewer people in Domain Admins than you think you need, and none permanently if you can avoid it ([Privileged access, just in time](Enterprise-Identity-and-Secrets-at-Scale.md#privileged-access-pam-just-in-time-and-break-glass)).
2. **Tiering.** Separate the most powerful accounts and systems from everyday ones, so that a stolen everyday credential is not also a key to the directory. Microsoft's access-model page says its enterprise access model builds on the older AD tier model, which focused on containing unauthorized escalation of privilege, and that "Tier 0" expands to become the control plane covering all aspects of access control. The beginner version: your admin account for the domain controllers signs in only to the domain controllers, not to a laptop that browses the web, and you use a different account for ordinary work.
3. **No shared local administrator password.** Microsoft's Windows LAPS (Local Administrator Password Solution) page says local administrator accounts often share the same password across many devices, and that LAPS regularly rotates each device's local administrator password, stores it securely, and lets authorized administrators retrieve it. Microsoft lists protection against pass-the-hash and lateral-traversal attacks among its benefits, and says it works for Entra-joined and AD-joined devices. If every laptop has the same local administrator password, one stolen laptop opens all of them. This is the answer to "why is a local admin account a risk".
4. **Protected accounts.** Microsoft's Protected Users group applies extra restrictions: members cannot authenticate with NTLM, cannot use DES or RC4 in Kerberos preauthentication, cannot be delegated, and cannot renew Kerberos TGTs beyond their initial four-hour lifetime. It is a bundle of settings you can opt your most privileged accounts into (test it first; it can break old applications).
5. **MFA** on every administrative sign-in, preferably phishing-resistant ([MFA, and why some resists phishing](Enterprise-Identity-SSO-SAML-OIDC.md#mfa-and-why-some-mfa-resists-phishing)).
6. **Patch and protect the domain controllers** like the crown jewels they are: few services on them, no web browsing, tight network access (**est.**).
7. **Audit policy on, logs shipped off the machine, and alerts on the events in the table above**, in particular changes to privileged groups.

## Hands-on, free path: read, then read-only commands

You need no account and no money for this path. The commands in Exercises 1 to 4 and 6 only **read**. Exercise 5 and Exercise 7 write small files into a new, uniquely named temporary folder that they delete again, and the optional virtual-machine path changes a disposable machine. There are two ways to do it, pick the one you have:

- **On a Windows machine you own.** Run the PowerShell blocks in a normal (non-administrator) PowerShell window. A few events need administrator rights to read, and the lesson says when.
- **On a Mac or a Linux machine.** Run the Bash or macOS commands. You will see the same ideas with different words.
- **On neither.** Do Exercise 7, which uses made-up data and runs anywhere, then read the rest.

> **On a work or school computer, do not run these without asking.** Reading the Security log, the registry or the firewall on a machine you do not own may break the organization's rules, and endpoint security software can raise an alert on unusual commands. Use your own machine, or get the owner's written yes. Nothing on this page should be pointed at a computer, a domain or a network that is not yours.

Each exercise has Predict, Do, Check and Undo. Windows and macOS lines are **est.** (not run).

### Exercise 1: who is on this machine, and which groups are they in

1. **Predict.** Write down how many local user accounts you think this machine has, and whether your own account is in the administrators group.
2. **Do.**

   ```powershell
   # PowerShell (Windows)
   whoami /groups
   Get-LocalUser | Select-Object Name, Enabled
   Get-LocalGroupMember -Group Administrators
   ```

   ```bash
   # macOS
   id
   dscl . -list /Users | grep -v '^_'
   dscl . -read /Groups/admin GroupMembership

   # Linux
   id
   getent passwd | cut -d: -f1
   getent group sudo; getent group wheel
   ```
3. **Check.** On Windows, built-in accounts such as Guest are usually disabled (**est.**). Count the enabled ones. A machine you set up yourself usually has one administrator; a machine from an employer often has more than one. On a Mac, accounts starting with an underscore are system accounts, which the `grep` hides.
4. **Undo.** Nothing changed; you only read.

### Exercise 2: services, and which one runs as what

1. **Predict.** Is the Windows Time service (`W32Time`) running on your machine? Why does a domain care (see Kerberos)?
2. **Do.**

   ```powershell
   # PowerShell (Windows)
   Get-Service | Group-Object Status | Select-Object Name, Count
   Get-CimInstance Win32_Service -Filter "Name='W32Time'" | Select-Object Name, State, StartMode, StartName
   ```

   ```bash
   # macOS
   launchctl list | head -n 15
   # Linux
   systemctl list-units --type=service --state=running | head -n 15
   ```
3. **Check.** The group counts show how many services are running and stopped. On a domain-joined machine, `W32Time` is normally set to start automatically (**est.**); on a standalone home PC it may be on demand. The `StartMode` column is the "does this survive a reboot" answer, as `systemctl enable` is on Linux, and `StartName` is the account the service runs as. (`Get-Service` itself has a start-type property only in some PowerShell versions, which is why this uses the CIM query, **est.**)
4. **Undo.** Nothing changed.

### Exercise 3: read the event log

1. **Predict.** What will the newest event in the System log be, an error, a warning, or information? Guess before looking.
2. **Do.** The System log can be read without administrator rights (**est.**), unlike the Security log.

   ```powershell
   # PowerShell (Windows): the 10 newest System events, then only warnings and errors from the last day
   Get-WinEvent -LogName System -MaxEvents 10 | Select-Object TimeCreated, Id, LevelDisplayName, ProviderName
   $since = (Get-Date).AddDays(-1)
   Get-WinEvent -FilterHashtable @{ LogName='System'; Level=2,3; StartTime=$since } -MaxEvents 20 |
     Select-Object TimeCreated, Id, ProviderName
   ```

   ```bash
   # macOS: the last few minutes of the unified log
   log show --last 5m | head -n 20
   # Linux
   journalctl -p warning -n 20 --no-pager
   ```
3. **Check.** Most events are information. The `Level` numbers (2 for error, 3 for warning; **est.**, check Microsoft's reference) are what the filter uses. If the second command prints nothing, your machine had a quiet day, which is a result. If you have an administrator window and want to see the sign-in events from the table above, `Get-WinEvent -FilterHashtable @{ LogName='Security'; Id=4624 } -MaxEvents 5` reads the five newest successful sign-ins; the `Message` text holds the logon type (**est.**).
4. **Undo.** Nothing changed.

### Exercise 4: the firewall, read-only

1. **Predict.** Is the firewall on for all three profiles (Domain, Private, Public)?
2. **Do.**

   ```powershell
   # PowerShell (Windows)
   Get-NetFirewallProfile | Select-Object Name, Enabled, DefaultInboundAction
   Get-NetFirewallRule -Enabled True -Direction Inbound -Action Allow | Measure-Object | Select-Object Count
   ```

   ```bash
   # macOS
   /usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate
   # Linux
   sudo ufw status verbose
   ```
3. **Check.** Each profile should show `Enabled : True` on a normally configured machine (**est.**). The second command counts inbound allow rules, which is often higher than people expect; reading that number is the point. It is the same "what is open" question as `firewall-cmd --list-all` in [Linux: firewalls](Linux-for-Enterprise-Beginners.md#firewalls). Do not change a rule to make the number smaller.
4. **Undo.** Nothing changed.

### Exercise 5: hash a file you make yourself

1. **Predict.** If you change one character in a file, how many characters of its SHA-256 will change?
2. **Do.** The file is built at run time with made-up content.

   ```powershell
   # PowerShell
   $dir = Join-Path ([System.IO.Path]::GetTempPath()) ("f8-hash-" + [guid]::NewGuid())
   New-Item -ItemType Directory -Path $dir | Out-Null
   Set-Content -Path "$dir\note.txt" -Value "hello domain" -NoNewline
   Get-FileHash "$dir\note.txt" | Select-Object Algorithm, Hash
   Set-Content -Path "$dir\note.txt" -Value "hello domaiN" -NoNewline
   Get-FileHash "$dir\note.txt" | Select-Object Algorithm, Hash
   ```

   ```bash
   # Bash (macOS: use shasum -a 256 instead of sha256sum)
   d="$(mktemp -d)"
   printf 'hello domain' > "$d/note.txt" && sha256sum "$d/note.txt"
   printf 'hello domaiN' > "$d/note.txt" && sha256sum "$d/note.txt"
   ```
3. **Check.** The two hashes look completely unrelated even though one character changed. This is why a published hash lets you check a download, and why a defender uses a file's hash to ask "is this the same file as before" ([Exercise 1 of the hashing lesson](Hashing-Encryption-and-Keys.md#exercise-1-hash-a-file-change-one-byte)).
4. **Undo.** `Remove-Item -Recurse $dir` (PowerShell) or `rm -r "$d"` (Bash).

### Exercise 6: read one registry value

1. **Predict.** Which registry key do you think holds the Windows version name?
2. **Do.**

   ```powershell
   # PowerShell (Windows): read, never write
   Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion' |
     Select-Object ProductName, CurrentBuild
   Get-ChildItem 'HKLM:\SOFTWARE' | Select-Object -First 10 Name
   ```

   ```bash
   # macOS
   sw_vers
   # Linux
   cat /etc/os-release
   ```
3. **Check.** `HKLM:` is PowerShell's name for the machine-wide hive. The value names `ProductName` and `CurrentBuild` are from general knowledge (**est.**); if they are missing on your build, list the key's values with `Get-ItemProperty` and no `Select-Object`. This is the Windows version of `cat /etc/os-release`.
4. **Undo.** Nothing changed. Do not use `Set-ItemProperty` or `New-Item` on the registry in this lesson.

### Exercise 7: a group-change report from made-up data (any operating system)

This list reads additions only: it does not know about removals or about people who were already members, so for current membership you would query the directory (`Get-ADGroupMember`) and use the event file only to see changes. This is the one exercise I ran, in Bash on Linux, on 2026-10-22. The data is invented: `casey`, `blake`, `drew` and `helpdesk1` are made-up names, and the file stands in for an export of group-change events. It shows how a defender spots a change to a privileged group.

1. **Predict.** Looking at the four rows you are about to create, which one would you ask about?
2. **Do.**

   ```bash
   # Bash
   d="$(mktemp -d)" && cd "$d"   # a new, empty, uniquely named folder
   printf 'casey\n' > approved_admins.txt
   cat > group_events.csv <<'EOF'
   time,event_id,group,member,changed_by
   2026-10-20T09:02:11Z,4728,Sales,blake,helpdesk1
   2026-10-20T09:15:40Z,4728,Engineering,drew,helpdesk1
   2026-10-20T22:47:03Z,4728,Domain Admins,blake,helpdesk1
   2026-10-21T08:30:00Z,4732,Remote Desktop Users,drew,helpdesk1
   EOF
   awk -F, -v p='^(Domain Admins|Enterprise Admins|Administrators)$' \
     'NR>1 && $3 ~ p {print "PRIVILEGED CHANGE:", $1, "event", $2, $3, "<-", $4, "by", $5}' group_events.csv
   echo "--- additions to Domain Admins of people who are not on the approved list:"
   awk -F, 'NR>1 && $3=="Domain Admins" {print $4}' group_events.csv | sort -u | grep -vxFf approved_admins.txt
   ```

   ```powershell
   # PowerShell (not run; est.)
   $dir = Join-Path $HOME ("f8-lab-" + [guid]::NewGuid()); New-Item -ItemType Directory -Path $dir | Out-Null
   Set-Location $dir
   Set-Content approved_admins.txt "casey"
   @"
   time,event_id,group,member,changed_by
   2026-10-20T09:02:11Z,4728,Sales,blake,helpdesk1
   2026-10-20T09:15:40Z,4728,Engineering,drew,helpdesk1
   2026-10-20T22:47:03Z,4728,Domain Admins,blake,helpdesk1
   2026-10-21T08:30:00Z,4732,Remote Desktop Users,drew,helpdesk1
   "@ | Set-Content group_events.csv
   $priv = 'Domain Admins','Enterprise Admins','Administrators'
   $rows = Import-Csv group_events.csv
   $rows | Where-Object { $priv -contains $_.group }
   $approved = Get-Content approved_admins.txt
   $rows | Where-Object { $_.group -eq 'Domain Admins' -and $approved -notcontains $_.member } |
     Select-Object -ExpandProperty member -Unique
   ```
3. **Check.** Output from my Bash run:

   ```text
   PRIVILEGED CHANGE: 2026-10-20T22:47:03Z event 4728 Domain Admins <- blake by helpdesk1
   --- additions to Domain Admins of people who are not on the approved list:
   blake
   ```

   One row is the odd one: a helpdesk account added someone to Domain Admins at 22:47. Two things made it stand out: the group, and the hour. Whether it was a mistake or an intrusion, nobody should learn about it from a quarterly review.
4. **Undo.** `cd ~ && rm -r "$d"` (Bash) or `Set-Location ~; Remove-Item -Recurse $dir` (PowerShell). Both paths were created fresh by this exercise (`mktemp -d`, a GUID in the name), so the recursive delete cannot reach anything you already had. Check the variable is set first: `echo "$d"` or `$dir`.

## Optional own-hardware path: a disposable Windows evaluation virtual machine

If you want to build a real domain and break it, the sensible place is a virtual machine on your own computer that holds nothing you care about. Microsoft publishes evaluation editions for exactly this kind of testing.

**What I read, on 2026-10-22, from Microsoft's Evaluation Center pages (the [Windows Server 2025 page](https://www.microsoft.com/en-us/evalcenter/evaluate-windows-server-2025) and the [Windows 11 Enterprise page](https://www.microsoft.com/en-us/evalcenter/evaluate-windows-11-enterprise)):**

- **Windows Server 2025** is offered as a 64-bit ISO and a 64-bit VHD (a virtual hard disk file), and as an option on Azure. You register, then download and install. The page notes that **this evaluation edition expires in 180 days**, that evaluation versions of Windows Server must be **activated over the internet in the first 10 days** to avoid an automatic shutdown, and that when you finish evaluating you can convert an evaluation version to retail. The page offers it with a full graphical desktop. The wording is the page's own as of my read on 2026-10-22; Microsoft can change it, so check the page before you plan around the number.
- **Windows 11 Enterprise** says "Register, then download and install the full-featured software for a 90-day evaluation", no product key is required, and Windows prompts you to activate. It says that if you fail to activate, or the evaluation period expires, the desktop background turns black, a persistent notification says the system is not genuine, and the PC shuts down every hour. It also says you cannot use the recovery partition to go back to a previous version of Windows. That page also says you must sign in with a Microsoft account, with a local account to follow at final release; that text looked dated to me, so treat it as unverified.
- **Cost.** The two pages describe the downloads as an evaluation to "get started for free". I read **no price** and I did not read the **evaluation license agreement**, so what the license allows is unverified: assume learning and testing only (**est.**) and read it before you accept. The cost to you is your own computer's disk, memory and time.
- **Hardware.** Microsoft's hardware-requirements page for Windows Server lists a 1.4 GHz 64-bit processor minimum and, for RAM, 2 GB minimum for Server Core and for Server with Desktop Experience, with 4 GB recommended for the latter. Give a lab domain controller 4 GB or more of memory and a disk of a few tens of gigabytes (**est.**).
- **Virtualization.** Microsoft documents Hyper-V on Windows (an edition and hardware requirement applies; **est.**). Free alternatives exist, such as VirtualBox ([downloads](https://www.virtualbox.org/wiki/Downloads), which I confirmed loads but did not review for terms).

**Isolation rules.** Activate the evaluation first (the Server edition needs internet activation in its first 10 days): give the new virtual machine a temporary NAT connection, activate, run Windows Update, then disconnect it. Only after that, build the domain lab and put the virtual machine on a **host-only or internal virtual network** with no route to your home network, so the test domain, its DNS and DHCP cannot collide with real ones. Take a snapshot before every change you may want to undo. Use a domain name under a reserved domain such as `corp.example.com`. Never join a real computer to it, and never reuse a real password.

**Teardown.** When you are done: delete the virtual machine and its disk files, delete the ISO or VHD if you will not use it again, and delete the snapshots. The evaluation expires on its own; deleting is cleaner.

### Build the lab domain (commands from Microsoft's documentation, est.)

Microsoft's AD DS installation page shows the two cmdlets below. I did not run them. They change the machine, so run them only in the disposable virtual machine, as an administrator.

```powershell
# On the lab server only.
Install-WindowsFeature -Name AD-Domain-Services -IncludeManagementTools
# Promotes this server to the first domain controller of a new forest.
# It prompts for the recovery (DSRM) password, so no password appears in the command.
Install-ADDSForest -DomainName "corp.example.com"
```

After the automatic reboot, create a small structure. Passwords are typed at the prompt; none is written in the script (a secret in a script is a finding, see [Hashing, encryption and keys](Hashing-Encryption-and-Keys.md)):

```powershell
# est.
New-ADOrganizationalUnit -Name "Staff" -Path "DC=corp,DC=example,DC=com"
New-ADGroup -Name "Helpdesk" -GroupScope Global -Path "OU=Staff,DC=corp,DC=example,DC=com"
$pw = Read-Host -AsSecureString -Prompt "Password for the test user"
New-ADUser -Name "Blake Test" -SamAccountName "blake" -Path "OU=Staff,DC=corp,DC=example,DC=com" `
  -AccountPassword $pw -Enabled $true
Add-ADGroupMember -Identity "Helpdesk" -Members "blake"
Get-ADGroupMember -Identity "Helpdesk" | Select-Object Name, SamAccountName
```

A first Group Policy: in the Group Policy Management console, create a GPO called "Lab banner", link it to an OU that holds the lab computer, and set a harmless value, such as the sign-in message text (**est.** where in the editor). That setting is a computer-side policy, so linking it to the Staff OU, which holds only users and a group, would do nothing: create a "Workstations" OU, move the joined lab computer into it (it lands in the default Computers container otherwise, **est.**), and link the GPO there. Then on a joined lab computer run `gpresult /r` and look for the GPO in the output.

## Build it, break it, detect it, evade it, defend it

The loop, on the lab domain if you built one, or on the fake data of Exercise 7 if you did not. Everything here is local and made up; none of it is aimed at another machine.

**Build.** A domain with an OU, a Helpdesk group, a test user and one GPO, and a short list of who is *supposed* to be in Domain Admins (`approved_admins.txt` in the exercise).

**Break.** Do what happens under pressure: add the test user to Domain Admins "just for an hour" so a task goes faster (`Add-ADGroupMember -Identity "Domain Admins" -Members "blake"` in the lab only, **est.**). In the fake data, this is the 22:47 row.

**Detect.** Two ways, and you want both. A *report*: list the members of the privileged groups and compare with the approved list (`Get-ADGroupMember -Identity "Domain Admins"` against `approved_admins.txt`; Exercise 7 does the comparison). An *event*: on a domain controller, the Security log records the group change (4728 for a global group, **est.**; 4732 for a local one, from Microsoft's page), and a sign-in with special privileges (4672). Microsoft's own monitoring recommendation for 4732 is to watch additions to security groups. A real deployment forwards these to a central log and alerts on privileged-group changes ([Detection and monitoring](Detection-and-Monitoring-Wazuh-and-the-Landscape.md)).

**Evade.** In words only. An intruder who has reached a privileged account wants to look like normal administration. They tend to prefer **valid accounts** over malware, since a legitimate sign-in raises fewer alarms (ATT&CK: Valid Accounts, Domain Accounts). They may add themselves to a group at an hour when the helpdesk is quiet, create a new account that looks like a service account (ATT&CK: Create Account), or **clear the event log** afterward (event 1102 is the trace of that, **est.** that it is reliably recorded) to remove the evidence. They may also lean on how an environment is set up, such as a shared local administrator password, or a Kerberos ticket that is valid longer than it should be (**est.**). The defender's counters are exactly why logs are shipped off the machine, alerts are written on behavior and not just on a file name, and privileged actions are rare enough that each one is explainable. Do not search for tools to try these. Nothing on this page needs one.

**Defend.** Fewer, time-limited privileged accounts; a separate administrative account per administrator; tiering so those accounts only sign in to the systems they manage; LAPS so no two computers share a local administrator password; Protected Users for the powerful accounts, tested first; MFA for admin sign-in; audit policy enabled and logs forwarded; an alert on every change to a privileged group; and a regular review of who is in which group, the same access review as in [Enterprise identity](Enterprise-Identity-SSO-SAML-OIDC.md#groups-roles-and-mapping-people-to-access).

**Flip the board.** Two short paper exercises. (1) You are the intruder who just got one helpdesk password. Using the lab picture above, list which groups that account can change and which single change would give you the most reach; then name the one log entry that would give you away. (2) You are the defender with ten minutes to write one alert. Pick the event, the group names it should fire on, and one benign case that would cause a false alarm (a planned change at a known time by a named person). Write down what the on-call person should do in the first five minutes.

**Undo.** In the lab, remove the test user from Domain Admins (`Remove-ADGroupMember -Identity "Domain Admins" -Members "blake"`, lab only, **est.**; it asks for confirmation), or revert to the snapshot you took before. Delete the virtual machine when you finish.

## Common mistakes

- Treating the domain as "just a login". It is also policy, DNS dependence and the place nearly every permission is decided.
- Giving a person's everyday account administrator rights "to save time".
- The same local administrator password on every laptop.
- Turning on auditing nowhere and then expecting the Security log to explain an incident.
- Editing the registry by hand on a machine nobody can rebuild.
- Running a PowerShell snippet copied from the internet without reading it first ([Make it safe](Terminal-and-Your-First-Script.md#make-it-safe)).
- Assuming a Mac is "managed" because it is a Mac. Without an MDM enrollment, it is a personal computer on your network.

## Checkpoint

You are done when you can say, without looking:

- What a domain, a domain controller, an OU and a GPO each are, and the order Group Policy is applied in.
- What Kerberos and NTLM each do in one sentence, and which one Microsoft's pages call preferred in AD.
- How Active Directory and Entra ID differ, and what makes an environment hybrid.
- The three Windows logs, and what 4624, 4625, 4672, 4732 and 1102 each mean.
- What an MDM service sends to a Mac, and what a configuration profile is.
- Why a shared local administrator password is a risk, and what LAPS does about it.
- Tiering in two sentences, and the one alert you would write first for a directory.

Answers are in the sections above.

## Claims register

All read-only requests; retrieved **2026-10-22** (Microsoft Learn, Microsoft Evaluation Center, Apple Support, MITRE ATT&CK). "Not read" means I could not get the detail and the page uses **est.**

| Claim | Source | Status |
|---|---|---|
| Windows Server 2025 evaluation: ISO, VHD and Azure options; "expires in 180 days"; activate over the internet within the first 10 days or it shuts down automatically; can convert to retail; register to download | [Windows Server 2025 evaluation](https://www.microsoft.com/en-us/evalcenter/evaluate-windows-server-2025) | Read 2026-10-22. The page loaded for a plain request; an earlier request with a browser-style header was refused |
| Windows 11 Enterprise evaluation: "90-day evaluation", no product key required, black desktop and hourly shutdown on expiry, cannot use recovery partition to go back, Microsoft account sign-in note | [Windows 11 Enterprise evaluation](https://www.microsoft.com/en-us/evalcenter/evaluate-windows-11-enterprise) | Read. The Microsoft-account sentence looked dated; unverified |
| Evaluation license terms (what use is allowed) and any price | The agreement shown at download or install | **Not read.** Unverified |
| Windows Server hardware: 1.4 GHz 64-bit processor minimum; 2 GB RAM minimum for Server Core and for Desktop Experience, 4 GB recommended for Desktop Experience | [Windows Server hardware requirements](https://learn.microsoft.com/en-us/windows-server/get-started/hardware-requirements) | Read |
| AD DS makes network resource data available to authorized users and administrators; integrates security through sign-in authentication and access control; all domain controllers in a domain replicate and hold a complete copy of that domain's directory data | [AD DS overview](https://learn.microsoft.com/en-us/windows-server/identity/ad-ds/get-started/virtual-dc/active-directory-domain-services-overview) | Read |
| "Forest" as a group of domains sharing a schema and the security boundary | Not read on a Microsoft page | **est.** |
| AD DS was introduced in Windows 2000; Entra ID is "the next evolution", IDaaS; on-premises apps use LDAP, NTLM and Kerberos; SaaS apps use SAML, OAuth 2.0 and WS-* protocols | [Compare Active Directory to Microsoft Entra ID](https://learn.microsoft.com/en-us/entra/fundamentals/compare) | Read |
| Hybrid identity = common identity on-premises and in the cloud, through provisioning and synchronization; Microsoft Entra Connect named | [What is hybrid identity](https://learn.microsoft.com/en-us/entra/identity/hybrid/whatis-hybrid-identity) | Read. Entra Connect's current naming not re-checked |
| GPO definition; OU is the lowest-level AD container to which you can assign Group Policy; `gpedit.msc` for local policy; background refresh | [Group Policy overview](https://learn.microsoft.com/en-us/windows-server/identity/ad-ds/manage/group-policy/group-policy-overview) | Read |
| Processing order (local, site, domain, OU, parent before child); block inheritance; enforced; computer settings at startup, user settings at sign-in | [Group Policy processing](https://learn.microsoft.com/en-us/windows-server/identity/ad-ds/manage/group-policy/group-policy-processing) | Read |
| `gpresult` with `/r` | [gpresult reference](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/gpresult) | Read (syntax). Output format not read |
| `gpupdate` forces a refresh | [gpupdate reference](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/gpupdate) | Page loads; behavior **est.** |
| Kerberos: three parties (client, service, KDC); AD DS required for default Kerberos in a domain or forest; NTLM required the server to contact a DC for every client | [Kerberos authentication overview](https://learn.microsoft.com/en-us/windows-server/security/kerberos/kerberos-authentication-overview) | Read |
| NTLM used for workgroups and local sign-in; Kerberos v5 preferred in AD; applications may still use NTLM | [NTLM overview](https://learn.microsoft.com/en-us/windows-server/security/kerberos/ntlm-overview) | Read |
| Registry is a system-defined configuration database; `HKEY_LOCAL_MACHINE` subkeys HARDWARE, SAM, SECURITY, SOFTWARE, SYSTEM | [Registry](https://learn.microsoft.com/en-us/windows/win32/sysinfo/registry), [Structure of the registry](https://learn.microsoft.com/en-us/windows/win32/sysinfo/structure-of-the-registry) | Read. `HKEY_CURRENT_USER` meaning and Group Policy writing to the registry: **est.** |
| `Get-Service` lists running and stopped services; `Get-WinEvent` reads event logs and supports `-FilterHashtable` with `LogName`, `Level`, `StartTime`; `Get-FileHash` defaults to SHA256 | [Get-Service](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.management/get-service), [Get-WinEvent](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.diagnostics/get-winevent), [Get-FileHash](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.utility/get-filehash) | Read |
| `Get-NetFirewallProfile`, `Get-NetFirewallRule`, `Get-LocalUser`, `Get-LocalGroupMember`, `Get-ADUser`, `Get-ADGroupMember` exist | [NetSecurity](https://learn.microsoft.com/en-us/powershell/module/netsecurity/get-netfirewallprofile), [Get-LocalGroupMember](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.localaccounts/get-localgroupmember), [Get-ADUser](https://learn.microsoft.com/en-us/powershell/module/activedirectory/get-aduser), [Get-ADGroupMember](https://learn.microsoft.com/en-us/powershell/module/activedirectory/get-adgroupmember) | Pages load; parameter and output details **not read**, so the commands are **est.** |
| PowerShell accepts and returns .NET objects, not only text | [PowerShell overview](https://learn.microsoft.com/en-us/powershell/scripting/overview) | Read |
| RSAT includes AD DS and AD LDS tools | [Remote Server Administration Tools](https://learn.microsoft.com/en-us/windows-server/remote/remote-server-administration-tools) | Read |
| `whoami` with `/groups` | [whoami reference](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/whoami) | Read (syntax) |
| `Install-WindowsFeature -name AD-Domain-Services -IncludeManagementTools`; `Install-ADDSForest -DomainName` prompts for the DSRM password; DNS installed by default | [Install AD DS (Level 100)](https://learn.microsoft.com/en-us/windows-server/identity/ad-ds/deploy/install-active-directory-domain-services--level-100-) | Read. Not run |
| Event 4624 (successful logon; logon types 2 interactive, 3 network), 4625 (failed logon), 4672 (special privileges), 4720 (user created), 4732 (member added to local group; monitoring recommendation), 4740 (lockout), 4768 (TGT requested), 1102 (log cleared) | [4624](https://learn.microsoft.com/en-us/previous-versions/windows/it-pro/windows-10/security/threat-protection/auditing/event-4624), [4625](https://learn.microsoft.com/en-us/previous-versions/windows/it-pro/windows-10/security/threat-protection/auditing/event-4625), [4672](https://learn.microsoft.com/en-us/previous-versions/windows/it-pro/windows-10/security/threat-protection/auditing/event-4672), [4720](https://learn.microsoft.com/en-us/previous-versions/windows/it-pro/windows-10/security/threat-protection/auditing/event-4720), [4732](https://learn.microsoft.com/en-us/previous-versions/windows/it-pro/windows-10/security/threat-protection/auditing/event-4732), [4740](https://learn.microsoft.com/en-us/previous-versions/windows/it-pro/windows-10/security/threat-protection/auditing/event-4740), [4768](https://learn.microsoft.com/en-us/previous-versions/windows/it-pro/windows-10/security/threat-protection/auditing/event-4768), [1102](https://learn.microsoft.com/en-us/previous-versions/windows/it-pro/windows-10/security/threat-protection/auditing/event-1102) | Read (titles and the cited fields) |
| Event 4728 (member added to a security-enabled global group) | Page not found at the address I tried | **est.** |
| Credential theft description and the accounts thieves target | [Best practices for securing Active Directory](https://learn.microsoft.com/en-us/windows-server/identity/ad-ds/plan/security-best-practices/best-practices-for-securing-active-directory) | Read |
| Enterprise access model builds on the AD tier model; Tier 0 expands to the control plane | [Enterprise access model](https://learn.microsoft.com/en-us/security/privileged-access-workstations/privileged-access-access-model) | Read |
| Windows LAPS rotates and stores each device's local administrator password; benefits include protection against pass-the-hash and lateral traversal; Entra-joined and AD-joined devices | [Windows LAPS overview](https://learn.microsoft.com/en-us/windows-server/identity/laps/laps-overview) | Read |
| Protected Users restrictions (no NTLM, no DES or RC4 in Kerberos preauthentication, no delegation, no TGT renewal beyond the initial four hours) | [Protected Users security group](https://learn.microsoft.com/en-us/windows-server/security/credentials-protection-and-management/protected-users-security-group) | Read |
| Apple device management: configurations, profiles and commands; enrollment profile; legacy configuration profile is `.mobileconfig`; configurations are JSON payloads; enrollment methods listed | [Intro to device management (Apple Platform Deployment)](https://support.apple.com/guide/deployment/intro-to-mdm-profiles-depc0aadd3fe/web) | Read. Supervision details and the automated enrollment flow **not read** |
| Apple Business Manager is now Apple Business | [Apple Business Manager User Guide](https://support.apple.com/guide/apple-business-manager/welcome/web) | Read |
| Keychain data protection classes; FileVault chapter exists | [Keychain data protection](https://support.apple.com/guide/security/keychain-data-protection-secb0694df1a/web), [Apple Platform Security](https://support.apple.com/guide/security/system-integrity-protection-sec3d8dc4b9e/web) | Read (table of contents and the class table). Escrow practice: **est.** |
| MITRE technique names (Valid Accounts: Domain Accounts, OS Credential Dumping, DCSync, Kerberoasting, Golden Ticket, Pass the Hash, Group Policy Modification, Create Account) | [MITRE ATT&CK](https://attack.mitre.org/techniques/T1003/) and the linked technique pages | Read (page titles) |
| Hyper-V on Windows has a quick-start to enable it | [Enable Hyper-V](https://learn.microsoft.com/en-us/virtualization/hyper-v-on-windows/quick-start/enable-hyper-v) | Page loads; edition requirements **est.** |
| The Bash commands of Exercise 7 and the output shown | Run on Linux by the author | 2026-10-22 |
| Market share, why companies choose Windows, Mac use of directories, how any one vendor is configured, and everything marked **est.** | General knowledge | Not verified |
| Cost of this lesson | None of it spends money on a cloud; the optional path uses your own computer | n/a |
