import React, { useState, useRef, useEffect } from 'react';
import logo from './loco.png';


const JailbreakProtectedChat = () => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMessage = { role: 'user', content: input, timestamp: new Date().toISOString() };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);


    // User Query is sent to the backend server.js /api/chat endpoint
    try { 
      const response = await fetch('http://localhost:3001/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          prompt: input,
          model: 'openai/gpt-4o-mini' //model is hardcoded for now
        }),
      });
      // Parse JSON response (transforming json string to object)
      const data = await response.json(); //response from backend (server.js) is captured here

      if (data.success) {
        //if response is 200
        const aiMessage = { //object to hold AI message
          role: 'ai',
          content: data.response,
          security_scan: data.security_scan,
          timestamp: data.timestamp
        };
        setMessages(prev => [...prev, aiMessage]); //adds AI message to chat
      } else { //if response is 403 or any other error
        const errorMessage = {
          role: 'system',
          content: data.error || 'An error occurred',
          security_scan: data.security_scan,
          blocked: data.blocked,
          timestamp: new Date().toISOString()
        };
        setMessages(prev => [...prev, errorMessage]); //aads error message to chat
      }
    } catch (error) {
      // network error or server down
      const errorMessage = {
        role: 'system',
        content: 'Failed to connect to the server. Please try again.',
        timestamp: new Date().toISOString()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <> 
    {/* HTML and CSS for the frontend */}
      <style>{`
        * {
          margin: 0;
          padding: 0;
          box-sizing: border-box;
        }

        body {
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }

        .chat-container {
          display: flex;
          flex-direction: column;
          height: 100vh;
          background: linear-gradient(135deg, #fef3e2 0%, #fae8d0 100%);
        }

        .chat-header {
          background: linear-gradient(135deg, #F05742 0%, #F05742 100%);
          box-shadow: 0 4px 6px rgba(0,0,0,0.1);
          padding: 20px;
        }

        .ai-logo-icon {
            width: 20px;
            height: 20px;
            object-fit: contain;
            vertical-align: middle;
        }

        .header-content {
          max-width: 1200px;
          margin: 0 auto;
          display: flex;
          align-items: center;
          gap: 15px;
        }

        .shield-icon {
          font-size: 32px;
          background: rgba(255,255,255,0.2);
          padding: 10px;
          border-radius: 12px;
          backdrop-filter: blur(10px);
        }

        .header-title {
          font-size: 24px;
          font-weight: bold;
          color: white;
          margin: 0;
        }

        .header-subtitle {
          font-size: 14px;
          color: rgba(255,255,255,0.9);
          margin: 4px 0 0 0;
        }

        .messages-container {
          flex: 1;
          overflow-y: auto;
          padding: 20px;
        }

        .messages-inner {
          max-width: 900px;
          margin: 0 auto;
          display: flex;
          flex-direction: column;
          gap: 20px;
        }

        .empty-state {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          height: 100%;
          padding: 80px 20px;
        }

        .empty-state-card {
          background: rgba(255, 255, 255, 0.8);
          backdrop-filter: blur(10px);
          padding: 40px;
          border-radius: 20px;
          border: 1px solid rgba(255, 140, 66, 0.3);
          max-width: 400px;
          text-align: center;
        }

        .lock-icon {
          font-size: 64px;
          margin-bottom: 20px;
        }

        .empty-title {
          font-size: 24px;
          font-weight: bold;
          color: #d2691e;
          margin: 0 0 10px 0;
        }

        .empty-text {
          color: #8b4513;
          line-height: 1.6;
          margin: 0;
        }

        .message-row {
          display: flex;
          animation: fadeIn 0.3s ease-out;
        }

        .message-row.user {
          justify-content: flex-end;
        }

        .message-row.ai, .message-row.system {
          justify-content: flex-start;
        }

        .message-wrapper {
          max-width: 700px;
          width: 100%;
        }

        .message-wrapper.user {
          margin-left: 60px;
        }

        .message-wrapper.ai, .message-wrapper.system {
          margin-right: 60px;
        }

        .message-bubble {
          border-radius: 20px;
          box-shadow: 0 4px 12px rgba(0,0,0,0.3);
          overflow: hidden;
        }

        .message-bubble.user {
          background: linear-gradient(135deg, #F05742 0%, #F05742 100%);
          color: white;
        }

        .message-bubble.system {
          background: rgba(239, 68, 68, 0.1);
          border: 2px solid rgba(239, 68, 68, 0.5);
          backdrop-filter: blur(10px);
          color: #dc2626;
        }

        .message-bubble.ai {
          background: rgba(255, 255, 255, 0.9);
          backdrop-filter: blur(10px);
          border: 1px solid rgba(255, 140, 66, 0.3);
          color: #4a4a4a;
        }

        .message-content {
          padding: 20px;
          display: flex;
          gap: 15px;
        }

        .icon-wrapper {
          font-size: 24px;
          margin-top: 2px;
        }

        .message-text {
          flex: 1;
        }

        .message-text-content {
          margin: 0;
          line-height: 1.6;
          font-size: 15px;
        }

        .security-scan {
          margin-top: 15px;
          padding: 12px;
          border-radius: 10px;
        }

        .security-scan.safe {
          background: rgba(34, 197, 94, 0.1);
          border: 1px solid rgba(34, 197, 94, 0.3);
        }

        .security-scan.unsafe {
          background: rgba(239, 68, 68, 0.1);
          border: 1px solid rgba(239, 68, 68, 0.3);
        }

        .security-header {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-bottom: 6px;
        }

        .security-icon {
          font-size: 16px;
        }

        .security-level {
          font-size: 12px;
          font-weight: bold;
        }

        .security-message {
          font-size: 12px;
          margin: 0;
          opacity: 0.9;
        }

        .timestamp {
          padding: 8px 20px;
          font-size: 11px;
          opacity: 0.6;
          border-top: 1px solid rgba(255,255,255,0.1);
        }

        .loading-bubble {
          background: rgba(255, 255, 255, 0.9);
          backdrop-filter: blur(10px);
          border: 1px solid rgba(255, 140, 66, 0.3);
          border-radius: 20px;
          padding: 20px;
          display: flex;
          align-items: center;
          gap: 12px;
          max-width: 700px;
        }

        .loading-dots {
          display: flex;
          gap: 6px;
        }

        .dot {
          color: #F05742;
          font-size: 12px;
          animation: bounce 1.4s infinite ease-in-out;
        }

        .dot:nth-child(2) {
          animation-delay: 0.15s;
        }

        .dot:nth-child(3) {
          animation-delay: 0.3s;
        }

        .loading-text {
          font-size: 14px;
          color: #8b4513;
        }

        .input-area {
          border-top: 1px solid rgba(255, 140, 66, 0.3);
          background: rgba(254, 243, 226, 0.95);
          backdrop-filter: blur(10px);
          padding: 20px;
        }

        .input-wrapper {
          max-width: 900px;
          margin: 0 auto;
          display: flex;
          gap: 12px;
        }

        .chat-input {
          flex: 1;
          padding: 14px 20px;
          background: white;
          border: 1px solid rgba(255, 140, 66, 0.4);
          border-radius: 12px;
          color: #4a4a4a;
          font-size: 15px;
          outline: none;
          transition: all 0.3s ease;
        }

        .chat-input:focus {
          border-color: #F05742;
          box-shadow: 0 0 0 3px rgba(255, 140, 66, 0.2);
        }

        .chat-input::placeholder {
          color: rgba(139, 69, 19, 0.4);
        }

        .send-button {
          padding: 14px 28px;
          background: linear-gradient(135deg, #F05742 0%, #F05742 100%);
          color: white;
          border: none;
          border-radius: 12px;
          font-size: 15px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.3s ease;
          box-shadow: 0 4px 12px rgba(255, 140, 66, 0.4);
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .send-button:hover:not(:disabled) {
          transform: translateY(-2px);
          box-shadow: 0 6px 16px rgba(255, 140, 66, 0.6);
        }

        .send-button:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .footer-text {
          text-align: center;
          font-size: 12px;
          color: rgba(139, 69, 19, 0.6);
          margin: 10px 0 0 0;
        }

        @keyframes bounce {
          0%, 100% {
            transform: translateY(0);
            opacity: 0.3;
          }
          50% {
            transform: translateY(-10px);
            opacity: 1;
          }
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
      `}</style>

      <div className="chat-container">
        {/* Header */}
        <div className="chat-header">
          <div className="header-content">
                {/* <img
                src="frontend\public\loco.png"
                alt="Company Logo"
                className="app-logo"
                /> */}
            <div>
              <h1 className="header-title">Jailbreak Detection</h1>            </div>
          </div>
        </div>

        {/* Messages Container */}
        <div className="messages-container">
          <div className="messages-inner">
            {messages.length === 0 && (
              <div className="empty-state">
                <div className="empty-state-card">
                  <div className="lock-icon">🔒</div>
                  <h2 className="empty-title">Jailbreak Testing Simulation</h2>
                  <p className="empty-text">Your messages are protected with real-time jailbreak detection and content filtering.</p>
                </div>
              </div>
            )}

            {messages.map((message, index) => (
              <div key={index} className={`message-row ${message.role}`}>
                <div className={`message-wrapper ${message.role}`}>
                  <div className={`message-bubble ${message.role}`}>
                    <div className="message-content">
                    <div className="icon-wrapper">
                    {message.role === 'user' && '👤'}

                    {message.role === 'system' && '⚠️'}

                    {message.role === 'ai' && (
                        <img
                        src={logo}
                        alt="AI Logo"
                        className="ai-logo-icon"
                        />
                    )}
                    </div>
                      <div className="message-text">
                        <p className="message-text-content">{message.content}</p>
                        
                        {message.security_scan && (
                          <div className={`security-scan ${message.security_scan.is_safe ? 'safe' : 'unsafe'}`}>
                            <div className="security-header">
                              <span className="security-icon">
                                {message.security_scan.is_safe ? '✓' : '⚠'}
                              </span>
                              <span className="security-level">
                                Security: {message.security_scan.risk_level}
                              </span>
                            </div>
                            <p className="security-message">
                              {message.security_scan.message}
                            </p>
                          </div>
                        )}
                      </div>
                    </div>
                    <div className="timestamp">
                      {new Date(message.timestamp).toLocaleTimeString()}
                    </div>
                  </div>
                </div>
              </div>
            ))}

            {loading && (
              <div className="message-row ai">
                <div className="loading-bubble">
                  <div className="loading-dots">
                    <span className="dot">●</span>
                    <span className="dot">●</span>
                    <span className="dot">●</span>
                  </div>
                  <span className="loading-text">AI is analyzing your message...</span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Input Area */}
        <div className="input-area">
          <div className="input-wrapper">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Type your message..."
              className="chat-input"
              disabled={loading}
            />
            <button
              onClick={sendMessage}
              disabled={loading || !input.trim()}
              className="send-button"
            >
              ✈️ {loading ? 'Sending...' : 'Send'}
            </button>
          </div>
          <p className="footer-text">@ iNextLabs</p>
        </div>
      </div>
    </>
  );
};

export default JailbreakProtectedChat;