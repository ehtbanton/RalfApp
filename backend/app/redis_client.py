import redis.asyncio as redis
from decouple import config
import json
from typing import Any, Optional
import logging

logger = logging.getLogger(__name__)

class RedisClient:
    def __init__(self):
        self.redis_url = config("REDIS_URL", default="redis://localhost:6379")
        self.redis_password = config("REDIS_PASSWORD", default=None)
        self.pool = None
        self.client = None

    async def connect(self):
        try:
            self.pool = redis.ConnectionPool.from_url(
                self.redis_url,
                password=self.redis_password,
                decode_responses=True
            )
            self.client = redis.Redis(connection_pool=self.pool)
            await self.client.ping()
            logger.info("Connected to Redis successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    async def disconnect(self):
        if self.client:
            await self.client.close()

    async def get(self, key: str) -> Optional[Any]:
        try:
            value = await self.client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Redis GET error for key {key}: {e}")
            return None

    async def set(self, key: str, value: Any, expire: int = 3600):
        try:
            serialized_value = json.dumps(value, default=str)
            await self.client.set(key, serialized_value, ex=expire)
        except Exception as e:
            logger.error(f"Redis SET error for key {key}: {e}")

    async def delete(self, key: str):
        try:
            await self.client.delete(key)
        except Exception as e:
            logger.error(f"Redis DELETE error for key {key}: {e}")

    async def exists(self, key: str) -> bool:
        try:
            return await self.client.exists(key)
        except Exception as e:
            logger.error(f"Redis EXISTS error for key {key}: {e}")
            return False

    async def set_session(self, session_id: str, data: dict, expire: int = 1800):
        """Store session data with expiration (30 minutes default)"""
        await self.set(f"session:{session_id}", data, expire)

    async def get_session(self, session_id: str) -> Optional[dict]:
        """Retrieve session data"""
        return await self.get(f"session:{session_id}")

    async def delete_session(self, session_id: str):
        """Delete session data"""
        await self.delete(f"session:{session_id}")

    async def cache_video_metadata(self, video_id: str, metadata: dict, expire: int = 3600):
        """Cache video metadata"""
        await self.set(f"video_metadata:{video_id}", metadata, expire)

    async def get_cached_video_metadata(self, video_id: str) -> Optional[dict]:
        """Get cached video metadata"""
        return await self.get(f"video_metadata:{video_id}")

    async def cache_analysis_result(self, analysis_id: str, result: dict, expire: int = 7200):
        """Cache analysis results (2 hours default)"""
        await self.set(f"analysis:{analysis_id}", result, expire)

    async def get_cached_analysis(self, analysis_id: str) -> Optional[dict]:
        """Get cached analysis result"""
        return await self.get(f"analysis:{analysis_id}")

    async def publish(self, channel: str, message: dict):
        """Publish message to Redis channel"""
        try:
            serialized_message = json.dumps(message, default=str)
            await self.client.publish(channel, serialized_message)
        except Exception as e:
            logger.error(f"Redis PUBLISH error for channel {channel}: {e}")

    async def subscribe(self, channel: str):
        """Subscribe to Redis channel"""
        try:
            pubsub = self.client.pubsub()
            await pubsub.subscribe(channel)
            return pubsub
        except Exception as e:
            logger.error(f"Redis SUBSCRIBE error for channel {channel}: {e}")
            return None

# Global Redis client instance
redis_client = RedisClient()

async def get_redis():
    return redis_client