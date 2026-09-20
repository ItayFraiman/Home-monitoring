terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# Amazon Linux 2023, latest, resolved at apply time rather than pinned --
# fine for a throwaway interview-prep box, would pin by AMI ID for anything
# longer-lived.
data "aws_ami" "al2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }
}

resource "aws_security_group" "cloud_tier" {
  name        = "home-monitoring-cloud"
  description = "Home-monitoring cloud tier: SSH + dashboards locked to my IP, all egress open (Tailscale needs outbound UDP for NAT traversal, apt/docker pulls need outbound HTTPS)."

  ingress {
    description = "SSH from me"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.my_ip_cidr]
  }

  ingress {
    description = "Grafana from me"
    from_port   = 3000
    to_port     = 3000
    protocol    = "tcp"
    cidr_blocks = [var.my_ip_cidr]
  }

  ingress {
    description = "Prometheus from me"
    from_port   = 9090
    to_port     = 9090
    protocol    = "tcp"
    cidr_blocks = [var.my_ip_cidr]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Deliberately no inbound rule for the sensor/actuator ports (8001/8002)
  # or for a Tailscale listener port -- the cloud box reaches the edge box
  # outbound-only over the tailnet, it never needs to accept inbound
  # connections from it. Nothing about this tier's job requires opening
  # ports toward the edge machine's home network.
}

resource "aws_instance" "cloud_tier" {
  ami                    = data.aws_ami.al2023.id
  instance_type          = var.instance_type
  vpc_security_group_ids = [aws_security_group.cloud_tier.id]

  user_data = templatefile("${path.module}/user_data.sh.tpl", {
    tailscale_authkey = var.tailscale_authkey
    edge_host          = var.edge_tailscale_host
    repo_url           = var.repo_url
    repo_ref           = var.repo_ref
  })

  root_block_device {
    volume_size = 12
    volume_type = "gp3"
  }

  tags = {
    Name    = "home-monitoring-cloud"
    Project = "home-monitoring"
  }
}
