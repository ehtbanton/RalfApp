import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { CloudArrowUpIcon, XMarkIcon } from '@heroicons/react/24/outline';
import { uploadApi, WebSocketUpload } from '../../services/api';
import { toast } from 'react-toastify';

const UploadDropzone = ({ onUploadComplete, onUploadProgress }) => {
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadMethod, setUploadMethod] = useState('websocket'); // 'websocket' or 'simple'
  const [currentUpload, setCurrentUpload] = useState(null);

  const onDrop = useCallback(async (acceptedFiles) => {
    const file = acceptedFiles[0];
    if (!file) return;

    if (!file.type.startsWith('video/')) {
      toast.error('Please select a video file');
      return;
    }

    if (file.size > 2 * 1024 * 1024 * 1024) { // 2GB limit
      toast.error('File size must be less than 2GB');
      return;
    }

    setUploading(true);
    setUploadProgress(0);

    try {
      if (uploadMethod === 'simple') {
        await handleSimpleUpload(file);
      } else {
        await handleWebSocketUpload(file);
      }
    } catch (error) {
      console.error('Upload failed:', error);
      toast.error('Upload failed: ' + error.message);
    } finally {
      setUploading(false);
      setCurrentUpload(null);
    }
  }, [uploadMethod]);

  const handleSimpleUpload = async (file) => {
    try {
      const response = await uploadApi.simpleUpload(file, (progressEvent) => {
        const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        setUploadProgress(progress);
        if (onUploadProgress) onUploadProgress(progress);
      });

      toast.success('Video uploaded successfully!');
      if (onUploadComplete) {
        onUploadComplete(response.data);
      }
    } catch (error) {
      throw new Error(error.response?.data?.detail || 'Upload failed');
    }
  };

  const handleWebSocketUpload = async (file) => {
    try {
      // Create upload session
      const sessionResponse = await uploadApi.createSession({
        filename: file.name,
        file_size: file.size,
        chunk_size: 1048576, // 1MB chunks
      });

      const session = sessionResponse.data;
      const wsUpload = new WebSocketUpload(session.session_token);
      setCurrentUpload(wsUpload);

      // Set up event handlers
      wsUpload.onProgress = (progressData) => {
        const progress = progressData.progress;
        setUploadProgress(progress);
        if (onUploadProgress) onUploadProgress(progress);
      };

      wsUpload.onComplete = (completeData) => {
        toast.success('Video uploaded successfully!');
        if (onUploadComplete) {
          onUploadComplete(completeData);
        }
      };

      wsUpload.onError = (error) => {
        throw error;
      };

      // Connect WebSocket
      await wsUpload.connect();

      // Upload chunks
      const chunkSize = session.chunk_size;
      const totalChunks = Math.ceil(file.size / chunkSize);

      for (let i = 0; i < totalChunks; i++) {
        const start = i * chunkSize;
        const end = Math.min(start + chunkSize, file.size);
        const chunk = file.slice(start, end);

        // Convert chunk to base64
        const reader = new FileReader();
        await new Promise((resolve) => {
          reader.onload = () => {
            const base64 = reader.result.split(',')[1]; // Remove data:... prefix
            wsUpload.uploadChunk(i, base64);
            resolve();
          };
          reader.readAsDataURL(chunk);
        });

        // Small delay to prevent overwhelming the server
        await new Promise(resolve => setTimeout(resolve, 10));
      }

    } catch (error) {
      throw new Error(error.message || 'WebSocket upload failed');
    }
  };

  const cancelUpload = () => {
    if (currentUpload) {
      currentUpload.cancel();
      currentUpload.close();
      setCurrentUpload(null);
    }
    setUploading(false);
    setUploadProgress(0);
    toast.info('Upload cancelled');
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'video/*': ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv']
    },
    maxFiles: 1,
    disabled: uploading,
  });

  return (
    <div className="w-full max-w-2xl mx-auto">
      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Upload Method
        </label>
        <select
          value={uploadMethod}
          onChange={(e) => setUploadMethod(e.target.value)}
          disabled={uploading}
          className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
        >
          <option value="websocket">WebSocket Upload (Chunked)</option>
          <option value="simple">Simple Upload</option>
        </select>
      </div>

      <div
        {...getRootProps()}
        className={`relative border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
          isDragActive
            ? 'border-blue-500 bg-blue-50'
            : uploading
            ? 'border-gray-300 bg-gray-50 cursor-not-allowed'
            : 'border-gray-300 hover:border-blue-500 hover:bg-blue-50 cursor-pointer'
        }`}
      >
        <input {...getInputProps()} />

        {uploading ? (
          <div className="space-y-4">
            <div className="spinner mx-auto"></div>
            <p className="text-lg font-medium text-gray-900">
              Uploading video... {Math.round(uploadProgress)}%
            </p>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-blue-600 h-2 rounded-full progress-bar"
                style={{ width: `${uploadProgress}%` }}
              ></div>
            </div>
            <button
              onClick={cancelUpload}
              className="inline-flex items-center px-3 py-2 border border-red-300 shadow-sm text-sm leading-4 font-medium rounded-md text-red-700 bg-white hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
            >
              <XMarkIcon className="h-4 w-4 mr-2" />
              Cancel Upload
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            <CloudArrowUpIcon className="mx-auto h-12 w-12 text-gray-400" />
            <div>
              <p className="text-lg font-medium text-gray-900">
                {isDragActive
                  ? 'Drop the video file here...'
                  : 'Drag & drop a video file here, or click to select'}
              </p>
              <p className="text-sm text-gray-600 mt-2">
                Supported formats: MP4, AVI, MOV, MKV, WebM, FLV (Max 2GB)
              </p>
            </div>
          </div>
        )}
      </div>

      <div className="mt-4 text-sm text-gray-500">
        <p>
          <strong>WebSocket Upload:</strong> Uploads large files in chunks with progress tracking and resume capability.
        </p>
        <p>
          <strong>Simple Upload:</strong> Direct upload for smaller files.
        </p>
      </div>
    </div>
  );
};

export default UploadDropzone;