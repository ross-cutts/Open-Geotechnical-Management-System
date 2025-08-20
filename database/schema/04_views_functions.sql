-- Views and Functions for GMS Foundation
-- Provides useful views and spatial analysis functions

SET search_path TO gms, public;

-- View: Comprehensive boring summary
CREATE OR REPLACE VIEW v_boring_summary AS
SELECT 
    gp.id,
    gp.point_id,
    gp.location,
    gp.elevation_m,
    gp.investigation_date,
    gp.total_depth_m,
    gp.groundwater_depth_m,
    gp.rock_depth_m,
    gp.confidence,
    p.project_number,
    p.name as project_name,
    COUNT(DISTINCT sl.id) as layer_count,
    COUNT(DISTINCT spt.id) as spt_count,
    COUNT(DISTINCT lt.id) as lab_test_count
FROM geotechnical_points gp
LEFT JOIN projects p ON gp.project_id = p.id
LEFT JOIN subsurface_layers sl ON sl.point_id = gp.id
LEFT JOIN spt_results spt ON spt.point_id = gp.id
LEFT JOIN laboratory_tests lt ON lt.point_id = gp.id
GROUP BY gp.id, p.project_number, p.name;

-- View: Recent maintenance activity summary
CREATE OR REPLACE VIEW v_maintenance_summary AS
SELECT 
    mr.id,
    mr.activity_date,
    mr.activity_type,
    mr.location,
    mr.route_id,
    mr.cost_usd,
    mr.is_emergency,
    ST_Area(mr.location::geography) as area_m2,
    ST_Length(mr.location::geography) as length_m
FROM maintenance_records mr
WHERE mr.activity_date >= CURRENT_DATE - INTERVAL '5 years';

-- View: Surface distress near borings
CREATE OR REPLACE VIEW v_distress_near_borings AS
SELECT 
    gp.id as boring_id,
    gp.point_id,
    so.id as observation_id,
    so.distress_type,
    so.severity,
    so.observation_date,
    ST_Distance(gp.location, so.observation_line) as distance_m
FROM geotechnical_points gp
CROSS JOIN LATERAL (
    SELECT * FROM surface_observations so
    WHERE ST_DWithin(gp.location::geography, so.observation_line::geography, 100)
    ORDER BY ST_Distance(gp.location, so.observation_line)
    LIMIT 10
) so;

-- Function: Find borings within distance of a point
CREATE OR REPLACE FUNCTION find_borings_near_point(
    search_point GEOMETRY,
    search_radius_m NUMERIC
)
RETURNS TABLE (
    boring_id UUID,
    point_id VARCHAR,
    distance_m NUMERIC,
    location GEOMETRY,
    project_number VARCHAR
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        gp.id,
        gp.point_id,
        ST_Distance(gp.location::geography, search_point::geography) as distance_m,
        gp.location,
        p.project_number
    FROM geotechnical_points gp
    LEFT JOIN projects p ON gp.project_id = p.id
    WHERE ST_DWithin(gp.location::geography, search_point::geography, search_radius_m)
    ORDER BY ST_Distance(gp.location::geography, search_point::geography);
END;
$$ LANGUAGE plpgsql;

-- Function: Calculate maintenance frequency for an area
CREATE OR REPLACE FUNCTION calculate_maintenance_frequency(
    area_polygon GEOMETRY,
    years_back INTEGER DEFAULT 5
)
RETURNS TABLE (
    activity_type maintenance_type,
    count BIGINT,
    total_cost NUMERIC,
    avg_cost NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        mr.activity_type,
        COUNT(*) as count,
        SUM(mr.cost_usd) as total_cost,
        AVG(mr.cost_usd) as avg_cost
    FROM maintenance_records mr
    WHERE ST_Intersects(mr.location, area_polygon)
    AND mr.activity_date >= CURRENT_DATE - (years_back || ' years')::INTERVAL
    GROUP BY mr.activity_type
    ORDER BY COUNT(*) DESC;
END;
$$ LANGUAGE plpgsql;

-- Function: Correlate surface distress with subsurface conditions
CREATE OR REPLACE FUNCTION correlate_distress_subsurface(
    correlation_distance_m NUMERIC DEFAULT 50
)
RETURNS TABLE (
    distress_type VARCHAR,
    severity distress_severity,
    avg_spt_n_value NUMERIC,
    boring_count BIGINT,
    correlation_score NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    WITH distress_boring_pairs AS (
        SELECT 
            so.distress_type,
            so.severity,
            spt.n_value
        FROM surface_observations so
        JOIN geotechnical_points gp 
            ON ST_DWithin(so.observation_line::geography, gp.location::geography, correlation_distance_m)
        JOIN spt_results spt ON spt.point_id = gp.id
        WHERE so.severity IS NOT NULL
        AND spt.n_value IS NOT NULL
    )
    SELECT 
        dbp.distress_type,
        dbp.severity,
        AVG(dbp.n_value) as avg_spt_n_value,
        COUNT(DISTINCT dbp.n_value) as boring_count,
        CASE 
            WHEN STDDEV(dbp.n_value) = 0 THEN 1.0
            ELSE 1.0 / (1.0 + STDDEV(dbp.n_value) / AVG(dbp.n_value))
        END as correlation_score
    FROM distress_boring_pairs dbp
    GROUP BY dbp.distress_type, dbp.severity
    HAVING COUNT(*) >= 5
    ORDER BY dbp.distress_type, dbp.severity;
END;
$$ LANGUAGE plpgsql;

-- Function: Generate subsurface profile along a line
CREATE OR REPLACE FUNCTION generate_subsurface_profile(
    profile_line GEOMETRY,
    buffer_distance_m NUMERIC DEFAULT 50
)
RETURNS TABLE (
    distance_along_line NUMERIC,
    boring_id UUID,
    point_id VARCHAR,
    offset_from_line NUMERIC,
    elevation_m NUMERIC,
    layer_top NUMERIC,
    layer_bottom NUMERIC,
    material_description TEXT,
    uscs_classification VARCHAR
) AS $$
BEGIN
    RETURN QUERY
    WITH line_points AS (
        SELECT 
            gp.*,
            ST_Distance(gp.location::geography, profile_line::geography) as offset_m,
            ST_LineLocatePoint(profile_line, gp.location) as fraction_along
        FROM geotechnical_points gp
        WHERE ST_DWithin(gp.location::geography, profile_line::geography, buffer_distance_m)
    )
    SELECT 
        ST_Length(profile_line::geography) * lp.fraction_along as distance_along_line,
        lp.id as boring_id,
        lp.point_id,
        lp.offset_m as offset_from_line,
        lp.elevation_m,
        sl.top_depth_m as layer_top,
        sl.bottom_depth_m as layer_bottom,
        sl.material_description,
        sl.uscs_classification
    FROM line_points lp
    JOIN subsurface_layers sl ON sl.point_id = lp.id
    ORDER BY distance_along_line, layer_top;
END;
$$ LANGUAGE plpgsql;

-- Materialized view for performance: Grid-based statistics
CREATE MATERIALIZED VIEW mv_grid_statistics AS
WITH grid AS (
    SELECT 
        row_number() OVER () as grid_id,
        cell
    FROM (
        SELECT ST_SquareGrid(1000, ST_Extent(location)) as cell
        FROM geotechnical_points
    ) g
)
SELECT 
    g.grid_id,
    g.cell as geometry,
    COUNT(DISTINCT gp.id) as boring_count,
    AVG(gp.total_depth_m) as avg_depth,
    AVG(gp.rock_depth_m) as avg_rock_depth,
    COUNT(DISTINCT mr.id) as maintenance_count,
    SUM(mr.cost_usd) as total_maintenance_cost,
    AVG(so.rut_depth_mm) as avg_rut_depth
FROM grid g
LEFT JOIN geotechnical_points gp ON ST_Contains(g.cell, gp.location)
LEFT JOIN maintenance_records mr ON ST_Intersects(g.cell, mr.location)
LEFT JOIN surface_observations so ON ST_Intersects(g.cell, so.observation_line)
GROUP BY g.grid_id, g.cell;

-- Create index on materialized view
CREATE INDEX idx_mv_grid_geom ON mv_grid_statistics USING GIST(geometry);

-- Function to refresh materialized view
CREATE OR REPLACE FUNCTION refresh_grid_statistics()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_grid_statistics;
END;
$$ LANGUAGE plpgsql;

-- Add comments
COMMENT ON VIEW v_boring_summary IS 'Summary view of all boring locations with counts of related data';
COMMENT ON VIEW v_maintenance_summary IS 'Recent maintenance activities with calculated metrics';
COMMENT ON VIEW v_distress_near_borings IS 'Surface distress observations near boring locations';
COMMENT ON FUNCTION find_borings_near_point IS 'Find all borings within specified distance of a point';
COMMENT ON FUNCTION calculate_maintenance_frequency IS 'Calculate maintenance statistics for an area';
COMMENT ON FUNCTION correlate_distress_subsurface IS 'Correlate surface distress with subsurface conditions';
COMMENT ON FUNCTION generate_subsurface_profile IS 'Generate subsurface profile data along a line';
COMMENT ON MATERIALIZED VIEW mv_grid_statistics IS 'Pre-calculated grid-based statistics for performance';