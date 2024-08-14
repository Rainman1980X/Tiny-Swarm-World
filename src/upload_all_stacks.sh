#!/bin/bash

# Variablen definieren
PORTAINER_URL="http://localhost:9000"
USERNAME="admin"
PASSWORD="admin1234567890"
BASE_DIR="../docker"  # Basisverzeichnis für alle docker-compose-Dateien

# Get JWT Token
echo "Authenticating and retrieving JWT token..."
JWT_TOKEN=$(curl -s -X POST "$PORTAINER_URL/api/auth" -H "Content-Type: application/json" -d "{
  \"Username\": \"$USERNAME\",
  \"Password\": \"$PASSWORD\"
}" | jq -r '.jwt')

if [ -z "$JWT_TOKEN" ]; then
  echo "Failed to retrieve JWT token. Aborting."
  exit 1
fi

echo "JWT token retrieved successfully."

# Endpunkt ID finden
ENDPOINT_ID=$(curl -s -H "Authorization: Bearer $JWT_TOKEN" "$PORTAINER_URL/api/endpoints" | jq -r '.[0].Id')

if [ -z "$ENDPOINT_ID" ]; then
  echo "Failed to retrieve Endpoint ID. Aborting."
  exit 1
fi

# Durchlaufen Sie alle Unterverzeichnisse im Basisverzeichnis
for APP_DIR in "$BASE_DIR"/*/; do
  if [ -d "$APP_DIR" ]; then
    COMPOSE_FILE_PATH="$APP_DIR/docker-compose.yml"

    if [ ! -f "$COMPOSE_FILE_PATH" ]; then
      echo "No docker-compose.yml file found in $APP_DIR. Skipping."
      continue
    fi

    STACK_NAME=$(basename "$APP_DIR")
    COMPOSE_FILE_CONTENT=$(<"$COMPOSE_FILE_PATH")

    # Sicherstellen, dass JSON korrekte Zeichenfolgen enthält, die richtig escaped sind
    ESCAPED_COMPOSE_FILE_CONTENT=$(echo "$COMPOSE_FILE_CONTENT" | jq -R -s '.')

    echo "Uploading docker-compose.yml from $APP_DIR to Portainer..."

    # Properly escape newlines for JSON compatibility
    PAYLOAD=$(jq -n --arg name "$STACK_NAME" --arg stackFileContent "$COMPOSE_FILE_CONTENT" '{
      name: $name,
      stackFileContent: $stackFileContent,
      fromAppTemplate: false,
      env: []
    }')

    RESPONSE=$(curl -s -X POST "$PORTAINER_URL/api/stacks?type=2&method=string&endpointId=$ENDPOINT_ID" \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $JWT_TOKEN" \
      -d "$PAYLOAD")

    # Überprüfen Sie die Antwort auf Fehler
    if echo "$RESPONSE" | grep -q "err"; then
      echo "Error uploading the stack for $STACK_NAME: $RESPONSE"
    else
      echo "Stack uploaded successfully for $STACK_NAME: $RESPONSE"
    fi
  fi
done

echo "All stacks processed."