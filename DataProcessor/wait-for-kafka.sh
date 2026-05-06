#!/bin/sh
# wait-for-kafka.sh
set -e
host="$1"
shift
until nc -z "$host" 9092; do
  echo "Waiting for Kafka..."
  sleep 2
done
exec "$@"