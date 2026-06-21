import React, { useState, useEffect } from 'react';
import './App.css';
import Dashboard from './components/Dashboard';
import ViolationsList from './components/ViolationsList';
import CameraView from './components/CameraView';
import Analytics from './components/Analytics';
import VideoUpload from './components/VideoUpload';
import { Bell, Camera, BarChart3, List, Upload } from 'lucide-react';

type View = 'dashboard' | 'violations' | 'cameras' | 'analytics' | 'upload';

function App() {
  const [currentView, setCurrentView] = useState<View>('dashboard');
  const [wsConnected, setWsConnected] = useState(false);

  useEffect(() => {
    // WebSocket connection indicator
    const ws = new WebSocket('ws://localhost:8000/ws');
    
    ws.onopen = () => setWsConnected(true);
    ws.onclose = () => setWsConnected(false);
    
    return () => ws.close();
  }, []);

  const renderView = () => {
    switch (currentView) {
      case 'dashboard':
        return <Dashboard />;
      case 'violations':
        return <ViolationsList />;
      case 'cameras':
        return <CameraView />;
      case 'analytics':
        return <Analytics />;
      case 'upload':
        return <VideoUpload />;
      default:
        return <Dashboard />;
    }
  };

  return (
    <div className="App">
      <header className="app-header">
        <div className="header-content">
          <div className="logo-section">
            <h1>🚦 Bengaluru Traffic AI</h1>
            <span className="subtitle">Real-time Violation Detection System</span>
          </div>
          
          <div className="connection-status">
            <div className={`status-indicator ${wsConnected ? 'connected' : 'disconnected'}`}>
              <div className="status-dot"></div>
              <span>{wsConnected ? 'Live' : 'Disconnected'}</span>
            </div>
          </div>
        </div>
        
        <nav className="nav-tabs">
          <button
            className={`nav-tab ${currentView === 'dashboard' ? 'active' : ''}`}
            onClick={() => setCurrentView('dashboard')}
          >
            <Bell size={18} />
            <span>Dashboard</span>
          </button>
          <button
            className={`nav-tab ${currentView === 'violations' ? 'active' : ''}`}
            onClick={() => setCurrentView('violations')}
          >
            <List size={18} />
            <span>Violations</span>
          </button>
          <button
            className={`nav-tab ${currentView === 'cameras' ? 'active' : ''}`}
            onClick={() => setCurrentView('cameras')}
          >
            <Camera size={18} />
            <span>Cameras</span>
          </button>
          <button
            className={`nav-tab ${currentView === 'analytics' ? 'active' : ''}`}
            onClick={() => setCurrentView('analytics')}
          >
            <BarChart3 size={18} />
            <span>Analytics</span>
          </button>
          <button
            className={`nav-tab ${currentView === 'upload' ? 'active' : ''}`}
            onClick={() => setCurrentView('upload')}
          >
            <Upload size={18} />
            <span>Upload</span>
          </button>
        </nav>
      </header>

      <main className="app-main">
        {renderView()}
      </main>
    </div>
  );
}

export default App;
