import os

from pxm_tools.Proxmox import Proxmox

def main():
    parser = Proxmox.default_parser()
    parser.add_argument("--prefix", type=str, help="Prefix for the VMs name", default="pxm")
    parser.add_argument("--pubkey", type=str, help="Public key to use", default=f"{os.getenv('HOME')}/.ssh/id_rsa.pub")
    args = Proxmox.parse_args(parser)
    p = Proxmox(args)
    p.create_all_vms()