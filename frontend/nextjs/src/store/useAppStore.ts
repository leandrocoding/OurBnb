'use client';

// @ts-ignore - zustand types may not be available in all environments
import { create } from 'zustand';
import { Filters } from '../types';
import { RecommendationListing, getRecommendations } from '../lib/api';

export interface StoredUser {
  id: number;
  groupId: number;
  nickname: string;
  avatar?: string;
}

// Threshold for fetching more recommendations
const REFETCH_THRESHOLD = 3;
const BATCH_SIZE = 10;

interface AppState {
  // User state (persisted manually to localStorage)
  currentUser: StoredUser | null;
  
  // Local filters state (for the filters page before saving to backend)
  filters: Filters;
  
  // Hydration state - true once localStorage has been loaded
  isHydrated: boolean;
  
  // Recommendations state (not persisted)
  recommendations: RecommendationListing[];
  currentIndex: number;
  totalRemaining: number;
  hasMore: boolean;
  isLoadingRecommendations: boolean;
  recommendationsError: string | null;
  // Version number - increment to trigger refetch (e.g., on filter/group change)
  recommendationsVersion: number;
  
  // Actions
  setCurrentUser: (user: StoredUser | null) => void;
  setFilters: (filters: Filters) => void;
  clearUser: () => void;
  hydrate: () => void;
  
  // Recommendations actions
  fetchRecommendations: (force?: boolean) => Promise<void>;
  advanceToNextCard: () => void;
  clearRecommendations: () => void;
  invalidateRecommendations: () => void;  // Call when filters or group settings change
}

const STORAGE_KEY = 'airbnb-group-storage';

// Manual persistence helper
const getStoredState = (): { currentUser: StoredUser | null; filters: Filters } | null => {
  if (typeof window === 'undefined') return null;
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      return JSON.parse(stored);
    }
  } catch {
    // Ignore parse errors
  }
  return null;
};

const saveState = (currentUser: StoredUser | null, filters: Filters) => {
  if (typeof window === 'undefined') return;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ currentUser, filters }));
  } catch {
    // Ignore storage errors
  }
};

type SetState = (partial: Partial<AppState> | ((state: AppState) => Partial<AppState>)) => void;
type GetState = () => AppState;

export const useAppStore = create<AppState>()((set: SetState, get: GetState) => ({
  currentUser: null,
  filters: {
    amenities: [],
  },
  isHydrated: false,
  
  // Recommendations initial state
  recommendations: [],
  currentIndex: 0,
  totalRemaining: 0,
  hasMore: false,
  isLoadingRecommendations: false,
  recommendationsError: null,
  recommendationsVersion: 0,

  setCurrentUser: (user: StoredUser | null) => {
    set({ currentUser: user });
    saveState(user, get().filters);
  },
  
  setFilters: (filters: Filters) => {
    set({ filters });
    saveState(get().currentUser, filters);
    // Invalidate recommendations when filters change
    get().invalidateRecommendations();
  },
  
  clearUser: () => {
    set({ currentUser: null });
    saveState(null, get().filters);
    // Clear recommendations when user logs out
    get().clearRecommendations();
  },
  
  hydrate: () => {
    const stored = getStoredState();
    if (stored) {
      set({ 
        currentUser: stored.currentUser, 
        filters: stored.filters || { amenities: [] },
        isHydrated: true,
      });
    } else {
      set({ isHydrated: true });
    }
  },
  
  // Fetch recommendations from the API
  fetchRecommendations: async (force = false) => {
    const state = get();
    const { currentUser, recommendations, currentIndex, isLoadingRecommendations } = state;
    
    // Don't fetch if already loading
    if (isLoadingRecommendations) return;
    
    // Don't fetch if no user
    if (!currentUser) return;
    
    // Calculate remaining items in local buffer
    const remainingInBuffer = recommendations.length - currentIndex;
    
    // Only fetch if forced or running low
    if (!force && remainingInBuffer > REFETCH_THRESHOLD) return;
    
    set({ isLoadingRecommendations: true, recommendationsError: null });
    
    try {
      // Get IDs of listings still in our local buffer (to exclude from new fetch)
      const excludeIds = recommendations.slice(currentIndex).map(r => r.airbnb_id);
      
      const response = await getRecommendations(currentUser.id, BATCH_SIZE, excludeIds);
      
      set((state) => {
        // Append new recommendations to the end of the current buffer
        const currentBuffer = state.recommendations.slice(state.currentIndex);
        const newRecommendations = [...currentBuffer, ...response.recommendations];
        
        return {
          recommendations: newRecommendations,
          currentIndex: 0, // Reset index since we rebuilt the array
          totalRemaining: response.total_remaining,
          hasMore: response.has_more,
          isLoadingRecommendations: false,
        };
      });
    } catch (error) {
      set({ 
        isLoadingRecommendations: false,
        recommendationsError: error instanceof Error ? error.message : 'Failed to fetch recommendations',
      });
    }
  },
  
  // Move to the next card after voting
  advanceToNextCard: () => {
    set((state) => {
      const newIndex = state.currentIndex + 1;
      const remainingInBuffer = state.recommendations.length - newIndex;
      
      // Trigger fetch if running low (but don't await it)
      if (remainingInBuffer <= REFETCH_THRESHOLD && state.hasMore) {
        // Use setTimeout to avoid calling fetch during render
        setTimeout(() => get().fetchRecommendations(), 0);
      }
      
      return { currentIndex: newIndex };
    });
  },
  
  // Clear all recommendations (e.g., on logout or group change)
  clearRecommendations: () => {
    set({
      recommendations: [],
      currentIndex: 0,
      totalRemaining: 0,
      hasMore: false,
      isLoadingRecommendations: false,
      recommendationsError: null,
    });
  },
  
  // Invalidate recommendations (triggers refetch)
  invalidateRecommendations: () => {
    set((state) => ({
      recommendations: [],
      currentIndex: 0,
      recommendationsVersion: state.recommendationsVersion + 1,
    }));
  },
}));

// Auto-hydrate on client side
if (typeof window !== 'undefined') {
  // Use setTimeout to ensure this runs after initial render
  setTimeout(() => {
    useAppStore.getState().hydrate();
  }, 0);
}
