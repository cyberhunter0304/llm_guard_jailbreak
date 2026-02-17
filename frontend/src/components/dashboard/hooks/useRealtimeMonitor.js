/**
 * useRealtimeMonitor Hook
 * Connects to SSE stream for real-time conversation processing updates
 */
import { useState, useEffect, useCallback, useRef } from 'react';

export const useRealtimeMonitor = (backendUrl, enabled = true) => {
  const [isConnected, setIsConnected] = useState(false);
  const [isMonitoring, setIsMonitoring] = useState(false);
  const [stats, setStats] = useState({
    processedCount: 0,
    errorCount: 0
  });
  const [recentEvents, setRecentEvents] = useState([]);
  const [error, setError] = useState(null);
  
  const eventSourceRef = useRef(null);
  const maxRecentEvents = 50; // Keep last 50 events

  // Connect to SSE stream
  const connect = useCallback(() => {
    if (!enabled || eventSourceRef.current) return;

    try {
      const eventSource = new EventSource(`${backendUrl}/api/monitor/stream`);
      eventSourceRef.current = eventSource;

      eventSource.onopen = () => {
        console.log('✅ SSE connection opened');
        setIsConnected(true);
        setError(null);
      };

      eventSource.onerror = (err) => {
        console.error('❌ SSE connection error:', err);
        setIsConnected(false);
        setError('Connection lost. Reconnecting...');
        
        // Auto-reconnect after 5 seconds
        setTimeout(() => {
          if (eventSourceRef.current) {
            eventSourceRef.current.close();
            eventSourceRef.current = null;
            connect();
          }
        }, 5000);
      };

      // Event: Monitor started
      eventSource.addEventListener('started', (e) => {
        const data = JSON.parse(e.data);
        console.log('🚀 Monitor started:', data);
        setIsMonitoring(true);
      });

      // Event: Processing a conversation
      eventSource.addEventListener('processing', (e) => {
        const data = JSON.parse(e.data);
        console.log('⚙️ Processing conversation:', data);
        
        addEvent({
          type: 'processing',
          ...data,
          status: 'in-progress'
        });
      });

      // Event: Conversation processed
      eventSource.addEventListener('processed', (e) => {
        const data = JSON.parse(e.data);
        console.log('✅ Conversation processed:', data);
        
        // Update stats
        setStats({
          processedCount: data.total_processed || 0,
          errorCount: data.total_errors || 0
        });
        
        addEvent({
          type: 'processed',
          ...data,
          status: 'completed'
        });
      });

      // Event: Stats update
      eventSource.addEventListener('stats', (e) => {
        const data = JSON.parse(e.data);
        setStats({
          processedCount: data.processed_count || 0,
          errorCount: data.error_count || 0
        });
      });

      // Event: Error
      eventSource.addEventListener('error', (e) => {
        const data = JSON.parse(e.data);
        console.error('❌ Monitor error:', data);
        setError(data.message);
        
        addEvent({
          type: 'error',
          ...data,
          status: 'error'
        });
      });

      // Event: Monitor stopped
      eventSource.addEventListener('stopped', (e) => {
        const data = JSON.parse(e.data);
        console.log('⏹️ Monitor stopped:', data);
        setIsMonitoring(false);
        
        // Update final stats
        setStats({
          processedCount: data.total_processed || 0,
          errorCount: data.total_errors || 0
        });
      });

    } catch (err) {
      console.error('Failed to create SSE connection:', err);
      setError(err.message);
    }
  }, [backendUrl, enabled]);

  // Disconnect from SSE stream
  const disconnect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
      setIsConnected(false);
      setIsMonitoring(false);
      console.log('SSE connection closed');
    }
  }, []);

  // Add event to recent events list
  const addEvent = useCallback((event) => {
    setRecentEvents(prev => {
      const newEvents = [event, ...prev].slice(0, maxRecentEvents);
      return newEvents;
    });
  }, []);

  // Start monitoring
  const startMonitor = useCallback(async () => {
    try {
      const response = await fetch(`${backendUrl}/api/monitor/start`, {
        method: 'POST'
      });
      const data = await response.json();
      
      if (data.success) {
        connect();
      } else {
        setError(data.message);
      }
      
      return data;
    } catch (err) {
      setError(err.message);
      return { success: false, message: err.message };
    }
  }, [backendUrl, connect]);

  // Stop monitoring
  const stopMonitor = useCallback(async () => {
    try {
      const response = await fetch(`${backendUrl}/api/monitor/stop`, {
        method: 'POST'
      });
      const data = await response.json();
      
      disconnect();
      
      return data;
    } catch (err) {
      setError(err.message);
      return { success: false, message: err.message };
    }
  }, [backendUrl, disconnect]);

  // Get monitor status
  const getStatus = useCallback(async () => {
    try {
      const response = await fetch(`${backendUrl}/api/monitor/status`);
      const data = await response.json();
      
      setIsMonitoring(data.running);
      setStats({
        processedCount: data.processed_count || 0,
        errorCount: data.error_count || 0
      });
      
      return data;
    } catch (err) {
      setError(err.message);
      return null;
    }
  }, [backendUrl]);

  // Auto-connect on mount if enabled
  useEffect(() => {
    if (enabled) {
      getStatus().then(status => {
        if (status && status.running) {
          connect();
        }
      });
    }

    return () => {
      disconnect();
    };
  }, [enabled, connect, disconnect, getStatus]);

  return {
    isConnected,
    isMonitoring,
    stats,
    recentEvents,
    error,
    startMonitor,
    stopMonitor,
    getStatus,
    connect,
    disconnect
  };
};

export default useRealtimeMonitor;