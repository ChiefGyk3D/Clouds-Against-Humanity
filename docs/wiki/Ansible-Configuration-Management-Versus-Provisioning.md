# Ansible: configuration management versus provisioning

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

> **Prerequisites.** A terminal ([The terminal and your first script](Terminal-and-Your-First-Script.md)), enough SSH to know what a key login is ([Hashing, encryption and keys](Hashing-Encryption-and-Keys.md)), and the idea of infrastructure as code ([What is infrastructure as code](What-Is-Infrastructure-as-Code.md)). YAML helps ([Data formats: JSON, YAML, HCL](Data-Formats-JSON-YAML-HCL.md)). The free path needs Python 3 and about 300 MB of disk (est.) and touches nothing outside one folder. About two hours with the exercises (est.).

> **Status: unverified draft.** On **2026-11-07** I ran the free path on one Linux machine with ansible-core 2.22.0 installed with `pip` into a throwaway virtual environment, against **the same machine** (the `local` connection), writing only inside one folder. I observed: an ad hoc `ping`, a playbook run twice (changed 3, then 0), drift made by hand and shown by check mode with diff, a `shell` task that reports a change on every run, a vaulted variable used with and without the password, and a small role with a handler. **Not run:** anything over SSH to another machine, a VM or a container as a target, `ansible-pull`, Windows targets, cloud modules, `ansible-lint`, AWX or any Red Hat product, and Ansible next to OpenTofu. Vendor statements were read on **2026-11-07** from the pages named in the [claims register](#claims-register); anything I did not read or run is marked **est.** Trust what your terminal prints over what this page says.

> **Where this runs, and the rule.** The exercises never leave your computer: no remote host, no cloud account, no `sudo`, no package installs outside a virtual environment. A playbook can do a great deal of damage to a machine you point it at, so the habit this page teaches first is the dry run: check mode, then the real run, on a machine you can throw away.

<!-- BEGIN GENERATED PAGE NAV top: rewritten from docs/wiki/_nav.yaml by scripts/gen_wiki_nav.py; edit the manifest, not this block -->
[Home](Home.md) > [Track 1: Foundations](Contents.md#track-1-foundations) > Ansible: configuration management versus provisioning

Previous: [OpenTofu plans, state, drift and recovery](Plans-State-Drift-and-Recovery.md) / Next: [Spacelift from zero](Spacelift-From-Zero.md)
<!-- END GENERATED PAGE NAV top -->

<!-- BEGIN GENERATED PAGE CONTENTS: rewritten from the page's own headings by scripts/gen_wiki_nav.py; edit the headings, not this block -->
**On this page:**

- [What you will be able to do](#what-you-will-be-able-to-do)
- [What the wiki already says](#what-the-wiki-already-says)
- [Provisioning and configuration management](#provisioning-and-configuration-management)
- [What Ansible is](#what-ansible-is)
- [Inventory](#inventory)
- [Modules, tasks and playbooks](#modules-tasks-and-playbooks)
- [Idempotence](#idempotence)
- [Check mode and diff](#check-mode-and-diff)
- [Handlers and roles](#handlers-and-roles)
- [Ansible Vault](#ansible-vault)
- [ansible-pull](#ansible-pull)
- [Ansible, OpenTofu and cloud-init side by side](#ansible-opentofu-and-cloud-init-side-by-side)
- [When to pick which](#when-to-pick-which)
- [Honest limits](#honest-limits)
- [Free path: a playbook, run twice](#free-path-a-playbook-run-twice)
- [Build, break, detect, evade, defend](#build-break-detect-evade-defend)
- [Checkpoint](#checkpoint)
- [Common mistakes](#common-mistakes)
- [Claims register](#claims-register)
<!-- END GENERATED PAGE CONTENTS -->

## What you will be able to do

- Say what configuration management is and how it differs from provisioning.
- Explain agentless, push over SSH, and what must be on the managed machine.
- Read an inventory, a task and a playbook, and say what a module is.
- Run a playbook twice and explain why the second run changes nothing, and spot a task that breaks that.
- Use check mode with diff to see a change before it happens, and say where check mode cannot predict.
- Say what a role, a handler, Ansible Vault and `ansible-pull` are for.
- Decide between OpenTofu, cloud-init and Ansible for a given job, and name the honest limits of Ansible.

## What the wiki already says

This project does not use Ansible. [What is infrastructure as code](What-Is-Infrastructure-as-Code.md#where-cloud-init-fits) says why in one paragraph (OpenTofu creates the machine, cloud-init configures it on first boot) and [Droplet hardening](Droplet-Hardening.md#why-cloud-init-and-not-ansible) says when that stops being enough: "If stage 3 brings hosts with real state and drifting config, a configuration management tool earns its place then." This page is for that day, and for any job or lab where you meet Ansible first. [First hour on a new system](First-Hour-on-a-New-System-Updates-and-Baseline.md) mentions Ansible's `serial` option for rolling out patches in batches; nothing else here repeats it.

## Provisioning and configuration management

Two jobs get blurred because one person usually does both.

- **Provisioning** is creating the things: a network, a firewall, a virtual machine. The output is a resource that exists. OpenTofu does this ([OpenTofu from zero](OpenTofu-From-Zero.md)).
- **Configuration management** is what the machine looks like inside once it exists: which packages are installed, which users exist, what is in `/etc/ssh/sshd_config`, which service is running. The output is a machine in a described state. Ansible does this.

The line is not clean. OpenTofu can hand a machine a script at creation, and Ansible has modules that create cloud resources (est.; I did not read the cloud collections' documentation). I would still draw the line by what each tool is good at. OpenTofu keeps a **state** file and shows a **plan** before it changes anything, which suits things that are created and destroyed. Ansible looks at the machine itself on every run, which suits a machine that lives for years and has to be kept in shape.

## What Ansible is

Ansible is a command-line tool. You install it on one machine, the **control node**. It manages other machines, the **managed nodes**, and the vendor's own description is that it is agentless: "no databases or daemons required" (installation guide, read 2026-11-07). Nothing runs on the managed node between runs. When you run a playbook, Ansible connects, copies small Python programs over, runs them, collects the results and removes them (the connect-copy-run-clean sequence is how I understand it, est.).

That is **push**: you decide when, from where, to which machines. What the managed node needs, from the same guide: Python, and a user account that can connect over SSH with an interactive POSIX shell. The control node can be nearly any UNIX-like machine with Python; Windows without WSL is not supported as a control node. Windows can be a managed node over PowerShell remoting (read, not run).

The tool is `ansible-core`, licensed GPL version 3 (read 2026-11-07, the repository's `COPYING`). There is also a bigger community package that bundles many collections of extra modules; I installed only `ansible-core`, so everything below ran on that (est. for what the bigger package adds).

What agentless costs: you need a login path to every machine. That is a real thing in a project whose whole design is "no open port" ([Threat model](Threat-Model.md)). The control node ends up holding keys that open every machine it manages, so it is the most valuable machine in the fleet.

## Inventory

The **inventory** is the list of what you manage: hosts, and groups of hosts, in INI or YAML. The default file is `/etc/ansible/hosts`, and you point somewhere else with `-i` (read 2026-11-07). The lab inventory is two lines:

```ini
[lab]
localhost ansible_connection=local ansible_python_interpreter=auto_silent
```

`[lab]` is a group. `ansible_connection=local` means "do not SSH, run it here", which is what makes the free path safe. For a real machine you would write its name and let SSH do the rest.

## Modules, tasks and playbooks

A **module** is one unit of work with a name and arguments: `ansible.builtin.file` makes sure a path exists as a directory, `ansible.builtin.copy` makes sure a file has this content, `ansible.builtin.lineinfile` makes sure a line is present, `ansible.builtin.apt` makes sure a package is installed (that last one I did not run). `ansible-doc ansible.builtin.copy` prints the manual for a module on your own machine (observed).

A **task** is a module call with a name. A **play** is a list of tasks aimed at a group. A **playbook** is a YAML file holding one or more plays. Tasks run top to bottom, in order, on each host. Here is the one the exercises use:

```yaml
---
- name: Make a small config directory
  hosts: lab
  gather_facts: false
  vars:
    lab_dir: "{{ playbook_dir }}/sandbox"
  tasks:
    - name: Directory exists
      ansible.builtin.file:
        path: "{{ lab_dir }}"
        state: directory
        mode: "0755"

    - name: Greeting file has exactly this content
      ansible.builtin.copy:
        dest: "{{ lab_dir }}/hello.conf"
        content: |
          greeting = hello
          colour = blue
        mode: "0644"

    - name: One line is present in a second file
      ansible.builtin.lineinfile:
        path: "{{ lab_dir }}/settings.conf"
        line: "retries = 3"
        create: true
        mode: "0644"
```

Note the shape of each task. It does not say "make a directory". It says what the directory should be, `state: directory`. That is the same declarative idea as OpenTofu, applied one task at a time.

## Idempotence

The Ansible docs put it this way: "When the system is in the state your playbook describes, Ansible does not change anything, even if the playbook runs multiple times" (introduction, read 2026-11-07). The word is **idempotent**, and [What is infrastructure as code](What-Is-Infrastructure-as-Code.md#declarative-not-a-script) explains why it matters. In Ansible it is a property of each **module**, not of the tool. The bundled modules check first and change only if they must. A module that runs a command you wrote cannot know what the command does.

The run output ends in a recap. On my first run of the playbook above: `ok=3 changed=3`. On the second: `ok=3 changed=0`. Everything was already true, so nothing was touched.

Where it breaks:

- `ansible.builtin.shell` and `ansible.builtin.command` report `changed` on every run unless you tell them otherwise. I ran `shell: echo "retries = 3" >> file` twice: `changed=1` both times, and the file had the line twice (observed). The fix is to use a module that describes the end state (`lineinfile`) or to tell the task when to skip (`creates:` or `changed_when:`, est.; I did not run those).
- Two tasks that disagree. My first draft of the playbook had `copy` write the whole file and `lineinfile` add a line to the same file. Every run, `copy` removed the line and `lineinfile` put it back: `changed=2` forever (observed). Idempotent tasks can still fight each other, and the recap is how you notice.

## Check mode and diff

`--check` runs a playbook without changing anything. Modules that support it report what they would have changed; "Modules that do not support check mode report nothing and do nothing" (check mode page, read 2026-11-07). `--diff` adds before-and-after text for the files. Together they are the Ansible version of `tofu plan`, with a difference you must know: it is a prediction made task by task, not a computed plan. On a fresh empty folder I ran `--check --diff` and it failed at the third task, because the earlier tasks had not really created the folder or the file, so `lineinfile` found nothing to edit (observed, with my first draft; the fixed version has `create: true`). Check mode is most reliable on a machine that is already close to the target state, and least reliable when later tasks depend on earlier changes.

## Handlers and roles

A **handler** is a task that runs only when another task reports a change, once, at the end of the play. The usual use is "restart the service when its config file changed". In my role run the handler printed on the first run and not on the second (observed).

A **role** is a folder layout for reusable tasks: `tasks/`, `handlers/`, `defaults/` and so on, so a play can say `roles: [motd]` instead of pasting forty lines. `defaults/main.yml` holds values a caller can override. This is the Ansible counterpart of an OpenTofu module ([OpenTofu, stacks and modules](OpenTofu-Stacks-and-Modules.md)): the unit you reuse, with inputs. A public site called Ansible Galaxy hosts shared roles and collections; you are running other people's code as root on your machines when you use one, so read it first (general knowledge; I did not use Galaxy).

## Ansible Vault

Playbooks need secrets, and playbooks live in git. **Ansible Vault** encrypts a file (or a single value) so the encrypted text can be committed and the password is kept elsewhere (vault guide, read 2026-11-07). I encrypted a variables file and observed the file begin with `$ANSIBLE_VAULT;1.1;AES256`, the playbook run with the password file, and the same playbook fail without it with "Attempting to decrypt but no vault secrets found."

Know what it does not do. It protects the file at rest in the repository. Once the playbook runs, the plain value is on the control node and on the managed node (wherever the task puts it), and a task that prints it will print it into your terminal and logs unless it has `no_log: true`. The vault password is itself a secret you have to keep somewhere, which is the problem [Doppler and secrets](Doppler-and-Secrets.md) solves for this project, and the way this wiki treats secrets ([Identity, secrets and zero trust](Identity-Secrets-and-Zero-Trust-Basics.md)) does not change because Ansible has its own box for them.

## ansible-pull

Everything above is push. `ansible-pull` flips it: each managed node runs it, fetches a playbook from a version-control repository and applies it to itself. The manual's description is "pulls playbooks from a VCS repo and executes them on target host" and it is "useful both for extreme scale-out and periodic remediation" (CLI page, read 2026-11-07). Run from a timer, it means no control node holds keys to the fleet, and a machine that was off when you pushed catches up when it wakes. The costs: Ansible and a git client now live on every machine, the machine needs to reach the repository, and you have lost the single place where you watch a run happen. I read the manual and printed `ansible-pull --help`; I did not run it.

## Ansible, OpenTofu and cloud-init side by side

| Question | OpenTofu | cloud-init | Ansible |
|---|---|---|---|
| Job | Create and destroy resources | Configure a machine as it first boots | Keep an existing machine in a described state |
| Runs | Where you run it (here, in Spacelift) | On the machine, at first boot | From a control node, or on the machine with `ansible-pull` |
| Needs a login path in | No, it calls the provider's API | No, the machine configures itself | Yes, SSH (or another transport) to each machine, unless you use pull |
| Remembers what it built | Yes, a state file | No | No state file of its own; it looks at the machine each run (est.) |
| Preview before change | `plan`, computed | None; you rebuild to change | `--check --diff`, predicted task by task |
| Change to existing machine | Often rebuilds it | Changing user-data replaces the droplet here | Edits it in place |
| Weak at | Settings inside a long-lived machine | Anything after first boot | Creating and tracking cloud resources; removing what you stopped declaring (est.) |

The last cell is worth saying slowly. If you delete a task from a playbook, Ansible does not undo what it did; it just stops mentioning it. You need a task that says "absent" to remove something. OpenTofu notices a resource disappearing from the code because it has state; Ansible has none (general knowledge, est. as stated for this tool).

## When to pick which

- **A server you will rebuild instead of repair, with nothing precious on it:** cloud-init, with the template in the same pull request as the machine. That is what this project does.
- **A cloud resource: network, firewall, machine, bucket:** OpenTofu.
- **A machine that lives for years, holds data, and drifts as people and packages touch it:** a configuration management tool, and Ansible is the one with the lowest entry cost because it needs nothing installed on the target beyond Python and SSH (est. as a ranking; I did not compare it with Puppet, Chef or Salt).
- **A fleet where no single machine should hold keys to the others:** `ansible-pull` or something equivalent.
- **One-off tasks across several machines** (restart a service, check a version): an Ansible ad hoc command, `ansible lab -m ansible.builtin.ping`.
- **Both:** OpenTofu creates the machine and prints its address; a playbook then configures it. That handoff is the awkward part. The inventory has to learn the new address, either by writing it out or by a dynamic inventory plugin (est.; I did not build this).

## Honest limits

- **YAML with templating gets hard to read.** Conditions, loops and `{{ variables }}` in YAML are fine at 40 lines and unpleasant at 4,000.
- **Tasks are ordered steps, not a graph.** There is no plan that works out dependencies. You order them, and you fix the order when it breaks.
- **Speed.** Each task is a round trip to each machine over SSH. A long playbook across many machines is slow (est.; I ran one machine).
- **Check mode is a hint.** See above.
- **It only looks when you run it.** Drift in between is invisible until the next run. Running from a schedule narrows that and does not close it.
- **The control node is a prize.** Whoever owns it can log in everywhere. Treat it like a bastion, not a laptop.
- **You can still run it wrong.** A playbook with a wide `hosts:` and no check run is how people take a fleet down. The cure is the same as for OpenTofu: dry run, small batch first (`serial`, see [First hour on a new system](First-Hour-on-a-New-System-Updates-and-Baseline.md)), read the diff.

## Free path: a playbook, run twice

All of this is local and free. Everything lives in `~/ansible-lab` and the playbook writes only into a `sandbox` folder inside it. The target is your own machine over the `local` connection, so you need no second machine, no SSH and no root. If you would rather aim it at a throwaway VM or container later, see Exercise 7.

### Exercise 1: install ansible-core in a virtual environment

> **Run** on 2026-11-07 (ansible-core 2.22.0, Python 3.13).

1. **Predict.** Will installing Ansible change anything outside the folder? (No: the virtual environment holds it.)
2. **Do.**

   ```bash
   mkdir -p ~/ansible-lab && cd ~/ansible-lab
   python3 -m venv venv
   . venv/bin/activate
   pip install ansible-core
   ansible --version
   ```

3. **Check.** The first line prints `ansible [core ...]` with a version and the Python it uses.
4. **Undo.** `deactivate`, then remove the folder when you finish the page.

### Exercise 2: an inventory and an ad hoc command

> **Run** on 2026-11-07.

1. **Predict.** What will a `ping` module do on a machine with no network? (This `ping` is not ICMP. It connects, runs a tiny Python program and answers `pong`, which proves the login and Python both work.)
2. **Do.**

   ```bash
   cd ~/ansible-lab
   cat > inventory.ini <<'EOF'
   [lab]
   localhost ansible_connection=local ansible_python_interpreter=auto_silent
   EOF
   ansible -i inventory.ini lab -m ansible.builtin.ping
   ```

3. **Check.** `"ping": "pong"` and `"changed": false`.
4. **Undo.** Nothing to undo.

### Exercise 3: run a playbook twice

> **Run** on 2026-11-07. The recap lines I saw: `ok=3 changed=3` then `ok=3 changed=0`.

1. **Predict.** Before the first run, how many tasks will report `changed`? On the second?
2. **Do.**

   ```bash
   cd ~/ansible-lab
   cat > site.yml <<'EOF'
   ---
   - name: Make a small config directory
     hosts: lab
     gather_facts: false
     vars:
       lab_dir: "{{ playbook_dir }}/sandbox"
     tasks:
       - name: Directory exists
         ansible.builtin.file:
           path: "{{ lab_dir }}"
           state: directory
           mode: "0755"

       - name: Greeting file has exactly this content
         ansible.builtin.copy:
           dest: "{{ lab_dir }}/hello.conf"
           content: |
             greeting = hello
             colour = blue
           mode: "0644"

       - name: One line is present in a second file
         ansible.builtin.lineinfile:
           path: "{{ lab_dir }}/settings.conf"
           line: "retries = 3"
           create: true
           mode: "0644"
   EOF
   ansible-playbook -i inventory.ini site.yml
   ansible-playbook -i inventory.ini site.yml
   ```

3. **Check.** First recap `changed=3`, second `changed=0`, and `ls sandbox` shows `hello.conf` and `settings.conf`. Idempotence is the second recap.
4. **Undo.** `rm -r sandbox` if you want a clean start.

### Exercise 4: drift, then check mode with diff

> **Run** on 2026-11-07.

1. **Predict.** Someone edits `hello.conf` by hand. What does `--check --diff` show, and does it change the file?
2. **Do.**

   ```bash
   cd ~/ansible-lab
   sed -i 's/blue/red/' sandbox/hello.conf
   ansible-playbook -i inventory.ini site.yml --check --diff
   cat sandbox/hello.conf
   ansible-playbook -i inventory.ini site.yml
   cat sandbox/hello.conf
   ```

3. **Check.** The diff shows `-colour = red` and `+colour = blue`, the file still says `red` after the check, the real run reports `changed=1`, and then it says `blue`. That is [drift](What-Is-Infrastructure-as-Code.md#drift), found and repaired, with the difference that you only learned about it because you ran the playbook.
4. **Undo.** Nothing to undo.

### Exercise 5: a task that is not idempotent

> **Run** on 2026-11-07.

1. **Predict.** Run this twice. What does the recap say, and how many lines will the file have?
2. **Do.**

   ```bash
   cd ~/ansible-lab
   cat > bad.yml <<'EOF'
   ---
   - name: A task that cannot tell what it already did
     hosts: lab
     gather_facts: false
     tasks:
       - name: Append a line
         ansible.builtin.shell: echo "retries = 3" >> "{{ playbook_dir }}/sandbox/bad.conf"
   EOF
   ansible-playbook -i inventory.ini bad.yml
   ansible-playbook -i inventory.ini bad.yml
   cat sandbox/bad.conf
   ```

3. **Check.** `changed=1` both times and two lines in the file. Now rewrite it with `lineinfile` and see it settle at `changed=0`.
4. **Undo.** `rm sandbox/bad.conf`.

### Exercise 6: Vault and a role

> **Run** on 2026-11-07. The password and value below are made up for the lab; never commit a real password file.

1. **Predict.** What happens when you run a playbook that reads an encrypted file without giving the password?
2. **Do.**

   ```bash
   cd ~/ansible-lab
   echo 'lesson-vault-password' > vault-pass.txt && chmod 600 vault-pass.txt
   echo 'db_password: example-not-real' > secret.yml
   ansible-vault encrypt --vault-password-file vault-pass.txt secret.yml
   head -1 secret.yml
   cat > vault-use.yml <<'EOF'
   ---
   - name: Use a vaulted variable
     hosts: lab
     gather_facts: false
     vars_files:
       - secret.yml
     tasks:
       - name: Write the secret to a file only the owner can read
         ansible.builtin.copy:
           dest: "{{ playbook_dir }}/sandbox/db.conf"
           content: "password={{ db_password }}\n"
           mode: "0600"
         no_log: true
   EOF
   ansible-playbook -i inventory.ini vault-use.yml --vault-password-file vault-pass.txt
   ansible-playbook -i inventory.ini vault-use.yml
   ```

   Then the role:

   ```bash
   cd ~/ansible-lab
   mkdir -p roles/motd/tasks roles/motd/handlers roles/motd/defaults
   cat > roles/motd/defaults/main.yml <<'EOF'
   ---
   motd_text: hello from a role
   EOF
   cat > roles/motd/tasks/main.yml <<'EOF'
   ---
   - name: Write the message of the day
     ansible.builtin.copy:
       dest: "{{ playbook_dir }}/sandbox/motd"
       content: "{{ motd_text }}\n"
       mode: "0644"
     notify: Say that it changed
   EOF
   cat > roles/motd/handlers/main.yml <<'EOF'
   ---
   - name: Say that it changed
     ansible.builtin.debug:
       msg: "handler ran"
   EOF
   cat > use-role.yml <<'EOF'
   ---
   - name: Apply the motd role
     hosts: lab
     gather_facts: false
     roles:
       - motd
   EOF
   ansible-playbook -i inventory.ini use-role.yml
   ansible-playbook -i inventory.ini use-role.yml
   ansible-playbook -i inventory.ini use-role.yml -e motd_text=changed
   ```

3. **Check.** `head -1 secret.yml` prints `$ANSIBLE_VAULT;1.1;AES256`. The first vault run succeeds; the second fails with "Attempting to decrypt but no vault secrets found." For the role, the handler prints `handler ran` on the first run, not on the second, and again on the third, after the override changes the file. `stat -c '%a' sandbox/db.conf` prints `600`.
4. **Undo.** `rm -r roles sandbox secret.yml vault-pass.txt`.

### Exercise 7: aim it at a throwaway VM or container (written from reading)

> **Not run.** Everything above used the `local` connection. This step needs a second machine reachable over SSH, which I did not set up.

1. **Predict.** What changes in the inventory line when the target is another machine? (The `ansible_connection=local` goes away; Ansible uses SSH by default, and you add `ansible_host` and `ansible_user` for the name and login, est.)
2. **Do.** Use the guest from [Virtual machines and hypervisors](Virtual-Machines-Hypervisors-Desktop-and-Datacenter-Options.md) on its default NAT network, or a container you started with an SSH server in it. Give it Python and a key login. Add a group to `inventory.ini` with `ansible_host=127.0.0.1`, the port you forwarded, and the user. Run `ansible-playbook ... --check --diff` first, then the real run, then the real run again.
3. **Check.** The same `changed=3` then `changed=0`. The first time you connect, SSH asks you to trust the host key ([Hashing, encryption and keys](Hashing-Encryption-and-Keys.md#key-pairs-in-the-wild-ssh-keys-and-tls-certificates)); say yes only for your own throwaway machine.
4. **Undo.** Delete the guest or the container.

## Build, break, detect, evade, defend

A small loop on the lab you just built. Local and throwaway; no real systems.

**Build.** The playbook from Exercise 3, applied and idempotent.

**Break.** Edit `sandbox/hello.conf` by hand, as in Exercise 4. Nothing alerts you; Ansible does not watch.

**Detect.** `ansible-playbook ... --check --diff` is the detection: a non-empty `changed` count in check mode means the machine has drifted from the playbook. In a company you would run that on a schedule and alert on it (est.; [File integrity and alerting](File-Integrity-and-Alerting-Tripwire-AIDE-Wazuh.md) covers tools that watch without being asked).

**Evade, in words only.** An intruder who changes a managed file is undone by the next run, which is useful, and the intruder's clever answer is to stop the thing that runs it or to change the playbook in the repository. The second is why the repository and the control node deserve the protection a production server gets. This page shows no technique.

**Defend.** Playbooks in git with review, as for any code ([Git, GitHub and pull requests](Git-GitHub-and-Pull-Requests.md)); a dry run before a real one; secrets in Vault or a secrets service, with `no_log` on tasks that handle them; the control node patched and small; a limited account on the managed nodes, with only the privileges the playbook needs.

**Undo (the whole lab).** `deactivate`, then `rm -r ~/ansible-lab`.

### Flip the board

**The reviewer.** A teammate writes: "I have a playbook that sets up our web servers. I ran it on all forty from my laptop with the `shell` module to restart nginx every time, and the vault password is in the repo's README so nobody has to ask." Find at least five problems.

<details>
<summary>What to find</summary>

1. No dry run (`--check --diff`) and no small first batch before forty machines.
2. `shell` to restart nginx runs and reports a change on every run; a handler that fires only when the config changed does it properly.
3. The restart on all forty at once can take the site down; `serial` rolls it out in batches.
4. The vault password in the README makes the vault pointless.
5. A laptop as the control node: the keys to forty servers sit on a machine that travels.
6. No statement of which inventory group the run targeted, or how the teammate confirmed it was the right one.
7. No `no_log` or mention of where the plain secret ends up on the servers.

</details>

**The auditor.** A manager says: "We use Ansible, so our servers cannot drift." What is wrong with that? (Ansible corrects what it is run against, when it is run. Between runs, anyone can change anything, and anything not mentioned in a playbook is not managed at all.)

## Checkpoint

Without looking back: say what the difference is between provisioning and configuration management and which tool in this wiki does each; say what agentless means and what the managed node still needs; explain why the second run of a playbook reports no changes and name one module that would not; say what `--check --diff` shows and one case where it cannot predict; say what a handler, a role and Vault are for and what Vault does not protect; explain what `ansible-pull` changes about who holds the keys.

## Common mistakes

| Symptom or belief | What is really true | What to check |
|---|---|---|
| "Ansible installs an agent on each server" | It does not; it needs SSH and Python on the target | The installation guide's managed node requirements |
| "A second run that changes things is a bug in Ansible" | Often it is a `shell` or `command` task, or two tasks that fight | The recap; replace with a state module |
| "Check mode is `tofu plan`" | It is a task-by-task prediction and cannot see what earlier tasks would have created | Run it on a machine already near the target state |
| "Vault keeps my secret safe everywhere" | It protects the file at rest; the plain value exists at run time | `no_log: true`; where the task writes the value |
| "I deleted the task, so Ansible removed the thing" | It only stops managing it | Add a task with `state: absent` |
| "Ansible replaces OpenTofu" | They split on what changes how: resource creation versus machine contents | The side-by-side table |
| "`ping` tests the network" | The Ansible `ping` module tests login and Python | Exercise 2 |
| "A roles from the internet are safe because they are shared" | You run them with your privileges on your machines | Read the role first |

## Claims register

Retrieved **2026-11-07** with read-only requests. "Read" means I read the page text. "Observed" means I ran it and saw it. Everything else is marked as such.

| Claim | Source | Status |
|---|---|---|
| Agentless tool installed on one control node, manages nodes over SSH, PowerShell remoting and other transports, "no databases or daemons required" | docs.ansible.com, "Ansible installation guide" | Read |
| Managed node needs Python and an SSH-reachable user with an interactive POSIX shell; Ansible need not be installed on it | Same page, managed node requirements | Read |
| Control node: nearly any UNIX-like machine with Python; Windows without WSL not supported | Same page, control node requirements | Read |
| Idempotence quote: when the system is in the described state Ansible does not change anything | docs.ansible.com, "Ansible introduction" | Read |
| Default inventory file `/etc/ansible/hosts`, overridden with `-i` | docs.ansible.com, "Building an inventory" | Read |
| Check mode makes no changes; modules without support report nothing and do nothing; diff mode shows before and after | docs.ansible.com, "Check mode and diff mode" | Read |
| `ansible-pull` pulls playbooks from a VCS repo and runs them on the target host; useful for extreme scale-out and periodic remediation | docs.ansible.com, "ansible-pull CLI page" | Read; `--help` printed, not run |
| Vault encrypts and manages sensitive data such as passwords | docs.ansible.com, "Ansible Vault guide" | Read |
| ansible-core is licensed GPL version 3 | `COPYING` in the [ansible repository](https://github.com/ansible/ansible) (devel branch) | Read |
| ansible-core 2.22.0 installs with `pip` and `ansible --version` reports it | Local run | Observed |
| `ping` returns `pong`, `changed: false` | Local run, Exercise 2 | Observed |
| Playbook run twice: `ok=3 changed=3`, then `ok=3 changed=0` | Local run, Exercise 3 | Observed |
| `--check --diff` showed `colour = red` to `blue`, file unchanged; real run `changed=1` | Local run, Exercise 4 | Observed |
| `shell` append reports `changed=1` twice and writes the line twice | Local run, Exercise 5 | Observed |
| `copy` plus `lineinfile` on the same file gives `changed=2` every run; `--check --diff` on an empty folder failed at `lineinfile` | Local run of my first draft | Observed |
| Vault file starts `$ANSIBLE_VAULT;1.1;AES256`; run succeeds with password file, fails without it with "Attempting to decrypt but no vault secrets found."; `no_log` file mode `600` | Local run, Exercise 6 | Observed |
| Handler ran on the first role run, not the second, and again after a variable override | Local run, Exercise 6 | Observed |
| `ansible-doc ansible.builtin.copy` prints the module manual locally | Local run | Observed |
| Ansible modules that create cloud resources exist and could provision; how well they compare with OpenTofu | Not read | **est.** |
| Connect, copy a Python program, run, remove: the sequence for a task | My understanding of the transport | **est.** |
| No state file of its own; deleting a task does not undo its effect | General knowledge of the tool; I did not test removal | **est.** |
| `creates:` and `changed_when:` make a `command` or `shell` task idempotent | General knowledge; not run | **est.** |
| Galaxy hosts shared roles and collections | General knowledge; not visited | **est.** |
| Ansible is the lowest-entry-cost configuration manager compared with Puppet, Chef, Salt | Not compared | **est.** |
| Speed cost of a round trip per task per host | Not measured; one machine only | **est.** |
| Everything over SSH to a second machine, Windows targets, `ansible-pull`, the bigger community package, dynamic inventory | Not run | **est.** |

<!-- BEGIN GENERATED PAGE NAV bottom: rewritten from docs/wiki/_nav.yaml by scripts/gen_wiki_nav.py; edit the manifest, not this block -->
Where you are: [Home](Home.md) > [Track 1: Foundations](Contents.md#track-1-foundations) > Ansible: configuration management versus provisioning

Previous: [OpenTofu plans, state, drift and recovery](Plans-State-Drift-and-Recovery.md) / Next: [Spacelift from zero](Spacelift-From-Zero.md)

In this track: [Track 1: Foundations](Contents.md#track-1-foundations), 32 pages

- OS and Linux, git and the terminal: [Git from zero](Git-From-Zero.md) / [The terminal and your first script](Terminal-and-Your-First-Script.md) / [Linux for enterprise beginners](Linux-for-Enterprise-Beginners.md) / [First hour on a new system](First-Hour-on-a-New-System-Updates-and-Baseline.md) / [Patch management and automatic security updates](Patch-Management-and-Automatic-Security-Updates.md) / [Red and blue, and choosing your lab OS](Red-and-Blue-Yin-and-Yang-and-Your-Lab-OS.md) / [Virtual machines and hypervisors: desktop to datacenter](Virtual-Machines-Hypervisors-Desktop-and-Datacenter-Options.md) / [Virtual machines, containers and cloud service models](Virtual-Machines-Containers-and-Cloud-Service-Models.md) / [Kubernetes for beginners](Kubernetes-for-Beginners-What-It-Adds-Over-Docker-and-Compose.md) / [Windows, Active Directory and macOS](Windows-Active-Directory-and-macOS-in-the-Enterprise.md) / [Cron, systemd timers and init scripts versus systemd](Cron-Systemd-Timers-and-Init-Scripts-vs-Systemd.md)
- Networking: [How a web request works](How-a-Web-Request-Works.md) / [DNS, Cloudflare and hosting your own website](DNS-Cloudflare-and-Hosting-Your-Own-Website.md) / [Subnets, NAT and firewalls by hand](Subnets-NAT-and-Firewalls-By-Hand.md) / [Behind a CDN: real client IPs and OSI basics](Behind-a-CDN-Real-Client-IPs-and-OSI-Basics.md) / [IPv6 adoption and handling it safely](IPv6-Adoption-and-Handling-It-Safely.md)
- Identity and secrets: [APIs and tokens from zero](APIs-and-Tokens-From-Zero.md) / [Hashing, encryption and keys](Hashing-Encryption-and-Keys.md) / [Secrets from day one](Secrets-From-Day-One.md) / [Enterprise identity: SSO, SAML and OIDC](Enterprise-Identity-SSO-SAML-OIDC.md)
- Infrastructure as code: [Data formats: JSON, YAML, HCL](Data-Formats-JSON-YAML-HCL.md) / [OpenTofu from zero](OpenTofu-From-Zero.md) / [OpenTofu plans, state, drift and recovery](Plans-State-Drift-and-Recovery.md) / **Ansible: configuration management versus provisioning** / [Spacelift from zero](Spacelift-From-Zero.md) / [Build and destroy: one stack per service](Build-and-Destroy-Stack-Per-Service.md) / [Environments and promotion](Environments-and-Promotion-Dev-Staging-Production.md)
- Web hosting: [LAMP and LEMP from zero](LAMP-and-LEMP-From-Zero.md) / [WordPress and PHP security, WAFs and static sites](WordPress-and-PHP-Security-WAF-and-Static-Sites.md) / [Static against dynamic: Hugo, WordPress and recon](Static-vs-Dynamic-Sites-Hugo-and-WordPress-and-Recon.md) / [WordPress at scale: CDN, WAF, caching and CI](WordPress-at-Scale-CDN-WAF-and-CI.md) / [Autoscaling and elasticity](Autoscaling-and-Elasticity-Scale-Out-Targets-Cooldowns-and-Cost-Caps.md)

Related pages:

- [OpenTofu from zero](OpenTofu-From-Zero.md)
- [Build and destroy: one stack per service](Build-and-Destroy-Stack-Per-Service.md)
- [Data formats: JSON, YAML, HCL](Data-Formats-JSON-YAML-HCL.md)
- [Environments and promotion](Environments-and-Promotion-Dev-Staging-Production.md)
<!-- END GENERATED PAGE NAV bottom -->
