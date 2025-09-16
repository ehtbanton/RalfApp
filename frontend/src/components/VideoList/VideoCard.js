import React, { useState } from 'react';
import ReactPlayer from 'react-player';
import {
  PlayIcon,
  TrashIcon,
  ChartBarIcon,
  ClockIcon,
  EyeIcon,
} from '@heroicons/react/24/outline';
import { formatDistanceToNow, formatBytes } from '../../utils/formatters';
import { analysisApi, videosApi } from '../../services/api';
import { toast } from 'react-toastify';

const VideoCard = ({ video, onDelete, onAnalysisCreate }) => {
  const [showPlayer, setShowPlayer] = useState(false);
  const [analyzing, setAnalyzing] = useState({});
  const [deleting, setDeleting] = useState(false);

  const handleDelete = async () => {
    if (!window.confirm('Are you sure you want to delete this video?')) {
      return;
    }

    setDeleting(true);
    try {
      await videosApi.delete(video.id);
      toast.success('Video deleted successfully');
      if (onDelete) onDelete(video.id);
    } catch (error) {
      toast.error('Failed to delete video');
      console.error('Delete error:', error);
    } finally {
      setDeleting(false);
    }
  };

  const handleAnalyze = async (analysisType) => {
    setAnalyzing({ ...analyzing, [analysisType]: true });

    try {
      const response = await analysisApi.create(video.id, {
        analysis_type: analysisType
      });

      toast.success(`${analysisType} analysis started`);
      if (onAnalysisCreate) {
        onAnalysisCreate(response.data);
      }
    } catch (error) {
      toast.error(`Failed to start ${analysisType} analysis`);
      console.error('Analysis error:', error);
    } finally {
      setAnalyzing({ ...analyzing, [analysisType]: false });
    }
  };

  const getVideoUrl = () => {
    return `${process.env.REACT_APP_API_URL || 'http://localhost:8000'}/static/${video.user_id}/${video.filename}`;
  };

  const analysisTypes = [
    { key: 'metadata_extraction', label: 'Extract Metadata', description: 'Basic video information' },
    { key: 'scene_detection', label: 'Scene Detection', description: 'Detect scene changes' },
    { key: 'motion_analysis', label: 'Motion Analysis', description: 'Analyze motion patterns' },
    { key: 'quality_assessment', label: 'Quality Assessment', description: 'Assess video quality' },
  ];

  return (
    <div className="bg-white rounded-lg shadow-md overflow-hidden hover:shadow-lg transition-shadow">
      {/* Video Thumbnail/Player */}
      <div className="aspect-video bg-gray-100 relative">
        {showPlayer ? (
          <ReactPlayer
            url={getVideoUrl()}
            width="100%"
            height="100%"
            controls
            playing={false}
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-gray-100 to-gray-200">
            <button
              onClick={() => setShowPlayer(true)}
              className="group flex items-center justify-center w-16 h-16 bg-white bg-opacity-90 rounded-full hover:bg-opacity-100 transition-all"
            >
              <PlayIcon className="w-6 h-6 text-blue-600 ml-1 group-hover:scale-110 transition-transform" />
            </button>
          </div>
        )}

        {/* Upload Status Badge */}
        <div className="absolute top-2 left-2">
          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
            video.upload_status === 'completed'
              ? 'bg-green-100 text-green-800'
              : video.upload_status === 'uploading'
              ? 'bg-yellow-100 text-yellow-800'
              : 'bg-red-100 text-red-800'
          }`}>
            {video.upload_status}
          </span>
        </div>
      </div>

      {/* Video Info */}
      <div className="p-4">
        <div className="flex items-start justify-between mb-2">
          <h3 className="text-lg font-semibold text-gray-900 truncate" title={video.original_filename}>
            {video.original_filename}
          </h3>
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setShowPlayer(!showPlayer)}
              className="p-1 text-gray-500 hover:text-blue-600 transition-colors"
              title="Toggle player"
            >
              <EyeIcon className="w-4 h-4" />
            </button>
            <button
              onClick={handleDelete}
              disabled={deleting}
              className="p-1 text-gray-500 hover:text-red-600 transition-colors disabled:opacity-50"
              title="Delete video"
            >
              <TrashIcon className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Video Stats */}
        <div className="grid grid-cols-2 gap-4 text-sm text-gray-600 mb-4">
          <div>
            <span className="font-medium">Size:</span> {formatBytes(video.file_size)}
          </div>
          <div className="flex items-center">
            <ClockIcon className="w-4 h-4 mr-1" />
            {formatDistanceToNow(new Date(video.created_at))} ago
          </div>
          {video.duration && (
            <div>
              <span className="font-medium">Duration:</span> {Math.round(video.duration)}s
            </div>
          )}
          {video.width && video.height && (
            <div>
              <span className="font-medium">Resolution:</span> {video.width}×{video.height}
            </div>
          )}
        </div>

        {/* Analysis Actions */}
        <div className="border-t pt-4">
          <h4 className="text-sm font-medium text-gray-900 mb-3 flex items-center">
            <ChartBarIcon className="w-4 h-4 mr-2" />
            Analysis
          </h4>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {analysisTypes.map((analysis) => (
              <button
                key={analysis.key}
                onClick={() => handleAnalyze(analysis.key)}
                disabled={analyzing[analysis.key] || video.upload_status !== 'completed'}
                className="flex items-center justify-center px-3 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                title={analysis.description}
              >
                {analyzing[analysis.key] ? (
                  <>
                    <div className="spinner mr-2"></div>
                    Running...
                  </>
                ) : (
                  analysis.label
                )}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default VideoCard;