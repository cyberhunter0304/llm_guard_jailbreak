import { useState, useCallback, useEffect } from 'react';
import { Session, BotDetails, AllSessionDetails, SecurityStats } from '../types/index.ts';

/**
 * Hook for managing session data fetching
 */
export const useSessionData = (backendUrl) => {
  const [sessions, setSessions] = useState([]);
  const [botDetails, setBotDetails] = useState(null);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    totalSessions: 0,
    totalPrompts: 0,
    totalBlocked: 0,
    totalPII: 0,
    totalJailbreaks: 0,
    totalToxicity: 0,
    totalSecrets: 0
  });

  const fetchAllSessions = useCallback(async () => {
    try {
      setLoading(true);
      const response = await fetch(`${backendUrl}/api/security`);
      const data = await response.json();
      
      setSessions(data.sessions || []);
      
      const totalStats = (data.sessions || []).reduce((acc, session) => ({
        totalSessions: acc.totalSessions + 1,
        totalPrompts: acc.totalPrompts + (session.total_prompts || 0),
        totalBlocked: acc.totalBlocked + (session.blocked_prompts || 0),
        totalPII: acc.totalPII + (session.pii_detections || 0),
        totalJailbreaks: acc.totalJailbreaks + (session.jailbreak_attempts || 0),
        totalToxicity: acc.totalToxicity + (session.toxicity_detections || 0),
        totalSecrets: acc.totalSecrets + (session.secrets_detections || 0)
      }), {
        totalSessions: 0,
        totalPrompts: 0,
        totalBlocked: 0,
        totalPII: 0,
        totalJailbreaks: 0,
        totalToxicity: 0,
        totalSecrets: 0
      });
      
      setStats(totalStats);
      setLoading(false);
    } catch (error) {
      console.error('Failed to fetch sessions:', error);
      setLoading(false);
    }
  }, [backendUrl]);

  const fetchBotDetails = useCallback(async (botId) => {
    try {
      const response = await fetch(`${backendUrl}/api/security/${botId}`);
      const data = await response.json();
      setBotDetails(data);
      return data;
    } catch (error) {
      console.error('Failed to fetch bot details:', error);
      return null;
    }
  }, [backendUrl]);

  const deleteBotSession = useCallback(async (botId) => {
    try {
      await fetch(`${backendUrl}/api/security/${botId}`, {
        method: 'DELETE'
      });
      await fetchAllSessions();
      if (botDetails?.bot_id === botId) {
        setBotDetails(null);
      }
      return true;
    } catch (error) {
      console.error('Failed to delete session:', error);
      return false;
    }
  }, [backendUrl, botDetails?.bot_id, fetchAllSessions]);

  const clearAllSessions = useCallback(async () => {
    try {
      await Promise.all(sessions.map(session => 
        fetch(`${backendUrl}/api/security/${session.bot_id}`, { method: 'DELETE' })
      ));
      await fetchAllSessions();
      setBotDetails(null);
      return true;
    } catch (error) {
      console.error('Failed to clear all sessions:', error);
      return false;
    }
  }, [backendUrl, sessions, fetchAllSessions]);

  return {
    sessions,
    botDetails,
    loading,
    stats,
    setSessions,
    setBotDetails,
    fetchAllSessions,
    fetchBotDetails,
    deleteBotSession,
    clearAllSessions
  };
};

/**
 * Hook for managing session filtering and sorting
 */
export const useSessionFiltering = (sessions, searchTerm, searchMode, filterType, sortBy, promptSearchResults) => {
  const [filteredSessions, setFilteredSessions] = useState([]);

  const filterAndSortSessions = useCallback(() => {
    let filtered = [...sessions];

    // Apply search filters
    if (searchTerm) {
      if (searchMode === 'botId') {
        filtered = filtered.filter(session =>
          session.bot_id.toLowerCase().includes(searchTerm.toLowerCase())
        );
      } else if (searchMode === 'prompt') {
        const matchingBotIds = new Set(promptSearchResults.map(result => result.bot_id));
        if (matchingBotIds.size > 0) {
          filtered = filtered.filter(session => matchingBotIds.has(session.bot_id));
        } else if (searchTerm.length >= 3) {
          filtered = [];
        }
      }
    }

    // Apply threat filters
    if (filterType === 'threats') {
      filtered = filtered.filter(session =>
        session.pii_detections > 0 || 
        session.jailbreak_attempts > 0 || 
        session.toxicity_detections > 0 ||
        (session.secrets_detections || 0) > 0 ||
        session.blocked_prompts > 0
      );
    } else if (filterType === 'clean') {
      filtered = filtered.filter(session =>
        session.pii_detections === 0 && 
        session.jailbreak_attempts === 0 && 
        session.toxicity_detections === 0 &&
        (session.secrets_detections || 0) === 0 &&
        session.blocked_prompts === 0
      );
    } else if (filterType === 'pii') {
      filtered = filtered.filter(session => session.pii_detections > 0);
    } else if (filterType === 'jailbreak') {
      filtered = filtered.filter(session => session.jailbreak_attempts > 0);
    } else if (filterType === 'toxicity') {
      filtered = filtered.filter(session => session.toxicity_detections > 0);
    } else if (filterType === 'secrets') {
      filtered = filtered.filter(session => (session.secrets_detections || 0) > 0);
    }

    // Apply sorting
    filtered.sort((a, b) => {
      switch (sortBy) {
        case 'date-desc':
          return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
        case 'date-asc':
          return new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
        case 'threats-desc': {
          const threatsA = (a.pii_detections || 0) + (a.jailbreak_attempts || 0) + (a.toxicity_detections || 0) + (a.secrets_detections || 0);
          const threatsB = (b.pii_detections || 0) + (b.jailbreak_attempts || 0) + (b.toxicity_detections || 0) + (b.secrets_detections || 0);
          return threatsB - threatsA;
        }
        case 'prompts-desc':
          return (b.total_prompts || 0) - (a.total_prompts || 0);
        default:
          return 0;
      }
    });

    setFilteredSessions(filtered);
  }, [sessions, searchTerm, searchMode, filterType, sortBy, promptSearchResults]);

  useEffect(() => {
    filterAndSortSessions();
  }, [filterAndSortSessions]);

  return filteredSessions;
};

/**
 * Hook for fetching all session details
 */
export const useAllSessionDetails = (sessions, backendUrl) => {
  const [allSessionDetails, setAllSessionDetails] = useState({});
  const [loadingPromptData, setLoadingPromptData] = useState(false);

  const fetchAllSessionDetails = useCallback(async () => {
    setLoadingPromptData(true);
    const details = {};
    
    await Promise.all(
      sessions.map(async (session) => {
        try {
          const response = await fetch(`${backendUrl}/api/security/${session.bot_id}`);
          const data = await response.json();
          details[session.bot_id] = data;
        } catch (error) {
          console.error(`Failed to fetch details for ${session.bot_id}:`, error);
        }
      })
    );
    
    setAllSessionDetails(details);
    setLoadingPromptData(false);
  }, [sessions, backendUrl]);

  useEffect(() => {
    if (sessions.length > 0) {
      fetchAllSessionDetails();
    }
  }, [sessions, fetchAllSessionDetails]);

  return { allSessionDetails, loadingPromptData };
};

/**
 * Hook for searching prompts
 */
export const usePromptSearch = (searchTerm, searchMode, allSessionDetails) => {
  const [promptSearchResults, setPromptSearchResults] = useState([]);

  const searchPrompts = useCallback((query) => {
    if (!query || query.length < 3) {
      setPromptSearchResults([]);
      return;
    }

    const lowerQuery = query.toLowerCase();
    const results = [];

    Object.entries(allSessionDetails).forEach(([botId, details]) => {
      if (details.security_events) {
        const matchingEvents = details.security_events.filter(event => 
          event.prompt?.toLowerCase().includes(lowerQuery) ||
          event.anonymized_prompt?.toLowerCase().includes(lowerQuery) ||
          event.llm_response?.toLowerCase().includes(lowerQuery)
        );

        if (matchingEvents.length > 0) {
          results.push({
            bot_id: botId,
            matchCount: matchingEvents.length,
            matches: matchingEvents.map(event => ({
              prompt: event.prompt,
              timestamp: event.timestamp
            }))
          });
        }
      }
    });

    setPromptSearchResults(results);
  }, [allSessionDetails]);

  useEffect(() => {
    if (searchMode === 'prompt') {
      searchPrompts(searchTerm);
    } else if (searchMode === 'botId') {
      setPromptSearchResults([]);
    }
  }, [searchTerm, searchMode, searchPrompts]);

  return promptSearchResults;
};

/**
 * Hook for pagination
 */
export const usePagination = (items, itemsPerPage = 20) => {
  const [currentPage, setCurrentPage] = useState(1);

  const indexOfLastItem = currentPage * itemsPerPage;
  const indexOfFirstItem = indexOfLastItem - itemsPerPage;
  const currentItems = items.slice(indexOfFirstItem, indexOfLastItem);
  const totalPages = Math.ceil(items.length / itemsPerPage);

  const paginate = useCallback((pageNumber) => {
    setCurrentPage(pageNumber);
  }, []);

  const resetPage = useCallback(() => {
    setCurrentPage(1);
  }, []);

  return {
    currentPage,
    currentItems,
    totalPages,
    indexOfFirstItem,
    indexOfLastItem,
    paginate,
    resetPage
  };
};
