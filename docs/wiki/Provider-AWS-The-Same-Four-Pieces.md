# AWS: the same four pieces

> **Status: unverified draft.** Written 2026-10-16 from AWS's documentation (sources in the [phase 0 evidence](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/superpowers/specs/2026-10-16-multicloud-phase0-evidence-aws.md)). **The three AWS modules now exist (see "Where this is built" below) and are tested with mocked providers only. They have never been applied to an AWS account, and there is no AWS stack yet.** The resource lists below are still a teaching map, and the code may differ from your answer for good reasons. Not yet reviewed by the maintainer.

Read [Why the clouds differ](Why-the-Clouds-Differ.md) and [OpenTofu, stacks and modules](OpenTofu-Stacks-and-Modules.md) first. This page walks the four pieces that this project builds on DigitalOcean (a private network, a firewall, a machine, an identity for the machine), points at the DigitalOcean file where each lives, and says what you would build on AWS instead and why it is not a one-line rename.

The method is the exercise: for each piece, **read the DigitalOcean file, predict the AWS resources, then check your list against the reference at the bottom of the piece.**

## Piece 1: the private network

**On DigitalOcean.** `modules/vpc/main.tf` is one resource, `digitalocean_vpc`, with a name, a region and an address range. That one object gives droplets a private network for droplet-to-droplet traffic. Internet access is a separate path: these droplets reach the internet through their own public interfaces, which DigitalOcean supplies without any routing for you to build. A VPC alone does not give a droplet internet access.

**On AWS.** A VPC is only the address space. For a machine to reach the internet from it you assemble the path yourself:

- a **subnet** inside the VPC, in one availability zone;
- an **internet gateway** attached to the VPC (this itself is free);
- a **route table** with a route that sends internet-bound traffic (`0.0.0.0/0`) to the gateway;
- an **association** that connects the route table to the subnet;
- a public address on the machine, either assigned automatically by the subnet or attached directly.

AWS's documentation is explicit that a VPC you create yourself has none of the internet path by default: no gateway, no route to one, and no automatic public address. (It does get a main route table with a local route so its own subnets can talk to each other; what it lacks is a route to an internet gateway.) A subnet whose route table has no route to a gateway is a *private* subnet. A machine in it cannot reach the internet over IPv4, even with a public address. There are two ways out: add the internet gateway route, which makes the subnet public (free), or keep the machine private and add a NAT service (expensive, see [the cost lesson](Provider-AWS-Cost-Lesson.md)).

**Why it matters.** This is the first place the DigitalOcean module's smallness hides a lesson. One resource on DigitalOcean is five on AWS, and each is something that can be missing. Most "the machine can't reach the internet" problems on AWS are a missing route or a subnet in the wrong table.

**Predict, then check.** Without looking below, list the AWS resource types you would need to replace `modules/vpc`. Include the one that makes the network public.

*Reference (one reasonable answer): a VPC, a subnet, an internet gateway, and a route to it. You can add that route to the VPC's main route table, or create an explicit route table and associate it with the subnet, which is clearer in code and is what this project's style would prefer.*

## Piece 2: the firewall

**On DigitalOcean.** `modules/firewall/main.tf` makes a cloud firewall that applies to every droplet carrying a tag, allows nothing in by default, and lists explicit outbound rules. It is attached by **tag, at creation**, so there is no moment when a new droplet is unprotected.

**On AWS.** The filter is a **security group**, and it is attached to a machine's **network interface**, not to a tag. The differences that matter:

- **Defaults.** A newly created security group has no inbound rules, so nothing gets in, and one rule that allows all outbound traffic. (The group AWS creates for every VPC, the *default* security group, is different: it allows traffic from members of itself. Create your own group and do not use the default.) You can remove the outbound rule; with no outbound rules, nothing gets out. So "default deny inbound" is the starting state rather than something you build.
- **The source of a rule can be another security group.** "Only the connectors may reach SSH on each other" is written as "allow SSH from the connector group." This is the AWS equivalent of this project's tag-sourced rules, but it works through private addresses and not for traffic that passes through a middlebox. For this build the scope is one VPC: AWS also allows references across a peered VPC and, for inbound rules only, across a transit gateway, which a two-machine project does not need.
- **Statefulness.** Replies to allowed traffic are allowed whatever the rules say, as with the DigitalOcean firewall.
- **What it does not filter.** Amazon's DNS resolver, address assignment, the instance metadata service and the time service sit outside the group's control. This is worth knowing for the threat model: the metadata service (where the connector token sits in the boot data on this project's droplets) is not something a security group can lock down.
- **Cost.** Security groups are free.

**Why it matters.** "Attach by tag at creation" is a DigitalOcean convenience. On AWS the group is attached at launch by naming it when you create the instance, which gives the same property: there is no unprotected window. But the module that creates the instance and the module that creates the group have a different relationship than on DigitalOcean, and a design that hides that behind one word ("membership") would hide the lesson.

**Predict, then check.** Your connectors must be able to SSH to each other and nothing else may reach them. In one sentence, what is the source of that rule on AWS? Then: why can the source not be the same rule on a *different* VPC without extra setup?

*Reference: the source is the connectors' own security group, resolved through private addresses. It does not reach an unrelated VPC unless the two are connected, for example by peering.*

## Piece 3: the machine

**On DigitalOcean.** `modules/twingate-connector/main.tf` creates a droplet from an Ubuntu image, in the VPC, with an SSH key, and passes a boot script (cloud-init) that installs and hardens the Twingate connector.

**On AWS.** An **instance** launched from an Ubuntu image, with the same cloud-init data. What changes:

- **Size and architecture.** The cheapest candidate was priced on 2026-10-16: a small burstable arm instance (`t4g.micro`, 2 vCPUs, 1 GiB of memory) at about $0.0084 an hour, with an x86 equivalent (`t3.micro`) as the fallback. **That 1 GiB is below Twingate's general guidance of 1 CPU and 2 GB of memory** (its smaller figure comes from a container deployment), so treat the micro as an experiment to test, not a recommendation. The next size up has 2 GiB and costs more; its price was not checked. Twingate publishes the connector for arm64 in its package repository, so the arm choice is open; running it on a real instance is untested here.
- **The root disk is a separate billed object** (EBS), with a default size that this wiki has not verified from an official source.
- **The public address** is an attribute of the instance (or a separate elastic address resource) and is billed by the hour, whether or not you notice it.
- **SSH key.** DigitalOcean registers a key at the account level and the droplet refers to its fingerprint. AWS has *key pairs*, and also lets you launch with no key at all and rely on Twingate for SSH. The project's rule is that SSH is only ever reached through Twingate, which makes the question "do you want an AWS key pair?" a real one. Twingate supplies the network path, not authentication to sshd. This project's cloud-init installs the `admin_ssh_public_key` for `cah-admin` and disables password login, so the SSH public key is still required whether or not you register an AWS key pair.
- **Boot data and the metadata service.** The same cloud-init data is readable from the machine. This project accepts that risk on DigitalOcean (threat T5). AWS has a stricter mode of its metadata service that requires a session token, aimed at defeating attacks that trick a web application into fetching it. Predict whether it would help against a *local* process on the instance, then read AWS's documentation to check. (The answer: not much. The stricter mode needs a session token fetched with a separate request, which defeats attacks that trick a web application into making one simple request on the attacker's behalf. A program already running on the instance can make both requests, so it can still read the boot data. It is worth turning on as defence in depth; it does not make the connector token safe from local code.)

**Predict, then check.** List the AWS resources for the two connectors, including the one that is not a separate resource on DigitalOcean but costs money every hour.

*Reference: two instances, each in the public subnet and in the connector security group; the public address on each; the root volumes. Whether an SSH key pair is created is a design choice.*

## Piece 4: the machine's identity

**On DigitalOcean.** There is none. The connectors do not call the cloud's API, and the cloud-init data carries their one secret.

**On AWS.** The platform's answer to "who is this machine?" is an **instance profile**: an IAM role attached to the instance, which the machine uses to get temporary credentials without ever holding a key. This project's connectors do not need to call AWS, so the right amount of identity is **none**: no profile, no role. That is a decision, and a good exercise in least privilege: the safest permission is the one that is not granted.

A different identity matters in this project: the one that lets **Spacelift** act in your AWS account. That is an IAM role in your account that Spacelift assumes, with a trust policy naming Spacelift and a per-stack identifier. It is not a machine identity, and the plan you use must support it; the [account preparation page](Provider-AWS-Account-Preparation.md) covers why this is checked first.

**Predict, then check.** Which of these needs an instance profile: a connector installing packages from the internet; a workload that reads a secret from a cloud secrets service; Spacelift running a plan? Why?

*Reference: only the workload that calls the cloud's secrets service. The package install uses the public internet. Spacelift is not a machine in your account: it assumes a role from outside.*

## Putting the pieces together

On DigitalOcean, `stacks/00-foundation` and `stacks/10-access` are two layers, and the second depends on outputs of the first. The same layering makes sense on AWS: a foundation layer (network, base security group) and an access layer (instances, connector group). The shared parts, the Twingate resources, the boot script, the Doppler hook and the cost gate, are provider-neutral and are not rewritten. [The design](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/superpowers/specs/2026-10-16-multicloud-design.md) explains how the two trees would sit side by side.

## Where this is built

Check your predictions against the code, in the repository under `modules/aws/`: [`vpc`](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/tree/main/modules/aws/vpc), [`firewall`](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/tree/main/modules/aws/firewall) and [`twingate-connector`](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/tree/main/modules/aws/twingate-connector), each with a README mapping the DigitalOcean object to the AWS one. The connector calls the same shared bootstrap as the DigitalOcean one, so the hardening is not copied. They are tested with mocked providers (`tofu test`), which proves the shape of the code and not how AWS behaves: nothing has been applied. The [Terraform reference](Terraform-Reference.md) walks through them. Piece 4 is a decision in the code: the instance has no instance profile and no AWS key pair.

## Try it yourself

- Draw the AWS network for two connectors on paper: the VPC, the subnet, the gateway, the route, the two instances, the group. Mark which arrows are allowed traffic and which would be blocked. Then check the group's inbound list: it should be empty except for the connector-to-connector rule.
- Name one thing on DigitalOcean that was automatic and on AWS you must build. Name one that is the other way round.
- Open the AWS documentation page on security groups and find where it says what they do *not* filter. Which of those items touches a threat in the [Threat model](Threat-Model.md)?

Next: [the AWS cost lesson](Provider-AWS-Cost-Lesson.md).
