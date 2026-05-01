# pxm-tools — Proxmox VM Provisioning Utilities

CLI toolkit for managing Proxmox VM lifecycle: cloning from templates, configuring specs, retrieving IPs, and bulk start/stop/remove. Built to provision distributed experiment nodes for the PKDD 2026 federated learning experiments.

## Requirements

- Python >= 3.12
- [`uv`](https://github.com/astral-sh/uv) (no prior installation step needed)

## CLI Commands

| Command | Purpose |
|---|---|
| `uv run pxm-create` | Clone VMs from templates and configure specs |
| `uv run pxm-start` | Start VMs and collect their IPs |
| `uv run pxm-stop` | Gracefully shut down VMs |
| `uv run pxm-rm` | Delete VMs |
| `uv run pxm-edit` | Edit specs of existing VMs |

All commands share a common set of flags:

| Flag | Default | Description |
|---|---|---|
| `--config` | — | Path to JSON config file |
| `--user` | `$PM_USER` | Proxmox username |
| `--pass` | `$PM_PASS` | Proxmox password |
| `--ids` | `ids.json` | File to read/write VM IDs |
| `--ips` | `ips.json` | File to write VM IPs (`pxm-start` only) |

`pxm-create` additionally accepts:

| Flag | Default | Description |
|---|---|---|
| `--prefix` | `pxm` | Name prefix for created VMs |
| `--pubkey` | `~/.ssh/id_rsa.pub` | SSH public key injected into VMs |

## Environment Variables

Credentials are read from a `.env` file in the working directory:

| Variable | Purpose |
|---|---|
| `PM_USER` | Proxmox username (e.g. `user@pam`) |
| `PM_PASS` | Proxmox password |

## Config File

Pass a JSON config to `pxm-create` via `--config`. Each entry in `vm_configs` targets one Proxmox node and clones `n_vms` VMs from the specified template.

```json
{
  "prefix": "fl-worker",
  "vm_configs": [
    {
      "node": "atnog-test1",
      "api": "https://atnog-test1.av.it.pt:8006/",
      "pool": "rafaelgteixeira",
      "template": 1003,
      "vms": [
        {
          "n_vms": 8,
          "vm-cipassword": "flexfl",
          "vm-net0/bridge": "vmbr1",
          "vm-localtime": 1,
          "vm-cores": 2,
          "vm-memory": 32768,
          "disk": "64G"
        }
      ]
    },
    {
      "node": "hobbit",
      "api": "https://hobbit.av.it.pt:8006/",
      "pool": "federatedLearning",
      "template": 4000,
      "vms": [
        {
          "n_vms": 16,
          "vm-cipassword": "flexfl",
          "vm-net0/bridge": "vmbr1",
          "vm-localtime": 1,
          "vm-cores": 3,
          "vm-memory": 16384,
          "disk": "64G"
        }
      ]
    },
    {
      "node": "samwise",
      "api": "https://samwise.av.it.pt:8006/",
      "pool": "federatedLearning",
      "template": 3000,
      "vms": [
        {
          "n_vms": 32,
          "vm-cipassword": "flexfl",
          "vm-net0/bridge": "vmbr1",
          "vm-localtime": 1,
          "vm-cores": 4,
          "vm-memory": 12288,
          "disk": "64G"
        }
      ]
    }
  ]
}
```

VM options use the `--vm-` prefix (matching the Proxmox API field names). Use `/` for sub-keys:

```
vm-cores          # Number of CPU cores
vm-memory         # RAM in MB
vm-net0/bridge    # Bridge for net0 interface
vm-net0/rate      # Network rate limit for net0
disk              # Disk resize target (e.g. "64G")
```

Full list of VM options: [Proxmox API docs](https://pve.proxmox.com/pve-docs/api-viewer/index.html#/nodes/{node}/qemu/{vmid}/config)

## Output Files

`pxm-create` writes `ids.json` mapping each node to its created VM IDs:

```json
{
  "atnog-test1": { "api": "https://atnog-test1.av.it.pt:8006/", "ids": [101, 102, 103] },
  "hobbit":      { "api": "https://hobbit.av.it.pt:8006/",      "ids": [201, 202] }
}
```

`pxm-start` reads `ids.json`, waits for all VMs to boot, then writes `ips.json` and a flat `ips.txt` (one IP per line, derived from the `--ips` path):

```json
{
  "atnog-test1": { "api": "https://atnog-test1.av.it.pt:8006/", "ips": ["10.0.0.1", "10.0.0.2"] },
  "hobbit":      { "api": "https://hobbit.av.it.pt:8006/",      "ips": ["10.0.1.1"] }
}
```

## Experiment Workflow

```bash
# 1. Create all VMs from config
uv run pxm-create --config config-experiment.json --ids ids.json

# 2. Start VMs and collect IPs (writes ids.json → ips.json + ips.txt)
uv run pxm-start --ids ids.json --ips ips.json

# 3. Use ips.txt with FlexFL scripts to set up and run experiments
bash ../FlexFL/scripts/setup_vms.sh -f ips.txt

# 4. Stop VMs when done
uv run pxm-stop --ids ids.json

# 5. Remove VMs to free resources
uv run pxm-rm --ids ids.json
```

## Notes

- VM cloning (`pxm-create`) is sequential — one at a time per Proxmox constraint.
- Start, stop, and remove operations are issued in bulk then waited on in parallel.
- `pxm-start` polls the QEMU guest agent for each VM's `eth0` IPv4 address before writing IPs.
