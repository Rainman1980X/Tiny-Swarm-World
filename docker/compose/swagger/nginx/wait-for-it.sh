#!/usr/bin/env bash

host="$1"
shift
cmd="$@"

until nc -z "$host" 8000; do
  echo "Waiting for $host..."
  sleep 3
done

exec $cmd