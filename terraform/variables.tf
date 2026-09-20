variable "aws_region" {
  description = "AWS region for the cloud tier."
  type        = string
  default     = "eu-central-1"
}

variable "instance_type" {
  description = "EC2 instance size. t3.small comfortably runs controller+prometheus+grafana."
  type        = string
  default     = "t3.small"
}

variable "my_ip_cidr" {
  description = "Your current public IP in CIDR form (e.g. 203.0.113.4/32), used to lock down SSH and the dashboard ports. Find it with: curl -s ifconfig.me"
  type        = string
}

variable "tailscale_authkey" {
  description = "A reusable, ephemeral Tailscale auth key (generate at https://login.tailscale.com/admin/settings/keys). Treated as sensitive -- pass via TF_VAR_tailscale_authkey env var, never commit it."
  type        = string
  sensitive   = true
}

variable "edge_tailscale_host" {
  description = "The edge machine's Tailscale MagicDNS name or 100.x.y.z IP (set this up first -- see docs/deploy/edge-setup.md -- then come back and fill this in)."
  type        = string
}

variable "repo_url" {
  description = "Git URL the instance clones to get docker-compose.cloud.yaml, prometheus config, etc."
  type        = string
  default     = "https://github.com/ItayFraiman/Home-monitoring.git"
}

variable "repo_ref" {
  description = "Branch or tag to check out."
  type        = string
  default     = "main"
}
