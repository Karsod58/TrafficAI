import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { Calendar, TrendingUp, MapPin, FileText } from 'lucide-react';
import './Analytics.css';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const COLORS = ['#3b82f6', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981', '#ef4444'];

interface TrendData {
  labels: string[];
  datasets: Array<{
    label: string;
    data: number[];
  }>;
  period: string;
  total_violations: number;
}

interface HeatmapLocation {
  camera_id: string;
  name: string;
  lat: number;
  lon: number;
  count: number;
  severity_avg: number;
}

interface Summary {
  period_days: number;
  total_violations: number;
  daily_average: number;
  total_fines_inr: number;
  auto_approved: number;
  pending_review: number;
  top_violations: Array<{ type: string; count: number }>;
  top_cameras: Array<{ camera_id: string; count: number }>;
  by_severity: {
    critical: number;
    high: number;
    medium: number;
    low: number;
  };
}

const Analytics: React.FC = () => {
  const [trendData, setTrendData] = useState<TrendData | null>(null);
  const [heatmapData, setHeatmapData] = useState<HeatmapLocation[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [period, setPeriod] = useState<'24h' | '7d' | '30d'>('24h');
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [summaryDays, setSummaryDays] = useState(7);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAnalytics();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [period, summaryDays]);

  const fetchAnalytics = async () => {
    setLoading(true);
    try {
      const [trendsRes, heatmapRes, summaryRes] = await Promise.all([
        axios.get(`${API_BASE}/analytics/trends?period=${period}`),
        axios.get(`${API_BASE}/analytics/heatmap?hours=24`),
        axios.get(`${API_BASE}/analytics/summary?days=${summaryDays}`),
      ]);

      setTrendData(trendsRes.data);
      setHeatmapData(heatmapRes.data);
      setSummary(summaryRes.data);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching analytics:', error);
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="loading">
        <div className="spinner"></div>
      </div>
    );
  }

  // Show message if no data
  if (!summary || !trendData) {
    return (
      <div className="analytics">
        <div className="analytics-header">
          <h2>Analytics & Insights</h2>
        </div>
        <div className="no-data" style={{ 
          textAlign: 'center', 
          padding: '60px 20px',
          color: '#9ca3af' 
        }}>
          <h3>No violation data available yet</h3>
          <p>Upload a video or process some violations to see analytics</p>
        </div>
      </div>
    );
  }

  // Prepare trend chart data
  const trendChartData = trendData
    ? trendData.labels.map((label, index) => {
        const dataPoint: any = { name: label };
        trendData.datasets.forEach((dataset) => {
          dataPoint[dataset.label] = dataset.data[index];
        });
        return dataPoint;
      })
    : [];

  // Prepare severity pie chart data
  const severityData = summary && summary.by_severity
    ? [
        { name: 'Critical', value: summary.by_severity.critical || 0 },
        { name: 'High', value: summary.by_severity.high || 0 },
        { name: 'Medium', value: summary.by_severity.medium || 0 },
        { name: 'Low', value: summary.by_severity.low || 0 },
      ]
    : [];

  // Prepare top violations bar chart
  const topViolationsData = summary?.top_violations?.map((v) => ({
    type: v.type.replace(/_/g, ' '),
    count: v.count,
  })) || [];
    count: v.count,
  }));

  return (
    <div className="analytics">
      <div className="analytics-header">
        <h2>Analytics & Insights</h2>
        <div className="period-selector">
          <button
            className={period === '24h' ? 'active' : ''}
            onClick={() => setPeriod('24h')}
          >
            24 Hours
          </button>
          <button
            className={period === '7d' ? 'active' : ''}
            onClick={() => setPeriod('7d')}
          >
            7 Days
          </button>
          <button
            className={period === '30d' ? 'active' : ''}
            onClick={() => setPeriod('30d')}
          >
            30 Days
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      {summary && (
        <div className="summary-grid">
          <div className="summary-card">
            <div className="summary-icon bg-blue">
              <TrendingUp size={24} />
            </div>
            <div className="summary-content">
              <div className="summary-label">Total Violations</div>
              <div className="summary-value">{summary.total_violations}</div>
              <div className="summary-subtext">
                Avg {summary.daily_average.toFixed(1)}/day
              </div>
            </div>
          </div>

          <div className="summary-card">
            <div className="summary-icon bg-green">
              <FileText size={24} />
            </div>
            <div className="summary-content">
              <div className="summary-label">Auto Approved</div>
              <div className="summary-value">{summary.auto_approved}</div>
              <div className="summary-subtext">
                {summary.total_violations > 0 
                  ? ((summary.auto_approved / summary.total_violations) * 100).toFixed(1) 
                  : 0}% of total
              </div>
            </div>
          </div>

          <div className="summary-card">
            <div className="summary-icon bg-yellow">
              <Calendar size={24} />
            </div>
            <div className="summary-content">
              <div className="summary-label">Pending Review</div>
              <div className="summary-value">{summary.pending_review}</div>
              <div className="summary-subtext">
                {summary.total_violations > 0
                  ? ((summary.pending_review / summary.total_violations) * 100).toFixed(1)
                  : 0}% of total
              </div>
            </div>
          </div>

          <div className="summary-card">
            <div className="summary-icon bg-orange">
              <TrendingUp size={24} />
            </div>
            <div className="summary-content">
              <div className="summary-label">Total Fines</div>
              <div className="summary-value">₹{summary.total_fines_inr.toLocaleString()}</div>
              <div className="summary-subtext">Last {summary.period_days} days</div>
            </div>
          </div>
        </div>
      )}

      {/* Trend Chart */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Violation Trends</h3>
          <span className="chart-subtitle">
            {trendData?.total_violations} total violations in {period}
          </span>
        </div>
        <ResponsiveContainer width="100%" height={350}>
          <LineChart data={trendChartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis dataKey="name" stroke="#9ca3af" />
            <YAxis stroke="#9ca3af" />
            <Tooltip
              contentStyle={{
                background: '#1a1f2e',
                border: '1px solid #374151',
                borderRadius: '8px',
              }}
              labelStyle={{ color: '#e4e6eb' }}
            />
            <Legend />
            {trendData?.datasets.map((dataset, index) => (
              <Line
                key={dataset.label}
                type="monotone"
                dataKey={dataset.label}
                stroke={COLORS[index % COLORS.length]}
                strokeWidth={2}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Charts Grid */}
      <div className="analytics-grid">
        {/* Top Violations */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Top Violations</h3>
          </div>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={topViolationsData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="type" stroke="#9ca3af" />
              <YAxis stroke="#9ca3af" />
              <Tooltip
                contentStyle={{
                  background: '#1a1f2e',
                  border: '1px solid #374151',
                  borderRadius: '8px',
                }}
                labelStyle={{ color: '#e4e6eb' }}
              />
              <Bar dataKey="count" fill="#3b82f6" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Severity Distribution */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Severity Distribution</h3>
          </div>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={severityData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, percent }) => `${name} ${((percent || 0) * 100).toFixed(0)}%`}
                outerRadius={80}
                fill="#8884d8"
                dataKey="value"
              >
                {severityData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  background: '#1a1f2e',
                  border: '1px solid #374151',
                  borderRadius: '8px',
                }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Heatmap */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">
            <MapPin size={20} />
            Violation Hotspots
          </h3>
        </div>
        <div className="heatmap-list">
          {heatmapData.map((location, index) => (
            <div key={location.camera_id} className="heatmap-item">
              <div className="heatmap-rank">#{index + 1}</div>
              <div className="heatmap-info">
                <h4>{location.name}</h4>
                <p className="heatmap-location">{location.camera_id}</p>
              </div>
              <div className="heatmap-stats">
                <div className="heatmap-count">{location.count} violations</div>
                <div className="heatmap-severity">
                  Avg severity: {location.severity_avg.toFixed(1)}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Top Cameras */}
      {summary && summary.top_cameras.length > 0 && (
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Most Active Cameras</h3>
          </div>
          <div className="top-cameras-grid">
            {summary.top_cameras.map((camera, index) => (
              <div key={camera.camera_id} className="top-camera-card">
                <div className="camera-rank-badge">#{index + 1}</div>
                <div className="camera-id">{camera.camera_id}</div>
                <div className="camera-count">{camera.count} violations</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default Analytics;
