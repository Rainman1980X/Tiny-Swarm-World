#!/bin/bash

USER_NAME="admin"
NEXUS_CONTAINERS=$(docker ps --filter "name=nexus" --format "{{.Names}}")
NEXUS_URL="http://localhost:8081" #See documentation about the used urls


# Find the nexus container
if [ -z "$NEXUS_CONTAINERS" ]; then
    printf "No container found containing nexus.\n"
    exit 1
else
    printf "Nexus-Container found: "
    printf "%s\n" "$NEXUS_CONTAINERS"
fi

# Step 1 create the new admin password.
# Path to the admins password
INITIAL_PASSWORD_FILE="/nexus-data/admin.password"
INITIAL_PASSWORD=""
NEW_PASSWORD="MyAdminPassWord1234-126354654"
MAX_ATTEMPTS=10
WAIT_TIME=5

printf "Check on admin Account on active \n"
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" -u "$USER_NAME:$NEW_PASSWORD" -X GET "$NEXUS_URL/service/rest/v1/security/users" -H "Content-Type: application/json")

if [ "$RESPONSE" -ne 200 ]; then
  attempt=1
  while [ $attempt -le $MAX_ATTEMPTS ]; do
    RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$NEXUS_URL/service/rest/v1/status")
    if [ "$RESPONSE" -ne 200 ]; then
      printf "File not found. Waiting %d seconds before retrying...\n" "$WAIT_TIME"
      attempt=$((attempt+1))
      sleep $WAIT_TIME
    else
      printf "Nexus is up and running.\n"
      break
    fi
  done

  attempt=1
  while [ $attempt -le $MAX_ATTEMPTS ]; do
    printf "Attempt %d of %d: Checking for file %s in container...\n" "$attempt" "$MAX_ATTEMPTS" "$INITIAL_PASSWORD_FILE"

    if docker exec -it "$NEXUS_CONTAINERS" test -f "$INITIAL_PASSWORD_FILE"; then
      printf "Docker container contains %s\n" "$INITIAL_PASSWORD_FILE"
      INITIAL_PASSWORD=$(docker exec -it "$NEXUS_CONTAINERS" cat "$INITIAL_PASSWORD_FILE")
      printf "The password is: %s\n" "$INITIAL_PASSWORD"
      break
    else
      printf "File not found. Waiting %d seconds before retrying...\n" "$WAIT_TIME"
      attempt=$((attempt+1))
      sleep $WAIT_TIME
    fi
  done

  # Check if the maximum number of attempts was reached
  if [ $attempt -gt $MAX_ATTEMPTS ]; then
    printf "Exceeded maximum attempts. File %s not found in container %s.\n" "$INITIAL_PASSWORD_FILE" "$NEXUS_CONTAINERS"
    exit 1
  fi

  # Setting Account on active
  printf "Setting Account on active \n"
  RESPONSE=$(curl -s -u "$USER_NAME:$INITIAL_PASSWORD" -X GET "$NEXUS_URL/service/rest/v1/security/users" -H "Content-Type: application/json")
  ADMIN_DETAILS=$(echo "$RESPONSE" | jq '.[] | select(.userId=="admin")')

  UPDATED_ADMIN_DETAILS=$(echo "$ADMIN_DETAILS" | jq '.status = "active"')
  curl -u "$USER_NAME:$INITIAL_PASSWORD" -X PUT "$NEXUS_URL/service/rest/v1/security/users/$USER_NAME" \
  -H "Content-Type: application/json" \
  -d "$UPDATED_ADMIN_DETAILS"

  printf "Successfully updated \n"
  sleep 3

  # Setting password
  printf "Setting the new password: %s\n" "$NEW_PASSWORD"
  curl -u "$USER_NAME:$INITIAL_PASSWORD" -X PUT "$NEXUS_URL/service/rest/v1/security/users/$USER_NAME/change-password" \
  -H "Content-Type: text/plain" \
  -d "$NEW_PASSWORD"
  printf "Successful \n"
  printf "The current password is %s\n" "$NEW_PASSWORD"
else
  printf "The current password is %s\n" "$NEW_PASSWORD"
  printf "Admin account is active and running...\n"
fi

# Step 2 create the mirror of maven
API_ENDPOINT="/service/rest/v1/repositories/maven/proxy"
REPO_NAME="maven-mirror"
REMOTE_URL="https://repo.maven.apache.org/maven2/"

REPO_EXISTS=$(curl -s -u "$USER_NAME:$PASSWORD" "$NEXUS_URL$API_ENDPOINT" | grep "\"name\":\"$REPO_NAME\"")

if [ -n "$REPO_EXISTS" ]; then
    printf "Repository '%s' already exists.\n" "$REPO_NAME"
else
  printf "Here the repositories setting"
fi
