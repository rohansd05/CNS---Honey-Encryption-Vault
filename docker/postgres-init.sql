-- =====================================================================
-- HoneyVault PostgreSQL Initialization Script
-- Executed on initial container startup by postgres:16-alpine
-- Creates separate roles and databases for honeyvault-api and honeychecker
-- =====================================================================

-- 1. HoneyVault API role and database
CREATE USER honeyvault WITH PASSWORD 'honeyvault';
CREATE DATABASE honeyvault OWNER honeyvault;
GRANT ALL PRIVILEGES ON DATABASE honeyvault TO honeyvault;

-- 2. Honeychecker role and database
CREATE USER honeychecker WITH PASSWORD 'honeychecker';
CREATE DATABASE honeychecker OWNER honeychecker;
GRANT ALL PRIVILEGES ON DATABASE honeychecker TO honeychecker;

-- 3. Schema grants for PostgreSQL 15+ (public schema ownership changes)
\connect honeyvault
GRANT ALL ON SCHEMA public TO honeyvault;

\connect honeychecker
GRANT ALL ON SCHEMA public TO honeychecker;
