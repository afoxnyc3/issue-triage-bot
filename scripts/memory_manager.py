#!/usr/bin/env python3
"""
Memory Manager - Store and retrieve issue embeddings for duplicate detection

This script provides a simple interface for the agent to:
1. Store issue embeddings in Supabase PostgreSQL
2. Search for similar issues using semantic similarity
3. Retrieve past issues for context

The agent will use PostgreSQL MCP to interact with this database.
"""

import json
import sys
from pathlib import Path

# For local testing, we can use this script directly
# But in production, the agent uses PostgreSQL MCP tools

def generate_test_embedding(text: str, dimension: int = 384):
    """
    Generate a test embedding for demonstration purposes.
    In production, the agent will use sentence-transformers via MCP.

    For demo: creates a simple hash-based vector
    """
    import hashlib
    # Create a deterministic "embedding" from text hash
    hash_obj = hashlib.sha256(text.encode())
    hash_bytes = hash_obj.digest()

    # Convert to float array (normalized)
    embedding = []
    for i in range(dimension):
        byte_val = hash_bytes[i % len(hash_bytes)]
        embedding.append((byte_val / 255.0) * 2 - 1)  # Normalize to [-1, 1]

    return embedding


def main():
    """
    CLI interface for memory operations.

    Usage:
        python memory_manager.py store <issue_number> "<title>" "<body>"
        python memory_manager.py search "<text>" [threshold]
    """
    if len(sys.argv) < 2:
        print("""Usage:
  Store issue:  python memory_manager.py store <issue_num> "title" "body"
  Search:       python memory_manager.py search "text" [threshold]

Examples:
  python memory_manager.py store 1 "App crashes" "Stack trace..."
  python memory_manager.py search "crash on submit" 0.85
""")
        sys.exit(1)

    command = sys.argv[1]

    if command == "store":
        if len(sys.argv) < 5:
            print("Usage: python memory_manager.py store <issue_num> 'title' 'body'")
            sys.exit(1)

        issue_num = int(sys.argv[2])
        title = sys.argv[3]
        body = sys.argv[4]

        # Generate embedding
        text = f"{title} {body}"
        embedding = generate_test_embedding(text)

        result = {
            "command": "store",
            "issue_number": issue_num,
            "title": title,
            "embedding_dimension": len(embedding),
            "message": f"Use PostgreSQL MCP to store this embedding"
        }

        print(json.dumps(result, indent=2))

    elif command == "search":
        if len(sys.argv) < 3:
            print("Usage: python memory_manager.py search 'text' [threshold]")
            sys.exit(1)

        query_text = sys.argv[2]
        threshold = float(sys.argv[3]) if len(sys.argv) > 3 else 0.85

        # Generate query embedding
        embedding = generate_test_embedding(query_text)

        result = {
            "command": "search",
            "query": query_text,
            "threshold": threshold,
            "embedding_dimension": len(embedding),
            "message": "Use PostgreSQL MCP to query: SELECT * FROM find_similar_issues(...)"
        }

        print(json.dumps(result, indent=2))

    else:
        print(f"Unknown command: {command}")
        print("Use 'store' or 'search'")
        sys.exit(1)


if __name__ == "__main__":
    main()
