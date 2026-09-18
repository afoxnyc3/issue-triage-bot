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

- 76a9df9: guarded operator CLI and redacted dry-run audits (211 tests).
- Current M0 evidence checkpoint: strict two-field probe output, bounded SDK execution
  parsing, exact model identity, empty built-in/MCP inventories, no tool-call blocks,
  successful bounded turns and absent environment/file canaries. Known literal,
  case-folded, base64 and hex canary representations are rejected throughout messages.
- Deterministic GitHub probe must observe HTTP 403 and the integration-permission
  denial message. Rate limiting, unauthorized/invalid endpoint responses and model
  claims do not establish read-only enforcement.
- Evidence contains only hashes, model/action identity and fixed booleans. It cannot
  mark M0 passed: non-collaborator trigger, full log/artifact privacy, personal billing
  and token lifecycle remain explicitly pending owner/live-run evidence.

Files: src/issue_triage_bot/m0.py, tests/unit/test_m0.py, EXECUTION_STATUS.md.

## Verification

- 30 focused tests cover healthy metadata, tool inventory/calls, model mismatch,
  malformed/duplicate/incomplete/reordered execution, bad structured output and turns,
  canary encodings and permission-denial distinction. No real inference was invoked.
- Full suite: 241 tests pass on Python 3.12.12; Ruff formatting/lint, strict mypy
  (13 source files), and git diff --check pass.
- Canary matching is evidence for tested representations, not proof against every
  possible encoding. Ephemeral execution files must never be uploaded. The validator
  alone cannot inspect complete Actions logs or prove subscription attribution.

## Exact next checkpoint

M0 disabled workflow harness: trusted credential-free build/preparation, isolated
no-checkout read-only inference job, scoped OAuth input, independent permission probe,
local redacted validation and metadata-only artifact. Verify wiring statically and
with mocked runtime fixtures, then document the exact owner-operated live sequence.

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
