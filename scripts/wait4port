#!/bin/bash
IFS=":" read -a a <<< "$1"
if [[ -z ${a[0]} || "${a[0]}" == "-h" || "${a[0]}" == "--help" ]]; then
  echo "$(basename $0) <ip>:[port] [interval] [timeout]"
  echo "  default port - 22"
  echo "  default interval - 1 second"
  echo "  default timeout - 5 seconds"
  exit 1
fi

ip=${a[0]}
port=${a[1]:-22}

while :; do
  printf "%s - %s:%s is ?\b" "$(date +'%Y%m%d.%T')" "${ip}" "${port}"
  timeout --foreground ${3:-5} bash -c "</dev/tcp/${ip}/${port}" 2>/dev/null && {
    echo "UP"
    exit 0
  } || {
    echo "DOWN"
  }
  sleep ${2:-1}
done
