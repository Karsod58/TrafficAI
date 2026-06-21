import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Camera as CameraIcon, MapPin, Activity, AlertCircle } from 'lucide-react';
import './CameraView.css';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

interface Camera {
  camera_id: string;
  name: string;
  location: string;
  lat: number | null;
  lon: number | null;
  active: boolean;
}

interface CameraStats {
  camera: Camera;
  total_violations: number;
  by_type: Record<string, number>;
  by_hour: number[];
  avg_confidence: number;
  top_plates: Array<{ plate: string; count: number }>;
}

const CameraView: React.FC = () => {
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [selectedCamera, setSelectedCamera] = useState<string | null>(null);
  const [cameraStats, setCameraStats] = useState<CameraStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [statsLoading, setStatsLoading] = useState(false);

  useEffect(() => {
    fetchCameras();
  }, []);

  useEffect(() => {
    if (selectedCamera) {
      fetchCameraStats(selectedCamera);
    }
  }, [selectedCamera]);

  const fetchCameras = async () => {
    try {
      const response = await axios.get(`${API_BASE}/cameras`);
      setCameras(response.data);
      if (response.data.length > 0) {
        setSelectedCamera(response.data[0].camera_id);
      }
      setLoading(false);
    } catch (error) {
      console.error('Error fetching cameras:', error);
      setLoading(false);
    }
  };

  const fetchCameraStats = async (cameraId: string) => {
    setStatsLoading(true);
    try {
      const response = await axios.get(`${API_BASE}/analytics/cameras/${cameraId}/stats`);
      setCameraStats(response.data);
      setStatsLoading(false);
    } catch (error) {
      console.error('Error fetching camera stats:', error);
      setStatsLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="loading">
        <div className="spinner"></div>
      </div>
    );
  }

  return (
    <div className="camera-view">
      <div className="camera-sidebar">
        <h3>Cameras ({cameras.length})</h3>
        <div className="camera-list">
          {cameras.map((camera) => (
            <div
              key={camera.camera_id}
              className={`camera-item ${selectedCamera === camera.camera_id ? 'active' : ''}`}
              onClick={() => setSelectedCamera(camera.camera_id)}
            >
              <div className="camera-icon">
                <CameraIcon size={20} />
              </div>
              <div className="camera-info">
                <h4>{camera.name}</h4>
                <p className="camera-location">
                  <MapPin size={14} />
                  {camera.location}
                </p>
              </div>
              <div className={`status-dot ${camera.active ? 'active' : 'inactive'}`}></div>
            </div>
          ))}
        </div>
      </div>

      <div className="camera-content">
        {statsLoading ? (
          <div className="loading">
            <div className="spinner"></div>
          </div>
        ) : cameraStats ? (
          <>
            <div className="camera-header-section">
              <div className="camera-title-section">
                <h2>{cameraStats.camera.name}</h2>
                <p className="location-text">
                  <MapPin size={18} />
                  {cameraStats.camera.location}
                </p>
              </div>
              <div className={`status-badge ${cameraStats.camera.active ? 'active' : 'inactive'}`}>
                <Activity size={16} />
                {cameraStats.camera.active ? 'Active' : 'Inactive'}
              </div>
            </div>

            {/* Stats Cards */}
            <div className="camera-stats-grid">
              <div className="stat-card-small">
                <div className="stat-label">Total Violations (24h)</div>
                <div className="stat-value-large">{cameraStats.total_violations}</div>
              </div>
              <div className="stat-card-small">
                <div className="stat-label">Avg Confidence</div>
                <div className="stat-value-large">{(cameraStats.avg_confidence * 100).toFixed(1)}%</div>
              </div>
              <div className="stat-card-small">
                <div className="stat-label">Peak Hour</div>
                <div className="stat-value-large">
                  {cameraStats.by_hour.indexOf(Math.max(...cameraStats.by_hour))}:00
                </div>
              </div>
              <div className="stat-card-small">
                <div className="stat-label">Coordinates</div>
                <div className="stat-value-small">
                  {cameraStats.camera.lat?.toFixed(4)}, {cameraStats.camera.lon?.toFixed(4)}
                </div>
              </div>
            </div>

            {/* Violations by Type */}
            <div className="card">
              <h3 className="section-title">Violations by Type (Last 24 Hours)</h3>
              <div className="violation-types-grid">
                {Object.entries(cameraStats.by_type).map(([type, count]) => (
                  <div key={type} className="violation-type-card">
                    <div className="type-count">{count}</div>
                    <div className="type-label">{type.replace(/_/g, ' ')}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Hourly Distribution */}
            <div className="card">
              <h3 className="section-title">Hourly Distribution</h3>
              <div className="hourly-chart">
                {cameraStats.by_hour.map((count, hour) => (
                  <div key={hour} className="hour-bar">
                    <div
                      className="bar-fill"
                      style={{
                        height: `${(count / Math.max(...cameraStats.by_hour)) * 100}%`,
                      }}
                    ></div>
                    <div className="hour-label">{hour}h</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Top Offenders */}
            {cameraStats.top_plates.length > 0 && (
              <div className="card">
                <h3 className="section-title">Top Offending Plates</h3>
                <div className="top-plates-list">
                  {cameraStats.top_plates.map((item, index) => (
                    <div key={index} className="plate-item">
                      <div className="plate-rank">#{index + 1}</div>
                      <div className="plate-number">{item.plate}</div>
                      <div className="plate-count">
                        <AlertCircle size={16} />
                        {item.count} violations
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        ) : (
          <div className="no-data">
            <CameraIcon size={48} />
            <p>Select a camera to view details</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default CameraView;
