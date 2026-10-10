#!/usr/bin/env bash
# Install Docker from its signed official apt repository on supported Ubuntu/Debian hosts.
set -Eeuo pipefail

compose_ready() {
  local version
  version="$(docker compose version --short 2>/dev/null)" || return 1
  version="${version#v}"
  [[ "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+ ]] || return 1
  [[ "$(printf '%s\n' 2.30.0 "$version" | sort -V | head -n1)" == 2.30.0 ]]
}

package_installed() {
  [[ "$(dpkg-query -W -f='${Status}' "$1" 2>/dev/null)" == 'install ok installed' ]]
}

if docker info >/dev/null 2>&1 && compose_ready && docker buildx version >/dev/null 2>&1; then
  printf '%s\n' 'Existing Docker, Compose and Buildx are ready.'
  exit 0
fi
if [[ "$(id -u)" != 0 ]]; then
  command -v sudo >/dev/null || { printf '%s\n' 'Root or sudo access is required to install prerequisites.' >&2; exit 1; }
  exec sudo bash "${BASH_SOURCE[0]}" "$@"
fi
[[ "$(uname -s)" == Linux ]] || { printf '%s\n' 'Linux is required.' >&2; exit 1; }
# shellcheck source=/dev/null
source /etc/os-release
case "${ID:-}:${VERSION_ID:-}" in
  ubuntu:22.04|ubuntu:24.04|ubuntu:26.04|debian:12|debian:13) ;;
  *) printf '%s\n' 'Supported: Ubuntu 22.04/24.04/26.04 or Debian 12/13.' >&2; exit 1 ;;
esac
architecture="$(dpkg --print-architecture)"
case "$architecture" in
  amd64|arm64) ;;
  *) printf '%s\n' 'The application installer supports amd64 and arm64 servers.' >&2; exit 1 ;;
esac

# Reuse a ready daemon without upgrading or restarting it.
if ! compose_ready || ! docker buildx version >/dev/null 2>&1; then
  for package in docker.io docker-compose docker-compose-v2 docker-doc docker-buildx podman-docker; do
    if package_installed "$package"; then
      printf 'Conflicting package: %s. It has not been removed. Follow Docker migration instructions first.\n' "$package" >&2
      exit 1
    fi
  done
  packages=(docker-buildx-plugin docker-compose-plugin)
  if ! package_installed docker-ce; then
    for package in containerd runc; do
      if package_installed "$package"; then
        printf 'Conflicting package: %s. It has not been removed. Use a fresh server or migrate Docker first.\n' "$package" >&2
        exit 1
      fi
    done
    if docker --version >/dev/null 2>&1; then
      printf '%s\n' 'An unmanaged Docker installation is present. Install compatible Compose/Buildx before continuing.' >&2
      exit 1
    fi
    packages=(docker-ce docker-ce-cli containerd.io "${packages[@]}")
  fi
  export DEBIAN_FRONTEND=noninteractive
  apt-get -o Acquire::Retries=3 update </dev/null
  apt-get -o Acquire::Retries=3 install -y --no-install-recommends ca-certificates curl </dev/null
  # Reuse an existing apt source, including hosts where Docker was previously removed.
  # Adding the same URI with another Signed-By path would break apt for the entire host.
  candidate="$(apt-cache policy docker-ce | awk '/Candidate:/ {print $2; exit}')"
  if ! package_installed docker-ce && [[ -z "$candidate" || "$candidate" == '(none)' ]]; then
    install -m 0755 -d /etc/apt/keyrings
    key_file="$(mktemp)"
    trap 'rm -f -- "$key_file"' EXIT
    curl --fail --silent --show-error --location --proto '=https' --tlsv1.2 --retry 3 \
      "https://download.docker.com/linux/$ID/gpg" -o "$key_file"
    install -m 0644 "$key_file" /etc/apt/keyrings/bitpin-docker.asc
    tee /etc/apt/sources.list.d/bitpin-docker.sources >/dev/null <<EOF
Types: deb
URIs: https://download.docker.com/linux/$ID
Suites: ${UBUNTU_CODENAME:-$VERSION_CODENAME}
Components: stable
Architectures: $architecture
Signed-By: /etc/apt/keyrings/bitpin-docker.asc
EOF
    rm -f -- "$key_file"
    trap - EXIT
    apt-get -o Acquire::Retries=3 update </dev/null
  fi
  apt-get -o Acquire::Retries=3 install -y --no-install-recommends "${packages[@]}" </dev/null
fi

if ! docker info >/dev/null 2>&1; then
  command -v systemctl >/dev/null || { printf '%s\n' 'A systemd Linux server is required to start Docker automatically.' >&2; exit 1; }
  systemctl enable --now docker
  for attempt in {1..30}; do
    docker info >/dev/null 2>&1 && break
    sleep 1
  done
fi
docker info >/dev/null 2>&1 || { printf '%s\n' 'Docker could not start. Check systemctl status docker.' >&2; exit 1; }
compose_ready || { printf '%s\n' 'Docker Compose 2.30+ could not be installed. Check your apt sources.' >&2; exit 1; }
docker buildx version >/dev/null
printf '%s\n' 'Docker Engine, Compose and Buildx are ready.'
