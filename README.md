# GMS Foundation - Geotechnical Management System

A modern, GIS-centric foundation for building Geotechnical Management Systems that integrate multiple data sources for comprehensive subsurface intelligence.

## 🎯 Vision

Transform traditional boring log databases into integrated spatial intelligence platforms that leverage ALL available data sources - from surface distress patterns to elevation changes - for better infrastructure decisions.

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/[your-org]/gms-foundation
cd gms-foundation

# Start the entire stack
docker-compose up -d

# Check that services are running
docker-compose ps

# Load sample data (optional)
./scripts/load_sample_data.sh

# Access the services
# Web Interface: http://localhost:8080
# API: http://localhost:8000
# PgAdmin: http://localhost:5050
# Jupyter: http://localhost:8888
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
5. **Jupyter** - Analysis and exploration environment

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
│   ├── imagery/         # ARAN/surface imagery processing
│   ├── elevation/       # DEM and LiDAR processing
│   ├── maintenance/     # Maintenance record imports
│   └── integration/     # Data fusion and correlation
├── api/                 # FastAPI REST API
├── visualization/       # Web interface (Leaflet.js)
├── docker/             # Docker configuration
├── scripts/            # Utility scripts
└── docs/               # Additional documentation
```

## 🗄️ Database Schema

The database uses PostgreSQL with PostGIS extension for spatial capabilities. Key tables include:

### Core Tables
- `geotechnical_points` - Boring locations with metadata
- `subsurface_layers` - Stratigraphy information
- `spt_results` - Standard Penetration Test data
- `laboratory_tests` - Various lab test results (flexible JSONB)

### Integration Tables
- `surface_observations` - ARAN/imagery data
- `maintenance_records` - Historical repairs
- `elevation_points` - DEM data
- `slope_analysis` - Calculated slope risks
- `data_correlations` - Links between data sources

### Views and Functions
- Spatial search functions
- Correlation analysis
- Subsurface profile generation
- Grid-based statistics

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

## 📈 Analysis Examples

Jupyter notebooks demonstrate:

1. **Correlation Analysis** - How surface distress relates to subsurface
2. **Predictive Maintenance** - Using patterns to predict failures
3. **Risk Assessment** - Combining multiple factors for risk zones
4. **Cost Optimization** - Prioritizing maintenance investments

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

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built on open standards including DIGGS and OGC specifications
- Leverages PostGIS for spatial capabilities
- Inspired by modern GIS-centric infrastructure management approaches

## 🆘 Support

- GitHub Issues: [Report bugs or request features](https://github.com/[your-org]/gms-foundation/issues)
- Documentation: [Full documentation](https://github.com/[your-org]/gms-foundation/wiki)


## 🚦 Roadmap

- [ ] Machine learning models for predictive analysis
- [ ] Real-time data streaming capabilities
- [ ] Mobile application for field data collection
- [ ] Advanced 3D visualization
- [ ] Integration with BIM systems
- [ ] Automated report generation

---

**Remember**: This is a foundation. Build upon it to create a GMS that meets your specific needs while maintaining the core principle of integrated, spatially-aware data management.
