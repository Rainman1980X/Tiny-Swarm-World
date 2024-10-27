#!/bin/bash

# Configuration variables
NEXUS_URL="http://127.0.0.1:8081"
NEXUS_DOCKER_URL="http://127.0.0.1:5000"
REPO_NAME="docker-hosted"
REPO_PORT="5000"
USER_NAME="admin"
NEW_PASSWORD="MyAdminPassWord1234-126354654"
PORTAINER_URL="http://localhost:9000"
PORTAINER_USERNAME="admin" # own user
PORTAINER_PASSWORD="admin1234567890" # own password

printf "Nexus3 %s authentication used User: %s\n" "$NEXUS_URL" "$USER_NAME"

# Function to create the Docker repository in Nexus
create_docker_repository() {
  printf "Creating Docker repository '%s' on %s\n" "$REPO_NAME" "$NEXUS_URL"

  curl -u "$USER_NAME:$NEW_PASSWORD" -X POST "$NEXUS_URL/service/rest/v1/repositories/docker/hosted" \
    -H "Content-Type: application/json" \
    -d "{
          \"name\": \"$REPO_NAME\",
          \"online\": true,
          \"storage\": {
            \"blobStoreName\": \"default\",
            \"strictContentTypeValidation\": true,
            \"writePolicy\": \"ALLOW_ONCE\"
          },
          \"docker\": {
            \"v1Enabled\": false,
            \"forceBasicAuth\": true,
            \"httpPort\": $REPO_PORT
          }
        }"

  printf "Docker repository '%s' successfully created and available on port %s.\n" "$REPO_NAME" "$REPO_PORT"
}

# Function to check if the repository already exists
check_repository_exists() {
  printf "Checking if the repository '%s' already exists...\n" "$REPO_NAME"

  response=$(curl -s -u "$USER_NAME:$NEW_PASSWORD" "$NEXUS_URL/service/rest/v1/repositories")

  if echo "$response" | grep -q "\"name\":\"$REPO_NAME\""; then
    printf "Repository '%s' already exists.\n" "$REPO_NAME"
    return 0
  else
    printf "Repository '%s' does not exist. Starting creation...\n" "$REPO_NAME"
    return 1
  fi
}

# Function to add the Nexus repository to Portainer
add_repository_to_portainer() {
  printf "Logging into Portainer to obtain API token...\n"

  # Log in and retrieve token
  PORTAINER_TOKEN=$(curl -s -X POST "$PORTAINER_URL/api/auth" \
    -H "Content-Type: application/json" \
    -d "{\"Username\": \"$PORTAINER_USERNAME\", \"Password\": \"$PORTAINER_PASSWORD\"}" | jq -r .jwt)
  printf "PORTAINER_TOKEN %s\n" "$PORTAINER_TOKEN"
  if [ "$PORTAINER_TOKEN" == "null" ]; then
    echo "Failed to retrieve Portainer token. Check your Portainer credentials."
    exit 1
  fi

  printf "Adding Nexus Docker repository to Portainer...\n"

  # Add Nexus as a new registry endpoint
  curl -X POST "http://localhost:9000/api/registries" \
      -H "Authorization: Bearer $PORTAINER_TOKEN" \
      -H "Content-Type: application/json" \
      -d "{
            \"Type\": 3,
            \"Name\": \"Nexus3 Docker Registry\",
            \"URL\": \"$NEXUS_DOCKER_URL\",
            \"BaseURL\": \"$NEXUS_DOCKER_URL\",
            \"tls\": true,
            \"tlsskipVerify\": true,
            \"Authentication\": true,
            \"Username\": \"$USER_NAME\",
            \"Password\": \"$NEW_PASSWORD\"
          }"

  printf "Nexus Docker repository added to Portainer.\n"
}

# Main logic
if ! check_repository_exists; then
  create_docker_repository
else
  printf "The repository already exists; no action required.\n"
fi

# Add Nexus as a registry in Portainer
add_repository_to_portainer
