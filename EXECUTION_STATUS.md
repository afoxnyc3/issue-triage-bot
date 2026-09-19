# Execution status

Updated: 2026-09-18. Owner approved publication; live M0 acceptance remains blocked.

## Current milestone / checkpoint

M1 apply state machine passes local fault-injection acceptance. No issue mutation or M0 inference has run; live M1 acceptance remains pending.
Owner-approved publication and protected-environment configuration are complete. M0 live gate remains pending; M2/M3 not started; M4 deferred.

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
- Legacy workflow now manual-trigger-only AND job-disabled locally and on main. Legacy source,
  classifier, memory and migration remain untouched.
- Replaced project dependencies with deterministic application dependencies; uv.lock
  is committed with this checkpoint. Legacy SDK is no longer in the active environment.
- Read-only CI pins checkout/setup-uv and runs locked installs, Ruff, mypy and pytest
  on Python 3.11/3.12. Both jobs passed on GitHub run 35395096666 at 5b46739.

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
  checked off. The legacy workflow is now published in its disabled form.

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
- GitHub CI run 35395096666 passed all checks on Python 3.11 and 3.12 at 5b46739.
  Actual M0 Linux Action/CLI execution, effective isolation and full logs are unverified.
- The pinned Action logs context prompts and may log SDK errors. Masks cover known
  literal/JSON forms; full live privacy review remains mandatory. Canary checks cannot
  prove absence of every conceivable encoding. No fallback tools/permissions are added.

## Owner-approved publication checkpoint

- Published verified commits through 5b46739 to origin/main following the owner's
  explicit approval. Read-only GitHub CI completed successfully:
  https://github.com/afoxnyc3/issue-triage-bot/actions/runs/35395096666
- Created triage-m0 environment with required reviewer afoxnyc3, self-review blocked,
  and a main-branch-only deployment policy. Read-back confirms those settings.
- Set TRIAGE_M0_ENABLED=false and verified the value. At that publication checkpoint no fixture number was selected,
  no test issue opened, and no inference started and no repository secret inspected or
  modified. Production control remains disabled. Owner files remain untouched.
- This resolves publication/environment setup. Existing code verification applies;
  this follow-up changes documentation only, checked with git diff --check.

## First live attempt: authentication input unavailable

Run 35410229693 at c8dbd158042c2e2fe2476ab1ce8fbffa158bc4c8 was triggered by
non-collaborator clarke-pna opening issue #5 and approved by the owner. The validator
build/install, masked fixture setup and independent supplied-token write-denial step
passed. The Claude Action failed at authentication environment validation because
no authentication input was available. This does not demonstrate a rejected/expired
token; tool inventory, canary isolation, structured output and billing remain untested.
No M0 inference evidence artifact was produced. See docs/m0/REVIEW.md for redacted facts.

Set TRIAGE_M0_ENABLED=false after this completed attempt. Diagnostics read only job
metadata, allowlisted annotation classifications, artifact names/sizes and reviewed
upstream source. No token, secret metadata, raw logs or model transcripts were read.
No fallback permissions/tools/provider were added and production triage stays disabled.

## Exact next checkpoint / genuine owner blocker

The owner must verify the exact CLAUDE_CODE_OAUTH_TOKEN repository Actions secret in
afoxnyc3/issue-triage-bot (not an Actions variable, Codespaces/Dependabot secret, another
repository or an unrelated environment). Secret inspection/correction remains outside
Codex under the execution prompt. Then coordinate the next protected live attempt;
do not claim M0 passed from partial setup/write-denial success. Failed-job-only reruns
also need care: the validator artifact name includes run_attempt, so a fresh attempt
must build its own bundle. Personal Max billing/lifecycle attestations remain pending.

After M0 passes, resume preflight/admission reservation accounting and M2 wiring,
followed by real M1/M2 acceptance, evaluation/shadow/write rollout, operations/cutover.
An actual M0 control failure requires architectural review, not a weakened check.

## Owner actions / remaining acceptance

- Only the owner confirms personal Max identity, generates/stores OAuth outside
  Codex, attests billing attribution and records rotation/expiry without token value.
- Publishing was authorized and completed. Protected environment configured; The first M0 attempt
  failed with authentication input unavailable; the gate is disabled again. No secret was accessed or modified.
- M1 GitHub dry-run and real issue acceptance, all M2 integration checks, adversarial
  evaluation plus real shadow observations, approved comment/type-label rollout,
  operational runbooks and safe cutover remain required. Priority stays advisory.
- No live model, workflow isolation or log-privacy acceptance is claimed.

## Preservation and limits

Started at main f0b84f9, already ahead of origin/main. Owner's initial PLAN.md was
explicitly authorized for amendment/commit. CODEX_EXECUTION_PROMPT.md and .claude/
remain untouched/untracked. No AGENTS.md/CLAUDE.md found in root/ancestor paths.
Verified commits were pushed after explicit owner approval. No merge/release, secret
operation, issue mutation or inference performed. Legacy code is retained for
cutover/history; its old SDK environment is no longer installed.
