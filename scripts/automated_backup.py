#!/usr/bin/env python3
"""
ProLaunch MVP Automated Backup Script
Handles Git operations, archive creation, and verification reporting
"""

import os
import sys
import json
import hashlib
import logging
import tarfile
import zipfile
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import argparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('backup.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BackupManager:
    """Manages automated backup operations for ProLaunch MVP"""
    
    def __init__(self, project_root: Path = None, config_file: str = None):
        # Always use the parent directory of scripts as project root
        if project_root is None:
            script_dir = Path(__file__).parent
            self.project_root = script_dir.parent
        else:
            self.project_root = project_root
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.backup_dir = self.project_root / 'backups'
        self.backup_dir.mkdir(exist_ok=True)
        
        # Load configuration
        self.config = self.load_config(config_file)
        
        # Directories to backup
        self.ai_directories = self.config.get('ai_directories', [
            'backend/src/ai',
            'prolaunch_prompts',
            'prolaunch_prompts/milestones',
            'backend/src/api/routes/prompts.py',
            'backend/src/api/v1/milestones.py',
            'backend/src/models/milestone.py',
            'backend/src/services/milestone_service.py',
            'backend/src/infrastructure/persistence/milestone_persistence.py'
        ])
        
        # Add additional directories if specified
        additional_dirs = self.config.get('additional_directories', [])
        self.ai_directories.extend(additional_dirs)
        
        # Critical files to verify
        self.critical_files = self.config.get('critical_files', [
            '.env.example',
            'docker-compose.yml',
            'Makefile',
            'README.md',
            'CLAUDE.md'
        ])
        
        self.checksums = {}
        self.backup_report = {
            'timestamp': self.timestamp,
            'version': self.config.get('default_version', 'v0.17.0'),
            'files_backed_up': [],
            'checksums': {},
            'git_info': {},
            'archive_info': {},
            'verification': {}
        }

    def load_config(self, config_file: str = None) -> dict:
        """Load configuration from JSON file"""
        if config_file is None:
            config_path = self.project_root / 'scripts' / 'backup_config.json'
        else:
            config_path = Path(config_file)
        
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                logger.info(f"Loaded configuration from {config_path}")
                return config
            except Exception as e:
                logger.warning(f"Failed to load config file: {e}. Using defaults.")
                return {}
        else:
            logger.info("No config file found, using defaults")
            return {}

    def run_command(self, command: List[str], capture_output: bool = True) -> Tuple[bool, str]:
        """Execute shell command and return success status and output"""
        try:
            result = subprocess.run(
                command,
                capture_output=capture_output,
                text=True,
                check=True,
                cwd=self.project_root
            )
            return True, result.stdout if capture_output else ""
        except subprocess.CalledProcessError as e:
            logger.error(f"Command failed: {' '.join(command)}")
            logger.error(f"Error: {e.stderr if hasattr(e, 'stderr') else str(e)}")
            return False, str(e)

    def calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum for a file"""
        sha256_hash = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception as e:
            logger.error(f"Failed to calculate checksum for {file_path}: {e}")
            return ""

    def git_operations(self, version: str = "v0.17.0", message: str = None) -> bool:
        """Perform Git operations: stage, commit, tag, and push"""
        logger.info("Starting Git operations...")
        
        # Check git status
        success, output = self.run_command(["git", "status", "--porcelain"])
        if not success:
            logger.error("Failed to get git status")
            return False
        
        has_changes = bool(output.strip())
        self.backup_report['git_info']['has_changes'] = has_changes
        
        if has_changes:
            # Stage all changes
            logger.info("Staging all changes...")
            success, _ = self.run_command(["git", "add", "-A"])
            if not success:
                logger.error("Failed to stage changes")
                return False
            
            # Commit changes
            commit_message = message or f"Automated backup and version update to {version}"
            logger.info(f"Committing changes: {commit_message}")
            success, _ = self.run_command(["git", "commit", "-m", commit_message])
            if not success:
                logger.error("Failed to commit changes")
                return False
            
            # Get commit hash
            success, commit_hash = self.run_command(["git", "rev-parse", "HEAD"])
            if success:
                self.backup_report['git_info']['commit_hash'] = commit_hash.strip()
        else:
            logger.info("No changes to commit")
        
        # Create annotated tag
        tag_message = f"Release {version} - Automated backup on {self.timestamp}"
        logger.info(f"Creating tag {version}...")
        
        # Check if tag already exists
        success, existing_tags = self.run_command(["git", "tag", "-l", version])
        if existing_tags.strip():
            logger.warning(f"Tag {version} already exists, deleting old tag...")
            self.run_command(["git", "tag", "-d", version])
        
        success, _ = self.run_command(["git", "tag", "-a", version, "-m", tag_message])
        if not success:
            logger.error("Failed to create tag")
            return False
        
        self.backup_report['git_info']['tag'] = version
        self.backup_report['git_info']['tag_message'] = tag_message
        
        # Push changes and tags
        logger.info("Pushing changes to remote...")
        success, _ = self.run_command(["git", "push"])
        if not success:
            logger.warning("Failed to push changes (might not have remote configured)")
        
        logger.info("Pushing tags to remote...")
        success, _ = self.run_command(["git", "push", "--tags"])
        if not success:
            logger.warning("Failed to push tags (might not have remote configured)")
        
        return True

    def create_tar_archive(self) -> Optional[Path]:
        """Create tar.gz archive of AI system directories"""
        archive_name = f"prolaunch_backup_{self.timestamp}.tar.gz"
        archive_path = self.backup_dir / archive_name
        
        logger.info(f"Creating tar archive: {archive_path}")
        
        try:
            with tarfile.open(archive_path, "w:gz") as tar:
                # Add AI directories
                for dir_path in self.ai_directories:
                    full_path = self.project_root / dir_path
                    if full_path.exists():
                        if full_path.is_dir():
                            tar.add(full_path, arcname=dir_path)
                            logger.info(f"Added directory: {dir_path}")
                            # Track all files in directory
                            for file in Path(full_path).rglob('*'):
                                if file.is_file():
                                    rel_path = file.relative_to(self.project_root)
                                    self.backup_report['files_backed_up'].append(str(rel_path))
                                    checksum = self.calculate_checksum(file)
                                    if checksum:
                                        self.checksums[str(rel_path)] = checksum
                        else:
                            tar.add(full_path, arcname=dir_path)
                            logger.info(f"Added file: {dir_path}")
                            self.backup_report['files_backed_up'].append(dir_path)
                            checksum = self.calculate_checksum(full_path)
                            if checksum:
                                self.checksums[dir_path] = checksum
                    else:
                        logger.warning(f"Path not found: {dir_path}")
                
                # Add critical files
                for file_path in self.critical_files:
                    full_path = self.project_root / file_path
                    if full_path.exists():
                        tar.add(full_path, arcname=file_path)
                        logger.info(f"Added critical file: {file_path}")
                        self.backup_report['files_backed_up'].append(file_path)
                        checksum = self.calculate_checksum(full_path)
                        if checksum:
                            self.checksums[file_path] = checksum
            
            self.backup_report['archive_info']['path'] = str(archive_path)
            self.backup_report['archive_info']['size'] = archive_path.stat().st_size
            self.backup_report['archive_info']['type'] = 'tar.gz'
            self.backup_report['checksums'] = self.checksums
            
            return archive_path
            
        except Exception as e:
            logger.error(f"Failed to create tar archive: {e}")
            return None

    def create_zip_archive(self) -> Optional[Path]:
        """Create zip archive as alternative backup format"""
        archive_name = f"prolaunch_backup_{self.timestamp}.zip"
        archive_path = self.backup_dir / archive_name
        
        logger.info(f"Creating zip archive: {archive_path}")
        
        try:
            with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Add AI directories
                for dir_path in self.ai_directories:
                    full_path = self.project_root / dir_path
                    if full_path.exists():
                        if full_path.is_dir():
                            for file in Path(full_path).rglob('*'):
                                if file.is_file():
                                    rel_path = file.relative_to(self.project_root)
                                    zipf.write(file, arcname=str(rel_path))
                        else:
                            zipf.write(full_path, arcname=dir_path)
                
                # Add critical files
                for file_path in self.critical_files:
                    full_path = self.project_root / file_path
                    if full_path.exists():
                        zipf.write(full_path, arcname=file_path)
            
            return archive_path
            
        except Exception as e:
            logger.error(f"Failed to create zip archive: {e}")
            return None

    def verify_archive(self, archive_path: Path) -> bool:
        """Verify archive integrity"""
        logger.info(f"Verifying archive: {archive_path}")
        
        try:
            if archive_path.suffix == '.gz':
                with tarfile.open(archive_path, "r:gz") as tar:
                    members = tar.getmembers()
                    self.backup_report['verification']['total_files'] = len(members)
                    self.backup_report['verification']['verified'] = True
                    
                    # Test extraction (without actually extracting)
                    for member in members:
                        try:
                            tar.extractfile(member)
                        except Exception as e:
                            logger.error(f"Failed to verify member {member.name}: {e}")
                            self.backup_report['verification']['verified'] = False
                            return False
                            
            elif archive_path.suffix == '.zip':
                with zipfile.ZipFile(archive_path, 'r') as zipf:
                    result = zipf.testzip()
                    if result is not None:
                        logger.error(f"Archive verification failed for: {result}")
                        self.backup_report['verification']['verified'] = False
                        return False
                    self.backup_report['verification']['total_files'] = len(zipf.namelist())
                    self.backup_report['verification']['verified'] = True
            
            # Calculate archive checksum
            archive_checksum = self.calculate_checksum(archive_path)
            self.backup_report['archive_info']['checksum'] = archive_checksum
            
            logger.info("Archive verification successful")
            return True
            
        except Exception as e:
            logger.error(f"Archive verification failed: {e}")
            self.backup_report['verification']['verified'] = False
            self.backup_report['verification']['error'] = str(e)
            return False

    def generate_report(self) -> None:
        """Generate and save backup report"""
        report_path = self.backup_dir / f"backup_report_{self.timestamp}.json"
        
        # Add summary statistics
        self.backup_report['summary'] = {
            'total_files_backed_up': len(self.backup_report['files_backed_up']),
            'total_checksums_calculated': len(self.checksums),
            'backup_successful': self.backup_report['verification'].get('verified', False)
        }
        
        # Save JSON report
        with open(report_path, 'w') as f:
            json.dump(self.backup_report, f, indent=2)
        
        logger.info(f"Backup report saved to: {report_path}")
        
        # Generate human-readable report
        readable_report_path = self.backup_dir / f"backup_report_{self.timestamp}.txt"
        with open(readable_report_path, 'w') as f:
            f.write("=" * 80 + "\n")
            f.write(f"PROLAUNCH MVP BACKUP REPORT\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n")
            f.write(f"Version: {self.backup_report['version']}\n")
            f.write("=" * 80 + "\n\n")
            
            f.write("GIT INFORMATION:\n")
            f.write("-" * 40 + "\n")
            for key, value in self.backup_report['git_info'].items():
                f.write(f"  {key}: {value}\n")
            f.write("\n")
            
            f.write("ARCHIVE INFORMATION:\n")
            f.write("-" * 40 + "\n")
            for key, value in self.backup_report['archive_info'].items():
                if key == 'size':
                    f.write(f"  {key}: {value:,} bytes\n")
                else:
                    f.write(f"  {key}: {value}\n")
            f.write("\n")
            
            f.write("VERIFICATION RESULTS:\n")
            f.write("-" * 40 + "\n")
            for key, value in self.backup_report['verification'].items():
                f.write(f"  {key}: {value}\n")
            f.write("\n")
            
            f.write("FILES BACKED UP:\n")
            f.write("-" * 40 + "\n")
            for file_path in sorted(self.backup_report['files_backed_up'][:20]):
                f.write(f"  - {file_path}\n")
            if len(self.backup_report['files_backed_up']) > 20:
                f.write(f"  ... and {len(self.backup_report['files_backed_up']) - 20} more files\n")
            f.write("\n")
            
            f.write("SAMPLE CHECKSUMS (first 5):\n")
            f.write("-" * 40 + "\n")
            for i, (file_path, checksum) in enumerate(list(self.checksums.items())[:5]):
                f.write(f"  {file_path}:\n")
                f.write(f"    {checksum}\n")
            f.write("\n")
            
            f.write("=" * 80 + "\n")
            f.write(f"Backup completed successfully: {self.backup_report['summary']['backup_successful']}\n")
            f.write(f"Total files backed up: {self.backup_report['summary']['total_files_backed_up']}\n")
            f.write("=" * 80 + "\n")
        
        logger.info(f"Human-readable report saved to: {readable_report_path}")
        
        # Print summary to console
        print("\n" + "=" * 80)
        print("BACKUP SUMMARY")
        print("=" * 80)
        print(f"Version: {self.backup_report['version']}")
        print(f"Timestamp: {self.timestamp}")
        print(f"Files backed up: {self.backup_report['summary']['total_files_backed_up']}")
        print(f"Archive created: {self.backup_report['archive_info'].get('path', 'N/A')}")
        print(f"Archive size: {self.backup_report['archive_info'].get('size', 0):,} bytes")
        print(f"Verification: {'PASSED' if self.backup_report['summary']['backup_successful'] else 'FAILED'}")
        print("=" * 80 + "\n")

    def run_backup(self, skip_git: bool = False, archive_format: str = 'tar') -> bool:
        """Execute complete backup process"""
        logger.info("Starting ProLaunch MVP backup process...")
        
        try:
            # Step 1: Git operations
            if not skip_git:
                if not self.git_operations():
                    logger.error("Git operations failed")
                    return False
            else:
                logger.info("Skipping Git operations as requested")
            
            # Step 2: Create archive
            if archive_format == 'tar':
                archive_path = self.create_tar_archive()
            elif archive_format == 'zip':
                archive_path = self.create_zip_archive()
            else:
                logger.error(f"Unknown archive format: {archive_format}")
                return False
            
            if not archive_path:
                logger.error("Failed to create archive")
                return False
            
            # Step 3: Verify archive
            if not self.verify_archive(archive_path):
                logger.error("Archive verification failed")
                return False
            
            # Step 4: Generate report
            self.generate_report()
            
            logger.info("Backup completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Backup failed with error: {e}")
            return False

def main():
    """Main entry point for the backup script"""
    parser = argparse.ArgumentParser(description='ProLaunch MVP Automated Backup Tool')
    parser.add_argument('--skip-git', action='store_true', 
                       help='Skip Git operations (useful for testing)')
    parser.add_argument('--format', choices=['tar', 'zip'], default='tar',
                       help='Archive format (default: tar)')
    parser.add_argument('--version', default=None,
                       help='Version tag to create (default: from config or v0.17.0)')
    parser.add_argument('--message', help='Custom commit message')
    parser.add_argument('--config', help='Path to custom configuration file')
    
    args = parser.parse_args()
    
    # Initialize backup manager
    backup_manager = BackupManager(config_file=args.config)
    
    # Override version if specified
    if args.version:
        backup_manager.backup_report['version'] = args.version
    
    # Run backup
    success = backup_manager.run_backup(
        skip_git=args.skip_git,
        archive_format=args.format
    )
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()