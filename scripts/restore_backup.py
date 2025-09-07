#!/usr/bin/env python3
"""
ProLaunch MVP Backup Restoration Script
Restores files from backup archives with verification
"""

import os
import sys
import json
import tarfile
import zipfile
import hashlib
import argparse
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BackupRestorer:
    """Manages backup restoration for ProLaunch MVP"""
    
    def __init__(self, project_root: Path = None):
        if project_root is None:
            script_dir = Path(__file__).parent
            self.project_root = script_dir.parent
        else:
            self.project_root = project_root
        
        self.backup_dir = self.project_root / 'backups'
        self.restore_dir = self.project_root / 'restored'
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    def list_backups(self) -> list:
        """List available backup files"""
        backups = []
        
        if not self.backup_dir.exists():
            logger.error(f"Backup directory not found: {self.backup_dir}")
            return backups
        
        # Find all backup archives
        for file in self.backup_dir.iterdir():
            if file.is_file() and file.name.startswith('prolaunch_backup_'):
                if file.suffix in ['.gz', '.zip']:
                    # Try to find corresponding report
                    report_name = file.name.replace('prolaunch_backup_', 'backup_report_')
                    report_name = report_name.replace('.tar.gz', '.json').replace('.zip', '.json')
                    report_path = self.backup_dir / report_name
                    
                    backup_info = {
                        'archive': file,
                        'size': file.stat().st_size,
                        'modified': datetime.fromtimestamp(file.stat().st_mtime),
                        'report': report_path if report_path.exists() else None
                    }
                    
                    # Load report info if available
                    if backup_info['report']:
                        try:
                            with open(backup_info['report'], 'r') as f:
                                report = json.load(f)
                                backup_info['version'] = report.get('version', 'Unknown')
                                backup_info['files_count'] = report['summary']['total_files_backed_up']
                                backup_info['verified'] = report['summary']['backup_successful']
                        except Exception as e:
                            logger.warning(f"Failed to load report for {file.name}: {e}")
                    
                    backups.append(backup_info)
        
        # Sort by modified time (newest first)
        backups.sort(key=lambda x: x['modified'], reverse=True)
        return backups
    
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
    
    def extract_archive(self, archive_path: Path, destination: Path = None, 
                       verify_checksums: bool = True) -> bool:
        """Extract backup archive to destination"""
        if destination is None:
            destination = self.restore_dir / f"restore_{self.timestamp}"
        
        destination.mkdir(parents=True, exist_ok=True)
        logger.info(f"Extracting to: {destination}")
        
        try:
            if archive_path.suffix == '.gz':
                with tarfile.open(archive_path, "r:gz") as tar:
                    # Extract all files
                    tar.extractall(path=destination)
                    members = tar.getmembers()
                    logger.info(f"Extracted {len(members)} files/directories")
                    
            elif archive_path.suffix == '.zip':
                with zipfile.ZipFile(archive_path, 'r') as zipf:
                    # Extract all files
                    zipf.extractall(path=destination)
                    members = zipf.namelist()
                    logger.info(f"Extracted {len(members)} files/directories")
            else:
                logger.error(f"Unsupported archive format: {archive_path.suffix}")
                return False
            
            # Verify checksums if report exists
            if verify_checksums:
                report_name = archive_path.name.replace('prolaunch_backup_', 'backup_report_')
                report_name = report_name.replace('.tar.gz', '.json').replace('.zip', '.json')
                report_path = archive_path.parent / report_name
                
                if report_path.exists():
                    logger.info("Verifying file checksums...")
                    with open(report_path, 'r') as f:
                        report = json.load(f)
                    
                    checksums = report.get('checksums', {})
                    verified = 0
                    failed = 0
                    
                    for file_path, expected_checksum in checksums.items():
                        restored_file = destination / file_path
                        if restored_file.exists() and restored_file.is_file():
                            actual_checksum = self.calculate_checksum(restored_file)
                            if actual_checksum == expected_checksum:
                                verified += 1
                            else:
                                failed += 1
                                logger.error(f"Checksum mismatch for {file_path}")
                    
                    logger.info(f"Checksum verification: {verified} passed, {failed} failed")
                    if failed > 0:
                        logger.warning("Some files failed checksum verification!")
                        return False
                else:
                    logger.warning("No report file found, skipping checksum verification")
            
            logger.info(f"Restoration completed successfully to: {destination}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to extract archive: {e}")
            return False
    
    def restore_to_project(self, archive_path: Path, dry_run: bool = True) -> bool:
        """Restore files directly to project (with optional dry-run)"""
        logger.info(f"{'DRY RUN: ' if dry_run else ''}Restoring to project from {archive_path.name}")
        
        files_to_restore = []
        
        try:
            if archive_path.suffix == '.gz':
                with tarfile.open(archive_path, "r:gz") as tar:
                    for member in tar.getmembers():
                        if member.isfile():
                            files_to_restore.append(member.name)
                            
            elif archive_path.suffix == '.zip':
                with zipfile.ZipFile(archive_path, 'r') as zipf:
                    files_to_restore = [f for f in zipf.namelist() if not f.endswith('/')]
            
            # Check for existing files
            existing_files = []
            for file_path in files_to_restore:
                target_path = self.project_root / file_path
                if target_path.exists():
                    existing_files.append(file_path)
            
            if existing_files:
                logger.warning(f"Found {len(existing_files)} existing files that would be overwritten:")
                for file in existing_files[:10]:
                    logger.warning(f"  - {file}")
                if len(existing_files) > 10:
                    logger.warning(f"  ... and {len(existing_files) - 10} more")
            
            if dry_run:
                logger.info("DRY RUN completed. No files were modified.")
                logger.info(f"Would restore {len(files_to_restore)} files")
                logger.info(f"Would overwrite {len(existing_files)} existing files")
                return True
            
            # Perform actual restoration
            if archive_path.suffix == '.gz':
                with tarfile.open(archive_path, "r:gz") as tar:
                    tar.extractall(path=self.project_root)
            elif archive_path.suffix == '.zip':
                with zipfile.ZipFile(archive_path, 'r') as zipf:
                    zipf.extractall(path=self.project_root)
            
            logger.info(f"Successfully restored {len(files_to_restore)} files")
            return True
            
        except Exception as e:
            logger.error(f"Failed to restore to project: {e}")
            return False

def main():
    """Main entry point for restoration script"""
    parser = argparse.ArgumentParser(description='ProLaunch MVP Backup Restoration Tool')
    parser.add_argument('action', choices=['list', 'extract', 'restore'],
                       help='Action to perform')
    parser.add_argument('--backup', help='Backup file name or path')
    parser.add_argument('--latest', action='store_true',
                       help='Use the latest backup')
    parser.add_argument('--destination', help='Extraction destination directory')
    parser.add_argument('--no-verify', action='store_true',
                       help='Skip checksum verification')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be restored without making changes')
    
    args = parser.parse_args()
    
    # Initialize restorer
    restorer = BackupRestorer()
    
    if args.action == 'list':
        # List available backups
        backups = restorer.list_backups()
        
        if not backups:
            print("No backups found.")
            sys.exit(1)
        
        print("\nAvailable Backups:")
        print("=" * 80)
        
        for i, backup in enumerate(backups):
            print(f"\n{i+1}. {backup['archive'].name}")
            print(f"   Size: {backup['size']:,} bytes")
            print(f"   Date: {backup['modified'].strftime('%Y-%m-%d %H:%M:%S')}")
            if 'version' in backup:
                print(f"   Version: {backup.get('version', 'Unknown')}")
                print(f"   Files: {backup.get('files_count', 'Unknown')}")
                print(f"   Verified: {'Yes' if backup.get('verified') else 'No'}")
        
        print("\n" + "=" * 80)
        print(f"Total backups: {len(backups)}")
        
    elif args.action == 'extract':
        # Extract backup to directory
        if args.latest:
            backups = restorer.list_backups()
            if not backups:
                logger.error("No backups found")
                sys.exit(1)
            archive_path = backups[0]['archive']
        elif args.backup:
            if Path(args.backup).exists():
                archive_path = Path(args.backup)
            else:
                archive_path = restorer.backup_dir / args.backup
                if not archive_path.exists():
                    logger.error(f"Backup not found: {args.backup}")
                    sys.exit(1)
        else:
            logger.error("Please specify --backup or --latest")
            sys.exit(1)
        
        destination = Path(args.destination) if args.destination else None
        success = restorer.extract_archive(
            archive_path, 
            destination,
            verify_checksums=not args.no_verify
        )
        
        sys.exit(0 if success else 1)
        
    elif args.action == 'restore':
        # Restore backup to project
        if args.latest:
            backups = restorer.list_backups()
            if not backups:
                logger.error("No backups found")
                sys.exit(1)
            archive_path = backups[0]['archive']
        elif args.backup:
            if Path(args.backup).exists():
                archive_path = Path(args.backup)
            else:
                archive_path = restorer.backup_dir / args.backup
                if not archive_path.exists():
                    logger.error(f"Backup not found: {args.backup}")
                    sys.exit(1)
        else:
            logger.error("Please specify --backup or --latest")
            sys.exit(1)
        
        success = restorer.restore_to_project(
            archive_path,
            dry_run=args.dry_run
        )
        
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()