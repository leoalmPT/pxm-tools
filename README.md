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

Options can be passed as a JSON file such as `--config config.json`

```json

{
    "prefix": "fl-worker",
    "vm_configs" : [
        {
            "api": "https://bilbo.av.it.pt:8006/",
            "node": "bilbo",
            "pool": "federatedLearning",
            "template": 1000,
            "vms" : [
                {
                "n_vms" : 2,
                "vm-cipassword": "flexfl",
                "vm-net0/rate": 50,
                "vm-net0/bridge": "vmbr1",
                "vm-localtime": 1,
                "vm-cores": 8,
                "vm-memory": 16384,
                "disk" : "64G"
                },
                {
                "n_vms" : 2,
                "vm-cipassword": "flexfl",
                "vm-net0/rate": 100,
                "vm-net0/bridge": "vmbr1",
                "vm-localtime": 1,
                "vm-cores": 4,
                "vm-memory": 8192,
                "disk" : "64G"
                }
            ]
        },
        {
            "api": "https://frodo.av.it.pt:8006/",
            "node": "frodo",
            "pool": "federatedLearning",
            "template": 4000,
            "vms" : [
                {
                "n_vms" : 2,
                "vm-cipassword": "flexfl",
                "vm-net0/rate": 50,
                "vm-net0/bridge": "vmbr1",
                "vm-localtime": 1,
                "vm-cores": 8,
                "vm-memory": 16384,
                "disk" : "64G"
                }
            ]
        },
        {
            "api": "https://samwise.av.it.pt:8006/",
            "node": "samwise",
            "pool": "federatedLearning",
            "template": 4000,
            "vms" : [
                {
                "n_vms" : 2,
                "vm-cipassword": "flexfl",
                "vm-net0/rate": 50,
                "vm-net0/bridge": "vmbr1",
                "vm-localtime": 1,
                "vm-cores": 8,
                "vm-memory": 16384,
                "disk" : "64G"
                }
            ]
        },
        {
            "api": "https://hobbit.av.it.pt:8006/",
            "node": "hobbit",
            "pool": "federatedLearning",
            "template": 4000,
            "vms" : [
                {
                "n_vms" : 2,
                "vm-cipassword": "flexfl",
                "vm-net0/rate": 50,
                "vm-net0/bridge": "vmbr1",
                "vm-localtime": 1,
                "vm-cores": 8,
                "vm-memory": 16384,
                "disk" : "64G"
                }
            ]
        },
        {
            "node": "atnog-test1",
            "api": "https://atnog-test1.av.it.pt:8006/",
            "pool": "rafaelgteixeira",
            "template": 1003,
            "vms" : [
                {
                "n_vms" : 2,
                "vm-cipassword": "flexfl",
                "vm-net0/rate": 50,
                "vm-net0/bridge": "vmbr1",
                "vm-localtime": 1,
                "vm-cores": 4,
                "vm-memory": 8192,
                "disk" : "64G"
                }
            ]
        }
    ]
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