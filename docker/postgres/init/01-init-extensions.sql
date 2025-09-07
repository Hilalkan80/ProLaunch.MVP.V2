-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Create vector search test
CREATE TABLE IF NOT EXISTS vector_test (
  id SERIAL PRIMARY KEY,
  embedding vector(1536),
  metadata JSONB
);

-- Create index for vector similarity search
CREATE INDEX IF NOT EXISTS vector_test_embedding_idx ON vector_test 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);