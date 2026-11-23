"""Exercise the real installer with isolated files and fake deployment commands."""
from __future__ import annotations

from pathlib import Path
import shlex
import shutil
import subprocess
import sys

import pytest
from cryptography.fernet import Fernet

REPOSITORY = Path(__file__).resolve().parents[1]


def _executable(path: Path, source: str) -> None:
    path.write_text(source)
    path.chmod(0o700)


@pytest.fixture()
def installer(tmp_path):
    node = tmp_path / "deploy/clinic-node"
    (node / "install").mkdir(parents=True)
    (node / "scripts").mkdir()
    (node / "proxy").mkdir()
    shutil.copyfile(REPOSITORY / "deploy/clinic-node/install/install.sh", node / "install/install.sh")
    (tmp_path / "core").mkdir()
    shutil.copyfile(REPOSITORY / "core/__init__.py", tmp_path / "core/__init__.py")
    shutil.copyfile(REPOSITORY / "core/settings.py", tmp_path / "core/settings.py")
    (node / "proxy/app.https.host.conf").write_text("listen 80;\nlisten 443 ssl;\n")
    _executable(node / "scripts/generate-pki.sh", '#!/bin/sh\nprintf "pki\\n" >> "$FAKE_CALLS"\n')
    binary = tmp_path / "bin"
    binary.mkdir()
    _executable(binary / "python3", f"#!/bin/sh\nexec {shlex.quote(sys.executable)} \"$@\"\n")
    _executable(binary / "openssl", "#!/bin/sh\nexit 0\n")
    if sys.platform == "darwin":
        # The installer targets Linux; adapt only GNU sed's in-place syntax.
        _executable(binary / "sed", '''#!/bin/sh
if [ "$1" = -i ]; then shift; exec /usr/bin/sed -i '' "$@"; fi
exec /usr/bin/sed "$@"
''')
    _executable(binary / "curl", '#!/bin/sh\nprintf "curl\\n" >> "$FAKE_CALLS"\nexit 0\n')
    _executable(binary / "docker", '''#!/bin/sh
printf 'docker %s\n' "$*" >> "$FAKE_CALLS"
if [ "$1" = run ] && [ "${FAKE_BRIDGE_FAILURE:-}" = true ]; then exit 1; fi
exit 0
''')
    calls = tmp_path / "calls.txt"
    environment = {
        "PATH": f"{binary}:/usr/bin:/bin",
        "HOME": str(tmp_path),
        "FAKE_CALLS": str(calls),
        "PYTHONDONTWRITEBYTECODE": "1",
        "LAN_IP": "127.0.0.1",
        "CLINIC_DATA_DIR": str(tmp_path / "data"),
    }

    def run(existing: dict[str, str] | None = None, **overrides):
        if existing is not None:
            (node / ".env").write_text("".join(f"{key}={value}\n" for key, value in existing.items()))
        return subprocess.run(
            ["/bin/bash", str(node / "install/install.sh")], cwd=tmp_path,
            env={**environment, **overrides}, capture_output=True, text=True, timeout=20,
        )

    return node, calls, run


def _existing_config() -> dict[str, str]:
    return {
        "ENVIRONMENT": "clinic-node", "SECRET_KEY": "SyntheticSigningMaterial0123456789abcdefgh",
        "JWT_SECRET": "SyntheticSigningMaterial0123456789abcdefgh",
        "CLINIC_NODE_LICENSE_SECRET": "SyntheticLicenseMaterial0123456789abcdefgh",
        "CLINIC_NODE_UPDATE_SECRET": "SyntheticUpdateMaterial0123456789abcdefgh",
        "ATTACHMENT_ENCRYPTION_KEY": Fernet.generate_key().decode(),
        "POSTGRES_PASSWORD": "SyntheticDatabaseMaterial0123456789", "DOMAIN": "sante-locale",
        "HTTP_PORT": "80", "HTTPS_PORT": "443", "CLINIC_NODE_NETWORK": "bridge",
        "CLINIC_NODE_ALLOW_HOST_NETWORK": "false",
    }


def test_fresh_installer_generates_one_signing_key_and_keeps_bridge(installer):
    node, calls, run = installer
    result = run(FAKE_BRIDGE_FAILURE="true")
    assert result.returncode == 0, result.stdout + result.stderr
    config = dict(line.split("=", 1) for line in (node / ".env").read_text().splitlines() if "=" in line)
    assert config["SECRET_KEY"] == config["JWT_SECRET"]
    assert config["CLINIC_NODE_NETWORK"] == "bridge"
    assert config["CLINIC_NODE_ALLOW_HOST_NETWORK"] == "false"
    assert len({config[name] for name in ("SECRET_KEY", "CLINIC_NODE_LICENSE_SECRET", "CLINIC_NODE_UPDATE_SECRET", "ATTACHMENT_ENCRYPTION_KEY")}) == 4
    assert "docker run " not in calls.read_text()
    assert "compose.host.yml" not in calls.read_text()


@pytest.mark.parametrize("bad", ["alias-mismatch", "ATTACHMENT_ENCRYPTION_KEY", "CLINIC_NODE_LICENSE_SECRET", "CLINIC_NODE_UPDATE_SECRET"])
def test_existing_key_problems_preserve_configuration_before_deployment(installer, bad):
    node, calls, run = installer
    config = _existing_config()
    if bad == "alias-mismatch":
        config["JWT_SECRET"] = "DifferentSyntheticSigningMaterial0123456789"
    else:
        config.pop(bad)
    expected = "".join(f"{key}={value}\n" for key, value in config.items())
    result = run(config, HTTP_PORT="8088")
    assert result.returncode != 0
    assert "recovery" in (result.stdout + result.stderr).lower()
    assert (node / ".env").read_text() == expected
    assert "pki" not in calls.read_text()
    assert "up -d" not in calls.read_text()


def test_host_network_requires_explicit_acknowledgment_without_rewriting_env(installer):
    node, calls, run = installer
    config = _existing_config()
    config["CLINIC_NODE_NETWORK"] = "host"
    expected = "".join(f"{key}={value}\n" for key, value in config.items())
    result = run(config)
    assert result.returncode != 0
    assert "CLINIC_NODE_ALLOW_HOST_NETWORK" in result.stdout + result.stderr
    assert (node / ".env").read_text() == expected
    assert "pki" not in calls.read_text()
    assert "up -d" not in calls.read_text()


def test_existing_approved_host_network_preserves_keys(installer):
    node, calls, run = installer
    config = _existing_config()
    config.update(CLINIC_NODE_NETWORK="host", CLINIC_NODE_ALLOW_HOST_NETWORK="true")
    expected = "".join(f"{key}={value}\n" for key, value in config.items())
    result = run(config)
    assert result.returncode == 0, result.stdout + result.stderr
    assert (node / ".env").read_text() == expected
    assert "compose.host.yml" in calls.read_text()


def test_legacy_auto_mode_keeps_bridge_without_network_probe(installer):
    _, calls, run = installer
    config = _existing_config()
    config["CLINIC_NODE_NETWORK"] = "auto"
    result = run(config, FAKE_BRIDGE_FAILURE="true")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "docker run " not in calls.read_text()
    assert "compose.host.yml" not in calls.read_text()


def test_fresh_host_without_acknowledgment_creates_no_configuration(installer):
    node, calls, run = installer
    result = run(CLINIC_NODE_NETWORK="host")
    assert result.returncode != 0
    assert not (node / ".env").exists()
    assert "pki" not in calls.read_text()


def test_ambient_key_does_not_fill_a_missing_existing_key(installer):
    node, _, run = installer
    config = _existing_config()
    key = config.pop("ATTACHMENT_ENCRYPTION_KEY")
    expected = "".join(f"{name}={value}\n" for name, value in config.items())
    result = run(config, ATTACHMENT_ENCRYPTION_KEY=key)
    assert result.returncode != 0
    assert (node / ".env").read_text() == expected


def test_existing_ports_are_preserved_without_an_explicit_override(installer):
    node, _, run = installer
    config = _existing_config()
    config.update(HTTP_PORT="8088", HTTPS_PORT="8443")
    expected = "".join(f"{name}={value}\n" for name, value in config.items())
    result = run(config)
    assert result.returncode == 0, result.stdout + result.stderr
    assert (node / ".env").read_text() == expected


@pytest.mark.parametrize("name", ["SECRET_KEY", "CLINIC_NODE_LICENSE_SECRET", "CLINIC_NODE_UPDATE_SECRET"])
@pytest.mark.parametrize("weak", ["short-value", "default-material-0123456789abcdefghijklmno"])
def test_weak_existing_keys_are_rejected_before_configuration_mutation(installer, name, weak):
    node, calls, run = installer
    config = _existing_config()
    config[name] = weak
    if name == "SECRET_KEY":
        config["JWT_SECRET"] = weak
    expected = "".join(f"{key}={value}\n" for key, value in config.items())
    result = run(config, HTTP_PORT="8088")
    assert result.returncode != 0
    assert "recovery" in (result.stdout + result.stderr).lower()
    assert (node / ".env").read_text() == expected
    assert "pki" not in calls.read_text()
    assert "up -d" not in calls.read_text()
