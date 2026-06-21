import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar } from 'recharts';
import { AlertTriangle, CheckCircle, Clock, TrendingUp, Camera, DollarSign } from 'lucide-react';
import './Dashboard.css';

const API_BASE = 'http://localhost:8000';

interface Stats {
  total_today: number;
  auto_approved: number;
  pending_review: number;
  avg_confidence: number;
  top_violation: string;
  active_cameras: number;
  violation_breakdown: Record<string, number>;
  hourly_trend: number[];
}

interface RecentViolation {
  id: number;
  event_id: string;
  violation_type: string;
  camera_id: string;
  plate_number: string | null;
  confidence: number;
  severity: number;
  timestamp: number;
  image_path: string | null;
  reviewed: boolean;
  approved: boolean | null;
}

const Dashboard: React.FC = () => {
  const [stats, setStats] = useState<Stats | null>(null);
  const [recentViolations, setRecentViolations] = useState<RecentViolation[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStats();
    fetchRecentViolations();
    
    // WebSocket for real-time updates
    const ws = new WebSocket('ws://localhost:8000/ws');
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      if (data.type === 'violation') {
        // New violation received
        setRecentViolations(prev => [data.data, ...prev.slice(0, 9)]);
        fetchStats(); // Refresh stats
      }
    };

    // Refresh every 30 seconds
    const interval = setInterval(() => {
      fetchStats();
      fetchRecentViolations();
    }, 30000);

    return () => {
      ws.close();
      clearInterval(interval);
    };
  }, []);

  const fetchStats = async () => {
    try {
      const response = await axios.get(`${API_BASE}/violations/stats`);
      setStats(response.data);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching stats:', error);
      setLoading(false);
    }
  };

  const fetchRecentViolations = async () => {
    try {
      const response = await axios.get(`${API_BASE}/violations?limit=10`);
      setRecentViolations(response.data);
    } catch (error) {
      console.error('Error fetching violations:', error);
    }
  };

  if (loading) {
    return (
      <div className="loading">
        <div className="spinner"></div>
      </div>
    );
  }

  if (!stats) {
    return <div>Error loading data</div>;
  }

  // Prepare hourly chart data
  const hourlyData = stats.hourly_trend.map((count, index) => ({
    hour: `${11 - index}h ago`,
    violations: count,
  })).reverse();

  // Prepare breakdown chart data
  const breakdownData = Object.entries(stats.violation_breakdown).map(([type, count]) => ({
    type: type.replace(/_/g, ' ').toUpperCase(),
    count,
  }));

  const getSeverityBadge = (severity: number) => {
    if (severity >= 4) return 'badge-critical';
    if (severity === 3) return 'badge-high';
    if (severity === 2) return 'badge-medium';
    return 'badge-low';
  };

  const getSeverityText = (severity: number) => {
    if (severity >= 4) return 'CRITICAL';
    if (severity === 3) return 'HIGH';
    if (severity === 2) return 'MEDIUM';
    return 'LOW';
  };

  const formatTimestamp = (timestamp: number) => {
    const date = new Date(timestamp * 1000);
    return date.toLocaleTimeString();
  };

  return (
    <div className="dashboard">
      {/* Stats Cards */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon bg-blue">
            <AlertTriangle size={24} />
          </div>
          <div className="stat-content">
            <div className="stat-value">{stats.total_today}</div>
            <div className="stat-label">Total Today</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon bg-green">
            <CheckCircle size={24} />
          </div>
          <div className="stat-content">
            <div className="stat-value">{stats.auto_approved}</div>
            <div className="stat-label">Auto Approved</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon bg-yellow">
            <Clock size={24} />
          </div>
          <div className="stat-content">
            <div className="stat-value">{stats.pending_review}</div>
            <div className="stat-label">Pending Review</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon bg-purple">
            <TrendingUp size={24} />
          </div>
          <div className="stat-content">
            <div className="stat-value">{(stats.avg_confidence * 100).toFixed(1)}%</div>
            <div className="stat-label">Avg Confidence</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon bg-orange">
            <Camera size={24} />
          </div>
          <div className="stat-content">
            <div className="stat-value">{stats.active_cameras}</div>
            <div className="stat-label">Active Cameras</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon bg-red">
            <DollarSign size={24} />
          </div>
          <div className="stat-content">
            <div className="stat-value">{stats.top_violation.replace(/_/g, ' ')}</div>
            <div className="stat-label">Top Violation</div>
          </div>
        </div>
      </div>

      {/* Charts */}
      <div className="charts-grid">
        <div className="card chart-card">
          <div className="card-header">
            <h3 className="card-title">Hourly Trend (Last 12 Hours)</h3>
          </div>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={hourlyData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="hour" stroke="#9ca3af" />
              <YAxis stroke="#9ca3af" />
              <Tooltip 
                contentStyle={{ background: '#1a1f2e', border: '1px solid #374151', borderRadius: '8px' }}
                labelStyle={{ color: '#e4e6eb' }}
              />
              <Legend />
              <Line type="monotone" dataKey="violations" stroke="#60a5fa" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="card chart-card">
          <div className="card-header">
            <h3 className="card-title">Violations by Type</h3>
          </div>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={breakdownData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="type" stroke="#9ca3af" />
              <YAxis stroke="#9ca3af" />
              <Tooltip 
                contentStyle={{ background: '#1a1f2e', border: '1px solid #374151', borderRadius: '8px' }}
                labelStyle={{ color: '#e4e6eb' }}
              />
              <Bar dataKey="count" fill="#8b5cf6" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Recent Violations */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Recent Violations</h3>
        </div>
        <div className="violations-table">
          <table>
            <thead>
              <tr>
                <th>Time</th>
                <th>Type</th>
                <th>Camera</th>
                <th>Plate</th>
                <th>Confidence</th>
                <th>Severity</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {recentViolations.map((v) => (
                <tr key={v.id}>
                  <td>{formatTimestamp(v.timestamp)}</td>
                  <td>
                    <span className="violation-type">
                      {v.violation_type.replace(/_/g, ' ')}
                    </span>
                  </td>
                  <td>{v.camera_id}</td>
                  <td>{v.plate_number || 'N/A'}</td>
                  <td>
                    <span className="confidence">{(v.confidence * 100).toFixed(1)}%</span>
                  </td>
                  <td>
                    <span className={`badge ${getSeverityBadge(v.severity)}`}>
                      {getSeverityText(v.severity)}
                    </span>
                  </td>
                  <td>
                    {v.reviewed ? (
                      <span className={`badge ${v.approved ? 'badge-success' : 'badge-danger'}`}>
                        {v.approved ? 'APPROVED' : 'REJECTED'}
                      </span>
                    ) : (
                      <span className="badge badge-pending">PENDING</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
