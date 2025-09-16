from celery import Celery
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from .database import async_session
from .models import VideoAnalysis, Video
from .redis_client import redis_client
import cv2
import torch
import torchvision.transforms as transforms
from torchvision.models import resnet50
import ffmpeg
import os
import json
import time
import logging
from datetime import datetime
from typing import Dict, Any
import numpy as np
from PIL import Image
import asyncio
from uuid import UUID

logger = logging.getLogger(__name__)

# Celery configuration
celery_app = Celery(
    "video_analysis_worker",
    broker=os.getenv("REDIS_URL", "redis://localhost:6379"),
    backend=os.getenv("REDIS_URL", "redis://localhost:6379")
)

# PyTorch model initialization
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
logger.info(f"Using device: {device}")

# Load pre-trained model for video analysis
model = resnet50(pretrained=True)
model.eval()
model.to(device)

# Image preprocessing for PyTorch
preprocess = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

class VideoAnalyzer:
    def __init__(self):
        self.supported_formats = ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv']

    async def extract_metadata(self, video_path: str) -> Dict[str, Any]:
        """Extract basic video metadata using ffmpeg"""
        try:
            probe = ffmpeg.probe(video_path)
            video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)

            if not video_stream:
                raise ValueError("No video stream found")

            metadata = {
                'duration': float(probe['format']['duration']),
                'file_size': int(probe['format']['size']),
                'bitrate': int(probe['format']['bit_rate']),
                'width': int(video_stream['width']),
                'height': int(video_stream['height']),
                'fps': eval(video_stream['r_frame_rate']),
                'codec': video_stream['codec_name'],
                'format': probe['format']['format_name']
            }

            return metadata

        except Exception as e:
            logger.error(f"Metadata extraction error: {e}")
            raise

    async def analyze_content(self, video_path: str, analysis_type: str) -> Dict[str, Any]:
        """Analyze video content using PyTorch models"""
        try:
            cap = cv2.VideoCapture(video_path)

            if not cap.isOpened():
                raise ValueError("Could not open video file")

            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)

            # Sample frames for analysis (every second)
            frame_interval = max(1, int(fps))
            sampled_frames = []
            frame_features = []

            frame_count = 0
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                if frame_count % frame_interval == 0:
                    # Convert BGR to RGB
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    pil_image = Image.fromarray(frame_rgb)

                    # Preprocess for PyTorch
                    input_tensor = preprocess(pil_image)
                    input_batch = input_tensor.unsqueeze(0).to(device)

                    # Extract features using ResNet
                    with torch.no_grad():
                        features = model(input_batch)
                        frame_features.append(features.cpu().numpy())

                    sampled_frames.append(frame_count / fps)  # timestamp

                frame_count += 1

            cap.release()

            if analysis_type == "scene_detection":
                return await self._analyze_scenes(frame_features, sampled_frames)
            elif analysis_type == "object_detection":
                return await self._detect_objects(video_path)
            elif analysis_type == "motion_analysis":
                return await self._analyze_motion(video_path)
            elif analysis_type == "quality_assessment":
                return await self._assess_quality(frame_features, video_path)
            else:
                return {
                    "analysis_type": analysis_type,
                    "total_frames": total_frames,
                    "sampled_frames": len(sampled_frames),
                    "avg_features": np.mean(frame_features, axis=0).tolist() if frame_features else []
                }

        except Exception as e:
            logger.error(f"Content analysis error: {e}")
            raise

    async def _analyze_scenes(self, frame_features: list, timestamps: list) -> Dict[str, Any]:
        """Detect scene changes using feature similarity"""
        if len(frame_features) < 2:
            return {"scenes": [], "scene_count": 0}

        scene_changes = []
        threshold = 0.7  # Similarity threshold

        for i in range(1, len(frame_features)):
            # Calculate cosine similarity between consecutive frames
            feat1 = frame_features[i-1].flatten()
            feat2 = frame_features[i].flatten()

            similarity = np.dot(feat1, feat2) / (np.linalg.norm(feat1) * np.linalg.norm(feat2))

            if similarity < threshold:
                scene_changes.append({
                    "timestamp": timestamps[i],
                    "similarity_score": float(similarity)
                })

        return {
            "scene_changes": scene_changes,
            "scene_count": len(scene_changes) + 1,
            "analysis_type": "scene_detection"
        }

    async def _detect_objects(self, video_path: str) -> Dict[str, Any]:
        """Basic object detection placeholder - can be extended with YOLO or other models"""
        # This is a placeholder for object detection
        # In a real implementation, you would use YOLO, SSD, or other object detection models
        return {
            "analysis_type": "object_detection",
            "objects_detected": [],
            "confidence_threshold": 0.5,
            "note": "Object detection requires additional models (YOLO, SSD, etc.)"
        }

    async def _analyze_motion(self, video_path: str) -> Dict[str, Any]:
        """Analyze motion in the video"""
        try:
            cap = cv2.VideoCapture(video_path)

            # Read first frame
            ret, frame1 = cap.read()
            if not ret:
                return {"error": "Could not read video frames"}

            prvs = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
            motion_data = []

            while True:
                ret, frame2 = cap.read()
                if not ret:
                    break

                next_frame = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)

                # Calculate optical flow
                flow = cv2.calcOpticalFlowPyrLK(prvs, next_frame, None, None)

                # Calculate motion magnitude
                if flow is not None:
                    mag, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])
                    motion_magnitude = np.mean(mag)
                    motion_data.append(float(motion_magnitude))

                prvs = next_frame

            cap.release()

            return {
                "analysis_type": "motion_analysis",
                "avg_motion": float(np.mean(motion_data)) if motion_data else 0,
                "max_motion": float(np.max(motion_data)) if motion_data else 0,
                "motion_variance": float(np.var(motion_data)) if motion_data else 0,
                "frame_count": len(motion_data)
            }

        except Exception as e:
            logger.error(f"Motion analysis error: {e}")
            return {"error": str(e), "analysis_type": "motion_analysis"}

    async def _assess_quality(self, frame_features: list, video_path: str) -> Dict[str, Any]:
        """Assess video quality metrics"""
        try:
            # Basic quality metrics
            cap = cv2.VideoCapture(video_path)
            sharpness_scores = []
            brightness_scores = []

            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                # Convert to grayscale for analysis
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                # Calculate sharpness using Laplacian variance
                sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
                sharpness_scores.append(sharpness)

                # Calculate brightness
                brightness = np.mean(gray)
                brightness_scores.append(brightness)

            cap.release()

            return {
                "analysis_type": "quality_assessment",
                "avg_sharpness": float(np.mean(sharpness_scores)) if sharpness_scores else 0,
                "avg_brightness": float(np.mean(brightness_scores)) if brightness_scores else 0,
                "sharpness_std": float(np.std(sharpness_scores)) if sharpness_scores else 0,
                "brightness_std": float(np.std(brightness_scores)) if brightness_scores else 0,
                "frame_count": len(sharpness_scores)
            }

        except Exception as e:
            logger.error(f"Quality assessment error: {e}")
            return {"error": str(e), "analysis_type": "quality_assessment"}

# Initialize analyzer
video_analyzer = VideoAnalyzer()

@celery_app.task(bind=True, max_retries=3)
def analyze_video(self, analysis_id: str):
    """Celery task for video analysis"""
    return asyncio.run(_analyze_video_async(self, analysis_id))

async def _analyze_video_async(task, analysis_id: str):
    start_time = time.time()

    try:
        # Get analysis record
        async with async_session() as db:
            result = await db.execute(
                select(VideoAnalysis, Video)
                .join(Video)
                .where(VideoAnalysis.id == UUID(analysis_id))
            )
            analysis_video = result.first()

            if not analysis_video:
                logger.error(f"Analysis {analysis_id} not found")
                return {"error": "Analysis not found"}

            analysis, video = analysis_video

            # Update status to running
            analysis.status = "running"
            analysis.worker_id = task.request.id
            await db.commit()

            # Notify user about analysis start
            await redis_client.publish(f"user_notifications:{video.user_id}", {
                "type": "analysis_started",
                "video_id": str(video.id),
                "analysis_id": analysis_id,
                "analysis_type": analysis.analysis_type
            })

            try:
                # Perform analysis based on type
                if analysis.analysis_type == "metadata_extraction":
                    result_data = await video_analyzer.extract_metadata(video.file_path)

                    # Update video metadata
                    video.duration = result_data.get('duration')
                    video.width = result_data.get('width')
                    video.height = result_data.get('height')
                    video.fps = result_data.get('fps')
                    video.codec = result_data.get('codec')
                    video.bitrate = result_data.get('bitrate')

                else:
                    # Content analysis
                    result_data = await video_analyzer.analyze_content(
                        video.file_path,
                        analysis.analysis_type
                    )

                # Update analysis with results
                processing_time = time.time() - start_time
                analysis.result = result_data
                analysis.status = "completed"
                analysis.completed_at = datetime.utcnow()
                analysis.processing_time = processing_time

                await db.commit()

                # Cache result in Redis
                await redis_client.cache_analysis_result(analysis_id, result_data)

                # Notify user about completion
                await redis_client.publish(f"user_notifications:{video.user_id}", {
                    "type": "analysis_completed",
                    "video_id": str(video.id),
                    "analysis_id": analysis_id,
                    "analysis_type": analysis.analysis_type,
                    "processing_time": processing_time
                })

                logger.info(f"Analysis {analysis_id} completed in {processing_time:.2f} seconds")
                return {"status": "completed", "processing_time": processing_time}

            except Exception as e:
                # Update analysis with error
                analysis.status = "failed"
                analysis.error_message = str(e)
                analysis.completed_at = datetime.utcnow()
                analysis.processing_time = time.time() - start_time

                await db.commit()

                # Notify user about failure
                await redis_client.publish(f"user_notifications:{video.user_id}", {
                    "type": "analysis_failed",
                    "video_id": str(video.id),
                    "analysis_id": analysis_id,
                    "analysis_type": analysis.analysis_type,
                    "error": str(e)
                })

                logger.error(f"Analysis {analysis_id} failed: {e}")
                raise

    except Exception as e:
        logger.error(f"Task execution error: {e}")
        raise task.retry(countdown=60, exc=e)