from __future__ import annotations

import json
import shutil
import socket
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


class TailscaleAccessError(RuntimeError):
    """Raised when private Tailscale access cannot be configured safely."""


@dataclass(frozen=True)
class TailscaleAccess:
    private_url: str
    tailnet: str
    hostname: str
    port: int


CommandRunner = Callable[[list[str]], subprocess.CompletedProcess[str]]


class TailscaleServeManager:
    """Configures a tailnet-only HTTPS proxy to a localhost app."""

    def __init__(
        self,
        executable: str | None = None,
        runner: CommandRunner | None = None,
        check_port: bool = True,
    ) -> None:
        self.executable = executable or self._find_executable()
        self.runner = runner or self._run_subprocess
        self.check_port = check_port

    @staticmethod
    def _find_executable() -> str:
        discovered = shutil.which("tailscale")
        if discovered:
            return discovered
        app_binary = Path("/Applications/Tailscale.app/Contents/MacOS/Tailscale")
        if app_binary.is_file():
            return str(app_binary)
        raise TailscaleAccessError(
            "Tailscale is not installed. Install it on this Mac, sign in, and try again."
        )

    @staticmethod
    def _run_subprocess(command: list[str]) -> subprocess.CompletedProcess[str]:
        if command[1:3] == ["serve", "--bg"]:
            # First use can wait while Tailscale prints an HTTPS approval link.
            # Inherit the terminal so the user can see and act on that link.
            return subprocess.run(command, text=True, check=False)
        return subprocess.run(command, capture_output=True, text=True, timeout=30, check=False)

    def _run(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        try:
            return self.runner([self.executable, *arguments])
        except (OSError, subprocess.SubprocessError) as error:
            raise TailscaleAccessError(f"Tailscale could not be reached: {error}") from error

    @staticmethod
    def _contains_public_funnel(value: Any) -> bool:
        """The Funnel status JSON also includes tailnet-only Serve routes."""
        if isinstance(value, dict):
            if value.get("AllowFunnel") is True:
                return True
            return any(TailscaleServeManager._contains_public_funnel(item) for item in value.values())
        if isinstance(value, list):
            return any(TailscaleServeManager._contains_public_funnel(item) for item in value)
        return False

    def _json(self, *arguments: str) -> dict[str, Any]:
        completed = self._run(*arguments)
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout).strip()
            raise TailscaleAccessError(detail or "Tailscale returned an unexpected error.")
        try:
            value = json.loads(completed.stdout or "{}")
        except json.JSONDecodeError as error:
            raise TailscaleAccessError("Tailscale returned an unreadable status response.") from error
        if not isinstance(value, dict):
            raise TailscaleAccessError("Tailscale returned an unexpected status response.")
        return value

    @staticmethod
    def _ensure_port_available(port: int) -> None:
        probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            probe.bind(("127.0.0.1", port))
        except OSError as error:
            raise TailscaleAccessError(
                f"Port {port} is already in use. Stop the currently running Research Agent "
                "with Control-C, then run this launcher again."
            ) from error
        finally:
            probe.close()

    def configure(self, port: int = 8765) -> TailscaleAccess:
        if not 1 <= port <= 65535:
            raise TailscaleAccessError("The port must be between 1 and 65535.")

        status = self._json("status", "--json")
        own_device = status.get("Self") if isinstance(status.get("Self"), dict) else {}
        if status.get("BackendState") != "Running" or not own_device.get("Online"):
            raise TailscaleAccessError(
                "Tailscale is not connected on this Mac. Open Tailscale, connect it, and try again."
            )

        funnel_status = self._json("funnel", "status", "--json")
        if self._contains_public_funnel(funnel_status):
            raise TailscaleAccessError(
                "Public Tailscale Funnel is currently configured on this Mac. This private launcher "
                "will not change or share a Funnel configuration. Disable Funnel first, then try again."
            )

        if self.check_port:
            self._ensure_port_available(port)

        dns_name = str(own_device.get("DNSName") or "").rstrip(".")
        if not dns_name:
            raise TailscaleAccessError(
                "Tailscale did not provide this Mac's private DNS name. Enable MagicDNS for the tailnet "
                "before using private HTTPS access."
            )

        configured = self._run("serve", "--bg", str(port))
        if configured.returncode != 0:
            detail = (configured.stderr or configured.stdout).strip()
            suffix = f"\n\nTailscale said:\n{detail}" if detail else ""
            raise TailscaleAccessError(
                "Tailscale Serve could not be enabled. On first use, Tailscale may provide a web address "
                "where you can approve HTTPS. Complete that step, then run this launcher again." + suffix
            )

        if not self._json("serve", "status", "--json"):
            raise TailscaleAccessError(
                "Tailscale reported success but no private Serve route is active. Try the launcher again."
            )

        current_tailnet = status.get("CurrentTailnet")
        tailnet = str(current_tailnet.get("Name") or "") if isinstance(current_tailnet, dict) else ""
        return TailscaleAccess(
            private_url=f"https://{dns_name}",
            tailnet=tailnet,
            hostname=str(own_device.get("HostName") or dns_name),
            port=port,
        )
