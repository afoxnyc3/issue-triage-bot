# Issue Triage Bot Refresh Plan

**Status:** Proposed for review  
**Purpose:** Alignment and challenge before implementation  
**Last updated:** 2026-09-18

## 1. Executive summary

The current repository is a useful proof of concept, but it is not ready for dependable production use. Its core workflow delegates GitHub, database, and shell operations to an autonomous Claude Code agent; its duplicate detection uses hash-derived values rather than semantic embeddings; its configuration is largely disconnected from the implementation; and its dependencies and deployment are not reproducible.

This plan proposes a focused rebuild around a deterministic application pipeline with a provider-neutral AI boundary. Anthropic and OpenAI will both produce the same validated domain object. Ordinary application code—not the model—will decide which GitHub and database operations are permitted and perform them.

The first useful release will support safe issue triage through either Anthropic or OpenAI. Duplicate detection will be restored afterward as an independent capability, once it has a real embedding implementation and measurable quality.

No implementation work should begin until the decisions in [Section 12](#12-decisions-to-review-and-challenge) are reviewed.

## 2. Goals

1. Support Anthropic and OpenAI as interchangeable triage providers.
2. Establish one stable, typed contract for issue input and triage output.
3. Prevent model output from directly controlling GitHub, the shell, or the database.
4. Make triage repeatable, testable, observable, and idempotent.
5. Restore genuine duplicate detection without coupling it to the selected language-model provider.
6. Produce reproducible local and GitHub Actions installations.
7. Consolidate the project onto one maintained branch with configuration-driven capabilities.

## 3. Non-goals for the first release

- A general-purpose coding agent.
- Arbitrary shell access for the model.
- Model-controlled MCP access to GitHub or PostgreSQL.
- Fully autonomous handling of sensitive security or critical-priority issues.
- Supporting every possible AI vendor through a generic framework.
- Rebuilding duplicate detection before the primary triage path is reliable.
- A hosted web dashboard or multi-tenant service.

These can be reconsidered after the dual-provider triage workflow is stable and measured.

## 4. Current-state assessment

### 4.1 Security and control

Issue content is untrusted input. The current agent can receive that input while holding GitHub write access, PostgreSQL full access, and shell access. This creates a prompt-injection path from an issue body to privileged tools.

The refreshed design will treat AI output as an untrusted proposal. It must pass schema validation and application policy before any side effect occurs.

### 4.2 AI integration

The project depends directly on the retired `claude-code-sdk` package name and hard-codes a Claude model. There is no application-level interface that an OpenAI implementation can satisfy.

The refreshed design will depend on the standard Anthropic and OpenAI Python SDKs. Each adapter will translate its vendor-specific request and response into shared domain models.

### 4.3 Classification

The classifier is described as TF-IDF-based but performs substring counting. Its declared confidence threshold is bypassed when any keyword matches. The main configuration file is not actually loaded.

Classification rules will either become real deterministic pre-processing or be removed. They will not silently compete with the model's decision.

### 4.4 Duplicate detection

The current memory script repeats bytes from a SHA-256 digest to create a 384-value vector. This is deterministic but not semantic: similar issue descriptions will not reliably be near each other. The PostgreSQL MCP server also does not generate the promised MiniLM embeddings.

Duplicate detection will therefore be considered unavailable until Milestone 5 is complete.

### 4.5 Delivery and operations

There are no tests, `uv.lock` is ignored, runtime dependencies are broadly unbounded, and several large packages are unused. The GitHub workflow does not provide its required database URL, does not declare explicit issue-write permission, and can post repeated comments when an issue is edited.

## 5. Design principles

1. **Model output is data, not authority.** The model returns a proposed `TriageDecision`; application policy controls side effects.
2. **Abstract the task, not the SDK.** The common provider interface describes issue triage rather than mirroring either vendor's message API.
3. **One internal vocabulary.** Repository-specific label names are mapped from stable domain values.
4. **Make invalid states difficult to represent.** Enumerations and validation constrain categories, priorities, confidence, and duplicate references.
5. **Keep providers replaceable.** Prompts and provider parameters remain adapter-specific where necessary, while the output contract stays shared.
6. **Be idempotent by default.** Reprocessing an issue updates the existing bot result instead of accumulating comments or labels.
7. **Prefer least privilege.** The model never receives credentials. The workflow receives only the permissions and secrets required for the configured operation.
8. **Measure before automating.** Dry-run and shadow modes precede automatic label or comment changes.

## 6. Target architecture

```text
GitHub issue event or CLI command
            |
            v
      GitHub client fetches issue
            |
            v
  Optional duplicate candidate lookup
            |
            v
       TriageRequest domain object
            |
            v
  AnthropicProvider | OpenAIProvider
            |
            v
  Validated TriageDecision proposal
            |
            v
     Policy and label mapping layer
            |
            v
  GitHub client applies approved changes
            |
            v
       Audit/metrics TriageResult
```

Suggested package layout:

```text
src/issue_triage_bot/
  cli.py
  config.py
  models.py
  policy.py
  prompts.py
  service.py
  github.py
  storage.py
  embeddings.py
  providers/
    base.py
    anthropic.py
    openai.py
tests/
  fixtures/
  unit/
  integration/
  contract/
```

## 7. Typed domain model

A typed domain model defines the concepts and valid states of the issue-triage application independently of GitHub, Anthropic, OpenAI, or PostgreSQL.

For example, `bug` and `chore` are valid internal issue kinds. They are not required to be the literal GitHub labels used by every repository.

```python
from enum import StrEnum

from pydantic import BaseModel, Field


class IssueKind(StrEnum):
    BUG = "bug"
    CHORE = "chore"
    FEATURE = "feature"
    DOCUMENTATION = "documentation"
    QUESTION = "question"
    SECURITY = "security"


class Priority(StrEnum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


class Complexity(StrEnum):
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"


class Issue(BaseModel):
    repository: str
    number: int = Field(gt=0)
    title: str
    body: str
    author: str
    existing_labels: set[str] = Field(default_factory=set)


class DuplicateCandidate(BaseModel):
    issue_number: int = Field(gt=0)
    title: str
    similarity: float = Field(ge=0, le=1)


class TriageRequest(BaseModel):
    issue: Issue
    allowed_kinds: set[IssueKind]
    duplicate_candidates: list[DuplicateCandidate] = Field(default_factory=list)


class TriageDecision(BaseModel):
    kind: IssueKind
    priority: Priority
    complexity: Complexity
    confidence: float = Field(ge=0, le=1)
    rationale: str
    duplicate_of: int | None = None
    missing_information: list[str] = Field(default_factory=list)
    suggested_assignees: list[str] = Field(default_factory=list)


class TriageResult(BaseModel):
    decision: TriageDecision
    provider: str
    model: str
    duration_ms: int = Field(ge=0)
    labels_applied: set[str] = Field(default_factory=set)
    comment_updated: bool = False
```

The repository-specific label mapping is a separate policy concern:

```yaml
label_mapping:
  bug: "type: bug"
  chore: "type: maintenance"
  feature: "type: feature"
  documentation: "type: docs"
```

This separation means both providers always return `IssueKind.BUG`, even when one repository uses `bug` and another uses `type: defect`. It also prevents a model from inventing arbitrary labels and applying them directly.

The initial vocabulary in this section is proposed, not final. Whether issues can have one primary kind or multiple kinds is an explicit review decision in Section 12.

## 8. Provider contract

The application-level provider boundary will be deliberately narrow:

```python
from typing import Protocol


class TriageProvider(Protocol):
    async def triage(self, request: TriageRequest) -> TriageDecision:
        ...
```

Provider selection will be configuration-driven:

```dotenv
LLM_PROVIDER=anthropic
LLM_MODEL=<configured-model-id>
ANTHROPIC_API_KEY=<secret>
# OPENAI_API_KEY=<secret when OpenAI is selected>
```

The Anthropic adapter will use the standard Anthropic Python SDK and structured output parsing. The OpenAI adapter will use the OpenAI Python SDK, the Responses API, and structured output parsing. Vendor-specific model parameters, refusal handling, request identifiers, and usage extraction will remain inside their respective adapters.

The application will not promise identical wording from both providers. It will require identical schema validity and comparable behavior against the same evaluation cases.

## 9. Milestones

### Milestone 1 — Establish a tested foundation

**Goal:** Convert the prototype into a maintainable Python application without enabling new production behavior.

#### Tasks

- Create the `src/issue_triage_bot/` package structure.
- Add the domain models described in Section 7.
- Replace manual argument parsing with a proper CLI.
- Introduce typed settings and explicit startup validation.
- Decide whether `config.yaml` remains or is replaced by one typed configuration format.
- Remove unused imports and dependencies.
- Stop ignoring `uv.lock`; generate and commit it.
- Configure current Ruff and pytest settings.
- Add unit tests for domain validation, configuration, classification policy, and label mapping.
- Add a `--dry-run` mode that performs no GitHub writes.
- Update project documentation to describe actual behavior.

#### Acceptance criteria

- `uv sync --locked` succeeds in a clean checkout.
- Linting, type checks, and tests pass.
- The CLI can load a fixture issue and produce a validated dry-run result.
- Unit tests require no external credentials or network access.
- Invalid priorities, confidence values, issue kinds, and label mappings fail clearly.

### Milestone 2 — Define the provider-neutral AI layer

**Goal:** Make the application independent of either vendor's SDK shape.

#### Tasks

- Define the `TriageProvider` protocol.
- Add a provider factory driven by `LLM_PROVIDER` and `LLM_MODEL`.
- Create shared prompt inputs while allowing provider-specific rendering.
- Separate deterministic policy from model judgment.
- Validate allowed kinds, priorities, duplicate references, assignees, and confidence.
- Define common timeout, retry, and error behavior.
- Add a fake provider for end-to-end application tests.
- Add provider contract tests.
- Test malformed output, refusal, timeout, authentication failure, and rate limiting.

#### Acceptance criteria

- The orchestration layer imports neither vendor SDK.
- A fake provider runs the complete dry-run workflow.
- Invalid model output cannot reach the GitHub write layer.
- Changing providers requires configuration rather than orchestration changes.

### Milestone 3 — Implement Anthropic and OpenAI providers

**Goal:** Offer equivalent triage capability through both APIs.

#### Tasks

- Implement `AnthropicProvider` with the standard asynchronous Anthropic client.
- Parse Anthropic structured output into `TriageDecision`.
- Implement `OpenAIProvider` with the asynchronous OpenAI client and Responses API.
- Parse OpenAI structured output into the same `TriageDecision` model.
- Keep vendor-specific request parameters inside each adapter.
- Record provider, model, duration, request identifier, token usage, and retry count.
- Add mocked response fixtures for both providers.
- Build an initial evaluation set of representative issues.
- Compare schema compliance, labels, priorities, latency, and usage.
- Document configuration examples for each provider.

#### Acceptance criteria

- Both providers pass the same contract suite.
- Both return the same application-level type.
- Neither provider receives GitHub tokens, database credentials, or shell access.
- Provider failures result in a clear, non-destructive workflow failure.

### Milestone 4 — Replace GitHub MCP with a safe integration

**Goal:** Make issue retrieval and updates deterministic, testable, and idempotent.

#### Tasks

- Implement a typed GitHub REST client.
- Fetch issue title, body, author, labels, and repository metadata.
- Read `CODEOWNERS` through application code.
- Validate proposed labels against the configured mapping and allowlist.
- Provide a setup/check command for required repository labels.
- Apply approved labels through the GitHub client.
- Maintain one bot comment using a hidden marker.
- Make `opened` and `edited` event processing idempotent.
- Add concurrency protection for rapid edits.
- Implement `--retriage-all` with pagination and bounded concurrency.
- Handle rate limits and transient failures.
- Add integration tests using mocked GitHub HTTP responses.

#### Acceptance criteria

- Reprocessing the same issue does not create duplicate comments.
- Editing an issue updates the existing bot comment.
- Issue content cannot directly invoke GitHub operations.
- Dry-run mode reports intended changes without performing them.
- Bulk retriage reports partial failures and does not use unbounded concurrency.

### Milestone 5 — Rebuild duplicate detection

**Goal:** Replace the demonstration hash with genuine, measurable semantic similarity.

#### Tasks

- Define an independent `Embedder` protocol.
- Select an initial embedding backend based on privacy, cost, latency, and operational burden.
- Replace PostgreSQL MCP with a restricted `psycopg` integration.
- Store repository, issue number, content hash, embedding provider, model, dimension, and timestamps.
- Scope similarity queries by repository by default.
- Exclude the current issue from its candidate results.
- Upsert embeddings when issue content changes.
- Honor age and threshold configuration.
- Support migrations when embedding dimensions or models change.
- Build labeled duplicate and non-duplicate evaluation cases.
- Tune thresholds using measured precision and recall.
- Make duplicate detection optional and fail-safe.

#### Acceptance criteria

- Similar fixtures rank above unrelated fixtures.
- Cross-repository candidates are excluded unless explicitly enabled.
- Embedding or database outages do not prevent ordinary triage.
- Database migrations and similarity queries have integration tests.
- Duplicate precision and recall are reported for the evaluation set.

### Milestone 6 — Harden CI and deployment

**Goal:** Provide a reproducible, least-privilege production workflow.

#### Tasks

- Update GitHub Actions runtime versions.
- Pin third-party actions to reviewed versions or commit SHAs.
- Install with `uv sync --locked`.
- Declare explicit `contents: read` and `issues: write` permissions.
- Add workflow concurrency keyed by repository and issue.
- Pass only the selected provider's API key.
- Provide database credentials only when duplicate detection is enabled.
- Remove Docker and `npx` runtime dependencies.
- Add lint, type-check, test, and build jobs for pull requests.
- Add a production triage job for issue events.
- Add job timeouts and useful failure summaries.
- Add automated dependency update configuration.
- Document secret provisioning and rotation.

#### Acceptance criteria

- CI succeeds from a clean runner using the committed lockfile.
- Production uses only the required permissions and secrets.
- Concurrent issue edits cannot produce overlapping writes.
- Logs contain no API keys, tokens, database URLs, or other credentials.

### Milestone 7 — Evaluate and roll out

**Goal:** Demonstrate useful quality before enabling automatic repository changes.

#### Tasks

- Build a versioned evaluation dataset from synthetic or appropriately anonymized issues.
- Measure label accuracy, priority agreement, schema failures, latency, usage, and estimated cost.
- Measure duplicate precision and recall when Milestone 5 is enabled.
- Run Anthropic and OpenAI in shadow or dry-run mode.
- Compare model decisions against human labels and review disagreements.
- Set confidence and policy thresholds for automatic changes.
- Require human review for sensitive decisions such as security or P0.
- Roll out in stages:
  1. Dry-run logs.
  2. One bot comment without labels.
  3. Safe label application.
  4. Duplicate warnings.
  5. Optional assignee recommendations.
- Add rollback and kill-switch instructions.
- Retire obsolete two-branch documentation after successful rollout.

#### Acceptance criteria

- Quality targets are documented and met before write automation advances.
- Sensitive actions are limited by explicit policy.
- Provider quality, latency, and usage can be compared from recorded metrics.
- The bot can be disabled or rolled back without database repair.

## 10. Delivery sequence and release boundaries

| Phase | Milestones | Release outcome |
|---|---:|---|
| Safe foundation | 1–2 | Tested application with stable types and provider boundary |
| Dual-provider MVP | 3–4 | Anthropic/OpenAI triage with safe, idempotent GitHub integration |
| Feature restoration | 5 | Genuine optional duplicate detection |
| Production rollout | 6–7 | Reproducible deployment with measured automation |

The recommended first release boundary is the completion of Milestones 1–4. Duplicate detection should not block the dual-provider MVP.

Each milestone should be delivered as a reviewable change set with its own tests and documentation. A later milestone should not be used to defer unmet acceptance criteria from an earlier one.

## 11. Proposed testing strategy

### Unit tests

- Domain model validation.
- Configuration parsing and startup validation.
- Label mapping and policy decisions.
- Prompt input construction.
- Comment rendering and hidden markers.
- Retry classification and error translation.

### Provider contract tests

- Valid response parsing.
- Unsupported issue kind rejection.
- Confidence range enforcement.
- Refusal and empty-output handling.
- Timeout, rate-limit, and authentication behavior.
- Usage and request metadata extraction.

### Integration tests

- Mocked GitHub fetch, label, and comment workflows.
- PostgreSQL migration, upsert, and similarity queries.
- CLI dry-run execution.
- Idempotent replay of the same issue event.

### Evaluation tests

- A stable set of issues with expected acceptable kinds and priorities.
- Provider comparisons that allow justified variation without accepting invalid output.
- Duplicate and non-duplicate pairs for threshold calibration.
- Regression tracking across prompt, model, and configuration changes.

Live API calls should not run in the default unit-test suite. Optional smoke tests may run manually or in a protected scheduled workflow with explicit budgets.

## 12. Decisions to review and challenge

The following decisions materially affect implementation. They should be accepted, changed, or explicitly deferred before execution.

### Decision 1 — One primary issue kind or multiple kinds?

**Recommendation:** One primary `IssueKind`, plus separately modeled attributes such as area, platform, and status.

**Reasoning:** `bug`, `chore`, and `feature` are usually mutually exclusive descriptions of work type. Mixing type labels with areas such as `frontend` or `database` makes validation and evaluation ambiguous.

**Alternative:** `kinds: set[IssueKind]`, allowing an issue to be both bug and documentation, for example.

### Decision 2 — What should the initial issue-kind vocabulary contain?

**Recommendation:** Start with `bug`, `chore`, `feature`, `documentation`, `question`, and `security`.

**Questions:**

- Is `security` a primary kind or a sensitive attribute on a bug?
- Should `performance` be a type, an area, or an impact attribute?
- Are `support`, `refactor`, `dependency`, or `investigation` required?

### Decision 3 — Should the model assign priority?

**Recommendation:** Let the model propose priority, then apply deterministic policy and require human review for P0 and security-related decisions.

**Alternative:** Calculate priority entirely through repository-specific rules and use the model only for classification.

### Decision 4 — Should label application be automatic in the MVP?

**Recommendation:** Begin with dry-run and a single bot comment, then enable an allowlisted subset of labels after evaluation.

**Alternative:** Apply type labels immediately but keep priority, security, and assignment advisory.

### Decision 5 — What provider behavior must be equivalent?

**Recommendation:** Require schema and policy equivalence, not identical prose or identical classifications in every case. Compare disagreement rates through evaluation.

**Question:** Is provider selection global, repository-specific, or selectable per run?

### Decision 6 — How should models be selected?

**Recommendation:** Keep model identifiers in configuration and test supported defaults through evaluation. Do not embed a supposedly permanent model name in domain code.

**Question:** Should the project ship one quality-focused and one cost-focused preset per provider?

### Decision 7 — What embedding strategy should duplicate detection use?

**Recommendation:** Keep embedding selection independent from the triage provider. Evaluate a local model against a hosted embedding service before choosing.

**Trade-offs:**

- Local embeddings improve vendor independence and privacy but increase package size and runner startup time.
- Hosted embeddings simplify execution but add a third service or couple duplicate detection to OpenAI.
- Lexical retrieval is cheaper and simpler but may miss semantically similar reports.

### Decision 8 — Is PostgreSQL required for the first deployment?

**Recommendation:** No. Make it optional until duplicate detection is enabled.

**Alternative:** Store every triage result from the MVP for audit and later evaluation, even before embeddings are introduced.

### Decision 9 — How should configuration work?

**Recommendation:** Use environment variables for secrets and deployment selection, with one validated YAML or TOML file for repository policy and label mapping.

**Question:** Does this bot need to support different policy files for multiple repositories?

### Decision 10 — What does the bot write to GitHub?

**Recommendation:** One managed comment plus approved labels. Assignees remain suggestions initially.

**Questions:**

- Should the bot create missing labels?
- Should it ever assign people automatically?
- Should edits remove labels the bot previously added if classification changes?

### Decision 11 — What data may be sent to AI providers?

**Recommendation:** Send only the issue fields and bounded repository context required for triage. Do not send secrets, arbitrary checkout contents, or unrelated issue history.

**Questions:**

- May private-repository issue content be sent to both providers?
- Are there retention, regional, or compliance constraints?
- Should issue authors or repository maintainers be able to opt out?

### Decision 12 — What are the rollout quality gates?

**Recommendation:** Define minimum label agreement, maximum schema-failure rate, acceptable latency, and a cost ceiling before enabling writes.

**Required input:** The project owner must define which mistakes are tolerable. A wrong `documentation` label is not equivalent to a wrong `security` or `P0` label.

## 13. Execution gates

Implementation may begin after:

1. The vocabulary and single-versus-multiple-kind decision are approved.
2. The MVP's permitted GitHub writes are approved.
3. Data-sharing constraints for Anthropic and OpenAI are documented.
4. The first-release boundary is confirmed as Milestones 1–4 or amended.
5. Duplicate detection is explicitly accepted as deferred or moved into the MVP.

Production write automation may begin only after:

1. Milestones 1–4 acceptance criteria pass.
2. Dry-run evaluation targets are defined and met.
3. The workflow permissions and secrets have been reviewed.
4. Idempotency and prompt-injection tests pass.
5. A rollback or kill switch has been tested.

## 14. Definition of done

The refresh is complete when:

- Anthropic and OpenAI can each triage the same request through the shared provider contract.
- Every provider response is validated as a typed `TriageDecision`.
- GitHub and database operations are executed only by deterministic application code.
- The workflow is reproducible from the committed lockfile.
- Replayed and edited issue events are idempotent.
- Automated actions are limited by documented policy and quality gates.
- Duplicate detection, if enabled, uses real embeddings with measured performance.
- Tests, deployment instructions, configuration reference, and rollback instructions are current.
- The obsolete branch-based provider or feature strategy has been retired.

