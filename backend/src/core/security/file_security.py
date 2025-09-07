import os
import magic
import hashlib
import logging
import aiofiles
import asyncio
from typing import List, Optional, Set, Tuple
from pathlib import Path
from datetime import datetime
from fastapi import UploadFile, HTTPException
import aiofiles.os

logger = logging.getLogger(__name__)

class FileSecurityValidator:
    def __init__(self):
        # Initialize magic for MIME type detection
        self.mime = magic.Magic(mime=True)
        
        # Maximum file size (10MB)
        self.MAX_FILE_SIZE = 10 * 1024 * 1024
        
        # Allowed file types and their corresponding MIME types
        self.ALLOWED_FILE_TYPES = {
            'image': {
                'image/jpeg',
                'image/png',
                'image/gif',
                'image/webp'
            },
            'document': {
                'application/pdf',
                'application/msword',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'text/plain'
            },
            'audio': {
                'audio/mpeg',
                'audio/wav',
                'audio/ogg'
            }
        }
        
        # Dangerous extensions that are always blocked
        self.BLOCKED_EXTENSIONS = {
            '.exe', '.dll', '.so', '.bat', '.cmd', '.sh', '.ps1',
            '.vbs', '.js', '.php', '.pl', '.py', '.rb', '.jar'
        }
        
        # Extensions that require extra validation
        self.RISKY_EXTENSIONS = {
            '.zip', '.tar', '.gz', '.rar', '.7z',
            '.doc', '.docx', '.pdf'
        }
        
        # Load virus signature database
        self.virus_signatures = self.load_virus_signatures()
        
        # Initialize scan results cache
        self.scan_cache = {}

    def load_virus_signatures(self) -> Set[bytes]:
        """
        Load virus signatures from database
        In a real implementation, this would load from an actual database
        """
        return {
            b'X5O!P%@AP[4\\PZX54(P^)7CC)7}$',  # Example EICAR signature
            b'virus_signature_2',
            b'malware_pattern_3'
        }

    async def validate_file(
        self,
        file: UploadFile,
        allowed_types: Optional[List[str]] = None
    ) -> Tuple[bool, List[str]]:
        """
        Validate a file upload
        Returns (is_valid, warnings)
        """
        warnings = []
        
        try:
            # Validate file size
            size = await self.get_file_size(file)
            if size > self.MAX_FILE_SIZE:
                return False, ['File size exceeds maximum allowed']
            
            # Validate file extension
            ext = self.get_file_extension(file.filename)
            if ext.lower() in self.BLOCKED_EXTENSIONS:
                return False, ['File type not allowed']
            
            # Get actual MIME type
            mime_type = await self.get_mime_type(file)
            
            # Validate against allowed types
            if allowed_types:
                allowed_mimes = set()
                for type_key in allowed_types:
                    allowed_mimes.update(
                        self.ALLOWED_FILE_TYPES.get(type_key, set())
                    )
                if mime_type not in allowed_mimes:
                    return False, ['File type not allowed']
            
            # Check for MIME type spoofing
            declared_type = file.content_type
            if declared_type != mime_type:
                warnings.append('MIME type mismatch detected')
            
            # Scan for malicious content
            is_safe, scan_warnings = await self.scan_file_content(file)
            if not is_safe:
                return False, scan_warnings
            
            warnings.extend(scan_warnings)
            
            # Additional checks for risky extensions
            if ext.lower() in self.RISKY_EXTENSIONS:
                warnings.append('File type requires extra caution')
            
            return True, warnings

        except Exception as e:
            logger.error(f"File validation error: {e}")
            return False, ['File validation failed']

    async def get_file_size(self, file: UploadFile) -> int:
        """
        Get file size in bytes
        """
        try:
            # Try to get size from file object
            if hasattr(file.file, 'seek') and hasattr(file.file, 'tell'):
                current_pos = file.file.tell()
                file.file.seek(0, 2)  # Seek to end
                size = file.file.tell()
                file.file.seek(current_pos)  # Restore position
                return size
            
            # Fallback to reading chunks
            size = 0
            chunk_size = 8192
            
            current_pos = file.file.tell()
            file.file.seek(0)
            
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                size += len(chunk)
            
            await file.seek(current_pos)
            return size

        except Exception as e:
            logger.error(f"File size check error: {e}")
            raise HTTPException(
                status_code=400,
                detail="Could not determine file size"
            )

    def get_file_extension(self, filename: str) -> str:
        """
        Get file extension from filename
        """
        return os.path.splitext(filename)[1].lower()

    async def get_mime_type(self, file: UploadFile) -> str:
        """
        Get actual MIME type of file
        """
        try:
            # Read first 2048 bytes for MIME detection
            current_pos = file.file.tell()
            file.file.seek(0)
            header = await file.read(2048)
            await file.seek(current_pos)
            
            return self.mime.from_buffer(header)

        except Exception as e:
            logger.error(f"MIME type detection error: {e}")
            raise HTTPException(
                status_code=400,
                detail="Could not determine file type"
            )

    async def scan_file_content(
        self,
        file: UploadFile
    ) -> Tuple[bool, List[str]]:
        """
        Scan file content for malicious patterns
        """
        warnings = []
        
        try:
            # Calculate file hash
            current_pos = file.file.tell()
            file.file.seek(0)
            
            hasher = hashlib.sha256()
            chunk_size = 8192
            
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                hasher.update(chunk)
            
            await file.seek(current_pos)
            file_hash = hasher.hexdigest()
            
            # Check cache
            if file_hash in self.scan_cache:
                cache_result = self.scan_cache[file_hash]
                if (datetime.now() - cache_result['timestamp']).total_seconds() < 3600:
                    return cache_result['is_safe'], cache_result['warnings']
            
            # Scan for virus signatures
            current_pos = file.file.tell()
            file.file.seek(0)
            
            content = await file.read()
            await file.seek(current_pos)
            
            for signature in self.virus_signatures:
                if signature in content:
                    return False, ['Malicious content detected']
            
            # Check for suspicious patterns
            patterns = [
                b'eval(',
                b'system(',
                b'exec(',
                b'<script',
                b'function()'
            ]
            
            for pattern in patterns:
                if pattern in content.lower():
                    warnings.append(f'Suspicious pattern detected: {pattern}')
            
            # Cache the result
            self.scan_cache[file_hash] = {
                'is_safe': True,
                'warnings': warnings,
                'timestamp': datetime.now()
            }
            
            return True, warnings

        except Exception as e:
            logger.error(f"File content scan error: {e}")
            return False, ['File scanning failed']

    async def save_file_safely(
        self,
        file: UploadFile,
        destination: Path,
        user_id: str
    ) -> Tuple[Path, List[str]]:
        """
        Safely save an uploaded file
        """
        warnings = []
        
        try:
            # Create user upload directory if it doesn't exist
            user_dir = destination / user_id
            await aiofiles.os.makedirs(user_dir, exist_ok=True)
            
            # Generate safe filename
            original_ext = self.get_file_extension(file.filename)
            safe_filename = f"{hashlib.sha256(str(datetime.now().timestamp()).encode()).hexdigest()}{original_ext}"
            file_path = user_dir / safe_filename
            
            # Save file
            async with aiofiles.open(file_path, 'wb') as f:
                current_pos = file.file.tell()
                file.file.seek(0)
                
                while True:
                    chunk = await file.read(8192)
                    if not chunk:
                        break
                    await f.write(chunk)
                
                await file.seek(current_pos)
            
            # Set secure permissions
            os.chmod(file_path, 0o644)
            
            return file_path, warnings

        except Exception as e:
            logger.error(f"File save error: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to save file"
            )