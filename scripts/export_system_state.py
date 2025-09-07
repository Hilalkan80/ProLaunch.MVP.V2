#!/usr/bin/env python3
import os
import sys
import json
import shutil
import hashlib
import logging
import datetime
import argparse
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv

class SystemStateExporter:
    def __init__(self, base_dir: Path, verbose: bool = False, compress: bool = True):
        self.base_dir = base_dir
        self.timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.export_dir = base_dir / "exports" / f"system_state_{self.timestamp}"
        self.verbose = verbose
        self.compress = compress
        self.logger = self._setup_logger()
        self.manifest = {
            "timestamp": self.timestamp,
            "components": {},
            "warnings": [],
            "errors": []
        }
        
    def _setup_logger(self) -> logging.Logger:
        logger = logging.getLogger("system_state_exporter")
        level = logging.DEBUG if self.verbose else logging.INFO
        logger.setLevel(level)
        
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s"
        )
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # File handler
        self.export_dir.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(
            self.export_dir.parent / f"export_{self.timestamp}.log",
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        return logger
        
    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of a file"""
        sha256_hash = hashlib.sha256()
        
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
                
        return sha256_hash.hexdigest()
        
    def _copy_with_manifest(
        self, 
        src: Path, 
        dst: Path, 
        manifest: Dict
    ) -> None:
        """Copy a file/directory and record info in manifest"""
        try:
            if not "files" in manifest:
                manifest["files"] = {}
            if not "directories" in manifest:
                manifest["directories"] = {}
                
            if src.is_file():
                if not dst.parent.exists():
                    dst.parent.mkdir(parents=True)
                shutil.copy2(src, dst)
                manifest["files"][str(src.relative_to(self.base_dir))] = {
                    "size": dst.stat().st_size,
                    "checksum": self._calculate_checksum(dst),
                    "modified": datetime.datetime.fromtimestamp(
                        dst.stat().st_mtime
                    ).isoformat()
                }
            elif src.is_dir():
                shutil.copytree(src, dst, dirs_exist_ok=True)
                manifest["directories"][str(src.relative_to(self.base_dir))] = {
                    "file_count": sum(1 for _ in dst.rglob("*") if _.is_file()),
                    "total_size": sum(_.stat().st_size for _ in dst.rglob("*") if _.is_file())
                }
        except FileNotFoundError:
            msg = f"Optional file/directory not found: {src}"
            self.logger.warning(msg)
            self.manifest["warnings"].append(msg)
        except Exception as e:
            msg = f"Error copying {src}: {str(e)}"
            self.logger.error(msg)
            self.manifest["errors"].append(msg)
            
    def export_ai_system(self) -> None:
        """Export AI system files and configurations"""
        self.logger.info("Exporting AI system...")
        
        ai_export_dir = self.export_dir / "ai_system"
        ai_manifest = {
            "files": {},
            "directories": {},
            "models": {},
            "embeddings": {}
        }
        
        # AI directories to export
        ai_dirs = {
            "configurations": self.base_dir / "ai" / "configs",
            "model_weights": self.base_dir / "ai" / "models",
            "embeddings": self.base_dir / "ai" / "embeddings",
            "training_data": self.base_dir / "ai" / "training",
            "cache": self.base_dir / "ai" / "cache",
            "state_files": self.base_dir / "ai" / "state",
            "llamaindex": self.base_dir / "ai" / "llamaindex"
        }
        
        for name, src_dir in ai_dirs.items():
            dst_dir = ai_export_dir / name
            self._copy_with_manifest(src_dir, dst_dir, ai_manifest)
            
        # Save manifest
        ai_export_dir.mkdir(parents=True, exist_ok=True)
        with open(ai_export_dir / "ai_manifest.json", "w", encoding='utf-8') as f:
            json.dump(ai_manifest, f, indent=2)
            
        self.manifest["components"]["ai_system"] = ai_manifest
        self.logger.info("AI system export completed")
        
    def export_database(self) -> None:
        """Export database schema and AI-related data"""
        self.logger.info("Exporting database...")
        
        db_export_dir = self.export_dir / "database"
        db_export_dir.mkdir(parents=True, exist_ok=True)
        
        db_manifest = {
            "tables": {},
            "views": {},
            "functions": {}
        }
        
        try:
            # Load database configuration
            load_dotenv()
            conn = psycopg2.connect(
                dbname=os.getenv("DB_NAME", "prolaunch"),
                user=os.getenv("DB_USER", "postgres"),
                password=os.getenv("DB_PASSWORD"),
                host=os.getenv("DB_HOST", "localhost")
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            
            with conn.cursor() as cur:
                # Export schema
                cur.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                    AND table_type = 'BASE TABLE'
                """)
                tables = cur.fetchall()
                
                for table in tables:
                    table_name = table[0]
                    
                    # Get table schema
                    cur.execute(f"""
                        SELECT column_name, data_type, is_nullable
                        FROM information_schema.columns
                        WHERE table_name = '{table_name}'
                    """)
                    columns = cur.fetchall()
                    
                    db_manifest["tables"][table_name] = {
                        "columns": [
                            {
                                "name": col[0],
                                "type": col[1],
                                "nullable": col[2]
                            }
                            for col in columns
                        ]
                    }
                    
                    # Export table data for AI-related tables
                    if any(ai_term in table_name.lower() 
                          for ai_term in ["ai", "model", "embedding", "vector"]):
                        output_file = db_export_dir / f"{table_name}.sql"
                        with open(output_file, "w", encoding='utf-8') as f:
                            cur.copy_expert(
                                f"COPY {table_name} TO STDOUT WITH CSV HEADER",
                                f
                            )
                        
                        db_manifest["tables"][table_name]["exported"] = True
                        db_manifest["tables"][table_name]["row_count"] = \
                            sum(1 for _ in open(output_file)) - 1  # Subtract header
                            
        except Exception as e:
            msg = f"Database export error: {str(e)}"
            self.logger.error(msg)
            self.manifest["errors"].append(msg)
        finally:
            if 'conn' in locals():
                conn.close()
                
        # Save manifest
        with open(db_export_dir / "db_manifest.json", "w", encoding='utf-8') as f:
            json.dump(db_manifest, f, indent=2)
            
        self.manifest["components"]["database"] = db_manifest
        self.logger.info("Database export completed")
        
    def export_mcp_config(self) -> None:
        """Export MCP server configuration"""
        self.logger.info("Exporting MCP configuration...")
        
        mcp_export_dir = self.export_dir / "mcp_integration"
        mcp_export_dir.mkdir(parents=True, exist_ok=True)
        
        mcp_manifest = {
            "files": {},
            "directories": {},
            "configurations": {}
        }
        
        # MCP directories to export
        mcp_dirs = {
            "server_configs": self.base_dir / "mcp" / "configs",
            "api_configs": self.base_dir / "mcp" / "api",
            "adapters": self.base_dir / "mcp" / "adapters",
            "integration_status": self.base_dir / "mcp" / "status"
        }
        
        for name, src_dir in mcp_dirs.items():
            dst_dir = mcp_export_dir / name
            self._copy_with_manifest(src_dir, dst_dir, mcp_manifest)
            
        # Export VS Code MCP settings
        vscode_settings = self.base_dir / ".vscode" / "settings.json"
        if vscode_settings.exists():
            with open(vscode_settings, encoding='utf-8') as f:
                settings = json.load(f)
                mcp_settings = {
                    k: v for k, v in settings.items() 
                    if k.startswith("mcp.") or k.startswith("ide.")
                }
                
            with open(mcp_export_dir / "vscode_mcp_settings.json", "w", encoding='utf-8') as f:
                json.dump(mcp_settings, f, indent=2)
                
        # Save manifest
        with open(mcp_export_dir / "mcp_manifest.json", "w", encoding='utf-8') as f:
            json.dump(mcp_manifest, f, indent=2)
            
        self.manifest["components"]["mcp_integration"] = mcp_manifest
        self.logger.info("MCP configuration export completed")
        
    def create_critical_files_checklist(self) -> None:
        """Create checklist of critical files for manual backup"""
        self.logger.info("Creating critical files checklist...")
        
        checklist_dir = self.export_dir / "critical_files"
        checklist_dir.mkdir(parents=True, exist_ok=True)
        
        checklist_manifest = {
            "manual_items": [],
            "automated_items": [],
            "security_items": []
        }
        
        # Define critical file categories
        critical_files = {
            "environment": [
                ".env",
                ".env.local",
                ".env.production"
            ],
            "docker": [
                "docker-compose.yml",
                "docker-compose.override.yml",
                "Dockerfile"
            ],
            "configuration": [
                "CLAUDE.md",
                "package.json",
                "requirements.txt"
            ],
            "security": [
                "security/certificates/",
                "security/keys/"
            ]
        }
        
        # Export automated items
        for category, files in critical_files.items():
            category_dir = checklist_dir / category
            category_dir.mkdir(parents=True, exist_ok=True)
            
            for file_path in files:
                src = self.base_dir / file_path
                if src.exists():
                    dst = category_dir / src.name
                    self._copy_with_manifest(src, dst, checklist_manifest)
                    checklist_manifest["automated_items"].append(str(file_path))
                else:
                    checklist_manifest["manual_items"].append(str(file_path))
                    
        # Generate manual backup checklist
        manual_checklist = [
            "# Critical Files Manual Backup Checklist\n",
            "\nThe following items require manual backup:\n"
        ]
        
        for item in checklist_manifest["manual_items"]:
            manual_checklist.append(f"- [ ] {item}")
            
        with open(checklist_dir / "manual_backup_checklist.txt", "w", encoding='utf-8') as f:
            f.write("\n".join(manual_checklist))
            
        # Save manifest
        with open(checklist_dir / "critical_manifest.json", "w", encoding='utf-8') as f:
            json.dump(checklist_manifest, f, indent=2)
            
        self.manifest["components"]["critical_files"] = checklist_manifest
        self.logger.info("Critical files checklist created")
        
    def generate_verification_report(self) -> None:
        """Generate verification report"""
        self.logger.info("Generating verification report...")
        
        verification = {
            "timestamp": self.timestamp,
            "components": {},
            "statistics": {
                "total_files": 0,
                "total_size": 0,
                "automated_items": 0,
                "manual_items": 0,
                "warnings": len(self.manifest["warnings"]),
                "errors": len(self.manifest["errors"])
            }
        }
        
        # Verify each component
        for component, data in self.manifest["components"].items():
            verification["components"][component] = {
                "status": "error" if any(
                    err.startswith(f"{component}:") 
                    for err in self.manifest["errors"]
                ) else "warning" if any(
                    warn.startswith(f"{component}:")
                    for warn in self.manifest["warnings"]
                ) else "success",
                "files": len(data.get("files", {})),
                "directories": len(data.get("directories", {})),
                "total_size": sum(
                    f.get("size", 0) 
                    for f in data.get("files", {}).values()
                ) + sum(
                    d.get("total_size", 0) 
                    for d in data.get("directories", {}).values()
                )
            }
            
            # Update statistics
            verification["statistics"]["total_files"] += \
                verification["components"][component]["files"]
            verification["statistics"]["total_size"] += \
                verification["components"][component]["total_size"]
                
        if "critical_files" in self.manifest["components"]:
            verification["statistics"]["automated_items"] = len(
                self.manifest["components"]["critical_files"]["automated_items"]
            )
            verification["statistics"]["manual_items"] = len(
                self.manifest["components"]["critical_files"]["manual_items"]
            )
            
        # Generate reports
        with open(self.export_dir / "verification_report.json", "w", encoding='utf-8') as f:
            json.dump(verification, f, indent=2)
            
        with open(self.export_dir / "export_summary.json", "w", encoding='utf-8') as f:
            json.dump(self.manifest, f, indent=2)
            
        # Generate README
        readme = [
            "# System State Export\n",
            f"\nGenerated: {self.timestamp}\n",
            "\n## Components\n"
        ]
        
        for component, status in verification["components"].items():
            status_text = "(Success)" if status["status"] == "success" else \
                         "(Warning)" if status["status"] == "warning" else "(Error)"
            readme.append(
                f"\n### {component} {status_text}\n\n"
                f"- Files: {status['files']}\n"
                f"- Directories: {status['directories']}\n"
                f"- Total Size: {status['total_size']} bytes\n"
            )
            
        readme.extend([
            "\n## Statistics\n\n",
            f"- Total Files: {verification['statistics']['total_files']}\n",
            f"- Total Size: {verification['statistics']['total_size']} bytes\n",
            f"- Automated Items: {verification['statistics']['automated_items']}\n",
            f"- Manual Items: {verification['statistics']['manual_items']}\n",
            f"- Warnings: {verification['statistics']['warnings']}\n",
            f"- Errors: {verification['statistics']['errors']}\n"
        ])
        
        with open(self.export_dir / "README.md", "w", encoding='utf-8') as f:
            f.write("".join(readme))
            
        self.logger.info("Verification report generated")
        
    def create_archive(self) -> None:
        """Create compressed archive of export"""
        if not self.compress:
            return
            
        self.logger.info("Creating archive...")
        
        archive_name = f"prolaunch_system_state_{self.timestamp}"
        archive_path = self.export_dir.parent / f"{archive_name}.zip"
        
        try:
            prev_cwd = os.getcwd()
            os.chdir(self.export_dir)
            
            shutil.make_archive(
                str(archive_path.with_suffix("")),
                "zip",
                "."
            )
            
            os.chdir(prev_cwd)
            
            # Verify archive
            if archive_path.exists():
                self.logger.info(f"Archive created: {archive_path}")
            else:
                raise Exception("Archive file not found after creation")
                
        except Exception as e:
            msg = f"Failed to create archive: {str(e)}"
            self.logger.error(msg)
            self.manifest["errors"].append(msg)
            
    def export(self) -> None:
        """Run full system state export"""
        try:
            # Create export directory
            self.export_dir.mkdir(parents=True, exist_ok=True)
            
            # Export components
            self.export_ai_system()
            self.export_database()
            self.export_mcp_config()
            self.create_critical_files_checklist()
            
            # Generate reports
            self.generate_verification_report()
            
            # Create archive
            self.create_archive()
            
            status = "completed with errors" if self.manifest["errors"] else \
                     "completed with warnings" if self.manifest["warnings"] else \
                     "completed successfully"
            self.logger.info(f"System state export {status}")
            
        except Exception as e:
            self.logger.error(f"Export failed: {str(e)}")
            raise
            
def main():
    parser = argparse.ArgumentParser(
        description="Export ProLaunch MVP system state"
    )
    parser.add_argument(
        "--base-dir",
        type=Path,
        default=Path(__file__).parent.parent,
        help="Base directory of the project"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--no-compress",
        action="store_true",
        help="Skip creating compressed archive"
    )
    
    args = parser.parse_args()
    
    try:
        exporter = SystemStateExporter(
            args.base_dir,
            verbose=args.verbose,
            compress=not args.no_compress
        )
        exporter.export()
    except Exception as e:
        logging.error(f"Export failed: {e}")
        sys.exit(1)
        
if __name__ == "__main__":
    main()