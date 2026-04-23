#!/usr/bin/env bash
set -euo pipefail

: "${SONAR_TOKEN:?Set SONAR_TOKEN first}"

PROJECT_KEY="SkyNet12345678_icloud-file-sorter"
OUT_FILE="sonar-issues.json"

curl --fail --silent --show-error \
  -H "Authorization: Bearer $SONAR_TOKEN" \
  "https://sonarcloud.io/api/issues/search?componentKeys=${PROJECT_KEY}&resolved=false&ps=500&p=1" \
  -o "$OUT_FILE"
