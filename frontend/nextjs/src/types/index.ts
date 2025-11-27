export type User = {
  id: string;
  name: string;
  avatar?: string;
};

export type Group = {
  id: string;
  name: string;
  location: string;
  startDate: string; // YYYY-MM-DD
  endDate: string;   // YYYY-MM-DD
  members: User[];
  code: string; // Join code
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
  price: string;
  priceInt: number;
  rating: string;
  images: string[];
  url: string;
  amenities: Amenity[]; // Mocked for now
  roomType: RoomType; // Mocked for now
  bedrooms: number;
  beds: number;
  bathrooms: number;
};

export type VoteType = 'veto' | 'ok' | 'love';

export type Vote = {
  userId: string;
  listingId: string;
  type: VoteType;
  reason?: string; // For veto
};

