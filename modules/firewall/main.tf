locals {
  default_outbound = [
    { protocol = "tcp", port_range = "443" },
    { protocol = "tcp", port_range = "80" },
    { protocol = "tcp", port_range = "53" },
    { protocol = "udp", port_range = "53" },
    { protocol = "udp", port_range = "123" },
  ]
  outbound = concat(local.default_outbound, var.extra_outbound_rules)
}

# No inbound_rule block: DigitalOcean denies all inbound traffic that no rule allows.
resource "digitalocean_firewall" "this" {
  name = "${var.layer}-${var.region}-${var.purpose}"
  tags = [var.tag]

  dynamic "outbound_rule" {
    for_each = local.outbound
    content {
      protocol              = outbound_rule.value.protocol
      port_range            = outbound_rule.value.port_range
      destination_addresses = ["0.0.0.0/0", "::/0"]
    }
  }
}
