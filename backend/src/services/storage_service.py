from typing import Optional, Dict, BinaryIO, Union, List
from ..infrastructure.storage.minio_client import MinioStorageClient
from ..infrastructure.redis.redis_mcp import RedisMCPClient
from datetime import timedelta
import mimetypes
import os
import json

class StorageService:
    def __init__(
        self,
        minio_client: MinioStorageClient,
        redis_client: RedisMCPClient,
        cache_expiry: int = 3600
    ):
        self.storage = minio_client
        self.cache = redis_client
        self.cache_expiry = cache_expiry

    async def upload_document(
        self,
        file_data: Union[bytes, BinaryIO],
        file_name: str,
        metadata: Optional[Dict] = None,
        cache: bool = True
    ) -> Dict:
        content_type, _ = mimetypes.guess_type(file_name)
        
        doc_metadata = metadata or {}
        doc_metadata.update({
            "original_filename": file_name,
            "content_type": content_type
        })
        
        result = await self.storage.upload_file(
            file_data=file_data,
            file_name=file_name,
            content_type=content_type,
            metadata=doc_metadata
        )
        
        if cache:
            cache_key = f"doc:{result['file_hash']}"
            await self.cache.set_cache(
                cache_key,
                result,
                expiry=self.cache_expiry
            )
        
        return result

    async def get_document(
        self,
        object_name: str,
        use_cache: bool = True
    ) -> Optional[bytes]:
        if use_cache:
            file_hash = object_name.split("/")[0]
            cache_key = f"doc:{file_hash}"
            cached_data = await self.cache.get_cache(cache_key)
            
            if cached_data and cached_data.get("object_name") == object_name:
                return await self.storage.download_file(object_name)
        
        return await self.storage.download_file(object_name)

    async def get_document_url(
        self,
        object_name: str,
        expires: timedelta = timedelta(hours=1)
    ) -> Optional[str]:
        return await self.storage.get_presigned_url(
            object_name=object_name,
            expires=expires
        )

    async def delete_document(
        self,
        object_name: str,
        clear_cache: bool = True
    ) -> bool:
        success = await self.storage.delete_file(object_name)
        
        if success and clear_cache:
            file_hash = object_name.split("/")[0]
            cache_key = f"doc:{file_hash}"
            await self.cache.delete_cache(cache_key)
        
        return success

    async def list_documents(
        self,
        prefix: Optional[str] = None,
        use_cache: bool = True
    ) -> List[Dict]:
        cache_key = f"doc_list:{prefix or 'all'}"
        
        if use_cache:
            cached_list = await self.cache.get_cache(cache_key)
            if cached_list:
                return cached_list
        
        documents = await self.storage.list_files(prefix=prefix)
        
        if documents and use_cache:
            await self.cache.set_cache(
                cache_key,
                documents,
                expiry=self.cache_expiry
            )
        
        return documents

    async def copy_document(
        self,
        source_object: str,
        dest_object: str,
        update_cache: bool = True
    ) -> bool:
        success = await self.storage.copy_file(
            source_object=source_object,
            dest_object=dest_object
        )
        
        if success and update_cache:
            source_hash = source_object.split("/")[0]
            dest_hash = dest_object.split("/")[0]
            
            source_cache_key = f"doc:{source_hash}"
            dest_cache_key = f"doc:{dest_hash}"
            
            source_data = await self.cache.get_cache(source_cache_key)
            if source_data:
                dest_data = dict(source_data)
                dest_data["object_name"] = dest_object
                await self.cache.set_cache(
                    dest_cache_key,
                    dest_data,
                    expiry=self.cache_expiry
                )
        
        return success

    async def get_document_metadata(
        self,
        object_name: str,
        use_cache: bool = True
    ) -> Optional[Dict]:
        if use_cache:
            file_hash = object_name.split("/")[0]
            cache_key = f"doc:{file_hash}"
            cached_data = await self.cache.get_cache(cache_key)
            
            if cached_data and cached_data.get("object_name") == object_name:
                return cached_data
        
        return await self.storage.get_file_metadata(object_name)