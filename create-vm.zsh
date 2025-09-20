#!/bin/sh

echo "Starting. Checking for base image..."

if [[ ! -f AlmaLinux-9-GenericCloud-latest.x86_64.qcow2 ]]; then
	echo "No image found -- downloading AlmaLinux-9-GenericCloud-latest.x86_64.qcow2..."
	curl -vfsSL "https://repo.almalinux.org/almalinux/9/cloud/x86_64/images/AlmaLinux-9-GenericCloud-latest.x86_64.qcow2" -o AlmaLinux-9-GenericCloud-latest.x86_64.qcow2
fi

#genisoimage -output cloud-init.iso -volid cidata -joliet -rock user-data.yml meta-data.yml

#echo "disk provision..."
#qemu-img create -f qcow2 kaspersky-1.qcow2 32G

echo "disk check..."
if [[ ! -f disk-1.qcow ]]; then
	echo "creating new disk 'disk-1.qcow2'..."
	cp AlmaLinux-9-GenericCloud-latest.x86_64.qcow2 disk-1.qcow2
	qemu-img resize disk-1.qcow2 32G
fi
 
qemu-system-x86_64 \
    -name kaspersky-1 \
    -m 4096 \
    -smp 2 \
    -cpu host \
    -machine q35 \
    -drive file=disk-1.qcow2,format=qcow2,if=virtio \
    -cdrom cloud-init.iso \
    -netdev user,id=net0,hostfwd=tcp::2222-:22,hostfwd=tcp::8080-:8080 \
    -device e1000,netdev=net0 \
    -enable-kvm \
    -boot d \
    -vga std
