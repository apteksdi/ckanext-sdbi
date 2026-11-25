# CKAN Logs Agent (ERROR → Telegram + Sysadmin UI)

Date: 2026-11-10  
Status: Approved (brainstorm)  
Ticket: SCOL-1234 (placeholder)

## Problem

Ops debugging for Portal Data BNPB relies on manual `docker logs` across `ckan`, harvest workers, and `datapusher`. ERROR spikes are easy to miss; there is no lightweight alert path and no sysadmin view of recent ERROR alerts.

## Goal

Ship a **low-CPU** logs agent that:

1. Watches ERROR lines from `ckan`, `ckan-harvest-*`, and `datapusher`.
2. Sends short Telegram alerts with a **15-minute** send interval and **max 200 characters**.
3. Persists alert records for **7 days** (plus a size cap).
4. Exposes a **sysadmin-only** read-only UI in CKAN for recent alerts.

Primary user: sysadmin / DevOps (Telegram first). Secondary: sysadmin browser drill-down.

## Decision

**Lean Docker sidecar + SQLite shared volume + thin `ckanext-sdbi` sysadmin page.**

- Do **not** use `ckanext-logs` (file viewer only; no Telegram; assumes `/var/log/ckan` files).
- Do **not** run monitoring inside uWSGI / CKAN workers.
- Do **not** wire LLM in v1 (optional future hook only).
- Do **not** rebuild the full stack; add/build only `ckan-logs-agent`, and redeploy `ckan` when the sdbi UI lands.

## Architecture

```
docker logs (ckan, harvest-*, datapusher)
        │
        ▼
┌─────────────────────┐
│  ckan-logs-agent    │  CPU/mem capped sidecar
│  ERROR rule gate    │
│  cooldown 15 min    │
│  Telegram ≤200 char │
│  SQLite persist     │
└─────────┬───────────┘
          │ shared volume (SQLite)
          ▼
┌─────────────────────┐
│  ckanext-sdbi       │  sysadmin-only alerts table
│  /ckan-admin/...    │  read-only mount
└─────────────────────┘
```

### Sidecar (`ckan-compose/logs-agent/`)

| Path | Role |
|------|------|
| `Dockerfile` | Small Python image |
| `requirements.txt` | docker SDK / httpx / etc. |
| `app/main.py` | Tail loop + reconnect |
| `app/rules.py` | `\bERROR\b` match + fingerprint |
| `app/telegram.py` | `sendMessage`, truncate to 200 chars |
| `app/store.py` | SQLite write + 7-day prune + size cap |
| `app/config.py` | Env config |

Compose service `ckan-logs-agent`:

- Read-only Docker socket (or equivalent) to stream target containers.
- Resource caps (target: ~0.25 CPU, ~128 MB).
- RW volume for SQLite; same volume RO on `ckan`.
- Env for Telegram and agent settings (not baked into image).

### Watched containers (v1)

- `ckan`
- All `ckan-harvest-*` workers present in compose
- `datapusher`

Not in v1: Solr, Redis, Postgres.

## Detection rules (v1)

- Match log lines containing `\bERROR\b` only.
- No WARNING/INFO, no LLM classification, no harvest/datapusher-specific extra rules unless the line already contains `ERROR`.
- Fingerprint = container + normalized message (stable enough for cooldown).

## Telegram

| Setting | Value |
|---------|--------|
| Channel | Telegram bot (`BOT_TOKEN` + `CHAT_ID`) |
| Max message length | **200 characters** (hard truncate) |
| Send interval | **15 minutes per fingerprint** (not a global mute of all alerts) |
| On Telegram failure | Keep SQLite row (`telegram_sent=0`); one retry; do not crash agent |
| Dry-run | `LOGS_AGENT_DRY_RUN=1` prints payload, skips send |

Suggested env:

```bash
LOGS_AGENT_TELEGRAM_BOT_TOKEN=...
LOGS_AGENT_TELEGRAM_CHAT_ID=...
LOGS_AGENT_COOLDOWN_MINUTES=15
LOGS_AGENT_TELEGRAM_MAX_CHARS=200
LOGS_AGENT_CONTAINERS=ckan,ckan-harvest-gather,ckan-harvest-fetch,ckan-harvest-run,ckan-harvest-cleanlog,datapusher
LOGS_AGENT_DRY_RUN=0
```

Message shape (within 200 chars): container, short time, truncated ERROR excerpt.

During cooldown: **always store** matching ERROR lines for the UI; **do not** send Telegram for that fingerprint until the 15-minute window opens.

## Retention

- Alert store (SQLite), not Docker’s own log driver rotation.
- Auto-delete alerts older than **7 days**.
- Hard cap: prune oldest when either **10,000 rows** or **~50 MB** DB file size is exceeded (whichever hits first).
- Do not wait for “disk full” as the only cleanup trigger.

Docker log rotation for containers remains a separate compose `logging:` concern if needed.

## Sysadmin UI (`ckanext-sdbi`)

- Sysadmin-only route (e.g. `/ckan-admin/logs-alerts`) linked from admin/dashboard.
- Read-only table of recent ERROR alerts from the shared SQLite volume.
- Columns: time, container, fingerprint/rule, excerpt, Telegram sent yes/no.
- Filters: container, date range; pagination.
- Empty state if DB missing or agent not running.
- Non-sysadmin → 403.

No live `docker logs` streaming in the browser in v1.

## Error handling

- Missing container / Docker disconnect: warn + backoff reconnect; never impact CKAN request path.
- Telegram outage: persist locally; retry once.
- SQLite errors: log; keep tailer alive when possible.
- Agent crash: Compose restart of sidecar only.

## Testing

- Unit: ERROR matcher, fingerprint, cooldown, 200-char truncation.
- Local Colima: dry-run or real bot; inject ERROR → one Telegram within rules; second within 15 min suppressed.
- Manual: sysadmin sees row; non-sysadmin blocked.

## Out of scope (v1)

- LLM summarization (keep a future hook only)
- `ckanext-logs` / `ckanext-tables`
- Solr / Redis / DB log watching
- Live log tail in UI, mute commands, Slack/email
- Full-stack image rebuild for unrelated services

## Success criteria

- ERROR in watched containers produces at most one Telegram per fingerprint per 15 minutes, ≤200 chars.
- Alerts appear in SQLite and in sysadmin UI; pruned after 7 days / size cap.
- CKAN web CPU unaffected by monitoring (sidecar capped).
- Adding the agent does not require rebuilding Solr/Redis/datapusher/harvest images; UI needs `ckan`/`ckanext-sdbi` redeploy only.

## Implementation sketch

1. Scaffold `ckan-compose/logs-agent/` and unit tests for rules/cooldown/truncate.
2. Add `ckan-logs-agent` to compose (dev + prod) with socket, volume, resource limits, env.
3. Implement tail → ERROR → store → Telegram path with dry-run.
4. Add `ckanext-sdbi` sysadmin controller + template + link; mount alerts volume RO on `ckan`.
5. Document BotFather setup and env vars in compose README or short how-to.
6. Smoke on Colima, then prod: enable Telegram secrets, verify one ERROR alert and UI.
