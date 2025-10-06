-- Enable pgvector extension for semantic similarity search
CREATE EXTENSION IF NOT EXISTS vector;

-- Create table for storing issue embeddings
CREATE TABLE IF NOT EXISTS issue_embeddings (
    id SERIAL PRIMARY KEY,
    issue_number INTEGER NOT NULL,
    repo_name TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT,
    embedding vector(384),  -- MiniLM model produces 384-dimensional vectors
    labels JSONB,
    priority TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Ensure we don't duplicate the same issue
    UNIQUE(repo_name, issue_number)
);

-- Create index for faster similarity searches using cosine distance
CREATE INDEX IF NOT EXISTS issue_embeddings_embedding_idx
ON issue_embeddings
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Create index for faster lookups by repo and issue number
CREATE INDEX IF NOT EXISTS issue_embeddings_repo_issue_idx
ON issue_embeddings (repo_name, issue_number);

-- Create index for faster lookups by creation date
CREATE INDEX IF NOT EXISTS issue_embeddings_created_at_idx
ON issue_embeddings (created_at DESC);

-- Function to find similar issues using cosine similarity
CREATE OR REPLACE FUNCTION find_similar_issues(
    query_embedding vector(384),
    similarity_threshold FLOAT DEFAULT 0.85,
    max_results INT DEFAULT 5
)
RETURNS TABLE (
    issue_number INTEGER,
    repo_name TEXT,
    title TEXT,
    similarity FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ie.issue_number,
        ie.repo_name,
        ie.title,
        1 - (ie.embedding <=> query_embedding) as similarity
    FROM issue_embeddings ie
    WHERE 1 - (ie.embedding <=> query_embedding) >= similarity_threshold
    ORDER BY ie.embedding <=> query_embedding
    LIMIT max_results;
END;
$$ LANGUAGE plpgsql;

-- Sample query to test (commented out)
-- SELECT * FROM find_similar_issues(
--     (SELECT embedding FROM issue_embeddings WHERE issue_number = 1 LIMIT 1),
--     0.85,
--     5
-- );
