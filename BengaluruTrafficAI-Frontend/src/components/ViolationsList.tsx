import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Search, Filter, Eye, CheckCircle, XCircle } from 'lucide-react';
import './ViolationsList.css';

const API_BASE = 'http://localhost:8000';

interface Violation {
  id: number;
  event_id: string;
  violation_type: string;
  camera_id: string;
  track_id: number | null;
  plate_number: string | null;
  confidence: number;
  severity: number;
  fine_inr: number;
  auto_approve: boolean;
  reviewed: boolean;
  approved: boolean | null;
  image_path: string | null;
  timestamp: number;
  created_at: string | null;
}

const ViolationsList: React.FC = () => {
  const [violations, setViolations] = useState<Violation[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedViolation, setSelectedViolation] = useState<Violation | null>(null);
  const [filters, setFilters] = useState({
    search: '',
    camera: '',
    type: '',
    reviewed: 'all',
  });

  useEffect(() => {
    fetchViolations();
  }, []);

  const fetchViolations = async () => {
    try {
      const params: any = { limit: 100 };
      
      if (filters.camera) params.camera_id = filters.camera;
      if (filters.type) params.violation_type = filters.type;
      if (filters.reviewed !== 'all') params.reviewed = filters.reviewed === 'true';
      
      const response = await axios.get(`${API_BASE}/violations`, { params });
      setViolations(response.data);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching violations:', error);
      setLoading(false);
    }
  };

  const handleReview = async (eventId: string, approved: boolean) => {
    try {
      await axios.patch(`${API_BASE}/violations/${eventId}/review`, { approved });
      fetchViolations();
      setSelectedViolation(null);
    } catch (error) {
      console.error('Error reviewing violation:', error);
    }
  };

  const filteredViolations = violations.filter(v => {
    if (filters.search) {
      const search = filters.search.toLowerCase();
      return (
        v.event_id.toLowerCase().includes(search) ||
        v.camera_id.toLowerCase().includes(search) ||
        v.plate_number?.toLowerCase().includes(search) ||
        v.violation_type.toLowerCase().includes(search)
      );
    }
    return true;
  });

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
    return date.toLocaleString();
  };

  if (loading) {
    return (
      <div className="loading">
        <div className="spinner"></div>
      </div>
    );
  }

  return (
    <div className="violations-list">
      <div className="violations-header">
        <h2>All Violations</h2>
        
        <div className="filters">
          <div className="search-box">
            <Search size={18} />
            <input
              type="text"
              placeholder="Search by ID, camera, plate..."
              value={filters.search}
              onChange={(e) => setFilters({ ...filters, search: e.target.value })}
            />
          </div>
          
          <select
            value={filters.type}
            onChange={(e) => setFilters({ ...filters, type: e.target.value })}
          >
            <option value="">All Types</option>
            <option value="no_helmet">No Helmet</option>
            <option value="no_seatbelt">No Seatbelt</option>
            <option value="signal_jump">Signal Jump</option>
            <option value="wrong_way">Wrong Way</option>
            <option value="triple_riding">Triple Riding</option>
          </select>
          
          <select
            value={filters.reviewed}
            onChange={(e) => setFilters({ ...filters, reviewed: e.target.value })}
          >
            <option value="all">All Status</option>
            <option value="false">Pending</option>
            <option value="true">Reviewed</option>
          </select>
          
          <button className="btn btn-primary" onClick={fetchViolations}>
            <Filter size={18} />
            Apply
          </button>
        </div>
      </div>

      <div className="violations-grid">
        {filteredViolations.map((violation) => (
          <div key={violation.id} className="violation-card">
            <div className="violation-image">
              {violation.image_path ? (
                <img
                  src={`${API_BASE}/${violation.image_path}`}
                  alt="Violation evidence"
                  onError={(e) => {
                    (e.target as HTMLImageElement).src = 'https://via.placeholder.com/300x200?text=No+Image';
                  }}
                />
              ) : (
                <div className="no-image">No Image Available</div>
              )}
              
              <div className="violation-overlay">
                <span className={`badge ${getSeverityBadge(violation.severity)}`}>
                  {getSeverityText(violation.severity)}
                </span>
              </div>
            </div>

            <div className="violation-content">
              <div className="violation-header-info">
                <h4>{violation.violation_type.replace(/_/g, ' ').toUpperCase()}</h4>
                <span className="fine">₹{violation.fine_inr}</span>
              </div>

              <div className="violation-details">
                <div className="detail-row">
                  <span className="label">Event ID:</span>
                  <span className="value">{violation.event_id.substring(0, 8)}...</span>
                </div>
                <div className="detail-row">
                  <span className="label">Camera:</span>
                  <span className="value">{violation.camera_id}</span>
                </div>
                <div className="detail-row">
                  <span className="label">Plate:</span>
                  <span className="value">{violation.plate_number || 'N/A'}</span>
                </div>
                <div className="detail-row">
                  <span className="label">Confidence:</span>
                  <span className="value confidence">{(violation.confidence * 100).toFixed(1)}%</span>
                </div>
                <div className="detail-row">
                  <span className="label">Time:</span>
                  <span className="value">{formatTimestamp(violation.timestamp)}</span>
                </div>
              </div>

              <div className="violation-actions">
                {violation.reviewed ? (
                  <div className={`status-badge ${violation.approved ? 'approved' : 'rejected'}`}>
                    {violation.approved ? (
                      <>
                        <CheckCircle size={16} />
                        Approved
                      </>
                    ) : (
                      <>
                        <XCircle size={16} />
                        Rejected
                      </>
                    )}
                  </div>
                ) : (
                  <>
                    <button
                      className="btn btn-success"
                      onClick={() => handleReview(violation.event_id, true)}
                    >
                      <CheckCircle size={16} />
                      Approve
                    </button>
                    <button
                      className="btn btn-danger"
                      onClick={() => handleReview(violation.event_id, false)}
                    >
                      <XCircle size={16} />
                      Reject
                    </button>
                  </>
                )}
                <button
                  className="btn btn-primary"
                  onClick={() => setSelectedViolation(violation)}
                >
                  <Eye size={16} />
                  Details
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Detail Modal */}
      {selectedViolation && (
        <div className="modal-overlay" onClick={() => setSelectedViolation(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Violation Details</h3>
              <button className="close-btn" onClick={() => setSelectedViolation(null)}>×</button>
            </div>
            
            <div className="modal-body">
              {selectedViolation.image_path && (
                <img
                  src={`${API_BASE}/${selectedViolation.image_path}`}
                  alt="Violation evidence"
                  className="modal-image"
                />
              )}
              
              <div className="modal-details">
                <div className="detail-group">
                  <label>Event ID</label>
                  <p>{selectedViolation.event_id}</p>
                </div>
                <div className="detail-group">
                  <label>Violation Type</label>
                  <p>{selectedViolation.violation_type.replace(/_/g, ' ')}</p>
                </div>
                <div className="detail-group">
                  <label>Camera ID</label>
                  <p>{selectedViolation.camera_id}</p>
                </div>
                <div className="detail-group">
                  <label>Plate Number</label>
                  <p>{selectedViolation.plate_number || 'Not detected'}</p>
                </div>
                <div className="detail-group">
                  <label>Confidence Score</label>
                  <p>{(selectedViolation.confidence * 100).toFixed(2)}%</p>
                </div>
                <div className="detail-group">
                  <label>Severity Level</label>
                  <p>{getSeverityText(selectedViolation.severity)}</p>
                </div>
                <div className="detail-group">
                  <label>Fine Amount</label>
                  <p>₹{selectedViolation.fine_inr}</p>
                </div>
                <div className="detail-group">
                  <label>Timestamp</label>
                  <p>{formatTimestamp(selectedViolation.timestamp)}</p>
                </div>
                <div className="detail-group">
                  <label>Auto Approved</label>
                  <p>{selectedViolation.auto_approve ? 'Yes' : 'No'}</p>
                </div>
                <div className="detail-group">
                  <label>Review Status</label>
                  <p>
                    {selectedViolation.reviewed
                      ? selectedViolation.approved
                        ? 'Approved'
                        : 'Rejected'
                      : 'Pending Review'}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ViolationsList;
