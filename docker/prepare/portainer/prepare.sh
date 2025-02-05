#!/bin/bash

MANAGER_VM="swarm-manager"

# Variablen definieren
PORTAINER_DIR="./portainer"

printf "Updating and starting Portainer in Swarm mode...\n"

# Clean up unused Docker objects (containers, networks, volumes, images)
docker system prune -a --volumes -f

# Remove the existing Portainer stack
printf "Removing Portainer Stack...\n"
docker stack rm portainer
# Clean up unused Docker objects (containers, networks, volumes, images)
docker system prune -a --volumes -f

printf "Removing Portainer data volume...\n"
docker volume rm portainer_portainer_data || printf "Volume not found or already deleted.\n"

# Clean up unused Docker objects (containers, networks, volumes, images)
docker system prune -a --volumes -f

# Wait for the stack removal to complete before redeploying
progress_bar 10

# Deploy the updated Portainer stack using Docker Swarm
# The latest image will be pulled automatically during the deployment
printf "Deploying updated Portainer Stack...\n"
docker stack deploy -c "$PORTAINER_DIR/docker-compose.yml" portainer

printf "Portainer has been updated and started in Swarm mode.\n"

# progress_bar 15

# Prüfen, ob Portainer erfolgreich gestartet ist
until curl -s "http://localhost:9000" | grep -q "Portainer"; do
  printf '.'
  sleep 5
done


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
