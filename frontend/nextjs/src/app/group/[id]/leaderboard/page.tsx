"use client";

import { useEffect, useState, useRef, useCallback } from 'react';
import { useParams } from 'next/navigation';
import { useAppStore } from '../../../../store/useAppStore';
import { getLeaderboard, getLeaderboardWebSocketUrl, LeaderboardEntry, LeaderboardResponse } from '../../../../lib/api';
import Link from 'next/link';
import { Trophy, Heart, ThumbsUp, AlertCircle, Loader2, Users, RefreshCw } from 'lucide-react';

export default function LeaderboardPage() {
  const { id } = useParams();
  const { currentUser } = useAppStore();
  
  const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>([]);
  const [totalListings, setTotalListings] = useState(0);
  const [totalUsers, setTotalUsers] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const mountedRef = useRef(true);

  const groupId = typeof id === 'string' ? parseInt(id, 10) : null;

  // Fetch leaderboard via REST API (fallback)
  const fetchLeaderboard = useCallback(async () => {
    if (!groupId || !mountedRef.current) return;

    try {
      const response = await getLeaderboard(groupId);
      if (mountedRef.current) {
        setLeaderboard(response.entries);
        setTotalListings(response.total_listings);
        setTotalUsers(response.total_users);
        setError(null);
      }
    } catch (err) {
      if (mountedRef.current) {
        setError(err instanceof Error ? err.message : 'Failed to load leaderboard');
      }
    } finally {
      if (mountedRef.current) {
        setIsLoading(false);
      }
    }
  }, [groupId]);

  // Connect to WebSocket for real-time updates
  const connectWebSocket = useCallback(() => {
    if (!groupId || !mountedRef.current) return;

    // Clean up existing connection
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    try {
      const wsUrl = getLeaderboardWebSocketUrl(groupId);
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        if (mountedRef.current) {
          setIsConnected(true);
          setError(null);
        }
      };

      ws.onmessage = (event) => {
        if (!mountedRef.current) return;
        
        try {
          const data = JSON.parse(event.data);
          
          if (data.type === 'ping') {
            // Respond to ping to keep connection alive
            return;
          }

          if (data.entries) {
            setLeaderboard(data.entries);
            if (data.total_listings !== undefined) {
              setTotalListings(data.total_listings);
            }
            if (data.total_users !== undefined) {
              setTotalUsers(data.total_users);
            }
            setIsLoading(false);
          }
        } catch {
          // Ignore parse errors silently
        }
      };

      ws.onerror = () => {
        if (mountedRef.current) {
          setIsConnected(false);
        }
      };

      ws.onclose = () => {
        if (mountedRef.current) {
          setIsConnected(false);
          
          // Only attempt to reconnect if still mounted and not already reconnecting
          if (!reconnectTimeoutRef.current) {
            reconnectTimeoutRef.current = setTimeout(() => {
              reconnectTimeoutRef.current = null;
              if (mountedRef.current) {
                connectWebSocket();
              }
            }, 5000);
          }
        }
      };

      wsRef.current = ws;
    } catch {
      // WebSocket construction failed, will retry via REST
      if (mountedRef.current) {
        setIsConnected(false);
      }
    }
  }, [groupId]);

  // Initial load and WebSocket connection
  useEffect(() => {
    mountedRef.current = true;
    
    // First fetch via REST for immediate data
    fetchLeaderboard();
    
    // Then connect WebSocket for real-time updates
    connectWebSocket();

    // Cleanup on unmount
    return () => {
      mountedRef.current = false;
      
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
    };
  }, [fetchLeaderboard, connectWebSocket]);

  // Manual refresh
  const handleRefresh = () => {
    setIsLoading(true);
    fetchLeaderboard();
  };

  // Calculate match percentage from score (simplified visualization)
  const getMatchPercent = (entry: LeaderboardEntry) => {
    // Score-based percentage, clamped between 0-100
    const baseScore = 50;
    const percent = Math.min(100, Math.max(0, baseScore + (entry.score * 2)));
    return Math.round(percent);
  };

  if (isLoading && leaderboard.length === 0) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-rose-500 mx-auto mb-4" />
          <p className="text-slate-600">Loading leaderboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full pb-24 overflow-y-auto">
      <header className="bg-white px-6 py-4 shadow-sm sticky top-0 z-10">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="font-bold text-slate-900 text-xl">Top Picks</h1>
            <p className="mt-1 text-sm text-slate-500">Based on Group Happiness Score</p>
          </div>
          <div className="flex items-center gap-3">
            {/* Connection status */}
            <div 
              className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-slate-300'}`} 
              title={isConnected ? 'Live updates active' : 'Connecting...'} 
            />
            
            {/* Refresh button */}
            <button
              onClick={handleRefresh}
              disabled={isLoading}
              className="p-2 rounded-lg hover:bg-slate-100 transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`w-5 h-5 text-slate-500 ${isLoading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>
        
        {/* Stats bar */}
        <div className="flex gap-4 mt-3 text-sm">
          <div className="flex items-center gap-1.5 text-slate-600">
            <Trophy className="w-4 h-4 text-yellow-500" />
            <span>{totalListings} listings</span>
          </div>
          <div className="flex items-center gap-1.5 text-slate-600">
            <Users className="w-4 h-4 text-blue-500" />
            <span>{totalUsers} voters</span>
          </div>
        </div>
      </header>

      {error && (
        <div className="mx-6 mt-4 p-3 bg-red-50 border border-red-200 rounded-xl text-red-600 text-sm flex items-center gap-2">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          {error}
        </div>
      )}

      {leaderboard.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center p-6 text-center">
          <div className="text-5xl mb-4">📭</div>
          <h2 className="text-xl font-bold text-slate-900 mb-2">No rankings yet</h2>
          <p className="text-slate-600 mb-6">Start voting to see the leaderboard!</p>
          <Link 
            href={`/group/${id}`}
            className="bg-rose-500 text-white px-6 py-3 rounded-full font-bold shadow-lg"
          >
            Start Voting
          </Link>
        </div>
      ) : (
        <div className="p-6 flex flex-col gap-4">
          {leaderboard.map((entry) => (
            <div key={entry.airbnb_id} className="bg-white rounded-2xl p-4 shadow-sm flex gap-4">
              <div className="relative w-24 h-24 flex-shrink-0 rounded-xl overflow-hidden bg-slate-100">
                {entry.images[0] && (
                  <img 
                    src={entry.images[0]} 
                    alt={entry.title} 
                    className="absolute inset-0 w-full h-full object-cover" 
                  />
                )}
                <div className={`absolute top-1 left-1 text-xs font-bold px-1.5 py-0.5 rounded text-white ${
                  entry.rank === 1 ? 'bg-yellow-500' : 
                  entry.rank === 2 ? 'bg-slate-400' : 
                  entry.rank === 3 ? 'bg-amber-600' : 'bg-slate-500'
                }`}>
                  #{entry.rank}
                </div>
              </div>
              
              <div className="flex-1 min-w-0">
                <div className="flex justify-between items-start">
                  <h3 className="font-bold text-slate-900 truncate pr-2">{entry.title}</h3>
                  <span className="font-bold text-green-600 flex-shrink-0">{getMatchPercent(entry)}%</span>
                </div>
                
                <p className="text-slate-600 text-sm mb-2">
                  CHF {entry.price} / night
                </p>
                
                <div className="flex gap-2 flex-wrap">
                  {entry.votes.love_count > 0 && (
                    <div className="flex items-center gap-1 text-xs font-medium text-rose-500 bg-rose-50 px-2 py-1 rounded">
                      <Heart className="w-3 h-3 fill-current" /> {entry.votes.love_count}
                    </div>
                  )}
                  {entry.votes.super_love_count > 0 && (
                    <div className="flex items-center gap-1 text-xs font-medium text-pink-500 bg-pink-50 px-2 py-1 rounded">
                      <Heart className="w-3 h-3 fill-current" /> {entry.votes.super_love_count} Super
                    </div>
                  )}
                  {entry.votes.ok_count > 0 && (
                    <div className="flex items-center gap-1 text-xs font-medium text-blue-500 bg-blue-50 px-2 py-1 rounded">
                      <ThumbsUp className="w-3 h-3" /> {entry.votes.ok_count}
                    </div>
                  )}
                  {entry.votes.veto_count > 0 && (
                    <div className="flex items-center gap-1 text-xs font-medium text-red-500 bg-red-50 px-2 py-1 rounded">
                      <AlertCircle className="w-3 h-3" /> {entry.votes.veto_count} veto
                    </div>
                  )}
                </div>
                
                {entry.filter_matches > 0 && (
                  <p className="text-xs text-slate-400 mt-2">
                    Matches {entry.filter_matches} user filter{entry.filter_matches > 1 ? 's' : ''}
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
