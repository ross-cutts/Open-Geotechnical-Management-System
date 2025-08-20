#!/usr/bin/env python3
"""
ARAN Data Processing Script
Processes Automated Road Analyzer data and correlates with subsurface conditions
"""

import json
import psycopg2
from psycopg2.extras import RealDictCursor
import numpy as np
from datetime import datetime
import logging
import argparse
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ARANProcessor:
    def __init__(self, db_config):
        """Initialize ARAN processor with database configuration"""
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
            
    def parse_aran_file(self, filepath):
        """
        Parse ARAN data file (simplified example - adapt to actual format)
        Expected format: JSON with surface distress measurements
        """
        logger.info(f"Parsing ARAN file: {filepath}")
        
        with open(filepath, 'r') as f:
            data = json.load(f)
            
        processed_records = []
        
        for record in data['observations']:
            processed = {
                'survey_id': record.get('survey_id'),
                'route_id': record.get('route_id'),
                'start_lat': record['start_point']['lat'],
                'start_lon': record['start_point']['lon'],
                'end_lat': record['end_point']['lat'],
                'end_lon': record['end_point']['lon'],
                'distress_type': record.get('distress_type'),
                'severity': record.get('severity', 'medium').lower(),
                'rut_depth_mm': record.get('rut_depth_mm'),
                'iri_value': record.get('iri_value'),
                'observation_date': record.get('date', datetime.now().date().isoformat()),
                'metadata': json.dumps(record.get('metadata', {}))
            }
            processed_records.append(processed)
            
        logger.info(f"Processed {len(processed_records)} ARAN records")
        return processed_records
        
    def insert_surface_observations(self, records):
        """Insert processed ARAN records into database"""
        insert_sql = """
        INSERT INTO gms.surface_observations (
            survey_id, route_id, start_point, end_point, observation_line,
            distress_type, severity, rut_depth_mm, iri_value,
            observation_date, data_source, metadata
        ) VALUES (
            %(survey_id)s, %(route_id)s,
            ST_SetSRID(ST_MakePoint(%(start_lon)s, %(start_lat)s), 4326),
            ST_SetSRID(ST_MakePoint(%(end_lon)s, %(end_lat)s), 4326),
            ST_SetSRID(ST_MakeLine(
                ST_MakePoint(%(start_lon)s, %(start_lat)s),
                ST_MakePoint(%(end_lon)s, %(end_lat)s)
            ), 4326),
            %(distress_type)s, %(severity)s::gms.distress_severity,
            %(rut_depth_mm)s, %(iri_value)s, %(observation_date)s,
            'aran_survey', %(metadata)s::jsonb
        ) RETURNING id;
        """
        
        inserted_ids = []
        for record in records:
            try:
                self.cursor.execute(insert_sql, record)
                result = self.cursor.fetchone()
                inserted_ids.append(result['id'])
            except Exception as e:
                logger.error(f"Failed to insert record: {e}")
                self.conn.rollback()
                raise
                
        self.conn.commit()
        logger.info(f"Inserted {len(inserted_ids)} surface observations")
        return inserted_ids
        
    def correlate_with_subsurface(self, observation_ids, correlation_distance=50):
        """
        Find and store correlations between surface observations and nearby borings
        """
        correlation_sql = """
        INSERT INTO gms.data_correlations (
            source_table, source_id, target_table, target_id,
            correlation_type, distance_m, correlation_score
        )
        SELECT 
            'surface_observations' as source_table,
            so.id as source_id,
            'geotechnical_points' as target_table,
            gp.id as target_id,
            'proximity' as correlation_type,
            ST_Distance(so.observation_line::geography, gp.location::geography) as distance_m,
            CASE 
                WHEN ST_Distance(so.observation_line::geography, gp.location::geography) < 10 THEN 1.0
                WHEN ST_Distance(so.observation_line::geography, gp.location::geography) < 25 THEN 0.8
                WHEN ST_Distance(so.observation_line::geography, gp.location::geography) < 50 THEN 0.6
                ELSE 0.4
            END as correlation_score
        FROM gms.surface_observations so
        CROSS JOIN LATERAL (
            SELECT * FROM gms.geotechnical_points gp
            WHERE ST_DWithin(so.observation_line::geography, gp.location::geography, %s)
            ORDER BY ST_Distance(so.observation_line::geography, gp.location::geography)
            LIMIT 5
        ) gp
        WHERE so.id = ANY(%s)
        ON CONFLICT (source_table, source_id, target_table, target_id) 
        DO UPDATE SET 
            distance_m = EXCLUDED.distance_m,
            correlation_score = EXCLUDED.correlation_score;
        """
        
        self.cursor.execute(correlation_sql, (correlation_distance, observation_ids))
        correlations_count = self.cursor.rowcount
        self.conn.commit()
        
        logger.info(f"Created {correlations_count} correlations with subsurface data")
        
    def analyze_distress_patterns(self):
        """
        Analyze patterns between surface distress and subsurface conditions
        """
        analysis_sql = """
        WITH correlated_data AS (
            SELECT 
                so.distress_type,
                so.severity,
                so.rut_depth_mm,
                AVG(spt.n_value) as avg_n_value,
                COUNT(DISTINCT gp.id) as boring_count,
                AVG(dc.distance_m) as avg_distance_m
            FROM gms.surface_observations so
            JOIN gms.data_correlations dc 
                ON dc.source_table = 'surface_observations' 
                AND dc.source_id = so.id
            JOIN gms.geotechnical_points gp 
                ON dc.target_table = 'geotechnical_points' 
                AND dc.target_id = gp.id
            LEFT JOIN gms.spt_results spt ON spt.point_id = gp.id
            WHERE spt.depth_m <= 3.0  -- Focus on near-surface conditions
            GROUP BY so.distress_type, so.severity, so.rut_depth_mm
        )
        SELECT 
            distress_type,
            severity,
            avg_n_value,
            boring_count,
            CASE 
                WHEN avg_n_value < 5 THEN 'Very Soft/Loose'
                WHEN avg_n_value < 10 THEN 'Soft/Loose'
                WHEN avg_n_value < 30 THEN 'Medium'
                WHEN avg_n_value < 50 THEN 'Dense/Stiff'
                ELSE 'Very Dense/Hard'
            END as soil_condition,
            avg_distance_m
        FROM correlated_data
        WHERE boring_count >= 3
        ORDER BY distress_type, severity;
        """
        
        self.cursor.execute(analysis_sql)
        results = self.cursor.fetchall()
        
        logger.info("\nDistress-Subsurface Correlation Analysis:")
        logger.info("-" * 80)
        for row in results:
            logger.info(
                f"Distress: {row['distress_type']} ({row['severity']}) | "
                f"Avg N-Value: {row['avg_n_value']:.1f} | "
                f"Soil: {row['soil_condition']} | "
                f"Samples: {row['boring_count']}"
            )
            
        return results

def main():
    parser = argparse.ArgumentParser(description='Process ARAN surface distress data')
    parser.add_argument('input_file', help='Path to ARAN data file (JSON format)')
    parser.add_argument('--host', default='localhost', help='Database host')
    parser.add_argument('--port', default=5432, type=int, help='Database port')
    parser.add_argument('--database', default='gms_foundation', help='Database name')
    parser.add_argument('--user', default='gms_user', help='Database user')
    parser.add_argument('--password', required=True, help='Database password')
    parser.add_argument('--correlation-distance', default=50, type=int, 
                       help='Maximum distance (m) for correlation analysis')
    
    args = parser.parse_args()
    
    # Database configuration
    db_config = {
        'host': args.host,
        'port': args.port,
        'database': args.database,
        'user': args.user,
        'password': args.password
    }
    
    # Process ARAN data
    processor = ARANProcessor(db_config)
    
    try:
        processor.connect()
        
        # Parse and insert ARAN data
        records = processor.parse_aran_file(args.input_file)
        observation_ids = processor.insert_surface_observations(records)
        
        # Correlate with subsurface data
        processor.correlate_with_subsurface(observation_ids, args.correlation_distance)
        
        # Analyze patterns
        processor.analyze_distress_patterns()
        
    except Exception as e:
        logger.error(f"Processing failed: {e}")
        raise
    finally:
        processor.disconnect()

if __name__ == "__main__":
    main()