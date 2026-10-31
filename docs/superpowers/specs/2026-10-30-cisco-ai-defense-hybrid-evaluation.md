# Evaluation: Cisco ai-defense-hybrid as a reference lesson

Status: DRAFT for the maintainer's decision. Date: 2026-10-30. Issue: #303 (related: #304, the AI-security lesson track).
Tooling: none. This note adds no lesson page, stack, workflow or cost entry. Nothing from the evaluated repository was run, installed or deployed; its files were read only. No Cisco account, token or paid service was used.

Facts carry a source and the date they were read. "Read" means a plain `git clone --depth 1` of the repository and the GitHub REST API (read-only metadata calls through `gh api`), both on the dates in the table. Anything I could not check is marked UNVERIFIED.

## 1. The question

Issue #303 asks: is `cisco-ai-defense/ai-defense-hybrid` worth a wiki lesson on how a vendor structures multi-cloud Terraform modules, shared prerequisites and a Terraform Cloud workspace manager, compared with CAH stacks and Spacelift? Or skip it. Done when a keep/skip decision with the reason is on the issue.

## 2. What it is

Its own README calls it "infrastructure templates to help customers deploy Cisco AI Defense hybrid deployments across multiple cloud providers", offered "as examples and starting points".

It is a deployment kit, not a security tool. It stands up the infrastructure for the AI Defense Hybrid Connector, a component of Cisco's commercial AI Defense product (the connector runs in the customer's cluster; the console that issues its installer is Cisco's). The repository contains, by directory:

| Path | What is there |
|---|---|
| `terraform/cloud-providers/aws`, `azure`, `gcp` | One connector module each (EKS, AKS, GKE): GPU Kubernetes cluster, network, private DNS, identity, and generated bash install scripts (Terraform templates that write scripts to run afterward). |
| `terraform/cloud-providers/rosa` | Red Hat OpenShift on AWS cluster module and deployment. |
| `terraform/cloud-providers/common` | Shared prerequisites (TLS certificate, SSH key, installer-script folders), two multi-cloud examples, and a Terraform Cloud workspace manager (`workspaces/`, using the `tfe` provider). |
| `aws-eks/`, `charts/redis/`, `docs/` | EKS config and IAM policy JSON (including Bedrock assume-role), a vendored Redis Helm chart, a Gateway API setup guide. |

233 files are tracked on the default branch (counted from the clone).

## 3. License and legal

| Item | Finding | Source, read |
|---|---|---|
| Repository license | Apache-2.0 (GitHub reports `Apache-2.0`; the `LICENSE` file is the standard Apache text, 11,367 bytes) | GitHub API `repos/cisco-ai-defense/ai-defense-hybrid` and the clone, 2026-10-30 |
| Vendored chart | `charts/redis` carries its own `LICENSE` and `NOTICE`, so it has its own terms, separate from the repository's | clone, 2026-10-30 |
| The product it deploys | Commercial and proprietary. The repository's license covers the templates, not the connector, the installer script or the AI Defense service. | README and the installer-script README in the clone, 2026-10-30; product terms UNVERIFIED (not read) |

Legal notes for any future lesson:

- Apache-2.0 allows quoting short excerpts with attribution; a lesson would link, not copy.
- Using the product requires accepting Cisco's own terms for the AI Defense console and installer. I did not read them. UNVERIFIED.
- The README's example DNS zone, `gruveai.com`, appears as a default in the module variables. It is a third party's domain name, not a placeholder. A lesson must not reuse it; CAH examples use `example.com`-style names.

## 4. Maintenance status

| Measure | Value | Source, read |
|---|---|---|
| Created | 2025-10-22 | GitHub API, 2026-10-30 |
| Last commit on default branch | 2026-07-29 ("Merge pull request #13 ...") | clone `git log -1` and GitHub API commits, 2026-10-30 |
| Age of last commit at reading | about 3 months | arithmetic from the two dates above |
| Commits in history | 31 | GitHub API commits list (per_page 100 returned 31), 2026-10-30 |
| Releases | 0 | GitHub API `releases`, 2026-10-30 |
| Tags | none returned | GitHub API `tags`, 2026-10-30 |
| Archived | no | GitHub API, 2026-10-30 |
| Stars / open issues | 7 / 5 (the open-issues figure includes pull requests) | GitHub API, 2026-10-30 |
| Security policy | `SECURITY.md` exists; uses GitHub private reporting and a Cisco open-source security mailbox | clone, 2026-10-30 |

Reading: alive but small and slow, with no release or version to pin. Its own module examples tell users to pin `?ref=v1.0.0`, but no such tag exists. A lesson would have to pin a commit, and commits like this move without notice.

Signs that the repository is a working export of an internal project rather than a polished teaching asset (all read in the clone, 2026-10-30):

- `terraform/cloud-providers/README.md` documents a "Module Structure" (`terraform-modules/`, `examples/`, `gv-k8-az-lab-ai-def-cisco/`, `gv-k8-gcp-lab-ai-def-cisco/`) that does not match the tracked files, and tells readers to look under `terraform-modules/{aws,azure,gcp}-modules/ai-defense`, which are not at those paths. The real modules are under `terraform/cloud-providers/<cloud>/ai-defense-connector/module`.
- The Terraform Cloud workspace manager is hard-wired to one internal organization and project names (`SBG-AITeam`, `NonProd AWS AI Defence`) and a fixed list of environments. Nobody else can run it without editing it.
- The README says `terraform-modules/...` while a standalone AKS stack carries its own copy of the Azure submodules, so shared code is copied rather than shared.

## 5. What it would teach

Honest candidate lessons, ranked by how well each is supported by what is in the repository:

1. **One module per cloud with a common prerequisites folder.** Real, readable, and the same shape as `OpenTofu-Stacks-and-Modules`. But the repository shows it unevenly (see the drift above), and CAH already teaches modules and stacks.
2. **Terraform generating shell scripts for a later manual step** (`scripts.tf` plus `*.tftpl`). This is a known anti-pattern worth a warning: the infrastructure is declared, but the install is imperative and happens outside state, so drift and re-runs are invisible to the plan. This is the single most teachable thing, and it needs only the files, not a tenant.
3. **Secrets kept out of state.** The README and install template read the API key from an `APIKEY` environment variable or an interactive prompt "so the key is not written into Terraform state or generated files". A good pattern, small enough to be a paragraph in an existing lesson.
4. **Least-privilege listing per cloud.** The README lists both managed policies and a granular permission list for AWS, Azure and GCP. Useful as a reference table, but it is a list of what this particular kit needs, and the "simple" path attaches `IAMFullAccess` and similar broad roles.
5. **A Terraform Cloud workspace manager (`tfe` provider)** compared with Spacelift. CAH is on Spacelift; a comparison of two platforms using a repository that cannot run outside its owner's organization is thin. The Spacelift pages already cover stacks and policies.

None of the five needs this repository. Each is already covered, or can be taught better, with CAH's own OpenTofu and Spacelift pages, which are runnable by the learner.

## 6. What it needs

| Need | Detail | Source, read |
|---|---|---|
| Cisco AI Defense tenant | A console login is required to download `aidefense-connector-installation.sh` and to copy the API key. Licensing, trial availability and cost: UNVERIFIED (not found in the repository; I did not read Cisco's site). | installer-script README, 2026-10-30 |
| Cloud account | AWS, Azure, GCP or an OpenShift-on-AWS account. No DigitalOcean module exists, and CAH runs OpenTofu on DigitalOcean. | README and file tree, 2026-10-30 |
| GPU capacity | Defaults: `gpu_model = "H100"` and `gpu_node_count = 4`. The README's table maps H100 to `p5.48xlarge` (8x H100 80 GB) on AWS and `a3-highgpu-8g` (8x H100) on GCP. By the README's own table, the default is 4 nodes of 8 H100 GPUs on AWS, so 32 GPUs. L40S (`g6e.xlarge`) is the smallest option and AWS-only. GPU quota approval is normally needed for such instances (general cloud practice, UNVERIFIED for these accounts). | `terraform/cloud-providers/README.md`, 2026-10-30 |
| Broad cloud permissions | Create VPC, EKS/AKS/GKE, IAM, DNS. The simple route is `IAMFullAccess` plus VPC and Route 53 full access on AWS. | same README, 2026-10-30 |
| Terraform tooling | Terraform; the workspace manager pins `terraform_version = "1.14.5"` and uses the `tfe` provider. CAH uses OpenTofu, so version and registry behavior would need checking. UNVERIFIED. | `workspaces/` files, 2026-10-30 |

Cost: no price figure is given here because I did not read any provider price page or Cisco quote; any figure would be invented. The kit's own defaults (multi-GPU nodes) put a hands-on run far outside what a learner can be asked to pay under the pay-to-play principle (theory free, hands-on paid and optional by the person doing it). A smaller single L40S run on AWS is possible by the README's table, but still needs a paid Cisco tenant.

## 7. Safety notes

- **It would put real GPU nodes and IAM roles into a learner's account.** The install path creates cluster-wide roles, an ingress, and a Kubernetes install run by generated scripts. A teardown lesson would be mandatory, and a forgotten GPU node would be an expensive teardown failure.
- **The installer script comes from a vendor console and is run against the learner's cluster (its permissions were not inspected; UNVERIFIED).** A lesson cannot vouch for it. It must be treated as untrusted code the learner chooses to run.
- **Credentials.** Two secrets are involved: the AI Defense API key and cloud credentials with broad rights. CAH rules say no cloud keys in lessons and Doppler-style handling for anything real. A lesson would have to teach the `APIKEY` environment-variable route and nothing else.
- **No offensive content.** Nothing in this repository teaches an attack. It does not map to Break, Detect or Evade in the Build / Break / Detect / Evade / Defend flow.
- **Data flow.** The connector exists to send traffic or metadata to a vendor service. What leaves the learner's cluster is UNVERIFIED; I did not read the product documentation.
- **Third-party and brand content.** The module defaults use another organization's domain (see section 3), and the workspace manager names an internal Cisco organization. Neither belongs in a lesson, even as an example.

## 8. Fit with the AI-security track (#304)

Issue #304 proposes a track built on Cisco's open-source tools, each to be verified by running it before any lesson: `aibom`, `mcp-scanner`, `a2a-scanner`, `skill-scanner`, `adversarial-hubness-detector`, `pickle-fuzzer`, `model-provenance-kit`. Its rules: theory free, hands-on paid and optional, local Ollama for any LLM engine, no cloud keys, American English, the voice rules.

Comparing `ai-defense-hybrid` against those rules and that flow:

| #304 requirement | `ai-defense-hybrid` |
|---|---|
| Open-source tool a learner can run | No. It deploys a connector for a commercial service; it is not itself an analyzer. |
| Local Ollama, no cloud keys | No. Needs a vendor tenant API key and a cloud account with GPU quota. |
| Free theory path | Partly. The files are readable for free (items 2 and 3 in section 5). |
| Cheap optional hands-on | No. The default footprint is multi-GPU nodes plus a paid tenant (cost UNVERIFIED). |
| Build / Break / Detect / Evade / Defend | At most "Build" and "Defend" (deploy a guardrail connector). Nothing for Break, Detect or Evade. |
| Verified by running before a lesson | Cannot be done without a paid tenant and GPU quota, which this task and the issue forbid. |

It is not in the #304 candidate list and does not belong in it. The seven listed tools are the real candidates for that track. Whether they earn pages is a separate question for #304 and is not decided here.

## 9. Recommendation

**Skip as a lesson. Close #303 as "evaluated, skipped".**

Reasons:

1. It cannot be run by a learner without a paid vendor tenant and GPU cloud capacity, so the pay-to-play principle (and the issue's own "no paid Cisco service, no credentials" limit) means the hands-on half cannot exist, and the lesson could not be verified before publishing.
2. No DigitalOcean module exists; CAH's teaching stack is OpenTofu on DigitalOcean with Spacelift.
3. What it can teach in theory (module-per-cloud layout, Terraform-generated scripts as drift, secrets kept out of state) is already covered by, or better placed in, CAH's own OpenTofu and Spacelift pages, which a learner can run.
4. The repository is young, has no release or tag, and shows signs of being an internal export (documentation that does not match the file tree, a workspace manager tied to one internal organization). A lesson pinned to a commit would age without notice.
5. It does not fit the #304 flow or its rules (section 8).

Cheap alternative, optional and not recommended as a priority: add two or three sentences to an existing OpenTofu lesson, naming "Terraform that writes install scripts for a later manual step" as a drift risk, linking this repository at a pinned commit as one example. That is a theory-only change and costs nothing to run. It would need its own issue.

Revisit if any of these change: a DigitalOcean or generic Kubernetes module appears, Cisco offers a free tier or trial that needs no GPU, the repository gets tagged releases, or the maintainer wants a vendor-neutral "how a vendor ships IaC" comparison page.

## 10. Decision needed from the maintainer

1. Confirm: skip the lesson and close #303 as evaluated and skipped (recommended). The alternative is to defer, which keeps the card open with no work planned; I do not recommend it, since none of the revisit conditions has a date.
2. Decide whether to file a separate, small issue for the optional theory-only paragraph in an existing OpenTofu lesson (section 9). Default if you say nothing: do not file it.
3. Confirm that `ai-defense-hybrid` stays out of the #304 list. Which of the seven Cisco open-source tools earn pages is a separate #304 decision.

## 11. What I did not do or could not check

- Did not run, install or deploy anything from the repository; read it only.
- Did not read the Cisco AI Defense product pages, pricing or terms, so licensing, trial availability, cost and data flow are UNVERIFIED.
- Did not verify any provider price or GPU quota policy.
- Did not run the seven #304 tools; no statement here about them beyond the issue text.
- The clone was shallow (`--depth 1`); commit count and dates come from the GitHub API, not local history.
- The repository may change after the read date.

## 12. Sources

| Source | Read |
|---|---|
| Issue #303 and #304 in this repository (`gh issue view`) | 2026-10-30 |
| Clone of `github.com/cisco-ai-defense/ai-defense-hybrid` at commit `e48fc08`, files: `README.md`, `LICENSE`, `SECURITY.md`, `terraform/cloud-providers/README.md`, `terraform/cloud-providers/common/prerequisites/aidef-install-script/README.md`, `terraform/cloud-providers/common/workspaces/*.tf`, `terraform/cloud-providers/aws/ai-defense-connector/module/templates/script-eks-ai-def-install.sh.tftpl`, and the file listing | 2026-10-30 |
| GitHub REST API: `repos/cisco-ai-defense/ai-defense-hybrid`, `/commits`, `/releases`, `/tags` | 2026-10-30 |
| Local prose draft of the summary: `llm-local`, task label `eval303-summary`, then rewritten and checked claim by claim against the sources above (the draft misdescribed the license as "free" and added "on top of" wording; both were replaced) | 2026-10-30 |
