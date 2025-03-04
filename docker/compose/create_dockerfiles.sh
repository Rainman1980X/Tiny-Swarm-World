#!/bin/bash

# Main configuration
NEXUS_URL="127.0.0.1:5000"                     # Nexus Docker Registry URL
NEW_PASSWORD="MyAdminPassWord1234-126354654"
USER_NAME="admin"
TAG="latest"                                   # Tag for the Docker image
DOCKERFILE_TEMPLATE="Dockerfile.template"

# Function to create Docker images from each found Dockerfile.template.orig.test.old
execute_prepare_scripts() {
  local directory="$1"
  local found_file=false   # Status variable to track if any Dockerfile.template.orig.test.old file_management are found

  for entry in "$directory"/*; do
    if [ -d "$entry" ]; then
      # Recursive call for each subdirectory
      printf "\nSearching in %s...\n" "$entry"
      execute_prepare_scripts "$entry"
    elif [ -f "$entry" ] && [ "$(basename "$entry")" == "$DOCKERFILE_TEMPLATE" ]; then
      # If Dockerfile.template.orig.test.old is found
      found_file=true

      local image_dir
      image_dir="$(dirname "$entry")"

      local image_name
      image_name="$(basename "$image_dir")"  # Use the directory name as the image name

      printf "\nCreating Docker container in %s...\n" "$image_dir"

      # Copy Dockerfile.template.orig.test.old to the target directory
      cp "$image_dir/$DOCKERFILE_TEMPLATE" "$image_dir/Dockerfile"

      # Build the Docker image
      docker build -t "$NEXUS_URL/$image_name:$TAG" -f "$entry" "$image_dir"

      # Login to Nexus repository
      docker login -u "$USER_NAME" -p "$NEW_PASSWORD" "$NEXUS_URL"

      # Push Docker image to Nexus repository
      docker push "$NEXUS_URL/$image_name:$TAG"

      # Logout from the Nexus repository
      docker logout "$NEXUS_URL"

      printf "Image %s has been successfully pushed to Nexus repository.\n" "$NEXUS_URL/$image_name:$TAG"
    fi
  done

  # Output message if no Dockerfile.template.orig.test.old file_management were found
  if [ "$found_file" = false ]; then
    printf "\nNo Dockerfile.template files found in %s or its subdirectories.\n" "$directory"
  else
    printf "\nAll Docker containers created successfully.\n"
  fi
}