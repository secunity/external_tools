# README - OVA Deployment Script

## Overview

This script automates the deployment of an OVA (Open Virtual Appliance) file to a VMware ESXi host. It simplifies the process of setting up a virtual machine by configuring essential parameters such as VM name, network settings, and default gateway.

## Usage

To run the script, use the following command:

```
./deploy_ova.sh --esxi_host [ESXI_HOST] --esxi_user [ESXI_USER] --esxi_password [ESXI_PASSWORD] \
                --ova [OVA_FILE] --ds [ESXI_DATASTORE] \
                --vm_name [VM_NAME] --ip [IP_ADDRESS/NETMASK] --gw [DEFAULT_GW_IP]
```

### Parameters:

- `--esxi_host [ESXI_HOST]` - IP address or hostname of the ESXi server.
- `--esxi_user [ESXI_USER]` - Username for ESXi authentication (default: `root`).
- `--esxi_password [ESXI_PASSWORD]` - Password for ESXi authentication. If not provided, the script will prompt for it.
- `--ova [OVA_FILE]` - Path to the OVA file that needs to be deployed.
- `--ds [ESXI_DATASTORE]` - Target datastore name for a VI locator. If not specified, the default ESXi datastore is used.
- `--vm_name [VM_NAME]` - Name for the new virtual machine (default: OVA filename without extension).
- `--ip [IP_ADDRESS/NETMASK]` - Static IP address and netmask for the VM (default: `192.168.1.100/24`).
- `--gw [DEFAULT_GW_IP]` - Default gateway IP address.

## Example

Deploy a VM with specific network settings:

```
./deploy_ova.sh --esxi_host 192.168.1.100 --esxi_user root --esxi_password mypassword --ova myvm.ova \
                --ds usbdrive --ip 172.20.20.18/24 --gw 172.20.20.1
```

## Requirements

To use this script, ensure the following dependencies are met:

- `ovftool` must be installed and available in the `./ovftool/` directory.
- The following system utilities must be installed and accessible in the system's `PATH`:
  - `tar`
  - `sha256sum`
  - `genisoimage`
- The ESXi host must be reachable, and the provided credentials must be valid.

## Notes

- If the `--esxi_password` argument is omitted, the script will securely prompt for the password.
- The default values are applied if `--vm_name` or `--ip` are not explicitly provided.
- The script assumes `ovftool` is in `./ovftool/`, but you may need to update the script if `ovftool` is installed elsewhere.

---

## Cloud-Init Data ISO (cidata.iso) Preparation

The `cidata.iso` provides network configuration to the VM at first boot via cloud-init.

### Prerequisites

```bash
sudo apt update && sudo apt install -y genisoimage
```

### Step-by-Step Instructions

#### 1. Create working directory

```bash
mkdir -p ~/cidata-build && cd ~/cidata-build
```

#### 2. Create `meta-data`

```bash
cat > meta-data << 'EOF'
instance-id: flowsec-local
local-hostname: flowsec-vm
EOF
```

#### 3. Create `user-data`

```bash
cat > user-data << 'EOF'
#cloud-config
bootcmd:
  - echo "Cloud-init started" > /tmp/cidata.txt
  - mount /dev/sr0 /mnt && cp /mnt/network.conf /etc/netplan/00-installer-config.yaml && umount /mnt
  - netplan apply
  - date >> /tmp/cidata.txt
EOF
```

#### 4. Create `network.conf`

Replace IP and gateway with your values:

```bash
cat > network.conf << 'EOF'
network:
  version: 2
  ethernets:
    ens160:
      addresses:
        - 192.168.1.100/24
      gateway4: 192.168.1.1
      nameservers:
        addresses:
          - 8.8.8.8
EOF
```

#### 5. Generate the ISO

```bash
genisoimage -output cidata.iso -volid cidata -joliet -rock meta-data user-data network.conf
```

#### 6. Verify the ISO

```bash
ls -lh cidata.iso
isoinfo -l -i cidata.iso
```

### Automated Script

```
```

### ISO Contents Summary

| File | Purpose |
|------|---------|
| `meta-data` | Instance identifier for cloud-init |
| `user-data` | Boot commands to apply network configuration |
| `network.conf` | Netplan network configuration (IP, gateway, DNS) |

> **Note:** The volume label **must** be `cidata` for cloud-init to detect the datasource.

## Author

Denis Chertkov\
denis\@chertkov.info\
version 1.08\
Date: [2025-05-04]
