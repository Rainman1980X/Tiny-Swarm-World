#!/bin/bash

# imports
source create_dockerfiles.sh


# Define constants
PORTAINER_URL="http://localhost:9000"
USERNAME="admin"  # own user
PASSWORD="admin1234567890"  # own password
BASE_DIR="./"  # Base directory for all docker-compose files

# Function to print usage
print_usage() {
  printf "\nUsage: %s [-u username] [-p password]\n" "$0"
  printf " -u username: Optional. Default is '%s'.\n" "$USERNAME"
  printf " -p password: Optional. Default is '%s'.\n" "$PASSWORD"
}

# Function to print current username and password
print_default() {
  printf " -u username: Optional. Current is '%s'.\n" "$USERNAME"
  printf " -p password: Optional. Current is '%s'.\n\n" "$PASSWORD"
}

# Function to parse input arguments
parse_arguments() {
  while getopts u:p: flag; do
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
}

# Function to authenticate and retrieve JWT token
get_jwt_token() {
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
}

# Function to retrieve the Portainer endpoint ID
get_endpoint_id() {
  ENDPOINT_ID=$(curl -s -H "Authorization: Bearer $JWT_TOKEN" "$PORTAINER_URL/api/endpoints" | jq -r ".[] | select(.Name == \"local\") | .Id")

  if [ -z "$ENDPOINT_ID" ]; then
    printf "Failed to retrieve Endpoint ID. Aborting.\n"
    exit 1
  fi
}

# Function to delete an existing stack if it exists
delete_existing_stack() {
  local stack_name="$1"
  EXISTING_STACK_ID=$(curl -s -H "Authorization: Bearer $JWT_TOKEN" "$PORTAINER_URL/api/stacks" | jq -r ".[] | select(.Name == \"$stack_name\") | .Id")

  if [ "$EXISTING_STACK_ID" ]; then
    printf "Stack already exists. Deleting old stack...\n"
    RESPONSE=$(curl -s -X DELETE -H "Authorization: Bearer $JWT_TOKEN" "$PORTAINER_URL/api/stacks/$EXISTING_STACK_ID?external=false&endpointId=$ENDPOINT_ID")
    if echo "$RESPONSE" | grep -q "message"; then
      message=$(echo "$RESPONSE" | jq -r .message)
      details=$(echo "$RESPONSE" | jq -r .details)
      printf 'Error deleting stack for %s: \n{\n"message":"%s",\n"details":"%s"\n}\n' "$stack_name" "$message" "$details"
    else
      printf "Stack deletion successful for %s\n" "$stack_name"
    fi
  else
    printf "Stack does not exist. Proceeding with creation.\n"
  fi
}

# Function to create or update stack
create_or_update_stack() {
  local stack_name="$1"
  local compose_file_content="$2"

  PAYLOAD=$(jq -n --arg name "$stack_name" --arg stackFileContent "$compose_file_content" '{
    env: [],
    name: $name,
    fromAppTemplate: false,
    stackFileContent: $stackFileContent
  }')

  RESPONSE=$(curl -s -X POST "$PORTAINER_URL/api/stacks/create/standalone/string?type=2&method=string&endpointId=$ENDPOINT_ID" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $JWT_TOKEN" \
    -d "$PAYLOAD")

  if echo "$RESPONSE" | grep -q "message"; then
    message=$(echo "$RESPONSE" | jq -r .message)
    details=$(echo "$RESPONSE" | jq -r .details)
    printf 'Error uploading the stack for %s: \n{\n"message":"%s",\n"details":"%s"\n}\n' "$stack_name" "$message" "$details"
  else
    printf "Stack uploaded successfully for %s\n" "$stack_name"
  fi
}



# Function to process each stack directory
process_stacks() {
  for APP_DIR in "$BASE_DIR"/*/; do
    if [ -d "$APP_DIR" ]; then
      COMPOSE_FILE_PATH="$APP_DIR/docker-compose.yml"

      if [ ! -f "$COMPOSE_FILE_PATH" ]; then
        printf "\nNo docker-compose.yml file found in %s. Skipping.\n" "$APP_DIR"
        continue
      fi

      STACK_NAME=$(basename "$APP_DIR")
      printf "\nStarting process for stack: %s to Portainer...\n" "$STACK_NAME"
      delete_existing_stack "$STACK_NAME"

      COMPOSE_FILE_CONTENT=$(<"$COMPOSE_FILE_PATH")
      create_or_update_stack "$STACK_NAME" "$COMPOSE_FILE_CONTENT"
    fi
  done
  printf "\n\nAll stacks processed.\n"
}

# Main script execution
print_default
parse_arguments "$@"
get_jwt_token
get_endpoint_id
execute_prepare_scripts "$BASE_DIR"
process_stacks
