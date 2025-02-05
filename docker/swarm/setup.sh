#!/bin/bash

# Configuration variables
WORKER_PREFIX="swarm-worker"                               # Prefix for the worker node names
WORKER_COUNT=2                                             # Number of worker nodes
VM_MEMORY="2G"                                             # RAM for each VM
VM_DISK="10G"                                              # Disk space for each VM
DOCKER_INSTALL_SCRIPT="https://get.docker.com"             # Docker installation script
SWARM_ADVERTISE_IP=""                                      # Automatically detected

source ../utils.sh
souce /multipass/swarmmanager.sh

# Dynamically determine the directory one level above the script
SOURCE_DIR="$HOME/setup_files"               # Set to the user's home directory for setup files
TARGET_DIR="/home/ubuntu/mounted-scripts"                  # Destination directory on the Swarm Manager

# Function: Copy and set permissions for setup files
copy_and_set_permissions() {

    local SOURCE_FOLDER
    SOURCE_FOLDER="$(realpath "$(dirname "$0")/../")"
    local DEST_FOLDER="$HOME/setup_files"

    if [ ! -d "$SOURCE_FOLDER" ]; then
        printf "Error: Source folder %s does not exist.\n" "$SOURCE_FOLDER"
        exit 1
    fi

    printf "Copying %s to %s...\n" "$SOURCE_FOLDER" "$DEST_FOLDER"
    rm -rf "$DEST_FOLDER"
    cp -rf "$SOURCE_FOLDER" "$DEST_FOLDER"

    printf "Setting permissions for %s...\n" "$DEST_FOLDER"
    sudo chown -R "$USER:$USER" "$DEST_FOLDER"
    sudo chmod -R 755 "$DEST_FOLDER"
    sudo find "$DEST_FOLDER" -type f -name "*.sh" -exec chmod +x {} \;

    printf "Folder copied and permissions set successfully.\n"
}

# Function: Install Docker and Docker Compose
install_docker() {
    INSTANCE_NAME=$1
    printf "Installing Docker and Docker Compose on %s...\n" "$INSTANCE_NAME"
    multipass exec "$INSTANCE_NAME" -- bash -c "curl -fsSL $DOCKER_INSTALL_SCRIPT | sudo bash"
    multipass exec "$INSTANCE_NAME" -- bash -c "sudo usermod -aG docker ubuntu"

    # Install Docker Compose
    multipass exec "$INSTANCE_NAME" -- bash -c "sudo apt update && sudo apt install -y docker-compose"

    # Verify installation
    multipass exec "$INSTANCE_NAME" -- bash -c "docker-compose --version"

    printf "Docker and Docker Compose installation on %s completed!\n" "$INSTANCE_NAME"

    # Install network tools
    multipass exec "$INSTANCE_NAME" -- sudo apt install -y net-tools
    printf "Network tools installation on %s completed!\n" "$INSTANCE_NAME"
}

# Function: Mount directory with proper permissions and error handling
mount_directory() {
    printf "Mounting and cleaning previous mount if exists...\n"
    multipass mount "$SOURCE_DIR" "$MANAGER_NODE:$TARGET_DIR"

    printf "Verifying ownership inside the VM...\n"
    if ! multipass exec "$MANAGER_NODE" -- ls -ld "$TARGET_DIR"; then
        printf "Error: Could not verify ownership of %s\n" "$TARGET_DIR"
        exit 1
    fi

    printf "The directory (%s) was successfully mounted on the Swarm Manager at %s, and all scripts are executable!\n" "$SOURCE_DIR" "$TARGET_DIR"
}

# Create workers and add them to the Swarm
setup_workers() {
    printf "Creating and configuring %d worker nodes...\n" "$WORKER_COUNT"
    for i in $(seq 1 $WORKER_COUNT); do
        WORKER_NODE="${WORKER_PREFIX}-${i}"
        printf "Creating Worker Node %s...\n" "$WORKER_NODE"
        multipass launch --name "$WORKER_NODE" --memory "$VM_MEMORY" --disk "$VM_DISK" --cloud-init ./cloud-config.yaml

        # Install Docker and Docker Compose
        install_docker "$WORKER_NODE"

        # Add the worker to the Swarm Cluster
        multipass exec "$WORKER_NODE" -- docker swarm join --token "$SWARM_JOIN_TOKEN" "$SWARM_ADVERTISE_IP:2377"
        printf "Worker Node %s successfully added to the Swarm Cluster!\n" "$WORKER_NODE"
    done
}

# Main setup
printf "Starting the Multipass Docker Swarm setup...\n"

# Configure the manager
setup_manager

# Configure and add workers
setup_workers

# Show Swarm status
printf "Docker Swarm Cluster status on %s:\n" "$MANAGER_NODE"
multipass exec "$MANAGER_NODE" -- docker node ls

printf "Docker Swarm is set up! To access the Manager Node, run:\n"
printf "multipass shell %s\n" "$MANAGER_NODE"