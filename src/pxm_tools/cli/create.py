import os

from pxm_tools.Proxmox import Proxmox

def main():
    parser = Proxmox.default_parser()
    parser.add_argument("--prefix", type=str, help="Prefix for the VMs name", default="pxm")
    parser.add_argument("-n", "--number", type=int, help="Number of VMs to create", default=1)
    parser.add_argument("--template", type=str, help="VM template to use")
    parser.add_argument("--pool", type=str, help="Pool to use")
    parser.add_argument("--pubkey", type=str, help="Public key to use", default=f"{os.getenv('HOME')}/.ssh/id_rsa.pub")
    args = Proxmox.parse_args(parser)
    p = Proxmox(args)
    p.create_all_vms()