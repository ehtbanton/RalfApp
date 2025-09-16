from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..database import get_db
from ..models import Video, VideoAnalysis
from ..schemas import VideoAnalysisCreate, VideoAnalysisResponse
from ..auth import get_current_user
from ..tasks import analyze_video
from uuid import UUID

router = APIRouter()

@router.post("/{video_id}", response_model=VideoAnalysisResponse)
async def create_analysis(
    video_id: UUID,
    analysis_data: VideoAnalysisCreate,
    background_tasks: BackgroundTasks,
    current_user_id: UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Check if video exists and belongs to user
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

    if video.upload_status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Video upload is not completed"
        )

    # Check if analysis of this type already exists and is pending/running
    existing_result = await db.execute(
        select(VideoAnalysis).where(
            VideoAnalysis.video_id == video_id,
            VideoAnalysis.analysis_type == analysis_data.analysis_type,
            VideoAnalysis.status.in_(["pending", "running"])
        )
    )
    existing_analysis = existing_result.scalars().first()

    if existing_analysis:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Analysis of type '{analysis_data.analysis_type}' is already pending or running"
        )

    # Create analysis record
    analysis = VideoAnalysis(
        video_id=video_id,
        analysis_type=analysis_data.analysis_type,
        status="pending"
    )

    db.add(analysis)
    await db.commit()
    await db.refresh(analysis)

    # Queue analysis task
    background_tasks.add_task(analyze_video, str(analysis.id))

    return analysis

@router.get("/{analysis_id}", response_model=VideoAnalysisResponse)
async def get_analysis(
    analysis_id: UUID,
    current_user_id: UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Get analysis with video to check ownership
    result = await db.execute(
        select(VideoAnalysis, Video).join(Video).where(
            VideoAnalysis.id == analysis_id,
            Video.user_id == current_user_id
        )
    )
    analysis_video = result.first()

    if not analysis_video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found"
        )

    analysis = analysis_video[0]
    return analysis

@router.delete("/{analysis_id}")
async def delete_analysis(
    analysis_id: UUID,
    current_user_id: UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Get analysis with video to check ownership
    result = await db.execute(
        select(VideoAnalysis, Video).join(Video).where(
            VideoAnalysis.id == analysis_id,
            Video.user_id == current_user_id
        )
    )
    analysis_video = result.first()

    if not analysis_video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found"
        )

    analysis = analysis_video[0]

    if analysis.status in ["pending", "running"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete running or pending analysis"
        )

    await db.delete(analysis)
    await db.commit()

    return {"message": "Analysis deleted successfully"}