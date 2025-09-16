import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';
const WS_BASE_URL = process.env.REACT_APP_WS_URL || 'ws://localhost:8000/ws';

// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Token management
const getToken = () => localStorage.getItem('access_token');
const setToken = (token) => localStorage.setItem('access_token', token);
const removeToken = () => localStorage.removeItem('access_token');

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = getToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor to handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      removeToken();
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Auth API
export const authApi = {
  register: (userData) => api.post('/auth/register', userData),
  login: (credentials) => api.post('/auth/login', credentials),
  getCurrentUser: () => api.get('/auth/me'),
};

// Videos API
export const videosApi = {
  list: (params = {}) => api.get('/videos', { params }),
  get: (id) => api.get(`/videos/${id}`),
  delete: (id) => api.delete(`/videos/${id}`),
  getAnalyses: (id) => api.get(`/videos/${id}/analyses`),
};

// Upload API
export const uploadApi = {
  createSession: (data) => api.post('/upload/session', data),
  getSession: (sessionToken) => api.get(`/upload/session/${sessionToken}`),
  simpleUpload: (file, onProgress) => {
    const formData = new FormData();
    formData.append('file', file);

    return api.post('/upload/simple', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: onProgress,
    });
  },
  cancelSession: (sessionToken) => api.delete(`/upload/session/${sessionToken}`),
};

// Analysis API
export const analysisApi = {
  create: (videoId, data) => api.post(`/analysis/${videoId}`, data),
  get: (analysisId) => api.get(`/analysis/${analysisId}`),
  delete: (analysisId) => api.delete(`/analysis/${analysisId}`),
};

// WebSocket utilities
export const createWebSocketUrl = (endpoint, token = null) => {
  const baseUrl = WS_BASE_URL.replace('http://', 'ws://').replace('https://', 'wss://');
  return token ? `${baseUrl}${endpoint}/${token}` : `${baseUrl}${endpoint}`;
};

// WebSocket upload
export class WebSocketUpload {
  constructor(sessionToken) {
    this.sessionToken = sessionToken;
    this.ws = null;
    this.onProgress = null;
    this.onComplete = null;
    this.onError = null;
  }

  connect() {
    return new Promise((resolve, reject) => {
      const wsUrl = createWebSocketUrl('/upload', this.sessionToken);
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        console.log('WebSocket connected for upload');
        resolve();
      };

      this.ws.onmessage = (event) => {
        const message = JSON.parse(event.data);
        this.handleMessage(message);
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        if (this.onError) this.onError(error);
        reject(error);
      };

      this.ws.onclose = () => {
        console.log('WebSocket closed');
      };
    });
  }

  handleMessage(message) {
    switch (message.type) {
      case 'session_info':
        console.log('Session info received:', message.data);
        break;
      case 'progress':
        if (this.onProgress) {
          this.onProgress(message.data);
        }
        break;
      case 'upload_complete':
        if (this.onComplete) {
          this.onComplete(message.data);
        }
        break;
      case 'error':
        if (this.onError) {
          this.onError(new Error(message.message));
        }
        break;
      default:
        console.log('Unknown message type:', message.type);
    }
  }

  uploadChunk(chunkIndex, chunkData) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      const message = {
        type: 'chunk',
        chunk_index: chunkIndex,
        chunk_data: chunkData, // Base64 encoded
      };
      this.ws.send(JSON.stringify(message));
    }
  }

  cancel() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      const message = { type: 'cancel' };
      this.ws.send(JSON.stringify(message));
    }
  }

  close() {
    if (this.ws) {
      this.ws.close();
    }
  }
}

// Notifications WebSocket
export class NotificationsWebSocket {
  constructor(token) {
    this.token = token;
    this.ws = null;
    this.onNotification = null;
    this.onConnect = null;
    this.onDisconnect = null;
  }

  connect() {
    return new Promise((resolve, reject) => {
      const wsUrl = createWebSocketUrl('/notifications', this.token);
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        console.log('Notifications WebSocket connected');
        if (this.onConnect) this.onConnect();
        resolve();
      };

      this.ws.onmessage = (event) => {
        const message = JSON.parse(event.data);
        if (message.type === 'notification' && this.onNotification) {
          this.onNotification(message.data);
        }
      };

      this.ws.onerror = (error) => {
        console.error('Notifications WebSocket error:', error);
        reject(error);
      };

      this.ws.onclose = () => {
        console.log('Notifications WebSocket closed');
        if (this.onDisconnect) this.onDisconnect();
      };
    });
  }

  sendPing() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: 'ping' }));
    }
  }

  close() {
    if (this.ws) {
      this.ws.close();
    }
  }
}

export { api, getToken, setToken, removeToken };