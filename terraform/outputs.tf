output "public_ip" {
  value       = aws_instance.cloud_tier.public_ip
  description = "SSH here, or open http://<this>:3000 for Grafana and http://<this>:9090 for Prometheus once the box finishes bootstrapping (a minute or two after apply)."
}

output "ssh_command" {
  value = "ssh ec2-user@${aws_instance.cloud_tier.public_ip}"
}
