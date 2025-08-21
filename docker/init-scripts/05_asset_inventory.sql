-- Geotechnical Asset Inventory Tables
-- Track geotechnical assets, risk features, and foundations

SET search_path TO gms, public;

-- Asset type enumerations
CREATE TYPE asset_type AS ENUM (
    'slope',
    'embankment',
    'retaining_wall',
    'bridge_foundation',
    'sound_wall',
    'sign_foundation',
    'culvert',
    'tunnel',
    'dam',
    'levee',
    'other'
);

CREATE TYPE asset_condition AS ENUM (
    'excellent',
    'good',
    'fair',
    'poor',
    'critical',
    'unknown'
);

CREATE TYPE risk_level AS ENUM (
    'very_low',
    'low',
    'moderate',
    'high',
    'very_high',
    'critical'
);

-- Main geotechnical assets table
CREATE TABLE geotechnical_assets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    asset_id VARCHAR(100) UNIQUE NOT NULL,
    asset_type asset_type NOT NULL,
    asset_name VARCHAR(255),
    location GEOMETRY(GEOMETRY, 4326) NOT NULL, -- Can be point, line, or polygon
    route_id VARCHAR(50),
    mile_point NUMERIC(8,3),
    construction_date DATE,
    design_life_years INTEGER,
    current_condition asset_condition DEFAULT 'unknown',
    last_inspection_date DATE,
    next_inspection_due DATE,
    owner VARCHAR(255),
    maintainer VARCHAR(255),
    replacement_cost_usd NUMERIC(12,2),
    criticality_score NUMERIC(3,2) CHECK (criticality_score >= 0 AND criticality_score <= 1),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Slopes and embankments specific data
CREATE TABLE slope_inventory (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    asset_id UUID REFERENCES geotechnical_assets(id) ON DELETE CASCADE,
    slope_height_m NUMERIC(8,2),
    slope_angle_degrees NUMERIC(5,2),
    slope_length_m NUMERIC(10,2),
    material_type VARCHAR(100),
    vegetation_type VARCHAR(100),
    drainage_features TEXT,
    stability_analysis_date DATE,
    factor_of_safety NUMERIC(4,2),
    monitoring_required BOOLEAN DEFAULT FALSE,
    instrumentation_type TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Retaining walls inventory
CREATE TABLE retaining_walls (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    asset_id UUID REFERENCES geotechnical_assets(id) ON DELETE CASCADE,
    wall_type VARCHAR(100), -- MSE, gravity, cantilever, sheet pile, etc.
    wall_height_m NUMERIC(8,2),
    wall_length_m NUMERIC(10,2),
    facing_material VARCHAR(100),
    backfill_type VARCHAR(100),
    drainage_system VARCHAR(255),
    design_lateral_pressure_kpa NUMERIC(10,2),
    reinforcement_type VARCHAR(100),
    reinforcement_length_m NUMERIC(8,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Foundation records (piles, footings, etc.)
CREATE TABLE foundation_inventory (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    asset_id UUID REFERENCES geotechnical_assets(id) ON DELETE CASCADE,
    structure_id VARCHAR(100),
    foundation_type VARCHAR(100), -- pile, drilled shaft, spread footing, mat
    pile_type VARCHAR(100), -- steel H, concrete, timber, pipe
    pile_count INTEGER,
    pile_depth_m NUMERIC(8,2),
    pile_capacity_kn NUMERIC(10,2),
    footing_dimensions VARCHAR(100),
    bearing_capacity_kpa NUMERIC(10,2),
    settlement_mm NUMERIC(8,2),
    load_test_date DATE,
    load_test_results JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Risk features (sinkholes, karst, landslides)
CREATE TABLE risk_features (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    feature_id VARCHAR(100) UNIQUE NOT NULL,
    feature_type VARCHAR(100), -- sinkhole, karst, landslide, settlement, erosion
    location GEOMETRY(GEOMETRY, 4326) NOT NULL,
    discovery_date DATE,
    size_m2 NUMERIC(10,2),
    depth_m NUMERIC(8,2),
    risk_level risk_level DEFAULT 'moderate',
    active BOOLEAN DEFAULT TRUE,
    cause VARCHAR(255),
    mitigation_status VARCHAR(100),
    mitigation_date DATE,
    mitigation_method TEXT,
    mitigation_cost_usd NUMERIC(12,2),
    monitoring_frequency VARCHAR(50),
    last_monitored DATE,
    recurrence_history TEXT[],
    affected_assets UUID[] DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Sinkhole specific information
CREATE TABLE sinkhole_details (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    risk_feature_id UUID REFERENCES risk_features(id) ON DELETE CASCADE,
    sinkhole_type VARCHAR(50), -- cover-collapse, cover-subsidence, dissolution
    bedrock_type VARCHAR(100),
    bedrock_depth_m NUMERIC(8,2),
    water_present BOOLEAN,
    previous_repairs INTEGER DEFAULT 0,
    subsidence_rate_mm_year NUMERIC(8,2),
    buffer_zone_m NUMERIC(8,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Stabilization measures inventory
CREATE TABLE stabilization_measures (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    related_asset_id UUID REFERENCES geotechnical_assets(id),
    related_risk_id UUID REFERENCES risk_features(id),
    measure_type VARCHAR(100), -- soil nail, rock bolt, anchor, drainage, reinforcement
    location GEOMETRY(GEOMETRY, 4326) NOT NULL,
    installation_date DATE,
    design_life_years INTEGER,
    quantity INTEGER,
    unit_of_measure VARCHAR(20),
    material_specs TEXT,
    installation_cost_usd NUMERIC(12,2),
    contractor VARCHAR(255),
    warranty_expiry DATE,
    performance_criteria TEXT,
    last_inspection_date DATE,
    condition asset_condition DEFAULT 'good',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Asset inspection history
CREATE TABLE asset_inspections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    asset_id UUID REFERENCES geotechnical_assets(id) ON DELETE CASCADE,
    inspection_date DATE NOT NULL,
    inspector_name VARCHAR(255),
    inspection_type VARCHAR(100),
    condition_rating asset_condition,
    defects_noted TEXT[],
    measurements JSONB,
    photos TEXT[],
    recommendations TEXT,
    follow_up_required BOOLEAN DEFAULT FALSE,
    follow_up_date DATE,
    report_pdf_path VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Asset performance monitoring
CREATE TABLE asset_monitoring (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    asset_id UUID REFERENCES geotechnical_assets(id) ON DELETE CASCADE,
    monitoring_date TIMESTAMP WITH TIME ZONE NOT NULL,
    parameter_name VARCHAR(100),
    parameter_value NUMERIC,
    parameter_unit VARCHAR(20),
    sensor_id VARCHAR(100),
    alarm_triggered BOOLEAN DEFAULT FALSE,
    threshold_exceeded BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX idx_geotech_assets_type ON geotechnical_assets(asset_type);
CREATE INDEX idx_geotech_assets_location ON geotechnical_assets USING GIST(location);
CREATE INDEX idx_geotech_assets_condition ON geotechnical_assets(current_condition);
CREATE INDEX idx_geotech_assets_route ON geotechnical_assets(route_id);

CREATE INDEX idx_risk_features_type ON risk_features(feature_type);
CREATE INDEX idx_risk_features_location ON risk_features USING GIST(location);
CREATE INDEX idx_risk_features_active ON risk_features(active) WHERE active = TRUE;
CREATE INDEX idx_risk_features_level ON risk_features(risk_level);

CREATE INDEX idx_stabilization_asset ON stabilization_measures(related_asset_id);
CREATE INDEX idx_stabilization_risk ON stabilization_measures(related_risk_id);
CREATE INDEX idx_stabilization_location ON stabilization_measures USING GIST(location);

CREATE INDEX idx_inspections_asset ON asset_inspections(asset_id);
CREATE INDEX idx_inspections_date ON asset_inspections(inspection_date);
CREATE INDEX idx_inspections_followup ON asset_inspections(follow_up_required) WHERE follow_up_required = TRUE;

CREATE INDEX idx_monitoring_asset ON asset_monitoring(asset_id);
CREATE INDEX idx_monitoring_date ON asset_monitoring(monitoring_date);
CREATE INDEX idx_monitoring_alarm ON asset_monitoring(alarm_triggered) WHERE alarm_triggered = TRUE;

-- Views for asset management
CREATE OR REPLACE VIEW v_assets_requiring_inspection AS
SELECT 
    ga.*,
    CURRENT_DATE - ga.last_inspection_date as days_since_inspection,
    ga.next_inspection_due - CURRENT_DATE as days_until_due
FROM geotechnical_assets ga
WHERE ga.next_inspection_due <= CURRENT_DATE + INTERVAL '30 days'
OR ga.last_inspection_date IS NULL
ORDER BY ga.next_inspection_due;

CREATE OR REPLACE VIEW v_high_risk_inventory AS
SELECT 
    rf.*,
    COUNT(DISTINCT ga.id) as affected_asset_count,
    ARRAY_AGG(DISTINCT ga.asset_name) as affected_asset_names
FROM risk_features rf
LEFT JOIN geotechnical_assets ga ON ga.id = ANY(rf.affected_assets)
WHERE rf.risk_level IN ('high', 'very_high', 'critical')
AND rf.active = TRUE
GROUP BY rf.id
ORDER BY rf.risk_level DESC, rf.discovery_date DESC;

-- Functions for asset analysis
CREATE OR REPLACE FUNCTION calculate_asset_risk_score(
    asset_uuid UUID
)
RETURNS NUMERIC AS $$
DECLARE
    risk_score NUMERIC := 0;
    asset_record RECORD;
    nearby_risks INTEGER;
    recent_failures INTEGER;
BEGIN
    -- Get asset details
    SELECT * INTO asset_record FROM geotechnical_assets WHERE id = asset_uuid;
    
    -- Base score from condition
    risk_score := CASE asset_record.current_condition
        WHEN 'critical' THEN 0.9
        WHEN 'poor' THEN 0.7
        WHEN 'fair' THEN 0.5
        WHEN 'good' THEN 0.3
        WHEN 'excellent' THEN 0.1
        ELSE 0.5
    END;
    
    -- Adjust for nearby risk features
    SELECT COUNT(*) INTO nearby_risks
    FROM risk_features rf
    WHERE ST_DWithin(rf.location::geography, asset_record.location::geography, 100)
    AND rf.active = TRUE;
    
    risk_score := risk_score + (nearby_risks * 0.1);
    
    -- Adjust for maintenance history
    SELECT COUNT(*) INTO recent_failures
    FROM maintenance_records mr
    WHERE ST_DWithin(mr.location::geography, asset_record.location::geography, 50)
    AND mr.is_emergency = TRUE
    AND mr.activity_date >= CURRENT_DATE - INTERVAL '2 years';
    
    risk_score := risk_score + (recent_failures * 0.05);
    
    -- Cap at 1.0
    RETURN LEAST(risk_score, 1.0);
END;
$$ LANGUAGE plpgsql;

-- Add comments for documentation
COMMENT ON TABLE geotechnical_assets IS 'Master inventory of all geotechnical assets';
COMMENT ON TABLE slope_inventory IS 'Detailed information for slopes and embankments';
COMMENT ON TABLE retaining_walls IS 'Inventory of retaining structures';
COMMENT ON TABLE foundation_inventory IS 'Bridge and structure foundation records including piles';
COMMENT ON TABLE risk_features IS 'Inventory of geotechnical hazards including sinkholes and karst';
COMMENT ON TABLE sinkhole_details IS 'Specific information for sinkhole features';
COMMENT ON TABLE stabilization_measures IS 'Inventory of soil/rock reinforcement and stabilization';
COMMENT ON TABLE asset_inspections IS 'Historical inspection records for assets';
COMMENT ON TABLE asset_monitoring IS 'Time-series monitoring data from instrumentation';

-- Trigger to update timestamps
CREATE TRIGGER update_geotech_assets_updated_at BEFORE UPDATE ON geotechnical_assets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_risk_features_updated_at BEFORE UPDATE ON risk_features
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();