#!/bin/bash
# Tema H della revisione completa: i minuti del CI di daniel-g-carrasco/meridiana, letti con gh (sola lettura).
# Scrive nella cartella data come primo argomento (o in quella dello script): runs.json (tutti i run),
# runs-per-day.txt (run per giorno, esito, evento), timing.txt (durata e campo "billable" dell'endpoint timing,
# che il 23/10/2026 rispondeva 0 per ogni run), jobs.txt (un job per riga: run, nome, secondi, esito).
# Poi H-ci-minuti.py fa i conti per giorno. Lanciato il 23/10/2026 alle 16 circa, 127 run.
set -euo pipefail
R=daniel-g-carrasco/meridiana
S="${1:-$(cd "$(dirname "$0")" && pwd)}"
gh run list --repo $R --limit 400 --json databaseId,createdAt,conclusion,event,headBranch > "$S/runs.json"
gh run list --repo $R --limit 400 --json databaseId,createdAt,conclusion,event \
  --jq '.[] | "\(.createdAt[:10]) \(.conclusion) \(.event)"' | sort | uniq -c > "$S/runs-per-day.txt"
: > "$S/timing.txt"
: > "$S/jobs.txt"
for id in $(gh run list --repo $R --limit 400 --json databaseId --jq '.[].databaseId'); do
  t="$(MSYS_NO_PATHCONV=1 gh api "repos/$R/actions/runs/$id/timing" \
       --jq '[(.run_duration_ms|tostring), ([.billable | to_entries[] | "\(.key)=\(.value.total_ms)"] | join(" "))] | join(" ")' \
       2>/dev/null || echo "no-timing")"
  echo "$id $t" >> "$S/timing.txt"
  # i job (nome, secondi, esito) dei run che sono partiti davvero: GitHub fattura ogni job arrotondato al minuto
  MSYS_NO_PATHCONV=1 gh api "repos/$R/actions/runs/$id/jobs" \
    --jq '.jobs[] | "'"$id"' \(.name) \((.completed_at|fromdateiso8601) - (.started_at|fromdateiso8601)) \(.conclusion)"' \
    >> "$S/jobs.txt" 2>/dev/null || true
done
echo "scritti in $S: runs.json, runs-per-day.txt, timing.txt, jobs.txt"
