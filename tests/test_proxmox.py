import json
import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock

import requests

from pxm_tools.Proxmox import Proxmox


class TestRequestTimeout(unittest.TestCase):
    def test_request_passes_request_timeout(self):
        px = Proxmox(args={})
        px.api = "https://proxmox.example:8006/"
        px.headers = {"Authorization": "PVEAuthCookie=abc"}

        with patch("requests.get") as mock_get:
            mock_get.return_value = MagicMock(status_code=200)
            px.request("get", "api2/json/cluster/nextid")

        mock_get.assert_called_once_with(
            "https://proxmox.example:8006/api2/json/cluster/nextid",
            headers=px.headers,
            data=None,
            verify=not Proxmox.INSECURE,
            timeout=Proxmox.REQUEST_TIMEOUT,
        )


class TestWaitFor(unittest.TestCase):
    def test_wait_for_raises_timeout_error_after_deadline(self):
        px = Proxmox(args={})
        response = MagicMock(status_code=999)
        with patch.object(px, "request", return_value=response), \
             patch("pxm_tools.Proxmox.time.monotonic", side_effect=[0, 1000]), \
             patch("pxm_tools.Proxmox.time.sleep") as mock_sleep:
            with self.assertRaises(TimeoutError):
                px.wait_for("api2/json/nodes/x/qemu/1/status/current", lambda r: False)
        mock_sleep.assert_not_called()

    def test_wait_for_tolerates_transient_request_exceptions(self):
        px = Proxmox(args={})
        matching_response = MagicMock(status_code=200)
        px.request = MagicMock(
            side_effect=[
                requests.exceptions.ConnectionError("boom"),
                requests.exceptions.ConnectionError("boom"),
                matching_response,
            ]
        )
        with patch("pxm_tools.Proxmox.time.monotonic", return_value=0), \
             patch("pxm_tools.Proxmox.time.sleep") as mock_sleep:
            result = px.wait_for(
                "api2/json/nodes/x/qemu/1/status/current",
                lambda r: r is matching_response,
            )
        self.assertIs(result, matching_response)
        self.assertEqual(mock_sleep.call_count, 2)
        self.assertEqual(px.request.call_count, 3)


class TestCreateAllVmsIncrementalPersistence(unittest.TestCase):
    def test_create_all_vms_persists_ids_before_change_specs_failure(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            ids_path = os.path.join(tmp_dir, "ids.json")
            vm_configs = [
                {
                    "api": "https://node1:8006/",
                    "node": "node1",
                    "pool": "pool1",
                    "template": 9000,
                    "vms": [{"n_vms": 2}],
                }
            ]
            px = Proxmox(args={"vm_configs": vm_configs, "prefix": "test", "ids": ids_path})
            px.auth = MagicMock()
            px.setup_vm = MagicMock(side_effect=[101, 102])
            px.change_specs = MagicMock(side_effect=[None, Exception("boom")])

            with self.assertRaises(Exception):
                px.create_all_vms()

            with open(ids_path) as f:
                saved = json.load(f)
            self.assertEqual(saved["node1"]["ids"], [101, 102])


class TestRemoveAllVms403Retry(unittest.TestCase):
    def _make_proxmox(self):
        px = Proxmox(args={"ids": "ids.json"})
        px.load_ids = MagicMock(
            return_value={"node1": {"api": "https://node1:8006/", "ids": [101]}}
        )
        px.auth = MagicMock()
        px.wait_for = MagicMock()
        return px

    def test_vm_skipped_when_still_403_after_reauth(self):
        px = self._make_proxmox()
        px.request = MagicMock(
            side_effect=[
                MagicMock(status_code=403),
                MagicMock(status_code=403),
            ]
        )

        px.remove_all_vms()

        self.assertEqual(px.request.call_count, 2)
        delete_calls = [c for c in px.request.call_args_list if c.args[0] == "delete"]
        self.assertEqual(len(delete_calls), 0)
        self.assertEqual(px.auth.call_count, 3)

    def test_vm_deleted_after_reauth_returns_non_403(self):
        px = self._make_proxmox()
        px.request = MagicMock(
            side_effect=[
                MagicMock(status_code=403),
                MagicMock(status_code=200),
                MagicMock(status_code=200),
            ]
        )

        px.remove_all_vms()

        self.assertEqual(px.request.call_count, 3)
        delete_calls = [c for c in px.request.call_args_list if c.args[0] == "delete"]
        self.assertEqual(len(delete_calls), 1)
        self.assertEqual(
            delete_calls[0].args[1],
            "api2/json/nodes/node1/qemu/101?purge=0&destroy-unreferenced-disks=0",
        )
        self.assertEqual(px.auth.call_count, 3)


if __name__ == "__main__":
    unittest.main()
