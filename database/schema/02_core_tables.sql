-- Core Tables for GMS Foundation
-- Includes geotechnical points, projects, and data quality tracking

SET search_path TO gms, public;

-- Data sources enumeration
CREATE TYPE data_source_type AS ENUM (
    'field_investigation',
    'laboratory_test',
    'aran_survey',
    'lidar_dem',
    'maintenance_record',
    'historical_report',
    'utility_record',
    'other'
);

-- Confidence level enumeration
CREATE TYPE confidence_level AS ENUM (
    'high',
    'medium', 
    'low',
    'uncertain'
);

-- Projects table - Groups related investigations
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_number VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    location_description VARCHAR(255),
    project_bounds GEOMETRY(POLYGON, 4326),
    start_date DATE,
    end_date DATE,
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Geotechnical investigation points
CREATE TABLE geotechnical_points (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    point_id VARCHAR(100) NOT NULL,
    location GEOMETRY(POINT, 4326) NOT NULL,
    elevation_m NUMERIC(8,2),
    investigation_date DATE,
    investigation_type VARCHAR(100),
    contractor VARCHAR(255),
    total_depth_m NUMERIC(8,2),
    groundwater_depth_m NUMERIC(8,2),
    rock_depth_m NUMERIC(8,2),
    data_source data_source_type DEFAULT 'field_investigation',
    confidence confidence_level DEFAULT 'medium',
    quality_score NUMERIC(3,2) CHECK (quality_score >= 0 AND quality_score <= 1),
    report_pdf_path VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb,
    UNIQUE(project_id, point_id)
);

-- Subsurface layers/stratigraphy
CREATE TABLE subsurface_layers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    point_id UUID REFERENCES geotechnical_points(id) ON DELETE CASCADE,
    layer_number INTEGER NOT NULL,
    top_depth_m NUMERIC(8,2) NOT NULL,
    bottom_depth_m NUMERIC(8,2) NOT NULL,
    material_description TEXT,
    uscs_classification VARCHAR(10),
    aashto_classification VARCHAR(10),
    color VARCHAR(100),
    moisture_content VARCHAR(50),
    consistency_density VARCHAR(50),
    plasticity VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb,
    CHECK (bottom_depth_m > top_depth_m),
    UNIQUE(point_id, layer_number)
);

-- Standard Penetration Test (SPT) results
CREATE TABLE spt_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    point_id UUID REFERENCES geotechnical_points(id) ON DELETE CASCADE,
    depth_m NUMERIC(8,2) NOT NULL,
    blow_counts INTEGER[],
    n_value INTEGER,
    refusal BOOLEAN DEFAULT FALSE,
    sampler_type VARCHAR(50),
    hammer_type VARCHAR(50),
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Laboratory test results (flexible schema using JSONB)
CREATE TABLE laboratory_tests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    point_id UUID REFERENCES geotechnical_points(id) ON DELETE CASCADE,
    layer_id UUID REFERENCES subsurface_layers(id) ON DELETE CASCADE,
    sample_depth_m NUMERIC(8,2),
    test_type VARCHAR(100) NOT NULL,
    test_standard VARCHAR(50),
    test_date DATE,
    laboratory_name VARCHAR(255),
    results JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Create indexes for performance
CREATE INDEX idx_projects_project_number ON projects(project_number);
CREATE INDEX idx_projects_bounds ON projects USING GIST(project_bounds);
CREATE INDEX idx_geotech_points_location ON geotechnical_points USING GIST(location);
CREATE INDEX idx_geotech_points_project ON geotechnical_points(project_id);
CREATE INDEX idx_geotech_points_date ON geotechnical_points(investigation_date);
CREATE INDEX idx_subsurface_point ON subsurface_layers(point_id);
CREATE INDEX idx_spt_point ON spt_results(point_id);
CREATE INDEX idx_lab_point ON laboratory_tests(point_id);
CREATE INDEX idx_lab_test_type ON laboratory_tests(test_type);

-- Add comments for documentation
COMMENT ON TABLE projects IS 'Master project table for grouping related geotechnical investigations';
COMMENT ON TABLE geotechnical_points IS 'Individual boring/investigation locations with basic metadata';
COMMENT ON TABLE subsurface_layers IS 'Soil and rock layers encountered at each investigation point';
COMMENT ON TABLE spt_results IS 'Standard Penetration Test blow count data';
COMMENT ON TABLE laboratory_tests IS 'Flexible storage for various laboratory test results using JSONB';

-- Trigger to update timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_projects_updated_at BEFORE UPDATE ON projects
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_geotech_points_updated_at BEFORE UPDATE ON geotechnical_points
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();