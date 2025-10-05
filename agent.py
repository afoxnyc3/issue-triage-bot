"""
Issue Triage Bot - Automatically categorize and route GitHub issues

This agent uses the Claude Code SDK to analyze GitHub issues and:
- Auto-label based on content
- Detect duplicates
- Assess priority
- Suggest assignees
"""

import asyncio
import json
import os
from typing import Any, Callable

from dotenv import load_dotenv
from claude_code_sdk import ClaudeCodeOptions, ClaudeSDKClient

load_dotenv()


def get_activity_text(msg) -> str | None:
    """Extract activity text from a message for logging"""
    try:
        if "Assistant" in msg.__class__.__name__:
            if hasattr(msg, "content") and msg.content:
                first_content = msg.content[0] if isinstance(msg.content, list) else msg.content
                if hasattr(first_content, "name"):
                    return f"🤖 Using: {first_content.name}()"
            return "🤖 Analyzing issue..."
        elif "User" in msg.__class__.__name__:
            return "✓ Tool completed"
    except (AttributeError, IndexError):
        pass
    return None


def print_activity(msg) -> None:
    """Print activity to console"""
    activity = get_activity_text(msg)
    if activity:
        print(activity)


async def triage_issue(
    issue_number: int = None,
    owner: str = None,
    repo: str = None,
    activity_handler: Callable[[Any], None] = print_activity,
) -> tuple[str | None, list]:
    """
    Triage a GitHub issue using the Claude Code SDK.

    Args:
        issue_number: GitHub issue number to triage
        owner: Repository owner (defaults to env var GITHUB_OWNER)
        repo: Repository name (defaults to env var GITHUB_REPO)
        activity_handler: Callback for activity updates

    Returns:
        Tuple of (result_text, messages)
    """

    # Get repo info from environment if not provided
    owner = owner or os.getenv("GITHUB_OWNER", "your-org")
    repo = repo or os.getenv("GITHUB_REPO", "your-repo")

    # GitHub MCP server configuration
    github_mcp = {
        "github": {
            "command": "docker",
            "args": [
                "run", "-i", "--rm",
                "-e", "GITHUB_PERSONAL_ACCESS_TOKEN",
                "ghcr.io/github/github-mcp-server"
            ],
            "env": {
                "GITHUB_PERSONAL_ACCESS_TOKEN": os.getenv("GITHUB_TOKEN")
            }
        }
    }

    # System prompt for the triage agent
    system_prompt = """You are an Issue Triage Bot for GitHub repositories.

Your responsibilities:
1. Analyze issue content (title and body)
2. Classify and label issues (bug, feature, docs, question, etc.)
3. Detect duplicate issues by comparing to existing issues
4. Assess priority (P0-critical, P1-high, P2-medium, P3-low)
5. Estimate complexity (simple, medium, complex)
6. Suggest appropriate assignees based on code ownership
7. Request missing information if needed

You have access to custom Python scripts via the Bash tool:
- scripts/issue_classifier.py: Classify issue into categories
- scripts/duplicate_detector.py: Find similar existing issues
- scripts/priority_assessor.py: Assign priority level
- scripts/assignee_router.py: Suggest best assignee

Always provide clear, actionable recommendations."""

    # Build query based on whether issue_number provided
    if issue_number:
        prompt = f"""Triage issue #{issue_number} in {owner}/{repo}.

Steps:
1. Fetch the issue details using GitHub MCP
2. Run classification script to determine labels
3. Check for duplicate issues
4. Assess priority level
5. Suggest assignee if applicable
6. Apply labels and post a summary comment

Provide a structured summary of your analysis."""
    else:
        # No specific issue - provide usage example
        prompt = """I'm the Issue Triage Bot, ready to analyze GitHub issues.

To triage an issue, call me with:
- issue_number: The issue # to analyze
- owner: Repository owner
- repo: Repository name

Example: triage_issue(issue_number=123, owner='acme', repo='app')"""

    options = ClaudeCodeOptions(
        model="claude-sonnet-4-20250514",
        allowed_tools=[
            "mcp__github",  # GitHub API access
            "Bash",         # Run classification scripts
            "Read",         # Read configuration files
        ],
        mcp_servers=github_mcp,
        system_prompt=system_prompt,
        cwd=os.path.dirname(os.path.abspath(__file__)),
    )

    result = None
    messages = []

    try:
        async with ClaudeSDKClient(options=options) as agent:
            await agent.query(prompt=prompt)
            async for msg in messages:
                messages.append(msg)

                if asyncio.iscoroutinefunction(activity_handler):
                    await activity_handler(msg)
                else:
                    activity_handler(msg)

                if hasattr(msg, "result"):
                    result = msg.result

    except Exception as e:
        print(f"❌ Triage error: {e}")
        raise

    return result, messages


async def retriage_all_open_issues(owner: str, repo: str):
    """Retriage all open issues in a repository"""
    print(f"🔄 Retriaging all open issues in {owner}/{repo}...")

    # TODO: Implement bulk retriaging
    # 1. Fetch all open issues via GitHub MCP
    # 2. For each issue, call triage_issue()
    # 3. Track results and errors

    print("⚠️ Bulk retriaging not yet implemented")
    print("Run: uv run python agent.py --issue <number> for individual issues")


async def main():
    """
    Main entry point for the Issue Triage Bot.

    Usage:
        python agent.py                          # Show usage
        python agent.py --issue 123              # Triage issue #123
        python agent.py --retriage-all           # Retriage all open issues
    """
    import sys

    print("🤖 Issue Triage Bot")
    print("=" * 60)

    if len(sys.argv) > 1:
        if "--issue" in sys.argv:
            # Triage specific issue
            try:
                issue_idx = sys.argv.index("--issue") + 1
                issue_num = int(sys.argv[issue_idx])
                result, _ = await triage_issue(issue_number=issue_num)
                print(f"\n📊 Triage Result:\n{result}\n")
            except (IndexError, ValueError):
                print("❌ Usage: python agent.py --issue <number>")

        elif "--retriage-all" in sys.argv:
            # Retriage all open issues
            owner = os.getenv("GITHUB_OWNER")
            repo = os.getenv("GITHUB_REPO")
            if not owner or not repo:
                print("❌ Set GITHUB_OWNER and GITHUB_REPO in .env")
                return
            await retriage_all_open_issues(owner, repo)
        else:
            print("❌ Unknown option")
            print("Usage:")
            print("  python agent.py --issue <number>")
            print("  python agent.py --retriage-all")
    else:
        # No arguments - show example
        result, _ = await triage_issue()
        print(f"\n{result}\n")
        print("💡 Tip: Run with --issue <number> to triage a specific issue")


if __name__ == "__main__":
    asyncio.run(main())
