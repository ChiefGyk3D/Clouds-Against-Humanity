# Self-hosting AI: Ollama, FrankenLLM, vLLM and the GPU stack (PyTorch, CUDA, ROCm and Intel)

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

> **Prerequisites.** [Containers and Docker basics](Containers-and-Docker-Basics.md): images, containers, published ports. A terminal ([The terminal and your first script](Terminal-and-Your-First-Script.md)). The idea of running a service yourself and what it costs: [Self-hosting: when and why, with SearXNG](Self-Hosting-When-and-Why-with-SearXNG-as-the-Worked-Example.md). The free exercise runs in a virtual machine you throw away, so [Virtual machines and hypervisors](Virtual-Machines-Hypervisors-Desktop-and-Datacenter-Options.md) is the side page if you do not have one. About 3 hours for the reading and the exercise (est.).

> **Status: unverified draft. No command on this page was run.** On **2026-11-25** I read the vendor pages named in the [claims register](#claims-register) and the public README and docs of FrankenLLM, and wrote the page from them. I did not install Ollama, vLLM, PyTorch, a GPU driver or a container, and I have no GPU on the machine I wrote this on, so every command in the exercise is copied from those pages or written from them and has not been seen to work. The vendor pages were read through a fetch tool that returns an extract of each page, so a quotation is as that extract gave it and is worth checking against the page. Anything I could not read is marked **est.** or listed under [Not verified, plainly](#not-verified-plainly). Version numbers and support lists change faster than this page does: trust what your terminal prints over what this page says.

> **Where this runs, and the rule.** Everything in the exercise is local and free. It uses one small model, a throwaway virtual machine and the loopback address `127.0.0.1`. Nothing here asks you to expose a model server to a network, to rent a GPU or to open an account. The exercise uses your electricity and downloads a model of a few hundred megabytes; it creates no cloud account or usage bill. Placeholder names only.

<!-- BEGIN GENERATED PAGE CONTENTS: rewritten from the page's own headings by scripts/gen_wiki_nav.py; edit the headings, not this block -->
**On this page:**

- [What you will be able to do](#what-you-will-be-able-to-do)
- [What the wiki already says](#what-the-wiki-already-says)
- [Why self-host a model, and what it costs](#why-self-host-a-model-and-what-it-costs)
- [VRAM math: weights, KV cache and context length](#vram-math-weights-kv-cache-and-context-length)
- [Ollama](#ollama)
- [LM Studio](#lm-studio)
- [Model families](#model-families)
- [FrankenLLM as the worked example](#frankenllm-as-the-worked-example)
- [vLLM](#vllm)
- [The other servers, briefly](#the-other-servers-briefly)
- [The stack under the servers](#the-stack-under-the-servers)
- [Security: the model API has no login](#security-the-model-api-has-no-login)
- [Using AI to build your own AI host](#using-ai-to-build-your-own-ai-host)
- [Try it yourself: a small model in a throwaway VM](#try-it-yourself-a-small-model-in-a-throwaway-vm)
- [Build, break, detect, evade, defend](#build-break-detect-evade-defend)
- [Checkpoint](#checkpoint)
- [Common mistakes](#common-mistakes)
- [Claims register](#claims-register)
- [Not verified, plainly](#not-verified-plainly)
<!-- END GENERATED PAGE CONTENTS -->

## What you will be able to do

- Give reasons to self-host a model and say what it costs, and say when to use a hosted model instead.
- Work out roughly whether a model fits in a given amount of GPU memory, from a formula you can show: weights, plus the KV cache, plus overhead.
- Explain why a longer context window changes what fits, and read `ollama ps` to see it.
- Say what Ollama is, what its defaults are (port, keep-alive, context length), and what a Modelfile does.
- Explain what LM Studio adds as a desktop app, local OpenAI-compatible server and headless or CLI option, and keep that server on loopback.
- Compare the Gemma, Mistral, Qwen, GLM and Llama families without treating a benchmark chart as a purchasing decision.
- Describe FrankenLLM, a public multi-GPU Ollama layout, and say what its own docs say about where it listens.
- Say when vLLM is the right server and when it is overkill, and name three other servers.
- Explain how PyTorch is tied to CUDA, ROCm, XPU or CPU, and what the driver, the toolkit and the container toolkit each do on NVIDIA.
- Say what is and is not officially supported on AMD and Intel, and what I could and could not verify.
- Name the security problems of the stack (no authentication on the local API, binding to every address, pickle files) and the defenses.
- Use an AI assistant to plan and debug a self-hosting setup without trusting it further than you can check it.

## What the wiki already says

| Idea | Where it is today | What this page adds |
|---|---|---|
| Self-hosting is a trade: control against a pager that never stops | [Self-hosting: when and why, with SearXNG](Self-Hosting-When-and-Why-with-SearXNG-as-the-Worked-Example.md) | The same checklist applied to a model server, plus the cost that is new here: GPU memory. |
| Containers, published ports, volumes, the daemon | [Containers and Docker basics](Containers-and-Docker-Basics.md) | Not repeated. Open WebUI is run this way. |
| An exposed service is attack surface; shrink and measure it | [Attack surface: list, shrink, measure](Attack-Surface-List-Shrink-Measure.md) | The model API as a service with no login. |
| Pin versions, never trust a package name you did not check | [Glossary: supply chain](Glossary.md), [Patch management](Patch-Management-and-Automatic-Security-Updates.md) | Model files are a supply chain too. |
| Secrets stay out of files and chats | [Secrets from day one](Secrets-From-Day-One.md), [Doppler and secrets](Doppler-and-Secrets.md) | What not to paste into an assistant. |
| Reach a private service over a private path, not the open internet | [Twingate](Twingate.md), [Subnets, NAT and firewalls by hand](Subnets-NAT-and-Firewalls-By-Hand.md) | Why the model API wants one. |
| Hashes and signatures tell you a file is the file | [Hashing, encryption and keys](Hashing-Encryption-and-Keys.md) | Checking a downloaded model or script. |

## Why self-host a model, and what it costs

The reasons people give, and what holds up:

- **Privacy.** A prompt sent to a hosted model is read by someone else's servers under someone else's terms. A local model keeps the text on your machine. That is a real gain for notes, source code and logs. It does not make the model correct, and it does not protect you if the machine itself is exposed (see [the security section](#security-the-model-api-has-no-login)).
- **Cost.** A hosted model bills per token or per month. A local one costs the card, the power and your time. Whether it is cheaper depends on how much you use it, and I read no price page for this lesson, so I give no number (**est.**). A card that sits idle is the expensive case.
- **Control.** You pick the model, the version, the context length and the logging. Nothing is deprecated under you. You also own every update.
- **Availability.** It works with the internet down. It stops when your machine does.

The costs that the pitch leaves out:

| You gain | You take on |
|---|---|
| Prompts stay on your machine | A GPU or a lot of patience on a CPU; models that fit are smaller and weaker than the largest hosted ones (**est.**) |
| No per-token bill | Power, noise, heat and the risk that a newer framework stops supporting the card (**est.**) |
| You choose the model and version | Reading model cards, licenses and file formats, and a model supply chain you must vet |
| It runs offline | Driver and runtime versions that must match each other (the [stack section](#the-stack-under-the-servers) is mostly about this) |
| Nobody else sees the logs | Nobody else secures the API either |

The same rules as [the SearXNG lesson's "when not to self-host"](Self-Hosting-When-and-Why-with-SearXNG-as-the-Worked-Example.md#when-not-to-self-host) apply: if you will not patch it, will not watch it, and the hosted service meets your threat model, do not run it. A hosted model is the right answer for a task that needs the strongest model available and involves nothing sensitive.

## VRAM math: weights, KV cache and context length

VRAM is the memory on the GPU. A model has to fit in it, or part of the work moves to the CPU and system RAM and gets much slower. Ollama's own docs show this as a split in `ollama ps`: the Processor column reads "100% GPU", "100% CPU", or something like "48%/52% CPU/GPU" (FAQ). Two things fill VRAM.

**1. The weights.** The model's parameters, stored at some precision.

```text
weights (bytes) = parameters x bits per parameter / 8
```

Quantization stores each parameter in fewer bits. Worked example for a model with 7 billion parameters, in decimal gigabytes (7 x 10^9 parameters times the bytes per parameter):

| Precision | Bytes per parameter | Weights |
|---|---|---|
| 16-bit (f16) | 2 | 14.0 GB |
| 8-bit | 1 | 7.0 GB |
| 4-bit | 0.5 | 3.5 GB |

These are the raw minimums. Real files are larger, because some tensors stay at higher precision and the file carries metadata. The Ollama library page for `qwen2.5` lists these file sizes: 0.5b is 398 MB, 1.5b is 986 MB, 3b is 1.9 GB, 7b is 4.7 GB, 14b is 9.0 GB, 32b is 20 GB, 72b is 47 GB. Dividing each size by the parameter count in its tag gives about 0.80 bytes per parameter for the 0.5b file and 0.63 to 0.67 for the larger ones, so roughly 5 to 6.4 bits per parameter. The page states no quantization for these tags, and the tag's count is a round number (the true count differs), so treat the arithmetic as a size check, not a measurement of the format.

**2. The KV cache.** While a model generates text it keeps, for every token already in the context and for every layer, a key and a value vector, so it does not recompute them. That store is the KV cache. It grows with the number of tokens in the context window, and it is on top of the weights.

```text
KV cache (bytes) = 2 x layers x KV heads x head dimension x bytes per value x tokens
```

The 2 is one key plus one value. Worked example with **invented inputs shaped like a mid-size model that uses grouped-query attention**: 32 layers, 8 KV heads, head dimension 128, stored as f16 (2 bytes, which is the default KV cache type on Ollama's FAQ page):

```text
2 x 32 x 8 x 128 x 2 = 131,072 bytes = 128 KiB per token
```

| Context length (tokens) | KV cache for those inputs |
|---|---|
| 2,048 | 0.25 GiB |
| 8,192 | 1 GiB |
| 32,768 | 4 GiB |
| 131,072 | 16 GiB |

I did not read these inputs from a model card, so they describe a shape, not a particular model (**est.**). The number agrees with the figure FrankenLLM's configuration doc gives, "~130MB per 1K tokens for an 8B model", which is 128 KiB x 1,000 tokens rounded. Another model has other inputs, and a model with sliding-window attention (FrankenLLM's README says Gemma 3 uses one) keeps less than this formula says. The point of the table is the shape: the cache grows in a straight line with the context, and at 131,072 tokens it is larger than the 4-bit weights of the 7B model by a factor of four.

**Why context length changes what fits.** The weights are fixed once you choose the model. The context length is a setting, and the KV cache scales with it. So the same model on the same card can fit at 8,192 tokens and spill to the CPU at 32,768. FrankenLLM's configuration doc gives this example: on a 16 GB card, one 12B model and an 8B guard model stay resident together at an 8,192-token context (about 14.2 GB) but not at 16,384, where "the guard evicts the main model".

**The rule of thumb to carry:**

```text
fits if: weights + KV cache at your context + runtime overhead <= VRAM
```

I measured nothing and read no number for the overhead, so leave margin (**est.**) and check with `ollama ps` (the PROCESSOR and CONTEXT columns, per Ollama's context-length page) and `nvidia-smi` after the model is loaded. A rule that you computed is a lead. What the server reports after loading is the measurement.

## Ollama

Ollama is a program that downloads models, runs them, and serves them over a local HTTP API. Its README describes it as a way to "get up and running" with named open models, is under the MIT license, and names llama.cpp among its backends (GitHub README, read 2026-11-25). A model library at ollama.com/library holds the downloads, each with tags for sizes (`qwen2.5:0.5b`, `qwen2.5:7b` and so on).

**Install and run, from the docs.** On Linux the install command is `curl -fsSL https://ollama.com/install.sh | sh`, and the Linux page also gives a manual install (download a `.tar.zst`, extract it into `/usr`) and a systemd unit: it creates an `ollama` user, runs `ExecStart=/usr/bin/ollama serve`, and shows `sudo systemctl edit ollama` for environment variables and `journalctl -e -u ollama` for logs. Models live under `/usr/share/ollama/.ollama/models` on Linux (override with `OLLAMA_MODELS`). Note that the one-line install pipes a script from the internet into a shell. The [AI-assistant section](#using-ai-to-build-your-own-ai-host) says what to do instead.

**The defaults I read.** Each is from the Ollama docs page named in the register.

| Setting | Default on the page | Change it with |
|---|---|---|
| Listening address | "Ollama binds 127.0.0.1 port 11434 by default." | `OLLAMA_HOST` (the page's example is `0.0.0.0:11434`) |
| Keep-alive | "By default models are kept in memory for 5 minutes before being unloaded." | `OLLAMA_KEEP_ALIVE`, or `keep_alive` per request (`0` unloads at once) |
| Parallel requests | "other backends default to 1" (the page says MLX on Metal chooses its own default) | `OLLAMA_NUM_PARALLEL` |
| Models loaded at once | "3 * the number of GPUs or 3 for CPU inference" | `OLLAMA_MAX_LOADED_MODELS` |
| Request queue | 512 | `OLLAMA_MAX_QUEUE` |
| KV cache type | `f16`; options `f16`, `q8_0`, `q4_0`; "a global option" | `OLLAMA_KV_CACHE_TYPE` |
| Flash attention | Set to `1` to force on, `0` to disable | `OLLAMA_FLASH_ATTENTION` |
| Context length | See below, because the pages disagree | `OLLAMA_CONTEXT_LENGTH`, `/set parameter num_ctx`, or `num_ctx` in an API request |

**Four pages, four numbers for the context length.** The FAQ says "By default, Ollama uses a context window size of 4096 tokens." The context-length page says the default depends on VRAM: "< 24 GiB VRAM: 4k context", "24-48 GiB VRAM: 32k context", ">= 48 GiB VRAM: 256k context". The Modelfile page's parameter table says `num_ctx` is "(Default: 2048)". And FrankenLLM's README says versions at or above 0.33 default to 32768. I do not know which page is current for your version, and I did not install any. That is not a reason to pick one; it is the reason to read the value your server reports (`ollama ps` shows a CONTEXT column) and to set it yourself when it matters.

**A Modelfile** is Ollama's recipe for a model, like a Dockerfile for a prompt setup. The page lists `FROM` (required), `PARAMETER`, `TEMPLATE`, `SYSTEM`, `LICENSE`, `MESSAGE`, `REQUIRES` and `CAPABILITY`. Its example sets a temperature and a context size and a system message:

```text
FROM llama3.2
PARAMETER temperature 1
PARAMETER num_ctx 4096
SYSTEM You are Mario from super mario bros, acting as an assistant.
```

You build it with `ollama create choose-a-model-name -f ./Modelfile` and run it with `ollama run choose-a-model-name`. Importing your own weights works for Safetensors directories and GGUF files (import page); the same page says "Ollama does not quantize GGUF models during import", so quantize first with llama.cpp's `llama-quantize` if you need it.

**The API.** The local base URL is `http://localhost:11434/api`. The pages list `POST /api/generate`, `GET /api/tags` (the models you have), and `GET /api/ps` (models loaded now, with `size`, `size_vram` and `context_length`). `stream` defaults to true on `/api/generate`; the examples set it to false to get one JSON reply. "Cloud requests need an API key. Local requests do not."

**GPU backends.** The GPU page lists:

- **NVIDIA:** compute capability 5.0 or higher and driver 550 or newer; for compute capability 5.0 to 6.2, driver 570 or newer.
- **AMD:** "Ollama requires the AMD ROCm v7 driver on Linux." On Windows the supported cards are limited to select Radeon RX 7000 and Radeon PRO W7000 series.
- **Vulkan:** support for more GPUs on Windows and Linux, "enabled by default when the backend is installed". On Linux it may need extra packages, and reporting VRAM needs root or `sudo setcap cap_perfmon+ep /usr/local/bin/ollama`.
- **Apple:** Metal.
- **Intel:** the page has no Intel section; Intel GPUs on Linux appear only under Vulkan, with a link to Intel's driver docs.

GPU selection is by environment variable: `CUDA_VISIBLE_DEVICES` for NVIDIA (UUIDs are more reliable than numbers; list them with `nvidia-smi -L`), `ROCR_VISIBLE_DEVICES` for AMD, `GGML_VK_VISIBLE_DEVICES` for Vulkan. An invalid ID such as `-1` forces CPU.

## LM Studio

LM Studio is a desktop application for finding, downloading and running models on your own computer. It also provides a local OpenAI-compatible HTTP server and a headless or command-line mode for a machine where you do not want the desktop interface (**est.**). I could not read LM Studio's documentation in this environment, so every LM Studio-specific detail in this section is **est.** Verify it before you depend on it.

Ollama is a small service and CLI with its own model library and API. LM Studio puts model discovery, downloads, chat, loading controls and a compatible server in one desktop application, with a headless route too (**est.**). vLLM is built for throughput, batching and multiple clients; LM Studio is aimed more at interactive use on one workstation (**est.**). LM Studio fits one person inspecting several quantizations and talking to them locally. Ollama is usually simpler for a boot-time service with basic automation. For many concurrent requests, start by testing vLLM.

**Keep the server local.** In the server settings, set the host or bind address to `127.0.0.1` and leave local-network access disabled (**est.**). The exact setting name and default were not read. Verify the result instead of trusting the checkbox:

```bash
ss -ltn
curl http://127.0.0.1:<LM-STUDIO-PORT>/v1/models
```

The first command should show the chosen port listening only on `127.0.0.1` or `::1`, instead of `0.0.0.0`, `[::]` or a LAN address (**est.**). Replace the placeholder with the port LM Studio reports. From another machine on the same network, a connection to that port should fail. Keep the host firewall default-deny. Do not add a router port-forward, publish the port from a container or put a public tunnel in front of it. Loopback is the control; the absence of a menu item called "public" proves nothing.

**Models and formats.** LM Studio can search model repositories and download models, commonly from Hugging Face publishers and community quantizers (**est.**). A search result is not provenance. Check who published the repository, then read its model card and license. Confirm the base model, quantizer, file size and hash when one is supplied. **GGUF** is the common llama.cpp-family file format for quantized models on Windows, Linux and macOS (**est.** for LM Studio support). **MLX** models target Apple's MLX stack on Apple silicon (**est.**). The same model name does not make the files interchangeable. Pick the format and quantization for the backend LM Studio actually selected.

Before calling it ready, verify the exact model and quantization against the license and download source. Check the listening address, port and API response, then confirm the context length, GPU offload and observed VRAM or unified-memory use. Restart it and check again. Send one known prompt through the desktop chat and the OpenAI-compatible endpoint to prove both paths reach the model you intended. Those checks only prove that you loaded the intended model. Your own test set tells you whether it is any good at your work.

## Model families

A family name is not one model. It covers generations and parameter counts, plus base and instruction-tuned variants with different context sizes, modalities and quantizations. The table is only a map. I could not read the makers' model cards in this environment, so the makers, sizes, license summaries and strengths below are all **est.** Do not make a license decision from an estimated row.

| Family | Maker | Representative sizes | License type | Common reason to test it |
|---|---|---|---|---|
| Gemma | Google (**est.**) | Roughly 1B to 27B across generations; multimodal variants exist (**est.**) | Open weights under Google's Gemma terms, not OSI open source (**est.**) | Strong small and mid-size choices, multilingual and multimodal variants, and good workstation-sized options (**est.**) |
| Mistral | Mistral AI (**est.**) | Roughly 3B to large mixture-of-experts and dense models (**est.**) | Mixed by release: some Apache-2.0, some open-weight custom licenses, and some gated or commercial terms (**est.**) | Efficient smaller models, instruction following, coding and mixture-of-experts options (**est.**) |
| Qwen | Alibaba Cloud's Qwen team (**est.**) | Roughly 0.5B to 72B and larger mixture-of-experts variants (**est.**) | Open weights; many releases use Apache-2.0, but check the exact model (**est.**) | Multilingual work, coding, math, long-context and many size choices (**est.**) |
| GLM | Zhipu AI and Tsinghua-origin teams (**est.**) | Roughly 6B to large dense and mixture-of-experts variants (**est.**) | Open weights under release-specific terms; OSI status varies or is unclear (**est.**) | Chinese and English work, tool use, coding and agent-style variants (**est.**) |
| Llama | Meta (**est.**) | Roughly 1B to 405B across recent generations (**est.**) | Open weights under Meta's Llama license, not OSI open source (**est.**) | Broad tool support, many community quantizations and a large compatibility ecosystem (**est.**) |

"Open weights" means you can obtain model weights under a license. It says nothing by itself about the Open Source Initiative's definition, commercial use or redistribution of a modified model. Read the exact license attached to the exact repository and version you download. The code around a model can have a different license from the weights.

**Choose by memory first, then by task.** Start with the page's formula:

```text
fits if: weights + KV cache at your context + runtime overhead <= VRAM
```

For a quick lower bound, use `parameters x bits per parameter / 8` for weights. Then add the KV cache for the context you will actually use and leave overhead margin. On an 8 GB card, that usually means testing roughly 3B to 8B models at 4-bit quantization and a modest context (**est.**). At 12 to 16 GB, roughly 7B to 14B 4-bit models become plausible (**est.**). At 24 GB, some models around 20B to 32B at 4-bit may fit, or a smaller model can keep a much larger context (**est.**). Architecture, quantization metadata, partial CPU offload and backend overhead can move every boundary. Load it and measure.

After it fits, choose a few families with variants aimed at your task. Give them the same prompts, context, sampling settings and output rubric. Record what they get right and wrong, along with tokens per second, time to first token and memory use. A vendor benchmark, leaderboard win or quantizer's description does not tell you whether the model works on your tasks. A smaller model that answers your questions reliably is better than a larger one that barely fits and spends its life evicting the KV cache.

## FrankenLLM as the worked example

FrankenLLM is a public repository by the maintainer of this wiki (github.com/ChiefGyk3D/FrankenLLM, MPL-2.0). I read its README and its `docs/` directory in a local clone whose last commit is dated 2026-10-07, on 2026-11-25. This section describes only what those documents say. I did not run it, and the page uses `127.0.0.1` and placeholders where the repository has real addresses.

**The idea.** One Ollama instance per GPU, each on its own port, so each card runs a model sized for its own VRAM and one cannot interfere with the other. The README: "Each GPU has its own Ollama instance on separate ports." Defaults are ports 11434 and 11435 for GPU 0 and GPU 1, more in the configuration doc. The instances are told which GPU to use through `CUDA_VISIBLE_DEVICES` in their systemd units (`ollama-gpu0`, `ollama-gpu1`), and each has its own model directory, so "models added to GPU 0 won't appear on GPU 1".

```text
GPU 0 (larger card)  ->  ollama-gpu0.service  ->  port 11434  ->  model A
GPU 1 (smaller card) ->  ollama-gpu1.service  ->  port 11435  ->  model B
                             both fronted by Open WebUI in Docker
```

| Piece | What the docs say it does |
|---|---|
| Installer | `setup-frankenllm.sh` detects Docker, Ollama and existing services, finds the GPUs with `nvidia-smi`, installs Ollama services and optionally Open WebUI, and works locally or over SSH. A manual route is `configure.sh` then `install.sh`. |
| systemd services | One per GPU, enabled at boot, restarted on failure. The install scripts also mask the default `ollama.service`, because that one grabs port 11434 first (the README's troubleshooting section describes the "address already in use" failure). |
| Configuration | A `.env` file: GPU count, ports, one model per GPU, an optional guard model, and a per-instance context length (`FRANKEN_GPU0_CONTEXT=8192`, written into the unit as `OLLAMA_CONTEXT_LENGTH`). |
| Keep-alive and warmup | New installs set `OLLAMA_KEEP_ALIVE=-1` so models stay loaded; a warmup service sends each model a small request at boot so the first real question does not wait on a load. The warmup doc gives per-model timeouts (180 s on GPU 0, 120 s on GPU 1) and exits non-zero if any model fails to load. |
| Health monitor | A health module checks the GPU on every boot before Ollama starts, detects driver and library mismatches, tries to reload the NVIDIA modules, reboots up to three times, and leaves a login alert if the problem persists. |
| Open WebUI | Installed in Docker on port 3000, connected to every Ollama instance through `host.docker.internal`; the first account becomes the admin. |
| RAG datasets | `scripts/fetch-rag-datasets.py` (Python standard library only) downloads public sources such as the OWASP cheat sheets, MITRE ATT&CK, recent NVD CVEs, CISA's known exploited vulnerabilities, Sigma rules and RFCs into text files, and can upload them into Open WebUI knowledge collections through its API. An embedding model on one GPU finds the relevant chunks and the chat model on the other writes the answer. |

**What the docs teach about VRAM, in its own words.** The configuration doc says the context length is the knob that decides whether two resident models coexist, and tells you to confirm with `ollama ps` that each shows `100% GPU` after warmup. It also warns that "Ollama keys a loaded model on its context size": if a client asks for a different `num_ctx` than the one a model was warmed with, Ollama unloads and reloads it, which costs the load time and can push out another resident model. That is the [VRAM math](#vram-math-weights-kv-cache-and-context-length) section happening in a real deployment.

**What the docs say about where it listens.** The Getting Started doc, in its port-conflict section: "FrankenLLM services bind to 0.0.0.0 (all interfaces)", against the stock service's `127.0.0.1:11434`. Its examples call the API at a remote server address on ports 11434 and 11435, and Open WebUI's N8n example uses the server's address on port 3000. In the documents I read I found no authentication step, firewall step or reverse proxy for the Ollama ports. The [security section](#security-the-model-api-has-no-login) says why that matters: the Ollama API has no login. If you copy this layout, bind the instances to loopback or a private interface, or put a default-deny firewall in front of them, before you do anything else. That is a defect in the layout as documented, not a reason to avoid reading it: the per-GPU split, the warmup and the context-versus-VRAM discipline are good ideas, and the missing step is an addition, not a redesign.

## vLLM

vLLM is a model server designed for throughput when many requests arrive at once. Its docs home describes it as a library for LLM inference and serving, originally from the Sky Computing Lab at UC Berkeley.

**What makes it different.**

- **PagedAttention.** The KV cache is split into fixed-size blocks instead of one contiguous slab per request. The design page I read describes the blocks and says the page is historical (the old kernel no longer exists and the paging now lives in the attention backends with block tables built by the scheduler). It did not describe fragmentation, so the usual explanation, that paging wastes less memory than reserving a worst-case slab per request, is **est.** here.
- **Continuous batching.** The docs list "Continuous batching of incoming requests, chunked prefill, prefix caching". New requests join the running batch instead of waiting for it to finish.
- **Quantization.** The docs list FP8, MXFP8/MXFP4, NVFP4, INT8, INT4, GPTQ/AWQ, GGUF, compressed-tensors, ModelOpt and TorchAO among others.
- **An OpenAI-compatible server.** `vllm serve <model>` starts one, and the endpoint list I read includes `/v1/chat/completions`, `/v1/completions`, `/v1/embeddings`, `/v1/models`, `/health` and `/metrics`, plus an Anthropic-style `/v1/messages`.

**Hardware.** The installation page lists GPUs (NVIDIA CUDA, AMD ROCm, Intel XPU, Apple silicon through vLLM-Metal), CPUs (Intel and AMD x86, ARM AArch64, Apple silicon, IBM Z) and third-party hardware plugins. The CPU page gives Python 3.11 to 3.14, Linux for x86 (AVX-512 recommended, AVX2 "Limited features"), pre-built x86 wheels since 0.17.0, Docker images (`vllm/vllm-openai-cpu`), and an example, `vllm serve facebook/opt-125m --dtype=bfloat16`. Apple silicon on CPU is "experimental" and has no pre-built wheel.

**Memory defaults to understand before you start it.** The `vllm serve` reference describes `--gpu-memory-utilization`: "If unspecified, 1.0 with the extensible KV cache (sized from measured memory) and 0.92 otherwise." The option name says it is a fraction of GPU memory, so vLLM is planning to use nearly all of the card unless you lower it (that reading is **est.**; I did not read the longer description). `--max-model-len` defaults to what the model config says, and a model with a long native context sizes a long KV cache. Ollama loads a model at the size you pulled and unloads it after five idle minutes; vLLM is built to be the one tenant of the card. The same page: `--port` defaults to 8000, `--dtype` and `--kv-cache-dtype` default to `auto`, `--tensor-parallel-size` defaults to 1, `--trust-remote-code` defaults to False.

**When it beats Ollama, and when it is overkill.** This part is my inference from the feature list, not a benchmark, and I read none (**est.**).

| Situation | Better fit |
|---|---|
| One person, one or two chats, a laptop or one consumer card | Ollama. vLLM's gains come from batching many requests, and you have one. |
| A service answering many users or many programs at the same time | vLLM, because continuous batching exists for that case. |
| You want pull-a-model-and-go, with a library and a Modelfile | Ollama |
| You need to split one big model across several GPUs | vLLM documents tensor parallelism (`--tensor-parallel-size`); Ollama's FAQ describes placing a model on one GPU if it fits (I did not read what it does when it does not). |
| You are sizing a box for a quiet home lab | Ollama. vLLM's habit of claiming the card is a cost when the card also runs your desktop. |

## The other servers, briefly

Only what I read on each project's own page.

- **llama.cpp.** "LLM inference in C/C++", MIT license, built on the ggml library. Its build guide lists backends and flags: CPU, BLAS, Metal (on by default on Apple GPUs), CUDA (`-DGGML_CUDA=ON`), HIP for AMD (`-DGGML_HIP=ON`, "requires ROCm"), Vulkan (`-DGGML_VULKAN=ON`), SYCL for Intel GPUs, OpenVINO for Intel CPUs, GPUs and NPUs, MUSA for Moore Threads, CANN for Ascend NPUs, OpenCL for Qualcomm Adreno and WebGPU. Its server is OpenAI-compatible. Ollama names llama.cpp among its backends, and Ollama's import page points at `llama-quantize` from it.
- **Open WebUI.** A front end, not a model server: "a self-hosted AI platform", with Ollama and OpenAI-compatible backends, including vLLM, as connections. Docker quick start: `-p 3000:8080`, a named volume at `/app/backend/data`, and an `ollama` default of `http://host.docker.internal:11434`. The first account is the administrator; sign-up then turns itself off. The docs say to pin a version tag for anything reproducible, because `:main` and `:latest` are rolling builds.
- **LocalAI.** "The open-source AI engine", MIT license, speaks the OpenAI and Anthropic formats, and lists NVIDIA (CUDA 12 and 13), AMD (ROCm), Intel (oneAPI/SYCL), Apple, Vulkan, Jetson and CPU-only.
- **SGLang.** "A high-performance serving framework for large language models and multimodal models", Apache-2.0, lists NVIDIA, AMD Instinct, Google TPU, Intel Arc GPUs and Xeon CPUs, Apple silicon, Huawei Ascend and Moore Threads.
- **Text Generation Inference (TGI).** Hugging Face's server. Its repository README says it is "now in maintenance mode" and the repository was "archived by the owner on Mar 21, 2026", which means read-only. If a guide tells you to deploy TGI today, that is a fact to weigh.

## The stack under the servers

Every server above sits on the same layers. A mismatch between these layers is one failure to check, especially after a driver, framework or server update.

```text
model server (Ollama, vLLM, llama.cpp ...)
      |
framework or engine (PyTorch, ggml)
      |
vendor compute stack (CUDA | ROCm/HIP | oneAPI/SYCL/Level Zero | Vulkan)
      |
kernel driver
      |
GPU
```

| Component | NVIDIA | AMD | Intel |
|---|---|---|---|
| Stack | CUDA | ROCm (HIP is its programming interface) | oneAPI: DPC++/SYCL compiler, Level Zero, OpenVINO |
| PyTorch build | `cuXXX` wheels | ROCm wheels, same `torch.cuda` API | XPU wheels, `torch.xpu` API |
| Source license | Proprietary toolkit and driver (est.) | Open source (ROCm home page) | Mixed; Level Zero MIT, DPC++ in an open LLVM repo |
| Ollama | Compute capability 5.0+, driver 550+ | ROCm v7 on Linux | Vulkan only, per the page read |
| Main limit covered here | Driver and toolkit versions must agree | Official support list is short and Linux first | Several Intel tools retired or archived in 2026 |

### PyTorch

PyTorch is the Python framework most model code is written in, and the engine under vLLM. A PyTorch **build** is compiled for one compute platform, so the wheel you install decides which GPUs it can use. The install selector on pytorch.org asks for the build, OS, package manager, language and compute platform, and prints one command whose index URL names the platform. The XPU page I read shows the pattern: `pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/xpu`. The CUDA wheels use `cuXXX` in the same position (the static text of the selector page I fetched showed `.../whl/cu118`).

I could not read what the selector offers **today**. The page is built by JavaScript, and the static text my fetch returned listed "Stable (2.7.0)" with CUDA 11.8, 12.6 and 12.8 and ROCm 6.3, while the PyTorch documentation tree I read is version 2.15. So that static text is stale, and I state no current version or current platform list (Not verified). Use the selector in a browser and copy the command it prints for your machine.

Two facts from the PyTorch docs that save time. On AMD, PyTorch "intentionally reuses the existing `torch.cuda` interfaces", the device string stays `cuda` (`'rocm'` and `'hip'` are not valid), and `torch.cuda.is_available()` returns the same on CUDA and HIP builds, so to tell them apart check `torch.version.hip` (set on ROCm builds) and `torch.version.cuda`. On Intel, `torch.xpu.is_available()` prints `False` if the driver is not installed correctly, which is the docs' advice to check first.

### CUDA (NVIDIA)

CUDA is NVIDIA's compute platform, and the word covers three separate things that people blur:

- **The driver.** The CUDA programming guide: "The NVIDIA Driver can be thought of as the operating system of the GPU." It is installed on the host and required for any GPU use.
- **The toolkit.** "A set of libraries, headers, and tools for writing, building, and analyzing software." It is a separate product from the driver.
- **The runtime.** A library inside the toolkit that provides the API programs call, built on the lower-level driver API.

So a machine that only runs PyTorch or Ollama needs the driver, and the CUDA runtime the program needs ships inside the wheel or the server (that last part is general knowledge, **est.**: I did not read a page that says PyTorch wheels bundle it). The compatibility page describes how far apart the pieces may be: "minor version compatibility" lets an application built within the same major CUDA release family run on a sufficiently new driver with some feature limits, and "forward compatibility" uses a `cuda-compat-<major>-<minor>` package to let a newer toolkit's applications run on an older base driver, subject to platform and GPU support. It adds that driver updates may follow different schedules than toolkit updates, which is why "driver/library version mismatch" is a classic failure (FrankenLLM's README has a section on it and a health module to fix it after a driver update without a reboot).

**Compute capability** is the version number of a GPU's hardware features, written X.Y. NVIDIA's table lists, for example, the GeForce RTX 3090 at 8.6, the RTX 4090 at 8.9 and the RTX 5090 at 12.0. Ollama's minimum is 5.0. A framework build supports a list of capabilities, and an old card can fall off it.

**NVIDIA Container Toolkit.** To give a container the GPU, the host needs the driver, a container engine and this toolkit. The install page shows adding NVIDIA's package repository, installing the `nvidia-container-toolkit` packages, then `sudo nvidia-ctk runtime configure --runtime=docker`, which "modifies the `/etc/docker/daemon.json` file on the host", and `sudo systemctl restart docker`. It does not say whether the CUDA toolkit is needed on the host; I read nothing that answers that (Not verified). FrankenLLM's README says its `install-docker.sh` installs Docker and the NVIDIA Container Toolkit; its Ollama instances run natively under systemd and Open WebUI runs in Docker, and I read nothing that says Open WebUI needs the GPU.

### ROCm (AMD)

ROCm is "AMD's open-source GPU computing platform" (ROCm home page), "open source, cross-platform (Linux and Windows)". **HIP** is its C++ runtime API and kernel language for AMD GPUs. The HIP docs say developers with CUDA experience "will find the HIP API straightforward" and that "HIP is not intended to be a drop-in replacement for NVIDIA CUDA", so porting takes manual work, with HIPIFY tools to convert CUDA API calls.

**The honest limits.** The ROCm system-requirements page for Linux says: "If a GPU is not listed on this table, it's not officially supported by AMD", and that an unlisted card "might be community-enabled through TheRock nightly builds", which "is not part of the official ROCm release". What the page lists as supported:

| Family | Supported (page read) | Listed as unsupported |
|---|---|---|
| Instinct | MI350 series (gfx950), MI300 series (gfx942), MI200 series (gfx90a), MI100 (gfx908) | MI50 (gfx906), MI25 (gfx900) |
| Radeon PRO | RDNA4 (gfx1201), RDNA3 (gfx1100, gfx1101), RDNA2 (gfx1030) | PRO VII (gfx906) |
| Radeon RX | RX 9000 series (gfx1200, gfx1201), RX 7000 series (gfx1100, gfx1101) | Radeon VII (gfx906) |

Supported distributions are named versions (Ubuntu 24.04.4 and 22.04.5, specific RHEL, SLES and Debian releases, and others), and "Radeon GPUs support only a subset of these distributions". A separate Radeon page for native Linux lists the individual cards (RX 9060 through 9070 XT, RX 7700 through 7900 XTX, several PRO and AI PRO models) for ROCm 7.2.1. In short: the documented route is a listed Radeon model on one of the supported Ubuntu releases; an older card (the page's own examples are MI50 and Radeon VII) is off the official list.

Two contradictions I could not resolve. The ROCm home page showed "AMD ROCm 10.2.0", while the system-requirements page said "For production use, continue to use ROCm 7.14.0 documentation" and the Radeon page covered releases through 7.2.1 and said the docs are being unified starting with ROCm Core SDK 7.13.0. I do not know which version number is right for what you will install, so I state none. llama.cpp's build guide mentions `HSA_OVERRIDE_GFX_VERSION` on Linux for unsupported GPUs, "not supported on Windows". That is a workaround for an unofficial card, not support.

### Intel

This is where I could verify the least: Intel retired or archived two of the tools older guides still recommend, while its current documentation points to PyTorch XPU.

| Piece | What the page I read says |
|---|---|
| **oneAPI and SYCL** | The repository `intel/llvm` is the "oneAPI DPC++ compiler": "an LLVM-based compiler project that implements compiler and runtime support for the SYCL language". SYCL is a C++ model for writing code for different accelerators. I did not read its backends list. |
| **Level Zero** | "oneAPI Level Zero Specification Headers and Loader", MIT license, "part of the larger oneAPI project": the low-level interface to the GPU. I did not read how it relates to SYCL. |
| **PyTorch XPU** | `torch.xpu` is "the API for Intel GPU support", bringing "Intel GPUs and the SYCL software stack into the official PyTorch stack". Hardware listed: Data Center GPU Max Series; Arc A-Series and B-Series; Core Ultra processors with Arc Graphics (Meteor Lake-H, Arrow Lake-H, Lunar Lake, Panther Lake). The data-center OS list is RHEL 9.2, SLES 15 SP5 and Ubuntu Server 22.04; the client list is Windows 11, Ubuntu 24.04 and 26.04, and WSL2. The page gives no driver version and points to Intel's prerequisites guide. |
| **OpenVINO** | "An open-source toolkit" to "convert, optimize, and run inference" on Intel hardware; the home page shows release 2026.4, device sections for CPU, GPU and NPU, and an OpenVINO GenAI package for LLMs. I did not find a license on the page, and I did not read its supported-devices page. |
| **Intel Extension for PyTorch** | A retirement notice: "we have discontinued active development" after release 2.8, features were upstreamed into PyTorch, maintenance runs "until the end of March 2026", and the advice is to use PyTorch directly. |
| **IPEX-LLM** | The repository "was archived by the owner on Jan 28, 2026": "Intel will not provide or guarantee development of or support for this project", patches are not accepted, and "This project has been identified as having known security issues." Its README (Apache-2.0) also warned that mmap-based model loading in llama.cpp "may leak data via side-channels" and suggested `--no-mmap` in shared environments. Guides that tell you to run Ollama or llama.cpp on Intel through IPEX-LLM point at an archived project. |
| **Arc and Gaudi** | Arc GPUs appear in PyTorch XPU, llama.cpp (SYCL, Vulkan, OpenVINO), SGLang and LocalAI. Gaudi appears only as a name: vLLM lists "Intel Gaudi" among third-party hardware plugins and TGI lists Gaudi. I read no Intel Gaudi documentation, so I say nothing about what it supports (Not read). |

What I could not verify for Intel: which of the three llama.cpp routes (SYCL, OpenVINO, Vulkan) is fastest or best supported on a given Arc card, whether Ollama runs on Arc without IPEX-LLM beyond the Vulkan route, whether `--index-url .../whl/xpu` produces a working install today, and anything about Gaudi. The practical reading: PyTorch's own XPU support is the path Intel now points to, and anything built on the archived IPEX-LLM is a risk you accept knowingly.

### Vulkan, the cross-vendor fallback

Vulkan is a graphics and compute API that every major GPU vendor's driver exposes. Because the same code runs on NVIDIA, AMD and Intel GPUs. It is another backend to check when CUDA, ROCm or XPU does not support your card. Ollama enables it "by default when the backend is installed" for GPUs outside the vendor routes, and Intel GPUs on Linux appear on its GPU page only under Vulkan. llama.cpp builds it with `-DGGML_VULKAN=ON` and describes it as "cross-platform GPUs via Vulkan drivers", needing the Vulkan SDK or distro packages. The costs are the ones the pages hint at and I measured none: extra packages to install, a VRAM-reporting permission quirk (`cap_perfmon`), and I read no performance comparison against CUDA or ROCm, so benchmark the available backends on your card.

## Security: the model API has no login

**Ollama.** By default it listens on loopback only (FAQ: "Ollama binds 127.0.0.1 port 11434 by default"), which is the thing protecting it, because the API itself has no authentication for local use: "Cloud requests need an API key. Local requests do not." Set `OLLAMA_HOST=0.0.0.0` and everyone who can reach the port can list your models, run them on your GPU, and load large ones until the card is full. The FAQ's page text carries no warning about that; the warning is this lesson's. The FAQ also says Ollama accepts cross-origin requests from `127.0.0.1` and `0.0.0.0` by default (`OLLAMA_ORIGINS`), which is the setting that decides whether a web page in your browser may talk to your local server. I read no Ollama document on what an attacker could do with a wrong value, so that consequence is general knowledge (**est.**).

**Open WebUI.** The first account is the administrator and sign-up switches itself off afterwards (quick start). Its docs tell you to "read the hardening guide before exposing it beyond your machine"; I could not read that guide (the page I fetched held only a summary, Not read). The quick-start command publishes `-p 3000:8080` with no host address. Docker's rule, as the [SearXNG lesson](Self-Hosting-When-and-Why-with-SearXNG-as-the-Worked-Example.md) recorded on 2026-11-01 and I did not re-read, is that a published port with no host address is open on every host address, and that published-port traffic bypasses host firewall rules such as ufw. Writing the address into the mapping (`-p 127.0.0.1:3000:8080`) is the fix that the SearXNG lesson uses for its own container (**est.** that it applies unchanged here). Pin the image to a version tag, as the Open WebUI docs advise; `:main` and `:latest` move.

**vLLM.** The `--api-key` flag only covers `/v1`, `/v2`, `/inference` and `/cohere` paths: "Many other sensitive endpoints are exposed on the same HTTP server without any authentication enforcement." The security page says: "Do not rely exclusively on `--api-key` for securing access to vLLM." It adds that communication between nodes in a multi-node setup is "insecure by default", that PyTorch's `TCPStore` "by default, listens on all network interfaces", and gives the rule: "Block all incoming connections except to the TCP port the API server is listening on." I found no default host address for the HTTP server on the pages I read, so check with `ss -ltn` after starting it. `--trust-remote-code` is False by default and means what it says: the model's own Python code would run on your machine, so leave it off unless you read the code.

**FrankenLLM, as documented.** Services on all interfaces and no documented authentication or firewall for the Ollama ports (see [above](#frankenllm-as-the-worked-example)). Anyone on a network that can reach the server can use it. Put it behind a private path ([Twingate](Twingate.md), a VPN) or a default-deny firewall.

**Model file formats.** A model is a file you download from the internet and open with a parser.

- **Pickle.** PyTorch's `torch.load` "uses an unpickler under the hood. Never load data from an untrusted source." Pickle can run code when it loads. In the 2.15 docs `weights_only` defaults to `True`, which restricts the unpickler "to loading only tensors, primitive types, dictionaries" and a list you add yourself. Do not switch it off for a file you did not make.
- **Safetensors.** A format designed to hold tensors and no code. I did not read its documentation (Hugging Face is outside the sites I was limited to), so the safety claim is **est.**; Ollama's import page lists Safetensors as a supported format.
- **GGUF.** "A file format for storing models for inference with GGML and executors based on GGML", single file, loadable with `mmap`, "designed to be extensible". I read nothing about its safety properties. A parser bug is a parser bug; treat a downloaded file from an unknown author as untrusted input and keep the server updated.
- **Quantization labels.** `Q4_K_M` on a file name is a claim. It does not prove the file contains what the card says.

**Data into a knowledge base.** FrankenLLM's RAG fetcher pulls public feeds into Open WebUI, and the model will read them as context. Text you did not write that enters a prompt can try to steer the model. That is general knowledge here (**est.**) and the subject of the upcoming AI-security track, which the project tracks as issue 304 and has not written yet.

**Defenses, in order.** Loopback or a private interface for every model API. A default-deny firewall in front of what must listen. Authentication at a reverse proxy for anything that crosses a network, and a private path (Twingate or a VPN) in preference to a public address. Pinned image tags and pinned package versions. Model files only from sources you can name, loaded with `weights_only` left on. Logs that do not store prompts you would not want stored ([what a search proxy should log](Self-Hosting-When-and-Why-with-SearXNG-as-the-Worked-Example.md#what-a-search-proxy-should-and-should-not-log) is the same question). And apply [the CIA triad](The-CIA-Triad-Confidentiality-Integrity-Availability.md): an open model API is a confidentiality problem (your loaded models and prompts), an integrity problem (answers you act on) and an availability problem (someone else fills your GPU).

## Using AI to build your own AI host

An assistant is a fast way to a first draft of a self-hosting plan and a poor way to a trusted one. It writes confidently, and the stack in this lesson is exactly the kind of thing it gets wrong: the version numbers, support lists and flags changed this year, and the pages disagree with each other. This lesson already holds an example. Four Ollama pages give four different context-length defaults, so an answer of "the default is 2048" or "4096" can be quoted from a real page and still be wrong for your install.

**Rules that keep it useful and safe.**

1. **Treat every package name, flag, URL and version as a lead, not a source.** Models invent flags and versions. In the Ollama and llama.cpp pages I read, GPU choice is an environment variable (`CUDA_VISIBLE_DEVICES`, `ROCR_VISIBLE_DEVICES`, `GGML_VK_VISIBLE_DEVICES`, `HIP_VISIBLE_DEVICES` in llama.cpp's guide). I found no `--gpu` flag on them. If an assistant gives you one, that is the pattern to catch: look the flag up on the vendor page, or run `--help`, before it goes into a service file.
2. **Verify against the vendor docs and mark what you checked.** Keep two lists in your notes: verified (with the page and the date) and inferred. The [claims register](#claims-register) at the end of this page is that habit written out.
3. **Never paste secrets.** No tokens, API keys, `.env` files, SSH private keys, license keys, or Open WebUI and Doppler values into a chat. Run `env` or `docker inspect` and your terminal prints them; do not paste that output. Paste the error line, not the dump. See [Secrets from day one](Secrets-From-Day-One.md).
4. **Read what a script does before you run it.** `curl -fsSL https://ollama.com/install.sh | sh` is on the project's own page, and so are a thousand scripts an assistant will hand you in the same shape. Download it to a file, read it, then run it: `curl -fsSL -o install.sh https://ollama.com/install.sh`, read `install.sh`, and only then `sh install.sh`. If the assistant's script touches `sudo`, `systemctl`, `iptables`, `/etc` or a package repository, read those lines twice.
5. **A throwaway VM first.** Run the whole sequence in a virtual machine you will delete ([Virtual machines and hypervisors](Virtual-Machines-Hypervisors-Desktop-and-Datacenter-Options.md)), take a snapshot before each big step, and only then repeat it on the real host. A GPU driver change is the step most likely to need the rollback.
6. **One change at a time.** Install the driver, check `nvidia-smi`. Install the server, check `ss -ltn`. Pull a model, check `ollama ps`. When an assistant gives you twelve steps at once, you cannot tell which broke it.
7. **Ask for the check, not just the command.** "What output means this worked, and what means it failed?" is a better question than "what do I type". Then compare with what your terminal printed.
8. **Do not ask it to bypass a guard.** If a firewall, a package signature or a permission blocks a command, that is a message to read, not an obstacle to route around.
9. **The assistant is not the source for security advice about itself.** Where it matters (binding, authentication, formats), read the vendor's page.

A local model can help with a plan without sending your configuration to a hosted service. It keeps that configuration on your machine; a hosted assistant sends it to the provider under that provider's terms. I read no evidence on how much more often a small model invents flags than a large one, so I will not claim it does (**est.**); the rules above apply to both.

## Try it yourself: a small model in a throwaway VM

Free. **Not run** (see the status banner). It follows the Ollama Linux page, the FAQ, the context-length page and the API pages as read on 2026-11-25. Use a CPU-only virtual machine. A card is not required, which is also why you will see `100% CPU` rather than a GPU split.

**0. A VM.** Make a Linux VM as in [the first-VM exercise](Virtual-Machines-Hypervisors-Desktop-and-Datacenter-Options.md#free-path-a-first-vm-with-qemu-and-a-small-linux-iso). Give it a few gigabytes of memory and enough disk for the install and a model of a few hundred megabytes (**est.**; I read no memory figure for Ollama). Snapshot it.

**1. Read the install script, then run it.**

```bash
curl -fsSL -o install.sh https://ollama.com/install.sh
less install.sh
sh install.sh
```

The one-line form on the Ollama page is `curl -fsSL https://ollama.com/install.sh | sh`. The three-line form does the same and lets you read the script first. The Linux page describes running Ollama as a systemd service named `ollama`. I did not read whether the install script sets that service up, so check it with `systemctl status ollama` (est. for the output).

**2. Check where it listens.**

```bash
ss -ltn | grep 11434
```

You should see `127.0.0.1:11434` and nothing for 11434 on `0.0.0.0` or `[::]`. The FAQ says it binds 127.0.0.1 port 11434 by default. If you see a wildcard address, someone set `OLLAMA_HOST`.

**3. Pull one small model.** The Ollama library lists `qwen2.5:0.5b` at 398 MB.

```bash
ollama pull qwen2.5:0.5b
curl -s http://127.0.0.1:11434/api/tags
```

`/api/tags` lists the models you have. The model name should appear in it.

**4. Call the API.**

```bash
curl -s http://127.0.0.1:11434/api/generate -d '{
  "model": "qwen2.5:0.5b",
  "prompt": "In one sentence, what is VRAM?",
  "stream": false,
  "options": {"num_ctx": 2048}
}'
```

The reply is one JSON object. Without `"stream": false` you get a stream of partial objects (the generate page: default true).

**5. See what is loaded, and at what context.**

```bash
ollama ps
curl -s http://127.0.0.1:11434/api/ps
```

`ollama ps` shows a CONTEXT column and a PROCESSOR column (context-length page). On a VM with no GPU expect `100% CPU` (FAQ). `/api/ps` returns `size`, `size_vram`, `context_length` and `expires_at`. Write down the size and context.

**6. Change the context and watch the memory.**

```bash
curl -s http://127.0.0.1:11434/api/generate -d '{
  "model": "qwen2.5:0.5b",
  "prompt": "In one sentence, what is VRAM?",
  "stream": false,
  "options": {"num_ctx": 32768}
}'
ollama ps
```

The CONTEXT column should now say 32768 and the size should have grown, because the KV cache grew. FrankenLLM's docs say Ollama reloads a model when a request arrives with a different `num_ctx`, so the model reloads on this call (est. for the exact numbers). Compare the size to step 5, and do the [KV arithmetic](#vram-math-weights-kv-cache-and-context-length) with this model's real layer count, KV head count and head dimension from its model card to see whether it matches. The page I read for the library does not list them (est.).

**7. Unload it.** Send the same request with `"keep_alive": 0`; the generate page says `0` unloads the model immediately. Run `ollama ps` again and the list should be empty.

**8. Optional, describe-only: compare against vLLM on CPU.** The vLLM CPU page documents x86 Linux, Python 3.11 to 3.14, pre-built wheels since 0.17.0, a Docker image and the example `vllm serve facebook/opt-125m --dtype=bfloat16`. I did not read the page end to end, I could not confirm a complete working install from it, and the model in that example is a different, much smaller one, so a timing comparison with the step 4 call would not be a fair one. Read the page, then decide whether the comparison is worth a snapshot of your VM. On a CPU with one request at a time, the feature list gives no reason to expect vLLM to win (**est.**).

**9. Undo.** Delete the VM, or follow the Linux page's uninstall: `sudo systemctl stop ollama`, `sudo systemctl disable ollama`, remove the unit file and the binary, then remove the downloaded models and the `ollama` user, group and `/usr/share/ollama`. Check `ss -ltn | grep 11434` shows nothing.

## Build, break, detect, evade, defend

**Build.** The loopback-only server above, with a model pulled and called.

**Break.** In the throwaway VM only, override the service environment with the page's own pattern: `sudo systemctl edit ollama`, add `Environment="OLLAMA_HOST=0.0.0.0:11434"` under `[Service]`, then `sudo systemctl restart ollama`. From the VM host, call the VM's address on port 11434 with `curl http://<VM-ADDRESS>:11434/api/tags` (use your VM's own private address, not one from this page). You get the model list with no password, because the local API does not ask for one. Then ask for a context length far larger than the VM's memory and watch `ollama ps` for the CPU and GPU split, or the failure.

**Detect.** `ss -ltn` shows `0.0.0.0:11434`. `journalctl -e -u ollama` shows who called and what model loaded (est. for the log format). A firewall or connection log shows requests from addresses that are not yours. A GPU that is busy when you are not using it is a sign (`nvidia-smi`).

**Evade, in words only.** Someone who finds an open model port can read which models you host, use your GPU for their own prompts, load large models to fill the memory so your own jobs fail, and test what the model will reveal. This page shows no technique for finding or using one. An exposed Ollama port presents no authentication barrier to a client that can reach it.

**Defend.** Remove the override (`OLLAMA_HOST` unset, back to loopback), or keep a private bind and a default-deny firewall that allows only the clients you name, authentication in a reverse proxy, a private path such as Twingate in front, pinned images, models from known sources, `weights_only` on, and Open WebUI's hardening guide read before it leaves your machine.

**Undo (the whole lab).** Delete the VM and its disk image. Check that no virtual machine process is left running.

## Checkpoint

Without looking back: write the weights formula and the KV cache formula and say which one grows with context; say why a card that fits a model at 8,192 tokens might not at 32,768; name Ollama's default address and port and what that protects; explain how LM Studio differs from Ollama and vLLM, how you would keep its server on loopback, and what you would verify; name the makers of Gemma, Mistral, Qwen, GLM and Llama, then explain why the exact model card and license beat a family-level summary; choose a plausible model size for a stated VRAM budget with the page's formula; explain the difference between the NVIDIA driver, the toolkit and the runtime; say how to tell a ROCm PyTorch build from a CUDA one; name one thing the ROCm page says about unlisted GPUs and one Intel project that is archived; explain why `torch.load` has a `weights_only` option; and give three habits for using an assistant on this kind of project.

## Common mistakes

| Symptom or belief | What is really true | What to check |
|---|---|---|
| "A 7B model needs 7 GB" | It depends on the precision (14 GB at 16-bit, 3.5 GB raw at 4-bit) and the KV cache is extra | The formulas above; `ollama ps` after loading |
| "It fits, so a longer context is free" | The KV cache grows with the context and can push the model to the CPU | The CONTEXT and PROCESSOR columns |
| "The default context is N" | Four pages give four numbers | What your server reports |
| "My docs say the API is secured" | The local Ollama API has no authentication; vLLM's `--api-key` covers only some paths | `ss -ltn`; a test from another machine |
| "I set `OLLAMA_HOST=0.0.0.0` so the web UI could reach it" | Now everyone can. Bind to the interface the UI uses, and firewall it | `ss -ltn` |
| "`docker run -p 3000:8080` is local" | A published port with no host address is open on all addresses (Docker's rule, per the SearXNG lesson) | Write `127.0.0.1:` in the mapping |
| "The CUDA toolkit and the driver are the same thing" | They are separate products with separate versions | `nvidia-smi` shows the driver; the toolkit is its own package |
| "PyTorch found no GPU, so the GPU is broken" | Often the wheel is for another platform | `torch.version.cuda`, `torch.version.hip`, `torch.xpu.is_available()` |
| "My Radeon is not on the list, so it will not work" | Not officially supported; some unlisted cards work with community builds or overrides, with no promise | The ROCm system-requirements page for your release |
| "Any model file is just data" | Pickle files can run code when loaded | `weights_only`; the file's source |
| "The assistant said to use `--gpu 1`" | A lead, not a source | The server's `--help` and its docs |
| "A tutorial said use IPEX-LLM on my Arc card" | The project was archived in January 2026 | The repository's banner; PyTorch XPU, llama.cpp |

## Claims register

Read on 2026-11-25 with read-only requests, through a fetch tool that returns an extract of each page. "Read" means the extract of the page text was read. The FrankenLLM rows cite the public repository's files in a local clone (last commit dated 2026-10-07). "Constructed" means an arithmetic example whose inputs are shown on this page.

| Claim | Source | Status |
|---|---|---|
| Ollama binds 127.0.0.1 port 11434 by default; `OLLAMA_HOST` changes it | [Ollama FAQ](https://docs.ollama.com/faq) | Read |
| Keep-alive default 5 minutes; `OLLAMA_NUM_PARALLEL` other backends default 1; max loaded models 3 x GPUs or 3 on CPU; queue 512 | [Ollama FAQ](https://docs.ollama.com/faq) | Read |
| KV cache type default `f16`, options `f16`, `q8_0`, `q4_0`, global; flash attention env var; `ollama ps` Processor column forms | [Ollama FAQ](https://docs.ollama.com/faq) | Read |
| FAQ context default 4096 tokens | [Ollama FAQ](https://docs.ollama.com/faq) | Read |
| Context default by VRAM: under 24 GiB 4k, 24 to 48 GiB 32k, 48 GiB and up 256k; `ollama ps` CONTEXT column | [Ollama context length](https://docs.ollama.com/context-length) | Read |
| Modelfile instructions list; `num_ctx` described as default 2048; example Modelfile; `ollama create` | [Ollama Modelfile](https://docs.ollama.com/modelfile) | Read |
| Local base URL `http://localhost:11434/api`; cloud needs an API key, local does not | [Ollama API introduction](https://docs.ollama.com/api/introduction) | Read |
| `POST /api/generate` fields, stream default true, `keep_alive` `0` unloads | [Ollama API: generate](https://docs.ollama.com/api/generate) | Read |
| `GET /api/ps` returns size, size_vram, context_length, expires_at; `/api/tags` lists models | [Ollama API: ps](https://docs.ollama.com/api/ps), [tags](https://docs.ollama.com/api/tags) | Read |
| NVIDIA compute capability 5.0+ and driver 550+ (570+ for 5.0 to 6.2); AMD ROCm v7 on Linux; Vulkan enabled by default when installed; Intel only under Vulkan; GPU env vars | [Ollama GPU](https://docs.ollama.com/gpu) | Read |
| Linux install command, manual install, systemd unit, `systemctl edit`, logs, model path, uninstall | [Ollama Linux](https://docs.ollama.com/linux), [FAQ](https://docs.ollama.com/faq) | Read |
| Ollama import supports Safetensors and GGUF; does not quantize GGUF on import | [Ollama import](https://docs.ollama.com/import) | Read |
| Ollama is MIT licensed and names llama.cpp among its backends | [github.com/ollama/ollama](https://github.com/ollama/ollama) | Read |
| LM Studio is a desktop app with a local OpenAI-compatible server and headless or CLI mode | LM Studio documentation | Not read; **est.** |
| LM Studio can bind to loopback, its setting names and defaults, and the `/v1/models` verification path | LM Studio documentation | Not read; **est.** |
| LM Studio downloads from Hugging Face publishers and community quantizers and supports GGUF and MLX | LM Studio documentation | Not read; **est.** |
| LM Studio is aimed at interactive workstation use; comparison with Ollama and vLLM | Inference from product descriptions; no current documentation or benchmark read | Not read; **est.** |
| Gemma maker, size range, license class and common strengths | Google Gemma model cards and license | Not read; **est.** |
| Mistral maker, size range, release-dependent licenses and common strengths | Mistral AI model cards and licenses | Not read; **est.** |
| Qwen maker, size range, release-dependent licenses and common strengths | Qwen model cards and licenses | Not read; **est.** |
| GLM maker, size range, release-dependent licenses and common strengths | GLM model cards and licenses | Not read; **est.** |
| Llama maker, size range, license class and common strengths | Meta Llama model cards and license | Not read; **est.** |
| Suggested parameter ranges for 8, 12 to 16 and 24 GB cards | Estimate from the page's weights and KV-cache formulas; no models loaded | Not read; **est.** |
| `qwen2.5` tags and file sizes (398 MB to 47 GB); no quantization stated | [ollama.com/library/qwen2.5](https://ollama.com/library/qwen2.5) | Read |
| Weights and KV cache arithmetic in the VRAM section | The formulas and invented inputs on this page | Constructed |
| 32 layers, 8 KV heads, head dimension 128 describe a real model | No model card read | **est.** |
| About 130 MB per 1K tokens for an 8B model; 12B plus 8B guard fit at 8192 (about 14.2 GB) and not at 16384 on a 16 GB card | FrankenLLM `docs/CONFIGURATION.md` | Read |
| FrankenLLM: one Ollama instance per GPU on separate ports, systemd services, warmup, health monitor, Open WebUI in Docker, RAG dataset fetcher | FrankenLLM README and `docs/` ([repository](https://github.com/ChiefGyk3D/FrankenLLM)) | Read |
| FrankenLLM services bind to 0.0.0.0; stock service is 127.0.0.1 | FrankenLLM `docs/GETTING_STARTED.md` | Read |
| No authentication, firewall or proxy step for the Ollama ports in FrankenLLM's docs | FrankenLLM README and `docs/` (search for auth, firewall, 0.0.0.0) | Read; absence checked by text search of the README and docs, not by running it |
| FrankenLLM README states Ollama 0.33 and later default to 32768 context | FrankenLLM README | Read |
| FrankenLLM runs Ollama natively and Open WebUI in Docker; install script installs Docker and the NVIDIA Container Toolkit | FrankenLLM README, `docs/QUESTIONS_ANSWERED.md` | Read |
| vLLM: library for LLM inference and serving; PagedAttention; continuous batching, chunked prefill, prefix caching; quantization list; OpenAI-compatible server | [vLLM docs home](https://docs.vllm.ai/en/latest/) | Read |
| vLLM hardware: NVIDIA CUDA, AMD ROCm, Intel XPU, Apple silicon, several CPUs, plugins | [vLLM installation](https://docs.vllm.ai/en/latest/getting_started/installation/) | Read |
| vLLM CPU: Python 3.11 to 3.14, x86 wheels since 0.17.0, Docker images, example serve command | [vLLM CPU](https://docs.vllm.ai/en/latest/getting_started/installation/cpu/) | Read |
| vLLM `--gpu-memory-utilization`, `--port` 8000, `--trust-remote-code` False, `--api-key` limits | [vLLM serve reference](https://docs.vllm.ai/en/latest/cli/serve/) | Read; output was truncated before `--max-num-seqs`, which I did not read |
| vLLM endpoints list | [vLLM online serving](https://docs.vllm.ai/en/latest/serving/online_serving/) | Read |
| vLLM `--api-key` covers only some paths; inter-node traffic insecure by default; TCPStore on all interfaces; firewall advice | [vLLM security](https://docs.vllm.ai/en/latest/usage/security/) | Read |
| vLLM PagedAttention block layout; page is historical | [vLLM PagedAttention design](https://docs.vllm.ai/en/latest/design/paged_attention/) | Read |
| Why paging saves memory (less fragmentation) and when vLLM beats Ollama | My inference from the feature list; no benchmark read | **est.** |
| llama.cpp: MIT, backend list and flags, HIP requires ROCm, `HSA_OVERRIDE_GFX_VERSION`, Vulkan needs the SDK | [llama.cpp README](https://github.com/ggml-org/llama.cpp), [build guide](https://github.com/ggml-org/llama.cpp/blob/master/docs/build.md) | Read |
| GGUF description, single file, mmap, extensible | [GGUF spec](https://github.com/ggml-org/ggml/blob/master/docs/gguf.md) | Read |
| Open WebUI: self-hosted platform, Docker quick start, first account is admin, pin a version tag, hardening guide exists | [Open WebUI docs](https://docs.openwebui.com/), [quick start](https://docs.openwebui.com/getting-started/quick-start/) | Read |
| Open WebUI hardening guide contents | [Open WebUI security](https://docs.openwebui.com/security/) | Not read |
| LocalAI: MIT, OpenAI and Anthropic formats, listed hardware | [github.com/mudler/LocalAI](https://github.com/mudler/LocalAI) | Read |
| SGLang: Apache-2.0, listed hardware | [github.com/sgl-project/sglang](https://github.com/sgl-project/sglang) | Read |
| TGI in maintenance mode; archived 2026-03-21 | [github.com/huggingface/text-generation-inference](https://github.com/huggingface/text-generation-inference) | Read |
| Selector asks build, OS, package, language, compute platform; static text showed 2.7.0 and old CUDA and ROCm versions | [PyTorch get started](https://pytorch.org/get-started/locally/) | Read (static text; stale against the 2.15 docs; current offering Not verified) |
| XPU install command and hardware list; `torch.xpu.is_available()` | [PyTorch XPU](https://docs.pytorch.org/docs/2.15/notes/get_start_xpu.html) | Read |
| HIP reuses `torch.cuda`; check `torch.version.hip` | [PyTorch HIP](https://docs.pytorch.org/docs/2.15/notes/hip.html) | Read |
| `torch.load` unpickler warning; `weights_only` default True | [torch.load](https://docs.pytorch.org/docs/2.15/generated/torch.load.html) | Read |
| NVIDIA driver, toolkit and runtime definitions; compute capability X.Y | [CUDA programming guide](https://docs.nvidia.com/cuda/cuda-programming-guide/01-introduction/cuda-platform.html) | Read |
| Minor version compatibility and forward compatibility | [CUDA compatibility](https://docs.nvidia.com/deploy/cuda-compatibility/) | Read |
| Compute capability of RTX 3090, 4090, 5090 | [developer.nvidia.com/cuda-gpus](https://developer.nvidia.com/cuda-gpus) | Read |
| NVIDIA Container Toolkit install and `nvidia-ctk runtime configure` | [Container Toolkit install guide](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) | Read; the page does not say whether the CUDA toolkit is needed on the host |
| PyTorch wheels bundle the CUDA runtime | General knowledge | **est.** |
| ROCm: open source, Linux and Windows; versions shown disagree across pages | [ROCm home](https://rocm.docs.amd.com/en/latest/), [system requirements](https://rocm.docs.amd.com/projects/install-on-linux/en/latest/reference/system-requirements.html) | Read; current version Not verified <!-- identifier-check: ignore ROCm documentation URL path, not a cloud project id --> |
| ROCm supported and unsupported GPU families; unlisted GPUs not officially supported | [ROCm system requirements (Linux)](https://rocm.docs.amd.com/projects/install-on-linux/en/latest/reference/system-requirements.html) | Read <!-- identifier-check: ignore ROCm documentation URL path, not a cloud project id --> |
| Radeon cards on native Linux for ROCm 7.2.1 | [ROCm Radeon compatibility](https://rocm.docs.amd.com/projects/radeon-ryzen/en/latest/docs/compatibility/compatibilityrad/native_linux/native_linux_compatibility.html) | Read <!-- identifier-check: ignore ROCm documentation URL path, not a cloud project id --> |
| HIP: C++ runtime API and kernel language, not a drop-in CUDA replacement, HIPIFY | [HIP: what is HIP](https://rocm.docs.amd.com/projects/HIP/en/latest/what_is_hip.html) | Read <!-- identifier-check: ignore ROCm documentation URL path, not a cloud project id --> |
| DPC++ implements SYCL | [github.com/intel/llvm](https://github.com/intel/llvm) | Read |
| Level Zero: headers and loader, MIT, part of oneAPI | [github.com/oneapi-src/level-zero](https://github.com/oneapi-src/level-zero) | Read |
| OpenVINO: open-source toolkit, release 2026.4, CPU, GPU and NPU sections, GenAI | [OpenVINO docs](https://docs.openvino.ai/2026/index.html) | Read; license and supported-devices page Not read |
| Intel Extension for PyTorch retired, maintained to end of March 2026 | [IPEX docs](https://intel.github.io/intel-extension-for-pytorch/) | Read |
| IPEX-LLM archived 2026-01-28, no support, known security issues, mmap side-channel note | [github.com/intel/ipex-llm](https://github.com/intel/ipex-llm) | Read |
| Intel Gaudi support in any server | vLLM and TGI list it by name only | Not read |
| Vulkan needs extra packages on most Linux distributions | General knowledge | **est.** |
| Safetensors holds tensors only, no code | General knowledge; the format's own docs not in scope | **est.** |
| Docker publishes a port with no host address on all addresses; published-port traffic bypasses ufw | [Self-hosting lesson, claims register](Self-Hosting-When-and-Why-with-SearXNG-as-the-Worked-Example.md#claims-register) | Repeated from that lesson, not re-read |
| `-p 127.0.0.1:3000:8080` works for Open WebUI | Docker syntax from the SearXNG lesson, applied here | **est.** |
| Output of every command in the exercise | Not run | **est.** |
| Price per token, GPU price, and power cost comparisons | Not read | **est.** |

## Not verified, plainly

- That any command in the exercise works. No Ollama, vLLM or PyTorch was installed, and there is no GPU on the machine this was written on.
- What `ollama ps`, `ss -ltn`, `systemctl status ollama` and the Ollama logs print on your version. The column names come from the pages, the rest is estimated.
- Which context-length default is right for any given Ollama version. Four pages disagree and no version was installed.
- The current stable PyTorch version and the compute platforms its selector offers today.
- Which ROCm version number is current, and whether a particular Radeon card works with a community build.
- Anything about Intel Gaudi, OpenVINO's supported-devices list or license, and whether Ollama runs on an Arc card other than through Vulkan.
- That the CUDA runtime ships inside the PyTorch and Ollama packages. I did not read a page that says so.
- That the NVIDIA Container Toolkit install needs, or does not need, the CUDA toolkit on the host.
- Open WebUI's hardening guide, vLLM's default listening address and the full list of its server flags (the reference page was too long for one read).
- Any benchmark: vLLM against Ollama, Vulkan against CUDA, one quantization against another. I read none and state none.
- Every LM Studio-specific detail on this page, including its current modes, download sources, formats, bind controls, defaults and API behavior.
- The current sizes, licenses and claimed strengths of Gemma, Mistral, Qwen, GLM and Llama. Every family-table entry is estimated until the exact model card and license are read.
- The accuracy of the extract my fetch tool returned for each page. A quotation here is as that extract gave it.
- Anything about FrankenLLM beyond what its README and docs say. I did not run it or read its scripts.
