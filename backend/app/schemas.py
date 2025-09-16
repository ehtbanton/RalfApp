from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID

# User schemas
class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: UUID
    email: str
    username: str
    is_active: bool
    is_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

# Video schemas
class VideoCreate(BaseModel):
    filename: str
    original_filename: str
    file_size: int
    mime_type: str

class VideoResponse(BaseModel):
    id: UUID
    filename: str
    original_filename: str
    file_path: str
    file_size: int
    duration: Optional[float]
    width: Optional[int]
    height: Optional[int]
    fps: Optional[float]
    codec: Optional[str]
    bitrate: Optional[int]
    mime_type: str
    upload_status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class VideoListResponse(BaseModel):
    videos: List[VideoResponse]
    total: int
    page: int
    per_page: int

# Upload session schemas
class UploadSessionCreate(BaseModel):
    filename: str
    file_size: int
    chunk_size: int = 1048576  # 1MB default

class UploadSessionResponse(BaseModel):
    id: UUID
    filename: str
    file_size: int
    chunk_size: int
    total_chunks: int
    uploaded_chunks: int
    status: str
    session_token: str
    expires_at: datetime

    class Config:
        from_attributes = True

# Video analysis schemas
class VideoAnalysisCreate(BaseModel):
    analysis_type: str

class VideoAnalysisResponse(BaseModel):
    id: UUID
    video_id: UUID
    analysis_type: str
    status: str
    result: Optional[Dict[str, Any]]
    error_message: Optional[str]
    processing_time: Optional[float]
    worker_id: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True

# WebSocket message schemas
class WebSocketMessage(BaseModel):
    type: str
    data: Dict[str, Any]

class ChunkUploadMessage(BaseModel):
    session_token: str
    chunk_index: int
    chunk_data: str  # Base64 encoded chunk data