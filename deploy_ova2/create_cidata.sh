#!/bin/bash
# create_cidata.sh - Generate cidata.iso with custom network settings
# Usage: ./create_cidata.sh <IP/MASK> <GATEWAY>
# Example: ./create_cidata.sh 172.20.20.18/24 172.20.20.1

set -e

IP="${1:-192.168.1.100/24}"
GW="${2:-192.168.1.1}"

WORKDIR=$(mktemp -d)
cd "$WORKDIR"

cat > meta-data << 'EOF'
instance-id: flowsec-local
local-hostname: flowsec-vm
EOF

cat > user-data << 'EOF'
#cloud-config
bootcmd:
  - echo "Cloud-init started" > /tmp/cidata.txt
  - mount /dev/sr0 /mnt && cp /mnt/network.conf /etc/netplan/00-installer-config.yaml && umount /mnt
  - netplan apply
  - date >> /tmp/cidata.txt
EOF

cat > network.conf << EOF
network:
  version: 2
  ethernets:
    ens160:
      addresses:
        - ${IP}
      gateway4: ${GW}
      nameservers:
        addresses:
          - 8.8.8.8
EOF

genisoimage -output cidata.iso -volid cidata -joliet -rock meta-data user-data network.conf

mv cidata.iso "$OLDPWD/"
cd "$OLDPWD"
rm -rf "$WORKDIR"

echo "Created: $(ls -lh cidata.iso)"
