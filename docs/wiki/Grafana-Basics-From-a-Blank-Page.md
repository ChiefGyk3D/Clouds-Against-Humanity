# Grafana basics: from a blank page to one useful panel and one alert

> **Status: written from reading, not run.** The facts about Grafana come from the Grafana documentation pages listed in the [claims register](#claims-register), read on **2026-10-30**. None of the exercise was run by the author: no data source was added, no panel built, no alert rule created and no contact point tested, not even in the [synthetic lab](Lab-Demo-Monitoring-Stack.md). The lab runs Grafana 12.1.0, while the documentation pages are the "latest" ones and mention Grafana 13, so a menu name or a screen may differ from what you see. The SQL and OpenSearch connections are explained from the documentation only: this project runs no SQL database, and no OpenSearch has been run here. Stage 4 (Grafana, on-prem) is planned and not built. Where something is general knowledge and not read on a Grafana page, the text says **est.**

> Unfamiliar word or acronym? The [Glossary](Glossary.md) defines it.

**Prerequisites:** [Reading a dashboard as an operator](Reading-a-Dashboard-as-an-Operator.md) (what a panel hides), [Telemetry crosses the trust boundary](Telemetry-Crosses-the-Trust-Boundary.md) (why a one-port path is not read-only) and [Doppler and secrets](Doppler-and-Secrets.md). To run the exercise you need the [synthetic monitoring lab](Lab-Demo-Monitoring-Stack.md) up on your own computer. It is free and touches no cloud.

This page extends [Grafana dashboards: the three this repository ships](Grafana-Dashboards.md). That page tells you what is in the box. This one starts from an empty Grafana and walks the other way: connect something, ask it a question, draw the answer, and decide when it should wake a person.

## Where this sits: the cloud side comes first

Grafana here is **stage 4**, and it runs **on-prem**, next to the SIEM at home. It adds $0 to the cloud bill ([Roadmap](Roadmap.md)). A dashboard is only as good as what feeds it, so the cloud side of telemetry comes first: the exporters and the agent on the connector droplets, the [pull for metrics, push for logs](Telemetry-Crosses-the-Trust-Boundary.md#pull-for-metrics-push-for-logs) design, and the [home-side runbook](Stage-2-Home-Side-Runbook.md). None of that is applied yet. How an event travels from a droplet to a panel is the subject of the pipelines lesson, tracked in issue #321 and not written yet. Until then, the lab's generator plays the part of the cloud. The telemetry path itself is tracked in issue #100 (enabling connector telemetry one connector at a time) and issue #101 (Prometheus scraping the connectors through a headless Twingate client).

Cost first: Grafana is open source and the lab runs in containers on your laptop, so this lesson costs nothing. A cloud Grafana is a learner build, priced in [Build your own mini SOC](Build-Your-Own-Mini-SOC.md#what-it-costs), and is not part of the reference environment.

## What you will be able to do

- Say what a data source is, and what Grafana stores for one.
- Connect Grafana to Prometheus, to a SQL database and to OpenSearch, and say what is different about each.
- Give Grafana a database account that can only read, and keep the password out of the dashboard file.
- Say what **Save & test** proves, and what it does not.
- Build one panel from a blank page, give it a threshold, and turn the same query into an alert rule with a contact point.
- Decide which panels are decoration and which help someone act.
- Say why dashboards and data sources are kept as files in git.

## What a data source is

Grafana does not keep your metrics or your logs. A **data source** is a saved connection to a system that does ([Grafana: data sources](https://grafana.com/docs/grafana/latest/datasources/)). It holds a name, an address (a URL, or a host and port), how to log in, and the TLS settings. Panels and alert rules send a question, called a query, to a data source and draw or judge the answer. Each data source type has its own query editor, because a PromQL query, a SQL query and a Lucene search do not look alike.

Three facts shape everything below:

- **Only an organization administrator can add a data source.** Anyone else can only use one.
- **By default any user in the organization can query any data source in it.** Restricting that needs Grafana Enterprise or Grafana Cloud ([data source management](https://grafana.com/docs/grafana/latest/administration/data-source-management/)). So on the open source Grafana a stage 4 viewer can run a query as the data source's account. That account is therefore the real limit on what a viewer can do, and it is why the next sections insist on read-only.
- **One data source can be marked the default.** It is pre-selected for new panels, for Explore and for alert rules. The repository's dashboards do not rely on that: they pick the data source through a variable, so the file names no connection at all ([Grafana dashboards](Grafana-Dashboards.md)).

## Database connection basics

Every connection answers the same six questions. Write the answers down before you open Grafana.

| Question | For Prometheus | For a SQL database (PostgreSQL, MySQL) | For OpenSearch |
|---|---|---|---|
| Where is it? | A URL such as `http://prometheus:9090` | A host and an optional port (PostgreSQL 5432, MySQL 3306) and a database name | A URL with protocol and port, such as `http://localhost:9200` |
| Who am I? | Basic authentication, forwarded OAuth identity, or none | A user name and password | Basic authentication, TLS client certificate, AWS SigV4 or OAuth pass-through |
| What may that account do? | Prometheus itself has no account that "can only read": the limit is the network path or a proxy in front (est., see below) | `SELECT` on the tables you chart, and nothing else | A role that can read the indices you chart (est.: the role system is OpenSearch's, not read for this page) |
| Is it encrypted, and is the server's identity checked? | TLS is set up in Prometheus first, then in Grafana | A TLS mode, and a CA certificate for the strict modes | TLS client auth with CA cert, client cert and client key |
| What is the path? | The scrape and query ports, here a Twingate resource | One host and port, here a Twingate resource | One host and port, here a Twingate resource |
| What did the test prove? | See "What Save & test proves" | Same | Same |

### Prometheus

The Prometheus data source needs a server URL and an authentication choice, and its page says to have any certificates ready first ([configure the Prometheus data source](https://grafana.com/docs/grafana/latest/datasources/prometheus/configure/)). Two details from that page are easy to miss:

- **In containers, `localhost` is the container itself.** When Grafana and Prometheus run in separate containers, `localhost:9090` points at port 9090 inside the Grafana container. The page says to use the container's address, or the service name under Docker Compose. This is why the lab's own data source uses `http://prometheus:9090`.
- **Add TLS to Prometheus before you set it in Grafana.** The page says the TLS settings must be in the Prometheus configuration file before you set these options in Grafana. It also describes a "Skip TLS verify" switch and says skipping is not recommended unless absolutely necessary or for testing.

Prometheus has no database user to make read-only. Twingate limits the host and port a client can reach, and the [one-port resource page](Telemetry-Crosses-the-Trust-Boundary.md#a-one-port-resource-is-not-read-only) explains why that is not the same as read-only: the design's answer is a read-only, authenticated proxy at home that passes only query endpoints. That is the project's design, not something Grafana provides.

### A SQL database

The documentation for both MySQL and PostgreSQL says the same thing, in nearly the same words: give Grafana a **dedicated database user with only `SELECT`** on the relevant tables, because **Grafana does not validate the safety of queries**. A user who can edit a panel can type `DROP TABLE` as easily as `SELECT`, and the database will do what its account is allowed to do ([MySQL](https://grafana.com/docs/grafana/latest/datasources/mysql/configure/), [PostgreSQL](https://grafana.com/docs/grafana/latest/datasources/postgres/configure/)). The PostgreSQL page's example is a single `GRANT SELECT ON schema.table TO grafanareader;`, and the MySQL page creates a `grafanaReader` user the same way. A **read-only database user** is the only control here that does not depend on anyone behaving.

Sketch (PostgreSQL syntax from the page; names are examples, and the password never goes in a file you commit):

```sql
CREATE USER grafanareader WITH PASSWORD :'reader_password';  -- psql variable, supplied at run time
GRANT USAGE ON SCHEMA app TO grafanareader;
GRANT SELECT ON app.events TO grafanareader;
```

The `GRANT SELECT` line is from the documentation. The `CREATE USER ... :'reader_password'` form and the `GRANT USAGE` line are the author's general knowledge (**est.**): the schema usually needs a `USAGE` grant for the user to see its tables. Not run.

For TLS, the PostgreSQL page lists the modes `disable`, `require`, `verify-ca` and `verify-full`, and says `disable` is for local development or trusted private networks only, `require` encrypts but does not check the server's certificate, and `verify-full` checks the certificate authority and the host name and is recommended for production when you control the certificates. The MySQL page has toggles for a CA certificate and for skipping verification of the certificate chain and host name. The difference between "encrypted" and "encrypted to the right server" is the one to remember: a mode that encrypts but does not verify protects against someone reading the wire, not against someone answering in the server's place.

The host in the data source is a name or an address and a port. In documentation, use the reserved ranges: a connection might be `192.0.2.50:5432`. A real address belongs in your own Grafana, never in a file in this repository.

### OpenSearch

OpenSearch is a plugin data source. Its page lists a URL, then basic authentication or TLS client authentication (CA cert, client cert and client key), with a "Skip TLS Verify" switch it calls not recommended for production ([configure the OpenSearch data source](https://grafana.com/docs/plugins/grafana-opensearch-datasource/latest/configure/)). It also needs the index name (a pattern is allowed), the time field (default `@timestamp`) and the server **version**, because query composition differs between versions. A version that no longer matches after an upgrade can cause errors. The Wazuh dashboard uses this data source type, and its page says plainly that no OpenSearch query was ever run here.

## Credentials come from a secret store, never from the dashboard

The password for a data source is a secret, and secrets in this project live in a secret store ([Doppler and secrets](Doppler-and-Secrets.md)). Three places could hold it, and only one is right:

| Where | Verdict |
|---|---|
| Inside the dashboard JSON | Never. The file is committed, reviewed, copied and shared. The repository's dashboards contain no data source uid, URL or address, and a test enforces that. |
| Typed into the Grafana screen by hand | Works once, then nobody can rebuild it or say what it is. Fine for a lab, not for an operation. |
| In a provisioning file as an environment variable lookup | The pattern to use. |

The provisioning page says environment variable lookups work in all provisioning configuration, with `$NAME` or `${NAME}`, and that the example puts the password under `secureJsonData`, the map Grafana encrypts before storing ([provisioning](https://grafana.com/docs/grafana/latest/administration/provisioning/)). It also warns that a value containing `$` is expanded twice with the braces form, so use `$NAME` for such a value, and says to use environment variables for configuration values only, not for keys or big parts of the file's structure.

```yaml
# datasources/postgres.yaml (example; names are placeholders)
apiVersion: 1
datasources:
  - name: Events DB
    type: postgres
    url: db.example.internal:5432
    user: grafanareader
    secureJsonData:
      password: $GRAFANA_DB_PASSWORD   # supplied by the environment, from the secret store
    jsonData:
      database: events
      sslmode: verify-full
```

The structure and the `database` and `sslmode` fields follow the PostgreSQL page's own provisioning example, which also says `type: postgres` remains a supported alias. The `$GRAFANA_DB_PASSWORD` lookup follows the provisioning page's environment variable example. The combination was not run.

How the value reaches Grafana's environment on the stage 4 host is not designed yet. The shape would match the rest of the project: the secret store holds the value, and the process that starts Grafana receives it as an environment variable, so no file holds it. Rotating the password is then a change in the secret store and a restart, plus the matching `ALTER USER` on the database.

Two more rules that cost nothing: a data source provisioned from a file cannot be edited in the Grafana screen (the Prometheus page says so; the lab's data source also sets `editable: false`), and a read-only database user means a leaked Grafana password lets someone read, not rewrite.

## The network path: least privilege through Twingate

Grafana at home must reach three things: the Prometheus that scrapes the cloud connectors, a possible SQL database, and OpenSearch for the Wazuh dashboard. The rule for each is the one the rest of the project uses ([Twingate](Twingate.md), [Telemetry crosses the trust boundary](Telemetry-Crosses-the-Trust-Boundary.md)):

- **One resource per service, one port each.** Do not grant a network. A Twingate resource for the database is that host and TCP port 5432, nothing wider.
- **Grant it to the one identity that needs it.** Grafana's identity gets the databases it charts; a person's laptop does not get the database port just because the person likes dashboards. Which kind of Twingate identity Grafana can use depends on the plan: see [Twingate service accounts in CAH](Twingate-Service-Accounts-in-CAH.md).
- **The connection starts at Grafana.** Grafana asks, the database answers. Nothing on the database side should be able to open a path back to Grafana.
- **The path is not the permission.** A one-port resource limits where you can knock, not what you can say once inside, which is why the read-only account above is still required.

## What Save & test proves

Every data source page ends with a **Save & test** button. The Prometheus page says that after it you should see "Successfully queried the Prometheus API." The PostgreSQL and OpenSearch pages tell you to click it to confirm the connection and give no message text, so this lesson quotes none.

What a pass proves, in this author's reading: Grafana, from where it runs, reached that address, completed the login you configured and got an answer back. What it does not prove:

- That the account is **read-only**. A passing test says nothing about what the account may do. Check the grants in the database.
- That the **TLS mode is the strict one**. A test passes with `disable` just as well, and also with a mode that encrypts without verifying.
- That a **dashboard query** will work: the table may not exist or the metric may not be exported, and an empty panel is a different failure from a failed test.
- That the path stays up, or that a viewer can reach it. The test runs once, as the person who clicked.

These are the author's reasoning from what the pages say a test does (**est.**). A test that fails is the more informative result: that is the exercise's last step.

## Build one panel from a blank page

You will use the lab, so nothing here touches a cloud or a real host.

**Set up.** From the repository root, `scripts/demo_monitoring.sh up`, then open `http://127.0.0.1:3300` and log in as `admin` (the lab page says where the password is). Give it two minutes for rates.

**1. Add a second Prometheus data source yourself.** The lab's own data source is provisioned and not editable, so make a practice one. In Grafana, Connections, Add new connection, search Prometheus, Add new data source. Name it `practice-prom`. Set the URL to `http://prometheus:9090`, which is the service name, not `localhost`, for the reason above. Leave authentication at none. Click **Save & test**. Predict the message first.

**2. Break it, then read the error.** Change the URL port to `9091`, which nothing listens on, and click **Save & test** again. Write down what the error says and which of the six questions it points at. Put the port back.

**3. Create a panel.** New dashboard, Add visualization, choose `practice-prom`. Switch the query editor to Code and enter:

```promql
sum by (site) (1 - up{job="twingate-ztna"})
```

`up` is 1 for a target that answered its last scrape and 0 for one that did not, so `1 - up` is 1 for each failed target and the sum is the number of failed targets per site. With the lab healthy it shows 0 for each of the two sites.

**4. Choose a panel type.** Pick **Stat**. The Stat page says it shows single values of interest, such as the latest value of a series, and suits monitoring key metrics at a glance and highlighting values above your normal thresholds ([Stat](https://grafana.com/docs/grafana/latest/visualizations/panels-visualizations/visualizations/stat/)). The question is "how many things are broken right now, per site", which is one number per site. A time series would answer "when did it break", a different question.

**5. Set a threshold.** A threshold is a value that changes how the panel is colored when it is met or exceeded ([thresholds](https://grafana.com/docs/grafana/latest/visualizations/panels-visualizations/configure-thresholds/)), and Stat can color the background or the value text. Make the base green and add one step at `1` in red. Title the panel "Failed targets per site". Save the dashboard.

**6. Predict, then break it.** Write down what the two sites will show after `scripts/demo_monitoring.sh silent-site site-tor2`, then run it and watch for about two minutes. Restore with `scripts/demo_monitoring.sh restore-site`. The lab's alert tests say a site fully down shows four failed targets.

**7. Compare with the shipped panel.** Open **CAH: Sites overview** and its "Targets down per site". It starts from the expected-target inventory, so a site that vanished from the target list still shows. Your query cannot do that: if the series disappear, `sum` has nothing to add and the site drops off the panel. Explain in one sentence why a panel that cannot show a vanished site is not enough, using [Reading a dashboard as an operator](Reading-a-Dashboard-as-an-Operator.md#up-up--0-and-a-missing-series).

## Decoration or decision

A panel earns its place if someone can look at it and do something. Ask of each panel, in this order:

1. **What decision does this change?** "Page someone", "wait", "roll back", "nothing, this is normal". If the answer is "nothing, but it looks good", it is decoration.
2. **What would it look like if the answer were bad?** If the bad case looks like the good case (an empty panel, a flat line), it can lie. This is the lesson of the previous page.
3. **Is there a number or a color that means "act"?** That is a threshold with a reason. A red step at a value nobody chose is decoration with an alarming color.
4. **Who looks, and how often?** A panel nobody opens should be an alert or be deleted.

Applied to the shipped dashboards: "Targets down per site", "Targets that are not up" and the target-state bars help a person decide (page, wait, find the host). "Scrape duration" and "Samples scraped" are early warnings that help only if someone reads them next to the others. "Uptime since boot" helps once, after a change. A wall of CPU graphs for droplets that are idle most days is decoration until the CPU line is tied to something you would do. The Stat-with-threshold pattern is for the first kind; the time series is for diagnosis after the first kind has fired.

## An alert rule and a contact point

A panel needs a person looking. An **alert rule** looks for you. The same query you charted becomes the rule's condition, and a **contact point** says where the message goes.

**1. Make a contact point.** Alerting, Notification configuration, Contact points, New contact point. Name it `practice-hook`. Pick an integration type. The Grafana page lists email, Slack, webhook, PagerDuty and many more, and says a contact point can hold one or more integrations ([manage contact points](https://grafana.com/docs/grafana/latest/alerting/configure-notifications/manage-contact-points/)). The lab has no mail server and no chat, so choose **Webhook** and give it a URL of a listener you run yourself, or accept that delivery will fail. The page's Test button sends a test notification, and the Contact points tab shows the status of the latest deliveries, so a failed delivery is still something you can read. (Reaching a listener on your own computer from the Grafana container is the same `localhost` trap as above; this was not run, so how to route it on your machine is for you to find.) Real notification URLs and keys are secrets: they come from the secret store like a database password. The page also says some fields in a contact point are protected, and only an admin can change them, so a viewer cannot redirect alerts.

**2. Make the rule.** Alerting, Alert rules, New alert rule ([create Grafana-managed alert rules](https://grafana.com/docs/grafana/latest/alerting/alerting-rules/create-grafana-managed-rule/)). Name it `Targets failing`. The name becomes the `alertname` label on every alert it creates. Choose `practice-prom`, enter the same query, and set the condition to "is above 0". Click **Preview**.

**3. Set the pending period.** The page defines it: the period during which a rule can be in breach before it fires. After the condition is met the alert is **Pending**; if it holds for the full period it becomes **Firing**, and if not it returns to **Normal**. Set one minute. That matches the lab's own Prometheus rules, which wait one minute so a lesson fits in a sitting; the design waits five. A short period catches problems quickly and pages on every blip. A long one is quiet and late.

**4. Decide what no data means.** The page lets you choose the state for "no data" and for "error" (Normal, Alerting, Error or No Data, and Keep last state). That choice is the same silent-site problem again: with the wrong setting, a rule whose query returns nothing reports that everything is fine. Think about which setting you would pick for this rule and write down why before you choose.

**5. Choose the contact point.** Under notifications, the default view lets you pick a contact point and sends every notification for this rule there, skipping notification policies. The Advanced view routes by labels through the notification policy tree. For one rule and one operator, the default is enough; with many rules and people, use policies.

**6. Fire it.** Run `scripts/demo_monitoring.sh silent-site site-tor2`, open the rule's list entry, and watch it go Normal, Pending, Firing for `site-tor2` only. Rules that return one value per site create one alert instance per site (the page describes separate alerts per series). Then run `scripts/demo_monitoring.sh restore-site` and watch it resolve. Read the contact point's delivery status.

**What the alert does not do.** It judges only what it can query. It says nothing if Grafana is down or the data source is unreachable, except through the "error" state you chose, and the lab's Prometheus rules (`CloudSiteSilent`, `CloudSiteDegraded`) remain the thing that sees a vanished site. Who watches the watcher is a stage 4 design question, not answered here.

## Dashboards and rules as code

A dashboard clicked together in a browser exists in one Grafana's database. A dashboard in a file can be reviewed in a pull request, tested, rebuilt after a crash and installed in two places, which is the argument the rest of the project makes for infrastructure ([What is infrastructure as code](What-Is-Infrastructure-as-Code.md)).

The provisioning page describes a file-based provider: Grafana reads dashboard JSON files from a path and creates or updates them at start, and rescans on an interval. Settings worth knowing, with the lab's values:

| Setting | What the page says | Lab ([`dashboards.yml`](https://github.com/ChiefGyk3D/Clouds-Against-Humanity/blob/main/labs/demo-monitoring/grafana/provisioning/dashboards/dashboards.yml)) |
|---|---|---|
| `allowUiUpdates` | Allows saving changes to a provisioned dashboard from the UI. With `false` you cannot save changes to it. With `true`, saved changes persist to Grafana's database | `false` |
| `disableDeletion` | Stops Grafana deleting a dashboard whose file is removed. Without it, removing the provisioning source deletes the dashboard | `true` |
| `updateIntervalSeconds` | How often Grafana scans for changes | `30` |
| `foldersFromFilesStructure` | Builds Grafana folders from the folder names on disk | not used |

A provisioned data source cannot be edited in the UI either. Alerting resources can also be provisioned, and the contact point page says contact points can be exported as JSON, YAML or Terraform. The provisioning page says Grafana encrypts secure settings in its database, and environment variables are for provisioning configuration but not for the dashboard definition files themselves, which is another reason the dashboards here carry no connection details.

The honest cost of "as code": a change made by hand in the browser on a provisioned dashboard is not kept, and a person can find that out at the worst moment. The lab sets `allowUiUpdates: false` so the dashboard on screen is always the dashboard in git. To change one, change the file, run `python -I -m pytest tests/test_dashboards.py`, and let the next provisioning scan pick it up. The Terraform provider for Grafana is mentioned on the pages as an alternative; this project has not tried it.

## Predict, then check

1. A teammate says "the database test passed, so we are safe." Name three things the test did not prove.
2. You type the real database password into a provisioning YAML instead of a lookup, and commit it. Name two places the value now lives that you cannot easily clean. What is the first thing you do?
3. Your Stat panel reads `0` for a site. Name two situations that would make that wrong.
4. You set a rule's no-data state to Normal, and a site stops reporting. What does the rule say, and what catches it?
5. Why is "only an admin can add data sources" not enough to protect a SQL database?

<details>
<summary>Answers</summary>

1. That the account is read-only; that TLS is the strict mode (a disabled or non-verifying mode also passes); that a dashboard query will return anything; and that it will keep working.
2. The git history (including every clone and fork) and any copy of the file. Rotate the password first, then clean up the history; the password is already spent.
3. The series vanished (nothing to sum, the panel can read 0 or no data depending on the panel, the site may be gone), or the panel's time range or variable excludes the target.
4. It says Normal. A separate rule that counts expected targets, as the lab's Prometheus rules do, or a "no data" setting that alerts.
5. Any viewer in the organization can query any data source, by default, as that data source's account. The account's grants are the limit.

</details>

## Try it yourself

- Add a second `site` to the lab as the [Grafana dashboards page](Grafana-Dashboards.md#try-it-yourself) describes, and see whether your panel and rule pick it up without a change. Does your rule see the new site if its targets are all down?
- Re-create the panel as a **Time series** and set the same threshold. Which of the two would you put on a wall, and which would you open after an alert?
- Export your rule or your contact point as YAML from the Grafana screen, and read what it holds. Is a secret in it?
- Delete your practice dashboard and data source, then run `scripts/demo_monitoring.sh down` when you are done.

## Claims register

All requests were read-only page fetches, retrieved **2026-10-30**. Each page carries a "Last reviewed" date; that is the date on the page, not the date of this lesson.

| Claim | Source | Status |
|---|---|---|
| A data source is a connection to a storage backend; only organization administrators add them; by default any user in the organization can query any data source; one can be the default; restricting query access needs Enterprise or Cloud | [Grafana: data sources](https://grafana.com/docs/grafana/latest/datasources/) (last reviewed 2026-03-10) | Read, 2026-10-30 |
| Data source permissions and read-only provisioned data sources | [Data source management](https://grafana.com/docs/grafana/latest/administration/data-source-management/) (last reviewed 2026-09-22) | Read, 2026-10-30 |
| Prometheus: URL, authentication choices, localhost-in-a-container note, TLS must be set in Prometheus first, skip TLS verify not recommended, Save & test message, provisioned data sources cannot be edited in the UI | [Configure the Prometheus data source](https://grafana.com/docs/grafana/latest/datasources/prometheus/configure/) (last reviewed 2026-08-04) | Read, 2026-10-30 |
| MySQL: dedicated user with only `SELECT`, Grafana does not validate query safety, default port 3306, TLS toggles | [Configure the MySQL data source](https://grafana.com/docs/grafana/latest/datasources/mysql/configure/) (last reviewed 2026-08-10) | Read, 2026-10-30 |
| PostgreSQL: dedicated `SELECT`-only user, default port 5432, TLS modes `disable`, `require`, `verify-ca`, `verify-full` and what each verifies | [Configure the PostgreSQL data source](https://grafana.com/docs/grafana/latest/datasources/postgres/configure/) (last reviewed 2026-09-10) | Read, 2026-10-30 |
| OpenSearch: URL, basic auth and TLS client auth, index name, time field default `@timestamp`, version setting | [Configure the OpenSearch data source](https://grafana.com/docs/plugins/grafana-opensearch-datasource/latest/configure/) (last reviewed 2026-03-26) | Read, 2026-10-30 |
| Environment variable lookups in provisioning, `secureJsonData` encrypted, `$` double-expansion warning, dashboard provider settings, secure settings encrypted in the database | [Provision Grafana](https://grafana.com/docs/grafana/latest/administration/provisioning/) | Read, 2026-10-30 (no "last reviewed" line was in the page text) |
| Stat visualization: single values, thresholds | [Stat](https://grafana.com/docs/grafana/latest/visualizations/panels-visualizations/visualizations/stat/) | Read, 2026-10-30 |
| A threshold colors a panel when a value is met or exceeded | [Configure thresholds](https://grafana.com/docs/grafana/latest/visualizations/panels-visualizations/configure-thresholds/) | Read, 2026-10-30 |
| Contact points: integrations, protected fields, Test button, delivery status, export formats | [Configure contact points](https://grafana.com/docs/grafana/latest/alerting/configure-notifications/manage-contact-points/) | Read, 2026-10-30 |
| Alert rules: name becomes `alertname`, pending period and states, no-data and error handling, default versus advanced notification routing | [Configure Grafana-managed alert rules](https://grafana.com/docs/grafana/latest/alerting/alerting-rules/create-grafana-managed-rule/) | Read, 2026-10-30 |
| The `GRANT USAGE` line and the `CREATE USER` form, the OpenSearch role needed to read an index, the Twingate and secret-store arrangement for stage 4 | Author's general knowledge or the project's design | **est.**; not read on a Grafana page, not run |
| What a passing Save & test does and does not prove | Author's reasoning from the pages above | **est.** |
| Every step of the exercise | Not run | Written from reading; the lab image is Grafana 12.1.0, the pages are "latest" |
| Lab facts: provisioned data source `editable: false`, `allowUiUpdates: false`, the alert rules and the `silent-site` and `restore-site` commands | [Lab](Lab-Demo-Monitoring-Stack.md) and the files under `labs/demo-monitoring/` | Read in the repository; `tests/test_demo_monitoring.py` checks the files |

Next: [Grafana dashboards](Grafana-Dashboards.md), then the [Roadmap](Roadmap.md). Back to the [Reading order](Reading-Order.md).
