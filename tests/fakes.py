from pathlib import Path

from issue_triage_bot.codec import content_hash
from issue_triage_bot.github import GitHubError
from issue_triage_bot.models import Comment, Issue, ProposalEnvelope, RunContext
from issue_triage_bot.policy import LabelEvent
from issue_triage_bot.release import load_live


class Repo:
    def __init__(self):
        self.files = {
            path: Path(path).read_bytes()
            for path in [
                ".github/triage-control.yml",
                "triage/policy.yml",
                "triage/inference.yml",
                "triage/PROMPT.md",
            ]
        }
        self.files[".github/triage-control.yml"] = (
            b"enabled: true\npolicy_generation: 1\ncanary:\n  first_issue: 12\n"
            b"  max_issues: 20\n  max_mutations: 60\n"
        )
        self.files["triage/policy.yml"] = self.files["triage/policy.yml"].replace(
            b"dry_run", b"type_labels"
        )
        self.current = Issue(
            repository="example/repo",
            number=12,
            node_id="I_fixture",
            title="Crash",
            body=None,
            labels=("human",),
        )
        self.comment_rows = []
        self.events = []
        self.writes = []
        self.fail_after = None
        self.after_write = lambda repo, name: None

    def default_head(self):
        return "a" * 40

    def file(self, path, ref):
        return self.files.get(path)

    def issue(self, number):
        if number == 12:
            return self.current
        if number == 8:
            return Issue(
                repository="example/repo", number=8, node_id="I_8", title="Related", body=""
            )
        raise GitHubError(404, transient=False)

    def comments(self, number):
        return tuple(self.comment_rows)

    def timeline(self, number):
        return tuple(self.events)

    def _after(self, name):
        self.writes.append(name)
        self.after_write(self, name)
        if self.fail_after == len(self.writes):
            raise GitHubError(None, transient=True, uncertain=True)

    def create_comment(self, number, body):
        id = len(self.comment_rows) + 1
        self.comment_rows.append(
            Comment(id=id, author_login="github-actions[bot]", author_type="Bot", body=body)
        )
        self._after("create_comment")
        return id

    def edit_comment(self, number, comment_id, body):
        index = next(i for i, c in enumerate(self.comment_rows) if c.id == comment_id)
        self.comment_rows[index] = Comment(
            id=comment_id, author_login="github-actions[bot]", author_type="Bot", body=body
        )
        self._after("edit_comment")

    def label(self, label, event, actor="github-actions[bot]", kind="Bot"):
        labels = set(self.current.labels)
        if event == "labeled":
            labels.add(label)
        else:
            labels.discard(label)
        self.current = Issue(**(self.current.model_dump() | {"labels": tuple(sorted(labels))}))
        self.events.append(
            LabelEvent(
                id=len(self.events) + 1,
                event=event,
                label=label,
                actor_login=actor,
                actor_type=kind,
            )
        )

    def add_label(self, number, label):
        self.label(label, "labeled")
        self._after("add_label")

    def remove_label(self, number, label):
        self.label(label, "unlabeled")
        self._after("remove_label")


def prepare(repo, *, run=100, mode="propose"):
    live = load_live(repo)
    issue = repo.current
    context = RunContext(
        repository=issue.repository,
        issue_number=issue.number,
        node_id=issue.node_id,
        run_id=run,
        run_attempt=1,
    )
    env = ProposalEnvelope(
        **context.model_dump(),
        release=live.identity,
        content_hash=content_hash(issue, live.identity),
        mode=mode,
        candidates=(8,),
    )
    return env, context
