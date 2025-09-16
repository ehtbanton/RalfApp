from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..database import get_db
from ..models import UploadSession, Video
from ..schemas import UploadSessionCreate, UploadSessionResponse
from ..auth import get_current_user
from datetime import datetime, timedelta
import secrets
import os
import aiofiles
from uuid import UUID

router = APIRouter()

@router.post("/session", response_model=UploadSessionResponse)
async def create_upload_session(
    session_data: UploadSessionCreate,
    current_user_id: UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Calculate total chunks
    total_chunks = (session_data.file_size + session_data.chunk_size - 1) // session_data.chunk_size

    # Generate session token
    session_token = secrets.token_urlsafe(32)

    # Create upload session
    upload_session = UploadSession(
        user_id=current_user_id,
        filename=session_data.filename,
        file_size=session_data.file_size,
        chunk_size=session_data.chunk_size,
        total_chunks=total_chunks,
        session_token=session_token,
        expires_at=datetime.utcnow() + timedelta(hours=24)
    )

    db.add(upload_session)
    await db.commit()
    await db.refresh(upload_session)

    return upload_session

@router.get("/session/{session_token}", response_model=UploadSessionResponse)
async def get_upload_session(
    session_token: str,
    current_user_id: UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(UploadSession).where(
            UploadSession.session_token == session_token,
            UploadSession.user_id == current_user_id
        )
    )
    session = result.scalars().first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upload session not found"
        )

    if session.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload session expired"
        )

    return session

@router.post("/simple")
async def simple_upload(
    file: UploadFile = File(...),
    current_user_id: UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Validate file type
    if not file.content_type.startswith('video/'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only video files are allowed"
        )

    # Generate unique filename
    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{secrets.token_urlsafe(16)}{file_extension}"

    # Create storage path
    storage_path = os.getenv("VIDEO_STORAGE_PATH", "/app/storage")
    user_dir = os.path.join(storage_path, str(current_user_id))
    os.makedirs(user_dir, exist_ok=True)

    file_path = os.path.join(user_dir, unique_filename)

    # Save file
    async with aiofiles.open(file_path, 'wb') as f:
        content = await file.read()
        await f.write(content)

    # Create video record
    video = Video(
        user_id=current_user_id,
        filename=unique_filename,
        original_filename=file.filename,
        file_path=file_path,
        file_size=len(content),
        mime_type=file.content_type,
        upload_status="completed"
    )

    db.add(video)
    await db.commit()
    await db.refresh(video)

    return {
        "message": "File uploaded successfully",
        "video_id": video.id,
        "filename": unique_filename
    }

@router.delete("/session/{session_token}")
async def cancel_upload_session(
    session_token: str,
    current_user_id: UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(UploadSession).where(
            UploadSession.session_token == session_token,
            UploadSession.user_id == current_user_id
        )
    )
    session = result.scalars().first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upload session not found"
        )

    session.status = "cancelled"
    await db.commit()

    return {"message": "Upload session cancelled"}