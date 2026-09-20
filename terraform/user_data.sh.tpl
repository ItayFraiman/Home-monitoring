#!/bin/bash
# Bootstraps the EC2 instance: Docker, Tailscale, clones the repo, and
# brings up the cloud-tier compose stack. Runs once at first boot as root.
set -euxo pipefail

dnf install -y docker git
systemctl enable --now docker
usermod -aG docker ec2-user

# Docker Compose v2 plugin
mkdir -p /usr/local/lib/docker/cli-plugins
curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64 \
  -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

# Tailscale: joins the same tailnet as the edge box so the two can reach
# each other without either one accepting inbound connections from the
# public internet.
curl -fsSL https://tailscale.com/install.sh | sh
tailscale up --authkey="${tailscale_authkey}" --hostname=home-monitoring-cloud --ssh

git clone --branch "${repo_ref}" --depth 1 "${repo_url}" /opt/home-monitoring
cd /opt/home-monitoring

echo "EDGE_HOST=${edge_host}" > .env
echo "IMAGE_TAG=local" >> .env
sed -i "s/EDGE_HOST_PLACEHOLDER/${edge_host}/g" prometheus/prometheus.cloud.yaml

docker compose -f docker-compose.cloud.yaml up -d
