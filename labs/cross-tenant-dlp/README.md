# Cross-tenant data flows lab

Free, local, loopback only, invented data. The lesson is
[Cross-tenant data flows, data governance and retention, and DLP](../../docs/wiki/Cross-Tenant-Data-Governance-Retention-and-DLP.md);
this folder holds only the code it runs. `start_tenants.sh` starts two `moto`
servers (Apache-2.0), `make_fake_data.py` builds invented data at run time,
`tenants_setup.py` sets the buckets, policy and lifecycle rule,
`monthly_job.py` is the monthly batch with a dry run, verify, alert and
manual sweep, and `dlp_scan.py` is a toy scanner. Nothing here is a product.
