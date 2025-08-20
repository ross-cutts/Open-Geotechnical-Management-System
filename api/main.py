"""
GMS Foundation API
RESTful API with spatial query capabilities
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import date, datetime
import psycopg2
from psycopg2.extras import RealDictCursor
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="GMS Foundation API",
    description="Geotechnical Management System API with spatial capabilities",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'postgres'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'database': os.getenv('DB_NAME', 'gms_foundation'),
    'user': os.getenv('DB_USER', 'gms_user'),
    'password': os.getenv('DB_PASSWORD', 'gms_password')
}

# Pydantic models
class PointLocation(BaseModel):
    latitude: float
    longitude: float

class BoundingBox(BaseModel):
    min_lat: float
    min_lon: float
    max_lat: float
    max_lon: float

class GeotechnicalPoint(BaseModel):
    id: str
    point_id: str
    location: PointLocation
    elevation_m: Optional[float]
    investigation_date: Optional[date]
    total_depth_m: Optional[float]
    project_number: Optional[str]
    confidence: Optional[str]

class SurfaceObservation(BaseModel):
    id: str
    observation_date: date
    distress_type: Optional[str]
    severity: Optional[str]
    iri_value: Optional[float]
    rut_depth_mm: Optional[float]

class CorrelationResult(BaseModel):
    source_type: str
    source_id: str
    target_type: str
    target_id: str
    distance_m: float
    correlation_score: float

# Database connection helper
def get_db_connection():
    """Create database connection"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection failed: {str(e)}")

# API Endpoints
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "GMS Foundation API",
        "version": "1.0.0",
        "endpoints": {
            "borings": "/api/borings",
            "surface_observations": "/api/surface-observations",
            "spatial_search": "/api/spatial/search",
            "correlations": "/api/correlations"
        }
    }

@app.get("/api/borings", response_model=List[Dict[str, Any]])
async def get_borings(
    bbox: Optional[str] = Query(None, description="Bounding box: min_lon,min_lat,max_lon,max_lat"),
    project_number: Optional[str] = None,
    limit: int = Query(100, le=1000),
    offset: int = 0
):
    """Get geotechnical boring points with optional spatial filtering"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        query = """
        SELECT 
            gp.id,
            gp.point_id,
            ST_Y(gp.location) as latitude,
            ST_X(gp.location) as longitude,
            gp.elevation_m,
            gp.investigation_date,
            gp.total_depth_m,
            gp.groundwater_depth_m,
            gp.rock_depth_m,
            gp.confidence,
            p.project_number,
            p.name as project_name
        FROM gms.geotechnical_points gp
        LEFT JOIN gms.projects p ON gp.project_id = p.id
        WHERE 1=1
        """
        
        params = []
        
        # Add spatial filter if bbox provided
        if bbox:
            coords = [float(x) for x in bbox.split(',')]
            if len(coords) == 4:
                query += """
                AND gp.location && ST_MakeEnvelope(%s, %s, %s, %s, 4326)
                """
                params.extend(coords)
        
        # Add project filter
        if project_number:
            query += " AND p.project_number = %s"
            params.append(project_number)
            
        query += " ORDER BY gp.created_at DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        return results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

@app.get("/api/borings/{boring_id}")
async def get_boring_details(boring_id: str):
    """Get detailed information for a specific boring"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # Get boring details
        cursor.execute("""
            SELECT 
                gp.*,
                ST_Y(gp.location) as latitude,
                ST_X(gp.location) as longitude,
                p.project_number,
                p.name as project_name
            FROM gms.geotechnical_points gp
            LEFT JOIN gms.projects p ON gp.project_id = p.id
            WHERE gp.id = %s::uuid
        """, (boring_id,))
        
        boring = cursor.fetchone()
        if not boring:
            raise HTTPException(status_code=404, detail="Boring not found")
            
        # Get layers
        cursor.execute("""
            SELECT * FROM gms.subsurface_layers
            WHERE point_id = %s::uuid
            ORDER BY top_depth_m
        """, (boring_id,))
        layers = cursor.fetchall()
        
        # Get SPT results
        cursor.execute("""
            SELECT * FROM gms.spt_results
            WHERE point_id = %s::uuid
            ORDER BY depth_m
        """, (boring_id,))
        spt_results = cursor.fetchall()
        
        # Get lab tests
        cursor.execute("""
            SELECT * FROM gms.laboratory_tests
            WHERE point_id = %s::uuid
            ORDER BY test_type, sample_depth_m
        """, (boring_id,))
        lab_tests = cursor.fetchall()
        
        result = {
            "boring": boring,
            "layers": layers,
            "spt_results": spt_results,
            "lab_tests": lab_tests
        }
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

@app.post("/api/spatial/search")
async def spatial_search(
    center: PointLocation,
    radius_m: float = Query(..., description="Search radius in meters"),
    data_types: List[str] = Query(["borings"], description="Data types to search")
):
    """Search for data within a radius of a point"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        results = {}
        
        # Search borings
        if "borings" in data_types:
            cursor.execute("""
                SELECT 
                    gp.id,
                    gp.point_id,
                    ST_Y(gp.location) as latitude,
                    ST_X(gp.location) as longitude,
                    ST_Distance(
                        gp.location::geography,
                        ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography
                    ) as distance_m,
                    gp.total_depth_m,
                    p.project_number
                FROM gms.geotechnical_points gp
                LEFT JOIN gms.projects p ON gp.project_id = p.id
                WHERE ST_DWithin(
                    gp.location::geography,
                    ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography,
                    %s
                )
                ORDER BY distance_m
                LIMIT 100
            """, (center.longitude, center.latitude, center.longitude, center.latitude, radius_m))
            
            results["borings"] = cursor.fetchall()
            
        # Search surface observations
        if "surface_observations" in data_types:
            cursor.execute("""
                SELECT 
                    so.id,
                    so.observation_date,
                    so.distress_type,
                    so.severity,
                    ST_Distance(
                        so.observation_line::geography,
                        ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography
                    ) as distance_m
                FROM gms.surface_observations so
                WHERE ST_DWithin(
                    so.observation_line::geography,
                    ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography,
                    %s
                )
                ORDER BY distance_m
                LIMIT 100
            """, (center.longitude, center.latitude, center.longitude, center.latitude, radius_m))
            
            results["surface_observations"] = cursor.fetchall()
            
        # Search maintenance records
        if "maintenance" in data_types:
            cursor.execute("""
                SELECT 
                    mr.id,
                    mr.activity_date,
                    mr.activity_type,
                    mr.cost_usd,
                    ST_Distance(
                        mr.location::geography,
                        ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography
                    ) as distance_m
                FROM gms.maintenance_records mr
                WHERE ST_DWithin(
                    mr.location::geography,
                    ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography,
                    %s
                )
                ORDER BY distance_m
                LIMIT 100
            """, (center.longitude, center.latitude, center.longitude, center.latitude, radius_m))
            
            results["maintenance_records"] = cursor.fetchall()
            
        return results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

@app.get("/api/correlations")
async def get_correlations(
    source_type: str = Query(..., description="Source data type"),
    source_id: str = Query(..., description="Source record ID"),
    max_distance: float = Query(100, description="Maximum correlation distance in meters")
):
    """Get correlations between different data sources"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        cursor.execute("""
            SELECT * FROM gms.data_correlations
            WHERE source_table = %s
            AND source_id = %s::uuid
            AND distance_m <= %s
            ORDER BY correlation_score DESC, distance_m
        """, (source_type, source_id, max_distance))
        
        results = cursor.fetchall()
        return results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

@app.get("/api/analysis/maintenance-frequency")
async def analyze_maintenance_frequency(
    bbox: str = Query(..., description="Bounding box: min_lon,min_lat,max_lon,max_lat"),
    years_back: int = Query(5, description="Years of history to analyze")
):
    """Analyze maintenance frequency for an area"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        coords = [float(x) for x in bbox.split(',')]
        if len(coords) != 4:
            raise HTTPException(status_code=400, detail="Invalid bounding box")
            
        cursor.execute("""
            SELECT * FROM gms.calculate_maintenance_frequency(
                ST_MakeEnvelope(%s, %s, %s, %s, 4326),
                %s
            )
        """, (*coords, years_back))
        
        results = cursor.fetchall()
        return results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

@app.get("/api/analysis/subsurface-profile")
async def generate_subsurface_profile(
    line_wkt: str = Query(..., description="Line geometry in WKT format"),
    buffer_m: float = Query(50, description="Buffer distance in meters")
):
    """Generate subsurface profile along a line"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        cursor.execute("""
            SELECT * FROM gms.generate_subsurface_profile(
                ST_GeomFromText(%s, 4326),
                %s
            )
        """, (line_wkt, buffer_m))
        
        results = cursor.fetchall()
        return results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

@app.get("/api/stats/grid")
async def get_grid_statistics(
    bbox: Optional[str] = Query(None, description="Bounding box filter")
):
    """Get pre-calculated grid statistics"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        query = """
            SELECT 
                grid_id,
                ST_AsGeoJSON(geometry) as geojson,
                boring_count,
                avg_depth,
                avg_rock_depth,
                maintenance_count,
                total_maintenance_cost,
                avg_rut_depth
            FROM gms.mv_grid_statistics
            WHERE 1=1
        """
        
        params = []
        
        if bbox:
            coords = [float(x) for x in bbox.split(',')]
            if len(coords) == 4:
                query += """
                AND geometry && ST_MakeEnvelope(%s, %s, %s, %s, 4326)
                """
                params.extend(coords)
                
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        # Convert GeoJSON strings to objects
        for row in results:
            row['geometry'] = json.loads(row.pop('geojson'))
            
        return results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

# Health check endpoint
@app.get("/health")
async def health_check():
    """API health check"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        conn.close()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)