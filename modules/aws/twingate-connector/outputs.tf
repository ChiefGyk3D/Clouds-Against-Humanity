# The module contract (design section 5): neutral names, the same on every
# provider. Each is exactly an instance attribute, never derived from the boot
# data.
output "instance_id" {
  value = aws_instance.connector.id
}

output "instance_name" {
  value = aws_instance.connector.tags["Name"]
}

output "private_ip" {
  value = aws_instance.connector.private_ip
}

output "size" {
  value = aws_instance.connector.instance_type
}
