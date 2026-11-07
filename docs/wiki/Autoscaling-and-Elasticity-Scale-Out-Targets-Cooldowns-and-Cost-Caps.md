# Autoscaling and elasticity: scale out, targets, cooldowns and cost caps

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

> **Status: unverified draft. Two small scripts were run; no cloud account, autoscaler or cluster was touched.** On **2026-11-07** I ran, on one Linux machine with Python 3.13.5 and nothing but the standard library, a toy web service and a load test against `127.0.0.1` (the three runs are quoted in [the free exercise](#free-exercise-a-local-load-test-and-a-scale-decision-by-hand)) and a 60-line decision loop that replays a fixed load trace. **Not run:** an AWS Auto Scaling group, an Azure scale set, a Google managed instance group, a DigitalOcean autoscale pool or App Platform autoscaling, Kubernetes, a load balancer, anything on macOS or Windows. Vendor statements were read on **2026-11-07** from the pages in the [claims register](#claims-register); anything I could not read there is marked **est.** Trust what your terminal prints over what this page says.

> **Prerequisites.** [Containers and Docker basics](Containers-and-Docker-Basics.md), especially [the state section](Containers-and-Docker-Basics.md#state-the-thing-that-makes-containers-hard), and [How money works in the cloud](How-Money-Works-in-the-Cloud.md). A terminal and Python 3 for the exercise ([The terminal and your first script](Terminal-and-Your-First-Script.md)). You do not need a cloud account. About 75 minutes for the reading and the exercise (est.).

> **Where this runs, and the rule.** The exercise is local and costs nothing: a server on `127.0.0.1`, a client on the same machine, and a script that only prints. No cloud resource is created anywhere on this page. If you later try a real autoscaler in your own account, set the billing alert and the maximum size first (see [the guard rails](#cost-guard-rails-unbounded-scaling-is-a-billing-risk)).

<!-- BEGIN GENERATED PAGE NAV top: rewritten from docs/wiki/_nav.yaml by scripts/gen_wiki_nav.py; edit the manifest, not this block -->
[Home](Home.md) > [Track 1: Foundations](Contents.md#track-1-foundations) > Autoscaling and elasticity

Previous: [WordPress at scale: CDN, WAF, caching and CI](WordPress-at-Scale-CDN-WAF-and-CI.md)
<!-- END GENERATED PAGE NAV top -->

<!-- BEGIN GENERATED PAGE CONTENTS: rewritten from the page's own headings by scripts/gen_wiki_nav.py; edit the headings, not this block -->
**On this page:**

- [What you will be able to do](#what-you-will-be-able-to-do)
- [Scalable and elastic are different words](#scalable-and-elastic-are-different-words)
- [Horizontal and vertical](#horizontal-and-vertical)
- [Metrics and policies](#metrics-and-policies)
- [Cooldowns, warmup and flapping](#cooldowns-warmup-and-flapping)
- [Why stateless matters](#why-stateless-matters)
- [Health checks and the load balancer](#health-checks-and-the-load-balancer)
- [Scale to zero](#scale-to-zero)
- [Kubernetes: the Horizontal Pod Autoscaler](#kubernetes-the-horizontal-pod-autoscaler)
- [Autoscaling groups and their managed equivalents](#autoscaling-groups-and-their-managed-equivalents)
- [Cost guard rails: unbounded scaling is a billing risk](#cost-guard-rails-unbounded-scaling-is-a-billing-risk)
- [What this project does](#what-this-project-does)
- [Free exercise: a local load test and a scale decision by hand](#free-exercise-a-local-load-test-and-a-scale-decision-by-hand)
- [Checkpoint](#checkpoint)
- [Common mistakes](#common-mistakes)
- [Claims register](#claims-register)
<!-- END GENERATED PAGE CONTENTS -->

## What you will be able to do

- Say the difference between horizontal and vertical scaling, and between scalable and elastic.
- Read a scaling policy: a metric, a target, a minimum, a maximum, and what the cooldown is for.
- Tell target tracking, step scaling and scheduled scaling apart and say when each fits.
- Explain flapping and name the two usual fixes.
- Say why a server that keeps its own state cannot be scaled out safely, and what the health check does for a load balancer.
- Name the autoscaling product on AWS, Azure, Google Cloud, DigitalOcean and Kubernetes.
- Do the Kubernetes replica arithmetic by hand.
- Explain why a missing maximum is a billing risk and where this project's cost gate stands on it.

## Scalable and elastic are different words

A system is **scalable** if you can make it handle more load by adding capacity. A system is **elastic** if it does that for you, in both directions, without a person: it grows when load arrives and shrinks when load leaves, and you pay for what is running. The second half is the part people forget. Autoscaling that only ever goes up is a bill, not elasticity.

The thing that does it is an **autoscaler**: a loop that reads a number (CPU, requests per second, queue length), compares it with a target, and changes how many copies of something are running. Everything else on this page is a detail of that loop.

## Horizontal and vertical

**Horizontal scaling** (scale out and in) changes the number of copies. **Vertical scaling** (scale up and down) changes the size of one copy: more memory, a faster CPU.

| Question | Horizontal | Vertical |
|---|---|---|
| What changes | The count of instances | The size of an instance |
| Needs the program to cooperate | Yes: copies must be interchangeable (see [state](#why-stateless-matters)) | Usually no |
| Limit | How many you are allowed and can pay for | The biggest machine that exists |
| Interruption | None if a load balancer sits in front | Often a restart |
| Failure | Lose one copy of many | Lose the only one |

The vendors say the same thing. Azure's autoscale page says it scales horizontally only, "Autoscale does not support vertical scaling", that vertical scaling "is limited by the availability of larger hardware" and "might also require a restart of the VM". DigitalOcean's App Platform page says it "only offers fixed vertical scaling": you resize a container by hand. Kubernetes describes horizontal scaling as "deploy more Pods" and vertical as giving the existing Pods more CPU or memory. (All three read 2026-11-07.)

That is why almost every autoscaler on this page is horizontal. Vertical is still the right first move for a single small server that is simply too small, and it is the only move for a database that cannot run as interchangeable copies. Plenty of production systems do both: a database scaled up, the web tier scaled out.

## Metrics and policies

An autoscaling setup has four numbers and one rule:

- **Minimum**: never fewer than this many copies.
- **Maximum**: never more than this many.
- **Desired** (or current): how many there are now.
- **Metric and target**: what to watch and what value to hold it near.
- **Policy**: the rule that turns the metric into a change in the desired number.

AWS describes the shape directly: the group "adjusts the desired capacity of the group, between the minimum and maximum capacity values that you specify" (Amazon EC2 Auto Scaling User Guide, read 2026-11-07). Azure's rules likewise carry "a minimum level of resources" and "a maximum level of resources that won't be exceeded".

### Target tracking

You pick a metric and a value, and the autoscaler does the arithmetic. AWS's example is a policy that targets an average CPU utilization of 50 percent: the group scales out when CPU is above 50 percent and scales in when it is below, "to optimize costs during periods of low utilization". You do not say how many instances to add; the service works that out. AWS recommends target tracking over the other two dynamic types when the metric moves in proportion to the number of instances. Kubernetes' Horizontal Pod Autoscaler is this style by design (formula below).

Pick a metric that moves **inversely** with the number of copies. CPU per instance falls when you add instances. A metric that does not fall (total requests per second, which is the same however many servers there are) makes a poor target unless it is divided by the count.

### Step scaling

You define bands: if the metric is between 70 and 80 percent add one, between 80 and 90 add three, above 90 add five. AWS builds step scaling on CloudWatch alarms and lets you define separate policies for scaling out and in. Use it when the right response is not proportional, or when you want a hard response to a big breach.

### Scheduled scaling

You scale by the clock: "at 08:00 set the minimum to 6; at 20:00 set it back to 2". AWS lists it as its own scaling method, with recurring schedules and a time zone setting. Use it when the load is a known shape (an office-hours internal tool, a weekly event) because it needs no warning from a metric. It also covers the case where a metric reacts too late: a machine that takes five minutes to start (est.) cannot be started when the traffic is already there. Azure also offers predictive autoscale for cyclical patterns on scale sets, which is beyond this page.

In practice you combine them: a schedule for the known shape, target tracking for the surprises, and a minimum and maximum around both.

## Cooldowns, warmup and flapping

Scaling is slow compared with a metric. A new copy takes time to start, pass its first health check and begin taking traffic. During that time the metric still looks bad. A naive autoscaler sees "still too high", adds more, and overshoots. Then the extra copies come online, the metric collapses, and it removes them. Then the load comes back. This is **flapping** (also called thrashing): the count bounces around the right answer.

Kubernetes' own page names it: when you manage replicas with the Horizontal Pod Autoscaler, "the number of replicas keeps fluctuating frequently due to the dynamic nature of the metrics evaluated. This is sometimes referred to as thrashing, or flapping." (read 2026-11-07).

The fixes, with the vendors' names:

- **Cooldown.** After a change, wait before the next one. DigitalOcean's droplet autoscale pool has `cooldown_minutes`, "the number of minutes to wait between scaling events", default 10 (API reference generated 6 Nov 2026). Google calls the related setting the **initialization period** and says it was "formerly known as cool down period". AWS has a cooldown for simple scaling policies, with a warning above it: "As a best practice, we recommend that you do not use simple scaling policies and scaling cooldowns. A target tracking scaling policy or a step scaling policy is better."
- **Warmup.** Do not count a new copy's numbers until it has started up. AWS says target tracking and step scaling "can initiate a scale-out activity immediately without waiting for the cooldown period to end" and use an instance warmup instead, and that while a scale-out is in progress, scale-in is blocked until the new instances finish warming up.
- **Stabilization window.** Scale out quickly, scale in slowly. Kubernetes defaults to a 300-second stabilization window for scaling down and none for scaling up: "When the metrics indicate that the target should be scaled up the target is scaled up immediately". It scales down only to the highest desired count seen in the window.
- **Tolerance.** Do nothing when the number is close enough. Kubernetes skips any change "if the ratio is sufficiently close to 1.0 (within a configurable tolerance, 0.1 by default)".

The exercise below shows flapping on a fixed trace, and then removes it with a window.

## Why stateless matters

If every copy is interchangeable, any copy can answer any request, and you can add or remove copies freely. If copy A holds something copy B does not (a user's login session in memory, an uploaded file on its local disk, a counter), then removing A loses data and adding B gives a user a different answer on the next click. A server that works this way is **stateful**. A **stateless** server keeps nothing it cannot lose: state lives somewhere shared, such as a database, a cache or an object storage bucket, and the web tier only does work.

[Containers and Docker basics: state](Containers-and-Docker-Basics.md#state-the-thing-that-makes-containers-hard) made the same point for a different reason: you want to be able to throw the machine away and rebuild it. Autoscaling makes that a routine event instead of an emergency, because the autoscaler throws machines away on purpose, on its own schedule, at 03:00. Concretely:

- Sessions go in a shared store (or in a signed token the client holds), not in the process.
- Uploads go to object storage, not the local disk.
- Logs go to standard output or a collector, not a file on a machine that will disappear.
- Startup must be fast and need no human step, or new copies join too late to help.
- A copy being shut down should finish its current request and exit. AWS notes that Elastic Load Balancing waits 300 seconds by default for deregistration (connection draining) before a terminating instance goes away.

Some things do not become stateless: the database itself, a single-leader queue, a game server holding a live match. They scale by other means (bigger machine, read replicas, partitioning) and are out of scope here.

## Health checks and the load balancer

A **load balancer** spreads requests across the copies. To do that safely it needs to know which copies are fit to receive them. It sends each one a small request on a schedule (a **health check**), and stops sending traffic to a copy that fails. DigitalOcean's load balancers "only send requests to Droplets that pass health checks", you define the check endpoint and what counts as a healthy response, and a failing droplet is removed from rotation and added back when it passes again (read 2026-11-07).

Two things to know:

1. **The health check is a different job from the scaling metric.** The metric asks "do we need more or fewer copies?" The health check asks "is this copy broken?" A group can use both: AWS notes an Auto Scaling group can take health notifications from EC2 status checks, Elastic Load Balancing, VPC Lattice, EBS and "custom health checks that you define", and when it decides an in-service instance is unhealthy, "it replaces it with a new instance to maintain the desired capacity". It does not wait for a scaling cooldown to do that.
2. **A shallow check lies.** [Containers and Docker basics](Containers-and-Docker-Basics.md#pi-shaped-to-cloud-shaped) makes the same point about "the process exists". A check that only confirms the web server answers will report healthy when the database behind it is down, and the autoscaler will then replace perfectly good machines or, worse, keep serving errors. Check what a real request needs, but not so deep that one slow dependency makes every copy fail at once and the whole pool is taken out of rotation.

A health check also starts the clock for a new copy. Give it a **grace period** (AWS has a setting for exactly this) so a copy that is still starting is not killed for failing a check it was never ready to pass.

## Scale to zero

If the minimum is zero, nothing runs when nobody asks, and nothing is billed for running (est., depends on the product). The cost is the first request after a quiet period, which waits while a copy starts: a **cold start**. Examples, each from its own vendor page:

- **Google Cloud Run** removes instances that are not processing requests; a minimum-instances setting keeps some warm "even if they're not processing requests" to cut that wait.
- **AWS Lambda** runs a function per request and scales the number of execution environments on its own, up to your account's concurrency limit. The default is 1,000 concurrent executions per Region, and you can ask for more.
- **Kubernetes** can set `minReplicas: 0`, but only for metrics that can be read when nothing is running. The documentation says it is supported "only for object and external metrics", not CPU or memory, "because those can only be measured on running Pods". The page I read marks the feature Beta since Kubernetes v1.37 and on by default. I did not check how this reads on older versions, so check yours.
- **A Google managed instance group** can scale to zero only if you do not use CPU utilization, load balancer serving capacity or per-instance monitoring metrics, and set `minNumReplicas` to 0.
- **DigitalOcean App Platform** has Scale to Zero for web services. The page says "To request access, contact Support", and that a scaled-to-zero component is billed at 10 percent of the standard price. That page is marked private, so ask before you plan around it.

Scale to zero fits a hobby web service nobody visits at night, and a worker that wakes for a queue. It fits badly where a cold start of seconds breaks something, and where a connection must stay open (the same line [serverless in the Containers lesson](Containers-and-Docker-Basics.md#serverless-the-container-you-do-not-run) draws).

## Kubernetes: the Horizontal Pod Autoscaler

Kubernetes keeps a count of Pods (copies of a container) for a Deployment. The **HorizontalPodAutoscaler** (HPA) changes that count. Its core is one line of arithmetic from the Kubernetes documentation:

```text
desiredReplicas = ceil[ currentReplicas * ( currentMetricValue / desiredMetricValue ) ]
```

If the current value is 200m and the target is 100m, the replicas double. If it is 50m against 100m, they halve. The controller runs this on a loop, every 15 seconds by default (`--horizontal-pod-autoscaler-sync-period`), skips the change inside the 0.1 tolerance, and applies the stabilization behavior from the previous section. You set the minimum and the maximum, the metric and the target. That is target tracking, with the formula visible.

Two practical points. The HPA changes how many **Pods** run; it does not add machines. If the cluster has no room, new Pods wait. A separate component scales the machines: DigitalOcean's Kubernetes product has a cluster autoscaler per node pool with a minimum and a maximum node count (page last verified 29 Oct 2026), and it states that it scales nodes only, which is the same split. And the HPA reads metrics through the metrics API, which needs something installed to answer it; a CPU target does nothing if no metrics server is running (est.).

## Autoscaling groups and their managed equivalents

The AWS word is the **Auto Scaling group**: EC2 instances treated as one logical group, held to a minimum, maximum and desired capacity, and replaced when unhealthy. The other providers have the same idea under other names.

| Provider | Group of machines | Platform (containers or apps) | Source read 2026-11-07 |
|---|---|---|---|
| AWS | Amazon EC2 Auto Scaling group: target tracking, step, simple and scheduled policies | Lambda scales on its own (concurrency limit); other AWS container products are not covered here | EC2 Auto Scaling User Guide; Lambda Developer Guide |
| Azure | Virtual Machine Scale Sets, scaled by Azure Monitor autoscale rules on metrics or a schedule | Autoscale supports many resource types, listed on a separate page that I did not read | Azure Monitor autoscale overview; scale sets overview |
| Google Cloud | Managed instance group with an autoscaler (policies on CPU, load balancing capacity, monitoring metrics or schedules) | Cloud Run scales instances on requests, minimum and maximum instances settable | Compute Engine autoscaler page; Cloud Run min instances |
| DigitalOcean | Droplet autoscale pool: minimum, maximum, a CPU and/or memory target, a cooldown, or a fixed count | App Platform: manual, CPU-based or request-based autoscaling, 1 to 250 instances; DOKS: node pool cluster autoscaler | Droplet autoscale pools API reference; App Platform scaling page; DOKS autoscaling page |
| Kubernetes (any host) | Cluster autoscaler for nodes (provider-specific) | HorizontalPodAutoscaler for Pods | Kubernetes documentation |

Notes on the DigitalOcean row, since this project uses that provider. The autoscale pool is documented in the API reference (generated 6 Nov 2026); I did not find a how-to page for it. App Platform's CPU-based autoscaling needs a dedicated CPU plan, and request-based autoscaling is capped at a `max_instance_count` of 100, against 250 for the CPU-based kind. App Platform's `min_instance_count` must be 1 or higher; going to zero is the separate Scale to Zero feature.

## Cost guard rails: unbounded scaling is a billing risk

An autoscaler spends money on your behalf, automatically, in response to a number. That is the point and it is also the risk. A traffic spike you wanted becomes a bill, and a traffic spike you did not want (a crawler, an attack, a retry loop in your own code) becomes a bill too, with no one awake. [How money works in the cloud](How-Money-Works-in-the-Cloud.md#how-bills-get-out-of-hand) lists the ways bills grow; autoscaling adds a new one, because the machines are created without a person clicking anything.

The guard rails, in the order they act:

1. **A maximum, always.** Every setup above has one, and a missing one is an unlimited credit card. Choose it from a budget, not from a hope: maximum copies times the hourly price times 730 hours (est., the usual hours in a month) is the worst month you are agreeing to. DigitalOcean's pool requires `max_instances`; App Platform's autoscaling requires `max_instance_count`; AWS and Azure take a maximum on the group. The Lambda concurrency limit is a cap too, set by the provider and adjustable by you.
2. **A budget alert.** [Step 1 of the defenses](How-Money-Works-in-the-Cloud.md#1-a-billing-alert-before-anything-else). An alert will not stop spending, but it makes a runaway visible the same day. The project set two in stage 0, at $10 and $25.
3. **A ceiling that is code.** Here the cost gate reads the price of everything the code would create and fails the build over the phase's ceiling ([CI, tests and the cost gate](CI-Tests-and-Cost-Gate.md#the-cost-gate)). Its resource-type list is an allowlist, so an autoscaling resource it does not know is refused by name until someone prices and approves it. The gate cannot see what an autoscaler decides later, so any scaling resource would have to be priced at its **maximum**, which is exactly why the maximum has to exist. I did not test how the gate would price one. [What the gate cannot do](CI-Tests-and-Cost-Gate.md#what-the-gate-cannot-do) lists the other blind spots, such as bandwidth overage.
4. **Autoscale on a metric an attacker cannot cheaply push.** CPU rises when anyone sends requests. Put [rate limiting](Rate-Limiting-at-Every-Layer.md) in front, so scaling out answers real users and not a flood.
5. **Alert on "at the maximum for an hour".** A group pinned at its maximum is either a success or an attack. Either way a person should look.

## What this project does

Nothing here autoscales. Stage 3 is one droplet running Docker, Portainer, the five daemons and a Spaces bucket, at $29 a month in the Roadmap's current figure, against a $30 ceiling, and at the time of writing it is planned, not built ([Roadmap: stage 3](Roadmap.md#stage-3-workloads-planned)). One droplet is a fixed size with a fixed price, and that is a deliberate property: the cost gate can prove the bill because there is no number that moves. A second droplet, a load balancer or an autoscale pool would each be a new line in the manifest and a reviewed raise of the ceiling.

What the stage 3 design does take from this lesson is the part that does not need a scaler: state in a bucket instead of on the disk, a disposable machine, a health check that means something, and a run-once mode for the daemons that fit a function. Those are what you would need if you ever scaled it out. For the five daemons, the honest answer to "do they need autoscaling" is no: they are bots with a trickle of traffic (est.), and the failure to plan for is a stuck loop, not a crowd. Autoscaling here is a lesson, not a plan.

## Free exercise: a local load test and a scale decision by hand

No account, no cloud, no money. You need Python 3 (I ran 3.13.5 on Linux) and a terminal. The first script is a toy web service on `127.0.0.1` with a fixed number of "workers"; the second hammers it from the same machine; the third replays a load trace through a scale decision. About 30 minutes (est.).

### 1. A toy service with a fixed capacity

Save as `toy.py`. It holds a worker slot for 50 milliseconds per request, so one slot handles about 20 requests a second. The number of slots comes from the command line.

```python
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

WORKERS = int(sys.argv[1])
slots = threading.Semaphore(WORKERS)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        with slots:
            time.sleep(0.05)
        self.send_response(200)
        self.send_header("Content-Length", "2")
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *args):
        pass


ThreadingHTTPServer(("127.0.0.1", 8099), Handler).serve_forever()
```

### 2. A load test

Save as `load.py`. It starts N client threads that send requests back to back for 3 seconds and prints throughput and latency.

```python
import sys
import threading
import time
import urllib.request

CLIENTS = int(sys.argv[1])
SECONDS = 3
lat = []
lock = threading.Lock()
stop = time.time() + SECONDS


def run():
    mine = []
    while time.time() < stop:
        t = time.time()
        urllib.request.urlopen("http://127.0.0.1:8099/").read()
        mine.append(time.time() - t)
    with lock:
        lat.extend(mine)


threads = [threading.Thread(target=run) for _ in range(CLIENTS)]
for t in threads:
    t.start()
for t in threads:
    t.join()
lat.sort()
print(f"clients={CLIENTS} requests={len(lat)} per_second={len(lat) / SECONDS:.0f} "
      f"p50_ms={lat[len(lat) // 2] * 1000:.0f} p95_ms={lat[int(len(lat) * 0.95)] * 1000:.0f}")
```

Run it in two terminals, once per worker count. Terminal 1: `python3 -I toy.py 1`. Terminal 2: `python3 -I load.py 8`. Stop the server with Ctrl-C, then repeat with `2` and `4`.

What I saw on 2026-11-07, one run each (yours will differ by a few percent):

| Workers | Requests in 3 s | Requests per second | Median latency | 95th percentile |
|---|---|---|---|---|
| 1 | 67 | 22 | 402 ms | 404 ms |
| 2 | 126 | 42 | 201 ms | 223 ms |
| 4 | 244 | 81 | 100 ms | 149 ms |

Eight clients are always waiting. With one worker each request queues behind seven others, about 8 x 50 ms = 400 ms. Doubling the workers about halves the latency and doubles the throughput. That is horizontal scaling, and it is also why "latency" is a metric an autoscaler can watch: it falls as you add copies.

### 3. The scale decision, by hand and by script

Take the numbers from step 2: one worker is about 20 requests a second. Set a target of 70 percent utilization, so there is headroom. Suppose 90 requests a second arrive and you have 2 workers (capacity 40):

- utilization = 90 / 40 = 2.25
- ratio = 2.25 / 0.70 = 3.21
- desired = ceil(2 x 3.21) = ceil(6.43) = **7**

Check yourself with 6 workers and the same 90 requests: 90 / 120 = 0.75, ratio 1.07, inside the 0.10 tolerance, so no change. Now set a maximum of 6 and the 7 becomes 6. That is the cap doing its job.

Save as `scaler.py`. It replays one load value per 15-second tick, makes this decision at every tick, and runs the same trace twice: with no stabilization window and with a window of 4 ticks (one minute) on scale-down.

```python
import math

PER_WORKER = 20      # requests/s one worker handles (measured above)
TARGET = 0.70        # keep average utilization near 70 percent
TOLERANCE = 0.10     # skip the change if the ratio is within 10 percent of 1.0
MIN_W, MAX_W = 1, 6  # the cap: never above 6, however high the load goes
LOAD = [20, 20, 90, 90, 90, 90, 40, 90, 40, 90, 40, 40, 40, 40, 40, 40, 40]  # requests/s, one value per 15 s tick


def run(window):
    workers, history = 2, []
    print(f"stabilization window = {window} ticks, cap = {MAX_W}")
    print("tick  load  workers  util   desired  action")
    changes = 0
    for tick, load in enumerate(LOAD):
        util = load / (workers * PER_WORKER)
        ratio = util / TARGET
        raw = math.ceil(workers * ratio)
        history.append(raw)
        # scale down only to the highest desired value seen in the window
        desired = max(history[-(window + 1):]) if raw < workers else raw
        desired = max(MIN_W, min(MAX_W, desired))
        if abs(ratio - 1.0) <= TOLERANCE:
            desired = workers
        action = "-" if desired == workers else f"{workers} -> {desired}"
        print(f"{tick:>4}  {load:>4}  {workers:>7}  {util:>4.2f}  {desired:>7}  {action}")
        if desired != workers:
            changes += 1
        workers = desired
    print(f"scale changes: {changes}\n")


for w in (0, 4):
    run(w)
```

Run `python3 -I scaler.py`. What it printed on 2026-11-07, trimmed to the lines that matter:

```text
stabilization window = 0 ticks, cap = 6
   2    90        2  2.25        6  2 -> 6
   6    40        6  0.33        3  6 -> 3
   7    90        3  1.50        6  3 -> 6
   8    40        6  0.33        3  6 -> 3
   9    90        3  1.50        6  3 -> 6
  10    40        6  0.33        3  6 -> 3
scale changes: 6

stabilization window = 4 ticks, cap = 6
   2    90        2  2.25        6  2 -> 6
  14    40        6  0.33        3  6 -> 3
scale changes: 2
```

(The full output also lists the ticks where nothing changed; run the script to see them. Tick 2 asks for 7 and the cap makes it 6.)

With no window the service changes size six times in 17 ticks, bouncing between 3 and 6 as the load alternates 40 and 90: that is flapping. With a one-minute window it grows once and shrinks once, after the load has stayed low for the whole window. The price of the window is visible too: the service held 6 workers for eight ticks it did not strictly need (ticks 6 to 13, where the load was 40 or 90 and utilization was 0.33 or 0.75), which is the cost of not flapping. Change `window`, `TARGET` and `MAX_W` and see what the cap and the window each buy you.

This is a toy. It has no start-up delay, no warmup, no health check and a perfectly accurate metric. A real autoscaler also has to guess when the metric lags the truth, which is where the vendors' cooldown and warmup settings come from.

### 4. Clean up

Stop the toy server (Ctrl-C). Nothing was installed and nothing was written beyond the three files you saved; delete them when done.

## Checkpoint

Without looking back: give one reason the web tier scales out more easily than the database; say what target tracking, step scaling and scheduled scaling each do; explain flapping and name two fixes; do the HPA arithmetic for 4 replicas at 150 percent of the target; say what a health check is for and why a shallow one is dangerous; explain why a missing maximum is a billing risk; say whether stage 3 autoscales and why that is a feature.

## Common mistakes

| Symptom or belief | What is really true | What to check |
|---|---|---|
| "Autoscaling makes it cheaper" | It makes it follow the load. A busy service scales to a bigger bill | The maximum and the budget alert |
| "No maximum, so it can never run out of capacity" | Also no ceiling on the bill, and the dependencies behind it (a database) still have a fixed size | A maximum from the budget, and what the database can take |
| Scaling on a metric that does not fall when you add copies | The scaler adds copies forever up to the maximum | Pick per-instance CPU or latency, not total requests |
| "The health check passes, so it is fine" | It proves the check passes | What the check actually exercises |
| Sessions or uploads kept on the instance | The next scale-in deletes them | Shared store and object storage |
| "Scale in as fast as scale out" | The load often comes straight back | A longer window for scale-in |
| "Our cooldown is long enough" with start-up slower than the cooldown | New copies are not ready when the next decision is made | Warmup and start-up time |
| "I have one droplet, so I have autoscaling if I resize it" | Resizing one droplet by hand is manual vertical scaling | An autoscale pool or group is a separate resource with its own cost |

## Claims register

| Claim | Source | Status |
|---|---|---|
| HPA formula, 15-second sync period, 0.1 tolerance, 300 s default scale-down window, no scale-up window, "thrashing, or flapping", horizontal versus vertical wording, `minReplicas: 0` for object and external metrics only, Beta since v1.37 and on by default | [Kubernetes: Horizontal Pod Autoscaling](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/) | Read 2026-11-07 |
| Auto Scaling group definition, min/max/desired, replace unhealthy instances, health sources, scheduled scaling | [EC2 Auto Scaling groups](https://docs.aws.amazon.com/autoscaling/ec2/userguide/auto-scaling-groups.html), [health checks](https://docs.aws.amazon.com/autoscaling/ec2/userguide/ec2-auto-scaling-health-checks.html), [scheduled scaling](https://docs.aws.amazon.com/autoscaling/ec2/userguide/ec2-auto-scaling-scheduled-scaling.html) | Read 2026-11-07 |
| Target tracking at 50 percent CPU; step scaling on CloudWatch alarms | [Target tracking](https://docs.aws.amazon.com/autoscaling/ec2/userguide/as-scaling-target-tracking.html), [step and simple scaling](https://docs.aws.amazon.com/autoscaling/ec2/userguide/as-scaling-simple-step.html) | Read 2026-11-07 |
| Cooldown applies to simple scaling, AWS recommends against simple scaling, warmup for target tracking and step, scale-in blocked during warmup, 300 s deregistration | [Scaling cooldowns](https://docs.aws.amazon.com/autoscaling/ec2/userguide/ec2-auto-scaling-scaling-cooldowns.html) | Read 2026-11-07 |
| Lambda default 1,000 concurrent executions per Region | [Lambda concurrency](https://docs.aws.amazon.com/lambda/latest/dg/lambda-concurrency.html) | Read 2026-11-07 |
| Azure autoscale is horizontal only, min and max in rules, 70/40 percent example, predictive autoscale for scale sets; Virtual Machine Scale Sets grow and shrink on demand or schedule | [Azure Monitor autoscale overview](https://learn.microsoft.com/en-us/azure/azure-monitor/autoscale/autoscale-overview), [Virtual Machine Scale Sets overview](https://learn.microsoft.com/en-us/azure/virtual-machine-scale-sets/overview) | Read 2026-11-07 |
| Google MIG autoscaler, initialization period "formerly known as cool down period", which metrics block scale to zero | [Autoscaling groups of instances](https://cloud.google.com/compute/docs/autoscaler) | Read 2026-11-07 |
| Cloud Run removes idle instances; minimum instances keep some warm | [Cloud Run minimum instances](https://cloud.google.com/run/docs/configuring/min-instances) | Read 2026-11-07 |
| Droplet autoscale pool: min, max, CPU and memory targets, `cooldown_minutes` default 10 | [DigitalOcean API reference: Droplet Autoscale Pools](https://docs.digitalocean.com/reference/api/reference/droplet-autoscale-pools/) | Read 2026-11-07 (page generated 6 Nov 2026) |
| App Platform: manual, CPU-based and request-based autoscaling, `instance_count` 1 to 250, request-based `max_instance_count` 100, CPU-based needs a dedicated CPU plan, fixed vertical scaling only | [App Platform: scale apps](https://docs.digitalocean.com/products/app-platform/how-to/scale-app/) | Read 2026-11-07 |
| Scale to Zero on App Platform: web services only, by request, billed at 10 percent when at zero | [App Platform: scale to zero](https://docs.digitalocean.com/products/app-platform/how-to/scale-to-zero/) | Read 2026-11-07 (page "last verified 13 Jul 2026", marked private) |
| DOKS cluster autoscaler: node pools, minimum and maximum nodes, scales nodes only | [DOKS: enable cluster autoscaler](https://docs.digitalocean.com/products/kubernetes/how-to/autoscale/) | Read 2026-11-07 (page "last verified 29 Oct 2026") |
| DigitalOcean load balancers remove failing droplets and re-add them | [Load balancer features](https://docs.digitalocean.com/products/networking/load-balancers/details/features/) | Read 2026-11-07 |
| Cost gate allowlist, ceiling per phase, blind spots; stage 3 estimate and status | [CI, tests and the cost gate](CI-Tests-and-Cost-Gate.md), [Roadmap](Roadmap.md) | Read in this repo 2026-11-07 |
| Load test table, the 7 and 6 decisions, 6 and 2 scale changes | One run each on Linux with Python 3.13.5, 2026-11-07 | Observed; yours differ |
| Cold start lag, typical VM start time of minutes, 730 hours in a month, metrics server needed for CPU targets, scale to zero meaning no running cost (varies), the 75-minute and 30-minute estimates | General knowledge | **est.** |

Not verified, plainly: any real autoscaler, group, pool or cluster; the Azure list of resources autoscale supports; AWS predictive scaling details; how any of the pages above read before 2026-11-07 or after; whether Scale to Zero is open to your account; the cost of any of it.

Next: [How money works in the cloud](How-Money-Works-in-the-Cloud.md), then continue on the [Reading order](Reading-Order.md) page.

<!-- BEGIN GENERATED PAGE NAV bottom: rewritten from docs/wiki/_nav.yaml by scripts/gen_wiki_nav.py; edit the manifest, not this block -->
Where you are: [Home](Home.md) > [Track 1: Foundations](Contents.md#track-1-foundations) > Autoscaling and elasticity

Previous: [WordPress at scale: CDN, WAF, caching and CI](WordPress-at-Scale-CDN-WAF-and-CI.md)

In this track: [Track 1: Foundations](Contents.md#track-1-foundations), 37 pages

- OS and Linux, git and the terminal: [Git from zero](Git-From-Zero.md) / [The terminal and your first script](Terminal-and-Your-First-Script.md) / [Linux for enterprise beginners](Linux-for-Enterprise-Beginners.md) / [First hour on a new system](First-Hour-on-a-New-System-Updates-and-Baseline.md) / [Patch management and automatic security updates](Patch-Management-and-Automatic-Security-Updates.md) / [Red and blue, and choosing your lab OS](Red-and-Blue-Yin-and-Yang-and-Your-Lab-OS.md) / [Virtual machines and hypervisors: desktop to datacenter](Virtual-Machines-Hypervisors-Desktop-and-Datacenter-Options.md) / [Device firmware security: Intel ME, AMD PSP, MINIX and kernel design](Device-Firmware-Security-Intel-ME-AMD-PSP-MINIX-and-Kernel-Design.md) / [Virtual machines, containers and cloud service models](Virtual-Machines-Containers-and-Cloud-Service-Models.md) / [Kubernetes for beginners](Kubernetes-for-Beginners-What-It-Adds-Over-Docker-and-Compose.md) / [Windows, Active Directory and macOS](Windows-Active-Directory-and-macOS-in-the-Enterprise.md) / [Cron, systemd timers and init scripts versus systemd](Cron-Systemd-Timers-and-Init-Scripts-vs-Systemd.md)
- Networking: [How a web request works](How-a-Web-Request-Works.md) / [DNS, Cloudflare and hosting your own website](DNS-Cloudflare-and-Hosting-Your-Own-Website.md) / [Subnets, NAT and firewalls by hand](Subnets-NAT-and-Firewalls-By-Hand.md) / [Behind a CDN: real client IPs and OSI basics](Behind-a-CDN-Real-Client-IPs-and-OSI-Basics.md) / [IPv6 adoption and handling it safely](IPv6-Adoption-and-Handling-It-Safely.md)
- Identity and secrets: [APIs and tokens from zero](APIs-and-Tokens-From-Zero.md) / [Hashing, encryption and keys](Hashing-Encryption-and-Keys.md) / [Secrets from day one](Secrets-From-Day-One.md) / [Password managers and passkeys](Password-Managers-and-Passkeys-What-Each-Protects-and-Where-They-Fail.md) / [Disk and file encryption: VeraCrypt, TrueCrypt, BitLocker, FileVault, LUKS](Disk-and-File-Encryption-VeraCrypt-TrueCrypt-History-BitLocker-FileVault-and-LUKS.md) / [Enterprise identity: SSO, SAML and OIDC](Enterprise-Identity-SSO-SAML-OIDC.md) / [Hardware security keys: YubiKey, Nitrokey, PIV](Hardware-Security-Keys-YubiKey-Nitrokey-Smart-Cards-and-PIV.md)
- Infrastructure as code: [Data formats: JSON, YAML, HCL](Data-Formats-JSON-YAML-HCL.md) / [OpenTofu from zero](OpenTofu-From-Zero.md) / [OpenTofu plans, state, drift and recovery](Plans-State-Drift-and-Recovery.md) / [Ansible: configuration management versus provisioning](Ansible-Configuration-Management-Versus-Provisioning.md) / [Native IaC versus open standards](Native-IaC-vs-Open-Standards-CloudFormation-ARM-Bicep-and-OpenTofu.md) / [Spacelift from zero](Spacelift-From-Zero.md) / [Build and destroy: one stack per service](Build-and-Destroy-Stack-Per-Service.md) / [Environments and promotion](Environments-and-Promotion-Dev-Staging-Production.md)
- Web hosting: [LAMP and LEMP from zero](LAMP-and-LEMP-From-Zero.md) / [WordPress and PHP security, WAFs and static sites](WordPress-and-PHP-Security-WAF-and-Static-Sites.md) / [Static against dynamic: Hugo, WordPress and recon](Static-vs-Dynamic-Sites-Hugo-and-WordPress-and-Recon.md) / [WordPress at scale: CDN, WAF, caching and CI](WordPress-at-Scale-CDN-WAF-and-CI.md) / **Autoscaling and elasticity**

Related pages:

- [Containers and Docker (optional)](Containers-and-Docker-Basics.md)
- [How money works](How-Money-Works-in-the-Cloud.md)
- [CI, tests and the cost gate](CI-Tests-and-Cost-Gate.md)
- [Virtual machines, containers and cloud service models](Virtual-Machines-Containers-and-Cloud-Service-Models.md)
- [WordPress at scale: CDN, WAF, caching and CI](WordPress-at-Scale-CDN-WAF-and-CI.md)
- [Rate limiting at every layer](Rate-Limiting-at-Every-Layer.md)
<!-- END GENERATED PAGE NAV bottom -->
