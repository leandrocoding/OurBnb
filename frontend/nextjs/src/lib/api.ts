/**
 * API Client for the Airbnb Group Voting backend.
 * Handles all HTTP requests and localStorage user management.
 */

// In Docker, nginx proxies /api/* to the backend on port 80
// Use empty string for relative URLs (works in browser)
const API_URL = process.env.NEXT_PUBLIC_API_URL || '';

// ============ LocalStorage User Management ============

const USER_STORAGE_KEY = 'airbnb_group_user';

export interface StoredUser {
  id: number;
  groupId: number;
  nickname: string;
  avatar?: string;
}

export function getStoredUser(): StoredUser | null {
  if (typeof window === 'undefined') return null;
  const stored = localStorage.getItem(USER_STORAGE_KEY);
  if (!stored) return null;
  try {
    return JSON.parse(stored);
  } catch {
    return null;
  }
}

export function setStoredUser(user: StoredUser): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(user));
}

export function clearStoredUser(): void {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(USER_STORAGE_KEY);
}

// ============ API Types (matching backend schemas) ============

export interface DestinationInfo {
  id: number;
  name: string;
}

export interface UserInfo {
  id: number;
  nickname: string;
  avatar?: string;
}

export interface GroupInfo {
  group_id: number;
  group_name: string;
  destinations: DestinationInfo[];
  date_start: string;
  date_end: string;
  adults: number;
  children: number;
  infants: number;
  pets: number;
  users: UserInfo[];
}

export interface CreateGroupRequest {
  group_name: string;
  destinations: string[];
  date_start: string;
  date_end: string;
  adults: number;
  children: number;
  infants: number;
  pets: number;
}

export interface CreateGroupResponse {
  group_id: number;
}

export interface JoinGroupRequest {
  group_id: number;
  username: string;
  avatar?: string;
}

export interface JoinGroupResponse {
  user_id: number;
}

export interface PropertyInfo {
  id: string;
  title: string;
  price: number;
  rating?: number;
  review_count?: number;
  images: string[];
  bedrooms?: number;
  beds?: number;
  bathrooms?: number;
  property_type?: string;
  amenities: number[];
}

export interface GroupListingsResponse {
  listings: PropertyInfo[];
}

export interface GroupVote {
  user_id: number;
  user_name: string;
  airbnb_id: string;
  vote: number;
  reason?: string;
}

export interface QueuedListing {
  airbnb_id: string;
  title: string;
  price: number;
  rating?: number;
  review_count?: number;
  images: string[];
  bedrooms?: number;
  beds?: number;
  bathrooms?: number;
  property_type?: string;
  amenities: number[];
  other_votes: GroupVote[];
}

export interface VotingQueueResponse {
  user_id: number;
  queue: QueuedListing[];
  total_unvoted: number;
}

export interface VoteRequest {
  user_id: number;
  airbnb_id: string;
  vote: number; // 0 = veto, 1 = ok, 2 = love, 3 = super love
  reason?: string;
}

export interface VoteResponse {
  user_id: number;
  airbnb_id: string;
  vote: number;
  reason?: string;
}

export interface NextToVoteResponse {
  airbnb_id?: string;
  title?: string;
  price?: number;
  rating?: number;
  review_count?: number;
  images: string[];
  bedrooms?: number;
  beds?: number;
  bathrooms?: number;
  property_type?: string;
  amenities: number[];
  other_votes: GroupVote[];
  booking_link?: string;
  has_listing: boolean;
  total_remaining: number;   // Unvoted listings for this user
  total_listings: number;    // Total listings in the group
}

export interface VoteWithNextResponse {
  user_id: number;
  airbnb_id: string;
  vote: number;
  reason?: string;
  next_listing?: NextToVoteResponse;
}

export interface LeaderboardVoteSummary {
  veto_count: number;
  ok_count: number;
  love_count: number;
  super_love_count: number;
}

export interface LeaderboardEntry {
  rank: number;
  airbnb_id: string;
  title: string;
  price: number;
  rating?: number;
  review_count?: number;
  images: string[];
  bedrooms?: number;
  beds?: number;
  bathrooms?: number;
  property_type?: string;
  amenities: number[];
  score: number;
  filter_matches: number;
  votes: LeaderboardVoteSummary;
  booking_link: string;
}

export interface LeaderboardResponse {
  entries: LeaderboardEntry[];
  total_listings: number;
  total_users: number;
}

export interface FilterResponse {
  user_id: number;
  min_price?: number;
  max_price?: number;
  min_bedrooms?: number;
  min_beds?: number;
  min_bathrooms?: number;
  property_type?: string;
  updated_at?: string;
  amenities?: number[];
}

export interface UserFilter {
  min_price?: number;
  max_price?: number;
  min_bedrooms?: number;
  min_beds?: number;
  min_bathrooms?: number;
  property_type?: string;
  amenities?: number[];
}

export interface VoteProgressResponse {
  user_id: number;
  votes_cast: number;
  total_listings: number;
  remaining: number;
  completion_percent: number;
}

// ============ API Functions ============

async function fetchApi<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_URL}${endpoint}`;
  
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `API Error: ${response.status}`);
  }

  // Handle empty responses
  const text = await response.text();
  if (!text) return null as T;
  
  return JSON.parse(text);
}

// ============ Groups API ============

export async function createGroup(data: CreateGroupRequest): Promise<CreateGroupResponse> {
  return fetchApi<CreateGroupResponse>('/api/group/create', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function getGroupInfo(groupId: number): Promise<GroupInfo> {
  return fetchApi<GroupInfo>(`/api/group/info/${groupId}`);
}

export async function joinGroup(
  groupId: number,
  username: string,
  avatar?: string
): Promise<JoinGroupResponse> {
  return fetchApi<JoinGroupResponse>('/api/group/join', {
    method: 'POST',
    body: JSON.stringify({
      group_id: groupId,
      username,
      avatar,
    }),
  });
}

// ============ Listings API ============

export async function getGroupListings(groupId: number): Promise<GroupListingsResponse> {
  return fetchApi<GroupListingsResponse>(`/api/group/${groupId}/listings`);
}

export async function getVotingQueue(
  userId: number,
  limit: number = 10
): Promise<VotingQueueResponse> {
  return fetchApi<VotingQueueResponse>(`/api/user/${userId}/queue?limit=${limit}`);
}

export async function getVoteProgress(userId: number): Promise<VoteProgressResponse> {
  return fetchApi<VoteProgressResponse>(`/api/user/${userId}/vote-progress`);
}

// ============ Votes API ============

export async function submitVote(
  userId: number,
  airbnbId: string,
  vote: number,
  reason?: string
): Promise<VoteWithNextResponse> {
  return fetchApi<VoteWithNextResponse>('/api/vote', {
    method: 'POST',
    body: JSON.stringify({
      user_id: userId,
      airbnb_id: airbnbId,
      vote,
      reason,
    }),
  });
}

// ============ Next To Vote API ============

export async function getNextToVote(
  userId: number,
  excludeAirbnbIds?: string[]
): Promise<NextToVoteResponse> {
  const params = excludeAirbnbIds?.length ? `?exclude_ids=${excludeAirbnbIds.join(',')}` : '';
  return fetchApi<NextToVoteResponse>(`/api/user/${userId}/next-to-vote${params}`);
}

// ============ Leaderboard API ============

export async function getLeaderboard(groupId: number): Promise<LeaderboardResponse> {
  return fetchApi<LeaderboardResponse>(`/api/group/${groupId}/leaderboard`);
}

// WebSocket URL for real-time leaderboard updates
export function getLeaderboardWebSocketUrl(groupId: number): string {
  // Handle empty API_URL (relative URLs) by using current host
  if (!API_URL || API_URL === '') {
    const wsProtocol = typeof window !== 'undefined' && window.location.protocol === 'https:' ? 'wss' : 'ws';
    const host = typeof window !== 'undefined' ? window.location.host : 'localhost';
    return `${wsProtocol}://${host}/api/ws/leaderboard/${groupId}`;
  }
  const wsProtocol = API_URL.startsWith('https') ? 'wss' : 'ws';
  const wsHost = API_URL.replace(/^https?:\/\//, '');
  return `${wsProtocol}://${wsHost}/api/ws/leaderboard/${groupId}`;
}

// ============ Filters API ============

export async function getUserFilters(userId: number): Promise<FilterResponse> {
  return fetchApi<FilterResponse>(`/api/filter/${userId}`);
}

export async function updateUserFilters(
  userId: number,
  filters: UserFilter
): Promise<FilterResponse> {
  return fetchApi<FilterResponse>(`/api/filter/${userId}`, {
    method: 'PATCH',
    body: JSON.stringify(filters),
  });
}

// ============ Demo API ============

export interface DemoGroupInfo {
  group_id: number;
  group_name: string;
  users: UserInfo[];
}

export interface DemoAllGroupsResponse {
  groups: DemoGroupInfo[];
}

export async function getAllGroupsForDemo(): Promise<DemoAllGroupsResponse> {
  return fetchApi<DemoAllGroupsResponse>('/api/demo/groups');
}
