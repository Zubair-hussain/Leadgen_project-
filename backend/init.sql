-- LeadGen Database Initialization
-- This file runs when the PostgreSQL container is first created

-- Create database if it does not exist
DO
$$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_database WHERE datname = 'leadgen') THEN
      CREATE DATABASE leadgen;
   END IF;
END
$$;

-- Create extensions if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Set timezone
SET timezone = 'UTC';

-- Create indexes for better performance (will be created by Django migrations)
-- These are just examples of what Django will create