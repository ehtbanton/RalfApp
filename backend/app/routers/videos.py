from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from typing import Optional
from ..database import get_db
from ..models import Video, VideoAnalysis
from ..schemas import VideoResponse, VideoListResponse
from ..auth import get_current_user
from uuid import UUID

router = APIRouter()

@router.get("/", response_model=VideoListResponse)
async def list_videos(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    status: Optional[str] = Query(None),
    current_user_id: UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Build query
    query = select(Video).where(Video.user_id == current_user_id)

    if status:
        query = query.where(Video.upload_status == status)

    # Get total count
    count_query = select(func.count(Video.id)).where(Video.user_id == current_user_id)
    if status:
        count_query = count_query.where(Video.upload_status == status)

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Get paginated results
    query = query.order_by(desc(Video.created_at))
    query = query.offset((page - 1) * per_page).limit(per_page)

    result = await db.execute(query)
    videos = result.scalars().all()

    return VideoListResponse(
        videos=videos,
        total=total,
        page=page,
        per_page=per_page
    )

@router.get("/{video_id}", response_model=VideoResponse)
async def get_video(
    video_id: UUID,
    current_user_id: UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Video).where(
            Video.id == video_id,
            Video.user_id == current_user_id
        )
    )
    video = result.scalars().first()

    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )

    return video

@router.delete("/{video_id}")
async def delete_video(
    video_id: UUID,
    current_user_id: UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Video).where(
            Video.id == video_id,
            Video.user_id == current_user_id
        )
    )
    video = result.scalars().first()

    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )

    await db.delete(video)
    await db.commit()

    return {"message": "Video deleted successfully"}

@router.get("/{video_id}/analyses")
async def get_video_analyses(
    video_id: UUID,
    current_user_id: UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # First check if video belongs to user
    video_result = await db.execute(
        select(Video).where(
            Video.id == video_id,
            Video.user_id == current_user_id
        )
    )
    video = video_result.scalars().first()

    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )

    # Get analyses
    result = await db.execute(
        select(VideoAnalysis).where(VideoAnalysis.video_id == video_id)
        .order_by(desc(VideoAnalysis.created_at))
    )
    analyses = result.scalars().all()

    return analyses