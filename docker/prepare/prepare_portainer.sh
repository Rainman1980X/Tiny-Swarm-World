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