# GMS Foundation Database Schema

## Entity Relationship Diagram

```mermaid
erDiagram
    %% Core Geotechnical Tables
    PROJECTS {
        uuid id PK
        varchar project_number UK
        varchar name
        text description
        geometry project_bounds
        date start_date
        date end_date
        varchar status
        jsonb metadata
    }

    GEOTECHNICAL_POINTS {
        uuid id PK
        uuid project_id FK
        varchar point_id
        geometry location
        numeric elevation_m
        date investigation_date
        varchar investigation_type
        numeric total_depth_m
        numeric groundwater_depth_m
        numeric rock_depth_m
        enum data_source
        enum confidence
        numeric quality_score
        varchar report_pdf_path
        jsonb metadata
    }

    SUBSURFACE_LAYERS {
        uuid id PK
        uuid point_id FK
        integer layer_number
        numeric top_depth_m
        numeric bottom_depth_m
        text material_description
        varchar uscs_classification
        varchar aashto_classification
        varchar color
        varchar moisture_content
        varchar consistency_density
        jsonb metadata
    }

    SPT_RESULTS {
        uuid id PK
        uuid point_id FK
        numeric depth_m
        integer_array blow_counts
        integer n_value
        boolean refusal
        varchar sampler_type
        varchar hammer_type
        text notes
    }

    LABORATORY_TESTS {
        uuid id PK
        uuid point_id FK
        uuid layer_id FK
        numeric sample_depth_m
        varchar test_type
        varchar test_standard
        date test_date
        varchar laboratory_name
        jsonb results
    }

    %% Integration Tables
    SURFACE_OBSERVATIONS {
        uuid id PK
        date observation_date
        varchar survey_id
        varchar route_id
        geometry start_point
        geometry end_point
        geometry observation_line
        varchar distress_type
        enum severity
        numeric iri_value
        numeric rut_depth_mm
        text_array image_paths
        jsonb metadata
    }

    MAINTENANCE_RECORDS {
        uuid id PK
        date activity_date
        enum activity_type
        geometry location
        varchar route_id
        numeric mile_point_start
        numeric mile_point_end
        text description
        numeric cost_usd
        boolean is_emergency
        jsonb metadata
    }

    ELEVATION_POINTS {
        uuid id PK
        geometry location
        numeric elevation_m
        date acquisition_date
        varchar data_source
        numeric accuracy_m
        numeric point_density_per_m2
    }

    SLOPE_ANALYSIS {
        uuid id PK
        geometry analysis_polygon
        date analysis_date
        numeric average_slope_degrees
        numeric max_slope_degrees
        varchar risk_category
        numeric vegetation_cover_percent
        jsonb metadata
    }

    GROUNDWATER_MONITORING {
        uuid id PK
        geometry well_location
        varchar well_id UK
        timestamp measurement_date
        numeric water_level_m_below_surface
        numeric water_elevation_m
        numeric temperature_c
        numeric ph
        jsonb metadata
    }

    WEATHER_DATA {
        uuid id PK
        geometry station_location
        varchar station_id
        date observation_date
        numeric precipitation_mm
        numeric temperature_max_c
        numeric temperature_min_c
        integer freeze_thaw_cycles
    }

    TRAFFIC_DATA {
        uuid id PK
        geometry route_segment
        varchar route_id
        date count_date
        integer aadt
        numeric truck_percentage
        numeric esal_daily
        jsonb metadata
    }

    DATA_CORRELATIONS {
        uuid id PK
        varchar source_table
        uuid source_id
        varchar target_table
        uuid target_id
        varchar correlation_type
        numeric distance_m
        numeric correlation_score
        timestamp calculated_at
        jsonb metadata
    }

    %% Relationships
    PROJECTS ||--o{ GEOTECHNICAL_POINTS : contains
    GEOTECHNICAL_POINTS ||--o{ SUBSURFACE_LAYERS : has
    GEOTECHNICAL_POINTS ||--o{ SPT_RESULTS : has
    GEOTECHNICAL_POINTS ||--o{ LABORATORY_TESTS : has
    SUBSURFACE_LAYERS ||--o{ LABORATORY_TESTS : tested_in
    
    %% Correlations (simplified - actual correlations are dynamic)
    GEOTECHNICAL_POINTS }o..o{ SURFACE_OBSERVATIONS : "correlated via proximity"
    GEOTECHNICAL_POINTS }o..o{ MAINTENANCE_RECORDS : "correlated via proximity"
    SURFACE_OBSERVATIONS }o..o{ MAINTENANCE_RECORDS : "correlated via proximity"
    
    %% Data Correlations table links everything
    DATA_CORRELATIONS }o--|| GEOTECHNICAL_POINTS : references
    DATA_CORRELATIONS }o--|| SURFACE_OBSERVATIONS : references
    DATA_CORRELATIONS }o--|| MAINTENANCE_RECORDS : references
    DATA_CORRELATIONS }o--|| SLOPE_ANALYSIS : references
```

## Key Design Principles

### 1. **Spatial-First Design**
- Every table with location data uses PostGIS geometry types
- Spatial indexes enable fast proximity queries
- All coordinates stored in WGS84 (EPSG:4326)

### 2. **Flexible Data Storage**
- JSONB columns for metadata and variable test results
- Allows schema evolution without migrations
- Supports diverse data sources and formats

### 3. **Data Quality Tracking**
- Confidence levels and quality scores
- Data source tracking for provenance
- Temporal tracking with timestamps

### 4. **Integration Through Correlation**
- `DATA_CORRELATIONS` table links any data types
- Correlation scores indicate relationship strength
- Distance-based and analytical correlations

### 5. **Performance Optimization**
- Materialized views for complex calculations
- Spatial and standard indexes on key columns
- Partitioning ready for large datasets

## Common Query Patterns

### Find all data near a location
```sql
-- Using spatial functions to find related data
SELECT * FROM geotechnical_points
WHERE ST_DWithin(location, point::geography, radius_meters);
```

### Correlate surface and subsurface
```sql
-- Join through correlations table
SELECT gp.*, so.distress_type, dc.correlation_score
FROM geotechnical_points gp
JOIN data_correlations dc ON dc.target_id = gp.id
JOIN surface_observations so ON dc.source_id = so.id
WHERE dc.correlation_type = 'proximity';
```

### Generate subsurface profiles
```sql
-- Use built-in function for cross-sections
SELECT * FROM generate_subsurface_profile(
    ST_MakeLine(start_point, end_point),
    buffer_distance
);
```