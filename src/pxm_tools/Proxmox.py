import requests
from dotenv import load_dotenv
import os
import urllib3
import urllib.parse
import time
from rich.console import Console
import argparse
from typing import Callable, Any
import json
from pathlib import Path

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
load_dotenv()

class Proxmox:

    INSECURE = True 
    SLEEP = 5

    @staticmethod
    def default_parser() -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(description="Proxmox API Wrapper")
        parser.add_argument("--config", type=str, help="Path to the config file", default="config.json")
        parser.add_argument("--api", type=str, default=os.getenv("PM_API_URL"), help="Proxmox API URL")
        parser.add_argument("--user", type=str, default=os.getenv("PM_USER"), help="Proxmox user")
        parser.add_argument("--pass", type=str, default=os.getenv("PM_PASS"), help="Proxmox password")
        parser.add_argument("--node", type=str, default=None, help="Proxmox node name")
        parser.add_argument("--ids", type=str, default="ids.txt", help="File to save VM IDs")
        parser.add_argument("--ips", type=str, default="ips.txt", help="File to save VM IPs")
        return parser
    

    @staticmethod
    def parse_args(parser: argparse.ArgumentParser) -> dict:
        args, unknown = parser.parse_known_args()
        config = {}
        if args.config is not None:
            if not Path(args.config).exists():
                raise Exception(f"Config file {args.config} does not exist.")
            with open(args.config, "r") as f:
                config = json.load(f)
            parser.set_defaults(**config)
        args, unknown = parser.parse_known_args()
        args = vars(args)
        args.pop("config")
        for k, v in args.items():
            if v is None:
                raise Exception(f"Missing required argument --{k}.")
        for i, arg in enumerate(unknown):
            if arg.startswith("--"):
                key = arg[2:]
                if i + 1 >= len(unknown) or unknown[i + 1].startswith("--"):
                    raise Exception(f"Missing value for argument {arg}")
                value = unknown[i + 1]
                if value.isdigit():
                    value = int(value)
                args[key] = value
        return args


    def __init__(self, args: dict, **kwargs):
        self.console = Console()
        self.args: dict = {**args, **kwargs}
        self.api: str = self.args["api"]
        self.node: str = self.args["node"]
        self.headers: dict = {}
        self.auth()


    def request(self, method: str, endpoint: str, data: Any = None) -> requests.Response:
        url = f"{self.api}{endpoint}"
        return getattr(requests, method.lower())(url, headers=self.headers, data=data, verify=not Proxmox.INSECURE)


    def check_response(self, response: requests.Response) -> None:
        if response.status_code != 200:
            self.console.log(f"Error: {response.status_code}, {response.text}")
            raise Exception(f"Request failed with status code {response.status_code}")
        

    def auth(self) -> None:
        data = {
            "username": self.args["user"],
            "password": self.args["pass"],
        }
        response = self.request("post", "/access/ticket", data=data)
        self.check_response(response)
        data = response.json()["data"]
        self.console.log("Authenticated successfully.", style="bold green")
        self.headers = {
            "Authorization": f"PVEAuthCookie={data["ticket"]}",
            "CSRFPreventionToken": data["CSRFPreventionToken"],
        }
    

    def next_id(self) -> int:
        response = self.request("get", "/cluster/nextid")
        self.check_response(response)
        return response.json()["data"]
    

    def wait_for(self, endpoint: str, fn: Callable[[requests.Response], bool]) -> requests.Response:
        while True:
            response = self.request("get", endpoint)
            if fn(response):
                break
            time.sleep(Proxmox.SLEEP)
        return response
    

    def clone_vm(self, vm_id, vm_name) -> None:
        vm_data = {
            "newid": vm_id,
            "name": vm_name,
            "target": self.node,
            "pool": self.args["pool"],
            "full": 1,
        }
        endpoint = f"/nodes/{self.node}/qemu/{self.args["template"]}/clone"
        response = self.request("post", endpoint, data=vm_data)
        self.check_response(response)


    def setup_vm(self, name) -> int:
        vm_id = self.next_id()
        self.clone_vm(vm_id, name)
        self.console.log(f"VM [bold cyan]{name}[/bold cyan] created with ID {vm_id}.")
        with self.console.status(f"Cloning VM {vm_id}..."):
            endpoint = f"/nodes/{self.node}/qemu/{vm_id}/status/current"
            self.wait_for(endpoint, lambda r: r.status_code != 403)
        self.console.log(f"VM [bold cyan]{vm_id}[/bold cyan] cloning completed.")
        return vm_id
    

    def decode_value(self, value: str) -> dict:
        result = {}
        for item in value.split(","):
            key, val = item.split("=")
            result[key] = val
        return result


    def encode_value(self, value: dict) -> str:
        return ",".join(f"{k}={v}" for k, v in value.items())
    

    def change_specs(self, vm_id) -> None:
        endpoint = f"/nodes/{self.node}/qemu/{vm_id}/config"
        response = self.request("get", endpoint)
        self.check_response(response)
        data = response.json()["data"]
        payload = {}
        for k, v in self.args.items():
            if not k.startswith("vm-"):
                continue
            k = k[3:]
            if "/" in k:
                k, sub_k = k.split("/")
                actual = payload.get(k, data[k])
                actual = self.decode_value(actual)
                actual[sub_k] = v
                payload[k] = self.encode_value(actual)
            else:
                payload[k] = v
        if self.args.get("pubkey", None) is not None and Path(self.args["pubkey"]).exists():
            with open(self.args["pubkey"], "r") as f:
                sshkey = f.read().strip()
            sshkeys = urllib.parse.unquote(data["sshkeys"])
            sshkeys = sshkeys + f"\n\n{sshkey}\n"
            sshkeys = urllib.parse.quote(sshkeys, safe="")
            payload["sshkeys"] = sshkeys
        response = self.request("put", endpoint, data=payload)
        self.check_response(response)
        self.console.log(f"VM {vm_id} specs changed.")


    def create_all_vms(self) -> None:
        ids = []
        self.console.log(f"Creating {self.args["number"]} VMs...")
        for i in range(1, self.args["number"] + 1):
            name = f"{self.args["prefix"]}-{i}"
            vm_id = self.setup_vm(name)
            self.change_specs(vm_id)
            ids.append(vm_id)
        self.console.log("All VMs created successfully.", style="bold green")
        with open(self.args["ids"], "w") as f:
            for vm_id in ids:
                f.write(f"{vm_id}\n")


    def load_ids(self) -> list:
        with open(self.args["ids"], "r") as f:
            ids = [int(line.strip()) for line in f.readlines()]
        return ids


    def get_ip(self, vm_id) -> str:
        endpoint = f"/nodes/{self.node}/qemu/{vm_id}/agent/network-get-interfaces"
        response = self.wait_for(endpoint, lambda r: r.status_code != 500)
        self.check_response(response)
        data = response.json()["data"]["result"]
        for interface in data:
            if interface.get("name", None) == "eth0":
                for ip_addr in interface.get("ip-addresses", []):
                    if ip_addr["ip-address-type"] == "ipv4":
                        return ip_addr["ip-address"]
        raise Exception("No IPv4 address found for eth0.")
    

    def start_vm(self, vm_id) -> None:
        endpoint = f"/nodes/{self.node}/qemu/{vm_id}/status/current"
        response = self.request("get", endpoint)
        self.check_response(response)
        if response.json()["data"]["status"] == "running":
            self.console.log(f"VM {vm_id} is already running.")
            return
        endpoint = f"/nodes/{self.node}/qemu/{vm_id}/status/start"
        response = self.request("post", endpoint)
        self.check_response(response)
        self.console.log(f"VM {vm_id} is starting...")


    def start_all_vms(self) -> None:
        ids = self.load_ids()
        ips = []
        for vm_id in ids:
            self.start_vm(vm_id)
        with self.console.status("Waiting for VMs to start..."):
            for vm_id in ids:
                endpoint = f"/nodes/{self.node}/qemu/{vm_id}/status/current"
                self.wait_for(endpoint, lambda r: r.json()["data"]["status"] == "running")
        self.console.log("All VMs started successfully.", style="bold green")
        with self.console.status("Waiting for VM IPs..."):
            for vm_id in ids:
                ip = self.get_ip(vm_id)
                ips.append(ip)
                self.console.log(f"VM {vm_id} IP: {ip}")
        self.console.log("All VM IPs retrieved successfully.", style="bold green")
        with open(self.args["ips"], "w") as f:
            for ip in ips:
                f.write(f"{ip}\n")


    def stop_all_vms(self) -> None:
        ids = self.load_ids()
        for vm_id in ids:
            endpoint = f"/nodes/{self.node}/qemu/{vm_id}/status/current"
            response = self.request("get", endpoint)
            self.check_response(response)
            if response.json()["data"]["status"] == "stopped":
                self.console.log(f"VM {vm_id} is already stopped.")
                continue
            self.console.log(f"Stopping VM {vm_id}...")
            endpoint = f"/nodes/{self.node}/qemu/{vm_id}/status/shutdown"
            response = self.request("post", endpoint)
            self.check_response(response)
        with self.console.status("Waiting for VMs to stop..."):
            for vm_id in ids:
                endpoint = f"/nodes/{self.node}/qemu/{vm_id}/status/current"
                self.wait_for(endpoint, lambda r: r.json()["data"]["status"] == "stopped")
        self.console.log("All VMs stopped successfully.", style="bold green")


    def remove_all_vms(self) -> None:
        ids = self.load_ids()
        ignore_ids = []
        for vm_id in ids:
            endpoint = f"/nodes/{self.node}/qemu/{vm_id}/status/current"
            response = self.request("get", endpoint)
            if response.status_code == 403:
                self.console.log(f"VM {vm_id} does not exist.")
                ignore_ids.append(vm_id)
                continue
            self.console.log(f"Deleting VM {vm_id}...")
            endpoint = f"/nodes/{self.node}/qemu/{vm_id}?purge=0&destroy-unreferenced-disks=0"
            response = self.request("delete", endpoint)
            self.check_response(response)
        with self.console.status("Waiting for VMs to be deleted..."):
            for vm_id in sorted(set(ids) - set(ignore_ids)):
                endpoint = f"/nodes/{self.node}/qemu/{vm_id}/status/current"
                self.wait_for(endpoint, lambda r: r.status_code == 403)
                self.console.log(f"VM {vm_id} deleted.")
        self.console.log("All VMs deleted successfully.", style="bold green")


    def edit_all(self) -> None:
        ids = self.load_ids()
        for vm_id in ids:
            self.console.log(f"Editing VM {vm_id}...")
            self.change_specs(vm_id)
        self.console.log("All VMs edited successfully.", style="bold green")
