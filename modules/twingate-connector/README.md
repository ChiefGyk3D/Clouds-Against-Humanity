# twingate-connector (DigitalOcean)

The DigitalOcean machine that runs a Twingate connector. The Twingate resources
and the hardened cloud-init are not here: they come from
[`../twingate-bootstrap`](../twingate-bootstrap), which every provider's
connector module calls, and `main.tf` passes its `user_data` straight to the
droplet.

| Role | DigitalOcean object | Another provider's object |
|---|---|---|
| The machine | `digitalocean_droplet` | AWS: an instance. Azure: a virtual machine. GCP: a compute instance. |
| Its identity | `instance_id`, `instance_name` | The provider's instance id and name. |
| Its private address | `private_ip` | The interface's private address. |
| Boot data | `user_data` | AWS `user_data`, Azure `custom_data`, GCP `metadata_startup_script`. |

Contract outputs: `instance_id`, `instance_name`, `private_ip`, `size`. The
older `droplet_name` and `droplet_urn` stay because stack 10 uses them.

## Provider extensions

`ssh_key_fingerprint` (a key registered on the DigitalOcean account) and `tags`
(set at creation so the firewall applies from the first second). Other
providers have their own equivalents, such as an AWS key-pair name.
