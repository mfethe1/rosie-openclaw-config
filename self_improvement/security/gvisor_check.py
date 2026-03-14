#!/usr/bin/env python3
"""
gVisor Integration Check
Checks runsc installation, Docker daemon config, and generates compose overrides.
"""
import sys
import json
import os
import subprocess
import shutil
import platform
from pathlib import Path


DOCKER_DAEMON_JSON = Path("/etc/docker/daemon.json")

INSTALL_GUIDE = {
    "macos": {
        "note": "gVisor (runsc) does not run natively on macOS. It runs inside Linux VMs (e.g. via Docker Desktop or Lima).",
        "steps": [
            "# Option A: Use Lima VM",
            "brew install lima",
            "limactl start --name=gvisor template://ubuntu",
            "limactl shell gvisor -- sudo apt-get install -y apt-transport-https ca-certificates curl gnupg",
            "limactl shell gvisor -- curl -fsSL https://gvisor.dev/archive.key | sudo gpg --dearmor -o /usr/share/keyrings/gvisor-archive-keyring.gpg",
            "limactl shell gvisor -- echo 'deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/gvisor-archive-keyring.gpg] https://storage.googleapis.com/gvisor/releases release main' | sudo tee /etc/apt/sources.list.d/gvisor.list > /dev/null",
            "limactl shell gvisor -- sudo apt-get update && sudo apt-get install -y runsc",
            "limactl shell gvisor -- sudo runsc install",
            "limactl shell gvisor -- sudo systemctl reload docker",
            "",
            "# Option B: Docker Desktop (if already running Linux containers)",
            "# Enable gVisor in Docker Desktop > Settings > Features in Development",
        ]
    },
    "linux": {
        "steps": [
            "sudo apt-get update && sudo apt-get install -y apt-transport-https ca-certificates curl gnupg",
            "curl -fsSL https://gvisor.dev/archive.key | sudo gpg --dearmor -o /usr/share/keyrings/gvisor-archive-keyring.gpg",
            "echo \"deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/gvisor-archive-keyring.gpg] https://storage.googleapis.com/gvisor/releases release main\" | sudo tee /etc/apt/sources.list.d/gvisor.list > /dev/null",
            "sudo apt-get update && sudo apt-get install -y runsc",
            "sudo runsc install",
            "sudo systemctl reload docker",
        ]
    }
}

DOCKER_COMPOSE_SNIPPET = """\
# docker-compose.override.yml — gVisor runtime
# Add to your project's docker-compose.override.yml or merge into docker-compose.yml
version: "3.8"
services:
  # Apply to each service that should run under gVisor
  your_service:
    runtime: runsc
"""


def run_cmd(cmd: list) -> tuple:
    """Run command, return (returncode, stdout, stderr)."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except FileNotFoundError:
        return -1, "", f"Command not found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"


def check_runsc_installed() -> dict:
    path = shutil.which("runsc")
    if not path:
        return {"installed": False, "path": None, "version": None}
    rc, out, err = run_cmd(["runsc", "--version"])
    version = out if rc == 0 else err
    return {"installed": True, "path": path, "version": version}


def check_docker_daemon() -> dict:
    result = {"config_exists": False, "gvisor_runtime_configured": False, "config_path": str(DOCKER_DAEMON_JSON), "config": None}
    if DOCKER_DAEMON_JSON.exists():
        result["config_exists"] = True
        try:
            with open(DOCKER_DAEMON_JSON) as f:
                cfg = json.load(f)
            result["config"] = cfg
            runtimes = cfg.get("runtimes", {})
            result["gvisor_runtime_configured"] = "runsc" in runtimes
        except (json.JSONDecodeError, PermissionError) as e:
            result["error"] = str(e)
    return result


def check_docker_running() -> dict:
    rc, out, err = run_cmd(["docker", "info", "--format", "{{.ServerVersion}}"])
    return {"running": rc == 0, "version": out if rc == 0 else None}


def do_check() -> dict:
    os_type = platform.system().lower()
    runsc = check_runsc_installed()
    daemon = check_docker_daemon()
    docker = check_docker_running()

    result = {
        "os": os_type,
        "runsc": runsc,
        "docker": docker,
        "daemon_config": daemon,
        "docker_compose_snippet": DOCKER_COMPOSE_SNIPPET,
        "status": "ok",
        "warnings": [],
        "actions_needed": []
    }

    if not runsc["installed"]:
        result["status"] = "not_installed"
        result["actions_needed"].append("runsc not found — run install-guide for instructions")
    else:
        if not daemon["config_exists"]:
            result["warnings"].append("/etc/docker/daemon.json not found")
            result["actions_needed"].append("Create /etc/docker/daemon.json with gVisor runtime entry (see install-guide)")
        elif not daemon["gvisor_runtime_configured"]:
            result["warnings"].append("runsc installed but not configured as Docker runtime")
            result["actions_needed"].append("Run: sudo runsc install && sudo systemctl reload docker")

    if not docker["running"]:
        result["warnings"].append("Docker daemon not running or not accessible")

    if os_type == "darwin":
        result["warnings"].append("gVisor runs in Linux VMs on macOS — native support not available")

    return result


def do_install_guide() -> dict:
    os_type = platform.system().lower()
    if os_type == "darwin":
        guide = INSTALL_GUIDE["macos"]
    else:
        guide = INSTALL_GUIDE["linux"]

    return {
        "os": os_type,
        "guide": guide,
        "docker_compose_snippet": DOCKER_COMPOSE_SNIPPET,
        "daemon_json_example": {
            "runtimes": {
                "runsc": {
                    "path": "/usr/local/bin/runsc"
                }
            }
        }
    }


def run_tests():
    print("Running gvisor_check tests...")
    passed = 0
    failed = 0

    def check(name, cond, detail=""):
        nonlocal passed, failed
        status = "PASS" if cond else "FAIL"
        print(f"  [{status}] {name}" + (f": {detail}" if detail else ""))
        if cond:
            passed += 1
        else:
            failed += 1

    # Test 1: check() returns expected keys
    result = do_check()
    check("check() returns os key", "os" in result)
    check("check() returns runsc key", "runsc" in result)
    check("check() returns docker key", "docker" in result)
    check("check() returns daemon_config key", "daemon_config" in result)
    check("check() returns docker_compose_snippet", "docker_compose_snippet" in result)
    check("check() returns status", result.get("status") in ("ok", "not_installed"))

    # Test 2: runsc installed check has correct shape
    r = check_runsc_installed()
    check("runsc check has installed key", "installed" in r)
    check("runsc check has path key", "path" in r)
    check("runsc check has version key", "version" in r)

    # Test 3: install_guide returns guide for current OS
    guide = do_install_guide()
    check("install_guide returns guide", "guide" in guide)
    check("install_guide returns compose snippet", "docker_compose_snippet" in guide)
    check("install_guide returns daemon_json_example", "daemon_json_example" in guide)

    # Test 4: compose snippet contains 'runsc'
    check("Compose snippet mentions runsc", "runsc" in DOCKER_COMPOSE_SNIPPET)

    # Test 5: macOS guide mentions lima or Docker Desktop
    import gvisor_check as gc_mod
    old_sys = platform.system
    platform.system = lambda: "Darwin"
    mac_guide = gc_mod.do_install_guide()
    platform.system = old_sys
    check("macOS guide steps present", len(mac_guide["guide"].get("steps", [])) > 0)

    # Test 6: Linux guide has apt-get steps
    platform.system = lambda: "Linux"
    lin_guide = gc_mod.do_install_guide()
    platform.system = old_sys
    has_apt = any("apt-get" in s for s in lin_guide["guide"].get("steps", []))
    check("Linux guide has apt-get steps", has_apt)

    print(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 gvisor_check.py check")
        print("       python3 gvisor_check.py install-guide")
        print("       python3 gvisor_check.py --test")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "--test":
        success = run_tests()
        sys.exit(0 if success else 1)

    elif cmd == "check":
        result = do_check()
        print(json.dumps(result, indent=2))
        sys.exit(0 if result["status"] == "ok" else 1)

    elif cmd == "install-guide":
        result = do_install_guide()
        print(json.dumps(result, indent=2))

    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
