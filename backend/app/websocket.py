from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from .database import get_db
from .models import UploadSession, Video
from .redis_client import redis_client
from .auth import verify_token
import json
import base64
import os
import aiofiles
from datetime import datetime
from uuid import UUID
import logging
import secrets

logger = logging.getLogger(__name__)
websocket_router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"WebSocket connection established for client: {client_id}")

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"WebSocket connection closed for client: {client_id}")

    async def send_personal_message(self, message: dict, client_id: str):
        if client_id in self.active_connections:
            websocket = self.active_connections[client_id]
            await websocket.send_text(json.dumps(message))

    async def broadcast(self, message: dict):
        for connection in self.active_connections.values():
            await connection.send_text(json.dumps(message))

manager = ConnectionManager()

@websocket_router.websocket("/upload/{session_token}")
async def websocket_upload_endpoint(websocket: WebSocket, session_token: str):
    client_id = f"upload_{session_token}"
    await manager.connect(websocket, client_id)

    try:
        # Get upload session from database
        from .database import async_session
        async with async_session() as db:
            result = await db.execute(
                select(UploadSession).where(UploadSession.session_token == session_token)
            )
            upload_session = result.scalars().first()

            if not upload_session:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Invalid session token"
                }))
                return

            if upload_session.expires_at < datetime.utcnow():
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Session expired"
                }))
                return

            if upload_session.status != "active":
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Session is not active"
                }))
                return

            # Send session info
            await websocket.send_text(json.dumps({
                "type": "session_info",
                "data": {
                    "session_id": str(upload_session.id),
                    "filename": upload_session.filename,
                    "file_size": upload_session.file_size,
                    "chunk_size": upload_session.chunk_size,
                    "total_chunks": upload_session.total_chunks,
                    "uploaded_chunks": upload_session.uploaded_chunks
                }
            }))

            # Create storage directory
            storage_path = os.getenv("VIDEO_STORAGE_PATH", "/app/storage")
            user_dir = os.path.join(storage_path, str(upload_session.user_id))
            os.makedirs(user_dir, exist_ok=True)

            # Generate unique filename
            file_extension = os.path.splitext(upload_session.filename)[1]
            unique_filename = f"{secrets.token_urlsafe(16)}{file_extension}"
            file_path = os.path.join(user_dir, unique_filename)

            # Keep track of received chunks
            received_chunks = set()
            chunk_data = {}

            while True:
                try:
                    data = await websocket.receive_text()
                    message = json.loads(data)

                    if message["type"] == "chunk":
                        chunk_index = message["chunk_index"]
                        chunk_content = base64.b64decode(message["chunk_data"])

                        # Store chunk temporarily
                        chunk_data[chunk_index] = chunk_content
                        received_chunks.add(chunk_index)

                        # Update progress in database
                        upload_session.uploaded_chunks = len(received_chunks)
                        await db.commit()

                        # Send progress update
                        progress = (len(received_chunks) / upload_session.total_chunks) * 100
                        await websocket.send_text(json.dumps({
                            "type": "progress",
                            "data": {
                                "chunk_index": chunk_index,
                                "uploaded_chunks": len(received_chunks),
                                "total_chunks": upload_session.total_chunks,
                                "progress": progress
                            }
                        }))

                        # Check if all chunks received
                        if len(received_chunks) == upload_session.total_chunks:
                            # Write file
                            async with aiofiles.open(file_path, 'wb') as f:
                                for i in range(upload_session.total_chunks):
                                    if i in chunk_data:
                                        await f.write(chunk_data[i])

                            # Create video record
                            video = Video(
                                user_id=upload_session.user_id,
                                filename=unique_filename,
                                original_filename=upload_session.filename,
                                file_path=file_path,
                                file_size=upload_session.file_size,
                                mime_type="video/mp4",  # Default, will be updated by analysis
                                upload_status="completed"
                            )

                            db.add(video)

                            # Update session status
                            upload_session.status = "completed"
                            await db.commit()
                            await db.refresh(video)

                            # Send completion message
                            await websocket.send_text(json.dumps({
                                "type": "upload_complete",
                                "data": {
                                    "video_id": str(video.id),
                                    "filename": unique_filename,
                                    "message": "Upload completed successfully"
                                }
                            }))

                            # Trigger video analysis
                            await redis_client.publish("video_analysis_queue", {
                                "video_id": str(video.id),
                                "analysis_type": "metadata_extraction"
                            })

                            break

                    elif message["type"] == "cancel":
                        # Cancel upload
                        upload_session.status = "cancelled"
                        await db.commit()

                        await websocket.send_text(json.dumps({
                            "type": "upload_cancelled",
                            "message": "Upload cancelled"
                        }))
                        break

                except WebSocketDisconnect:
                    logger.info(f"WebSocket disconnected for session: {session_token}")
                    break
                except Exception as e:
                    logger.error(f"WebSocket error: {e}")
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": str(e)
                    }))
                    break

    except Exception as e:
        logger.error(f"WebSocket endpoint error: {e}")
    finally:
        manager.disconnect(client_id)

@websocket_router.websocket("/notifications/{user_token}")
async def websocket_notifications(websocket: WebSocket, user_token: str):
    # Verify JWT token
    try:
        user_id = verify_token(user_token)
    except:
        await websocket.close(code=4001)
        return

    client_id = f"notifications_{user_id}"
    await manager.connect(websocket, client_id)

    try:
        # Subscribe to user-specific notifications
        pubsub = await redis_client.subscribe(f"user_notifications:{user_id}")

        await websocket.send_text(json.dumps({
            "type": "connected",
            "message": "Connected to notifications"
        }))

        # Listen for messages
        while True:
            try:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message:
                    notification_data = json.loads(message["data"])
                    await websocket.send_text(json.dumps({
                        "type": "notification",
                        "data": notification_data
                    }))

                # Check for WebSocket messages (like ping/pong)
                try:
                    data = await websocket.receive_text()
                    message = json.loads(data)
                    if message.get("type") == "ping":
                        await websocket.send_text(json.dumps({"type": "pong"}))
                except:
                    pass

            except WebSocketDisconnect:
                logger.info(f"Notifications WebSocket disconnected for user: {user_id}")
                break
            except Exception as e:
                logger.error(f"Notifications WebSocket error: {e}")
                break

    except Exception as e:
        logger.error(f"Notifications WebSocket endpoint error: {e}")
    finally:
        manager.disconnect(client_id)
        if 'pubsub' in locals():
            await pubsub.unsubscribe(f"user_notifications:{user_id}")
            await pubsub.close()