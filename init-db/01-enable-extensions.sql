-- Enable required PostgreSQL extensions
-- This script runs automatically when the Docker container is first initialized

-- Enable pg_trgm for trigram-based text search
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Enable other useful extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";  -- For UUID generation
CREATE EXTENSION IF NOT EXISTS btree_gin;     -- For GIN indexes on multiple column types

-- Verify extensions are installed
SELECT extname, extversion FROM pg_extension WHERE extname IN ('pg_trgm', 'uuid-ossp', 'btree_gin');

