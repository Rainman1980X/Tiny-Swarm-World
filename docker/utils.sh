#!/bin/bash

SWARM_MANAGER_IP=

# Function: Check if Swarm is already initialized on the Manager node
check_swarm_status() {
    VM=$1
    SWARM_STATUS=$(multipass exec "$VM" -- bash -c "docker info --format '{{ .Swarm.LocalNodeState }}'" 2>/dev/null)

    if [ "$SWARM_STATUS" == "active" ]; then
        printf "Swarm is already initialized on %s.\n" "$VM"
        return 0
    else
        return 1
    fi
}

# Funktion, die einen Progress Bar für eine bestimmte Anzahl von Sekunden anzeigt
progress_bar() {

  local duration=$1
  local steps=30
  local step_duration
  step_duration=$(awk "BEGIN {print $duration / $steps}")

  printf "Waiting for %s seconds to start up...\n" "$duration"

  for i in $(seq 1 $steps); do
    local progress
    progress=$(printf '#%.0s' $(seq 1 "$i"))
    printf "\r[%-30s]" "$progress"
    sleep "$step_duration"
  done
  echo
}