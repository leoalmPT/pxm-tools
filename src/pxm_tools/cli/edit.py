
from pxm_tools.Proxmox import Proxmox


def main():
    parser = Proxmox.default_parser()
    parser.add_argument("--vmid", type=int, help="VM ID to edit")
    args = Proxmox.parse_args(parser)
    p = Proxmox(args)
    p.change_specs(args["vmid"])