#!/usr/bin/env bash
# Keep the entry point last so piping the download does not consume interactive answers.
set -Eeuo pipefail
umask 077

main() {
  local repository='https://github.com/Erfouni/bitpin-ai-connector.git'
  local destination="${BITPIN_INSTALL_DIR:-/opt/bitpin-ai-connector}"
  [[ "$(uname -s)" == Linux ]] || { printf '%s\n' 'Use an Ubuntu/Debian Linux server.' >&2; return 1; }
  [[ "$(id -u)" == 0 ]] || { printf '%s\n' 'Run the documented one-command installer with root/sudo access.' >&2; return 1; }
  if ! (true </dev/tty) 2>/dev/null; then
    printf '%s\n' 'An interactive terminal is required. Connect with SSH (ssh -t if needed), then rerun.' >&2
    return 1
  fi
  # /etc/os-release is supplied by the operating system, never by the repository.
  # shellcheck source=/dev/null
  source /etc/os-release
  case "${ID:-}:${VERSION_ID:-}" in
    ubuntu:22.04|ubuntu:24.04|ubuntu:26.04|debian:12|debian:13) ;;
    *) printf '%s\n' 'Supported: Ubuntu 22.04/24.04/26.04 or Debian 12/13.' >&2; return 1 ;;
  esac
  destination="${destination%/}"
  if [[ "$destination" != /* || -z "$destination" || -L "$destination" ]]; then
    printf '%s\n' 'BITPIN_INSTALL_DIR must be an absolute, non-root, non-symlink directory.' >&2
    return 1
  fi

  export DEBIAN_FRONTEND=noninteractive GIT_TERMINAL_PROMPT=0
  printf '\n%s\n' 'Installing prerequisites (no API keys are needed yet)…'
  apt-get -o Acquire::Retries=3 update </dev/null
  apt-get -o Acquire::Retries=3 install -y --no-install-recommends ca-certificates curl git util-linux </dev/null
  mkdir -p -- "$(dirname -- "$destination")"
  exec 9>"${destination}.install.lock"
  flock -n 9 || { printf '%s\n' 'Another installation is already running for this directory.' >&2; return 1; }

  if [[ -e "$destination" ]]; then
    if [[ ! -d "$destination/.git" ]] ||
       [[ "$(git -C "$destination" config --get remote.origin.url)" != "$repository" ]]; then
      printf '%s\n' 'Refusing to overwrite an existing directory that is not this repository.' >&2
      return 1
    fi
    if [[ -n "$(git -C "$destination" status --porcelain)" ]] ||
       [[ "$(git -C "$destination" branch --show-current)" != main ]]; then
      printf '%s\n' 'Existing checkout has local changes or is not on main. Preserve your work before updating.' >&2
      return 1
    fi
    printf '%s\n' 'Updating code; existing configuration and Docker volumes are preserved.'
    git -C "$destination" pull --ff-only origin main </dev/null
  else
    git clone --branch main "$repository" "$destination" </dev/null
  fi
  cd -- "$destination"
  printf '\nInstallation directory: %s\n' "$destination"
  # The bootstrap may arrive on stdin via curl | bash; the wizard must read the terminal.
  bash install.sh "$@" </dev/tty
}

main "$@"
