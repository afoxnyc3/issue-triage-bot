# Execution status

Updated: 2026-09-18. Durable goal active; no milestone is yet complete.

## Current milestone / checkpoint

M1 live release loader passes local acceptance. GitHub client, policy, security
gate, snapshot and ownership reconciliation are committed. M0 live gate remains pending; M2/M3 not started; M4 deferred.

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

## Latest completed/checkpoint work

- 70d4758: deterministic policy/gates/snapshots and explicit label ownership.
- 06610ab: bounded GitHub client with complete pagination, guarded writes, scoped
  reads, safe retries and lost-response handling (139 tests at that revision).
- Current checkpoint: live default-head release loader; control/policy/prompt and
  inference fetched at one immutable commit; all raw file digests plus generation,
  provider/model/action/schema/config identity bound together. Missing/disabled
  control exits before inference configuration or policy reads.
- Committed prompt v1, exported strict decision schema and candidate Sonnet 4.6
  configuration. Official model-ID documentation identifies claude-sonnet-4-6 as a
  fixed identifier, not an evergreen alias. Personal Max availability and isolation
  remain live M0 checks; no model invocation occurred.
- Type-label mode requires a canary in this first release contract. Removing the
  cap after reviewed M3 evidence remains an explicit future rollout checkpoint.

Files: src/issue_triage_bot/{config,release}.py, triage/{PROMPT.md,inference.yml,schema.json},
tests/unit/test_release.py, EXECUTION_STATUS.md.

## Verification

- Release loader: 18 tests cover coherent commit reads, missing/disabled control,
  missing release files, digest changes without generation bumps, schema drift,
  canary requirement and rejected weakened/coerced inference flags.
- `uv run --locked pytest -q`: all 157 tests pass on Python 3.12.12.
- Ruff lint/format, strict mypy (10 source files), `git diff --check`: pass.
- Read-only pinned CI is defined but has not run remotely. No live/inference/write
  acceptance is inferred from the local suite.

## Exact next checkpoint

M1 apply state machine: invoke fresh release/control/issue fences immediately before
EVERY write, persist signed pending intent before labels, reconcile/read back/finalize,
resume uncertain boundaries, and emit bounded redacted outcome records. Dry-run and
shadow must never write. Add fault injection with the full live-release loader.
Then CLI and remaining M0/M2 workflow/privacy/budget boundaries.

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
