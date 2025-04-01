import requests
from dotenv import load_dotenv
import os
import urllib3
import urllib.parse
import time
from rich.console import Console
import argparse

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
load_dotenv()


API_URL = os.getenv("PM_API_URL")
USER = os.getenv("PM_USERNAME")
PASS = os.getenv("PM_PASSWORD")
VM_PASSWORD = os.getenv("VM_PASSWORD")
PUBLIC_KEY = os.getenv("HOME") + "/.ssh/id_rsa.pub"
INSECURE = True 
SLEEP = 5


console = Console()
parser = argparse.ArgumentParser(description="Proxmox VM Management")
parser.add_argument("-a", "--action", choices=["create", "start", "stop", "delete"], help="Action to perform on VMs", required=True)
parser.add_argument("-u", "--user", type=str, default=USER, help="Proxmox username")
parser.add_argument("-p", "--password", type=str, default=PASS, help="Proxmox password")
parser.add_argument("--api", type=str, default=API_URL, help="Proxmox API URL")
parser.add_argument("--ids", type=str, default="scripts/ids.txt", help="File to store VM IDs")
parser.add_argument("--ips", type=str, default="scripts/ips.txt", help="File to store VM IPs")
parser.add_argument("--node", type=str, default="frodo", help="Node name")
parser.add_argument("-n", "--number", type=int, default=1, help="Number of VMs to create")
parser.add_argument("--prefix", type=str, default="fl-worker", help="Prefix for VM names")
parser.add_argument("--template", type=int, default=2000, help="Template ID to clone from")
parser.add_argument("--vmpass", type=str, default=VM_PASSWORD, help="VM password")
parser.add_argument("--pool", type=str, default="federatedLearning", help="Pool name")
parser.add_argument("--pubkey", type=str, default=PUBLIC_KEY, help="Path to public key file")
args = parser.parse_args()


def check_env_vars() -> None:
    if not all([args.api, args.user, args.password]):
        raise EnvironmentError("Please set PM_API_URL, PM_USERNAME, and PM_PASSWORD in your environment variables.")
    

def check_response(response) -> None:
    if response.status_code != 200:
        print(f"Error: {response.status_code}, {response.text}")
        raise Exception(f"Request failed with status code {response.status_code}")


def authenticate() -> dict:
    url = f"{args.api}/access/ticket"
    data = {
        "username": args.user,
        "password": args.password,
    }
    response = requests.post(url, data=data, verify=not INSECURE)
    check_response(response)
    ticket = response.json()["data"]["ticket"]
    csrf_token = response.json()["data"]["CSRFPreventionToken"]
    console.log("Authenticated successfully.", style="bold green")
    return {
        "Authorization": f"PVEAuthCookie={ticket}",
        "CSRFPreventionToken": csrf_token,
    }
    

def next_id(headers) -> int:
    url = f"{args.api}/cluster/nextid"
    response = requests.get(url, headers=headers, verify=not INSECURE)
    check_response(response)
    return response.json()["data"]


def create_vm(headers, vm_id, vm_name) -> None:
    vm_data = {
        "newid": vm_id,
        "name": vm_name,
        "target": args.node,
        "pool": args.pool,
        "full": 1,
    }

    url = f"{args.api}/nodes/{args.node}/qemu/{args.template}/clone"
    response = requests.post(url, headers=headers, data=vm_data, verify=not INSECURE)
    check_response(response)


def wait_for_cloning(headers, vm_id) -> None:
    url = f"{args.api}/nodes/{args.node}/qemu/{vm_id}/status/current"
    while True:
        response = requests.get(url, headers=headers, verify=not INSECURE)
        if response.status_code == 403:
            time.sleep(SLEEP)
            continue
        check_response(response)
        break


def setup_vm(headers, name) -> int:
    vm_id = next_id(headers)
    create_vm(headers, vm_id, name)
    console.log(f"VM: [bold cyan]{name}[/bold cyan] created with ID: {vm_id}.")
    with console.status(f"Cloning VM {vm_id}..."):
        wait_for_cloning(headers, vm_id)
    console.log(f"VM [bold cyan]{vm_id}:{name}[/bold cyan] cloning completed.")
    return vm_id


def decode_value(value: str) -> dict:
    result = {}
    for item in value.split(","):
        key, val = item.split("=")
        result[key] = val
    return result


def encode_value(value: dict) -> str:
    return ",".join(f"{k}={v}" for k, v in value.items())


def change_specs(headers, vm_id) -> None:
    url = f"{args.api}/nodes/{args.node}/qemu/{vm_id}/config"
    response = requests.get(url, headers=headers, verify=not INSECURE)
    check_response(response)
    data = response.json()["data"]
    net0 = decode_value(data["net0"])
    net0["rate"] = "50"
    # TODO: Add private network
    net0 = encode_value(net0)
    print(f"Net0: {net0}")
    exit()
    with open(args.pubkey, "r") as f:
        sshkey = f.read().strip()
    sshkeys = urllib.parse.unquote(data["sshkeys"])
    sshkeys = sshkeys + f"\n\n{sshkey}\n"
    sshkeys = urllib.parse.quote(sshkeys, safe="")
    payload = {
        "net0": net0,
        "sshkeys": sshkeys,
        "cipassword": args.vmpass,
    }
    response = requests.put(url, headers=headers, data=payload, verify=not INSECURE)
    check_response(response)
    console.log(f"VM {vm_id} specs changed.")


def create_all_vms(headers) -> None:
    ids = []
    console.log("Creating VMs...")
    for i in range(1, args.number + 1):
        name = f"{args.prefix}-{i}"
        vm_id = setup_vm(headers, name)
        change_specs(headers, vm_id)
        ids.append(vm_id)
    console.log("All VMs created successfully.", style="bold green")
    with open(args.ids, "w") as f:
        for vm_id in ids:
            f.write(f"{vm_id}\n")


def load_ids() -> list:
    with open(args.ids, "r") as f:
        ids = [int(line.strip()) for line in f.readlines()]
    return ids


def get_ip(headers, vm_id) -> str:
    url = f"{args.api}/nodes/{args.node}/qemu/{vm_id}/agent/network-get-interfaces"
    while True:
        response = requests.get(url, headers=headers, verify=not INSECURE)
        if response.status_code != 500:
            break
        time.sleep(SLEEP)
    check_response(response)
    data = response.json()["data"]["result"]
    for interface in data:
        if interface.get("name", None) == "eth0":
            for ip_addr in interface.get("ip-addresses", []):
                if ip_addr["ip-address-type"] == "ipv4":
                    return ip_addr["ip-address"]
    raise Exception("No IPv4 address found for eth0.")


def wait_for_status(headers, vm_id, status) -> None:
    url = f"{args.api}/nodes/{args.node}/qemu/{vm_id}/status/current"
    while True:
        response = requests.get(url, headers=headers, verify=not INSECURE)
        check_response(response)
        if response.json()["data"]["status"] == status:
            break


def wait_all_status(headers, ids, status) -> None:
    for vm_id in ids:
        url = f"{args.api}/nodes/{args.node}/qemu/{vm_id}/status/current"
        while True:
            response = requests.get(url, headers=headers, verify=not INSECURE)
            check_response(response)
            if response.json()["data"]["status"] == status:
                break
            time.sleep(SLEEP)


def start_vm(headers, vm_id) -> None:
    url = f"{args.api}/nodes/{args.node}/qemu/{vm_id}/status/current"
    response = requests.get(url, headers=headers, verify=not INSECURE)
    check_response(response)
    if response.json()["data"]["status"] == "running":
        console.log(f"VM {vm_id} is already running.")
        return
    url = f"{args.api}/nodes/{args.node}/qemu/{vm_id}/status/start"
    response = requests.post(url, headers=headers, verify=not INSECURE)
    check_response(response)
    console.log(f"VM {vm_id} is starting...")


def start_vms(headers) -> None:
    ids = load_ids()
    ips = []
    for vm_id in ids:
        start_vm(headers, vm_id)
    wait_all_status(headers, ids, "running")
    console.log("All VMs started successfully.", style="bold green")
    with console.status("Waiting for VM IPs..."):
        for vm_id in ids:
            ip = get_ip(headers, vm_id)
            ips.append(ip)
            console.log(f"VM {vm_id} IP: {ip}")
    console.log("All VM IPs retrieved successfully.", style="bold green")
    with open(args.ips, "w") as f:
        for ip in ips:
            f.write(f"{ip}\n")


def shutdown_vms(headers) -> None:
    ids = load_ids()
    for vm_id in ids:
        url = f"{args.api}/nodes/{args.node}/qemu/{vm_id}/status/current"
        response = requests.get(url, headers=headers, verify=not INSECURE)
        check_response(response)
        if response.json()["data"]["status"] == "stopped":
            console.log(f"VM {vm_id} is already stopped.")
            continue
        console.log(f"Stopping VM {vm_id}...")
        url = f"{args.api}/nodes/{args.node}/qemu/{vm_id}/status/shutdown"
        response = requests.post(url, headers=headers, verify=not INSECURE)
        check_response(response)
    with console.status("Waiting for VMs to stop..."):
        wait_all_status(headers, ids, "stopped")
    console.log("All VMs stopped successfully.", style="bold green")


def wait_for_deletion(headers, vm_id) -> None:
    url = f"{args.api}/nodes/{args.node}/qemu/{vm_id}/status/current"
    while True:
        response = requests.get(url, headers=headers, verify=not INSECURE)
        if response.status_code == 403:
            break
        check_response(response)
        time.sleep(SLEEP)


def delete_vms(headers) -> None:
    ids = load_ids()
    ignore_ids = []
    for vm_id in ids:
        url = f"{args.api}/nodes/{args.node}/qemu/{vm_id}/status/current"
        response = requests.get(url, headers=headers, verify=not INSECURE)
        if response.status_code == 403:
            console.log(f"VM {vm_id} does not exist.")
            ignore_ids.append(vm_id)
            continue
        console.log(f"Deleting VM {vm_id}...")
        url = f"{args.api}/nodes/{args.node}/qemu/{vm_id}?purge=0&destroy-unreferenced-disks=0"
        response = requests.delete(url, headers=headers, verify=not INSECURE)
        check_response(response)
    with console.status("Waiting for VMs to be deleted..."):
        for vm_id in sorted(set(ids) - set(ignore_ids)):
            wait_for_deletion(headers, vm_id)
            console.log(f"VM {vm_id} deleted.")
    console.log("All VMs deleted successfully.", style="bold green")


def main():
    actions = {
        "create": create_all_vms,
        "start": start_vms,
        "stop": shutdown_vms,
        "delete": delete_vms,
    }
    check_env_vars()
    headers = authenticate()
    # actions[args.action](headers)
    change_specs(headers, 142)
    

if __name__ == "__main__":
    main()
