# Execution status

Updated: 2026-09-18. Durable goal active; no milestone is yet complete.

## Current milestone / checkpoint

M1 credential-free foundation: strict trust-boundary models, hashing, locked tooling
and disabled legacy workflow pass local acceptance. M0 live gate remains pending.
M2/M3 have not started; M4 is optional/deferred.

## Completed checkpoints

- 741717f: all 15 execution amendments recorded in PLAN.md; historical review kept.
- 8bff36d: reproducible source-level loss of `--tools ""` in candidate Action parser.
- 899fdc2: traced SDK/CLI transport. Initial owner-review stop was premature; an
  argument representation failure is not a failed live M0 check. Candidate `--tools=`
  preserves the explicit empty value. No tools/runtime acceptance is claimed.
- Current checkpoint: strict frozen issue/decision/envelope/release/run models;
  bounded JSON rejects unknown/duplicate fields, coercions and nonfinite numbers;
  complete content and all release/model metadata participate in hashes/fences;
  stale content and cross-issue/run/attempt proposals rejected.
- Legacy workflow now manual-trigger-only AND job-disabled locally. Legacy source,
  classifier, memory and migration remain untouched. Remote workflow unchanged.
- Replaced project dependencies with deterministic application dependencies; uv.lock
  is committed with this checkpoint. Legacy SDK is no longer in the active environment.
- Read-only CI pins checkout/setup-uv and runs locked installs, Ruff, mypy and pytest
  on Python 3.11/3.12. CI definition is statically tested, not yet run on GitHub.

## Current checkpoint files

.github/workflows/{triage,ci}.yml, .gitignore, pyproject.toml, uv.lock,
src/issue_triage_bot/{__init__,models,codec}.py,
tests/conftest.py, tests/unit/{test_models,test_workflows}.py, EXECUTION_STATUS.md.

## Verification

- `uv sync --locked --group dev`: passes.
- `uv run --locked pytest tests/unit/test_models.py -q`: 47 pass.
- `uv run --locked pytest -q`: 49 pass on Python 3.12.12.
- Isolated locked Python 3.11.15 environment: same 49 tests pass.
- `uv run --locked ruff check src tests`: passes.
- `uv run --locked ruff format --check src tests`: passes before final commit.
- `uv run --locked mypy`: passes (3 application source files).
- `git diff --check`: passes.
- Initial tests caught JSON tuple validation being disrupted by a pre-validator;
  moved Unicode validation after field parsing and verified valid and hostile cases.
- Reviewed changed code for untrusted rendering/logging and credentials: no writes,
  model calls, secret reads or untrusted error payloads in this foundation slice.
- Action parser diagnostic remains a deliberately failing representation probe;
  docs/m0/{REVIEW.md,parser-contract-result.json,transport-review.json} preserve scope.

## Exact next checkpoint

M1 signed comment-state codec: HMAC-SHA256, key IDs/current+previous rotation,
author/repository/issue/node binding, safe rendering and forged/duplicate marker
rejection. Add adversarial tests before policy/reconciliation/client work. Continue
unblocked credential-free checkpoints; never mark M0 passed without live evidence.

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
