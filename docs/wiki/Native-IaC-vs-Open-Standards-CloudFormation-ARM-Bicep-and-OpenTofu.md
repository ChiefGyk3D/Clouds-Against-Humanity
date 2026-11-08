# Native cloud IaC versus open standards: CloudFormation, ARM, Bicep, OpenTofu, Pulumi and Crossplane

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

> **Status: unverified draft. The free exercise was run, with only the lint and validate steps; no cloud account was used and nothing was deployed.** On **2026-11-07** I ran `cfn-lint` 1.60.0 on one CloudFormation template, and on OpenTofu 1.12.6 the commands `tofu init`, `tofu fmt -check` and `tofu validate` on the matching configuration (the AWS provider it pulled was 6.72.0). I ran each once on a good file and once on a file I broke on purpose. I had no AWS credentials on that machine (no `AWS_` environment variables, no `~/.aws` folder). `tofu init` needs the internet once to download a provider; that is the only network step. **Not run:** Bicep, ARM templates, Pulumi, Crossplane, `tofu plan`, any deployment, anything on macOS or Windows. Vendor statements were read on **2026-11-07** from the pages in the [claims register](#claims-register); a claim I could not read there is marked **est.** Trust what your terminal prints over what this page says.

> **Prerequisites.** You have read [What is infrastructure as code](What-Is-Infrastructure-as-Code.md) and know the words plan, apply and state. Having typed `tofu init` and `tofu validate` once helps ([OpenTofu from zero](OpenTofu-From-Zero.md)). No cloud account, no money. The exercise needs a terminal, Python 3 with `pip`, OpenTofu and a few hundred megabytes of free disk for a provider download (est.). About 90 minutes for the reading and the exercise (est.).

## What you will be able to do

- Say which cloud each of CloudFormation, ARM templates and Bicep works on, in one word each.
- Say what happened to Google's Deployment Manager, and what Google points people at now.
- Name what OpenTofu, Pulumi and Crossplane each are, and which of them are tied to one cloud (none are, with a catch).
- Explain lock-in as a list of things you would have to rewrite, not as a slogan.
- Explain why "portable tool" does not mean "portable code".
- Name three honest reasons to pick a native tool anyway.
- Read a small CloudFormation template next to the same thing in OpenTofu, and lint both without an account.

## The short version

My recommendation is to learn and use an open tool first. This project does: it uses OpenTofu, and [How this repository uses it](OpenTofu-From-Zero.md#how-this-repository-uses-it) shows where. The reason is not that native tools are bad. The reason is that what you learn from an open tool carries to the next cloud, the next job and the next project, and what you learn from a native tool mostly does not.

The catch, which gets its own section below: an open tool is portable, but the code you write with it is not. Moving a stack from one cloud to another is still a rewrite of every resource.

## The native tools

A **native** tool is one the cloud vendor builds, for that vendor's cloud. Each is free to use in the sense that you pay for the resources it creates (est.; I did not read each vendor's pricing page for the tool itself).

### AWS CloudFormation: AWS only

CloudFormation is Amazon's own tool, and it manages **AWS resources only**. AWS describes it as a service that helps you "model and set up your AWS resources" (CloudFormation User Guide, read 2026-11-07). You write a **template** that lists the resources you want, and CloudFormation creates and configures them. A template is YAML or JSON (est.; the template anatomy page I read lists the sections, and I wrote and linted a YAML one, but I did not read a sentence naming both formats). A deployed copy of a template is a **stack**. CloudFormation has **drift detection**, which compares what is really there with what the stack expects (same guide, read 2026-11-07).

Two neighbors you will hear about:

- **AWS CDK** lets you write the infrastructure in TypeScript, JavaScript, Python, Java, C# or Go, and "provisions it through AWS CloudFormation" (AWS CDK guide, read 2026-11-07). It changes how you write the template, not where it runs. It is still AWS only.
- **Third-party resource types.** CloudFormation has a registry that lets vendors add resource types (est.). That widens what it can manage. It does not make a CloudFormation template run on another cloud.

### Azure ARM templates and Bicep: Azure only

**Azure Resource Manager** (ARM) is the service in Azure that creates and changes resources. An **ARM template** is a JSON file that declares what to deploy, and it works for **Azure only** (Microsoft Learn, ARM templates overview, read 2026-11-07).

**Bicep** is the newer language for the same job. Microsoft calls it "a domain-specific language that uses declarative syntax to deploy Azure resources" and says "Bicep is a transparent abstraction over a Resource Manager JSON template": during deployment, the Bicep tool converts the Bicep file into an ARM JSON template (Microsoft Learn, What is Bicep, read 2026-11-07). The ARM page itself tells you that if you are weighing infrastructure as code options, "we recommend looking at Bicep". So for a new Azure-only project, read Bicep, and treat raw ARM JSON as what Bicep compiles to.

Bicep is still **Azure only**. The page calls it free and open source. It also says there is "no state or state files to manage": Azure stores the state, and a **what-if** operation previews changes before you deploy (same page, read 2026-11-07). That is real convenience, and it is also the lock-in: the state lives in Azure, in a form you do not hold.

### Google: Deployment Manager is over

Google had a native tool too, **Deployment Manager**. Google's documentation now carries a banner saying it "reached end of support on March 31, 2026" and tells users to migrate to **Infrastructure Manager** "or an alternative deployment technology" (read 2026-11-07). The deprecation page gives a slightly different date: support "was discontinued on April 1, 2026", with a maximum extension that ends March 31, 2027, and existing resources "will continue to function" (read 2026-11-07). I report both dates because Google's two pages do not match; for a learner the point is the same, which is that the tool is gone or going.

The replacement is worth reading closely. Infrastructure Manager is "a managed service" that works "by using Terraform configurations" (Infrastructure Manager overview, read 2026-11-07). So Google's current answer to "what do we use for infrastructure as code" is a hosted runner for the same Terraform-style language that OpenTofu reads, not a new language of its own. That is a vendor choosing the open format, and it is part of the evidence for this page's recommendation. What this tells you about other vendors' plans is **est.**; I read no statement of their intent.

## The open tools

An **open** tool is one that is not tied to one cloud's API and whose source you can read. All three below run against more than one cloud.

| Tool | What it is | How you write it | Where state lives | Notes (read 2026-11-07) |
|---|---|---|---|---|
| **OpenTofu** | An infrastructure as code tool with a plan and apply workflow; a fork-compatible peer of Terraform | HCL ([Data formats](Data-Formats-JSON-YAML-HCL.md)) | A state file you control, local or in a backend you pick (see [Plans, state, drift and recovery](Plans-State-Drift-and-Recovery.md)) | opentofu.org says you can define "cloud and on-prem resources" and that providers exist for AWS, Azure, Google Cloud, Kubernetes, Helm, GitHub and more. Relationship to Terraform: [OpenTofu and Terraform](OpenTofu-From-Zero.md#opentofu-and-terraform) |
| **Pulumi** | An infrastructure as code SDK | TypeScript, Python, Go, .NET, Java, YAML or HCL | A backend (Pulumi's hosted service or one you run; est., not read in detail) | Pulumi's docs call it an "open source infrastructure as code SDK" that manages AWS, Azure, Google Cloud, Kubernetes "and thousands of cloud providers" |
| **Crossplane** | A control plane framework that runs inside Kubernetes | Kubernetes resource files (YAML) | In the Kubernetes cluster's API (est., from how a control plane works) | The docs say it "extends Kubernetes" with new custom resources; the CNCF page says it moved to the Graduated level on October 28, 2025 |

How they feel in use, with the unverified parts marked: OpenTofu is the one this wiki teaches, and the simplest to start with. Pulumi suits someone who would rather write a loop in Python than learn HCL (est.). Crossplane suits a team that already runs Kubernetes and wants its platform to offer cloud resources as Kubernetes objects (est.); a beginner does not need it.

## The lock-in tradeoff, made explicit

**Lock-in** is the cost of leaving. It is not one thing. For a native tool, count what you would have to redo:

| What you would redo | Native (CloudFormation, ARM, Bicep) | Open (OpenTofu, Pulumi, Crossplane) |
|---|---|---|
| The tool and its commands | Learn a new one for each cloud | Keep it |
| The file syntax | Rewrite | Keep it (or, with Pulumi, your language) |
| The state and where it lives | Held by the cloud vendor, in its own service | Held by you, and movable (est., for the move itself) |
| The resource definitions | Rewrite | **Rewrite** (see the next section) |
| Your skills and habits | Mostly start over | Mostly keep |
| CI jobs, review habits, policy checks | Rebuild | Mostly keep (est.) |

The fourth row is the same for both. The other rows are where the open tools save you, and they save the most for people: the habit of reading a plan, the habit of keeping state safe, and the habit of reviewing a diff all stay with you.

Lock-in also has a second, quieter side: your tool's future. Google's Deployment Manager is the live example. A team that wrote its Google infrastructure in it is now doing a migration it did not schedule. That is a risk of any single-vendor tool, and I would be dishonest to say open tools have none (a fork, a license change or a stalled project can hurt an open tool too), but the plain format is one a second tool can read, which is what Google's own replacement does.

## "Portable" has a limit

An open tool is portable. The **code** is not. A provider is the plugin that knows one service's resources, and each cloud has its own provider with its own resource types. The storage example, using resource type names I confirmed by installing the three providers on 2026-11-07 (OpenTofu 1.12.6, AWS provider 6.72.0, Azure provider 5.13.0, Google provider 8.10.0):

| Cloud | The resource for "a place to put files" | Provider |
|---|---|---|
| AWS | `aws_s3_bucket` | `hashicorp/aws` |
| Azure | `azurerm_storage_account`, plus `azurerm_storage_container` inside it | `hashicorp/azurerm` |
| Google | `google_storage_bucket` | `hashicorp/google` |

The same job needs a different resource, with different arguments and different rules, on each. A tool that is portable lets you carry your **method** (write, plan, review, apply, keep state) from one cloud to the next. It does not let you copy the files. The lessons [AWS: the same four pieces](Provider-AWS-The-Same-Four-Pieces.md), [Azure: the same four pieces](Provider-Azure-The-Same-Four-Pieces.md) and [GCP: the same four pieces](Provider-GCP-The-Same-Four-Pieces.md) walk through exactly this for a network, a firewall, a machine and an identity, so I will not repeat them here. The mismatch is the lesson those pages teach.

Anyone who tells you that an open tool means "write once, run on any cloud" is selling something. Pulumi's and Crossplane's own pages talk about managing many clouds, not about one program that works unchanged on all of them (my reading of the pages; I did not search for a counterexample).

## Where a native tool is still the right call

Open is my default. Here is where I would pick native, and say so.

1. **Day-zero feature support.** Microsoft's Bicep page says Bicep "immediately supports all preview and GA versions for Azure services", because it targets the Azure resource providers directly (read 2026-11-07). A third-party provider has to add each new resource or setting, so a brand-new service can be missing from it for a while. I did not measure how long that gap is on any cloud, so treat how often it bites as **est.** If your work is "use the newest AWS or Azure service the week it ships", a native tool is the safer bet.
2. **State the vendor holds for you.** Bicep's "no state files to manage" and CloudFormation's stacks mean there is no state file to lose, leak or lock. For a small team that has already lost a state file, that is a real benefit. The price is that you do not hold the state ([The state file in plain words](OpenTofu-From-Zero.md#the-state-file-in-plain-words) explains what you would be holding).
3. **An organization mandate.** Some employers say "Azure means Bicep" or "AWS means CloudFormation", for support contracts, audit or training reasons. You may not get a vote. That is a good reason to learn the native tool as a second one. Knowing both makes you more useful, not less.
4. **One cloud forever, and small.** If you know you will only ever use one cloud, the cross-cloud argument does not apply, and a native tool is a fair choice (est.). Be honest about the word "forever"; plans change.

None of these says native is better in general. Each says what you get in exchange for the lock-in.

## Hands-on: read two files side by side, with no cloud account

A free exercise. You read a small CloudFormation template and the same thing in OpenTofu, lint both, and break each once to see the tools catch it. Nothing is created and nothing is deployed. Below is what I ran on 2026-11-07, on Linux with OpenTofu 1.12.6 and `cfn-lint` 1.60.0.

**Set up (once).** Make a scratch folder and a Python virtual environment for the linter. Do not put either inside a repository.

```bash
mkdir -p ~/scratch/native-vs-open && cd ~/scratch/native-vs-open
python3 -m venv .venv
.venv/bin/pip install cfn-lint
.venv/bin/cfn-lint --version
```

**Step 1: the CloudFormation template.** Save this as `template.yaml`. It is one private S3 bucket with versioning on and public access blocked.

```yaml
AWSTemplateFormatVersion: "2010-09-09"
Description: One private, versioned S3 bucket.

Parameters:
  BucketName:
    Type: String
    Description: Globally unique bucket name.

Resources:
  NotesBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: !Ref BucketName
      VersioningConfiguration:
        Status: Enabled
      PublicAccessBlockConfiguration:
        BlockPublicAcls: true
        BlockPublicPolicy: true
        IgnorePublicAcls: true
        RestrictPublicBuckets: true

Outputs:
  BucketArn:
    Value: !GetAtt NotesBucket.Arn
```

Read it top to bottom. `Parameters` is an input. `Resources` holds one resource, a bucket, whose `Type` is `AWS::S3::Bucket`, a name that only exists in AWS. `!Ref` and `!GetAtt` are CloudFormation's own functions for reading a value. `Outputs` prints one.

**Step 2: the same thing in OpenTofu.** Save this as `main.tf`.

```hcl
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

variable "bucket_name" {
  type        = string
  description = "Globally unique bucket name."
}

resource "aws_s3_bucket" "notes" {
  bucket = var.bucket_name
}

resource "aws_s3_bucket_versioning" "notes" {
  bucket = aws_s3_bucket.notes.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "notes" {
  bucket                  = aws_s3_bucket.notes.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

output "bucket_arn" {
  value = aws_s3_bucket.notes.arn
}
```

Match the parts: `Parameters` is the `variable`; `Resources` is the `resource` blocks; `Outputs` is the `output`. Two differences are worth noticing. First, CloudFormation has one resource where OpenTofu has three: in this provider, versioning and the public access block are separate resources that point at the bucket (why the provider is built that way is **est.**; I did not read its changelog). Second, this configuration is **still AWS only**: `aws_s3_bucket` exists nowhere else. The tool is portable. This file is not.

**Step 3: lint the template.** This step makes no network call that I know of (est.; I did not watch the traffic).

```bash
.venv/bin/cfn-lint template.yaml; echo "exit=$?"
```

I got no output and `exit=0`.

**Step 4: validate the OpenTofu.** `init` downloads the AWS provider, which needs the internet once and no credentials.

```bash
tofu init -input=false
tofu fmt -check; echo "fmt exit=$?"
tofu validate; echo "validate exit=$?"
```

I got `fmt exit=0` and `The configuration is valid.` with `validate exit=0`. There is no `plan` here on purpose: a plan with the AWS provider wants to talk to AWS, and this exercise does not.

**Step 5: break each one on purpose.** In `template.yaml`, change `VersioningConfiguration` to `VersionConfiguration` (a typo) and lint again:

```bash
sed 's/VersioningConfiguration/VersionConfiguration/' template.yaml > bad.yaml
.venv/bin/cfn-lint bad.yaml; echo "exit=$?"
```

I got `E3002 Additional properties are not allowed ('VersionConfiguration' was unexpected. Did you mean 'CorsConfiguration'?)` pointing at line 14, and `exit=2`. Now the same kind of typo in OpenTofu, in a second folder so the good one stays good:

```bash
mkdir ../bad && sed 's/versioning_configuration/versioning_config/' main.tf > ../bad/main.tf
cd ../bad && tofu init -input=false && tofu validate; echo "exit=$?"
```

I got two errors, `Insufficient versioning_configuration blocks` and `Unsupported block type` for `versioning_config`, and `exit=1`. Both tools caught a misspelled property without touching a cloud. That is the real gain of both: a mistake caught on your laptop. It is not a difference between native and open.

**Step 6 (optional, not run): the Azure view.** Microsoft publishes a Bicep and ARM storage account example on the pages in the register. Read one of them next to `azurerm_storage_account` and see how many lines are the same idea in three spellings. I did not install Bicep or run it, so I have no output for you.

**Clean up.** Delete the scratch folders, including `.terraform` and the virtual environment:

```bash
cd ~ && rm -rf ~/scratch/native-vs-open ~/scratch/bad
```

Check the folder is gone with `ls ~/scratch`. Nothing outside the scratch folders was created.

## Build, break, detect, defend

- **Build:** the exercise above.
- **Break:** typos in both files (Step 5). A wrong name is the cheap mistake. The expensive one, which this exercise does not touch, is a valid file that opens a bucket to the world; no linter I ran was asked about it, so I cannot tell you which tools flag it.
- **Detect:** drift detection in CloudFormation, `what-if` in Bicep and `tofu plan` in OpenTofu all compare the code with reality; see [Plans, state, drift and recovery](Plans-State-Drift-and-Recovery.md) for the open-tool version.
- **Defend:** the defense in any of them is the same: a reviewer reads the change before it applies, and the credentials that apply it are scoped small.

## Checkpoint

1. Name the cloud each of CloudFormation, ARM and Bicep works on.
2. Deployment Manager ended in 2026. What does Google point users to, and what language does it use?
3. Which row of the lock-in table is the same for native and open tools, and why?
4. You move a stack from AWS to Azure with OpenTofu. What carries over and what do you rewrite?
5. Give two reasons to choose Bicep over OpenTofu on an Azure-only project.

## Common mistakes

- **Reading "portable" as "unchanged".** The tool moves. The resources do not.
- **Treating Bicep as a different thing from ARM.** It compiles to an ARM template; it is a nicer way to write one.
- **Choosing a tool by its logo.** Choose by what you must keep when you change cloud.
- **Believing vendor-held state is no state.** It exists; someone else holds it.
- **Trusting a lint pass as a security review.** `exit=0` told me the files were well formed. It said nothing about whether the bucket was a good idea.

## Claims register

| Claim | Source | Status |
|---|---|---|
| CloudFormation helps you "model and set up your AWS resources" from a template | [CloudFormation User Guide, What is CloudFormation](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/Welcome.html) | Read, 2026-11-07 |
| CloudFormation detects drift between a stack's actual and expected configuration | [Drift detection](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-stack-drift.html) | Read, 2026-11-07 |
| AWS CDK is open source, supports TypeScript, JavaScript, Python, Java, C# and Go, and provisions through CloudFormation | [AWS CDK guide](https://docs.aws.amazon.com/cdk/v2/guide/home.html) | Read, 2026-11-07 |
| CloudFormation templates are YAML or JSON; the third-party resource type registry; no extra charge for the tools themselves | AWS documentation | **est.**, not read as a sentence |
| ARM templates are JSON, declarative, for Azure; Microsoft recommends looking at Bicep | [ARM templates overview](https://learn.microsoft.com/en-us/azure/azure-resource-manager/templates/overview) | Read, 2026-11-07 |
| Bicep is a DSL for Azure, converted to an ARM JSON template at deployment; supports all preview and GA API versions immediately; no state files to manage, Azure stores state; what-if; free and open source | [What is Bicep](https://learn.microsoft.com/en-us/azure/azure-resource-manager/bicep/overview) | Read, 2026-11-07 |
| Deployment Manager: banner "reached end of support on March 31, 2026"; deprecation page "discontinued on April 1, 2026", maximum extension ends March 31, 2027, existing resources keep working | [Deployment Manager docs](https://docs.cloud.google.com/deployment-manager/docs), [deprecation](https://docs.cloud.google.com/deployment-manager/docs/deprecations) | Read, 2026-11-07. The two pages give different dates |
| Infrastructure Manager is a managed service using Terraform configurations | [Infrastructure Manager overview](https://docs.cloud.google.com/infrastructure-manager/docs/overview) | Read, 2026-11-07 |
| OpenTofu defines cloud and on-prem resources, with providers for AWS, Azure, Google Cloud, Kubernetes, Helm, GitHub and others; plan then apply | [OpenTofu intro](https://opentofu.org/docs/intro/) | Read, 2026-11-07 |
| Pulumi: open source SDK; TypeScript, Python, Go, .NET, Java, YAML, HCL; AWS, Azure, Google Cloud, Kubernetes and thousands of providers | [Pulumi IaC docs](https://www.pulumi.com/docs/iac/) | Read, 2026-11-07 |
| Crossplane extends Kubernetes with custom resources; accepted to CNCF 2020-06-25, Incubating 2021-09-14, Graduated 2025-10-28 | [Crossplane docs](https://docs.crossplane.io/latest/whats-crossplane/), the Crossplane page on the CNCF site (cncf.io) | Read, 2026-11-07 |
| Resource types `aws_s3_bucket`, `azurerm_storage_account`, `azurerm_storage_container`, `google_storage_bucket` exist (AWS 6.72.0, Azure 5.13.0, Google 8.10.0) | `tofu providers schema -json` after `tofu init` | Observed, 2026-11-07 |
| `cfn-lint` 1.60.0 passed the good template (exit 0) and failed the typo (E3002, exit 2); OpenTofu 1.12.6 `fmt -check` and `validate` passed the good file (exit 0) and failed the typo (exit 1) | One run each on Linux | Observed, 2026-11-07; yours differ |
| No AWS credentials were present when I ran the exercise | `env` and `~/.aws` checked | Observed, 2026-11-07 |
| Open-tool state is movable; Pulumi and Crossplane state locations; how tool skills carry over; CI reuse; why the AWS provider splits one bucket into three resources; how big the day-zero gap is for third-party providers; one-cloud-forever reasoning; Pulumi suits Python writers; Crossplane suits Kubernetes teams; other vendors' plans | General knowledge | **est.** |

Not verified, plainly: Bicep, ARM, Pulumi and Crossplane in use; `tofu plan` or any deployment on any cloud; whether `cfn-lint` makes network calls; how current providers lag new services; vendor pricing for the native tools; anything on macOS or Windows; and everything marked est.

Next: [Why the clouds differ](Why-the-Clouds-Differ.md), then [OpenTofu, stacks and modules](OpenTofu-Stacks-and-Modules.md), and continue on the [Reading order](Reading-Order.md) page.
