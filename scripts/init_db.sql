-- ============================================
-- MCP Server - Database Initialization Script
-- ============================================

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For fuzzy text search

-- Create custom types (if needed)
-- Note: SQLAlchemy Enums will create these automatically

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE mcpdb TO mcpuser;

-- Create schema for future organization (optional)
-- CREATE SCHEMA IF NOT EXISTS mcp;

-- Logging
DO $$
BEGIN
    RAISE NOTICE 'MCP Database initialized successfully';
END $$;
