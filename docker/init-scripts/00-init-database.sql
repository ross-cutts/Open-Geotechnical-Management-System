-- Initialize GMS Foundation Database
-- This script runs automatically when the Docker container starts

-- Create extensions if not exists
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create schema
CREATE SCHEMA IF NOT EXISTS gms;

-- Grant permissions
GRANT ALL ON SCHEMA gms TO gms_user;
GRANT ALL ON ALL TABLES IN SCHEMA gms TO gms_user;
GRANT ALL ON ALL SEQUENCES IN SCHEMA gms TO gms_user;

-- Set default search path
ALTER DATABASE gms_foundation SET search_path TO gms, public;

-- Create a simple version tracking table
CREATE TABLE IF NOT EXISTS gms.schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

-- Insert initial version
INSERT INTO gms.schema_version (version, description) 
VALUES (1, 'Initial GMS Foundation schema')
ON CONFLICT (version) DO NOTHING;