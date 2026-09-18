# Execution status

Updated: 2026-09-18. Durable goal active; no milestone is yet complete.

## Current milestone / checkpoint

M1 apply state machine passes local fault-injection acceptance. No real GitHub
write or M0 inference has run; live M1 acceptance remains pending. M0 live gate remains pending; M2/M3 not started; M4 deferred.

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

- 04ea950: signed comment-first apply state machine and crash recovery (196 tests).
- Current M1 CLI checkpoint: installed `triage apply/check/setup-labels/repair` entry
  point; default dry-run, explicit workflow-context-bound apply writes, concrete
  per-write guards, bounded inputs and redacted errors/audits. No OAuth access.
- Dry-run reports include planned comment/label operations, decision hash and intended
  outcome. Label setup fences the full live release before each creation. Repair
  performs bounded read-only enumeration, excluding pull requests and rejecting
  foreign/duplicate issues; unreadable authenticated state is surfaced for review.
- Shared in-memory gateway moved to tests/fakes.py for CLI/integration verification.
  Operator contracts and runtime environment are documented in docs/CLI.md.

Files: pyproject.toml, src/issue_triage_bot/{cli,apply,github}.py,
tests/{__init__,fakes}.py, tests/unit/{test_cli,test_github}.py,
tests/integration/test_apply.py, docs/CLI.md, EXECUTION_STATUS.md.

## Verification

- Targeted CLI/GitHub tests: 44 pass, including default nonwriting behavior, explicit
  guarded comment-only writes, workflow mismatch, key redaction, repair enumeration,
  pagination and prompt drift between label creations.
- Full suite: 211 tests pass on Python 3.12.12. Ruff format/lint, strict mypy
  (12 source files) and git diff --check pass. No live credentials, model, GitHub
  writes or remote CI used.
- Apply canary mutations still require a durable reservation adapter. Repair remains
  inspection only. Early CLI failures can precede audit creation; workflow fallback
  audit handling is still needed. No model-dependent acceptance is claimed.

## Exact next checkpoint

Return to the earliest incomplete gate: implement and locally verify the M0 harness
and its redacted evidence validator. Keep it disabled pending owner publishing and
personal Max authentication/billing attestation. Then continue preflight/admission
and M2 workflow integration as allowed by M0 results.

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
