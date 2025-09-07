#!/usr/bin/env python3
import os
import sys
import json
import logging
import datetime
import docker
import psycopg2
from pathlib import Path
from rich.console import Console
from rich.logging import RichHandler
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True)]
)
logger = logging.getLogger("transition-report")

# Load environment variables
load_dotenv()

class TransitionReport:
    def __init__(self):
        self.console = Console()
        self.timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.report_data = {
            "timestamp": self.timestamp,
            "development_status": {},
            "services": {},
            "database": {},
            "ai_components": {}
        }
        
    def check_development_status(self):
        """Check development milestone status"""
        systems = {
            "Context_Management": 0.75,
            "Citation_Tracking": 0.60,
            "Milestone_Infrastructure": 0.30,
            "M0_Processing_Engine": 0.50
        }
        
        self.report_data["development_status"] = {
            "overall_progress": sum(systems.values()) / len(systems) * 100,
            "systems": systems
        }
        
    def check_services(self):
        """Check Docker services status"""
        try:
            client = docker.from_env()
            containers = client.containers.list(all=True)
            
            for container in containers:
                self.report_data["services"][container.name] = {
                    "status": container.status,
                    "health": getattr(container, "health", "N/A"),
                    "image": container.image.tags[0] if container.image.tags else "N/A"
                }
        except Exception as e:
            logger.error(f"Error checking Docker services: {e}")
            
    def check_database(self):
        """Export database schema information"""
        try:
            conn = psycopg2.connect(
                dbname=os.getenv("DB_NAME", "prolaunch"),
                user=os.getenv("DB_USER", "postgres"),
                password=os.getenv("DB_PASSWORD"),
                host=os.getenv("DB_HOST", "localhost")
            )
            
            with conn.cursor() as cur:
                # Get tables
                cur.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                """)
                tables = cur.fetchall()
                
                schema_info = {}
                for table in tables:
                    table_name = table[0]
                    cur.execute(f"""
                        SELECT column_name, data_type 
                        FROM information_schema.columns 
                        WHERE table_name = '{table_name}'
                    """)
                    columns = cur.fetchall()
                    schema_info[table_name] = {
                        "columns": {col[0]: col[1] for col in columns}
                    }
                
                self.report_data["database"]["schema"] = schema_info
                
        except Exception as e:
            logger.error(f"Error checking database: {e}")
            
    def check_ai_components(self):
        """Document AI components and MCP integrations"""
        ai_components = {
            "LlamaIndex": {
                "status": "configured",
                "version": "0.9.x",
                "integration_points": [
                    "Document processing",
                    "Vector storage",
                    "Query pipeline"
                ]
            },
            "MCP_Adapters": {
                "status": "pending",
                "planned_integrations": [
                    "Code analysis",
                    "Natural language processing",
                    "Context management"
                ]
            }
        }
        
        self.report_data["ai_components"] = ai_components
        
    def generate_markdown(self):
        """Generate markdown report"""
        report_path = Path("transition-log.md")
        
        with report_path.open("w", encoding="utf-8") as f:
            f.write(f"# ProLaunch MVP Transition Report\n\n")
            f.write(f"Generated: {self.timestamp}\n\n")
            
            # Development Status
            f.write("## Development Status\n\n")
            overall = self.report_data["development_status"]["overall_progress"]
            f.write(f"Overall Progress: {overall:.1f}%\n\n")
            
            for system, progress in self.report_data["development_status"]["systems"].items():
                f.write(f"- {system.replace('_', ' ')}: {progress*100:.1f}%\n")
            
            # Services
            f.write("\n## Service Status\n\n")
            for service, info in self.report_data["services"].items():
                status_emoji = "✅" if info["status"] == "running" else "❌"
                f.write(f"- {status_emoji} {service}\n")
                f.write(f"  - Status: {info['status']}\n")
                f.write(f"  - Image: {info['image']}\n")
            
            # Database
            f.write("\n## Database Schema\n\n")
            for table, info in self.report_data["database"].get("schema", {}).items():
                f.write(f"### {table}\n\n")
                f.write("| Column | Type |\n|--------|------|\n")
                for column, type_ in info["columns"].items():
                    f.write(f"| {column} | {type_} |\n")
            
            # AI Components
            f.write("\n## AI Components\n\n")
            for component, info in self.report_data["ai_components"].items():
                f.write(f"### {component}\n\n")
                f.write(f"Status: {info['status']}\n\n")
                
                if "version" in info:
                    f.write(f"Version: {info['version']}\n\n")
                    
                if "integration_points" in info:
                    f.write("Integration Points:\n")
                    for point in info["integration_points"]:
                        f.write(f"- {point}\n")
                        
                if "planned_integrations" in info:
                    f.write("\nPlanned Integrations:\n")
                    for integration in info["planned_integrations"]:
                        f.write(f"- {integration}\n")
            
        # Also save JSON data
        with open("transition-log.json", "w") as f:
            json.dump(self.report_data, f, indent=2)
            
        logger.info(f"Report generated: {report_path.absolute()}")

def main():
    try:
        report = TransitionReport()
        report.check_development_status()
        report.check_services()
        report.check_database()
        report.check_ai_components()
        report.generate_markdown()
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()