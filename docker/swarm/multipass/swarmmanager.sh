#!/bin/bash

GATEWAY=""                    # IP of the Swarm Manager Node
MANAGER_NODE="swarm-manager"  # Name of the Swarm Manager Node
# Create and configure the manager
setup_manager() {
    printf "Creating and starting the Manager Node %s...\n" "$MANAGER_NODE"
    create_cloud_init_manager

    multipass launch --name "$MANAGER_NODE" --memory "$VM_MEMORY" --disk "$VM_DISK" --cloud-init cloud-init-manager.yaml

    # Install Docker and Docker Compose
    install_docker $MANAGER_NODE

    # Prepare setup files
    copy_and_set_permissions

    # Mount the directory
    mount_directory

    # Initialize Docker Swarm
    printf "Initializing Docker Swarm on the Manager Node %s...\n" "$MANAGER_NODE"
    SWARM_ADVERTISE_IP=$(multipass info $MANAGER_NODE | grep "IPv4" | awk '{print $2}')
    multipass exec $MANAGER_NODE -- docker swarm init --advertise-addr "$SWARM_ADVERTISE_IP"

    # Get the token for workers
    SWARM_JOIN_TOKEN=$(multipass exec $MANAGER_NODE -- docker swarm join-token -q worker)
    printf "Swarm Manager %s configured!\n IPv4 %s\n" "$MANAGER_NODE" "$SWARM_ADVERTISE_IP"

}

create_cloud_init_manager() {
  # Getting the gateway ip
  get_gateway
  printf "Creating cloud-init-manager.yaml for gateway %s...\n" "$GATEWAY"
cat <<EOF > cloud-init-manager.yaml
#cloud-config
network:
    version: 2
    ethernets:
        ens3:
            dhcp4: no
            addresses:
                - 10.34.157.100/24
            gateway4: $GATEWAY
            nameservers:
                addresses:
                    - 8.8.8.8
                    - 8.8.4.4
EOF
}
get_gateway() {
  multipass launch -n temp-vm
  GATEWAY=$(multipass exec temp-vm -- ip route | grep default | awk '{print $3}')
  multipass delete temp-vm && multipass purge
}

