import asyncio
from typing import Dict, Optional
from ..redis.redis_mcp import RedisMCPClient
from ..storage.minio_client import MinioStorageClient
import os
import json
import time
from datetime import datetime

class InfrastructureTest:
    def __init__(
        self,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_password: Optional[str] = None,
        minio_endpoint: str = "localhost:9000",
        minio_access_key: str = "minioadmin",
        minio_secret_key: str = "minioadmin",
        minio_secure: bool = False
    ):
        self.redis = RedisMCPClient(
            host=redis_host,
            port=redis_port,
            password=redis_password
        )
        self.minio = MinioStorageClient(
            endpoint=minio_endpoint,
            access_key=minio_access_key,
            secret_key=minio_secret_key,
            secure=minio_secure
        )

    async def test_redis_connection(self) -> Dict:
        start_time = time.time()
        error = None
        
        try:
            test_key = f"test:connection:{datetime.now().timestamp()}"
            test_data = {"timestamp": datetime.now().isoformat()}
            
            # Test basic set/get
            await self.redis.set_cache(test_key, test_data, expiry=60)
            retrieved_data = await self.redis.get_cache(test_key)
            assert retrieved_data == test_data, "Data mismatch in Redis get/set test"
            
            # Test pub/sub
            test_channel = f"test:channel:{datetime.now().timestamp()}"
            message_count = await self.redis.publish(test_channel, test_data)
            assert message_count >= 0, "Failed to publish message"
            
            # Test rate limiting
            rate_key = f"test:rate:{datetime.now().timestamp()}"
            rate_check = await self.redis.rate_limit(rate_key, 5, 10)
            assert rate_check is True, "Rate limiting check failed"
            
            # Test locking
            lock_name = f"test:lock:{datetime.now().timestamp()}"
            lock_value = await self.redis.lock(lock_name, expiry=10)
            assert lock_value is not None, "Failed to acquire lock"
            unlock_success = await self.redis.unlock(lock_name, lock_value)
            assert unlock_success is True, "Failed to release lock"
            
            # Test session
            session_id = f"test:session:{datetime.now().timestamp()}"
            session_data = {"user_id": "test_user", "timestamp": datetime.now().isoformat()}
            session_success = await self.redis.session_manager(session_id, session_data)
            assert session_success is True, "Failed to create session"
            retrieved_session = await self.redis.session_manager(session_id)
            assert retrieved_session == session_data, "Session data mismatch"
            
            # Cleanup
            await self.redis.delete_cache(test_key)
            await self.redis.delete_cache(rate_key)
            await self.redis.delete_cache(f"session:{session_id}")
            
        except Exception as e:
            error = str(e)
        
        end_time = time.time()
        duration = end_time - start_time
        
        return {
            "service": "Redis",
            "success": error is None,
            "error": error,
            "duration_ms": int(duration * 1000),
            "timestamp": datetime.now().isoformat()
        }

    async def test_minio_connection(self) -> Dict:
        start_time = time.time()
        error = None
        
        try:
            test_file_data = b"Test file content"
            test_filename = f"test_file_{datetime.now().timestamp()}.txt"
            test_metadata = {"test_key": "test_value"}
            
            # Test upload
            upload_result = await self.minio.upload_file(
                test_file_data,
                test_filename,
                content_type="text/plain",
                metadata=test_metadata
            )
            assert upload_result["object_name"], "Failed to upload file"
            
            # Test download
            downloaded_data = await self.minio.download_file(upload_result["object_name"])
            assert downloaded_data == test_file_data, "Downloaded content mismatch"
            
            # Test presigned URL
            url = await self.minio.get_presigned_url(upload_result["object_name"])
            assert url is not None, "Failed to generate presigned URL"
            
            # Test metadata
            metadata = await self.minio.get_file_metadata(upload_result["object_name"])
            assert metadata is not None, "Failed to get metadata"
            assert metadata["content_type"] == "text/plain", "Content type mismatch"
            
            # Test copy
            copy_filename = f"copy_{test_filename}"
            copy_success = await self.minio.copy_file(
                upload_result["object_name"],
                copy_filename
            )
            assert copy_success is True, "Failed to copy file"
            
            # Test list files
            files = await self.minio.list_files()
            assert len(files) > 0, "Failed to list files"
            
            # Cleanup
            await self.minio.delete_file(upload_result["object_name"])
            await self.minio.delete_file(copy_filename)
            
        except Exception as e:
            error = str(e)
        
        end_time = time.time()
        duration = end_time - start_time
        
        return {
            "service": "MinIO",
            "success": error is None,
            "error": error,
            "duration_ms": int(duration * 1000),
            "timestamp": datetime.now().isoformat()
        }

    async def test_all_connections(self) -> Dict:
        results = await asyncio.gather(
            self.test_redis_connection(),
            self.test_minio_connection()
        )
        
        all_successful = all(result["success"] for result in results)
        
        return {
            "overall_status": "healthy" if all_successful else "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "services": results
        }

    async def close(self):
        await self.redis.close()

async def run_tests():
    tester = InfrastructureTest(
        redis_host=os.getenv("REDIS_HOST", "localhost"),
        redis_port=int(os.getenv("REDIS_PORT", "6379")),
        redis_password=os.getenv("REDIS_PASSWORD"),
        minio_endpoint=os.getenv("MINIO_ENDPOINT", "localhost:9000"),
        minio_access_key=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
        minio_secret_key=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
        minio_secure=os.getenv("MINIO_SECURE", "false").lower() == "true"
    )
    
    try:
        results = await tester.test_all_connections()
        print(json.dumps(results, indent=2))
    finally:
        await tester.close()

if __name__ == "__main__":
    asyncio.run(run_tests())