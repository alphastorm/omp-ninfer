"""Fixture coverage; no launchd job, real SSH login or GPU is touched."""
import contextlib
import http.server
import io
import json
import os
from pathlib import Path
import plistlib
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
if os.name != "nt":
    import mac_tunnel as tunnel
import doctor


@unittest.skipIf(os.name == "nt", "macOS/POSIX lifecycle fixtures")
class MacTunnelTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.p = tunnel.paths(self.temp.name)
        tunnel.private_root(self.p)
        self.key = Path(self.temp.name) / "existing.key"
        self.key.write_text("fixture-not-a-credential")
        self.key.chmod(0o600)
        self.config = {"schema_version": 1, "label": tunnel.LABEL, "destination": "owner@example.invalid",
                       "local_port": 18089, "remote_port": 18089, "ssh_port": 22,
                       "key_file": str(self.key), "identity_file": None}
        self.p["plist"].parent.mkdir(parents=True)
        tunnel.save(self.p["config"], self.config)
        tunnel.atomic(self.p["plist"], plistlib.dumps(tunnel.plist(self.p)))

    def test_plist_keeps_supervisor_alive_without_secrets_or_shell(self):
        value = tunnel.plist(self.p)
        self.assertTrue(value["KeepAlive"] and value["RunAtLoad"])
        self.assertEqual(value["ThrottleInterval"], 10)
        self.assertEqual(value["ProgramArguments"][1:], [str(self.p["worker"]), "_run"])
        self.assertEqual(value["Umask"], 0o077)
        self.assertNotIn(self.key.read_text(), repr(value))
        self.assertNotIn("EnvironmentVariables", value)

    def test_ssh_is_strict_nonmultiplexed_loopback_only(self):
        command = tunnel.ssh_command(self.config)
        self.assertEqual(command[:4], ["/usr/bin/ssh", "-F", "/dev/null", "-NT"])
        for option in ("ControlMaster=no", "ControlPersist=no", "BatchMode=yes", "StrictHostKeyChecking=yes",
                       "ExitOnForwardFailure=yes", "ServerAliveInterval=30", "ServerAliveCountMax=3", "GatewayPorts=no"):
            self.assertIn(option, command)
        self.assertIn("127.0.0.1:18089:127.0.0.1:18089", command)
        self.assertEqual(command[-1], "owner@example.invalid")
        self.assertNotIn(str(self.key), command)
        self.config["identity_file"] = str(Path(self.temp.name) / "identity")
        self.assertIn("IdentitiesOnly=yes", tunnel.ssh_command(self.config))

    def test_destination_and_ports_reject_option_or_command_injection(self):
        for value in ("-oProxyCommand=bad", "user@host x", "user@host;touch", "alias", "user@@host", "user@host\n"):
            with self.subTest(value=value), self.assertRaises(tunnel.TunnelError):
                tunnel.validate({**self.config, "destination": value})
        for value in (0, 65536, True, "22"):
            with self.subTest(value=value), self.assertRaises(tunnel.TunnelError):
                tunnel.validate({**self.config, "ssh_port": value})

    def test_install_stages_disabled_and_does_not_copy_bearer(self):
        with patch.object(tunnel, "job", return_value={"loaded": False}), patch.object(tunnel, "checked") as checked:
            tunnel.install(self.p, self.config)
        checked.assert_called_once_with("disable", tunnel.domain() + "/" + tunnel.LABEL)
        self.assertEqual(self.p["worker"].read_bytes(), Path(tunnel.__file__).read_bytes())
        self.assertTrue(tunnel.private_file(self.p["config"]))
        self.assertTrue(tunnel.private_file(self.p["plist"]))
        self.assertNotIn(self.key.read_text(), self.p["config"].read_text())
        self.assertEqual(self.key.read_text(), "fixture-not-a-credential")

    def test_install_refuses_live_agent_or_foreign_plist(self):
        with patch.object(tunnel, "job", return_value={"loaded": True}), self.assertRaises(tunnel.TunnelError):
            tunnel.install(self.p, self.config)
        tunnel.atomic(self.p["plist"], plistlib.dumps({"Label": "foreign"}))
        with self.assertRaises(tunnel.TunnelError):
            tunnel.install(self.p, self.config)

    def test_start_enables_then_bootstraps_only_when_absent(self):
        with patch.object(tunnel, "job", return_value={"loaded": False}), patch.object(tunnel, "checked") as checked:
            tunnel.start(self.p)
        self.assertEqual([call.args[0] for call in checked.call_args_list], ["enable", "bootstrap"])
        with patch.object(tunnel, "job", return_value={"loaded": True}), patch.object(tunnel, "checked") as checked:
            tunnel.start(self.p)
        checked.assert_called_once_with("enable", tunnel.domain() + "/" + tunnel.LABEL)

    def test_stop_disables_before_unloading_and_removes_stale_runtime(self):
        tunnel.save(self.p["runtime"], {"status": "forwarding"})
        with patch.object(tunnel, "job", side_effect=[{"loaded": True}, {"loaded": False}]), patch.object(tunnel, "checked") as checked:
            tunnel.stop(self.p)
        self.assertEqual([call.args[0] for call in checked.call_args_list], ["disable", "bootout"])
        self.assertFalse(self.p["runtime"].exists())

    def test_uninstall_preserves_credentials_client_settings_and_unowned_files(self):
        extra = self.p["root"] / "owner-file"
        extra.write_text("keep")
        with patch.object(tunnel, "job", return_value={"loaded": False}), patch.object(tunnel, "checked"):
            tunnel.uninstall(self.p)
            tunnel.uninstall(self.p)
        self.assertTrue(self.key.exists() and extra.exists())
        self.assertFalse(self.p["plist"].exists() or self.p["config"].exists())

    def test_uninstall_never_deletes_after_bootout_failure(self):
        with patch.object(tunnel, "job", return_value={"loaded": True}), \
             patch.object(tunnel, "checked", side_effect=tunnel.TunnelError("launchctl operation failed")), \
             self.assertRaises(tunnel.TunnelError):
            tunnel.uninstall(self.p)
        self.assertTrue(self.p["plist"].exists() and self.p["config"].exists())

    def test_foreign_pid_and_stale_runtime_never_report_owned_listener(self):
        tunnel.save(self.p["runtime"], {"supervisor_pid": 42, "status": "forwarding", "ssh_pid": 43})
        with patch.object(tunnel, "job", return_value={"loaded": True, "pid": 99}), patch.object(tunnel, "listener_owned") as listener:
            result = tunnel.snapshot(self.p)
            listener.assert_not_called()
        self.assertFalse(result["listener_owned"])
        with patch.object(tunnel, "job", return_value={"loaded": True, "pid": 42}), patch.object(tunnel, "listener_owned", return_value=False):
            result = tunnel.snapshot(self.p)
        self.assertEqual(result["status"], "connecting")
        with patch.object(tunnel, "job", return_value={"loaded": True, "pid": 42}), patch.object(tunnel, "listener_owned", return_value=True):
            result = tunnel.snapshot(self.p)
        self.assertTrue(result["listener_owned"])
        self.assertNotIn(self.config["destination"], json.dumps(result))
        self.assertNotIn(str(self.key), json.dumps(result))

    def test_listener_fixture_rejects_foreign_owner_or_wildcard(self):
        for text, expected in (("p43\nn127.0.0.1:18089\n", True), ("p99\nn127.0.0.1:18089\n", False),
                               ("p43\nn*:18089\n", False), ("p43\nn127.0.0.1:18089\np99\nn[::1]:18089\n", False), ("", False)):
            with patch.object(tunnel.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, text)):
                self.assertEqual(tunnel.listener_owned(18089, 43), expected)

    def test_retry_is_exponential_capped_and_resets_after_stability(self):
        delay = 1
        delays = [delay]
        for _ in range(8):
            delay = tunnel.retry_delay(delay, 0)
            delays.append(delay)
        self.assertEqual(delays, [1, 2, 4, 8, 16, 32, 60, 60, 60])
        self.assertEqual(tunnel.retry_delay(60, 60), 1)

    def test_supervisor_retries_and_interrupt_terminates_owned_child(self):
        first = Mock(pid=42, returncode=255)
        first.poll.return_value = 255
        second = Mock(pid=43, returncode=None)
        second.poll.return_value = None
        event = Mock()
        event.is_set.return_value = False
        # Backoff wait; second child's wait sees stop, then loop observes it.
        event.wait.side_effect = [False, True]
        event.is_set.side_effect = [False, False, False, True]
        with patch.object(tunnel.threading, "Event", return_value=event), patch.object(tunnel.signal, "signal"), \
             patch.object(tunnel.subprocess, "Popen", side_effect=[first, second]) as popen:
            tunnel.supervise(self.p)
        self.assertEqual(popen.call_count, 2)
        second.terminate.assert_called_once()
        second.wait.assert_called_once_with(timeout=5)
        self.assertEqual(json.loads(self.p["runtime"].read_text())["status"], "stopped")

    def test_offline_doctor_never_launches_process_or_network(self):
        with patch.object(tunnel, "job", side_effect=AssertionError("launchctl")), \
             patch.object(tunnel, "authenticated_endpoint", side_effect=AssertionError("HTTP")):
            result = tunnel.diagnose(True, self.p)
        self.assertEqual(result["status"], "offline")
        self.assertFalse(result["qualification_claimed"] or result["hardware_checked"])

    def test_doctor_wont_send_bearer_to_foreign_listener(self):
        with patch.object(tunnel, "snapshot", return_value={"listener_owned": False}), \
             patch.object(tunnel, "authenticated_endpoint") as endpoint:
            result = tunnel.diagnose(False, self.p)
            endpoint.assert_not_called()
        self.assertEqual(result["status"], "failed")

    def test_doctor_distinguishes_transport_and_endpoint(self):
        with patch.object(tunnel, "snapshot", return_value={"listener_owned": True}), \
             patch.object(tunnel, "authenticated_endpoint", return_value=False):
            result = tunnel.diagnose(False, self.p)
        self.assertEqual(result["checks"][-1]["name"], "mac_tunnel_endpoint")
        self.assertEqual(result["status"], "failed")

    def test_doctor_cli_integration_selects_client_only_branch(self):
        with patch.object(tunnel, "diagnose", return_value={"status": "offline", "checks": []}) as diagnose, \
             patch.object(doctor.platform, "system", return_value="Darwin"), \
             patch.object(doctor, "load", side_effect=AssertionError("runtime profile")), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(doctor.main(["--mac-tunnel", "--offline", "--json"]), 0)
        diagnose.assert_called_once_with(True)

    def test_private_key_checks_fail_without_network(self):
        self.key.chmod(0o644)
        with self.assertRaises(tunnel.TunnelError):
            tunnel.authenticated_endpoint(self.config)
        self.key.chmod(0o600)
        self.key.write_text("")
        with self.assertRaises(tunnel.TunnelError):
            tunnel.authenticated_endpoint(self.config)

    def test_authenticated_http_ignores_proxy_and_refuses_redirect(self):
        seen = []
        class Handler(http.server.BaseHTTPRequestHandler):
            redirect = False
            body = b'{"data":[{"id":"fixture"}]}'
            def log_message(self, *_):
                pass
            def do_GET(self):
                seen.append((self.path, self.headers.get("Authorization")))
                self.send_response(302 if self.redirect else 200)
                if self.redirect:
                    self.send_header("Location", "http://example.invalid/token-leak")
                self.end_headers()
                self.wfile.write(self.body)
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        config = {**self.config, "local_port": server.server_port}
        with patch.dict(os.environ, {"http_proxy": "http://example.invalid:1", "no_proxy": ""}):
            self.assertTrue(tunnel.authenticated_endpoint(config))
            Handler.body = b"[]"
            self.assertFalse(tunnel.authenticated_endpoint(config))
            Handler.redirect = True
            with self.assertRaises(OSError):
                tunnel.authenticated_endpoint(config)
        self.assertEqual(seen, [("/v1/models", "Bearer fixture-not-a-credential")] * 3)

    def test_missing_gui_domain_is_not_successful_stop(self):
        with patch.object(tunnel, "launchctl", return_value=subprocess.CompletedProcess([], 1, "")), self.assertRaises(tunnel.TunnelError):
            tunnel.job()

    def test_permissions_and_symlink_are_not_adopted(self):
        self.p["config"].chmod(0o644)
        with self.assertRaises(tunnel.TunnelError):
            tunnel.load_config(self.p)
        self.p["plist"].unlink()
        self.p["plist"].symlink_to(self.key)
        with self.assertRaises(tunnel.TunnelError):
            tunnel.owned_plist(self.p)


if __name__ == "__main__":
    unittest.main()
