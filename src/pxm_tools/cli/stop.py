
from pxm_tools.Proxmox import Proxmox


def main():
    parser = Proxmox.default_parser()
    args = Proxmox.parse_args(parser)
    p = Proxmox(args)
    p.stop_all_vms()