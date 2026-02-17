import React, { useState, useRef, useEffect } from 'react';
import logo from './loco.png'; // Your iNextLabs logo

// Generate unique BotID for this session
const getBotId = () => {
  let botId = localStorage.getItem('bot_id');
  if (!botId) {
    botId = `bot_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    localStorage.setItem('bot_id', botId);
  }
  return botId;
};

const ChatbotApp = () => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState('checking');
  const [showMenu, setShowMenu] = useState(false);
  const messagesEndRef = useRef(null);
  const botId = useRef(getBotId());

  // ✅ CHANGED: Point to backend on port 8000
const FASTAPI_URL = `http://${window.location.hostname}:8000`;
const BOT_NAME = 'iNextLabs AI Assistant';

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    const checkConnection = async () => {
      try {
        const response = await fetch(`${FASTAPI_URL}/health`);
        if (response.ok) {
          setConnectionStatus('connected');
          console.log('✅ Connected to backend');
        } else {
          setConnectionStatus('error');
        }
      } catch (error) {
        console.error('Connection check failed:', error);
        setConnectionStatus('error');
      }
    };
    checkConnection();
    const interval = setInterval(checkConnection, 30000);
    return () => clearInterval(interval);
  }, [FASTAPI_URL]);

  const sendMessage = async () => {
    if (!input.trim()) return;

    const promptText = input.trim();

    // Show user message immediately — no waiting
    setMessages(prev => [...prev, {
      role: 'user',
      content: promptText,
      timestamp: new Date().toISOString(),
    }]);
    setInput('');
    setLoading(true);

    try {
      const response = await fetch(`${FASTAPI_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: promptText,
          model: 'openai/gpt-4o-mini',
          bot_id: botId.current,
        }),
      });

      const data = await response.json();

      if (data.success && data.response) {
        // LLM replied — show it naturally
        setMessages(prev => [...prev, {
          role: 'ai',
          content: data.response,
          timestamp: new Date().toISOString(),
        }]);
      } else {
        // Something went wrong server-side
        setMessages(prev => [...prev, {
          role: 'system',
          content: data.detail || data.message || 'An error occurred. Please try again.',
          timestamp: new Date().toISOString(),
        }]);
      }
    } catch (error) {
      console.error('❌ Chat request failed:', error);
      setMessages(prev => [...prev, {
        role: 'system',
        content: 'Failed to connect to server. Please check your connection and try again.',
        timestamp: new Date().toISOString(),
      }]);
    } finally {
      setLoading(false);
    }
  };

  const clearChat = () => {
    setMessages([]);
    setShowMenu(false);
  };

  const resetSession = () => {
    // ✅ ADDED: Function to create new bot session
    localStorage.removeItem('bot_id');
    botId.current = getBotId();
    setMessages([]);
    setShowMenu(false);
    alert(`New session started!\nBot ID: ${botId.current}`);
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const suggestedPrompts = [
    "What can you help me with?",
    "Tell me about AI solutions",
    "How does this work?",
    "What services do you offer?"
  ];

  return (
    <> 
      <style>{`
        * {
          margin: 0;
          padding: 0;
          box-sizing: border-box;
        }

        body {
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
          overflow: hidden;
        }

        .app-container {
          display: flex;
          flex-direction: column;
          height: 100vh;
          background: linear-gradient(135deg, #FF6B35 0%, #F7931E 100%);
          position: relative;
        }

        /* Modern Header - iNextLabs Style */
        .app-header {
          background: rgba(255, 255, 255, 0.98);
          backdrop-filter: blur(20px);
          box-shadow: 0 2px 8px rgba(0,0,0,0.08);
          padding: 16px 24px;
          display: flex;
          align-items: center;
          justify-content: space-between;
          z-index: 10;
        }

        .header-left {
          display: flex;
          align-items: center;
          gap: 14px;
        }

        .app-logo {
          width: 42px;
          height: 42px;
          border-radius: 10px;
          overflow: hidden;
          box-shadow: 0 2px 8px rgba(255, 107, 53, 0.2);
        }

        .app-logo img {
          width: 100%;
          height: 100%;
          object-fit: contain;
        }

        .app-title {
          font-size: 19px;
          font-weight: 700;
          color: #1f2937;
          letter-spacing: -0.3px;
        }

        .app-subtitle {
          font-size: 12px;
          color: #6b7280;
          font-weight: 500;
        }

        .header-right {
          display: flex;
          align-items: center;
          gap: 12px;
        }

        .status-indicator {
          display: flex;
          align-items: center;
          gap: 6px;
          padding: 6px 14px;
          border-radius: 20px;
          font-size: 12px;
          font-weight: 600;
        }

        .status-indicator.connected {
          background: #d1fae5;
          color: #065f46;
        }

        .status-indicator.checking {
          background: #fef3c7;
          color: #92400e;
        }

        .status-indicator.error {
          background: #fee2e2;
          color: #991b1b;
        }

        .status-dot {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          animation: pulse 2s ease-in-out infinite;
        }

        .status-dot.connected {
          background: #10b981;
        }

        .status-dot.checking {
          background: #f59e0b;
        }

        .status-dot.error {
          background: #ef4444;
        }

        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }

        .menu-button {
          background: none;
          border: none;
          font-size: 24px;
          cursor: pointer;
          padding: 8px;
          border-radius: 8px;
          transition: background 0.2s;
          color: #6b7280;
        }

        .menu-button:hover {
          background: #f3f4f6;
          color: #FF6B35;
        }

        /* Dropdown Menu */
        .dropdown-menu {
          position: absolute;
          top: 75px;
          right: 24px;
          background: white;
          border-radius: 14px;
          box-shadow: 0 10px 40px rgba(0,0,0,0.12);
          padding: 8px;
          min-width: 200px;
          z-index: 100;
          animation: slideDown 0.2s ease-out;
        }

        @keyframes slideDown {
          from {
            opacity: 0;
            transform: translateY(-10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        .menu-item {
          padding: 12px 16px;
          border-radius: 8px;
          cursor: pointer;
          transition: background 0.2s;
          display: flex;
          align-items: center;
          gap: 12px;
          font-size: 14px;
          font-weight: 500;
          color: #374151;
        }

        .menu-item:hover {
          background: #f3f4f6;
          color: #FF6B35;
        }

        .menu-item-icon {
          font-size: 18px;
        }

        /* Chat Area */
        .chat-area {
          flex: 1;
          overflow-y: auto;
          padding: 20px;
        }

        .messages-wrapper {
          max-width: 900px;
          margin: 0 auto;
        }

        /* Welcome Screen */
        .welcome-screen {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          min-height: 500px;
          text-align: center;
        }

        .welcome-logo {
          width: 100px;
          height: 100px;
          background: white;
          border-radius: 24px;
          padding: 18px;
          box-shadow: 0 8px 24px rgba(255, 107, 53, 0.2);
          margin-bottom: 30px;
        }

        .welcome-logo img {
          width: 100%;
          height: 100%;
          object-fit: contain;
        }

        .welcome-title {
          font-size: 32px;
          font-weight: 800;
          color: white;
          margin-bottom: 12px;
          text-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }

        .welcome-subtitle {
          font-size: 17px;
          color: rgba(255, 255, 255, 0.95);
          margin-bottom: 40px;
          max-width: 500px;
          line-height: 1.6;
        }

        /* Suggested Prompts */
        .suggested-prompts {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
          gap: 14px;
          width: 100%;
          max-width: 700px;
        }

        .prompt-card {
          background: rgba(255, 255, 255, 0.95);
          padding: 18px 20px;
          border-radius: 16px;
          cursor: pointer;
          transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
          box-shadow: 0 4px 12px rgba(0,0,0,0.08);
          display: flex;
          align-items: center;
          gap: 12px;
        }

        .prompt-card:hover {
          transform: translateY(-4px);
          box-shadow: 0 8px 24px rgba(255, 107, 53, 0.2);
          background: white;
        }

        .prompt-icon {
          font-size: 24px;
          flex-shrink: 0;
        }

        .prompt-text {
          font-size: 14px;
          font-weight: 600;
          color: #374151;
          text-align: left;
        }

        /* Messages */
        .message {
          display: flex;
          gap: 12px;
          margin-bottom: 20px;
          animation: fadeIn 0.4s ease-out;
        }

        @keyframes fadeIn {
          from {
            opacity: 0;
            transform: translateY(10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        .message.user {
          flex-direction: row-reverse;
        }

        .message-avatar {
          width: 38px;
          height: 38px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 20px;
          flex-shrink: 0;
          box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }

        .message-avatar.user {
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }

        .message-avatar.ai {
          background: white;
          padding: 6px;
        }

        .message-avatar.ai img {
          width: 100%;
          height: 100%;
          object-fit: contain;
        }

        .message-avatar.system {
          background: #fef3c7;
        }

        .message-content-wrapper {
          max-width: 65%;
          display: flex;
          flex-direction: column;
          gap: 6px;
        }

        .message.user .message-content-wrapper {
          align-items: flex-end;
        }

        .message-bubble {
          padding: 14px 18px;
          border-radius: 18px;
          box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }

        .message-bubble.user {
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white;
          border-bottom-right-radius: 4px;
        }

        .message-bubble.ai {
          background: white;
          color: #1f2937;
          border-bottom-left-radius: 4px;
        }

        .message-bubble.system {
          background: #fee2e2;
          color: #991b1b;
          border: 1px solid #fca5a5;
        }

        .message-text {
          font-size: 15px;
          line-height: 1.5;
          margin: 0;
          white-space: pre-wrap;
          word-wrap: break-word;
        }

        .message-time {
          font-size: 11px;
          color: rgba(255, 255, 255, 0.7);
          padding: 0 4px;
        }

        .message.ai .message-time {
          color: #9ca3af;
        }

        /* Typing Indicator */
        .typing-indicator {
          display: flex;
          gap: 12px;
          margin-bottom: 20px;
          animation: fadeIn 0.4s ease-out;
        }

        .typing-bubble {
          background: white;
          padding: 16px 20px;
          border-radius: 18px;
          border-bottom-left-radius: 4px;
          box-shadow: 0 2px 8px rgba(0,0,0,0.08);
          display: flex;
          gap: 6px;
        }

        .typing-dot {
          width: 8px;
          height: 8px;
          background: #9ca3af;
          border-radius: 50%;
          animation: typing 1.4s ease-in-out infinite;
        }

        .typing-dot:nth-child(2) {
          animation-delay: 0.2s;
        }

        .typing-dot:nth-child(3) {
          animation-delay: 0.4s;
        }

        @keyframes typing {
          0%, 60%, 100% {
            transform: translateY(0);
            opacity: 0.7;
          }
          30% {
            transform: translateY(-10px);
            opacity: 1;
          }
        }

        /* Input Area */
        .input-container {
          background: rgba(255, 255, 255, 0.98);
          backdrop-filter: blur(20px);
          padding: 20px 24px;
          box-shadow: 0 -2px 8px rgba(0,0,0,0.08);
        }

        .input-wrapper {
          max-width: 800px;
          margin: 0 auto;
          display: flex;
          gap: 12px;
          align-items: flex-end;
        }

        .input-box {
          flex: 1;
          background: #f9fafb;
          border: 2px solid transparent;
          border-radius: 24px;
          padding: 14px 22px;
          font-size: 15px;
          resize: none;
          outline: none;
          transition: all 0.3s;
          font-family: inherit;
          max-height: 120px;
          color: #1f2937;
        }

        .input-box:focus {
          background: white;
          border-color: #FF6B35;
          box-shadow: 0 0 0 4px rgba(255, 107, 53, 0.1);
        }

        .input-box::placeholder {
          color: #9ca3af;
        }

        .input-box:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }

        .send-button {
          width: 52px;
          height: 52px;
          border-radius: 50%;
          background: linear-gradient(135deg, #FF6B35 0%, #F7931E 100%);
          border: none;
          color: white;
          font-size: 22px;
          cursor: pointer;
          transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
          display: flex;
          align-items: center;
          justify-content: center;
          box-shadow: 0 4px 14px rgba(255, 107, 53, 0.4);
        }

        .send-button:hover:not(:disabled) {
          transform: scale(1.08);
          box-shadow: 0 6px 20px rgba(255, 107, 53, 0.5);
        }

        .send-button:active:not(:disabled) {
          transform: scale(0.95);
        }

        .send-button:disabled {
          opacity: 0.5;
          cursor: not-allowed;
          transform: scale(1);
        }

        .powered-by {
          text-align: center;
          font-size: 11px;
          color: #9ca3af;
          margin-top: 12px;
          font-weight: 500;
        }

        .powered-by a {
          color: #FF6B35;
          text-decoration: none;
          font-weight: 600;
        }

        .powered-by a:hover {
          text-decoration: underline;
        }

        /* Scrollbar Styling */
        .chat-area::-webkit-scrollbar {
          width: 8px;
        }

        .chat-area::-webkit-scrollbar-track {
          background: transparent;
        }

        .chat-area::-webkit-scrollbar-thumb {
          background: rgba(255,255,255,0.3);
          border-radius: 4px;
        }

        .chat-area::-webkit-scrollbar-thumb:hover {
          background: rgba(255,255,255,0.5);
        }

        /* Responsive */
        @media (max-width: 768px) {
          .welcome-title {
            font-size: 26px;
          }

          .welcome-subtitle {
            font-size: 15px;
          }

          .suggested-prompts {
            grid-template-columns: 1fr;
          }

          .message-content-wrapper {
            max-width: 85%;
          }

          .app-title {
            font-size: 17px;
          }

          .app-subtitle {
            display: none;
          }
        }
      `}</style>

      <div className="app-container">
        {/* Header */}
        <div className="app-header">
          <div className="header-left">
            <div className="app-logo">
              <img src={logo} alt="iNextLabs" />
            </div>
            <div>
              <div className="app-title">{BOT_NAME}</div>
              <div className="app-subtitle">Powered by Advanced AI Security</div>
            </div>
          </div>
          <div className="header-right">
            <div className={`status-indicator ${connectionStatus}`}>
              <div className={`status-dot ${connectionStatus}`}></div>
              {connectionStatus === 'connected' && 'Online'}
              {connectionStatus === 'checking' && 'Connecting...'}
              {connectionStatus === 'error' && 'Offline'}
            </div>
            <button className="menu-button" onClick={() => setShowMenu(!showMenu)}>
              ⋮
            </button>
          </div>
        </div>

        {/* Dropdown Menu */}
        {showMenu && (
          <div className="dropdown-menu">
            <div className="menu-item" onClick={clearChat}>
              <span className="menu-item-icon">🗑️</span>
              <span>Clear Chat</span>
            </div>
            {/* ✅ ADDED: New Session option */}
            <div className="menu-item" onClick={resetSession}>
              <span className="menu-item-icon">🔄</span>
              <span>New Session</span>
            </div>
            <div className="menu-item" onClick={() => window.open('https://inextlabs.com', '_blank')}>
              <span className="menu-item-icon">🌐</span>
              <span>Visit iNextLabs</span>
            </div>
            <div className="menu-item" onClick={() => {
              alert(`Bot ID: ${botId.current}\n\nThis unique ID identifies your chat session.`);
              setShowMenu(false);
            }}>
              <span className="menu-item-icon">ℹ️</span>
              <span>Session Info</span>
            </div>
            {/* ✅ ADDED: Link to Analytics Dashboard */}
            <div className="menu-item" onClick={() => window.open('http://localhost:3000/analytics', '_blank')}>
              <span className="menu-item-icon">📊</span>
              <span>View Analytics</span>
            </div>
          </div>
        )}

        {/* Chat Area */}
        <div className="chat-area">
          <div className="messages-wrapper">
            {messages.length === 0 ? (
              <div className="welcome-screen">
                <div className="welcome-logo">
                  <img src={logo} alt="iNextLabs" />
                </div>
                <h1 className="welcome-title">Welcome to {BOT_NAME}</h1>
                <p className="welcome-subtitle">
                  Your intelligent assistant with enterprise-grade AI security. Ask me anything!
                </p>
                <div className="suggested-prompts">
                  {suggestedPrompts.map((prompt, index) => (
                    <div 
                      key={index} 
                      className="prompt-card"
                      onClick={() => setInput(prompt)}
                    >
                      <div className="prompt-icon">💡</div>
                      <p className="prompt-text">{prompt}</p>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              messages.map((message, index) => (
                <div key={index} className={`message ${message.role}`}>
                  <div className={`message-avatar ${message.role}`}>
                    {message.role === 'user' && '👤'}
                    {message.role === 'system' && '⚠️'}
                    {message.role === 'ai' && <img src={logo} alt="AI" />}
                  </div>
                  <div className="message-content-wrapper">
                    <div className={`message-bubble ${message.role}`}>
                      <p className="message-text">{message.content}</p>
                    <div className="message-time">
                      {new Date(message.timestamp).toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'})}
                    </div>
                    </div>
                  </div>
                </div>
              ))
            )}

            {loading && (
              <div className="typing-indicator">
                <div className="message-avatar ai">
                  <img src={logo} alt="AI" />
                </div>
                <div className="typing-bubble">
                  <div className="typing-dot"></div>
                  <div className="typing-dot"></div>
                  <div className="typing-dot"></div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Input Area */}
        <div className="input-container">
          <div className="input-wrapper">
            <textarea
              className="input-box"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Type your message..."
              rows="1"
              onInput={(e) => {
                e.target.style.height = 'auto';
                e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px';
              }}
            />
            <button
              className="send-button"
              onClick={sendMessage}
              disabled={loading || !input.trim() || connectionStatus === 'error'}
            >
              {loading ? '⏳' : '➤'}
            </button>
          </div>
          <div className="powered-by">
            Powered by <a href="https://inextlabs.com" target="_blank" rel="noopener noreferrer">iNextLabs</a>
            {' · '}
            Secured with AI Guardrails
            {' · '}
            Session: {botId.current.substring(0, 15)}...
          </div>
        </div>
      </div>
    </>
  );
};

export default ChatbotApp;