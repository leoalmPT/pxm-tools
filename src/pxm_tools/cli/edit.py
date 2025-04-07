
from pxm_tools.Proxmox import Proxmox


def main():
    parser = Proxmox.default_parser()
    parser.add_argument("--vmid", type=str, help="VM ID to edit (\"all\" to edit all VMs)", default="all")
    args = Proxmox.parse_args(parser)
    p = Proxmox(args)
    if args["vmid"] == "all":
        p.edit_all()
    else:
        args["vmid"] = int(args["vmid"])
        p.change_specs(args["vmid"])
        