"""Strict, bounded release configuration. YAML aliases and duplicate keys are rejected."""

import re
from typing import Annotated, Literal, Self

import yaml
from pydantic import Field, model_validator
from yaml.tokens import AliasToken

from .codec import BoundaryError, Model, canonical_json, parse_json
from .models import IssueKind, Label, PositiveID, StrictModel

CONTROL_LABELS = frozenset({"needs-triage-review", "triage-deferred", "triage-retry"})
PRIORITY_LABEL = re.compile(r"^(?:p[0-3](?:$|[- :])|priority(?:$|[- :]))", re.IGNORECASE)


class Canary(StrictModel):
    first_issue: PositiveID
    max_issues: Annotated[int, Field(ge=1, le=20)] = 20
    max_mutations: Annotated[int, Field(ge=1, le=60)] = 60


class Control(StrictModel):
    enabled: bool = False
    policy_generation: PositiveID
    daily_inference_limit: Annotated[int, Field(ge=0, le=40)] = 40
    canary: Canary | None = None


class Policy(StrictModel):
    rollout: Literal["dry_run", "shadow", "comment_only", "type_labels"] = "dry_run"
    type_labels: dict[IssueKind, tuple[Label, ...]]
    label_allowlist: Annotated[tuple[Label, ...], Field(max_length=32)]
    retired_labels: Annotated[tuple[Label, ...], Field(max_length=32)] = ()
    areas: dict[str, str] = Field(default_factory=dict)
    security_terms: Annotated[tuple[str, ...], Field(min_length=1, max_length=50)]
    excluded_actors: tuple[str, ...] = ()
    snapshot_bytes: Annotated[int, Field(ge=256, le=16384)] = 8192

    @model_validator(mode="after")
    def safe_configuration(self) -> Self:
        if IssueKind.SECURITY in self.type_labels:
            raise ValueError("security cannot have automatic type labels")
        all_labels = set(self.label_allowlist) | set(self.retired_labels)
        all_labels.update(label for labels in self.type_labels.values() for label in labels)
        if any(PRIORITY_LABEL.match(label) for label in all_labels):
            raise ValueError("priority labels are not supported")
        if any(label in CONTROL_LABELS for labels in self.type_labels.values() for label in labels):
            raise ValueError("control labels cannot be type mappings")
        if any(not term.strip() or len(term) > 80 for term in self.security_terms):
            raise ValueError("invalid security term")
        if len(self.areas) > 30 or any(len(k) > 40 or len(v) > 80 for k, v in self.areas.items()):
            raise ValueError("invalid area mapping")
        return self


class _UniqueLoader(yaml.SafeLoader):
    pass


def _mapping(loader: _UniqueLoader, node: yaml.MappingNode, deep: bool = False) -> object:
    result: dict[object, object] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in result:
            raise BoundaryError("duplicate YAML key")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


_UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping)


def parse_yaml(model: type[Model], raw: bytes) -> Model:
    if len(raw) > 64 * 1024:
        raise BoundaryError("configuration exceeds size limit")
    try:
        text = raw.decode("utf-8")
        if any(isinstance(token, AliasToken) for token in yaml.scan(text)):
            raise BoundaryError("YAML aliases are forbidden")
        data = yaml.load(text, Loader=_UniqueLoader)
        return parse_json(model, canonical_json(data), max_bytes=64 * 1024)
    except (yaml.YAMLError, ValueError, TypeError, RecursionError):
        raise BoundaryError("invalid configuration") from None
