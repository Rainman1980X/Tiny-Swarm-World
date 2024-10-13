#!/bin/bash

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