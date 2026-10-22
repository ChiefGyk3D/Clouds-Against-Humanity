# Cloud Cowrie for a weekend: build it, run it, tear it down

Lesson 8 of the [deception and honeypots track](Deception-and-Honeypots-Start-Here.md), the hands-on lesson of **track 2**. You run a small Cowrie honeypot on one cloud server in **your own account**, for a window you set before you start, and you delete it on the end date. A foundations side page to [Anatomy of a cloud honeypot](Deception-and-Honeypots-Cloud-Sensor-Anatomy.md) and [DigitalOcean network and firewalls](DigitalOcean-Network-and-Firewalls.md). Nothing in this repository deploys it: the lesson shows the steps and you run them. Next: [Read what arrived](Deception-and-Honeypots-Read-the-Sensor-Logs.md), lesson 9.

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

> **Status: written from reading; the cloud and Cowrie steps were never run.** On **2026-10-22** the author read the Cowrie installation page, its default configuration and the DigitalOcean pages in the [claims register](#claims-register), and ran two things locally: the lure-file script (Python 3.13.5) and a syntax-only check of the firewall file in a throwaway network namespace (no packets, nothing exposed). **Every other command is est.** (not run): the `doctl` commands, the `ssh` and `scp` commands, everything on the server, and every PowerShell command. Cowrie was not installed or started by the author. Expect to hit a command that needs a small fix, and treat that as part of the exercise rather than a failure. The latest Cowrie release when read was 3.1.3 (2026-10-19).

> **Prerequisites.** [Anatomy of a cloud honeypot](Deception-and-Honeypots-Cloud-Sensor-Anatomy.md) (lesson 7) with the plan on paper; [Deception safety and law](Deception-and-Honeypots-Safety-and-Law.md) (lesson 6) with a reviewer who answered "yes"; **the provider's written consent**; and a cloud account of your own that holds nothing else. You also need an SSH client and a key pair ([Hashing, encryption and keys](Hashing-Encryption-and-Keys.md) explains them), and optionally the provider's command-line tool, `doctl`. About 3 to 4 hours of your time (est.) plus the window you choose. **Cost: it uses your own provider bill.** The figure is below, before any step.

## What you will be able to do

- Write the teardown before you build, and use it.
- Build a small server whose real SSH is on a port only you can reach, with a second firewall layer on the host, and outgoing traffic closed once it is built.
- Install and configure Cowrie from its own documentation, run it as an unprivileged user, and put it on the ports visitors try.
- Plant a honeytoken (a decoy credential in a decoy file) inside Cowrie's fake file system.
- Run it for a stated window, pull the logs out over your management port, and delete everything.

## The free theory path

The theory path of track 2 is lesson 7, plus reading this page without running it. Lesson 9 also has a part that needs no cloud account at all: it reads invented sensor logs. If you do not want a bill, stop reading here and go on to lesson 9.

## Cost first

From [`docs/cost-prices.json`](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/cost-prices.json) (retrieved 2026-10-21): the `s-1vcpu-1gb` droplet is **$6 a month**. This lesson uses that one droplet and nothing else: no log bucket (the $5 bucket in [`docs/cost.md`](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/cost.md) is the design's option A and is not used here), no backups, no snapshots, no volumes, no reserved address. [Lesson 7](Deception-and-Honeypots-Cloud-Sensor-Anatomy.md#what-it-costs-and-what-is-not-a-cap) has the arithmetic: $6 is the most one such droplet costs in a month, and a 48-hour weekend is about $0.43 (est.). That figure is not a quote for your account. Region and size availability differ by account; this repository's cost page records a `422 Size is not available in this region` on a new account, so check yours with `doctl compute size list` before you pick.

**You enforce the limit.** The provider's own page says a spend alert "is not a spending cap". Use all five layers from lesson 7. The two that matter most on the day are the end date and the destroy command, which you write next.

## Teardown first

Do not create anything until this section is on paper.

| Item | What you write |
|---|---|
| End date and time | A real date, in your calendar, with an alarm. A weekend sensor ends on Monday morning, not "when I get to it". |
| Who reads the abuse inbox | You, daily, until the droplet is deleted. |
| Kill switch layer 1: stop attracting traffic | Remove the inbound rules for ports 22 and 23 (a one-minute action in the console). |
| Kill switch layer 2: delete the server | Destroy the droplet. Do not rely on power-off: the provider's pricing page says a powered-off droplet is still billed. |
| Kill switch layer 3: delete the rest | The firewalls, the access token you made for `doctl`, and any key made only for this. |
| Triggers to use it **at once** | A message from the provider; any outgoing connection from the server that you did not expect; any sign of a path to anything else of yours; a spend alert; the end of the window; a published exploit for Cowrie. |
| Proof | A listing of droplets, firewalls, snapshots, volumes and reserved addresses that shows none of them, and the billing page the next day. |

The commands for layer 2 and 3 and for the proof (replace the IDs and names with yours; **est.**):

```bash
doctl compute droplet delete cowrie-lab --force
doctl compute firewall list --format ID,Name
doctl compute firewall delete FIREWALL_ID --force
doctl compute droplet list
doctl compute snapshot list
doctl compute volume list
doctl compute reserved-ip list
```

```powershell
doctl compute droplet delete cowrie-lab --force
doctl compute firewall list --format ID,Name
doctl compute firewall delete FIREWALL_ID --force
doctl compute droplet list
doctl compute snapshot list
doctl compute volume list
doctl compute reserved-ip list
```

(`doctl` is the same program on every system, so the commands are the same in both shells. `--force` skips the confirmation prompt: with it, there is no second chance, which is the point on the end date.)

**Exercise 0: write it.**

**Predict.** How long will the teardown take on the end date? (The author's guess: five minutes if it is written down, fifty if it is not.)

**Do.** Fill in the table, with your real end date, on one page. Run `doctl compute droplet list` once now, in your empty account, so you know what an empty listing looks like.

**Check.** A reviewer can follow the page and delete everything without asking you anything.

**Undo.** Nothing: it is paper.

## The plan: addresses, ports and two firewalls

The addresses below are documentation placeholders. In your shell you will use your own; never put them in a file you share.

| Name | Placeholder | Meaning |
|---|---|---|
| `SENSOR` | `192.0.2.10` | The server's public address, which the provider shows you once it exists. |
| `YOU` | `203.0.113.10` | **Your** public address, the only one allowed to reach the management port. Your router's status page shows it. It may change (most homes have a changing address): if it does you are locked out until you edit the firewall from your account console. |
| `MGMT_PORT` | `49152` | The port real SSH moves to. Pick your own between 1024 and 65535, not 22, 23, 2222 or 2223. |

Two firewalls, by tag, on the **cloud** side. The provider's pages (read 2026-10-22) say that when more than one firewall applies to a droplet, "the rules from every one of those firewalls are combined into a single set", that allow rules are additive, and that a firewall blocks "all traffic that isn't expressly permitted by a rule". That makes the second firewall easy to remove:

| Firewall | Tag | Inbound | Outbound | When |
|---|---|---|---|---|
| `cowrie-lab-core` | `cowrie-lab-core` | TCP `MGMT_PORT` from `YOU/32` only; **later**, TCP 22 and 23 from anywhere | **none** | The whole life of the server |
| `cowrie-lab-build` | `cowrie-lab-build` | TCP 22 from `YOU/32` only | TCP 80, 443 and 53, UDP 53 and 123, to anywhere | **Only while you install**; deleted before you expose anything |

With no outgoing rule at all, the provider's page says no outgoing traffic is permitted. Your own connections in still work, because the firewall is stateful. IPv6 is off on a new droplet unless you turn it on (the provider's IPv6 page says droplets get IPv4 addresses by default), so these rules are written for IPv4 only; do not enable IPv6.

On the **host**, the same story again in a file the server loads (guardrails 2, 3 and 6). `LEARNER_ADDR` and `MGMT_PORT` are placeholders you replace with `sed` in exercise 5:

```nft
#!/usr/sbin/nft -f
# Host firewall for the sensor. Replace LEARNER_ADDR and MGMT_PORT before loading.
# nat: a visitor's port 22 and 23 are redirected to the unprivileged ports Cowrie listens on.
# filter: drop everything not listed; allow replies; allow nothing outgoing except replies.
flush ruleset

table ip nat {
    chain prerouting {
        type nat hook prerouting priority dstnat; policy accept;
        tcp dport 22 redirect to :2222
        tcp dport 23 redirect to :2223
    }
}

table inet filter {
    chain input {
        type filter hook input priority filter; policy drop;
        iif "lo" accept
        ct state established,related accept
        ip saddr LEARNER_ADDR tcp dport MGMT_PORT accept
        tcp dport { 2222, 2223 } accept
    }
    chain forward {
        type filter hook forward priority filter; policy drop;
    }
    chain output {
        type filter hook output priority filter; policy drop;
        oif "lo" accept
        ct state established,related accept
    }
}
```

Why the input chain lists 2222 and 2223 and not 22 and 23: the redirect happens first (the "prerouting" step), so by the time the filter looks at a packet, its port has already been rewritten. The Cowrie installation page gives the same redirect as `nft add rule ip nat prerouting tcp dport 22 redirect to 2222` and warns that "these rules do not apply to loopback", so test from another machine. The page's one-line command assumes the table and chain already exist; the file above creates them.

## Exercise 1: make the lure (a honeytoken)

A **honeytoken** is a fake piece of data with no use except to be noticed when used ([What deception is](Deception-and-Honeypots-What-Deception-Is.md#the-vocabulary)). Cowrie's fake file system can hold a file that a visitor reads with `cat`. This script makes the file on **your** computer, with an invented user name and an invented password that exist nowhere. Nothing about it is real and nothing about it is a secret.

```python
# Builds the lure file for the sensor's fake filesystem. Everything is invented at run time:
# the user name and the password are random and belong to no real system. Run:
#   python3 -I make_lure.py
import os, secrets

user = "svc-backup-" + secrets.token_hex(3)
password = secrets.token_urlsafe(12)
os.makedirs("lure", exist_ok=True)
with open("lure/deploy-notes-OLD.txt", "w") as f:
    f.write(
        "old backup login, do not use\n"
        f"user: {user}\n"
        f"password: {password}\n"
    )
print("built lure/deploy-notes-OLD.txt")
```

**Predict.** Run it twice. Will the two files have the same password?

**Do.**

```bash
mkdir -p ~/deception-lab/cloud && cd ~/deception-lab/cloud
python3 -I make_lure.py
cat lure/deploy-notes-OLD.txt
wc -c lure/deploy-notes-OLD.txt
```

```powershell
New-Item -ItemType Directory -Force $HOME\deception-lab\cloud | Out-Null
Set-Location $HOME\deception-lab\cloud
py -3 -I make_lure.py
Get-Content lure\deploy-notes-OLD.txt
(Get-Item lure\deploy-notes-OLD.txt).Length
```

(Save the script as `make_lure.py` in that folder first.)

**Check.** It prints `built lure/deploy-notes-OLD.txt`, then three lines: a title, a `user:` line with `svc-backup-` and six hex characters, and a `password:` line with a random string. The byte count is about 75 (you will need it in exercise 4). Run it again: the password differs, because it is built at run time and committed nowhere.

**Undo.** `rm -r lure` (PowerShell: `Remove-Item -Recurse lure`).

## Exercise 2: create the firewalls and the server

Do this in your own account, after the consent and the teardown page. Two ways: the web console, or `doctl`. The console path is the one with screenshots to take yourself (placeholders below); the `doctl` path is shorter and is the one the commands use.

*Screenshot to take yourself: the create-droplet page with the size, region, image and tags chosen. Blur your account name, address and key.*

**Do.** With `doctl` (the console works too). First your token: create a personal access token in the console with only the permissions you use (est.), and give it to `doctl` with `doctl auth init`. Treat the token like a password and plan to delete it in teardown. Then:

```bash
YOU=203.0.113.10
MGMT_PORT=49152
doctl compute firewall create --name cowrie-lab-core --tag-names cowrie-lab-core \
  --inbound-rules "protocol:tcp,ports:${MGMT_PORT},address:${YOU}/32"
doctl compute firewall create --name cowrie-lab-build --tag-names cowrie-lab-build \
  --inbound-rules "protocol:tcp,ports:22,address:${YOU}/32" \
  --outbound-rules "protocol:tcp,ports:80,address:0.0.0.0/0 protocol:tcp,ports:443,address:0.0.0.0/0 protocol:tcp,ports:53,address:0.0.0.0/0 protocol:udp,ports:53,address:0.0.0.0/0 protocol:udp,ports:123,address:0.0.0.0/0"
doctl compute image list-distribution
doctl compute droplet create cowrie-lab --region tor1 --size s-1vcpu-1gb --image debian-12-x64 \
  --ssh-keys YOUR_KEY_FINGERPRINT --tag-names cowrie-lab-core,cowrie-lab-build --wait
```

```powershell
$You = "203.0.113.10"
$MgmtPort = "49152"
doctl compute firewall create --name cowrie-lab-core --tag-names cowrie-lab-core `
  --inbound-rules "protocol:tcp,ports:$MgmtPort,address:$You/32"
doctl compute firewall create --name cowrie-lab-build --tag-names cowrie-lab-build `
  --inbound-rules "protocol:tcp,ports:22,address:$You/32" `
  --outbound-rules "protocol:tcp,ports:80,address:0.0.0.0/0 protocol:tcp,ports:443,address:0.0.0.0/0 protocol:tcp,ports:53,address:0.0.0.0/0 protocol:udp,ports:53,address:0.0.0.0/0 protocol:udp,ports:123,address:0.0.0.0/0"
doctl compute image list-distribution
doctl compute droplet create cowrie-lab --region tor1 --size s-1vcpu-1gb --image debian-12-x64 `
  --ssh-keys YOUR_KEY_FINGERPRINT --tag-names cowrie-lab-core,cowrie-lab-build --wait
```

Notes on the choices. **Debian 12** is the system the Cowrie installation page says it last verified on ("last verified on Debian Bookworm"); its Python is new enough, since Cowrie 3.1.3 needs 3.11 or newer. The image name `debian-12-x64` and the `tor1` region are **est.**: the `image list-distribution` command lists the names your account can use, and `doctl compute size list` the sizes. Use a region near you with the $6 size available. The flags used are the ones on the provider's `doctl` reference pages (read 2026-10-22). An open question on those pages: the "Configure Firewall Rules" page says `doctl` does not support a rule's `action` field and that deny rules need the API, while the `doctl` reference for `firewall create` documents an `action` key. This lesson uses no deny rule (everything not allowed is already denied), so it does not depend on the answer; if you want deny rules, test which page is right on a firewall that has nothing attached.

**Predict.** Which of the two firewalls would you expect to let you reach the server by SSH on port 22 right now, and which would not?

**Check.** `doctl compute droplet list --format Name,PublicIPv4,Tags` shows `cowrie-lab` with an address (that is `SENSOR`) and both tags. In the console, each firewall shows the rules in the table above and the droplet under "applied to". `ssh -o PasswordAuthentication=no root@SENSOR` works from your computer (only `YOU` is allowed). From any other network, port 22 does not answer (try a phone's hotspot; a timeout, not a refusal).

**Undo.** The teardown commands.

## Exercise 3: prepare the server

The server is Linux, so every command in this exercise and the next three runs **on the server in Bash**; PowerShell has nothing to add except the `ssh` and `scp` lines on your own side, which are the same.

**Do.** Log in as the administrator the image gives you (the provider's Debian image logs in as `root` with your key, est.) and do the housekeeping:

```bash
ssh root@SENSOR
# on the server:
apt-get update && apt-get -y upgrade
apt-get -y install sudo nftables python3-venv python3-pip libssl-dev libffi-dev build-essential libpython3-dev
adduser --disabled-password --gecos "" admin
usermod -aG sudo admin
echo 'admin ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/admin && chmod 440 /etc/sudoers.d/admin
install -d -m 700 -o admin -g admin /home/admin/.ssh
cp /root/.ssh/authorized_keys /home/admin/.ssh/authorized_keys
chown admin:admin /home/admin/.ssh/authorized_keys
adduser --disabled-password --gecos "" cowrie
```

The package list is the Cowrie installation page's Debian list (`python3-pip python3-venv libssl-dev libffi-dev build-essential libpython3-dev`), minus `authbind` (the redirect does that job), plus `sudo` and `nftables`. `NOPASSWD` sudo is a convenience that is acceptable only because the box holds nothing and only your key reaches it. The `cowrie` user has no password and no login key: it only runs the honeypot.

Now move real SSH. Do it in this order, and **do not close your first session until the new one works**:

```bash
# still on the server, as root
cat > /etc/ssh/sshd_config.d/10-lab.conf <<'EOF'
Port 49152
PermitRootLogin no
PasswordAuthentication no
KbdInteractiveAuthentication no
AllowUsers admin
EOF
sshd -t && systemctl restart ssh
ss -ltnp | grep sshd
```

(`49152` is `MGMT_PORT`; use yours. Debian 12's main SSH configuration includes the files in `/etc/ssh/sshd_config.d/`, est. Ubuntu has started SSH from a systemd socket since 22.10, and forum posts show a changed port surprising people, which is one reason this lesson uses Debian.) Then, from a **second** terminal on your computer:

```bash
ssh -p 49152 admin@SENSOR
```

```powershell
ssh -p 49152 admin@SENSOR
```

**Predict.** After the restart, what does `ss -ltnp` show for SSH: port 22, port 49152, or both?

**Check.** `ss` shows only `49152` for `sshd`. The second terminal logs you in as `admin`. `ssh root@SENSOR` (port 22) now fails: nothing is listening there. The cloud firewall rule for 22 from `YOU` is harmless but now pointless; it goes with the build firewall.

**Undo.** If you are locked out, do not fight it: the server is disposable. Delete it and make a new one.

## Exercise 4: install Cowrie, give it a fake home and a lure

**Do.** Everything here follows the Cowrie [installation page](https://raw.githubusercontent.com/cowrie/cowrie/HEAD/INSTALL.rst), read on 2026-10-22. It recommends installing the published package into a virtual environment, and says Cowrie "refuses to start as root". **Pin the version** so a rebuild gets the same code. As the `cowrie` user:

```bash
sudo -iu cowrie
mkdir ~/my-honeypot && cd ~/my-honeypot
python3 -m venv cowrie-env
source cowrie-env/bin/activate
python -m pip install --upgrade pip
python -m pip install "cowrie==3.1.3"
cowrie init
```

`cowrie init` writes `etc/cowrie.cfg`, and the first `cowrie start` creates the log directories and the host keys. Cowrie reads built-in defaults first and then your `etc/cowrie.cfg`, so the file only needs the keys you change. Write these (`hostname` is yours to choose: pick a plausible name that mentions nothing about honeypots, and nothing of yours):

```ini
[honeypot]
hostname = web03
download_limit_size = 1048576

[ssh]
forwarding = false

[telnet]
enabled = true
```

What each line does, from the default configuration file (read 2026-10-22): `hostname` is the name in the visitor's shell prompt (the default is `svr04`); `download_limit_size` caps a stored file at 1 MiB (the default has no limit); `forwarding = false` turns off SSH direct-tcpip forwarding, which is on by default and which you do not want near an "open proxy" clause; and telnet is off by default, so `enabled = true` is what turns it on. Telnet adds exposure and visitors; leave it out if you want less.

The fake home and the lure. Cowrie's `HONEYFS` documentation says a file the visitor can read needs both an entry in the fake file system and content for it. The installation page says the bundled file system is read-only for operators: copy it out, point Cowrie at the copy, and edit the copy with `fsctl`. Copy the lure from your computer first (the `scp` runs on **your** side):

```bash
scp -P 49152 -r lure admin@SENSOR:/tmp/lure
```

```powershell
scp -P 49152 -r lure admin@SENSOR:/tmp/lure
```

On the server, as `cowrie` (still in `~/my-honeypot` with the environment active):

```bash
sudo install -d -o cowrie -g cowrie /home/cowrie/lure
sudo install -o cowrie -g cowrie -m 644 /tmp/lure/deploy-notes-OLD.txt /home/cowrie/lure/
python -c "from cowrie.core.resources import read_data_bytes; open('var/lib/cowrie/fs.pickle', 'wb').write(read_data_bytes('fs.pickle'))"
printf '\n[shell]\nfilesystem = var/lib/cowrie/fs.pickle\n' >> etc/cowrie.cfg
SIZE=$(wc -c < /home/cowrie/lure/deploy-notes-OLD.txt)
echo "$SIZE"
fsctl var/lib/cowrie/fs.pickle
```

At the `fs.pickle:/$` prompt (the pattern is the one in Cowrie's FAQ; use the byte count `SIZE` printed above):

```text
touch /home/phil/deploy-notes-OLD.txt SIZE
chown 1000:1000 /home/phil/deploy-notes-OLD.txt
load /home/phil/deploy-notes-OLD.txt /home/cowrie/lure/deploy-notes-OLD.txt
exit
```

The fake user `phil` is Cowrie's default account (the FAQ says "Having the same user always available is an easy way to identify Cowrie"). Lesson 9 comes back to that: for now, the lure lives where the default visitor lands. Start it and test **from the server itself**, using the port Cowrie listens on (the redirect does not apply on the same machine):

```bash
cowrie start
cowrie status
exit    # back to admin
ssh -p 2222 -o PubkeyAuthentication=no -o PreferredAuthentications=password root@localhost
```

At the password prompt type any short invented word (not `root`, not `123456`). Cowrie's built-in login list, read in its source on 2026-10-22, accepts the user `root` with any password except `root`, `123456` and anything containing "honeypot", and the user `phil` with any password; a different list can go in `etc/userdb.txt`. Inside, run `uname -a`, `cat /home/phil/deploy-notes-OLD.txt` and `exit`. The options on that `ssh` line stop your own client from offering your real keys to the imitation: a key offered to a honeypot is a key written in its log.

**Predict.** Will the `cat` show your lure file's text? And what do you expect `uname -a` to claim?

**Check.** `cowrie status` says it is running. The `cat` prints the three lines from your file. `uname -a` prints the kernel text from Cowrie's configuration (`6.1.0-21-amd64` by default, est. since the file may differ per release), not the real kernel. `~/my-honeypot/var/log/cowrie/cowrie.json` now has lines for your own visit, from `127.0.0.1`: look at it with `tail -n 3` (lesson 9 teaches reading it).

**Undo.** `cowrie stop` as the `cowrie` user.

## Exercise 5: lock it down, then close the outgoing door

This is the point of no return for safety, so it is slow on purpose.

**Do.** Step 1, write the host firewall with your values, check it, and set a safety net. As `admin`:

```bash
sudo nano /etc/nftables.conf      # paste the file from the plan section above, then save
sudo sed -i 's/LEARNER_ADDR/203.0.113.10/; s/MGMT_PORT/49152/' /etc/nftables.conf
sudo nft -c -f /etc/nftables.conf && echo SYNTAX_OK
sudo systemd-run --on-active=5m --unit=nft-revert nft flush ruleset
sudo nft -f /etc/nftables.conf
```

Use your own address and port in the `sed` line. `nft -c` only checks the file. The `systemd-run` line schedules a flush five minutes from now, so if you load a rule that locks you out, the box opens again by itself (est.; the cloud firewall still guards it). Now, from a **new** terminal on your computer, run `ssh -p 49152 admin@SENSOR`. If it works, cancel the net and keep the rules for a reboot:

```bash
sudo systemctl stop nft-revert.timer
sudo systemctl enable nftables
```

**2. Delete the build firewall.** This closes the outgoing door at the provider's layer. On your computer:

```bash
doctl compute firewall list --format ID,Name
doctl compute firewall delete BUILD_FIREWALL_ID --force
```

```powershell
doctl compute firewall list --format ID,Name
doctl compute firewall delete BUILD_FIREWALL_ID --force
```

**3. Prove nothing leaves.** On the server, as `admin`:

```bash
curl -m 5 -sS https://example.com -o /dev/null; echo "exit=$?"
```

**Predict.** What exit code?

**Check.** `curl` fails: the error says a timeout or that it could not resolve the name, and `exit=` is not `0` (typically `6` or `28`; the number is curl's, est.). If you get `0`, **stop**: something still allows traffic out. Fix it before you go on.

**Undo.** `sudo nft flush ruleset` opens the host layer (the cloud layer is the firewalls).

## Exercise 6: open the lure ports and run the window

**Predict.** How long until the first visitor that is not you? Write a number down now, before you open anything.

**Do.** Now, and only now, expose it. Check the list once more: consent in writing, the end date on the calendar, the abuse inbox in front of you, the outgoing test just failed. Note the time:

```bash
date -u +%Y-%m-%dT%H:%M:%SZ
```

```powershell
(Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
```

Write it down: it is `T_open`. Then open ports 22 and 23 to everyone on the core firewall (the console has an "add inbound rule" button; here is `doctl`):

```bash
doctl compute firewall add-rules CORE_FIREWALL_ID \
  --inbound-rules "protocol:tcp,ports:22,address:0.0.0.0/0 protocol:tcp,ports:23,address:0.0.0.0/0"
```

```powershell
doctl compute firewall add-rules CORE_FIREWALL_ID `
  --inbound-rules "protocol:tcp,ports:22,address:0.0.0.0/0 protocol:tcp,ports:23,address:0.0.0.0/0"
```

If the server was restarted since exercise 4, start Cowrie again as the `cowrie` user (`cd ~/my-honeypot && source cowrie-env/bin/activate && cowrie start`); it does not start by itself, and that is a safe way to fail.

**Test from another machine** (the redirect does not apply to the server's own loopback): from a network that is not the one allowed on the management port, or from your own computer's `ssh`, with keys disabled:

```bash
ssh -o PubkeyAuthentication=no -o PreferredAuthentications=password -p 22 root@SENSOR
```

Any short invented password will log in (see exercise 4). Do not use a password you use anywhere. Type `exit`. Your own visit is in the log too; lesson 9 shows how to leave it out of the count.

**While it runs, do three things each day, and nothing else:** read the abuse inbox; look at the billing page against your arithmetic; log in on the management port and run `cowrie status`. Do not "improve" the box while it is exposed: a change is a rebuild. And do not look back at any address that appears in the log: no scan, no login attempt, no report by script.

*Screenshot to take yourself: the billing usage page after day one. Blur everything that identifies the account.*

**Check.** Within hours (est.; the ISC's own FAQ says even a home connection sees "several attacks a day"), the log has connection events from addresses you do not know. Your **time to first attempt** is the earliest `cowrie.session.connect` that is not yours, minus `T_open`. Write the number down.

**Undo.** Layer 1 of the kill switch: remove the two inbound rules for 22 and 23.

## Exercise 7: pull the logs, then tear down

**Predict.** What will the teardown listings show if it worked, and what could still be billing that they do not list?

**Do.** Pull the logs out **before** you delete the server, over the management port, and delete the copies on the server. As `admin` on the server first:

```bash
sudo -u cowrie ls -l /home/cowrie/my-honeypot/var/log/cowrie
sudo tar -C /home/cowrie/my-honeypot/var/log -czf /home/admin/cowrie-logs.tgz cowrie
```

Then on your computer:

```bash
scp -P 49152 admin@SENSOR:/home/admin/cowrie-logs.tgz .
tar -xzf cowrie-logs.tgz
ls cowrie
```

```powershell
scp -P 49152 admin@SENSOR:/home/admin/cowrie-logs.tgz .
tar -xzf cowrie-logs.tgz
Get-ChildItem cowrie
```

By default Cowrie rotates its logs at midnight (the default configuration sets `logtype = rotating`), so you may see dated files next to `cowrie.json`; copy the whole directory, as above, rather than one file. The logs are the raw material of lesson 9. They hold other people's addresses and the passwords they typed, so **they stay on your computer and are never posted** ([lesson 6](Deception-and-Honeypots-Safety-and-Law.md#recording-people-who-did-not-agree)); delete them when you finish, or within a retention you chose in advance (the design proposes 30 days for raw logs, an estimate and not a legal rule).

Then run the teardown from the top of this page. Do not stop at the droplet:

```bash
doctl compute droplet delete cowrie-lab --force
doctl compute firewall delete CORE_FIREWALL_ID --force
doctl compute droplet list
doctl compute firewall list
doctl compute snapshot list
doctl compute volume list
doctl compute reserved-ip list
```

**Check.** Every listing is empty. Delete the API token you created for `doctl` in the console, and any SSH key made only for this. Look at the billing page the next day: usage for the droplet should have stopped.

**Undo.** There is no undo for a destroyed droplet, which is what you wanted.

## Build, break, detect, evade, defend

- **Build.** The server, the two firewalls, the host rules, Cowrie, the lure.
- **Break.** Attack your own plan from the inside: with `ssh -p 22` from another network, try `wget`, `curl http://example.com`, `nc` and `ping` inside the Cowrie shell. Cowrie's `wget` imitation tries a real outgoing connection; with both firewalls closed it should fail, and the log should still record the attempt (the output documentation defines `cowrie.session.file_download.failed` for "a download the attacker attempted did not complete"; that it appears with a closed network is **est.**). Then, from the real shell, try the same `curl` as in exercise 5. Both should fail.
- **Detect.** What tells you something is wrong: a session from your management port you did not make (`last` on the server), a process other than Cowrie and `sshd` listening (`ss -ltnp`), any outgoing connection (`ss -tnp` should show only your session), a spend alert, a provider message. Write which you will check each day.
- **Evade.** What a visitor who wants to be sure it is a honeypot does, and what one who wants out of it does: that is lesson 9's [flip-the-board](Deception-and-Honeypots-Read-the-Sensor-Logs.md#flip-the-board-how-a-visitor-spots-cowrie-and-how-you-harden-it) section. For the escape case, write down what would happen if a visitor got a real shell as the `cowrie` user, step by step: what is on the box, what can they reach, what does the provider see?
- **Defend.** The nine guardrails of lesson 7 as controls: separate account, management port from your address only, only 22 and 23 open, nothing real, no route, no outgoing, a pull, a written teardown, a spend limit you enforce.
- **Flip the board.** You are the visitor. You have a root login on an unfamiliar machine and you are in a hurry. What is the first thing you run to decide if you are in a real machine, and which line of this lesson's configuration makes your test pass or fail? (The answer is in lesson 9. Write your guess first.)

## Common mistakes

| Mistake | Why it hurts | Better |
|---|---|---|
| Loading the host firewall before testing the management rule. | Lock-out, and you pay to rebuild. | Check with `nft -c`, keep the five-minute revert, test from a second terminal. |
| Opening 22 and 23 while the build firewall still allows outgoing traffic. | A taken-over sensor can attack others. | Delete the build firewall and prove with `curl` that nothing leaves. |
| Offering your own SSH keys to your own honeypot. | A key offered to a honeypot is written into its log. | `-o PubkeyAuthentication=no` every time. |
| Forgetting the end date. | A sensor left running is a bill and a hazard. | The alarm, the teardown commands, the daily check. |
| Powering the server off instead of deleting it. | A powered-off droplet is still billed. | Destroy it. |
| Publishing raw logs "for science". | Other people's addresses and passwords go public. | Counts and examples with addresses and passwords removed. |

## Claims register

Retrieved 2026-10-22 unless stated.

| Claim | Source | Status |
|---|---|---|
| Install steps, pip install into a virtual environment, `cowrie init`, `cowrie start`; "Cowrie refuses to start as root"; SSH defaults to port 2222; the nft redirect and the loopback warning; copying `fs.pickle` out and editing it with `fsctl`; Debian package list; "last verified on Debian Bookworm" | [Cowrie INSTALL.rst](https://raw.githubusercontent.com/cowrie/cowrie/HEAD/INSTALL.rst) | Read. Not run |
| Latest release 3.1.3 (2026-10-19); needs Python 3.11 or newer | [GitHub release](https://github.com/cowrie/cowrie/releases/tag/v3.1.3), [PyPI metadata](https://pypi.org/pypi/cowrie/json), [pyproject.toml at v3.1.3](https://raw.githubusercontent.com/cowrie/cowrie/v3.1.3/pyproject.toml) | Read |
| Default `hostname` `svr04`; telnet off by default; SSH port 2222 and telnet 2223; `forwarding = true` by default; `download_limit_size` unlimited by default; JSON log on by default at `var/log/cowrie/cowrie.json`; `logtype = rotating` by default | [Cowrie default configuration](https://raw.githubusercontent.com/cowrie/cowrie/HEAD/src/cowrie/data/etc/cowrie.cfg.dist) | Read, on the default branch (newer than 3.1.3 by an unknown amount). Not run |
| The built-in login list: `root` with any password except `root`, `123456` and any containing "honeypot"; `phil` with any password | [Cowrie source, `core/auth.py` at v3.1.3](https://raw.githubusercontent.com/cowrie/cowrie/v3.1.3/src/cowrie/core/auth.py) | Read |
| The default user is `phil` and "having the same user always available is an easy way to identify Cowrie"; the `fsctl` `touch`, `chown`, `load` pattern | [Cowrie FAQ](https://raw.githubusercontent.com/cowrie/cowrie/HEAD/docs/FAQ.rst) | Read. Not run |
| A file needs both an entry in the fake file system and content to be readable | [Cowrie HONEYFS documentation](https://raw.githubusercontent.com/cowrie/cowrie/HEAD/docs/HONEYFS.rst) | Read |
| `cowrie.session.file_download.failed` means "a download the attacker attempted did not complete" | [Cowrie output documentation](https://docs.cowrie.org/en/latest/_sources/OUTPUT.rst.txt) | Read. That it fires under a closed network is **est.** |
| A cloud firewall blocks all traffic not expressly permitted; no outbound rules means no outbound traffic; rules of several firewalls on one droplet are combined, allow rules additive, deny rules take precedence; it is stateful; droplets get IPv4 by default | [Firewall features](https://docs.digitalocean.com/products/networking/firewalls/details/features/) (Last verified 3 Sep 2026), [Configure rules](https://docs.digitalocean.com/products/networking/firewalls/how-to/configure-rules/) (Last verified 4 Aug 2026), [IPv6](https://docs.digitalocean.com/products/networking/ipv6/) | Read. Not run |
| The `doctl` flags used (`droplet create --tag-names --ssh-keys --wait`, `firewall create --inbound-rules --outbound-rules --tag-names`, `add-rules`, `delete --force`) and the "space-separated values for multiple rules" rule | [doctl reference](https://docs.digitalocean.com/reference/doctl/reference/compute/firewall/create/) | Read. Not run. The `action` key disagreement is described in exercise 2 |
| Billing ends on destroy; a powered-off droplet is still billed; spend alert "is not a spending cap"; $6 a month for `s-1vcpu-1gb` | See [lesson 7's register](Deception-and-Honeypots-Cloud-Sensor-Anatomy.md#claims-register), `docs/cost-prices.json` | Read |
| Ubuntu starts SSH from a systemd socket (since 22.10) and people were confused when port settings seemed ignored | [Ubuntu discourse thread on socket-based activation](https://discourse.ubuntu.com/t/sshd-now-uses-socket-based-activation-ubuntu-22-10-and-later/30189) | Read; the thread also says that in 24.04 the port is read from the SSH configuration by a generator, so the choice of Debian is caution, not a proven need |
| The host firewall file | `nft -c -f` in a throwaway user and network namespace on 2026-10-22 with the placeholders replaced | Syntax checked. Never loaded on a real host; whether the redirect and the drops behave as described is **est.** |
| The lure script | Run on 2026-10-22 with Python 3.13.5 | Run |
| The design's kill-switch layers, 30-day raw-log retention proposal | [Honeypot design](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/superpowers/specs/2026-10-21-honeypot-design.md), sections 7.2 and 10 | Read; the retention is the design's estimate |
| "Even a normal home connection will likely see several attacks a day" | [ISC honeypot page](https://isc.sans.edu/honeypot.html) | The ISC's claim |

Not verified, plainly: that any command here works on a real droplet; that Debian 12's image has the packages and SSH layout assumed; that the lock-out safety net works; what your provider will say to your request; the `NOPASSWD` sudo choice against your own risk view; time to first attempt on your sensor.

Next: [Read what arrived](Deception-and-Honeypots-Read-the-Sensor-Logs.md), lesson 9. Or back to the [track hub](Deception-and-Honeypots-Start-Here.md).
