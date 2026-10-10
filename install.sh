#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
root_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$root_dir"
if [[ "$(uname -s)" != Linux ]]; then
  printf '%s\n' 'The server installer requires Linux. See README for local Windows/macOS setup.' >&2
  exit 1
fi
bash "$root_dir/scripts/prepare-host.sh"
docker_cmd=(docker)
if ! docker info >/dev/null 2>&1; then
  if command -v sudo >/dev/null && sudo docker info >/dev/null 2>&1; then
    docker_cmd=(sudo docker)
  else
    printf '%s\n' 'Docker daemon is unavailable. Start Docker, then rerun this installer.' >&2
    exit 1
  fi
fi
version="$("${docker_cmd[@]}" compose version --short)"
version="${version#v}"
if [[ "$(printf '%s\n' 2.30.0 "$version" | sort -V | head -n1)" != 2.30.0 ]]; then
  printf '%s\n' 'Docker Compose 2.30+ is required for literal secret values. Update the Compose plugin.' >&2
  exit 1
fi
printf '\n%s\n' 'Building Bitpin AI Connector…'
"${docker_cmd[@]}" build -t bitpin-ai-connector:local .
"${docker_cmd[@]}" run --rm -it --user "$(id -u):$(id -g)" \
  -v "$root_dir:/workspace" bitpin-ai-connector:local \
  python /app/scripts/setup.py --directory /workspace "$@"
"${docker_cmd[@]}" compose config --quiet
"${docker_cmd[@]}" compose up -d --wait --wait-timeout 120
printf '\n%s\n' 'Application started. Checking Bitpin authentication (no trade is submitted)…'
"${docker_cmd[@]}" compose exec -T connector bitpin-ai-connector ip
if ! "${docker_cmd[@]}" compose exec -T connector bitpin-ai-connector doctor --private; then
  printf '%s\n' 'Bitpin check failed. Check API keys, their permissions, and the outbound server IP allowlist. Services remain running.' >&2
  exit 1
fi
printf '\n%s\n' 'Checking public HTTPS certificate and health endpoint…'
"${docker_cmd[@]}" compose exec -T connector bitpin-ai-connector check-https
printf '\n%s\n' 'Installation complete. Your private connector URL:'
"${docker_cmd[@]}" compose exec -T connector bitpin-ai-connector url
printf '%s\n' 'Default setup: choose No authentication in ChatGPT or Claude; keep this URL private.' \
  'With --oauth: choose OAuth and use your connector password.' \
  'Operations: docker compose logs --tail 100; docker compose restart; docker compose down (preserves data).'
