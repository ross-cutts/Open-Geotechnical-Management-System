-- Integration Tables for External Data Sources
-- Surface observations, maintenance records, elevation data, etc.

SET search_path TO gms, public;

-- Surface distress severity levels
CREATE TYPE distress_severity AS ENUM ('low', 'medium', 'high', 'severe');

-- Maintenance activity types
CREATE TYPE maintenance_type AS ENUM (
    'patching',
    'crack_sealing',
    'resurfacing',
    'reconstruction',
    'emergency_repair',
    'sinkhole_repair',
    'drainage_improvement',
    'other'
);

-- ARAN/Surface observation data
CREATE TABLE surface_observations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    observation_date DATE NOT NULL,
    survey_id VARCHAR(100),
    route_id VARCHAR(50),
    start_point GEOMETRY(POINT, 4326),
    end_point GEOMETRY(POINT, 4326),
    observation_line GEOMETRY(LINESTRING, 4326) NOT NULL,
    distress_type VARCHAR(100),
    severity distress_severity,
    quantity NUMERIC(10,2),
    quantity_unit VARCHAR(20),
    iri_value NUMERIC(6,2),
    rut_depth_mm NUMERIC(6,2),
    texture_depth_mm NUMERIC(6,2),
    image_paths TEXT[],
    data_source data_source_type DEFAULT 'aran_survey',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Maintenance/repair records
CREATE TABLE maintenance_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    activity_date DATE NOT NULL,
    activity_type maintenance_type NOT NULL,
    location GEOMETRY(GEOMETRY, 4326) NOT NULL, -- Can be point, line, or polygon
    route_id VARCHAR(50),
    mile_point_start NUMERIC(8,3),
    mile_point_end NUMERIC(8,3),
    description TEXT,
    quantity NUMERIC(10,2),
    quantity_unit VARCHAR(20),
    cost_usd NUMERIC(12,2),
    contractor VARCHAR(255),
    warranty_years INTEGER,
    is_emergency BOOLEAN DEFAULT FALSE,
    weather_conditions VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Digital Elevation Model (DEM) data points
CREATE TABLE elevation_points (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    location GEOMETRY(POINT, 4326) NOT NULL,
    elevation_m NUMERIC(8,2) NOT NULL,
    acquisition_date DATE,
    data_source VARCHAR(100),
    accuracy_m NUMERIC(4,2),
    point_density_per_m2 NUMERIC(6,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Slope stability analysis results
CREATE TABLE slope_analysis (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    analysis_polygon GEOMETRY(POLYGON, 4326) NOT NULL,
    analysis_date DATE,
    average_slope_degrees NUMERIC(5,2),
    max_slope_degrees NUMERIC(5,2),
    aspect_degrees NUMERIC(5,2),
    stability_factor NUMERIC(4,2),
    risk_category VARCHAR(50),
    vegetation_cover_percent NUMERIC(5,2),
    drainage_condition VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Groundwater monitoring data
CREATE TABLE groundwater_monitoring (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    well_location GEOMETRY(POINT, 4326) NOT NULL,
    well_id VARCHAR(100) UNIQUE NOT NULL,
    measurement_date TIMESTAMP WITH TIME ZONE NOT NULL,
    water_level_m_below_surface NUMERIC(8,2),
    water_elevation_m NUMERIC(8,2),
    temperature_c NUMERIC(5,2),
    ph NUMERIC(4,2),
    conductivity_us_cm NUMERIC(10,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Weather station data
CREATE TABLE weather_data (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    station_location GEOMETRY(POINT, 4326) NOT NULL,
    station_id VARCHAR(50),
    observation_date DATE NOT NULL,
    precipitation_mm NUMERIC(6,2),
    temperature_max_c NUMERIC(5,2),
    temperature_min_c NUMERIC(5,2),
    freeze_thaw_cycles INTEGER,
    snow_depth_mm NUMERIC(8,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(station_id, observation_date)
);

-- Traffic loading data
CREATE TABLE traffic_data (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    route_segment GEOMETRY(LINESTRING, 4326) NOT NULL,
    route_id VARCHAR(50),
    count_date DATE NOT NULL,
    aadt INTEGER,
    truck_percentage NUMERIC(5,2),
    esal_daily NUMERIC(10,2),
    speed_limit_mph INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Integration correlation table - Links different data sources
CREATE TABLE data_correlations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_table VARCHAR(100) NOT NULL,
    source_id UUID NOT NULL,
    target_table VARCHAR(100) NOT NULL,
    target_id UUID NOT NULL,
    correlation_type VARCHAR(100),
    distance_m NUMERIC(10,2),
    correlation_score NUMERIC(3,2) CHECK (correlation_score >= 0 AND correlation_score <= 1),
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb,
    UNIQUE(source_table, source_id, target_table, target_id)
);

-- Create spatial and performance indexes
CREATE INDEX idx_surface_obs_line ON surface_observations USING GIST(observation_line);
CREATE INDEX idx_surface_obs_date ON surface_observations(observation_date);
CREATE INDEX idx_surface_obs_severity ON surface_observations(severity);

CREATE INDEX idx_maintenance_location ON maintenance_records USING GIST(location);
CREATE INDEX idx_maintenance_date ON maintenance_records(activity_date);
CREATE INDEX idx_maintenance_type ON maintenance_records(activity_type);
CREATE INDEX idx_maintenance_emergency ON maintenance_records(is_emergency) WHERE is_emergency = TRUE;

CREATE INDEX idx_elevation_location ON elevation_points USING GIST(location);
CREATE INDEX idx_slope_polygon ON slope_analysis USING GIST(analysis_polygon);
CREATE INDEX idx_slope_risk ON slope_analysis(risk_category);

CREATE INDEX idx_groundwater_location ON groundwater_monitoring USING GIST(well_location);
CREATE INDEX idx_groundwater_date ON groundwater_monitoring(measurement_date);

CREATE INDEX idx_weather_location ON weather_data USING GIST(station_location);
CREATE INDEX idx_weather_date ON weather_data(observation_date);

CREATE INDEX idx_traffic_segment ON traffic_data USING GIST(route_segment);
CREATE INDEX idx_traffic_esal ON traffic_data(esal_daily);

CREATE INDEX idx_correlations_source ON data_correlations(source_table, source_id);
CREATE INDEX idx_correlations_target ON data_correlations(target_table, target_id);

-- Add comments for documentation
COMMENT ON TABLE surface_observations IS 'Surface distress data from ARAN vehicles or visual surveys';
COMMENT ON TABLE maintenance_records IS 'Historical maintenance and repair activities';
COMMENT ON TABLE elevation_points IS 'DEM points for topographic analysis';
COMMENT ON TABLE slope_analysis IS 'Slope stability analysis results for risk assessment';
COMMENT ON TABLE groundwater_monitoring IS 'Groundwater level monitoring data';
COMMENT ON TABLE weather_data IS 'Weather station data for environmental correlation';
COMMENT ON TABLE traffic_data IS 'Traffic counts and loading data';
COMMENT ON TABLE data_correlations IS 'Links between different data sources for integrated analysis';