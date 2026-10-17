# GCP: the same four pieces

> **Status: unverified draft.** Written 2026-10-16 from Google's documentation (sources in the [phase 0 evidence](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/superpowers/specs/2026-10-16-multicloud-phase0-evidence-azure-gcp.md)). **No GCP version of this project has been built yet.** The resource lists below are a teaching map of what such a build would need, not code in this repository, and the actual build may differ. Not reviewed by anyone who runs GCP; please send corrections to [issue #22](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/issues/22).

Read [Why the clouds differ](Why-the-Clouds-Differ.md) and [OpenTofu, stacks and modules](OpenTofu-Stacks-and-Modules.md) first. This page walks the four pieces that this project builds on DigitalOcean (a private network, a firewall, a machine, an identity for the machine), points at the DigitalOcean file where each lives, and says what you would build on GCP instead and why it is not a one-line rename.

The method is the exercise: for each piece, **read the DigitalOcean file, predict the GCP resources, then check your list against the reference at the bottom of the piece.**

## Piece 1: the private network

**On DigitalOcean.** `modules/vpc/main.tf` is one resource, `digitalocean_vpc`, with a name, a region and an address range.

**On GCP.** A **VPC network** is also one resource, but its scope is different: *the network, with its routes and firewall rules, is global; subnets are regional.* So the network has no region and does not take an address range. The address ranges live on **subnets**, one or more per region, and a machine sits in a subnet.

The network has a **mode**:

- **Auto mode:** one subnet in every region is created for you, from the `10.128.0.0/9` block, and new regions are added automatically.
- **Custom mode:** no subnets exist until you create them. Google recommends custom mode for production.

Every new project starts with a network named `default`, in auto mode, with pre-populated firewall rules (including ingress for SSH and RDP and a rule that allows traffic between instances). A learner on a personal account cannot use an organization policy to prevent that, so the project's style would be: create your own **custom-mode** network with **one subnet in your one region**, and do not use `default`.

On the internet path: there is no internet gateway to build. Routes are part of the network, and a default route to the internet exists in a new network. What decides whether a machine can *use* it is whether the machine has an **external IP address** (or sits behind Cloud NAT). That is the choice [the cost lesson](Provider-GCP-Cost-Lesson.md) prices. (The default route's existence in a custom-mode network is from general GCP knowledge and was not re-read from a Google page on 2026-10-16: UNVERIFIED. Check the network's route list.)

**Why it matters.** AWS needed five resources to get a machine to the internet; GCP needs two (a network and a subnet), because the global network carries the routes. The lesson is not that GCP is simpler. It is that the *scope* of the object moved: a global network with regional subnets means a single network can quietly hold subnets you never chose, if you used auto mode.

**Predict, then check.** Without looking below, list the GCP resource types that replace `modules/vpc`, and say which one holds the address range.

*Reference: a VPC network (custom mode, no automatic subnets) and one subnet in your chosen region, which holds the address range. No gateway or route table resource is needed for a basic public path.*

## Piece 2: the firewall

**On DigitalOcean.** `modules/firewall/main.tf` makes a cloud firewall that applies to every droplet carrying a tag, allows nothing in by default, and lists explicit outbound rules, with sources and destinations that can themselves be tags.

**On GCP.** **Firewall rules** belong to the VPC network. Each rule has a direction (ingress or egress), an action (allow or deny), a priority (0 to 65535, default 1000, lower number first), and a **target**, which says which machines it applies to:

- no target set: every instance in the network;
- **network tags**: instances carrying the tag;
- **target service accounts**: instances running as that service account.

For ingress rules, the **source** can be address ranges, source tags, or source service accounts (tags and service accounts only match instances in the same network). For egress rules, the **destination** is **address ranges only**. This is the sharp difference from this project's DigitalOcean module: you cannot write "egress only to droplets carrying this tag."

Rules to remember:

- **Tags and service accounts cannot be mixed.** Google: you cannot use target service accounts and target network tags together in any firewall rule, ingress or egress, and tags and service accounts cannot be used in the same rule.
- **Implied rules.** Every network has an implied rule that denies ingress and one that allows egress, at the lowest priority. The page does not state their priority number, so this wiki does not teach one. (The pre-populated rules in the `default` network use priority 65534; do not infer the implied number from that.)
- **Stateful.** Once a connection is allowed in either direction, return traffic is allowed and you cannot deny it.
- **Service accounts are stricter than tags.** Anyone who can edit an instance can change its tags, so a tag is a weaker statement than "this instance runs as this identity."
- **Cost.** VPC firewall rules themselves are free as far as the evidence shows; no charge was found, but the pricing for the newer firewall product tiers was not checked: UNVERIFIED.
- **Hierarchical firewall policies** attach at an organization or folder. You have neither (see the [account preparation page](Provider-GCP-Account-Preparation.md)), so they are not available to you.

**What this build would look like.** With the implied deny-ingress rule, "nothing in from the internet" is already the starting state: you write **no** allow-ingress rule that opens a port to `0.0.0.0/0`. Because egress is allowed by default, the DigitalOcean module's explicit outbound list would be written as *deny* rules with lower-numbered (higher-priority) allows for what you want, or accepted as a looser default. Twingate lists the outbound traffic a connector needs: TCP 443, TCP 30000 to 31000, and UDP for peer-to-peer. A reasonable teaching design: a rule allowing those egress ports to `0.0.0.0/0`, a **separate, higher-priority egress allow for TCP 22 targeting the connectors, with the peers' internal addresses (or the subnet range) as the destination**, and a lower-priority deny-all egress. The SSH allow is needed because rules are stateful only for replies: the first packet of a connector-to-connector SSH connection is egress at the sending VM, and the deny-all would drop it before the other machine's ingress rule is ever consulted. Both ends need a rule, one egress and one ingress. The destination has to be an address range because egress destinations cannot be tags or service accounts (Google's firewall page, read 2026-10-16). Whether that breaks anything (DNS and the metadata server are the first suspects) is untested here.

For the two connectors to reach each other on SSH and nothing else to reach them, use **target and source service accounts** (the same dedicated service account on both), not tags, if you want the stricter form. Using tags is simpler and weaker.

**Predict, then check.** You want an ingress rule that lets the connectors reach each other and nothing else. Which of these can you use for the source: a tag, a service account, an address range? Can you put a tag in the target and a service account in the source of the same rule? Then: why can the outbound rule not name the other connector the same way?

*Reference: all three work as an ingress source, but a rule uses tags or service accounts, not both, so a tag target with a service-account source is refused. The egress destination can only be an address range, so "only to the other connector" has to be written as that machine's internal address range (or the whole subnet). If you also deny all egress, the sending machine needs its own TCP 22 egress allow to that range, at a higher priority than the deny; the ingress rule alone is not enough, because stateful tracking only permits replies.*

## Piece 3: the machine

**On DigitalOcean.** `modules/twingate-connector/main.tf` creates a droplet from an Ubuntu image, in the VPC, with an SSH key, and passes a boot script (cloud-init) that installs and hardens the Twingate connector.

**On GCP.** A **Compute Engine instance** (`google_compute_instance`) in a zone, in a subnet, from an Ubuntu image, with a **machine type**, a **boot disk**, optional **external IP**, and a **service account** (Piece 4). What changes:

- **Size.** Shared-core `e2-micro` has 1 GB of memory, `e2-small` has 2 GB. Twingate's guidance is 1 CPU and 2 GB and its suggested GCP starting point is `e2-small`, so `e2-micro` is an experiment. **Hourly prices for both are UNVERIFIED from Google**; see the cost lesson for the working figures. The E2 shared-core family is x86; an Arm shared-core option on GCP is UNVERIFIED.
- **The boot disk is a separate billed object.** Its size and type are settings on the instance.
- **The external IP** is a setting on the instance's network interface (an `access_config` block). Omit it and the machine has no external address, and then it needs Cloud NAT to reach out. The Always Free VM tier does not remove the address charge.
- **The boot script is not a rename.** DigitalOcean's `user_data` takes cloud-init. Compute Engine's `startup-script` metadata key (Terraform: `metadata_startup_script`) takes a **script**, run as root at boot by Google's guest tooling, bash or another interpreter named by a `#!` line. A `#cloud-config` YAML file given to it would not be run as cloud-config. Two ways to carry this project's shared cloud-init: put it in the metadata key **`user-data`**, which cloud-init's GCE datasource documents (it says `user-data` and `user-data-encoding` can be provided as custom metadata keys), or convert it to a shell script for `startup-script`. Whether the Ubuntu image you choose runs cloud-init and honours `user-data` was not checked: UNVERIFIED, test it. A real difference to note: `startup-script` runs on **every** boot (the first boot and then each reboot), while cloud-init's main configuration normally runs once.
- **SSH keys.** Compute Engine has its own ways to distribute SSH keys (project or instance metadata, or OS Login, which ties SSH to Google identities). This project's rule is that SSH is only reached through Twingate; Twingate supplies the network path, not authentication to sshd, so this project's cloud-init still installs the `admin_ssh_public_key` for `cah-admin` and disables passwords. Which of Google's key mechanisms to leave off is a design choice not covered by the evidence: UNVERIFIED.
- **The metadata server.** As on DigitalOcean and AWS, the boot data (where the connector token sits) is readable from the machine. A service account attached to the instance also makes the metadata server hand out tokens for that account; that is the next piece.

**Predict, then check.** List the GCP resources for the two connectors, including the ones that are settings rather than separate resources, and say which of them cost money every hour.

*Reference: two instances in the custom subnet, each with a machine type, a boot disk and (if you choose that path) an external IP; a dedicated service account; the firewall rules. The hourly costs are the machine type, the boot disk and the external IP, or the Cloud NAT gateway if you remove the addresses.*

## Piece 4: the machine's identity

**On DigitalOcean.** There is none. The connectors do not call the cloud's API.

**On GCP.** The answer to "who is this machine?" is the **service account attached to the instance**: software on the VM can ask the metadata server for short-lived tokens for that account, with no key file. Three facts matter:

- A VM can have **one** service account attached; one service account can serve many VMs. So changing a service account's roles changes every VM that uses it.
- The **default Compute Engine service account** may be granted the broad **Editor** role on the project automatically. Google strongly recommends disabling that automatic grant, which is an organization-policy setting you do not have. So **do not use the default service account**.
- You can create a VM with **no service account attached**, or with a **dedicated user-managed service account that has no roles at all**. This project's connectors do not call Google, so the right amount of identity is none. The more defensible choice for a first build is a dedicated service account with no roles, because it is something you can aim a firewall rule at (Piece 2) without granting it any power. Whether a VM with no service account at all is accepted by every tool you use is untested here.

Access scopes (the older mechanism that further narrows what an attached account can do) work alongside IAM roles. Google's advice is to use fine-grained roles rather than broad scopes. The details of scopes were not read in full: UNVERIFIED.

**How Spacelift would authenticate.** A different identity, not a machine identity. Per Spacelift's documentation (read 2026-10-16): attaching the GCP integration to a stack makes Spacelift create a **service account** for that stack; you add that service account's email to your project in IAM with the roles you choose; each run gets a **short-lived OAuth token** exposed as `GOOGLE_OAUTH_ACCESS_TOKEN`, which the Google provider reads. There is no long-lived key. Spacelift's page also says it strongly recommends **OIDC** for the GCP integration and links to a separate guide that was not read: the OIDC details are UNVERIFIED. The page's own example grants the Owner role at the organization level; you have no organization, and a stack that only builds a network, a firewall and two instances needs far less than Owner. Which exact roles is not yet worked out. The page mentions no plan or tier requirement; check your own plan.

**Predict, then check.** Which of these needs roles granted to a service account, and which service account: a connector installing packages from the internet; a workload reading a secret from a cloud secrets service; Spacelift running a plan? Why? Then: why is it a mistake to leave a new VM on the default service account even if it never calls Google?

*Reference: two of the three need roles. The workload that calls the secrets service needs a role on its attached service account. Spacelift running a plan also needs roles, because planning reads (refreshes) the resources in your project; those go on Spacelift's per-stack service account, which is a different identity from anything attached to a machine. The connector installing packages uses the public internet and needs no roles, so its attached identity (if any) should hold none. The default account may carry Editor on the project, so any code that runs on the VM, including through a bug in the connector, can then use a broad identity through the metadata server.*

## Putting the pieces together

On DigitalOcean, `stacks/00-foundation` and `stacks/10-access` are two layers. The same layering makes sense on GCP: a foundation layer (the custom network, the subnet, the dedicated service account, base firewall rules) and an access layer (the instances and the connector rules). The Twingate resources, the boot script content, the Doppler hook and the cost gate are provider-neutral. [The design](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/superpowers/specs/2026-10-16-multicloud-design.md) explains how the trees would sit side by side. This project's plan is that GCP code waits until someone who runs GCP has reviewed these lessons, so nothing here is code yet.

## Try it yourself

- Draw the GCP network for two connectors on paper: the network, the subnet, the two instances, the dedicated service account, the rules. Mark which arrows are allowed and which are blocked by the implied deny.
- Name one thing that was a single resource on DigitalOcean and is more than one on GCP, and one that is the other way round.
- Open Google's firewall documentation and find the sentence about mixing tags and service accounts. Rewrite the connector-to-connector rule once with tags and once with service accounts. What is the security difference? (Reference: service accounts are stricter, because tags can be edited by anyone who can edit the instance.)
- Find the place on the instance where the external IP is set. What do you have to change to remove it, and what would then stop working?

Next: [the GCP cost lesson](Provider-GCP-Cost-Lesson.md).
