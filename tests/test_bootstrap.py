"""Run the real shell bootstrap, Git and a controlling terminal; fake only host package installation."""

import os
import re
import select
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "linux", reason="Linux installer and controlling terminal")
ROOT = Path(__file__).resolve().parents[1]


def run_terminal(command, env, *, input_bytes=b"\n"):
    import pty

    pid, fd = pty.fork()
    if pid == 0:
        os.execvpe(command[0], command, env)
    output = bytearray()
    deadline = time.monotonic() + 20
    os.write(fd, input_bytes)
    try:
        while time.monotonic() < deadline:
            if select.select([fd], [], [], 0.1)[0]:
                try:
                    chunk = os.read(fd, 65536)
                except OSError:
                    break
                if not chunk:
                    break
                output.extend(chunk)
        else:
            os.kill(pid, 9)
            pytest.fail("Bootstrap did not finish: " + output.decode(errors="replace"))
    finally:
        os.close(fd)
        _, status = os.waitpid(pid, 0)
    return os.waitstatus_to_exitcode(status), output.decode(errors="replace")


@pytest.fixture
def bootstrap_environment(tmp_path):
    git = shutil.which("git")
    assert git, "The Linux installer tests require Git"
    source = tmp_path / "source"
    source.mkdir()
    subprocess.run([git, "init", "--initial-branch=main", str(source)], check=True, capture_output=True)
    (source / ".gitignore").write_text(".env\n.secrets.env\ninstalled\n")
    (source / "install.sh").write_text(
        '#!/bin/bash\nset -eu\n[[ -t 0 ]] || exit 30\nread -r pause\nprintf "ok" > installed\n'
    )
    subprocess.run([git, "-C", str(source), "add", "."], check=True)
    subprocess.run(
        [
            git,
            "-C",
            str(source),
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.com",
            "commit",
            "-m",
            "fixture",
        ],
        check=True,
        capture_output=True,
    )
    config = tmp_path / "gitconfig"
    config.write_text(
        f'[url "file://{source}"]\n\tinsteadOf = https://github.com/Erfouni/bitpin-ai-connector.git\n'
    )
    binaries = tmp_path / "bin"
    binaries.mkdir()
    for name, script in {
        "id": '#!/bin/sh\nif [ "$1" = -u ]; then echo 0; else /usr/bin/id "$@"; fi\n',
        "apt-get": '#!/bin/sh\n[ "${FAIL_APT:-}" != 1 ] || exit 42\nexit 0\n',
    }.items():
        file = binaries / name
        file.write_text(script)
        file.chmod(0o755)
    env = {
        **os.environ,
        "PATH": str(binaries) + os.pathsep + os.environ["PATH"],
        "GIT_CONFIG_GLOBAL": str(config),
        "GIT_CONFIG_NOSYSTEM": "1",
        "BITPIN_INSTALL_DIR": str(tmp_path / "installed connector"),
    }
    return env, Path(env["BITPIN_INSTALL_DIR"])


def test_piped_bootstrap_keeps_tty_and_preserves_existing_secrets(bootstrap_environment):
    env, destination = bootstrap_environment
    command = ["bash", "-o", "pipefail", "-c", 'cat "$1" | bash', "test", str(ROOT / "bootstrap.sh")]
    code, output = run_terminal(command, env)
    assert code == 0, output
    assert (destination / "installed").read_text() == "ok"
    (destination / ".env").write_text("TRADING_ENABLED=false\n")
    (destination / ".secrets.env").write_text("BITPIN_API_KEY=offline-fixture\n")
    code, output = run_terminal(command, env)
    assert code == 0, output
    assert (destination / ".env").read_text() == "TRADING_ENABLED=false\n"
    assert (destination / ".secrets.env").read_text() == "BITPIN_API_KEY=offline-fixture\n"


def test_bootstrap_does_not_overwrite_an_unrelated_directory(bootstrap_environment):
    env, destination = bootstrap_environment
    destination.mkdir()
    (destination / "keep.txt").write_text("keep me")
    code, output = run_terminal(["bash", str(ROOT / "bootstrap.sh")], env)
    assert code != 0
    assert "existing" in output.lower(), output
    assert (destination / "keep.txt").read_text() == "keep me"
    assert not (destination / "installed").exists()


def test_package_failure_stops_before_checkout_or_configuration(bootstrap_environment):
    env, destination = bootstrap_environment
    code, output = run_terminal(["bash", str(ROOT / "bootstrap.sh")], {**env, "FAIL_APT": "1"})
    assert code == 42, output
    assert not destination.exists()


def test_bootstrap_refuses_noninteractive_install_before_changes(bootstrap_environment):
    env, destination = bootstrap_environment
    result = subprocess.run(
        ["bash", str(ROOT / "bootstrap.sh")],
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        start_new_session=True,
        timeout=10,
    )
    assert result.returncode != 0
    assert "terminal" in result.stderr.lower(), result.stderr
    assert not destination.exists()


def test_documented_one_command_installs_downloader_before_fetching_and_keeps_tty(bootstrap_environment):
    env, destination = bootstrap_environment
    binaries = Path(env["PATH"].split(os.pathsep)[0])
    ready = binaries / "curl-ready"
    (binaries / "apt-get").write_text(
        '#!/bin/sh\ncase " $* " in *" curl "*) touch "$DOWNLOADER_READY" ;; esac\n'
    )
    for name, text in {
        "curl": '#!/bin/sh\n[ -f "$DOWNLOADER_READY" ] || exit 44\ncat "$BOOTSTRAP_SOURCE"\n',
        "sudo": '#!/bin/sh\nexec "$@"\n',
    }.items():
        path = binaries / name
        path.write_text(text)
        path.chmod(0o755)
    env.update(DOWNLOADER_READY=str(ready), BOOTSTRAP_SOURCE=str(ROOT / "bootstrap.sh"))
    assert subprocess.run([str(binaries / "curl")], env=env, capture_output=True).returncode == 44
    commands = [
        re.search(r"```bash\n([^\n]+)", (ROOT / name).read_text()).group(1)
        for name in ["README.md", "README.en.md"]
    ]
    assert commands[0] == commands[1], "Both languages must document the same tested installation command"
    code, output = run_terminal(["bash", "-c", commands[0]], env)
    assert code == 0, output
    assert ready.exists()
    assert (destination / "installed").read_text() == "ok"


@pytest.fixture
def host_environment(tmp_path):
    """Fake package/service boundaries; never write to the runner's /etc or install host packages."""
    binaries = tmp_path / "bin"
    binaries.mkdir()
    state = tmp_path / "state"
    state.mkdir()
    driver = binaries / "driver"
    driver.write_text(
        f"#!{sys.executable}\n"
        + """
import os, sys
from pathlib import Path
state = Path(os.environ['HOST_STATE'])
name = Path(sys.argv[0]).name
args = sys.argv[1:]
if name == 'id': print('0')
elif name == 'dpkg': print('amd64')
elif name == 'apt-cache':
    print('  Candidate: ' + ('5:29.2.1-1' if (state / 'repository').exists() else '(none)'))
elif name == 'dpkg-query':
    installed = (state / (args[-1] + '.installed')).exists()
    if installed: print('install ok installed')
    sys.exit(0 if installed else 1)
elif name == 'apt-get':
    with (state / 'apt.log').open('a') as file: file.write(' '.join(args) + '\\n')
    if 'install' in args:
        if 'docker-ce' in args and os.environ.get('FAIL_DOCKER_APT'): sys.exit(42)
        for package in args[args.index('install')+1:]:
            if not package.startswith('-'): (state / (package + '.installed')).touch()
elif name == 'curl':
    assert 'https://download.docker.com/linux/' in ' '.join(args)
    Path(args[args.index('-o')+1]).write_text('fake test key')
elif name == 'install':
    if '-d' not in args: (state / Path(args[-1]).name).write_bytes(Path(args[-2]).read_bytes())
elif name == 'tee':
    value = sys.stdin.read()
    (state / Path(args[-1]).name).write_text(value)
    print(value, end='')
elif name == 'systemctl':
    assert args == ['enable', '--now', 'docker']
    (state / 'running').touch()
elif name == 'docker':
    if args == ['info']: sys.exit(0 if (state / 'running').exists() else 1)
    if args[:2] == ['compose','version']:
        if not (state / 'docker-compose-plugin.installed').exists(): sys.exit(1)
        print('2.30.3')
    elif args[:2] == ['buildx','version']:
        sys.exit(0 if (state / 'docker-buildx-plugin.installed').exists() else 1)
    elif args == ['--version']:
        sys.exit(0 if (state / 'docker-ce.installed').exists() else 1)
    else: raise AssertionError(args)
else: raise AssertionError(name)
"""
    )
    driver.chmod(0o755)
    for name in [
        "id",
        "dpkg",
        "dpkg-query",
        "apt-get",
        "apt-cache",
        "curl",
        "install",
        "tee",
        "systemctl",
        "docker",
    ]:
        (binaries / name).symlink_to(driver)
    return {
        **os.environ,
        "PATH": str(binaries) + os.pathsep + os.environ["PATH"],
        "HOST_STATE": str(state),
    }, state


def run_host(env):
    return subprocess.run(
        ["bash", str(ROOT / "scripts" / "prepare-host.sh")],
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=20,
    )


def test_fresh_host_installs_docker_compose_and_starts_daemon_without_prompts(host_environment):
    env, state = host_environment
    result = run_host(env)
    assert result.returncode == 0, result.stderr
    assert (state / "docker-ce.installed").exists()
    assert (state / "docker-compose-plugin.installed").exists()
    assert (state / "docker-buildx-plugin.installed").exists()
    assert (state / "running").exists()
    assert "Signed-By: /etc/apt/keyrings/bitpin-docker.asc" in (state / "bitpin-docker.sources").read_text()


def test_ready_docker_is_reused_without_package_changes(host_environment):
    env, state = host_environment
    for name in [
        "running",
        "docker-ce.installed",
        "docker-compose-plugin.installed",
        "docker-buildx-plugin.installed",
    ]:
        (state / name).touch()
    result = run_host(env)
    assert result.returncode == 0, result.stderr
    assert not (state / "apt.log").exists()


def test_conflicting_engine_is_reported_instead_of_removed(host_environment):
    env, state = host_environment
    (state / "docker.io.installed").touch()
    result = run_host(env)
    assert result.returncode != 0
    assert "docker.io" in result.stderr
    assert not (state / "docker-ce.installed").exists()
    assert not (state / "running").exists()


def test_docker_package_failure_does_not_start_daemon(host_environment):
    env, state = host_environment
    result = run_host({**env, "FAIL_DOCKER_APT": "1"})
    assert result.returncode == 42, result.stderr
    assert not (state / "running").exists()


def test_preconfigured_docker_repository_is_reused_without_a_second_signing_key(host_environment):
    env, state = host_environment
    (state / "repository").touch()
    result = run_host(env)
    assert result.returncode == 0, result.stderr
    assert (state / "docker-ce.installed").exists()
    assert not (state / "bitpin-docker.sources").exists()
    assert not (state / "bitpin-docker.asc").exists()
