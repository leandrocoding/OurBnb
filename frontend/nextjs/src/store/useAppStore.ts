'use client';

// @ts-ignore - zustand types may not be available in all environments
import { create } from 'zustand';
import { Filters } from '../types';

export interface StoredUser {
  id: number;
  groupId: number;
  nickname: string;
  avatar?: string;
}

interface AppState {
  // User state (persisted manually to localStorage)
  currentUser: StoredUser | null;
  
  // Local filters state (for the filters page before saving to backend)
  filters: Filters;
  
  // Actions
  setCurrentUser: (user: StoredUser | null) => void;
  setFilters: (filters: Filters) => void;
  clearUser: () => void;
  hydrate: () => void;
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

  setCurrentUser: (user: StoredUser | null) => {
    set({ currentUser: user });
    saveState(user, get().filters);
  },
  
  setFilters: (filters: Filters) => {
    set({ filters });
    saveState(get().currentUser, filters);
  },
  
  clearUser: () => {
    set({ currentUser: null });
    saveState(null, get().filters);
  },
  
  hydrate: () => {
    const stored = getStoredState();
    if (stored) {
      set({ 
        currentUser: stored.currentUser, 
        filters: stored.filters || { amenities: [] } 
      });
    }
  },
}));

// Auto-hydrate on client side
if (typeof window !== 'undefined') {
  // Use setTimeout to ensure this runs after initial render
  setTimeout(() => {
    useAppStore.getState().hydrate();
  }, 0);
}
