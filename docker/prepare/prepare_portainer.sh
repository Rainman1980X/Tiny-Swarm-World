#!/bin/bash

# Variablen definieren
PORTAINER_DIR="./portainer"

printf "Updating and starting Portainer...\n"
docker system prune -a --volumes -f
printf "Downing Portainer..."
docker-compose -f "$PORTAINER_DIR/docker-compose.yml" down
printf "Pulling Portainer..."
docker-compose -f "$PORTAINER_DIR/docker-compose.yml" pull portainer
printf "Updating Portainer..."
docker-compose -f "$PORTAINER_DIR/docker-compose.yml" up -d portainer

printf "Waiting for 15 sec to start up...\n"
sleep 15

printf "Init adminuser for portainer\n"

PAYLOAD=$(jq -n '{
      "username": "admin",
      "password": "admin1234567890"
    }')

RESPONSE=$(curl -s -X POST "http://localhost:9000/api/users/admin/init" \
    -H "Content-Type: application/json" \
    -d "$PAYLOAD")

if printf "Response %s" "$RESPONSE" | grep -q "message"; then
  message=$(echo "$RESPONSE" | jq -r .message)
  details=$(echo "$RESPONSE" | jq -r .details)

  printf 'Error creating the admin account \n{\n"message":"%s",\n"details":"%s"\n}\n' "$message" "$details"

else
  printf "Admin account created successfully\n"
fi
