# Execution status

Updated: 2026-09-18. Durable goal active; no milestone is yet complete.

## Current milestone / checkpoint

M1 signed comment-state codec and safe rendering pass local acceptance. Strict
trust-boundary models, hashing, locked tooling and disabled legacy workflow are committed. M0 live gate remains pending.
M2/M3 have not started; M4 is optional/deferred.

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

## Signed-state checkpoint

HMAC-SHA256 over canonical key-ID/payload data; current/previous-key rotation;
bounded signed state; author/type/repository/issue/node authentication; malformed,
unsigned, duplicate and unknown-version state fails closed. Discovery considers
all supplied comments and ignores foreign-author markers. Rendering bounds model
fields, strips HTML/link/image markup and neutralizes mentions/issue autolinks.
Related references are deliberately not rendered until later GitHub verification.

Files: src/issue_triage_bot/{models,codec,comment,sanitize}.py,
tests/unit/test_comment.py, EXECUTION_STATUS.md.

## Verification

- Foundation checkpoint: locked sync, 49 tests on Python 3.11.15 and 3.12.12,
  Ruff formatting/lint and strict mypy passed; read-only pinned CI statically tested.
- Signed-state targeted tests: 37 pass (forgery, signatures, key rotation/retirement,
  author spoofing, identity replay, duplicate/version markers, all-comment discovery,
  size bounds, invalid state transitions/timestamps and hostile rendering).
- `uv run --locked pytest -q`: all 86 tests pass on Python 3.12.12.
- `uv run --locked ruff check src tests`: passes.
- `uv run --locked ruff format --check src tests`: passes before commit.
- `uv run --locked mypy`: passes (5 application files).
- `git diff --check`: passes. Keys in tests are ephemeral random values; no real
  secrets, model calls, remote writes or raw issue content were accessed/logged.
- No live milestone acceptance is inferred from these local tests.

## Exact next checkpoint

M1 deterministic policy/security gate: strict YAML policy/control configuration,
full-content security scan, advisory priority, bounded UTF-8 snapshot, mapping and
signed-state/timeline label ownership reconciliation tests. Then GitHub client,
apply state machine, CLI and fault-injection checkpoints. M0 harness/live checklist
remains required; foundations may continue without credentials.

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
