
from pxm_tools.Proxmox import Proxmox

'''
Needs to be improved as the default config no longer applies.
Small work arround proposed here.
'''
def main():
    parser = Proxmox.default_parser()
    parser.add_argument("--vmid", type=str, help="VM ID to edit (\"all\" to edit all VMs)", default="all")
    parser.add_argument("--specs", type=str, help="Json File with the new specs", default="specs.json")
    args = Proxmox.parse_args(parser)
    p = Proxmox(args)
    if args["vmid"] == "all":
        p.edit_all(args["specs"])
    else:
        args["vmid"] = int(args["vmid"])
        p.change_specs(args["vmid"], args["specs"])
        