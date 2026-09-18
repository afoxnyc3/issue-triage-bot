"""Live default-branch control, policy, prompt and inference release fencing."""

from dataclasses import dataclass
from typing import Protocol

from .codec import BoundaryError, canonical_json, digest_bytes
from .config import Control, Inference, Policy, parse_yaml
from .models import Release, TriageDecision


class ReleaseReader(Protocol):
    def default_head(self) -> str: ...
    def file(self, path: str, ref: str) -> bytes | None: ...


@dataclass(frozen=True)
class LiveRelease:
    head: str
    control: Control
    policy: Policy
    inference: Inference
    prompt: str
    identity: Release


def schema_bytes() -> bytes:
    return canonical_json(TriageDecision.model_json_schema())


def load_live(reader: ReleaseReader) -> LiveRelease | None:
    # Resolve the default branch head once per read; all content shares one immutable ref.
    head = reader.default_head()
    raw_control = reader.file(".github/triage-control.yml", head)
    if raw_control is None:
        return None
    control = parse_yaml(Control, raw_control)
    if not control.enabled:
        return None
    raw_policy = reader.file("triage/policy.yml", head)
    raw_prompt = reader.file("triage/PROMPT.md", head)
    raw_inference = reader.file("triage/inference.yml", head)
    if raw_policy is None or raw_prompt is None or raw_inference is None:
        raise BoundaryError("incomplete live release")
    policy = parse_yaml(Policy, raw_policy)
    inference = parse_yaml(Inference, raw_inference)
    if inference.decision_schema_digest != digest_bytes(schema_bytes()):
        raise BoundaryError("local schema does not match live inference configuration")
    try:
        prompt = raw_prompt.decode("utf-8")
    except UnicodeError:
        raise BoundaryError("invalid live prompt") from None
    if not prompt.strip() or len(raw_prompt) > 16 * 1024:
        raise BoundaryError("invalid live prompt")
    identity = Release(
        provider=inference.provider,
        model=inference.model,
        action_sha=inference.action_sha,
        schema_version=inference.schema_version,
        inference_digest=digest_bytes(raw_inference),
        prompt_digest=digest_bytes(raw_prompt),
        policy_digest=digest_bytes(raw_policy),
        control_digest=digest_bytes(raw_control),
        policy_generation=control.policy_generation,
    )
    if policy.rollout == "type_labels" and control.canary is None:
        # A first live write release must have a canary. Lifting it needs a later reviewed contract.
        raise BoundaryError("type-label rollout requires a canary")
    return LiveRelease(head, control, policy, inference, prompt, identity)
