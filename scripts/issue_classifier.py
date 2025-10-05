#!/usr/bin/env python3
"""
Issue Classifier - Categorize GitHub issues based on content

Uses TF-IDF and keyword matching to classify issues into categories.
"""

import json
import sys
from pathlib import Path

# Load configuration
config_path = Path(__file__).parent.parent / "config.yaml"

# Default label keywords (loaded from config.yaml in production)
LABELS = {
    'bug': ['error', 'crash', 'broken', 'fail', 'exception', 'bug'],
    'feature': ['feature', 'enhancement', 'add', 'support', 'implement'],
    'docs': ['documentation', 'docs', 'readme', 'guide', 'tutorial'],
    'question': ['how', 'why', 'question', 'help', 'confused'],
    'performance': ['slow', 'performance', 'lag', 'optimize', 'speed'],
    'security': ['security', 'vulnerability', 'exploit', 'CVE']
}


def classify_issue(title: str, body: str = "", min_confidence: float = 0.6) -> dict:
    """
    Classify an issue based on title and body content.

    Args:
        title: Issue title
        body: Issue body (optional)
        min_confidence: Minimum confidence threshold (0-1)

    Returns:
        Dictionary with classification results
    """
    text = f"{title} {body}".lower()

    # Score each category
    scores = {}
    for category, keywords in LABELS.items():
        score = sum(1 for keyword in keywords if keyword in text)
        # Normalize by number of keywords
        scores[category] = score / len(keywords) if keywords else 0

    # Get categories above threshold
    labels = [cat for cat, score in scores.items() if score >= min_confidence]

    # If no labels meet threshold, pick top scoring if any matches
    if not labels and scores:
        max_score = max(scores.values())
        if max_score > 0:
            labels = [cat for cat, score in scores.items() if score == max_score]

    return {
        "labels": labels,
        "scores": {k: round(v, 2) for k, v in scores.items()},
        "confidence": round(max(scores.values()) if scores else 0, 2)
    }


def main():
    """
    CLI interface for issue classification.

    Usage:
        python issue_classifier.py "Issue title" ["Issue body"]
    """
    if len(sys.argv) < 2:
        print("Usage: python issue_classifier.py 'Issue title' ['Issue body']")
        print("\nExample:")
        print("  python issue_classifier.py 'App crashes on startup'")
        sys.exit(1)

    title = sys.argv[1]
    body = sys.argv[2] if len(sys.argv) > 2 else ""

    result = classify_issue(title, body)

    print(json.dumps(result, indent=2))

    # Return exit code based on whether labels found
    sys.exit(0 if result["labels"] else 1)


if __name__ == "__main__":
    main()
