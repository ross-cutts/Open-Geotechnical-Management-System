-- Geotechnical Management System (GMS) Foundation Schema
-- PostgreSQL with PostGIS Extension
-- Version 1.0

-- Extensions and schema already created by 00-init-database.sql
SET search_path TO gms, public;

-- Set up spatial reference system tracking
INSERT INTO spatial_ref_sys (srid, auth_name, auth_srid, srtext, proj4text)
VALUES (
    4326,
    'EPSG',
    4326,
    'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]]',
    '+proj=longlat +datum=WGS84 +no_defs'
) ON CONFLICT (srid) DO NOTHING;