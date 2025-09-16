import React from 'react';
import { useQuery } from 'react-query';
import { videosApi } from '../services/api';
import { ChartBarIcon, EyeIcon, ClockIcon, CpuChipIcon } from '@heroicons/react/24/outline';
import { formatBytes } from '../utils/formatters';

const AnalyticsPage = () => {
  const { data: videosData } = useQuery(
    ['videos-analytics'],
    () => videosApi.list({ per_page: 100 }),
    {
      select: (data) => data.data.videos,
    }
  );

  const videos = videosData || [];

  // Calculate statistics
  const totalVideos = videos.length;
  const completedVideos = videos.filter(v => v.upload_status === 'completed').length;
  const totalSize = videos.reduce((acc, video) => acc + video.file_size, 0);
  const totalDuration = videos.reduce((acc, video) => acc + (video.duration || 0), 0);

  const formatDuration = (seconds) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    if (hours > 0) {
      return `${hours}h ${minutes}m`;
    }
    return `${minutes}m`;
  };

  // Video format distribution
  const formatDistribution = videos.reduce((acc, video) => {
    const extension = video.original_filename.split('.').pop().toLowerCase();
    acc[extension] = (acc[extension] || 0) + 1;
    return acc;
  }, {});

  // Upload status distribution
  const statusDistribution = videos.reduce((acc, video) => {
    acc[video.upload_status] = (acc[video.upload_status] || 0) + 1;
    return acc;
  }, {});

  // Resolution distribution
  const resolutionDistribution = videos.reduce((acc, video) => {
    if (video.width && video.height) {
      const resolution = `${video.width}×${video.height}`;
      acc[resolution] = (acc[resolution] || 0) + 1;
    }
    return acc;
  }, {});

  const StatCard = ({ title, value, icon: Icon, color = "blue" }) => (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center">
        <div className={`p-3 rounded-md bg-${color}-100`}>
          <Icon className={`h-6 w-6 text-${color}-600`} />
        </div>
        <div className="ml-4">
          <p className="text-sm font-medium text-gray-600">{title}</p>
          <p className="text-2xl font-semibold text-gray-900">{value}</p>
        </div>
      </div>
    </div>
  );

  const DistributionChart = ({ title, data, color = "blue" }) => (
    <div className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">{title}</h3>
      <div className="space-y-3">
        {Object.entries(data).map(([key, count]) => {
          const percentage = totalVideos > 0 ? (count / totalVideos) * 100 : 0;
          return (
            <div key={key}>
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">{key}</span>
                <span className="font-medium">{count} ({percentage.toFixed(1)}%)</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className={`bg-${color}-600 h-2 rounded-full`}
                  style={{ width: `${percentage}%` }}
                ></div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Analytics</h1>
          <p className="mt-2 text-gray-600">
            Insights and statistics about your video collection
          </p>
        </div>

        {/* Overview Stats */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <StatCard
            title="Total Videos"
            value={totalVideos}
            icon={EyeIcon}
            color="blue"
          />
          <StatCard
            title="Completed"
            value={completedVideos}
            icon={ChartBarIcon}
            color="green"
          />
          <StatCard
            title="Total Size"
            value={formatBytes(totalSize)}
            icon={CpuChipIcon}
            color="purple"
          />
          <StatCard
            title="Total Duration"
            value={formatDuration(totalDuration)}
            icon={ClockIcon}
            color="yellow"
          />
        </div>

        {/* Distribution Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          <DistributionChart
            title="Upload Status"
            data={statusDistribution}
            color="blue"
          />
          <DistributionChart
            title="Video Formats"
            data={formatDistribution}
            color="green"
          />
        </div>

        {/* Resolution Distribution */}
        {Object.keys(resolutionDistribution).length > 0 && (
          <div className="mb-8">
            <DistributionChart
              title="Video Resolutions"
              data={resolutionDistribution}
              color="purple"
            />
          </div>
        )}

        {/* Recent Activity */}
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900">Recent Videos</h3>
          </div>
          <div className="divide-y divide-gray-200">
            {videos.slice(0, 10).map((video) => (
              <div key={video.id} className="px-6 py-4">
                <div className="flex items-center justify-between">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {video.original_filename}
                    </p>
                    <div className="flex items-center text-sm text-gray-500 space-x-4">
                      <span>{formatBytes(video.file_size)}</span>
                      {video.duration && <span>{formatDuration(video.duration)}</span>}
                      {video.width && video.height && (
                        <span>{video.width}×{video.height}</span>
                      )}
                    </div>
                  </div>
                  <div className="flex-shrink-0">
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
              </div>
            ))}
          </div>
        </div>

        {/* Analysis Summary */}
        <div className="mt-8 bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Analysis Capabilities
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="text-center p-4 border border-gray-200 rounded-lg">
              <div className="text-2xl font-bold text-blue-600 mb-2">
                PyTorch
              </div>
              <p className="text-sm text-gray-600">
                Deep learning analysis with GPU acceleration
              </p>
            </div>
            <div className="text-center p-4 border border-gray-200 rounded-lg">
              <div className="text-2xl font-bold text-green-600 mb-2">
                OpenCV
              </div>
              <p className="text-sm text-gray-600">
                Computer vision and video processing
              </p>
            </div>
            <div className="text-center p-4 border border-gray-200 rounded-lg">
              <div className="text-2xl font-bold text-purple-600 mb-2">
                FFmpeg
              </div>
              <p className="text-sm text-gray-600">
                Video metadata extraction and conversion
              </p>
            </div>
            <div className="text-center p-4 border border-gray-200 rounded-lg">
              <div className="text-2xl font-bold text-yellow-600 mb-2">
                Real-time
              </div>
              <p className="text-sm text-gray-600">
                Live processing with WebSocket updates
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AnalyticsPage;