# pxm-tools

A collection of tools to interact with Proxmox API.

# Installation

```bash
pip install pxm-tools
```

# Usage

```bash
pxm-create -h
pxm-edit -h
pxm-start -h
pxm-stop -h
pxm-rm -h
```

# Must Know

Some arguments can be used from environment variables or .env file.

```bash
--api   # PM_API_URL
--user  # PM_USER
--pass  # PM_PASS
```

Options can be passed as a JSON file such as `--config my_config.json` (`config.json` by default)

```json
{
    "node": "frodo",
    "prefix": "fl-worker",
    "pool": "federatedLearning",
    "template": 2000,
    
    "vm-cipassword": "flexfl",
    "vm-net0/rate": 50,
    "vm-net0/bridge": "vmbr1"
}
```


Configurations for the VM can be passed with the prefix `--vm-`:

```bash
--vm-cores      # Number of CPU cores
--vm-net0/rate  # Network rate limit, use / when value has other options
```

To see all available options, check the Proxmox API documentation for the VM configuration:
- https://pve.proxmox.com/pve-docs/api-viewer/index.html#/nodes/{node}/qemu/{vmid}/config

VM cloning is done one by one on purpose, starting, stopping, and removing VMs is done in bulk.