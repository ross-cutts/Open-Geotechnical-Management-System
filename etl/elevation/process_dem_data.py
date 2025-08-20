#!/usr/bin/env python3
"""
DEM (Digital Elevation Model) Processing Script
Processes elevation data for slope analysis and subsidence detection
"""

import rasterio
import numpy as np
from rasterio.warp import calculate_default_transform, reproject, Resampling
from scipy.ndimage import generic_gradient_magnitude, sobel
import psycopg2
from psycopg2.extras import RealDictCursor
import json
import logging
import argparse
from pathlib import Path
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DEMProcessor:
    def __init__(self, db_config):
        """Initialize DEM processor with database configuration"""
        self.db_config = db_config
        self.conn = None
        self.cursor = None
        
    def connect(self):
        """Establish database connection"""
        try:
            self.conn = psycopg2.connect(**self.db_config)
            self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)
            logger.info("Connected to database successfully")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise
            
    def disconnect(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
            
    def process_dem_file(self, dem_path, sample_spacing=100):
        """
        Process DEM file and extract elevation points
        """
        logger.info(f"Processing DEM file: {dem_path}")
        
        with rasterio.open(dem_path) as src:
            # Reproject to WGS84 if needed
            if src.crs.to_epsg() != 4326:
                transform, width, height = calculate_default_transform(
                    src.crs, 'EPSG:4326', src.width, src.height, *src.bounds
                )
                
                kwargs = src.meta.copy()
                kwargs.update({
                    'crs': 'EPSG:4326',
                    'transform': transform,
                    'width': width,
                    'height': height
                })
                
                # Create temporary reprojected array
                dem_data = np.empty((height, width), dtype=np.float32)
                reproject(
                    source=rasterio.band(src, 1),
                    destination=dem_data,
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=transform,
                    dst_crs='EPSG:4326',
                    resampling=Resampling.bilinear
                )
            else:
                dem_data = src.read(1)
                transform = src.transform
                
            # Sample points at regular intervals
            rows, cols = np.mgrid[0:dem_data.shape[0]:sample_spacing, 
                                 0:dem_data.shape[1]:sample_spacing]
            
            elevation_points = []
            for r, c in zip(rows.flatten(), cols.flatten()):
                if not np.isnan(dem_data[r, c]):
                    # Convert pixel coordinates to geographic coordinates
                    lon, lat = transform * (c, r)
                    elevation_points.append({
                        'longitude': lon,
                        'latitude': lat,
                        'elevation_m': float(dem_data[r, c]),
                        'acquisition_date': datetime.now().date().isoformat()
                    })
                    
            logger.info(f"Extracted {len(elevation_points)} elevation points")
            return elevation_points, dem_data, transform
            
    def calculate_slope(self, dem_data, transform, cell_size_m=30):
        """
        Calculate slope from DEM data
        """
        logger.info("Calculating slope from DEM")
        
        # Calculate gradients
        dy, dx = np.gradient(dem_data, cell_size_m)
        
        # Calculate slope in degrees
        slope_radians = np.arctan(np.sqrt(dx**2 + dy**2))
        slope_degrees = np.degrees(slope_radians)
        
        # Calculate aspect
        aspect_radians = np.arctan2(-dy, dx)
        aspect_degrees = np.degrees(aspect_radians)
        aspect_degrees[aspect_degrees < 0] += 360
        
        return slope_degrees, aspect_degrees
        
    def insert_elevation_points(self, points):
        """Insert elevation points into database"""
        insert_sql = """
        INSERT INTO gms.elevation_points (
            location, elevation_m, acquisition_date, data_source
        ) VALUES (
            ST_SetSRID(ST_MakePoint(%(longitude)s, %(latitude)s), 4326),
            %(elevation_m)s, %(acquisition_date)s, 'lidar_dem'
        );
        """
        
        for point in points:
            try:
                self.cursor.execute(insert_sql, point)
            except Exception as e:
                logger.error(f"Failed to insert elevation point: {e}")
                self.conn.rollback()
                raise
                
        self.conn.commit()
        logger.info(f"Inserted {len(points)} elevation points")
        
    def analyze_slope_stability(self, slope_degrees, aspect_degrees, transform, 
                              threshold_degrees=30, grid_size=10):
        """
        Analyze slope stability and identify high-risk areas
        """
        logger.info("Analyzing slope stability")
        
        high_slope_mask = slope_degrees > threshold_degrees
        
        # Create analysis polygons for high-slope areas
        analysis_results = []
        
        # Sample grid points
        rows, cols = np.mgrid[0:slope_degrees.shape[0]:grid_size, 
                             0:slope_degrees.shape[1]:grid_size]
        
        for r, c in zip(rows.flatten(), cols.flatten()):
            # Define grid cell bounds
            r_end = min(r + grid_size, slope_degrees.shape[0])
            c_end = min(c + grid_size, slope_degrees.shape[1])
            
            # Calculate statistics for grid cell
            cell_slopes = slope_degrees[r:r_end, c:c_end]
            cell_mask = high_slope_mask[r:r_end, c:c_end]
            
            if np.any(cell_mask):
                # Convert corner coordinates to geographic
                corners = [
                    transform * (c, r),
                    transform * (c_end, r),
                    transform * (c_end, r_end),
                    transform * (c, r_end),
                    transform * (c, r)  # Close polygon
                ]
                
                # Create WKT polygon
                wkt_polygon = "POLYGON((" + ",".join([f"{lon} {lat}" for lon, lat in corners]) + "))"
                
                analysis_results.append({
                    'polygon_wkt': wkt_polygon,
                    'avg_slope': float(np.mean(cell_slopes)),
                    'max_slope': float(np.max(cell_slopes)),
                    'high_slope_percent': float(np.sum(cell_mask) / cell_mask.size * 100),
                    'risk_category': self._classify_slope_risk(np.max(cell_slopes))
                })
                
        logger.info(f"Identified {len(analysis_results)} areas for slope analysis")
        return analysis_results
        
    def _classify_slope_risk(self, max_slope):
        """Classify slope risk based on maximum slope angle"""
        if max_slope < 15:
            return 'low'
        elif max_slope < 30:
            return 'moderate'
        elif max_slope < 45:
            return 'high'
        else:
            return 'very_high'
            
    def insert_slope_analysis(self, analysis_results):
        """Insert slope analysis results into database"""
        insert_sql = """
        INSERT INTO gms.slope_analysis (
            analysis_polygon, analysis_date, average_slope_degrees,
            max_slope_degrees, risk_category, metadata
        ) VALUES (
            ST_GeomFromText(%(polygon_wkt)s, 4326),
            CURRENT_DATE,
            %(avg_slope)s,
            %(max_slope)s,
            %(risk_category)s,
            %(metadata)s::jsonb
        );
        """
        
        for result in analysis_results:
            metadata = {
                'high_slope_percent': result['high_slope_percent'],
                'analysis_method': 'dem_gradient'
            }
            
            params = {
                'polygon_wkt': result['polygon_wkt'],
                'avg_slope': result['avg_slope'],
                'max_slope': result['max_slope'],
                'risk_category': result['risk_category'],
                'metadata': json.dumps(metadata)
            }
            
            try:
                self.cursor.execute(insert_sql, params)
            except Exception as e:
                logger.error(f"Failed to insert slope analysis: {e}")
                self.conn.rollback()
                raise
                
        self.conn.commit()
        logger.info(f"Inserted {len(analysis_results)} slope analysis results")
        
    def detect_subsidence(self, dem_path_old, dem_path_new, threshold_m=0.1):
        """
        Detect subsidence by comparing two DEMs from different time periods
        """
        logger.info("Detecting subsidence from temporal DEM comparison")
        
        # Process both DEMs
        _, dem_old, transform_old = self.process_dem_file(dem_path_old, sample_spacing=50)
        _, dem_new, transform_new = self.process_dem_file(dem_path_new, sample_spacing=50)
        
        # Calculate elevation difference
        elevation_diff = dem_new - dem_old
        
        # Identify subsidence areas
        subsidence_mask = elevation_diff < -threshold_m
        
        # Find contiguous subsidence regions
        from scipy import ndimage
        labeled_array, num_features = ndimage.label(subsidence_mask)
        
        subsidence_areas = []
        for i in range(1, num_features + 1):
            region_mask = labeled_array == i
            if np.sum(region_mask) > 10:  # Minimum size threshold
                # Get bounding box
                rows, cols = np.where(region_mask)
                min_r, max_r = rows.min(), rows.max()
                min_c, max_c = cols.min(), cols.max()
                
                # Convert to geographic coordinates
                min_lon, max_lat = transform_new * (min_c, min_r)
                max_lon, min_lat = transform_new * (max_c, max_r)
                
                # Calculate statistics
                region_diff = elevation_diff[region_mask]
                
                subsidence_areas.append({
                    'bounds': (min_lon, min_lat, max_lon, max_lat),
                    'avg_subsidence_m': float(np.mean(region_diff)),
                    'max_subsidence_m': float(np.min(region_diff)),
                    'area_m2': float(np.sum(region_mask) * 900)  # Assuming 30m pixels
                })
                
        logger.info(f"Detected {len(subsidence_areas)} subsidence areas")
        return subsidence_areas

def main():
    parser = argparse.ArgumentParser(description='Process DEM data for slope and subsidence analysis')
    parser.add_argument('dem_file', help='Path to DEM file (GeoTIFF format)')
    parser.add_argument('--host', default='localhost', help='Database host')
    parser.add_argument('--port', default=5432, type=int, help='Database port')
    parser.add_argument('--database', default='gms_foundation', help='Database name')
    parser.add_argument('--user', default='gms_user', help='Database user')
    parser.add_argument('--password', required=True, help='Database password')
    parser.add_argument('--sample-spacing', default=100, type=int, 
                       help='Sample spacing for elevation points (pixels)')
    parser.add_argument('--slope-threshold', default=30, type=float,
                       help='Slope threshold in degrees for stability analysis')
    parser.add_argument('--compare-dem', help='Second DEM file for subsidence detection')
    
    args = parser.parse_args()
    
    # Database configuration
    db_config = {
        'host': args.host,
        'port': args.port,
        'database': args.database,
        'user': args.user,
        'password': args.password
    }
    
    # Process DEM data
    processor = DEMProcessor(db_config)
    
    try:
        processor.connect()
        
        # Process primary DEM
        points, dem_data, transform = processor.process_dem_file(
            args.dem_file, args.sample_spacing
        )
        processor.insert_elevation_points(points)
        
        # Calculate and analyze slope
        slope_degrees, aspect_degrees = processor.calculate_slope(dem_data, transform)
        analysis_results = processor.analyze_slope_stability(
            slope_degrees, aspect_degrees, transform, args.slope_threshold
        )
        processor.insert_slope_analysis(analysis_results)
        
        # Subsidence detection if second DEM provided
        if args.compare_dem:
            subsidence_areas = processor.detect_subsidence(args.dem_file, args.compare_dem)
            logger.info(f"Subsidence detection results: {subsidence_areas}")
        
    except Exception as e:
        logger.error(f"Processing failed: {e}")
        raise
    finally:
        processor.disconnect()

if __name__ == "__main__":
    main()