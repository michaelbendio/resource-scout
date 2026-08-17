from __future__ import annotations

import json
import socket
import subprocess
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path
from unittest.mock import patch

from resource_research_agent.server import ResearchHTTPServer
from resource_research_agent.storage import ResearchStore
from resource_research_agent.tailscale import TailscaleAccessError, TailscaleServeManager


def completed(command: list[str], returncode: int = 0, stdout: str = "", stderr: str = ""):
    return subprocess.CompletedProcess(command, returncode, stdout, stderr)


class FakeTailscale:
    def __init__(self, responses: list[subprocess.CompletedProcess[str]]) -> None:
        self.responses = list(responses)
        self.commands: list[list[str]] = []

    def __call__(self, command: list[str]) -> subprocess.CompletedProcess[str]:
        self.commands.append(command)
        if not self.responses:
            raise AssertionError(f"Unexpected Tailscale command: {command}")
        response = self.responses.pop(0)
        return subprocess.CompletedProcess(
            command, response.returncode, response.stdout, response.stderr
        )


def tailscale_status(online: bool = True) -> str:
    return json.dumps({
        "BackendState": "Running" if online else "Stopped",
        "CurrentTailnet": {"Name": "example.org"},
        "Self": {
            "Online": online,
            "DNSName": "research-mac.example.ts.net.",
            "HostName": "Research Mac",
        },
    })


class TailscaleServeManagerTests(unittest.TestCase):
    @patch("resource_research_agent.tailscale.subprocess.run")
    def test_first_use_serve_inherits_the_terminal_without_a_timeout(self, run) -> None:
        run.return_value = completed([])

        TailscaleServeManager._run_subprocess(
            ["/fake/tailscale", "serve", "--bg", "8765"]
        )

        run.assert_called_once_with(
            ["/fake/tailscale", "serve", "--bg", "8765"], text=True, check=False
        )

    def test_configures_private_serve_and_returns_ipad_address(self) -> None:
        runner = FakeTailscale([
            completed([], stdout=tailscale_status()),
            completed([], stdout=json.dumps({
                "TCP": {"443": {"HTTPS": True}},
                "Web": {"research-mac.example.ts.net:443": {
                    "Handlers": {"/": {"Proxy": "http://127.0.0.1:8765"}}
                }},
            })),
            completed([], stdout="Available within your tailnet"),
            completed([], stdout=json.dumps({"Web": {"https:443": {"Handlers": {}}}})),
        ])
        manager = TailscaleServeManager("/fake/tailscale", runner=runner, check_port=False)

        access = manager.configure(8765)

        self.assertEqual("https://research-mac.example.ts.net", access.private_url)
        self.assertEqual("example.org", access.tailnet)
        self.assertEqual(
            ["/fake/tailscale", "serve", "--bg", "8765"], runner.commands[2]
        )
        self.assertFalse(any("funnel" in command and "status" not in command for command in runner.commands))

    def test_refuses_to_change_an_active_public_funnel(self) -> None:
        runner = FakeTailscale([
            completed([], stdout=tailscale_status()),
            completed([], stdout=json.dumps({"Web": {"https:443": {"AllowFunnel": True}}})),
        ])
        manager = TailscaleServeManager("/fake/tailscale", runner=runner, check_port=False)

        with self.assertRaisesRegex(TailscaleAccessError, "Public Tailscale Funnel"):
            manager.configure()

        self.assertEqual(2, len(runner.commands))

    def test_requires_connected_tailscale(self) -> None:
        runner = FakeTailscale([completed([], stdout=tailscale_status(online=False))])
        manager = TailscaleServeManager("/fake/tailscale", runner=runner, check_port=False)

        with self.assertRaisesRegex(TailscaleAccessError, "not connected"):
            manager.configure()

    def test_first_use_error_preserves_https_approval_address(self) -> None:
        approval = "https://login.tailscale.com/admin/feature/serve?node=example"
        runner = FakeTailscale([
            completed([], stdout=tailscale_status()),
            completed([], stdout="{}"),
            completed([], returncode=1, stderr=f"Serve is not enabled. Visit {approval}"),
        ])
        manager = TailscaleServeManager("/fake/tailscale", runner=runner, check_port=False)

        with self.assertRaisesRegex(TailscaleAccessError, approval.replace("?", r"\?")):
            manager.configure()

    def test_refuses_a_port_that_is_already_in_use(self) -> None:
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        try:
            with self.assertRaisesRegex(TailscaleAccessError, "already in use"):
                TailscaleServeManager._ensure_port_available(listener.getsockname()[1])
        finally:
            listener.close()


class TailscaleStatusAPITests(unittest.TestCase):
    def test_status_exposes_private_address_and_decoded_requester(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        try:
            store = ResearchStore(Path(temporary.name) / "research.sqlite3")
            web_dir = Path(__file__).resolve().parent.parent / "web"
            server = ResearchHTTPServer(
                ("127.0.0.1", 0), store, web_dir,
                private_url="https://research-mac.example.ts.net",
            )
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                request = urllib.request.Request(
                    f"http://127.0.0.1:{server.server_address[1]}/api/status",
                    headers={
                        "Tailscale-User-Login": "stephanie@example.org",
                        "Tailscale-User-Name": "=?utf-8?b?U3TDqXBoYW5pZSBUZXN0?=",
                    },
                )
                with urllib.request.urlopen(request, timeout=5) as response:
                    access = json.loads(response.read())["access"]
                self.assertEqual("tailscale", access["mode"])
                self.assertEqual(
                    "https://research-mac.example.ts.net", access["privateUrl"]
                )
                self.assertEqual("Stéphanie Test", access["requester"]["name"])
                self.assertEqual("stephanie@example.org", access["requester"]["login"])
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)
        finally:
            temporary.cleanup()


if __name__ == "__main__":
    unittest.main()
