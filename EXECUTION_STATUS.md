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
- d60a948: bounded M0 evidence validator (241 tests).
- Current M0 harness checkpoint: default-off issue-number gate, trusted credential-free
  validator build, same-run artifact hashes verified before execution, no-checkout
  probe job with contents/issues read only, protected triage-m0 environment, OAuth
  scoped to the pinned Action input, and an independent single forbidden-write probe.
- Bounded non-collaborator issue-opened fixture, same-job masking including JSON forms,
  two private ephemeral canaries, strict no-tool candidate configuration, local SDK
  evidence validation, metadata-only 30-day audit artifact and always-run cleanup.
  Build artifact contains trusted code/locked dependencies only and expires in one day.
- RUNBOOK.md documents the exact owner sequence, denial semantics, full-log review,
  personal billing/lifecycle attestation and stop-on-failure rule. No live M0 item is
  checked off. The legacy workflow remains locally disabled and remotely unchanged.

Files: .github/workflows/triage-m0.yml, src/issue_triage_bot/m0_runtime.py,
tests/unit/test_m0_runtime.py, docs/m0/{REVIEW,RUNBOOK}.md, EXECUTION_STATUS.md.

## Verification

- 17 runner/workflow tests pass: event/association/bounds/debug guards, same-job masking,
  secret-free preparation, single denied write with no retry, redacted local validation,
  permission/checkout/OAuth/artifact boundaries and tampered bundle rejection.
- Full suite: 258 tests pass on Python 3.12.12 and Python 3.11.15. Ruff formatting/lint,
  strict mypy (14 source files), and git diff --check pass.
- Built a wheel, installed exported hash-locked dependencies into a separate temp
  environment, and ran the installed package through prepare/mock denial/mock SDK/
  validate. Pass; no OAuth or real GitHub request occurred.
- Workflow parsing and executable helper behavior are locally tested; GitHub's remote
  workflow validation, actual Linux Action/CLI execution and full logs are unverified.
- The pinned Action logs context prompts and may log SDK errors. Masks cover known
  literal/JSON forms; full live privacy review remains mandatory. Canary checks cannot
  prove absence of every conceivable encoding. No fallback tools/permissions are added.

## Exact next checkpoint / genuine owner blocker

M0 live acceptance now requires the owner-only sequence in docs/m0/RUNBOOK.md:
authorize publishing, configure the protected environment/one-fixture variables,
confirm personal Max using /status, run claude setup-token outside Codex and store it
directly as the repository OAuth secret, then obtain a non-collaborator fixture run
and redacted privacy/billing/lifecycle attestations. No token should enter this task.
CODEX_EXECUTION_PROMPT.md says to stop when this live owner action is required.
The same owner-only live M0 blocker was confirmed across three consecutive goal
turns. The last continuation made no implementation progress: it revalidated the
unchanged gate, not a running process. Current Git status still contains only the
preserved owner-untracked files; no live evidence or publishing authorization has
arrived. The durable goal is blocked on this owner action, not complete. This is
separate from the earlier resolved source-parser investigation. No milestone is
marked complete; resume with the redacted live M0 evidence described above.

After M0 passes, resume preflight/admission reservation accounting and M2 wiring,
followed by real M1/M2 acceptance, evaluation/shadow/write rollout, operations/cutover.
An actual M0 control failure requires architectural review, not a weakened check.

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
