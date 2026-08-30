#!/usr/bin/env bash
# Put the live demo back to a pristine state before recording.
set -euo pipefail
P=hyperdrift-distribution; R=europe-west1
U=https://helm-294160018950.europe-west1.run.app

echo "→ cargo: ingress all, max-instances 3"
gcloud run services update cargo --region $R --project $P \
  --ingress all --max-instances 3 --quiet >/dev/null

echo "→ apps: all online"
for a in nextrole intel web3-capital; do
  curl -s -X POST "$U/control/$a/on" >/dev/null
done

sleep 4
echo "→ state:"
for a in cargo nextrole intel web3-capital; do
  printf '   %-14s %s\n' "$a" "$(curl -s "$U/probe?app=$a")"
done
echo "ready to record."
