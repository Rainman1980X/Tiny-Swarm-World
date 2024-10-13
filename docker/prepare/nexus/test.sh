#!/bin/bash

# Setze die Variablen für den Container und die Datei
NEXUS_CONTAINERS="nexus-nexus-1"
INITIAL_PASSWORD_FILE="/nexus-data/admin.password"

# Überprüfen, ob die Datei im Container existiert
if docker exec -it "$NEXUS_CONTAINERS" test -f "$INITIAL_PASSWORD_FILE"; then
  echo "Die Datei $INITIAL_PASSWORD_FILE existiert im Container $NEXUS_CONTAINERS."
  # Dateiinhalt anzeigen
  #INITIAL_PASSWORD=$(docker exec -it "$NEXUS_CONTAINERS" cat "$INITIAL_PASSWORD_FILE")
  #echo "$INITIAL_PASSWORD"
else
  echo "Die Datei $INITIAL_PASSWORD_FILE existiert nicht im Container $NEXUS_CONTAINERS."
fi