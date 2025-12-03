// Vote types as numbers matching backend (0=veto, 1=ok, 2=love, 3=super_love)
export type VoteValue = 0 | 1 | 2 | 3;

export const VOTE_VETO = 0;
export const VOTE_OK = 1;
export const VOTE_LOVE = 2;
export const VOTE_SUPER_LOVE = 3;

// Legacy string type for backward compatibility during transition
export type VoteType = 'veto' | 'ok' | 'love' | 'super_love';

// Helper to convert string vote type to number
export function voteTypeToNumber(type: VoteType): VoteValue {
  switch (type) {
    case 'veto': return VOTE_VETO;
    case 'ok': return VOTE_OK;
    case 'love': return VOTE_LOVE;
    case 'super_love': return VOTE_SUPER_LOVE;
  }
}

// Helper to convert number to string vote type
export function voteNumberToType(vote: VoteValue): VoteType {
  switch (vote) {
    case 0: return 'veto';
    case 1: return 'ok';
    case 2: return 'love';
    case 3: return 'super_love';
  }
}

export type User = {
  id: number;
  nickname: string;
  avatar?: string;
};

export type Destination = {
  id: number;
  name: string;
};

export type Group = {
  id: number;
  name: string;
  destinations: Destination[];
  dateStart: string; // YYYY-MM-DD
  dateEnd: string;   // YYYY-MM-DD
  adults: number;
  children: number;
  infants: number;
  pets: number;
  members: User[];
};

export enum Amenity {
  WIFI = 4,
  KITCHEN = 8,
  WASHER = 33,
  DEDICATED_WORKSPACE = 47,
  TV = 58,
  POOL = 7,
  HOT_TUB = 25,
  FREE_PARKING = 9,
  EV_CHARGER = 97,
  CRIB = 286,
  KING_BED = 1000,
  GYM = 15,
  BBQ_GRILL = 99,
  BREAKFAST = 16,
  INDOOR_FIREPLACE = 27,
  SMOKING_ALLOWED = 11,
  SMOKE_ALARM = 35,
  CARBON_MONOXIDE_ALARM = 36,
  AC = 5,
}

export enum RoomType {
  ENTIRE_HOME = "Entire home/apt",
  PRIVATE_ROOM = "Private room",
}

export type Filters = {
  priceMin?: number;
  priceMax?: number;
  amenities: Amenity[];
  roomType?: RoomType;
  minBedrooms?: number;
  minBeds?: number;
  minBathrooms?: number;
};

export type Listing = {
  id: string;
  title: string;
  price: number;
  rating?: number;
  reviewCount?: number;
  images: string[];
  amenities: number[];
  propertyType?: string;
  bedrooms?: number;
  beds?: number;
  bathrooms?: number;
};

export type Vote = {
  userId: number;
  listingId: string;
  vote: VoteValue;
  reason?: string;
};

export type OtherVote = {
  userId: number;
  userName: string;
  vote: VoteValue;
};
