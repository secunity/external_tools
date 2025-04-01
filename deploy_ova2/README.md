# README - OVA Deployment Script

## Overview

This script automates the deployment of an OVA (Open Virtual Appliance) file to a VMware ESXi host. It simplifies the process of setting up a virtual machine by configuring essential parameters such as VM name, network settings, and default gateway.

## Usage

To run the script, use the following command:

```
./deploy_ova.sh --esxi_host [ESXI_HOST] --esxi_user [ESXI_USER] --esxi_password [ESXI_PASSWORD] --ova [OVA_FILE] \
                --vm_name [VM_NAME] --ip [IP_ADDRESS/NETMASK] --gw [DEFAULT_GW_IP]
```

### Parameters:

- `--esxi_host [ESXI_HOST]` - IP address or hostname of the ESXi server.
- `--esxi_user [ESXI_USER]` - Username for ESXi authentication (default: `root`).
- `--esxi_password [ESXI_PASSWORD]` - Password for ESXi authentication. If not provided, the script will prompt for it.
- `--ova [OVA_FILE]` - Path to the OVA file that needs to be deployed.
- `--vm_name [VM_NAME]` - Name for the new virtual machine (default: OVA filename without extension).
- `--ip [IP_ADDRESS/NETMASK]` - Static IP address and netmask for the VM (default: `192.168.1.100/24`).
- `--gw [DEFAULT_GW_IP]` - Default gateway IP address.

## Example

Deploy a VM with specific network settings:

```
./deploy_ova.sh --esxi_host 192.168.1.100 --esxi_user root --esxi_password mypassword --ova myvm.ova \
                --ip 172.20.20.18/24 --gw 172.20.20.1
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

## Author

Denis Chertkov\
denis\@chertkov.info\
version 1.06\
Date: [2025-03-28]
