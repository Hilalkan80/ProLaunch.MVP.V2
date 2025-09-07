from typing import Optional, Dict, BinaryIO, Union, List
import minio
from minio.error import MinioError
import hashlib
import os
import io
from datetime import timedelta
import asyncio
from functools import wraps

class MinioStorageClient:
    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        secure: bool = True,
        region: str = "us-east-1",
        default_bucket: str = "prolaunch-documents"
    ):
        self.client = minio.Minio(
            endpoint=endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
            region=region
        )
        self.default_bucket = default_bucket
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        try:
            if not self.client.bucket_exists(self.default_bucket):
                self.client.make_bucket(
                    self.default_bucket,
                    location=self.client._region_map[self.client._region]
                )
                
                config = {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {"AWS": "*"},
                            "Action": ["s3:GetObject"],
                            "Resource": [f"arn:aws:s3:::{self.default_bucket}/*"]
                        }
                    ]
                }
                self.client.set_bucket_policy(self.default_bucket, config)
        except MinioError as e:
            print(f"MinIO error in _ensure_bucket_exists: {e}")

    def _calculate_file_hash(self, file_data: Union[bytes, BinaryIO]) -> str:
        if isinstance(file_data, bytes):
            return hashlib.sha256(file_data).hexdigest()
        else:
            sha256_hash = hashlib.sha256()
            for byte_block in iter(lambda: file_data.read(4096), b""):
                sha256_hash.update(byte_block)
            file_data.seek(0)
            return sha256_hash.hexdigest()

    async def upload_file(
        self,
        file_data: Union[bytes, BinaryIO],
        file_name: str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict] = None,
        bucket_name: Optional[str] = None
    ) -> Dict:
        try:
            bucket = bucket_name or self.default_bucket
            file_hash = self._calculate_file_hash(file_data)
            object_name = f"{file_hash}/{file_name}"
            
            file_size = len(file_data) if isinstance(file_data, bytes) else file_data.seek(0, 2)
            if isinstance(file_data, BinaryIO):
                file_data.seek(0)
            
            if isinstance(file_data, bytes):
                file_stream = io.BytesIO(file_data)
            else:
                file_stream = file_data

            await asyncio.to_thread(
                self.client.put_object,
                bucket,
                object_name,
                file_stream,
                file_size,
                content_type=content_type,
                metadata=metadata
            )

            return {
                "bucket": bucket,
                "object_name": object_name,
                "file_hash": file_hash,
                "size": file_size,
                "content_type": content_type,
                "metadata": metadata
            }
        except MinioError as e:
            print(f"MinIO error in upload_file: {e}")
            raise

    async def download_file(
        self,
        object_name: str,
        bucket_name: Optional[str] = None
    ) -> Optional[bytes]:
        try:
            bucket = bucket_name or self.default_bucket
            response = await asyncio.to_thread(
                self.client.get_object,
                bucket,
                object_name
            )
            return await asyncio.to_thread(response.read)
        except MinioError as e:
            print(f"MinIO error in download_file: {e}")
            return None

    async def get_presigned_url(
        self,
        object_name: str,
        expires: timedelta = timedelta(hours=1),
        bucket_name: Optional[str] = None
    ) -> Optional[str]:
        try:
            bucket = bucket_name or self.default_bucket
            return await asyncio.to_thread(
                self.client.presigned_get_object,
                bucket,
                object_name,
                expires=int(expires.total_seconds())
            )
        except MinioError as e:
            print(f"MinIO error in get_presigned_url: {e}")
            return None

    async def delete_file(
        self,
        object_name: str,
        bucket_name: Optional[str] = None
    ) -> bool:
        try:
            bucket = bucket_name or self.default_bucket
            await asyncio.to_thread(
                self.client.remove_object,
                bucket,
                object_name
            )
            return True
        except MinioError as e:
            print(f"MinIO error in delete_file: {e}")
            return False

    async def list_files(
        self,
        prefix: Optional[str] = None,
        recursive: bool = True,
        bucket_name: Optional[str] = None
    ) -> List[Dict]:
        try:
            bucket = bucket_name or self.default_bucket
            objects = await asyncio.to_thread(
                lambda: list(self.client.list_objects(
                    bucket,
                    prefix=prefix,
                    recursive=recursive
                ))
            )
            
            return [
                {
                    "object_name": obj.object_name,
                    "size": obj.size,
                    "last_modified": obj.last_modified,
                    "etag": obj.etag,
                    "content_type": obj.content_type
                }
                for obj in objects
            ]
        except MinioError as e:
            print(f"MinIO error in list_files: {e}")
            return []

    async def copy_file(
        self,
        source_object: str,
        dest_object: str,
        source_bucket: Optional[str] = None,
        dest_bucket: Optional[str] = None
    ) -> bool:
        try:
            src_bucket = source_bucket or self.default_bucket
            dst_bucket = dest_bucket or self.default_bucket
            
            await asyncio.to_thread(
                self.client.copy_object,
                dst_bucket,
                dest_object,
                f"{src_bucket}/{source_object}"
            )
            return True
        except MinioError as e:
            print(f"MinIO error in copy_file: {e}")
            return False

    async def get_file_metadata(
        self,
        object_name: str,
        bucket_name: Optional[str] = None
    ) -> Optional[Dict]:
        try:
            bucket = bucket_name or self.default_bucket
            obj = await asyncio.to_thread(
                self.client.stat_object,
                bucket,
                object_name
            )
            return {
                "size": obj.size,
                "last_modified": obj.last_modified,
                "etag": obj.etag,
                "content_type": obj.content_type,
                "metadata": obj.metadata
            }
        except MinioError as e:
            print(f"MinIO error in get_file_metadata: {e}")
            return None