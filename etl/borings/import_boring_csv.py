#!/usr/bin/env python3
"""
Boring Log CSV Import Script
Imports geotechnical boring data from standard CSV format into the GMS database
"""

import csv
import psycopg2
from psycopg2.extras import RealDictCursor
import argparse
import logging
from datetime import datetime
from pathlib import Path
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BoringCSVImporter:
    def __init__(self, db_config):
        """Initialize the CSV importer with database configuration"""
        self.db_config = db_config
        self.conn = None
        self.cursor = None
        self.project_id = None
        
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
            
    def create_or_get_project(self, project_number, project_name=None):
        """Create a new project or get existing project ID"""
        try:
            # Check if project exists
            self.cursor.execute("""
                SELECT id FROM gms.projects WHERE project_number = %s
            """, (project_number,))
            
            result = self.cursor.fetchone()
            
            if result:
                self.project_id = result['id']
                logger.info(f"Using existing project: {project_number}")
            else:
                # Create new project
                self.cursor.execute("""
                    INSERT INTO gms.projects (project_number, name, status, created_at)
                    VALUES (%s, %s, 'active', CURRENT_TIMESTAMP)
                    RETURNING id
                """, (project_number, project_name or f"Project {project_number}"))
                
                result = self.cursor.fetchone()
                self.project_id = result['id']
                self.conn.commit()
                logger.info(f"Created new project: {project_number}")
                
            return self.project_id
            
        except Exception as e:
            logger.error(f"Error creating/getting project: {e}")
            self.conn.rollback()
            raise
            
    def parse_csv_file(self, filepath):
        """
        Parse CSV file with boring data
        Expected DIGGS-compliant CSV format:
        boring_id, latitude, longitude, elevation, date, total_depth, rock_depth, water_depth, depth_intervals, blow_counts, penetration_mm, description
        """
        logger.info(f"Parsing CSV file: {filepath}")
        
        borings = []
        
        with open(filepath, 'r') as csvfile:
            # Skip BOM if present
            first_bytes = csvfile.read(3)
            if first_bytes != '\ufeff':
                csvfile.seek(0)
            
            reader = csv.DictReader(csvfile)
            
            for row_num, row in enumerate(reader, start=2):
                try:
                    boring = {
                        'point_id': row.get('boring_id', '').strip(),
                        'latitude': float(row.get('latitude', 0)),
                        'longitude': float(row.get('longitude', 0)),
                        'elevation_m': float(row.get('elevation', 0)) if row.get('elevation') else None,
                        'investigation_date': row.get('date', '').strip() or None,
                        'total_depth_m': float(row.get('total_depth', 0)) if row.get('total_depth') else None,
                        'rock_depth_m': float(row.get('rock_depth', 0)) if row.get('rock_depth') else None,
                        'groundwater_depth_m': float(row.get('water_depth', 0)) if row.get('water_depth') else None,
                        'description': row.get('description', '').strip()
                    }
                    
                    # Parse DIGGS-compliant SPT data
                    depth_intervals = row.get('depth_intervals', '').strip()
                    blow_counts = row.get('blow_counts', '').strip()
                    penetration_mm = row.get('penetration_mm', '').strip()
                    
                    boring['spt_data'] = []
                    
                    if depth_intervals and blow_counts:
                        depths = [float(x.strip()) for x in depth_intervals.split(',') if x.strip()]
                        blows = blow_counts.split(',')
                        penetrations = penetration_mm.split(',') if penetration_mm else []
                        
                        for i, (depth, blow_string) in enumerate(zip(depths, blows)):
                            blow_string = blow_string.strip()
                            penetration = float(penetrations[i]) if i < len(penetrations) and penetrations[i].strip() else 150.0
                            
                            if '-' in blow_string and not blow_string.endswith('R'):
                                # Parse individual blows (e.g., "6-8-10")
                                individual_blows = [int(x) for x in blow_string.split('-') if x.isdigit()]
                                n_value = sum(individual_blows[-2:]) if len(individual_blows) >= 2 else sum(individual_blows)
                                refusal = False
                            elif blow_string.endswith('R') or blow_string == 'R':
                                # Handle refusal
                                if '-' in blow_string:
                                    individual_blows = [int(x) for x in blow_string.replace('R', '').split('-') if x.isdigit()]
                                else:
                                    individual_blows = []
                                n_value = 50  # Standard refusal value
                                refusal = True
                                penetration = penetration if penetration > 0 else 0
                            else:
                                continue
                                
                            boring['spt_data'].append({
                                'depth_m': depth * 0.3048,  # Convert feet to meters
                                'blow_counts': individual_blows,
                                'n_value': n_value,
                                'penetration_mm': penetration,
                                'refusal': refusal
                            })
                        
                    borings.append(boring)
                    
                except Exception as e:
                    logger.warning(f"Error parsing row {row_num}: {e}")
                    continue
                    
        logger.info(f"Parsed {len(borings)} boring records from CSV")
        return borings
        
    def import_boring(self, boring_data):
        """Import a single boring record into the database"""
        try:
            # Insert boring point
            insert_point_sql = """
                INSERT INTO gms.geotechnical_points (
                    project_id, point_id, location, elevation_m,
                    investigation_date, total_depth_m, groundwater_depth_m,
                    rock_depth_m, data_source, confidence, metadata
                ) VALUES (
                    %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326), %s,
                    %s, %s, %s, %s, 'field_investigation', 'medium',
                    jsonb_build_object('description', %s, 'import_date', %s)
                ) RETURNING id
            """
            
            self.cursor.execute(insert_point_sql, (
                self.project_id,
                boring_data['point_id'],
                boring_data['longitude'],
                boring_data['latitude'],
                boring_data['elevation_m'],
                boring_data['investigation_date'],
                boring_data['total_depth_m'],
                boring_data['groundwater_depth_m'],
                boring_data['rock_depth_m'],
                boring_data['description'],
                datetime.now().isoformat()
            ))
            
            point_result = self.cursor.fetchone()
            point_id = point_result['id']
            
            # Import DIGGS-compliant SPT data if available
            if boring_data.get('spt_data'):
                for spt_record in boring_data['spt_data']:
                    insert_spt_sql = """
                        INSERT INTO gms.spt_results (
                            point_id, depth_m, n_value, blow_counts, refusal,
                            sampler_type, hammer_type, notes
                        ) VALUES (
                            %s, %s, %s, %s, %s, 'Standard Split-Spoon', 
                            '140 lb Hammer', %s
                        )
                    """
                    
                    # Create notes with penetration info
                    notes = f"Penetration: {spt_record['penetration_mm']}mm"
                    if spt_record['refusal']:
                        notes += " (Refusal)"
                        
                    self.cursor.execute(insert_spt_sql, (
                        point_id,
                        spt_record['depth_m'],
                        spt_record['n_value'],
                        spt_record['blow_counts'],
                        spt_record['refusal'],
                        notes
                    ))
                    
            return point_id
            
        except Exception as e:
            logger.error(f"Failed to import boring {boring_data.get('point_id')}: {e}")
            raise
            
    def import_all_borings(self, borings):
        """Import all boring records"""
        imported_count = 0
        failed_count = 0
        
        for boring in borings:
            try:
                self.import_boring(boring)
                imported_count += 1
                
                if imported_count % 10 == 0:
                    self.conn.commit()
                    logger.info(f"Imported {imported_count} borings...")
                    
            except Exception as e:
                logger.error(f"Failed to import boring {boring.get('point_id')}: {e}")
                failed_count += 1
                self.conn.rollback()
                continue
                
        self.conn.commit()
        logger.info(f"Import complete: {imported_count} successful, {failed_count} failed")
        return imported_count, failed_count
        
    def validate_csv_structure(self, filepath):
        """Validate that CSV has required columns for DIGGS compliance"""
        required_columns = ['boring_id', 'latitude', 'longitude']
        recommended_columns = ['depth_intervals', 'blow_counts', 'penetration_mm']
        
        with open(filepath, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            headers = reader.fieldnames
            
            missing_columns = [col for col in required_columns if col not in headers]
            missing_recommended = [col for col in recommended_columns if col not in headers]
            
            if missing_columns:
                logger.error(f"Missing required columns: {missing_columns}")
                logger.error(f"CSV has columns: {headers}")
                return False
                
            if missing_recommended:
                logger.warning(f"Missing recommended DIGGS columns: {missing_recommended}")
                logger.warning("SPT data will not be imported without these columns")
                
            logger.info(f"CSV structure validated. Columns: {headers}")
            return True

def create_sample_csv(filepath):
    """Create a sample DIGGS-compliant CSV file with example boring data"""
    sample_data = [
        ['boring_id', 'latitude', 'longitude', 'elevation', 'date', 'total_depth', 'rock_depth', 'water_depth', 'depth_intervals', 'blow_counts', 'penetration_mm', 'description'],
        ['B-101', '40.051', '-78.512', '1250', '2023-05-15', '45', '32', '12', '2,4,6,8,10,12,14,16', '6-8-10,8-10-12,10-12-15,12-15-18,15-18-22,18-22-25,20-25-30,25-30-R', '150,150,150,150,150,150,150,0', 'Highway boring near MP 110'],
        ['B-102', '40.048', '-78.498', '1245', '2023-05-16', '38', '28', '10', '2,4,6,8,10,12,14,16', '4-6-8,6-8-10,8-10-12,10-12-15,12-15-18,15-18-20,18-20-25,20-25-R', '150,150,150,150,150,150,150,0', 'Bridge approach boring'],
        ['B-103', '40.045', '-78.485', '1255', '2023-05-17', '52', '41', '15', '2,4,6,8,10,12,14,16,18,20', '3-5-6,4-6-8,6-8-10,8-10-12,10-12-14,12-14-16,14-16-18,16-18-20,18-20-24,20-24-R', '150,150,150,150,150,150,150,150,150,0', 'Slope stability investigation']
    ]
    
    with open(filepath, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        for row in sample_data:
            writer.writerow(row)
            
    logger.info(f"Created sample CSV file: {filepath}")

def main():
    parser = argparse.ArgumentParser(description='Import boring data from CSV file')
    parser.add_argument('csv_file', help='Path to CSV file with boring data')
    parser.add_argument('--project-number', required=True, help='Project number for grouping borings')
    parser.add_argument('--project-name', help='Optional project name')
    parser.add_argument('--host', default='localhost', help='Database host')
    parser.add_argument('--port', default=5432, type=int, help='Database port')
    parser.add_argument('--database', default='gms_foundation', help='Database name')
    parser.add_argument('--user', default='gms_user', help='Database user')
    parser.add_argument('--password', required=True, help='Database password')
    parser.add_argument('--create-sample', action='store_true', help='Create a sample CSV file')
    
    args = parser.parse_args()
    
    # Create sample CSV if requested
    if args.create_sample:
        create_sample_csv(args.csv_file)
        logger.info("Sample CSV created. You can now run the import with this file.")
        return
        
    # Check if file exists
    if not Path(args.csv_file).exists():
        logger.error(f"CSV file not found: {args.csv_file}")
        sys.exit(1)
        
    # Database configuration
    db_config = {
        'host': args.host,
        'port': args.port,
        'database': args.database,
        'user': args.user,
        'password': args.password
    }
    
    # Import boring data
    importer = BoringCSVImporter(db_config)
    
    try:
        importer.connect()
        
        # Validate CSV structure
        if not importer.validate_csv_structure(args.csv_file):
            logger.error("CSV validation failed")
            sys.exit(1)
            
        # Create or get project
        importer.create_or_get_project(args.project_number, args.project_name)
        
        # Parse CSV
        borings = importer.parse_csv_file(args.csv_file)
        
        if not borings:
            logger.warning("No valid boring records found in CSV")
            sys.exit(1)
            
        # Import borings
        imported, failed = importer.import_all_borings(borings)
        
        if imported > 0:
            logger.info(f"Successfully imported {imported} borings to project {args.project_number}")
        else:
            logger.error("No borings were imported successfully")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Import failed: {e}")
        sys.exit(1)
    finally:
        importer.disconnect()

if __name__ == "__main__":
    main()