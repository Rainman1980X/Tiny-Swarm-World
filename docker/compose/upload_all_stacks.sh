#!/bin/bash

# Define variables
PORTAINER_URL="http://localhost:9000"
USERNAME="admin" # own user
PASSWORD="admin1234567890" # own password
BASE_DIR="./"  # Base directory for all docker-compose files

print_usage() {
  printf "\nUsage: %s [-u username] [-p password]\n" " $0"
  printf " -u username: Optional. Default is '%s'.\n" "$USERNAME"
  printf " -p password: Optional. Default is '%s'.\n" "$PASSWORD"
}

print_default() {
  printf " -u username: Optional. Current is '%s'.\n" "$USERNAME"
  printf " -p password: Optional. Current is '%s'.\n\n" "$PASSWORD"
}

while getopts u:p: flag
do
    case "${flag}" in
        u) USERNAME=${OPTARG};;
        p) PASSWORD=${OPTARG};;
        *)
            printf "Invalid option: -%s" "${OPTARG}"
            print_usage
            exit 1
            ;;
    esac
done

print_default

# Get JWT Token
printf "Authenticating and retrieving JWT token..."
JWT_TOKEN=$(curl -s -X POST "$PORTAINER_URL/api/auth" -H "Content-Type: application/json" -d "{
  \"Username\": \"$USERNAME\",
  \"Password\": \"$PASSWORD\"
}" | jq -r '.jwt')

if [ -z "$JWT_TOKEN" ]; then
  printf "Failed to retrieve JWT token. Aborting.\n"
  exit 1
fi

printf "JWT token retrieved successfully.\n"

# Find endpoint ID
ENDPOINT_ID=$(curl -s -H "Authorization: Bearer $JWT_TOKEN" "$PORTAINER_URL/api/endpoints" | jq -r '.[0].Id')

if [ -z "$ENDPOINT_ID" ]; then
  printf "Failed to retrieve Endpoint ID. Aborting.\n"
  exit 1
fi

# Iterate through all subdirectories in the base directory
for APP_DIR in "$BASE_DIR"/*/; do
  if [ -d "$APP_DIR" ]; then
    COMPOSE_FILE_PATH="$APP_DIR/docker-compose.yml"

    if [ ! -f "$COMPOSE_FILE_PATH" ]; then
      printf "\nNo docker-compose.yml file found in %s. Skipping.\n" "$APP_DIR"
      continue
    fi

    STACK_NAME=$(basename "$APP_DIR")
    printf "\nStarting process for stack: %s to Portainer...\n" "$STACK_NAME"
    printf "Checking if stack already exists...\n"

    ENDPOINT_ID=$(curl -s -H "Authorization: Bearer $JWT_TOKEN" "$PORTAINER_URL/api/endpoints" | jq -r ".[] | select(.Name == \"local\") | .Id")

    # check if stack already exists
    EXISTING_STACK_ID=$(curl -s -H "Authorization: Bearer $JWT_TOKEN" "$PORTAINER_URL/api/stacks" | jq -r ".[] | select(.Name == \"${STACK_NAME}\") | .Id")

    if [ "$EXISTING_STACK_ID" ]; then
      printf "Stack already exists. Deleting old stack...\n"
      RESPONSE=$(curl -s -X DELETE -H "Authorization: Bearer $JWT_TOKEN" "$PORTAINER_URL/api/stacks/$EXISTING_STACK_ID?external=false&endpointId=$ENDPOINT_ID")
      if printf "Response %s" "$RESPONSE" | grep -q "message"; then
        message=$(echo "$RESPONSE" | jq -r .message)
        details=$(echo "$RESPONSE" | jq -r .details)
        printf 'Error uploading the stack for %s: \n{\n"message":"%s",\n"details":"%s"\n}\n' "$STACK_NAME" "$message" "$details"
      else
        printf "Stack deleting was successfully for %s\n" "$STACK_NAME"
      fi
    else
      printf "Stack does not exist. Proceeding with creation of new stack...\n"
    fi

    printf "Uploading docker-compose.yml from %s to Portainer...\n" "$APP_DIR"
    COMPOSE_FILE_CONTENT=$(<"$COMPOSE_FILE_PATH")
    # Ensure JSON contains correct strings that are properly escaped
    # ESCAPED_COMPOSE_FILE_CONTENT=$(printf "%s" "$COMPOSE_FILE_CONTENT" | jq -R -s '.')

    #printf "%s" "$ESCAPED_COMPOSE_FILE_CONTENT"
    # Properly escape newlines for JSON compatibility
    PAYLOAD=$(jq -n --arg name "$STACK_NAME" --arg stackFileContent "$COMPOSE_FILE_CONTENT" '{
      env: [],
      name: $name,
      fromAppTemplate: false,
      stackFileContent: $stackFileContent
    }')

    RESPONSE=$(curl -s -X POST "$PORTAINER_URL/api/stacks/create/standalone/string?type=2&method=string&endpointId=$ENDPOINT_ID" \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $JWT_TOKEN" \
      -d "$PAYLOAD")

    # Has any errors
    if printf "Response %s" "$RESPONSE" | grep -q "message"; then
      message=$(echo "$RESPONSE" | jq -r .message)
      details=$(echo "$RESPONSE" | jq -r .details)

      printf 'Error uploading the stack for %s: \n{\n"message":"%s",\n"details":"%s"\n}\n' "$STACK_NAME" "$message" "$details"

    else
      printf "Stack uploaded successfully for %s\n" "$STACK_NAME"
    fi
  fi
done

printf "\n\nAll stacks processed.\n"