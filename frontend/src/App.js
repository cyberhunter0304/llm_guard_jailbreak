import React, { useState, useEffect } from 'react';
import AnalyticsDashboard from './components/AnalyticsDashboard.refactored';
import ChatbotApp from './components/ChatbotApp';

function App() {
  const [currentView, setCurrentView] = useState('dashboard');
  const [showMenu, setShowMenu] = useState(false);

  useEffect(() => {
    const handleKeyPress = (e) => {
      if (e.altKey) {
        if (e.key === '1') { setCurrentView('dashboard'); setShowMenu(false); }
        else if (e.key === '2') { setCurrentView('chat'); setShowMenu(false); }
      }
      if (e.key === 'Escape') setShowMenu(false);
    };
    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, []);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (showMenu && !e.target.closest('.floating-nav')) setShowMenu(false);
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [showMenu]);

  return (
    <>
      <style>{styles}</style>

      {/* Both views always mounted — CSS visibility toggles them */}
      <div style={{ display: currentView === 'dashboard' ? 'block' : 'none' }}>
        <AnalyticsDashboard />
      </div>
      <div style={{ display: currentView === 'chat' ? 'block' : 'none' }}>
        <ChatbotApp />
      </div>

      {/* Floating nav sits outside content flow, never blocks scrolling */}
      <div className="floating-nav">
        {showMenu && (
          <div className="nav-menu">
            <button
              className={`menu-item ${currentView === 'dashboard' ? 'active' : ''}`}
              onClick={() => { setCurrentView('dashboard'); setShowMenu(false); }}
            >
              <span className="menu-icon">📊</span>
              <span className="menu-label">Dashboard</span>
              <span className="menu-shortcut">Alt+1</span>
            </button>
            <button
              className={`menu-item ${currentView === 'chat' ? 'active' : ''}`}
              onClick={() => { setCurrentView('chat'); setShowMenu(false); }}
            >
              <span className="menu-icon">💬</span>
              <span className="menu-label">Chat Test</span>
              <span className="menu-shortcut">Alt+2</span>
            </button>
          </div>
        )}

        <button
          className="nav-toggle"
          onClick={() => setShowMenu(!showMenu)}
          title="Switch view"
        >
          <span className="toggle-icon">{showMenu ? '✕' : '☰'}</span>
          <span className="current-badge">
            {currentView === 'dashboard' ? '📊' : '💬'}
          </span>
        </button>
      </div>
    </>
  );
}

const styles = `
  /* ── Reset: let the page scroll naturally ── */
  html, body {
    margin: 0;
    padding: 0;
    height: auto;          /* NOT 100% or 100vh */
    overflow-y: auto;      /* normal document scroll */
  }

  #root {
    height: auto;          /* grow with content */
  }

  /* ── Floating nav: fixed, never in the scroll flow ── */
  .floating-nav {
    position: fixed;
    bottom: 20px;
    left: 20px;
    z-index: 9999;
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
    /* pointer-events only on children — keeps the layer invisible to scroll */
    pointer-events: none;
  }

  .nav-toggle,
  .nav-menu {
    pointer-events: auto;
  }

  /* ── Toggle button ── */
  .nav-toggle {
    position: relative;
    width: 52px;
    height: 52px;
    border-radius: 50%;
    border: none;
    background: linear-gradient(135deg, #f97316, #ea580c);
    color: white;
    font-size: 1.4rem;
    cursor: pointer;
    box-shadow: 0 4px 18px rgba(249, 115, 22, 0.45);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
    display: flex;
    align-items: center;
    justify-content: center;
    outline: none;
  }

  .nav-toggle:hover {
    transform: scale(1.08);
    box-shadow: 0 6px 22px rgba(249, 115, 22, 0.55);
  }

  .nav-toggle:active {
    transform: scale(0.95);
  }

  /* Small badge on the button showing current view */
  .current-badge {
    position: absolute;
    bottom: -4px;
    right: -4px;
    width: 22px;
    height: 22px;
    background: white;
    border: 2px solid #f97316;
    border-radius: 50%;
    font-size: 0.7rem;
    display: flex;
    align-items: center;
    justify-content: center;
    line-height: 1;
  }

  /* ── Dropdown menu ── */
  .nav-menu {
    background: white;
    border-radius: 12px;
    box-shadow: 0 8px 32px rgba(0,0,0,0.14);
    border: 2px solid #fed7aa;
    overflow: hidden;
    min-width: 200px;
    animation: slideUp 0.18s ease;
  }

  @keyframes slideUp {
    from { opacity: 0; transform: translateY(6px); }
    to   { opacity: 1; transform: translateY(0); }
  }

  .menu-item {
    width: 100%;
    padding: 0.9rem 1.2rem;
    border: none;
    background: white;
    color: #292524;
    font-size: 0.9375rem;
    font-weight: 600;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 0.75rem;
    transition: background 0.15s ease;
    border-bottom: 1px solid #fef3c7;
    outline: none;
    text-align: left;
  }

  .menu-item:last-child { border-bottom: none; }

  .menu-item:hover {
    background: rgba(249, 115, 22, 0.06);
  }

  .menu-item.active {
    background: linear-gradient(135deg, #f97316, #ea580c);
    color: white;
  }

  .menu-icon  { font-size: 1.2rem; }
  .menu-label { flex: 1; }

  .menu-shortcut {
    font-size: 0.65rem;
    opacity: 0.65;
    background: rgba(0,0,0,0.08);
    padding: 2px 6px;
    border-radius: 4px;
    font-family: monospace;
  }

  .menu-item.active .menu-shortcut {
    background: rgba(255,255,255,0.2);
    opacity: 1;
  }

  /* ── Mobile ── */
  @media (max-width: 768px) {
    .floating-nav  { bottom: 14px; left: 14px; }
    .nav-toggle    { width: 46px; height: 46px; font-size: 1.2rem; }
    .menu-shortcut { display: none; }
  }
`;

export default App;