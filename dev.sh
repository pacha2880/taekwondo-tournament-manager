#!/bin/sh
set -e

cd "$(dirname "$0")"

case "$1" in
  start) docker compose up --build -d ;;
  stop) docker compose down ;;
  *) echo "uso: $0 {start|stop}" >&2; exit 1 ;;
esac
