# n8n Import Validation — Phase 12

Phase 12 validates the packaged BotFucker n8n workflows against a real n8n target while keeping everything inactive, dry-run, and sample-only. The validation target used for this phase is `n8n-vps`, running n8n 2.18.5 in Docker.

This is still not OAuth work. no Gmail, no Microsoft, no IMAP, no SMTP, and no provider mutation credentials are attached. We are proving that the workflow exports import and that the approved-action bridge can exercise a dry-run path with sample data. Very glamorous. Like QA, but with fewer party hats.

## Artifacts under validation

- `docs/n8n-workflow.json` — local review import starter workflow.
- `docs/n8n-approved-action-bridge.json` — approved-action bridge dry-run workflow.
- `samples/approved-actions.sample.json` under n8n's allowed local-files directory, `/home/node/.n8n-files`. n8n 2.18.5 blocks Read/Write Files access outside that directory unless configured otherwise.
- `scripts/validate_n8n_workflow_exports.py` — static preflight check before n8n import.

## Static preflight

Run locally before copying anything to n8n:

```bash
python3 scripts/validate_n8n_workflow_exports.py
```

The script verifies both workflow exports are inactive, manual-triggered, credential-free, and free of obvious provider mutation nodes/terms. It also verifies the approved-action bridge includes `botfucker.approved_actions.v1`, `audit_id`, and `dry_run` markers.

## Real n8n target

Target checked during Phase 12:

```bash
ssh n8n-vps 'docker exec n8n-n8n-1 n8n --version'
# 2.18.5
```

Container:

```text
n8n-n8n-1
```

## Sample-only import procedure

Copy workflow exports and sample bundle to the n8n host/container:

```bash
scp docs/n8n-workflow.json docs/n8n-approved-action-bridge.json samples/approved-actions.sample.json n8n-vps:/tmp/
ssh n8n-vps 'docker exec n8n-n8n-1 mkdir -p /tmp/botfucker-phase12'
ssh n8n-vps 'docker cp /tmp/n8n-workflow.json n8n-n8n-1:/tmp/botfucker-phase12/n8n-workflow.json'
ssh n8n-vps 'docker cp /tmp/n8n-approved-action-bridge.json n8n-n8n-1:/tmp/botfucker-phase12/n8n-approved-action-bridge.json'
ssh n8n-vps 'docker cp /tmp/approved-actions.sample.json n8n-n8n-1:/home/node/.n8n-files/approved-actions.sample.json'
```

Import as inactive/manual workflows:

```bash
ssh n8n-vps 'docker exec n8n-n8n-1 n8n import:workflow --input=/tmp/botfucker-phase12/n8n-workflow.json'
ssh n8n-vps 'docker exec n8n-n8n-1 n8n import:workflow --input=/tmp/botfucker-phase12/n8n-approved-action-bridge.json'
```

After import, verify both workflow rows are `active = 0` before any execution attempt.

## Dry-run execution target

Only the approved-action bridge is suitable for Phase 12 dry-run execution because it reads a local sample bundle and logs `would_execute` records with `provider_execution: not_performed`.

Use the sample bundle only:

```bash
ssh n8n-vps 'docker exec -e BOTFUCKER_APPROVED_ACTIONS=/home/node/.n8n-files/approved-actions.sample.json n8n-n8n-1 n8n execute --id=<approved-action-bridge-workflow-id>'
```

Expected behavior:

- schema `botfucker.approved_actions.v1` is accepted
- `audit_id` is used as the dedupe key
- output is dry-run / `would_execute`
- `provider_execution` remains `not_performed`
- no provider mailbox mutation occurs

## Cleanup

Delete validation workflows after the test unless Kent explicitly wants them left in n8n.

Deletion can be done through the n8n UI or by removing only the validation rows from n8n's SQLite tables by exact workflow name. If doing SQL cleanup, delete validation workflows from `workflow_entity` and related rows such as `workflow_history`, `shared_workflow`, `workflow_statistics`, and `workflow_dependency` by exact workflow ID. Do not touch unrelated workflows. Yes, the obvious warning is necessary, because databases are where confidence goes to die.

## Validation result

Actual Phase 12 run on `n8n-vps` / n8n 2.18.5:

- Static preflight passed with `python3 scripts/validate_n8n_workflow_exports.py`.
- Both workflows imported successfully as inactive/manual workflows after adding explicit workflow IDs:
  - `botfucker-local-review-import-v1`
  - `botfucker-approved-action-bridge-dry-run-v1`
- Import verification showed both `active = 0`.
- Approved-action bridge dry-run executed successfully against `samples/approved-actions.sample.json` copied to `/home/node/.n8n-files/approved-actions.sample.json`.
- Final dry-run node emitted:
  - `dry_run: true`
  - `would_execute: approve_warning`
  - `audit_id: audit-sample-0001`
  - `provider_execution: not_performed`
  - `bridge_status: dry_run_logged_only`
- No Gmail, Microsoft, IMAP, SMTP, or provider mutation credentials were attached.
- Cleanup completed: validation workflow rows, related workflow history/dependency/statistic/share rows, sample execution rows, and temp sample files were removed.

Compatibility fixes discovered the hard way, because naturally n8n had opinions:

1. n8n 2.18.5 CLI import requires workflow exports to include non-null `id` values.
2. Read/Write Files access is restricted to `/home/node/.n8n-files` on this target.
3. `readWriteFile` returns file contents as binary data; the Code node must parse with `await this.helpers.getBinaryDataBuffer(0, 'data')` before validating the approved-action schema.
