#!/bin/bash

printf "Nexus3 %s authentication used User: %s  Password: %s\n" "$NEXUS_URL" "$USER_NAME" "$NEW_PASSWORD"

REPO_NAME="docker-hosted"
REPO_PORT="5000"

# Function to create the Docker repository
create_docker_repository() {
  printf "Creating Docker repository '%s' on %s\n" "$REPO_NAME" "$NEXUS_URL"

  # API call to create the Docker repository
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

# Main logic
if ! check_repository_exists; then
  create_docker_repository
else
  printf "The repository already exists; no action required.\n"
fi