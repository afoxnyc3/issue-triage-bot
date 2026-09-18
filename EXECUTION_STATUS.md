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

- 70d4758: deterministic policy/gates/snapshots and explicit label ownership.
- 06610ab: bounded GitHub client, complete pagination, guarded mutations (139 tests).
- 6be3e38: coherent live release loading, prompt/schema/inference identity (157 tests).
- Current: comment-first signed pending state, mutation-by-mutation reconciliation,
  timeline and live release/content rechecks at each write, read-back/finalization,
  same-content pending resume and edited-content abandonment/cleanup. Uncertain
  writes leave discoverable state; no blind mutation retry occurs.
- Human overrides during durable reservation are rechecked before mutation. Fresh
  review_only routing overrides earlier pending classification. Sensitive model
  outcomes win over bad related references; only verified related links are rendered.
- Replays/unchanged final outcomes skip. Exhausted retries cannot restart through
  a deferred run. Explicit operator force_decision is available for fixture/manual
  reclassification, but does not bypass release, content, sensitive or rollout gates.
- Dry-run/shadow never mutate. Canary label writes require a reservation callback;
  absent/denied accounting leaves signed pending state. The durable implementation
  of that callback is still required before runtime type-label integration.
- Invalid/duplicate/unsupported signed state produces invalid_state audit with no
  guessed ownership or writes. Repair and health integration must surface it for
  human review (not yet implemented).
- Bounded audit records contain only accepted envelope, hashes, operation results,
  label sets and timestamps. Unknown after-label state is null, not falsely empty.

Files: src/issue_triage_bot/{apply,comment,models}.py,
tests/integration/test_apply.py, EXECUTION_STATUS.md.

## Verification

- Apply integration/fault-injection suite: 39 tests pass; real live-release loader,
  strict schemas, signing, policy and rendering operate against an in-memory GitHub
  gateway. Failures injected after all initial and edit write boundaries, including
  successful create/finalize with a lost response.
- Covered kill switch before labels/finalization/after reservation, policy/prompt/
  generation/content drift, forged states, human override races, sensitive outcomes,
  retry exhaustion, all nonwriting modes, canary denial/cohort and safe related links.
- `uv run --locked pytest -q`: all 196 tests pass on Python 3.12.12.
- Ruff lint/format, strict mypy (11 source files), `git diff --check`: pass.
- No remote CI/run/write acceptance is claimed. No real credentials or inference
  were used. Remaining actual network TOCTOU is bounded by immediate per-write
  refetches; GitHub does not offer atomic compare-and-swap label mutations.

## Exact next checkpoint

M1 CLI: triage apply/check/setup-labels/repair with dry-run safety, strict workflow
context, redacted errors/audits and explicit runtime secret loading (never run with
real secrets in this task). Connect the concrete client's guard to Apply.guard.
Then preflight/retry/admission accounting, M0 harness and M2 workflow wiring.

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
