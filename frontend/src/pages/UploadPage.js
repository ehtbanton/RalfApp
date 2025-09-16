import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import UploadDropzone from '../components/VideoUpload/UploadDropzone';
import { toast } from 'react-toastify';

const UploadPage = () => {
  const navigate = useNavigate();
  const [uploadHistory, setUploadHistory] = useState([]);

  const handleUploadComplete = (uploadData) => {
    const newUpload = {
      id: uploadData.video_id || Date.now(),
      filename: uploadData.filename || uploadData.message,
      timestamp: new Date(),
      ...uploadData
    };

    setUploadHistory(prev => [newUpload, ...prev]);

    // Navigate to videos page after a short delay
    setTimeout(() => {
      navigate('/videos');
    }, 2000);
  };

  const handleUploadProgress = (progress) => {
    // Handle progress updates if needed
    console.log('Upload progress:', progress);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-gray-900">Upload Video</h1>
          <p className="mt-2 text-gray-600">
            Upload your videos for storage and analysis
          </p>
        </div>

        {/* Upload Component */}
        <div className="mb-8">
          <UploadDropzone
            onUploadComplete={handleUploadComplete}
            onUploadProgress={handleUploadProgress}
          />
        </div>

        {/* Upload Instructions */}
        <div className="bg-white rounded-lg shadow p-6 mb-8">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Upload Instructions
          </h2>
          <div className="prose text-sm text-gray-600">
            <ul className="space-y-2">
              <li>• Supported formats: MP4, AVI, MOV, MKV, WebM, FLV</li>
              <li>• Maximum file size: 2GB</li>
              <li>• Use WebSocket upload for large files (recommended)</li>
              <li>• Videos are automatically analyzed after upload</li>
              <li>• You'll receive notifications when analysis completes</li>
            </ul>
          </div>
        </div>

        {/* Recent Uploads */}
        {uploadHistory.length > 0 && (
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              Recent Uploads
            </h2>
            <div className="space-y-3">
              {uploadHistory.map((upload) => (
                <div
                  key={upload.id}
                  className="flex items-center justify-between p-3 bg-green-50 border border-green-200 rounded-md"
                >
                  <div>
                    <p className="font-medium text-green-800">
                      {upload.filename}
                    </p>
                    <p className="text-sm text-green-600">
                      Uploaded successfully at {upload.timestamp.toLocaleTimeString()}
                    </p>
                  </div>
                  <div className="text-green-600">
                    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Available Analysis Types */}
        <div className="mt-8 bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Available Analysis Types
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="border border-gray-200 rounded-lg p-4">
              <h3 className="font-medium text-gray-900">Metadata Extraction</h3>
              <p className="text-sm text-gray-600 mt-1">
                Extract basic video information like duration, resolution, codec, and bitrate.
              </p>
            </div>
            <div className="border border-gray-200 rounded-lg p-4">
              <h3 className="font-medium text-gray-900">Scene Detection</h3>
              <p className="text-sm text-gray-600 mt-1">
                Automatically detect scene changes and transitions in your video.
              </p>
            </div>
            <div className="border border-gray-200 rounded-lg p-4">
              <h3 className="font-medium text-gray-900">Motion Analysis</h3>
              <p className="text-sm text-gray-600 mt-1">
                Analyze motion patterns and movement throughout the video.
              </p>
            </div>
            <div className="border border-gray-200 rounded-lg p-4">
              <h3 className="font-medium text-gray-900">Quality Assessment</h3>
              <p className="text-sm text-gray-600 mt-1">
                Assess video quality metrics like sharpness and brightness.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default UploadPage;