# GMS Foundation - Geotechnical Management System

A modern, GIS-centric foundation for building Geotechnical Management Systems that integrate multiple data sources for comprehensive subsurface intelligence.

## 🎯 Vision

Transform traditional boring log databases into integrated spatial intelligence platforms that leverage ALL available data sources - from surface distress patterns to elevation changes - for better infrastructure decisions.

## 🗄️ Database Schema - Foundation for Your GMS

The core value of this repository is a **comprehensive database schema** designed specifically for geotechnical asset management. This schema can serve as the foundation for any agency looking to build a modern GMS.

### Entity Relationship Diagram

```mermaid
erDiagram
    %% Core Geotechnical Tables
    PROJECTS ||--o{ GEOTECHNICAL_POINTS : contains
    GEOTECHNICAL_POINTS ||--o{ SUBSURFACE_LAYERS : has
    GEOTECHNICAL_POINTS ||--o{ SPT_RESULTS : has
    GEOTECHNICAL_POINTS ||--o{ LABORATORY_TESTS : has
    SUBSURFACE_LAYERS ||--o{ LABORATORY_TESTS : tested_in
    
    %% Asset Management
    GEOTECHNICAL_ASSETS ||--o{ SLOPE_INVENTORY : details
    GEOTECHNICAL_ASSETS ||--o{ RETAINING_WALLS : details
    GEOTECHNICAL_ASSETS ||--o{ FOUNDATION_INVENTORY : details
    GEOTECHNICAL_ASSETS ||--o{ ASSET_INSPECTIONS : tracked_by
    
    %% Risk Management
    RISK_FEATURES ||--o{ SINKHOLE_DETAILS : classified_as
    RISK_FEATURES }o--o{ STABILIZATION_MEASURES : mitigated_by
    
    %% Data Integration
    GEOTECHNICAL_POINTS }o..o{ SURFACE_OBSERVATIONS : "correlated via proximity"
    GEOTECHNICAL_POINTS }o..o{ MAINTENANCE_RECORDS : "correlated via proximity"
    SURFACE_OBSERVATIONS }o..o{ MAINTENANCE_RECORDS : "correlated via proximity"
    
    %% Correlation System
    DATA_CORRELATIONS }o--|| GEOTECHNICAL_POINTS : references
    DATA_CORRELATIONS }o--|| SURFACE_OBSERVATIONS : references
    DATA_CORRELATIONS }o--|| MAINTENANCE_RECORDS : references
```

### Key Schema Features

#### 📍 **Core Geotechnical Data**
- Boring locations with full metadata
- Subsurface stratigraphy layers
- SPT blow counts and refusal data
- Flexible laboratory test storage (JSONB)
- Project-based organization

#### 🏗️ **Asset Inventory**
- **Earth Structures**: Slopes, embankments, levees
- **Retaining Systems**: MSE walls, soil nail walls, sheet piles
- **Foundations**: Bridge piles, spread footings, drilled shafts
- **Stabilization**: Rock bolts, anchors, drainage systems
- Complete inspection and monitoring history

#### ⚠️ **Risk Features**
- **Sinkholes**: Active, historical, and repaired
- **Karst Zones**: Risk areas and buffers
- **Landslides**: Historical and potential
- **Settlement Zones**: Monitoring and mitigation
- Risk levels and mitigation tracking

#### 🔄 **Data Integration**
- Surface distress observations (ARAN data)
- Maintenance and repair history
- Digital elevation models and slope analysis
- Weather and environmental data
- Traffic loading information
- Automatic correlation discovery

#### 📊 **Advanced Features**
- Spatial indexing for all geographic data
- Temporal tracking (valid_from, valid_to)
- Data quality and confidence scoring
- JSONB flexibility for evolving requirements
- Materialized views for performance
- Built-in spatial analysis functions

### Database Design Principles

1. **Spatial-First**: Every location uses PostGIS geometry types
2. **Flexible Storage**: JSONB for varying test types and metadata
3. **Quality Tracking**: Confidence levels and data source tracking
4. **Integration Ready**: Correlation system links any data types
5. **Performance Optimized**: Proper indexes and materialized views
6. **Standards Compliant**: Follows DIGGS and OGC specifications

> **For Agencies**: This schema provides a production-ready foundation that can be implemented as-is or customized for specific needs. It represents industry best practices and lessons learned from multiple DOT implementations.

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/[your-org]/gms-foundation
cd gms-foundation

# Start the entire stack
docker-compose up -d

# Check that services are running
docker-compose ps

# Access the services
# Web Interface: http://localhost:8080
# API: http://localhost:8000
# PgAdmin: http://localhost:5050
```

## 📋 Prerequisites

- Docker and Docker Compose
- Git
- 8GB+ RAM recommended
- 10GB+ free disk space

## 🏗️ Architecture

### Core Components

1. **PostgreSQL with PostGIS** - Spatial database engine
2. **FastAPI** - RESTful API with spatial query capabilities  
3. **Leaflet.js** - Web-based visualization
4. **ETL Scripts** - Data integration pipelines

### Data Sources Integration

The system is designed to integrate multiple data sources:

- **Geotechnical Borings** - Traditional SPT, lab tests, stratigraphy
- **Surface Imagery (ARAN)** - Pavement distress, rutting, cracking
- **Digital Elevation Models** - Slope analysis, subsidence detection
- **Maintenance Records** - Repair history, failure patterns
- **Weather Data** - Environmental impacts on infrastructure
- **Traffic Loading** - ESAL calculations and pavement stress

## 📁 Project Structure

```
gms-foundation/
├── database/
│   ├── schema/           # PostgreSQL/PostGIS schema files
│   ├── migrations/       # Database migration scripts
│   └── sample_data/      # Example datasets
├── etl/
│   ├── borings/         # DIGGS-compliant boring data imports
│   ├── elevation/       # DEM and LiDAR processing  
├── api/                 # FastAPI REST API
├── visualization/       # Web interface (Leaflet.js)
├── docker/             # Docker configuration
├── scripts/            # Utility scripts
└── docs/               # Additional documentation
```

## 📂 Database Implementation

The complete database schema is implemented in `/database/schema/` with the following SQL files:

1. **01_create_database.sql** - Database initialization and PostGIS setup
2. **02_core_tables.sql** - Core geotechnical data tables
3. **03_integration_tables.sql** - External data source integration
4. **04_views_functions.sql** - Spatial analysis functions and views
5. **05_asset_inventory.sql** - Geotechnical asset and risk management

See the [detailed schema documentation](docs/database_diagram.md) for complete table definitions and relationships.

## 🔌 API Endpoints

The FastAPI provides RESTful endpoints for all operations:

### Basic Queries
- `GET /api/borings` - List boring locations with filtering
- `GET /api/borings/{id}` - Detailed boring information
- `POST /api/spatial/search` - Search within radius

### Analysis
- `GET /api/analysis/maintenance-frequency` - Maintenance patterns
- `GET /api/analysis/subsurface-profile` - Generate cross-sections
- `GET /api/correlations` - Find data relationships

### Statistics
- `GET /api/stats/grid` - Pre-calculated grid statistics

## 📊 Data Processing

### ETL Scripts

#### ARAN Data Processing
```bash
python etl/imagery/process_aran_data.py \
  --input-file data/aran_survey.json \
  --correlation-distance 50
```

#### DEM Processing
```bash
python etl/elevation/process_dem_data.py \
  --dem-file data/elevation.tif \
  --slope-threshold 30
```

### Data Integration

The system automatically correlates different data sources based on spatial proximity:

1. Surface distress is linked to nearby borings
2. Maintenance records are correlated with subsurface conditions
3. Slope stability is analyzed with geotechnical properties

## 🗺️ Visualization

The web interface provides:

- Interactive 2D map with multiple data layers
- Cross-section generation tool
- Heat maps for various metrics
- Time-series analysis for temporal data

## 📈 Analysis Capabilities

The system supports various analytical functions:

1. **Correlation Analysis** - Discover relationships between surface distress and subsurface conditions
2. **Predictive Maintenance** - Use historical patterns to predict future failures
3. **Risk Assessment** - Combine multiple factors to identify risk zones
4. **Cost Optimization** - Prioritize maintenance investments based on risk and condition

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=gms_foundation
DB_USER=gms_user
DB_PASSWORD=your_secure_password

# API
API_PORT=8000
API_WORKERS=4

# Web
WEB_PORT=8080
```

### Database Connection

Standard PostgreSQL connection string:
```
postgresql://gms_user:password@localhost:5432/gms_foundation
```

## 🧪 Testing

```bash
# Run unit tests
docker-compose exec api pytest

# Run integration tests
./scripts/run_integration_tests.sh

# Test spatial queries
docker-compose exec postgres psql -U gms_user -d gms_foundation -f tests/spatial_tests.sql
```

## 📚 Documentation

- [Database Schema Details](docs/database_diagram.md)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Based on work from PennDOT, Md DOT.
- Built on open standards including DIGGS and OGC specifications
- Leverages PostGIS for spatial capabilities
- Inspired by modern GIS-centric infrastructure management approaches

## 🆘 Support

- GitHub Issues: [Report bugs or request features]([https://github.com/[your-org]/gms-foundation/issues](https://github.com/ross-cutts/Open-Geotechnical-Management-System/issues))

## 🚦 Roadmap

- [ ] Machine learning models for predictive analysis
- [ ] Real-time data streaming capabilities
- [ ] Mobile application for field data collection
- [ ] Advanced 3D visualization
- [ ] Integration with BIM systems
- [ ] Automated report generation

---

**Remember**: This is a foundation. Build upon it to create a GMS that meets your specific needs while maintaining the core principle of integrated, spatially-aware data management.
