# Start here if you are new

This page is for you if you have a Raspberry Pi or an old PC running a few things at home, you have heard words like "cloud", "Terraform", "zero trust" and "CI" without anyone ever explaining them, and this repository is one of your first looks at how infrastructure is built in a professional setting. Nothing on the start-from-zero pages assumes you have worked in IT. They assume you are curious and can type a command.

The rest of the wiki was written for people who already know the vocabulary. It is still the real documentation of this environment, and you will be able to read it by the time you finish these pages.

## Where zero is

The zero this project presumes is a basic power user. You know how a computer works, you may have built or repaired one, and you have set up a router and done basic networking. If you are qualified for basic help desk or an entry-level IT position, even as someone working a retail or repair counter at a place like Micro Center or Geek Squad, you know enough to start here.

If that is not you yet, that is fine: look at IT 101 level material first, including but not limited to the objectives of [CompTIA A+](https://www.comptia.org/en-us/certifications/a/), which is the certification most commonly associated with the minimum I am looking for you to know. This is not an endorsement of CompTIA or of any exam. It is just the benchmark people recognize, and it was checked as a public page on 2026-10-22. The primers here ([What is the cloud](What-Is-the-Cloud.md), [Networking basics](Networking-Basics-for-This-Project.md) and [Linux for enterprise beginners](Linux-for-Enterprise-Beginners.md)) are a bridge into the cloud and security side, not a substitute for knowing what a computer, a router or an IP address is.

## What this project actually is, in plain words

If you want the reason behind the project before the detail, [Why this exists](Why-This-Exists.md) is a short side page about that. It is not a step in the path below.

The author has a homelab: computers at home that run bots, dashboards and a security monitoring stack. This project rents two small computers from a cloud company (DigitalOcean), locks them down so that nothing on the internet can connect to them, and builds a private way to reach them. Later stages will move some of the home bots onto a third rented computer.

Everything about those rented computers is written down as code in this repository: what size they are, what network they sit on, which connections their firewall allows, which user may log in. A hosted service reads that code and builds the real thing. Changing the environment means changing the code, having it checked, and then approving the change. Nobody clicks around in a web console.

That is the whole idea. The rest is detail, and the detail is what the pages are for.

## The mental model: homelab words to cloud words

Most cloud concepts have a homelab equivalent. Start from what you already have.

| At home you have | In the cloud it is called | How it is different | Page |
|---|---|---|---|
| A Raspberry Pi or an old PC running Linux | A **virtual machine**; DigitalOcean calls one a **droplet** | Rented by the hour, created and destroyed with an API call, and it has a public internet address from the moment it boots | [What is the cloud](What-Is-the-Cloud.md) |
| Your home LAN behind the router | A **VPC**, virtual private cloud | A private network you define, with addresses you choose; nothing else in the datacenter is on it | [Networking basics](Networking-Basics-for-This-Project.md) |
| The firewall in your router, which blocks everything from outside by default | A **cloud firewall** | You write every rule yourself. The default for a fresh machine is "everything open", so the first job is to close it | [Networking basics](Networking-Basics-for-This-Project.md) |
| Tailscale, WireGuard or a VPN to reach home | **ZTNA**, zero trust network access (here, Twingate) | No open port anywhere. Access is granted per person, per host, per port, not "you are on the network now" | [Why ZTNA and not a VPN](Why-ZTNA-Not-a-VPN.md) |
| Running commands on the box and remembering what you did | **Infrastructure as code** (here, OpenTofu) | The whole environment is a set of text files. Applying them builds it; `tofu destroy` (or removing a resource from the files and applying) tears it down. Deleting the files alone removes nothing, and the bill keeps coming | [What is infrastructure as code](What-Is-Infrastructure-as-Code.md) |
| A `.env` file with your API keys in it | A **secrets manager** (here, Doppler) | Secrets live in one place with access logging and expiry. None of them are in a file in this repository | [Identity, secrets and zero trust](Identity-Secrets-and-Zero-Trust-Basics.md) |
| Docker and Portainer on the Pi | The same, on a droplet | Same tools. The difference is in how you get to them and how state is kept, so the machine can be thrown away | [Containers and Docker basics](Containers-and-Docker-Basics.md) |
| Copying files to a backup drive | **Version control** (git) for the code and **object storage** for data | Every change to the code is recorded with who made it and why. Data lives in a bucket that keeps old versions | [Git, GitHub and pull requests](Git-GitHub-and-Pull-Requests.md) |
| A monthly electricity bill | **Usage billing** | You pay for what exists, per hour or per second, and a mistake can cost money fast. This project has a ceiling and a check that blocks any change that would push the planned bill over it. The check only sees what the code creates; usage-billed things (bandwidth, functions) and anything clicked together by hand are watched on the billing page | [How money works in the cloud](How-Money-Works-in-the-Cloud.md) |

## A reading path

Read these in order. Each one is short, explains one idea, and ends by pointing at where that idea shows up in this repository.

| Step | Page | What you will understand afterwards |
|---|---|---|
| 1 | [What is the cloud](What-Is-the-Cloud.md) | What you are actually renting, why it has a public address, and what "the cloud is someone else's computer" leaves out |
| 2 | [Networking basics for this project](Networking-Basics-for-This-Project.md) | Addresses, ports, firewalls, and why a machine can use the internet while nothing on the internet can reach it |
| 3 | [Identity, secrets and zero trust basics](Identity-Secrets-and-Zero-Trust-Basics.md) | What a secret is, why it must never be in a file, what MFA and SSH keys do, and what "zero trust" means without the marketing |
| 4 | [What is infrastructure as code](What-Is-Infrastructure-as-Code.md) | What Terraform and OpenTofu are, what a plan is, what state is, and how to read the code in this repo |
| 5 | [Git, GitHub and pull requests](Git-GitHub-and-Pull-Requests.md) (never used git? do [Git from zero](Git-From-Zero.md) first) | How a change gets proposed, checked by robots, reviewed and merged, and why the documentation lives in git too |
| 6 | [Containers and Docker basics](Containers-and-Docker-Basics.md) | What a container is, how it differs from a virtual machine, and what has to change about a Pi-shaped app before it is "cloud shaped" |
| 7 | [How money works in the cloud](How-Money-Works-in-the-Cloud.md) | What costs, what is free, how a bill gets out of hand, and how this project makes the bill a reviewed number |
| 8 | [Enterprise engineering habits](Enterprise-Engineering-Habits.md) | Why this lab does things that look like overkill, and which of those habits are worth copying at home |

After step 8, continue with the core path on the [Reading order](Reading-Order.md) page (step 10 is the [Architecture overview](Architecture-Overview.md), which will make sense by then), and the [Glossary](Glossary.md) is there for any word that does not.

## Following along

You can get something out of this repository at three levels of commitment.

**Reading only, $0.** Everything here is public, including the code, the tests and the decisions. You can run the tests on your own computer without any cloud account, because they use fake providers; the [infrastructure as code](What-Is-Infrastructure-as-Code.md) page shows how.

**Build stage 0, $0.** Stage 0 creates a project, a private network and a firewall. None of those cost money at DigitalOcean. You need a DigitalOcean account, a Spacelift account and a Doppler account, all of which have free tiers at the time of writing (check their pricing pages; this repo does not promise they still do). The [stage 0 guide](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/stages/00-foundation.md) is the step-by-step.

**Build stage 1, $12 a month.** Two small droplets with Twingate connectors. This is the first stage that costs money, and the first one you can SSH into. You also need a Twingate account. The [stage 1 guide](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/docs/stages/01-access.md) covers it, and the cost page says what to expect on the bill.

Whatever level you pick, read [How money works in the cloud](How-Money-Works-in-the-Cloud.md) before you create an account, and set a billing alert before you create anything else.

## How to read these pages

- Words in **bold** on first use are defined in the [Glossary](Glossary.md).
- A diagram is never the only explanation. If a flowchart does not land, the text under it says the same thing.
- "Why" comes before "how" on purpose. If you understand why a firewall rule exists, you can write the next one. If you only know how, you can only copy.
- Everything that was tried and failed is on [Lessons learned](Lessons-Learned.md). Read it as a list of things you are now allowed to skip.
- Where a page states a vendor price, a limit or a product feature, it says the date it was checked. Those things change; the reasoning does not.

## What this is not

It is not a tutorial that ends with a working website. The environment is deliberately tiny: two machines, zero open ports, one way in. The value is in how it was built and why, and in the fact that every decision, including the wrong ones, is written down. If you want to learn cloud by building a thing, pick a thing and build it; then come back here to learn how to build it so that it does not get owned, does not surprise you on the bill, and can be rebuilt from scratch in an afternoon.

## On what I left out, and on AI

While this project helps you learn, some things have purposely been left out, condensed, or only given as partial lessons, because I, just like the real field, will not spoonfeed you all the answers, and AI can't reason for you. Learn to understand this yourself first, and then at most guide and direct the AI.

I will be honest and say I still google things the old-fashioned way, as you may call it today, because it is often faster and I can reason better than AI can. Practice it and you will get better at it. AI is a great tool, but it is not always right or perfect, and it will amplify what you are great at and what you suck at. Use it as a tool, not as a crutch.

I am not anti AI. [Scrum Around and Find Out](https://github.com/ChiefGyk3D/scrum-around-and-find-out), [Department of Internal Arguments](https://github.com/ChiefGyk3D/department-of-internal-arguments), [FrankenLLM](https://github.com/ChiefGyk3D/FrankenLLM), [Stream Daemon](https://github.com/ChiefGyk3D/Stream-Daemon), [Boon Tube Daemon](https://github.com/ChiefGyk3D/Boon-Tube-Daemon), [Star Daemon](https://github.com/ChiefGyk3D/Star-Daemon), [Penguin Overlord](https://github.com/ChiefGyk3D/penguin-overlord) and [Yo Mama as a Service](https://github.com/ChiefGyk3D/yomama-as-a-service) all have various AI features, I run my own AI server, and I am in both the Anthropic and OpenAI cybersecurity programs.

If something here is wrong, confusing or does not work on your computer, please tell me: [Give feedback and open an issue](Give-Feedback-and-Open-an-Issue.md) shows how, and it costs nothing.

Next: [What is the cloud](What-Is-the-Cloud.md), the first primer. Every path through the wiki is laid out on the [Reading order](Reading-Order.md) page, and [Contents](Contents.md) lists every page once, grouped by theme.
