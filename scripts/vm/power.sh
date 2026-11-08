#!/bin/bash
# VM power switch, runs inside .github/workflows/vm-power.yml (already authenticated as vm-power).
# Input: "<action> [name]" (workflow_dispatch), or the last line of trigger/vm.txt "<iso> <action> <name>" (push), or empty (hourly watchdog).
set -u
PROJECT="${GCP_PROJECT:-itcodlab-video}"
MAX_HOURS="${VM_MAX_HOURS:-3}"          # watchdog: itcod-gpu running longer than this is stopped
LINE="${1:-}"
if [ -z "$LINE" ] && [ "${GITHUB_EVENT_NAME:-}" = "push" ] && [ -f trigger/vm.txt ]; then
  LINE=$(grep -v '^\s*$' trigger/vm.txt | tail -1 | cut -d' ' -f2-)   # drop the timestamp
fi
[ -z "$LINE" ] && LINE="watchdog"
ACTION=$(echo "$LINE" | awk '{print $1}')
NAME=$(echo "$LINE" | awk '{print $2}')
case "$ACTION" in start|stop|status|watchdog|describe) ;; *) echo "BAD action: $ACTION"; exit 2;; esac
if [ -n "$NAME" ] && ! [[ "$NAME" =~ ^itcod-[a-z0-9-]+$ ]]; then echo "BAD name (only itcod-*): $NAME"; exit 2; fi

zone_of() { gcloud compute instances list --project "$PROJECT" --filter="name=$1" --format="value(zone.basename())" | head -1; }
state_of() { gcloud compute instances describe "$1" --project "$PROJECT" --zone "$2" --format="value(status)"; }

list_all() { gcloud compute instances list --project "$PROJECT" --format="table(name,zone.basename(),machineType.basename(),status,lastStartTimestamp)"; }

echo "ACTION $ACTION ${NAME:-}"
case "$ACTION" in
  status)
    list_all
    ;;
  describe)
    [ -n "$NAME" ] || { echo "need a name"; exit 2; }
    Z=$(zone_of "$NAME"); [ -n "$Z" ] || { echo "NOT FOUND: $NAME"; exit 1; }
    gcloud compute instances describe "$NAME" --project "$PROJECT" --zone "$Z" --format="yaml(name,status,machineType,guestAccelerators,scheduling,labels)"
    ;;
  start|stop)
    [ -n "$NAME" ] || { echo "need a name"; exit 2; }
    Z=$(zone_of "$NAME"); [ -n "$Z" ] || { echo "NOT FOUND: $NAME (VM not created yet)"; exit 1; }
    S=$(state_of "$NAME" "$Z")
    echo "before: $S"
    if [ "$ACTION" = "start" ] && [ "$S" != "RUNNING" ]; then gcloud compute instances start "$NAME" --project "$PROJECT" --zone "$Z" --quiet; fi
    if [ "$ACTION" = "stop" ] && [ "$S" != "TERMINATED" ]; then gcloud compute instances stop "$NAME" --project "$PROJECT" --zone "$Z" --quiet; fi
    echo "after: $(state_of "$NAME" "$Z")"
    ;;
  watchdog)
    for N in itcod-gpu; do
      Z=$(zone_of "$N"); [ -n "$Z" ] || { echo "$N: not created"; continue; }
      S=$(state_of "$N" "$Z")
      if [ "$S" = "RUNNING" ]; then
        T=$(gcloud compute instances describe "$N" --project "$PROJECT" --zone "$Z" --format="value(lastStartTimestamp)")
        AGE_H=$(( ( $(date +%s) - $(date -d "$T" +%s) ) / 3600 ))
        echo "$N running ${AGE_H}h (max $MAX_HOURS)"
        if [ "$AGE_H" -ge "$MAX_HOURS" ]; then echo "WATCHDOG: stopping $N"; gcloud compute instances stop "$N" --project "$PROJECT" --zone "$Z" --quiet; fi
      else
        echo "$N: $S"
      fi
    done
    ;;
esac
