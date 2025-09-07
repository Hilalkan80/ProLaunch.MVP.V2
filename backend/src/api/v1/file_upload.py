"""
Secure file upload endpoint for chat attachments.
Includes comprehensive security validation and threat detection.
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from typing import Optional, Dict, Any
from uuid import UUID
import logging
import hashlib
import os
import json
from datetime import datetime
from pathlib import Path
import aiofiles

from ...core.deps import get_db, get_redis, get_current_user
from ...core.security import (
    file_validator, ContentSecurityError, RedisRateLimiter, 
    RateLimitType, RateLimitExceeded, get_security_monitor,
    SecurityEventType, SecurityEventLevel
)
from ...models.user import User
from ...core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

# File storage configuration
UPLOAD_DIR = Path(settings.UPLOAD_DIR if hasattr(settings, 'UPLOAD_DIR') else './uploads')
MAX_TOTAL_SIZE = 100 * 1024 * 1024  # 100MB total per user
ALLOWED_TOTAL_FILES = 50  # Maximum files per user

class SecureFileUploadService:
    """Service for handling secure file uploads"""
    
    def __init__(self, redis, upload_dir: Path = UPLOAD_DIR):
        self.redis = redis
        self.upload_dir = upload_dir
        self.security_monitor = get_security_monitor()
        self.rate_limiter = RedisRateLimiter(redis)
        
        # Ensure upload directory exists
        self.upload_dir.mkdir(parents=True, exist_ok=True)
    
    async def process_upload(
        self,
        file: UploadFile,
        user: User,
        room_id: Optional[UUID] = None,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process and validate file upload with comprehensive security checks.
        
        Args:
            file: Uploaded file
            user: Current user
            room_id: Chat room ID if applicable
            description: File description
            
        Returns:
            Dict with file metadata and storage info
            
        Raises:
            ContentSecurityError: If file fails security validation
            RateLimitExceeded: If rate limit exceeded
            HTTPException: For other errors
        """
        user_id = user.id
        
        try:
            # Rate limit file uploads
            allowed, retry_after = await self.rate_limiter.is_allowed(
                str(user_id), RateLimitType.FILE_UPLOAD
            )
            
            if not allowed:
                if self.security_monitor:
                    self.security_monitor.track_rate_limit_violation(
                        user_id, "file_upload", 0, 10, 3600
                    )
                raise RateLimitExceeded(RateLimitType.FILE_UPLOAD, retry_after)
            
            # Check user storage quota
            await self._check_user_quota(user_id, len(await file.read()))
            await file.seek(0)  # Reset file pointer
            
            # Validate file security
            validation_result = await file_validator.validate_file_upload(
                file, user_id
            )
            
            if not validation_result['is_valid']:
                raise ContentSecurityError("File failed security validation")
            
            # Generate secure file path
            file_path, file_url = await self._generate_secure_path(
                user_id, file.filename, validation_result['hash']
            )
            
            # Save file securely
            await self._save_file_secure(file, file_path)
            
            # Store file metadata
            file_metadata = {
                'id': validation_result['hash'],
                'original_filename': validation_result['filename'],
                'stored_filename': file_path.name,
                'file_type': validation_result['file_type'],
                'mime_type': validation_result['mime_type'],\n                'size': validation_result['size'],\n                'hash': validation_result['hash'],\n                'user_id': str(user_id),\n                'room_id': str(room_id) if room_id else None,\n                'description': description,\n                'upload_url': file_url,\n                'security_scan_passed': validation_result['security_scan_passed'],\n                'upload_timestamp': datetime.utcnow().isoformat()\n            }\n            \n            # Store metadata in Redis\n            await self._store_file_metadata(validation_result['hash'], file_metadata)\n            \n            # Update user storage usage\n            await self._update_user_storage(user_id, validation_result['size'])\n            \n            # Log successful upload\n            logger.info(\n                f\"File uploaded successfully: {file.filename} by user {user_id}\"\n            )\n            \n            if self.security_monitor:\n                self.security_monitor.add_security_breadcrumb(\n                    f\"File uploaded: {file.filename}\",\n                    category=\"file_upload\",\n                    data={\n                        \"file_type\": validation_result['file_type'],\n                        \"size\": validation_result['size'],\n                        \"user_id\": str(user_id)\n                    }\n                )\n            \n            return file_metadata\n            \n        except (ContentSecurityError, RateLimitExceeded):\n            raise\n        except Exception as e:\n            logger.error(f\"File upload error: {str(e)}\")\n            if self.security_monitor:\n                self.security_monitor.track_security_event(\n                    SecurityEventType.SUSPICIOUS_FILE_UPLOAD,\n                    SecurityEventLevel.ERROR,\n                    user_id,\n                    {\n                        \"filename\": file.filename,\n                        \"error\": str(e)\n                    }\n                )\n            raise HTTPException(status_code=500, detail=\"File upload failed\")\n    \n    async def _check_user_quota(self, user_id: UUID, file_size: int):\n        \"\"\"Check if user has storage quota available\"\"\"\n        # Get current usage\n        usage_key = f\"user_storage:{user_id}\"\n        current_usage = await self.redis.get(usage_key) or 0\n        current_usage = int(current_usage)\n        \n        if current_usage + file_size > MAX_TOTAL_SIZE:\n            raise ContentSecurityError(\n                f\"Storage quota exceeded. Current: {current_usage}, \"\n                f\"Limit: {MAX_TOTAL_SIZE}, Requested: {file_size}\"\n            )\n        \n        # Check file count\n        count_key = f\"user_file_count:{user_id}\"\n        current_count = await self.redis.get(count_key) or 0\n        current_count = int(current_count)\n        \n        if current_count >= ALLOWED_TOTAL_FILES:\n            raise ContentSecurityError(\n                f\"File count limit exceeded. Current: {current_count}, \"\n                f\"Limit: {ALLOWED_TOTAL_FILES}\"\n            )\n    \n    async def _generate_secure_path(self, user_id: UUID, filename: str, file_hash: str) -> tuple:\n        \"\"\"Generate secure file path and URL\"\"\"\n        # Create user-specific subdirectory\n        user_dir = self.upload_dir / str(user_id)\n        user_dir.mkdir(exist_ok=True)\n        \n        # Use hash as filename to prevent conflicts and hide original names\n        file_ext = Path(filename).suffix.lower()\n        secure_filename = f\"{file_hash}{file_ext}\"\n        file_path = user_dir / secure_filename\n        \n        # Generate access URL (would typically be served through a secure endpoint)\n        file_url = f\"/api/v1/files/{user_id}/{secure_filename}\"\n        \n        return file_path, file_url\n    \n    async def _save_file_secure(self, file: UploadFile, file_path: Path):\n        \"\"\"Save file with security measures\"\"\"\n        # Read file content\n        content = await file.read()\n        \n        # Save with restricted permissions\n        async with aiofiles.open(file_path, 'wb') as f:\n            await f.write(content)\n        \n        # Set restrictive file permissions (read-only for owner)\n        os.chmod(file_path, 0o600)\n    \n    async def _store_file_metadata(self, file_hash: str, metadata: Dict):\n        \"\"\"Store file metadata in Redis\"\"\"\n        metadata_key = f\"file_metadata:{file_hash}\"\n        await self.redis.setex(\n            metadata_key,\n            86400 * 30,  # 30 days\n            json.dumps(metadata)\n        )\n    \n    async def _update_user_storage(self, user_id: UUID, file_size: int):\n        \"\"\"Update user storage usage counters\"\"\"\n        usage_key = f\"user_storage:{user_id}\"\n        count_key = f\"user_file_count:{user_id}\"\n        \n        # Update usage (atomic operation)\n        pipe = self.redis.pipeline()\n        pipe.incrby(usage_key, file_size)\n        pipe.incr(count_key)\n        pipe.expire(usage_key, 86400 * 30)  # 30 days\n        pipe.expire(count_key, 86400 * 30)  # 30 days\n        await pipe.execute()\n\n@router.post(\"/upload\")\nasync def upload_file(\n    file: UploadFile = File(...),\n    room_id: Optional[str] = Form(None),\n    description: Optional[str] = Form(None),\n    db = Depends(get_db),\n    redis = Depends(get_redis),\n    current_user: User = Depends(get_current_user)\n):\n    \"\"\"\n    Upload a file with comprehensive security validation.\n    \n    - **file**: The file to upload\n    - **room_id**: Optional chat room ID\n    - **description**: Optional file description\n    \"\"\"\n    upload_service = SecureFileUploadService(redis)\n    \n    try:\n        # Validate room_id format if provided\n        parsed_room_id = None\n        if room_id:\n            try:\n                parsed_room_id = UUID(room_id)\n            except ValueError:\n                raise HTTPException(status_code=400, detail=\"Invalid room_id format\")\n        \n        # Validate description length\n        if description and len(description) > 500:\n            raise HTTPException(status_code=400, detail=\"Description too long (max 500 characters)\")\n        \n        # Process upload\n        result = await upload_service.process_upload(\n            file=file,\n            user=current_user,\n            room_id=parsed_room_id,\n            description=description\n        )\n        \n        return {\n            \"success\": True,\n            \"file_id\": result['id'],\n            \"filename\": result['original_filename'],\n            \"size\": result['size'],\n            \"type\": result['file_type'],\n            \"url\": result['upload_url'],\n            \"upload_timestamp\": result['upload_timestamp']\n        }\n        \n    except ContentSecurityError as e:\n        raise HTTPException(status_code=400, detail=str(e))\n    except RateLimitExceeded as e:\n        raise HTTPException(\n            status_code=429, \n            detail=f\"Rate limit exceeded. Try again in {e.retry_after} seconds.\"\n        )\n    except HTTPException:\n        raise\n    except Exception as e:\n        logger.error(f\"Upload endpoint error: {str(e)}\")\n        raise HTTPException(status_code=500, detail=\"Upload failed\")\n\n@router.get(\"/files/{user_id}/{filename}\")\nasync def download_file(\n    user_id: str,\n    filename: str,\n    redis = Depends(get_redis),\n    current_user: User = Depends(get_current_user)\n):\n    \"\"\"\n    Download a file with access control validation.\n    \"\"\"\n    try:\n        # Validate access (user can only access their own files or shared files)\n        if str(current_user.id) != user_id:\n            # Check if file is shared in a room user has access to\n            # This would require additional logic to check room membership\n            raise HTTPException(status_code=403, detail=\"Access denied\")\n        \n        # Get file metadata\n        file_hash = filename.split('.')[0]  # Remove extension\n        metadata_key = f\"file_metadata:{file_hash}\"\n        metadata_json = await redis.get(metadata_key)\n        \n        if not metadata_json:\n            raise HTTPException(status_code=404, detail=\"File not found\")\n        \n        metadata = json.loads(metadata_json)\n        file_path = UPLOAD_DIR / user_id / filename\n        \n        if not file_path.exists():\n            raise HTTPException(status_code=404, detail=\"File not found on disk\")\n        \n        # Security: Validate file path is within allowed directory\n        if not str(file_path.resolve()).startswith(str(UPLOAD_DIR.resolve())):\n            logger.warning(f\"Path traversal attempt: {file_path}\")\n            raise HTTPException(status_code=403, detail=\"Access denied\")\n        \n        # Return file with proper headers\n        return FileResponse(\n            path=file_path,\n            filename=metadata['original_filename'],\n            media_type=metadata['mime_type']\n        )\n        \n    except HTTPException:\n        raise\n    except Exception as e:\n        logger.error(f\"Download endpoint error: {str(e)}\")\n        raise HTTPException(status_code=500, detail=\"Download failed\")\n\n@router.get(\"/files/{user_id}\")\nasync def list_user_files(\n    user_id: str,\n    redis = Depends(get_redis),\n    current_user: User = Depends(get_current_user)\n):\n    \"\"\"\n    List files for a user (admin or self only).\n    \"\"\"\n    if str(current_user.id) != user_id and not current_user.is_admin:\n        raise HTTPException(status_code=403, detail=\"Access denied\")\n    \n    try:\n        # Get user file list from Redis\n        pattern = f\"file_metadata:*\"\n        keys = await redis.keys(pattern)\n        \n        files = []\n        for key in keys:\n            metadata_json = await redis.get(key)\n            if metadata_json:\n                metadata = json.loads(metadata_json)\n                if metadata.get('user_id') == user_id:\n                    files.append({\n                        'id': metadata['id'],\n                        'filename': metadata['original_filename'],\n                        'size': metadata['size'],\n                        'type': metadata['file_type'],\n                        'upload_timestamp': metadata['upload_timestamp']\n                    })\n        \n        return {'files': files}\n        \n    except Exception as e:\n        logger.error(f\"List files error: {str(e)}\")\n        raise HTTPException(status_code=500, detail=\"Failed to list files\")