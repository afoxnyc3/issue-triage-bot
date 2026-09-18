"""Strict, bounded trust-boundary contracts (JSON input, immutable Python values)."""

from enum import StrEnum
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
CommitSHA = Annotated[str, Field(pattern=r"^[0-9a-f]{40}$")]
PositiveID = Annotated[int, Field(gt=0)]
Repository = Annotated[str, Field(pattern=r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$", max_length=200)]
Label = Annotated[str, Field(min_length=1, max_length=50)]
ShortText = Annotated[str, Field(max_length=120)]


class StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        frozen=True,
        hide_input_in_errors=True,
        revalidate_instances="always",
    )

    @field_validator("*", mode="after")
    @classmethod
    def reject_surrogates(cls, value: object) -> object:
        if isinstance(value, str):
            try:
                value.encode("utf-8")
            except UnicodeEncodeError:
                raise ValueError("invalid Unicode") from None
        return value


class IssueKind(StrEnum):
    BUG = "bug"
    FEATURE = "feature"
    DOCUMENTATION = "documentation"
    QUESTION = "question"
    CHORE = "chore"
    SECURITY = "security"


class Issue(StrictModel):
    repository: Repository
    number: PositiveID
    node_id: Annotated[str, Field(min_length=1, max_length=200)]
    # Complete GitHub content, not an inference snapshot. Do not truncate before hashing/scanning.
    title: str
    body: str | None
    labels: tuple[Label, ...] = ()


class RelatedIssue(StrictModel):
    number: PositiveID
    reason: ShortText


class TriageDecision(StrictModel):
    schema_version: Literal[1]
    kind: IssueKind
    priority: Literal["P0", "P1", "P2", "P3"]
    complexity: Literal["simple", "medium", "complex"]
    area: Annotated[str, Field(max_length=40)] | None = None
    rationale: Annotated[str, Field(max_length=600)]
    related_issues: Annotated[tuple[RelatedIssue, ...], Field(max_length=5)] = ()
    missing_information: Annotated[tuple[ShortText, ...], Field(max_length=5)] = ()

    @field_validator("schema_version", mode="before")
    @classmethod
    def integer_version(cls, value: object) -> object:
        if type(value) is not int:
            raise ValueError("schema_version must be an integer")
        return value

    @model_validator(mode="after")
    def unique_related(self) -> Self:
        numbers = [item.number for item in self.related_issues]
        if len(numbers) != len(set(numbers)):
            raise ValueError("duplicate related issue")
        return self


class Release(StrictModel):
    """Live release and inference identity; all fields participate in hashes/fences."""

    provider: Literal["anthropic"]
    model: Annotated[str, Field(min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9._:-]+$")]
    action_sha: CommitSHA
    schema_version: Literal[1]
    inference_digest: Digest
    prompt_digest: Digest
    policy_digest: Digest
    control_digest: Digest
    policy_generation: PositiveID

    @field_validator("schema_version", mode="before")
    @classmethod
    def integer_version(cls, value: object) -> object:
        if type(value) is not int:
            raise ValueError("schema_version must be an integer")
        return value

    @field_validator("model")
    @classmethod
    def exact_model_required(cls, value: str) -> str:
        if value in {"sonnet", "opus", "haiku", "default"} or value.endswith("-latest"):
            raise ValueError("configure an exact model identifier")
        return value


class RunContext(StrictModel):
    repository: Repository
    issue_number: PositiveID
    node_id: Annotated[str, Field(min_length=1, max_length=200)]
    run_id: PositiveID
    run_attempt: PositiveID


class ProposalEnvelope(RunContext):
    release: Release
    content_hash: Digest
    mode: Literal["skip", "deferred", "review_only", "resume", "propose"]
    candidates: Annotated[tuple[PositiveID, ...], Field(max_length=10)] = ()
    snapshot_truncated: bool = False

    @model_validator(mode="after")
    def valid_candidates(self) -> Self:
        if (
            len(self.candidates) != len(set(self.candidates))
            or self.issue_number in self.candidates
        ):
            raise ValueError("invalid candidate set")
        return self
