#!/usr/bin/env python3
import os
import sys
import json
import shutil
import hashlib
import logging
import datetime
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

class BackupManager:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.backup_dir = base_dir / "backups" / f"backup_{self.timestamp}"
        self.logger = self._setup_logger()
        
    def _setup_logger(self) -> logging.Logger:
        logger = logging.getLogger("backup_manager")
        logger.setLevel(logging.INFO)
        
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        
        file_handler = logging.FileHandler(f"backup_{self.timestamp}.log")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        return logger
    
    def _is_git_available(self) -> bool:
        try:
            subprocess.run(
                ["git", "--version"],
                capture_output=True,
                text=True,
                check=True
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
            
    def _run_git_command(self, command: List[str]) -> Optional[subprocess.CompletedProcess]:
        if not self._is_git_available():
            self.logger.warning("Git is not available, skipping git operations")
            return None
            
        try:
            result = subprocess.run(
                command,
                cwd=self.base_dir,
                capture_output=True,
                text=True,
                check=True
            )
            return result
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Git command failed: {e.cmd}")
            self.logger.error(f"Error output: {e.stderr}")
            return None
    
    def commit_changes(self, message: str) -> None:
        if not self._is_git_available():
            return
            
        self.logger.info("Committing changes...")
        try:
            # Stage all changes
            result = self._run_git_command(["git", "add", "."])
            if not result:
                return
                
            # Create commit
            commit_msg = f"""Step 17 Development Milestone

{message}

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"""
            result = self._run_git_command(["git", "commit", "-m", commit_msg])
            if result:
                self.logger.info("Changes committed successfully")
                
        except Exception as e:
            self.logger.error(f"Failed to commit changes: {e}")
            
    def create_git_tag(self, tag: str, message: str) -> None:
        if not self._is_git_available():
            return
            
        self.logger.info(f"Creating git tag: {tag}")
        try:
            result = self._run_git_command(["git", "tag", "-a", tag, "-m", message])
            if result:
                self.logger.info("Git tag created successfully")
        except Exception as e:
            self.logger.error(f"Failed to create git tag: {e}")
            
    def push_to_remote(self) -> None:
        if not self._is_git_available():
            return
            
        self.logger.info("Pushing to remote...")
        try:
            result = self._run_git_command(["git", "push", "origin", "main"])
            if result:
                result = self._run_git_command(["git", "push", "origin", "--tags"])
                if result:
                    self.logger.info("Push to remote completed")
        except Exception as e:
            self.logger.error(f"Failed to push to remote: {e}")
            
    def calculate_file_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of a file"""
        sha256_hash = hashlib.sha256()
        
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
                
        return sha256_hash.hexdigest()
        
    def create_backup_archive(self, dirs_to_backup: List[str]) -> Dict:
        """Create backup archive and return file info"""
        self.logger.info("Creating backup archive...")
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        backup_info = {
            "timestamp": self.timestamp,
            "files": {},
            "checksums": {}
        }
        
        try:
            # Copy directories to backup location
            for dir_name in dirs_to_backup:
                src_dir = self.base_dir / dir_name
                if src_dir.exists():
                    dst_dir = self.backup_dir / dir_name
                    if not dst_dir.parent.exists():
                        dst_dir.parent.mkdir(parents=True)
                    shutil.copytree(src_dir, dst_dir)
                    
                    # Record file info and checksums
                    for file_path in dst_dir.rglob("*"):
                        if file_path.is_file():
                            rel_path = file_path.relative_to(self.backup_dir)
                            backup_info["files"][str(rel_path)] = {
                                "size": file_path.stat().st_size,
                                "modified": datetime.datetime.fromtimestamp(
                                    file_path.stat().st_mtime
                                ).isoformat()
                            }
                            backup_info["checksums"][str(rel_path)] = \
                                self.calculate_file_checksum(file_path)
            
            # Create archive
            archive_name = f"backup_{self.timestamp}.zip"
            backup_root = self.base_dir / "backups"
            backup_root.mkdir(exist_ok=True)
            archive_path = backup_root / archive_name
            
            prev_cwd = os.getcwd()
            os.chdir(self.backup_dir)
            
            shutil.make_archive(
                str(archive_path.with_suffix("")),
                "zip",
                "."
            )
            
            os.chdir(prev_cwd)
            
            backup_info["archive"] = {
                "name": archive_name,
                "size": archive_path.stat().st_size,
                "checksum": self.calculate_file_checksum(archive_path)
            }
            
            # Clean up temporary directory
            shutil.rmtree(self.backup_dir)
            
            self.logger.info(f"Backup archive created: {archive_name}")
            return backup_info
            
        except Exception as e:
            self.logger.error(f"Failed to create backup archive: {e}")
            raise
            
    def generate_backup_report(self, backup_info: Dict) -> None:
        """Generate backup verification report"""
        self.logger.info("Generating backup report...")
        
        backup_root = self.base_dir / "backups"
        backup_root.mkdir(exist_ok=True)
        
        report_path = backup_root / f"backup_report_{self.timestamp}.md"
        json_path = report_path.with_suffix(".json")
        
        # Save JSON report
        with open(json_path, "w") as f:
            json.dump(backup_info, f, indent=2)
            
        # Generate markdown report
        with open(report_path, "w") as f:
            f.write(f"# Backup Verification Report\n\n")
            f.write(f"Generated: {backup_info['timestamp']}\n\n")
            
            f.write("## Archive Information\n\n")
            archive = backup_info["archive"]
            f.write(f"- Name: {archive['name']}\n")
            f.write(f"- Size: {archive['size']} bytes\n")
            f.write(f"- Checksum: {archive['checksum']}\n\n")
            
            f.write("## Backed Up Files\n\n")
            f.write("| File | Size | Modified | Checksum |\n")
            f.write("|------|------|----------|----------|\n")
            
            for file_path, file_info in backup_info["files"].items():
                checksum = backup_info["checksums"][file_path]
                f.write(
                    f"| {file_path} | {file_info['size']} bytes | "
                    f"{file_info['modified']} | {checksum[:8]}... |\n"
                )
                
        self.logger.info(f"Reports generated: {report_path}, {json_path}")
        
def main():
    try:
        base_dir = Path(__file__).parent.parent.parent
        backup_mgr = BackupManager(base_dir)
        
        # Commit changes
        backup_mgr.commit_changes(
            "Development milestone completed:\n"
            "- Context Management System implemented\n"
            "- Citation Tracking System completed\n"
            "- Milestone Infrastructure initialized\n"
            "- M0 Processing Engine development started"
        )
        
        # Create and push tag
        backup_mgr.create_git_tag(
            "v0.17.0",
            "Step 17 Development Milestone\n\n"
            "Major features completed:\n"
            "- Context Management System\n"
            "- Citation Tracking System\n"
            "- Milestone Infrastructure\n"
            "- M0 Processing Engine (initial)"
        )
        
        # Push changes
        backup_mgr.push_to_remote()
        
        # Create backup
        dirs_to_backup = ["ai", "milestones", "prompts"]
        backup_info = backup_mgr.create_backup_archive(dirs_to_backup)
        
        # Generate report
        backup_mgr.generate_backup_report(backup_info)
        
    except Exception as e:
        logging.error(f"Backup failed: {e}")
        sys.exit(1)
        
if __name__ == "__main__":
    main()