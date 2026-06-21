import React, { useState, useRef } from 'react';
import './VideoUpload.css';
import { Upload, Youtube, Link, CheckCircle, XCircle, Loader, FileVideo, Trash2 } from 'lucide-react';

const API_BASE = 'http://localhost:8000';

interface UploadJob {
  job_id: string;
  status: string;
  progress: number;
  message: string;
  camera_id: string;
  video_source: string;
  started_at?: number;
  completed_at?: number;
  results?: {
    violations_detected: number;
    camera_id: string;
    evidence_folder: string;
  };
}

type UploadMethod = 'file' | 'url';

function VideoUpload() {
  const [uploadMethod, setUploadMethod] = useState<UploadMethod>('file');
  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [videoUrl, setVideoUrl] = useState('');
  const [cameraId, setCameraId] = useState('upload_cam_01');
  const [skipFrames, setSkipFrames] = useState(3);
  const [maxFrames, setMaxFrames] = useState<number | undefined>(undefined);
  const [uploading, setUploading] = useState(false);
  const [jobs, setJobs] = useState<UploadJob[]>([]);
  
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Drag and drop handlers
  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      if (isValidVideoFile(file)) {
        setSelectedFile(file);
      } else {
        alert('Please upload a valid video file (MP4, AVI, MOV, MKV, WEBM)');
      }
    }
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      if (isValidVideoFile(file)) {
        setSelectedFile(file);
      } else {
        alert('Please upload a valid video file (MP4, AVI, MOV, MKV, WEBM)');
      }
    }
  };

  const isValidVideoFile = (file: File) => {
    const validExtensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm'];
    const fileName = file.name.toLowerCase();
    return validExtensions.some(ext => fileName.endsWith(ext));
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024 * 1024) {
      return `${(bytes / 1024).toFixed(2)} KB`;
    }
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  // Upload file
  const handleFileUpload = async () => {
    if (!selectedFile) return;

    setUploading(true);

    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('camera_id', cameraId);
    formData.append('skip_frames', skipFrames.toString());
    if (maxFrames) {
      formData.append('max_frames', maxFrames.toString());
    }

    try {
      const response = await fetch(`${API_BASE}/upload/video`, {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();

      if (response.ok) {
        // Start tracking job
        startJobTracking(data.job_id);
        setSelectedFile(null);
        if (fileInputRef.current) fileInputRef.current.value = '';
      } else {
        alert(`Upload failed: ${data.detail}`);
      }
    } catch (error) {
      console.error('Upload error:', error);
      alert('Upload failed. Please check if the API is running.');
    } finally {
      setUploading(false);
    }
  };

  // Upload URL
  const handleUrlUpload = async () => {
    if (!videoUrl.trim()) return;

    setUploading(true);

    try {
      const response = await fetch(`${API_BASE}/upload/url`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url: videoUrl,
          camera_id: cameraId,
          skip_frames: skipFrames,
          max_frames: maxFrames || null,
        }),
      });

      const data = await response.json();

      if (response.ok) {
        // Start tracking job
        startJobTracking(data.job_id);
        setVideoUrl('');
      } else {
        alert(`Upload failed: ${data.detail}`);
      }
    } catch (error) {
      console.error('URL upload error:', error);
      alert('Upload failed. Please check if the API is running.');
    } finally {
      setUploading(false);
    }
  };

  // Job tracking
  const startJobTracking = (jobId: string) => {
    // Add job to list with pending status
    const newJob: UploadJob = {
      job_id: jobId,
      status: 'pending',
      progress: 0,
      message: 'Queued for processing...',
      camera_id: cameraId,
      video_source: uploadMethod === 'file' ? selectedFile?.name || '' : videoUrl,
    };
    setJobs(prev => [newJob, ...prev]);

    // Poll status every 2 seconds
    const interval = setInterval(async () => {
      try {
        const response = await fetch(`${API_BASE}/upload/status/${jobId}`);
        const data: UploadJob = await response.json();

        setJobs(prev =>
          prev.map(job => (job.job_id === jobId ? data : job))
        );

        // Stop polling if completed or failed
        if (data.status === 'completed' || data.status === 'failed') {
          clearInterval(interval);
        }
      } catch (error) {
        console.error('Status check error:', error);
        clearInterval(interval);
      }
    }, 2000);
  };

  // Delete job
  const handleDeleteJob = async (jobId: string) => {
    try {
      await fetch(`${API_BASE}/upload/job/${jobId}`, {
        method: 'DELETE',
      });
      setJobs(prev => prev.filter(job => job.job_id !== jobId));
    } catch (error) {
      console.error('Delete error:', error);
    }
  };

  // Status icon
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="status-icon success" />;
      case 'failed':
        return <XCircle className="status-icon error" />;
      case 'processing':
        return <Loader className="status-icon processing spin" />;
      default:
        return <Loader className="status-icon pending" />;
    }
  };

  return (
    <div className="video-upload">
      <div className="upload-header">
        <h2>📹 Video Upload & Processing</h2>
        <p>Upload traffic videos for violation detection</p>
      </div>

      <div className="upload-content">
        {/* Upload Method Tabs */}
        <div className="upload-tabs">
          <button
            className={`upload-tab ${uploadMethod === 'file' ? 'active' : ''}`}
            onClick={() => setUploadMethod('file')}
          >
            <FileVideo size={20} />
            <span>Upload File</span>
          </button>
          <button
            className={`upload-tab ${uploadMethod === 'url' ? 'active' : ''}`}
            onClick={() => setUploadMethod('url')}
          >
            <Link size={20} />
            <span>Video URL</span>
          </button>
        </div>

        {/* Configuration Section */}
        <div className="upload-config">
          <div className="config-field">
            <label>Camera ID</label>
            <input
              type="text"
              value={cameraId}
              onChange={(e) => setCameraId(e.target.value)}
              placeholder="e.g., demo_cam_01"
            />
          </div>
          <div className="config-field">
            <label>Skip Frames</label>
            <input
              type="number"
              value={skipFrames}
              onChange={(e) => setSkipFrames(parseInt(e.target.value))}
              min={1}
              max={10}
            />
            <small>Process every Nth frame (higher = faster)</small>
          </div>
          <div className="config-field">
            <label>Max Frames (optional)</label>
            <input
              type="number"
              value={maxFrames || ''}
              onChange={(e) => setMaxFrames(e.target.value ? parseInt(e.target.value) : undefined)}
              placeholder="Leave empty for full video"
            />
            <small>Limit processing to N frames</small>
          </div>
        </div>

        {/* Upload Area */}
        {uploadMethod === 'file' ? (
          <div className="upload-section">
            <div
              className={`drop-zone ${dragActive ? 'drag-active' : ''} ${selectedFile ? 'has-file' : ''}`}
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".mp4,.avi,.mov,.mkv,.webm"
                onChange={handleFileInput}
                style={{ display: 'none' }}
              />
              
              {selectedFile ? (
                <div className="selected-file">
                  <FileVideo size={48} className="file-icon" />
                  <div className="file-info">
                    <h3>{selectedFile.name}</h3>
                    <p>{formatFileSize(selectedFile.size)}</p>
                  </div>
                  <button
                    className="remove-file"
                    onClick={(e) => {
                      e.stopPropagation();
                      setSelectedFile(null);
                      if (fileInputRef.current) fileInputRef.current.value = '';
                    }}
                  >
                    ×
                  </button>
                </div>
              ) : (
                <>
                  <Upload size={48} className="upload-icon" />
                  <h3>Drag & Drop Video File</h3>
                  <p>or click to browse</p>
                  <small>Supports MP4, AVI, MOV, MKV, WEBM (max 500 MB)</small>
                </>
              )}
            </div>

            <button
              className="upload-button"
              onClick={handleFileUpload}
              disabled={!selectedFile || uploading}
            >
              {uploading ? (
                <>
                  <Loader className="spin" size={20} />
                  Uploading...
                </>
              ) : (
                <>
                  <Upload size={20} />
                  Upload & Process
                </>
              )}
            </button>
          </div>
        ) : (
          <div className="upload-section">
            <div className="url-input-group">
              <Youtube size={24} className="url-icon" />
              <input
                type="text"
                className="url-input"
                placeholder="Enter YouTube URL or direct video link..."
                value={videoUrl}
                onChange={(e) => setVideoUrl(e.target.value)}
              />
            </div>
            <button
              className="upload-button"
              onClick={handleUrlUpload}
              disabled={!videoUrl.trim() || uploading}
            >
              {uploading ? (
                <>
                  <Loader className="spin" size={20} />
                  Processing...
                </>
              ) : (
                <>
                  <Upload size={20} />
                  Submit URL & Process
                </>
              )}
            </button>
          </div>
        )}
      </div>

      {/* Processing Jobs */}
      {jobs.length > 0 && (
        <div className="jobs-section">
          <h3>Processing Jobs</h3>
          <div className="jobs-list">
            {jobs.map((job) => (
              <div key={job.job_id} className={`job-card status-${job.status}`}>
                <div className="job-header">
                  <div className="job-info">
                    {getStatusIcon(job.status)}
                    <div>
                      <h4>{job.video_source}</h4>
                      <span className="job-id">Job ID: {job.job_id}</span>
                    </div>
                  </div>
                  <button
                    className="delete-job"
                    onClick={() => handleDeleteJob(job.job_id)}
                    title="Remove job"
                  >
                    <Trash2 size={18} />
                  </button>
                </div>

                <div className="job-progress">
                  <div className="progress-bar">
                    <div
                      className="progress-fill"
                      style={{ width: `${job.progress}%` }}
                    />
                  </div>
                  <span className="progress-text">{job.progress.toFixed(0)}%</span>
                </div>

                <div className="job-message">{job.message}</div>

                {job.results && (
                  <div className="job-results">
                    <div className="result-item">
                      <strong>Violations Detected:</strong>{' '}
                      {job.results.violations_detected}
                    </div>
                    <div className="result-item">
                      <strong>Evidence Folder:</strong>{' '}
                      {job.results.evidence_folder}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default VideoUpload;
