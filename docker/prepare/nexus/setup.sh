#!/bin/bash

PORTAINER_URL="http://localhost:9000"
PORTAINER_USERNAME="admin" # own user
PORTAINER_PASSWORD="admin1234567890" # own password

STACK_NAME="nexus"
USER_NAME="admin"
NEXUS_CONTAINERS=$(docker ps --filter "name=$STACK_NAME" --format "{{.Names}}")
NEXUS_URL="http://localhost:8081" #See documentation about the used urls


# Find the nexus container
if [ -z "$NEXUS_CONTAINERS" ]; then
    printf "No container found containing %s.\n" "$STACK_NAME"
    printf "Creating new container\n"

    JWT_TOKEN=$(curl -s -X POST "$PORTAINER_URL/api/auth" -H "Content-Type: application/json" -d "{
      \"Username\": \"$PORTAINER_USERNAME\",
      \"Password\": \"$PORTAINER_PASSWORD\"
    }" | jq -r '.jwt')

    ENDPOINT_ID=$(curl -s -H "Authorization: Bearer $JWT_TOKEN" "$PORTAINER_URL/api/endpoints" | jq -r '.[0].Id')

    COMPOSE_FILE_PATH="nexus/docker-compose.yml"
    COMPOSE_FILE_CONTENT=$(<"$COMPOSE_FILE_PATH")
    PAYLOAD=$(jq -n --arg name "$STACK_NAME" --arg stackFileContent "$COMPOSE_FILE_CONTENT" --argjson endpointId "$ENDPOINT_ID" '{
          env: [],
          name: $name,
          fromAppTemplate: false,
          stackFileContent: $stackFileContent,
          endpointId: $endpointId
       }')

    RESPONSE=$(curl -s -X POST "$PORTAINER_URL/api/stacks" \
          -H "Content-Type: application/json" \
          -H "Authorization: Bearer $JWT_TOKEN" \
          -d "$PAYLOAD")

    if printf "Response %s\n" "$RESPONSE" | grep -q "message"; then
        message=$(echo "$RESPONSE" | jq -r .message)
        details=$(echo "$RESPONSE" | jq -r .details)
        printf 'Error creating the stack for %s: \n{\n"message":"%s",\n"details":"%s"\n}\n' "$STACK_NAME" "$message" "$details"
    else
        printf "Stack created successfully for %s\n" "$STACK_NAME"
    fi

else
    printf "Nexus-Container found: %s\n" "$NEXUS_CONTAINERS"

    printf "Checking if an update is needed...\n"

    JWT_TOKEN=$(curl -s -X POST "$PORTAINER_URL/api/auth" -H "Content-Type: application/json" -d "{
      \"Username\": \"$PORTAINER_USERNAME\",
      \"Password\": \"$PORTAINER_PASSWORD\"
    }" | jq -r '.jwt')

    ENDPOINT_ID=$(curl -s -H "Authorization: Bearer $JWT_TOKEN" "$PORTAINER_URL/api/endpoints" | jq -r '.[0].Id')

    STACK_ID=$(curl -s -H "Authorization: Bearer $JWT_TOKEN" "$PORTAINER_URL/api/stacks" | jq -r ".[] | select(.Name==\"$STACK_NAME\") | .Id")

   if [ -n "$STACK_ID" ]; then
          printf "Updating existing Nexus stack %s at endpointId %s...\n" "$STACK_ID" "$ENDPOINT_ID"

          COMPOSE_FILE_PATH="nexus/docker-compose.yml"
          COMPOSE_FILE_CONTENT=$(<"$COMPOSE_FILE_PATH")
          PAYLOAD=$(jq -n --arg stackFileContent "$COMPOSE_FILE_CONTENT" '{
                env: [],
                prune: true,
                pullImage: false,
                stackFileContent: $stackFileContent
             }')

          RESPONSE=$(curl -s -X PUT "$PORTAINER_URL/api/stacks/$STACK_ID?endpointId=$ENDPOINT_ID" \
                -H "Content-Type: application/json" \
                -H "Authorization: Bearer $JWT_TOKEN" \
                -d "$PAYLOAD")

          if printf "Response %s\n" "$RESPONSE" | grep -q "message"; then
              message=$(echo "$RESPONSE" | jq -r .message)
              details=$(echo "$RESPONSE" | jq -r .details)
              printf 'Error updating the stack for %s: \n{\n"message":"%s",\n"details":"%s"\n}\n' "$STACK_NAME" "$message" "$details"
          else
              printf "Stack updated successfully for %s\n" "$STACK_NAME"
          fi
      else
          printf "No update needed. Stack is already up-to-date.\n"
      fi
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
      progress_bar $WAIT_TIME
      attempt=$((attempt+1))
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

# Create the Base64 authentication header
AUTH_HEADER="Authorization: Basic $(echo -n "$USER_NAME:$NEW_PASSWORD" | base64)"

# Example for enabling anonymous access using Basic Authentication
ANON_ACCESS_URL="$NEXUS_URL/service/rest/v1/security/anonymous"
ANON_ACCESS_PAYLOAD=$(cat <<EOF
{
  "enabled": true
}
EOF
)

# Make the API request using Basic Authentication
RESPONSE=$(curl -s -X PUT "${ANON_ACCESS_URL}" -H "${AUTH_HEADER}" -H "Content-Type: application/json" -d "${ANON_ACCESS_PAYLOAD}")
if echo "$RESPONSE" | jq -e '.message' > /dev/null; then
    printf "Error enabling anonymous access: %s\n" "$(echo "$RESPONSE" | jq -r '.message')"
else
    printf "Anonymous access enabled successfully.\n"
fi
