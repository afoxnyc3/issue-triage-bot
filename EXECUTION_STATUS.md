# Execution status

Updated: 2026-09-18. Durable goal active; no milestone is yet complete.

## Current milestone / checkpoint

M1 deterministic GitHub client passes mocked acceptance. Policy, security gate,
snapshot and ownership reconciliation are committed. M0 live gate remains pending; M2/M3 not started; M4 deferred.

## Completed checkpoints

- 741717f: all 15 execution amendments recorded in PLAN.md; historical review kept.
- 8bff36d: reproducible source-level loss of `--tools ""` in candidate Action parser.
- 899fdc2: traced SDK/CLI transport. Initial owner-review stop was premature; an
  argument representation failure is not a failed live M0 check. Candidate `--tools=`
  preserves the explicit empty value. No tools/runtime acceptance is claimed.
- be62161: strict frozen issue/decision/envelope/release/run models;
  bounded JSON rejects unknown/duplicate fields, coercions and nonfinite numbers;
  complete content and all release/model metadata participate in hashes/fences;
  stale content and cross-issue/run/attempt proposals rejected.
- Legacy workflow now manual-trigger-only AND job-disabled locally. Legacy source,
  classifier, memory and migration remain untouched. Remote workflow unchanged.
- Replaced project dependencies with deterministic application dependencies; uv.lock
  is committed with this checkpoint. Legacy SDK is no longer in the active environment.
- Read-only CI pins checkout/setup-uv and runs locked installs, Ruff, mypy and pytest
  on Python 3.11/3.12. CI definition is statically tested, not yet run on GitHub.

## Latest completed/checkpoint work

- 88c1dd1: signed state/key rotation, author/identity verification, fail-closed marker
  discovery and sanitized rendering (86 tests at that revision).
- Current checkpoint: strict YAML policy/control parsing with duplicate keys and
  aliases rejected; committed disabled/dry-run defaults; full-content security gate,
  shared UTF-8 snapshot bound, type mapping/allowlist, sensitive and retry outcomes,
  no automatic priority labels, timeline-backed signed ownership reconciliation.
- Recovery ownership now uses pending_additions separately from intended_labels.
  This preserves unowned legacy labels even when a pending intent names them.
- Configuration interpretation: comment_only suppresses model type-label writes;
  deterministic review/retry/deferred control labels remain permitted by the plan's
  explicit safety/recovery paths. Dry-run and shadow must perform zero GitHub writes
  (to be enforced in apply). No live rollout authorization is implied by these defaults.

## GitHub client checkpoint

- 70d4758: policy/gate/snapshot and signed ownership reconciliation (110 tests).
- Current: bounded authenticated REST reads, strict normalization, full comment and
  label-timeline pagination, default-head/immutable-ref release file reads, scoped
  related search, read-only default and explicit guard before each mutation.
- Read retries classify 429/5xx/secondary limits with bounded delay; mutations are
  never blindly retried after uncertain responses. Apply must rediscover signed
  pending state and reconcile before retrying a write.
- Short pages honor validated next links; external/jumping links fail closed. Label
  segments are encoded including `.`/`..`; unrelated issue comment edits are rejected.
- Raw API error bodies are never propagated; duplicate JSON fields are rejected.

Files: src/issue_triage_bot/{codec,github}.py, tests/unit/test_github.py,
EXECUTION_STATUS.md.

## Verification

- GitHub targeted suite: 29 tests pass using HTTPX MockTransport; no network/token
  used by tests. Includes missing/invalid identities, pagination, failure after page
  one, read retries, write-guard rejection, lost response without duplicate POST,
  wrong comment target, release reads, query injection and path/redirect fencing.
- `uv run --locked pytest -q`: all 139 tests pass on Python 3.12.12.
- Ruff lint/format, strict mypy (9 source files), `git diff --check`: pass.
- Foundation tests also previously passed on Python 3.11.15. New client has not been
  exercised live; no integration/milestone acceptance is inferred from mocks.
- Diff review confirms no actual credentials, broad API writer, model SDK or remote
  mutation. Public REST/HTTPX primary docs informed endpoint and mock behavior.

## Exact next checkpoint

M1 apply state machine: fresh release/control/issue fences before every write,
comment-first pending intent, explicit ownership, label-by-label reconciliation,
read-back/finalization and resume after every uncertain boundary. Dry-run/shadow
must never mutate. Add fault-injection tests, then CLI and M0/M2 workflow wiring.

## Owner actions / remaining acceptance

- Only the owner confirms personal Max identity, generates/stores OAuth outside
  Codex, attests billing attribution and records rotation/expiry without token value.
- Publishing/running the eventual reviewed M0 harness needs authorization; no push
  or live GitHub writes have been performed. No secret was accessed or modified.
- M1 GitHub dry-run and real issue acceptance, all M2 integration checks, adversarial
  evaluation plus real shadow observations, approved comment/type-label rollout,
  operational runbooks and safe cutover remain required. Priority stays advisory.
- No live model, workflow isolation or log-privacy acceptance is claimed.

## Preservation and limits

Started at main f0b84f9, already ahead of origin/main. Owner's initial PLAN.md was
explicitly authorized for amendment/commit. CODEX_EXECUTION_PROMPT.md and .claude/
remain untouched/untracked. No AGENTS.md/CLAUDE.md found in root/ancestor paths.
No push/merge/release, secret operation or inference performed. The legacy workflow
is not disabled remotely until the owner publishes these changes. Local legacy
code is retained for cutover/history; its old SDK environment is no longer installed.
