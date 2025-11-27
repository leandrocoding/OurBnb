import { create } from 'zustand';
import { Group, Listing, User, Vote, Filters, Amenity, RoomType } from '../types';

interface AppState {
  currentUser: User | null;
  currentGroup: Group | null;
  listings: Listing[];
  votes: Vote[];
  filters: Filters;
  
  setCurrentUser: (user: User) => void;
  createGroup: (group: Group) => void;
  joinGroup: (groupCode: string, user: User) => void;
  setFilters: (filters: Filters) => void;
  addVote: (vote: Vote) => void;
  
  // Computed/Actions
  getGroupListings: () => Listing[];
  getLeaderboard: () => { listing: Listing; score: number; loves: number; vetos: number }[];
}

// Mock Data
const MOCK_LISTINGS: Listing[] = [
    {
        "id": "1539600029584542590",
        "title": "Chocolate Suite – kostenloses Parken",
        "price": "496 CHF",
        "priceInt": 496,
        "rating": "New",
        "images": [
            "https://a0.muscache.com/im/pictures/hosting/Hosting-1539600029584542590/original/fe2b4caa-768e-493a-a4a2-079fe58619c1.jpeg",
            "https://a0.muscache.com/im/pictures/hosting/Hosting-1539600029584542590/original/b6a7929e-821a-4a1b-ae6b-19224e0d0c6c.jpeg",
            "https://a0.muscache.com/im/pictures/hosting/Hosting-1539600029584542590/original/fd4c21f5-c585-4ddf-9657-5a34c7091f7d.jpeg",
            "https://a0.muscache.com/im/pictures/hosting/Hosting-1539600029584542590/original/8543f237-5ee5-430a-96fd-5b29898acd7a.jpeg",
            "https://a0.muscache.com/im/pictures/hosting/Hosting-1539600029584542590/original/9c3a41c1-6953-493b-9639-78f495170d73.jpeg",
            "https://a0.muscache.com/im/pictures/hosting/Hosting-1539600029584542590/original/4eb115cf-2743-4462-9b60-332a3e8e5f31.jpeg"
        ],
        "url": "https://www.airbnb.ch/rooms/1539600029584542590",
        "amenities": [Amenity.WIFI, Amenity.KITCHEN],
        "roomType": RoomType.ENTIRE_HOME,
        "bedrooms": 2,
        "beds": 2,
        "bathrooms": 1,
    },
    {
        "id": "2920698",
        "title": "3-Zimmer-Wohnung in einer historischen Altstadt",
        "price": "465 CHF",
        "priceInt": 465,
        "rating": "4.69 (213)",
        "images": [
            "https://a0.muscache.com/im/pictures/miso/Hosting-2920698/original/fe6a0410-0b67-4fee-b7eb-6188a8b2b9c6.jpeg",
            "https://a0.muscache.com/im/pictures/miso/Hosting-2920698/original/fcb7cc77-a885-476f-99e9-99af9e767a11.jpeg",
            "https://a0.muscache.com/im/pictures/miso/Hosting-2920698/original/829988a9-32b0-4270-af51-bcceed428212.jpeg",
            "https://a0.muscache.com/im/pictures/38325297/39d9a62b_original.jpg",
            "https://a0.muscache.com/im/pictures/38325332/b3a7b9ed_original.jpg",
            "https://a0.muscache.com/im/pictures/87ad7d62-189d-4cc8-b8c0-59f5bc95aa87.jpg"
        ],
        "url": "https://www.airbnb.ch/rooms/2920698",
        "amenities": [Amenity.WIFI, Amenity.KITCHEN, Amenity.AC],
        "roomType": RoomType.ENTIRE_HOME,
        "bedrooms": 3,
        "beds": 4,
        "bathrooms": 1,
    },
    {
        "id": "48587690",
        "title": "Zürich & Airport nah – Wohnung mit Klimaanlage",
        "price": "464 CHF",
        "priceInt": 464,
        "rating": "5.0 (69)",
        "images": [
            "https://a0.muscache.com/im/pictures/hosting/Hosting-48587690/original/0be81a27-79d6-43aa-a893-1d4eac65749a.jpeg",
            "https://a0.muscache.com/im/pictures/hosting/Hosting-48587690/original/a19329b9-436a-4eeb-99ff-625859c313f8.jpeg",
            "https://a0.muscache.com/im/pictures/hosting/Hosting-48587690/original/6ff1a561-bb56-4366-b6a6-0458477e2536.jpeg",
            "https://a0.muscache.com/im/pictures/hosting/Hosting-48587690/original/8ee61333-a0e0-4d6d-b0f9-d02e7d3d595e.jpeg",
            "https://a0.muscache.com/im/pictures/miso/Hosting-48587690/original/b7ac5acd-4603-4927-931f-ce78669422f6.jpeg",
            "https://a0.muscache.com/im/pictures/hosting/Hosting-48587690/original/01087e3a-5ef7-4231-ba06-a8634e4beaba.jpeg"
        ],
        "url": "https://www.airbnb.ch/rooms/48587690",
        "amenities": [Amenity.WIFI, Amenity.AC, Amenity.KITCHEN],
        "roomType": RoomType.ENTIRE_HOME,
        "bedrooms": 2,
        "beds": 2,
        "bathrooms": 1,
    },
    {
        "id": "1182448378761473867",
        "title": "Charmante Wohnung nähe Flughafen und Zürich City",
        "price": "441 CHF",
        "priceInt": 441,
        "rating": "4.92 (61)",
        "images": [
            "https://a0.muscache.com/im/pictures/hosting/Hosting-1182448378761473867/original/7c4e1ad7-0490-4a73-a8c9-127acaa2321f.jpeg",
            "https://a0.muscache.com/im/pictures/hosting/Hosting-1182448378761473867/original/5db02718-6c71-4395-8a07-d15ffe100a73.jpeg",
            "https://a0.muscache.com/im/pictures/hosting/Hosting-1182448378761473867/original/005ecce1-329b-4b42-8287-b392b98ef508.jpeg",
            "https://a0.muscache.com/im/pictures/hosting/Hosting-1182448378761473867/original/1c7e6645-969a-4dc8-b1e2-2a8ff5cead83.jpeg",
            "https://a0.muscache.com/im/pictures/hosting/Hosting-1182448378761473867/original/f013b5e9-ce8f-4c98-bb57-d9f3be9ae7d7.jpeg",
            "https://a0.muscache.com/im/pictures/hosting/Hosting-1182448378761473867/original/e3b80740-9342-4e6f-a494-a625a3f906ed.jpeg"
        ],
        "url": "https://www.airbnb.ch/rooms/1182448378761473867",
        "amenities": [Amenity.WIFI, Amenity.KITCHEN],
        "roomType": RoomType.ENTIRE_HOME,
        "bedrooms": 1,
        "beds": 2,
        "bathrooms": 1,
    },
    {
        "id": "1394963917957884949",
        "title": "2-Zimmer-Wohnung für 4 Personen - Wiedikon",
        "price": "499 CHF",
        "priceInt": 499,
        "rating": "New",
        "images": [
            "https://a0.muscache.com/im/pictures/miso/Hosting-1394963917957884949/original/224cd05a-842d-415a-bd84-d45fc73c74c0.jpeg",
            "https://a0.muscache.com/im/pictures/miso/Hosting-1394963917957884949/original/ba0edcff-41b9-49eb-9d92-b2cbd988014c.jpeg",
            "https://a0.muscache.com/im/pictures/miso/Hosting-1394963917957884949/original/46343897-cfd6-4f70-bf45-d8f1b6e24670.jpeg",
            "https://a0.muscache.com/im/pictures/miso/Hosting-1394963917957884949/original/1f31a2af-9d0d-4044-a8d3-34abd135405b.jpeg",
            "https://a0.muscache.com/im/pictures/miso/Hosting-1394963917957884949/original/28ffd0c4-303f-4202-98d9-f950d55f29c9.jpeg",
            "https://a0.muscache.com/im/pictures/miso/Hosting-1394963917957884949/original/de21f701-f95a-4bd0-8f2c-f4eb2d246557.jpeg"
        ],
        "url": "https://www.airbnb.ch/rooms/1394963917957884949",
        "amenities": [Amenity.WIFI, Amenity.KITCHEN],
        "roomType": RoomType.ENTIRE_HOME,
        "bedrooms": 2,
        "beds": 2,
        "bathrooms": 1,
    },
    {
        "id": "1295546459742938911",
        "title": "Komfortabler Aufenthalt mit Zugang über Schlüsselbox",
        "price": "415 CHF",
        "priceInt": 415,
        "rating": "4.5 (14)",
        "images": [
            "https://a0.muscache.com/im/pictures/prohost-api/Hosting-1295546459742938911/original/aa50e08d-5eed-4038-8c40-a4fe9e1ef7e1.jpeg",
            "https://a0.muscache.com/im/pictures/prohost-api/Hosting-1295546459742938911/original/b782ef70-ffcd-4199-ad0e-c0365bd8e6c3.jpeg",
            "https://a0.muscache.com/im/pictures/prohost-api/Hosting-1295546459742938911/original/1178e062-6f5e-4217-9643-8f8e661d6726.jpeg",
            "https://a0.muscache.com/im/pictures/prohost-api/Hosting-1295546459742938911/original/93dc1273-544c-4ca9-a79d-beaab4ed9eb1.jpeg",
            "https://a0.muscache.com/im/pictures/prohost-api/Hosting-1295546459742938911/original/29f379f1-8fa1-4263-97cb-0aa1b305b82e.jpeg",
            "https://a0.muscache.com/im/pictures/prohost-api/Hosting-1295546459742938911/original/fe88ed06-4345-4d06-98f2-486d0bb3e4fc.jpeg"
        ],
        "url": "https://www.airbnb.ch/rooms/1295546459742938911",
        "amenities": [Amenity.WIFI],
        "roomType": RoomType.ENTIRE_HOME,
        "bedrooms": 1,
        "beds": 1,
        "bathrooms": 1,
    },
    {
        "id": "842033375277078900",
        "title": "Frische 2-BR-Wohnung am Zürich & See",
        "price": "487 CHF",
        "priceInt": 487,
        "rating": "4.93 (113)",
        "images": [
            "https://a0.muscache.com/im/pictures/hosting/Hosting-U3RheVN1cHBseUxpc3Rpbmc6ODQyMDMzMzc1Mjc3MDc4OTAw/original/2fc44587-630c-4aa9-8817-b3a801f2576e.jpeg",
            "https://a0.muscache.com/im/pictures/hosting/Hosting-U3RheVN1cHBseUxpc3Rpbmc6ODQyMDMzMzc1Mjc3MDc4OTAw/original/4780633d-9e2c-4038-9d1f-58839aef6b5c.jpeg",
            "https://a0.muscache.com/im/pictures/miso/Hosting-842033375277078900/original/005aef76-7d85-4423-86b2-e4db8e634b6a.jpeg",
            "https://a0.muscache.com/im/pictures/hosting/Hosting-U3RheVN1cHBseUxpc3Rpbmc6ODQyMDMzMzc1Mjc3MDc4OTAw/original/774291ae-3eaf-4d3b-9701-e36139f449ca.jpeg",
            "https://a0.muscache.com/im/pictures/hosting/Hosting-U3RheVN1cHBseUxpc3Rpbmc6ODQyMDMzMzc1Mjc3MDc4OTAw/original/7f74ee6a-9699-4684-9e91-e59251809abd.jpeg",
            "https://a0.muscache.com/im/pictures/hosting/Hosting-U3RheVN1cHBseUxpc3Rpbmc6ODQyMDMzMzc1Mjc3MDc4OTAw/original/3b17194d-7a2f-4b74-ae99-7cd3371f4bc2.jpeg"
        ],
        "url": "https://www.airbnb.ch/rooms/842033375277078900",
        "amenities": [Amenity.WIFI, Amenity.KITCHEN],
        "roomType": RoomType.ENTIRE_HOME,
        "bedrooms": 2,
        "beds": 2,
        "bathrooms": 1,
    },
    {
        "id": "1431940776803345911",
        "title": "Seeblick - 4,5 Zimmer, in der Nähe der Stadt Zürich, Parkplatz",
        "price": "431 CHF",
        "priceInt": 431,
        "rating": "4.82 (11)",
        "images": [
            "https://a0.muscache.com/im/pictures/miso/Hosting-1431940776803345911/original/f6e4f1b3-5e8d-4a94-a654-8132aab52cf2.jpeg",
            "https://a0.muscache.com/im/pictures/miso/Hosting-1431940776803345911/original/778fec3c-125d-4a7d-9440-25fa2a6b2e32.jpeg",
            "https://a0.muscache.com/im/pictures/miso/Hosting-1431940776803345911/original/35303c7f-ffc1-4092-9c55-eb26261a9ca9.jpeg",
            "https://a0.muscache.com/im/pictures/miso/Hosting-1431940776803345911/original/9398537e-aaea-4121-81df-8fc7b5953fc7.jpeg",
            "https://a0.muscache.com/im/pictures/miso/Hosting-1431940776803345911/original/2988fdfb-8206-4c22-9fd7-2c2fff929cb0.jpeg",
            "https://a0.muscache.com/im/pictures/miso/Hosting-1431940776803345911/original/758bc406-a208-4c6c-abd7-7fa1059041a5.jpeg"
        ],
        "url": "https://www.airbnb.ch/rooms/1431940776803345911",
        "amenities": [Amenity.WIFI, Amenity.KITCHEN, Amenity.POOL],
        "roomType": RoomType.ENTIRE_HOME,
        "bedrooms": 3,
        "beds": 4,
        "bathrooms": 2,
    },
    {
        "id": "1176878538805266347",
        "title": "Großes modernes 2BR Apartment, gut mit dem Zentrum verbunden",
        "price": "505 CHF",
        "priceInt": 505,
        "rating": "4.85 (20)",
        "images": [
            "https://a0.muscache.com/im/pictures/hosting/Hosting-U3RheVN1cHBseUxpc3Rpbmc6MTE3Njg3ODUzODgwNTI2NjM0Nw==/original/d862f8b9-a5d4-4263-baa8-87cbedf5f723.jpeg",
            "https://a0.muscache.com/im/pictures/hosting/Hosting-U3RheVN1cHBseUxpc3Rpbmc6MTE3Njg3ODUzODgwNTI2NjM0Nw==/original/7948e854-5149-4c08-8571-1c1104df6089.jpeg",
            "https://a0.muscache.com/im/pictures/hosting/Hosting-U3RheVN1cHBseUxpc3Rpbmc6MTE3Njg3ODUzODgwNTI2NjM0Nw==/original/97180429-62b4-4c0a-95cd-0f37a27f53f7.jpeg",
            "https://a0.muscache.com/im/pictures/hosting/Hosting-U3RheVN1cHBseUxpc3Rpbmc6MTE3Njg3ODUzODgwNTI2NjM0Nw==/original/ec152c1d-aa87-4e4b-8d44-fdac6f9e34fd.jpeg",
            "https://a0.muscache.com/im/pictures/hosting/Hosting-U3RheVN1cHBseUxpc3Rpbmc6MTE3Njg3ODUzODgwNTI2NjM0Nw==/original/64f7ab75-61ec-466c-9c24-7ddc15b94ac3.jpeg",
            "https://a0.muscache.com/im/pictures/hosting/Hosting-U3RheVN1cHBseUxpc3Rpbmc6MTE3Njg3ODUzODgwNTI2NjM0Nw==/original/7b609334-5cdd-43a2-a8d3-65491d2184d2.jpeg"
        ],
        "url": "https://www.airbnb.ch/rooms/1176878538805266347",
        "amenities": [Amenity.WIFI, Amenity.KITCHEN],
        "roomType": RoomType.ENTIRE_HOME,
        "bedrooms": 2,
        "beds": 2,
        "bathrooms": 1,
    }
];

export const useAppStore = create<AppState>((set, get) => ({
  currentUser: null,
  currentGroup: null,
  listings: MOCK_LISTINGS,
  votes: [],
  filters: {
    amenities: [],
  },

  setCurrentUser: (user: User) => set({ currentUser: user }),
  
  createGroup: (group: Group) => set({ currentGroup: group, listings: MOCK_LISTINGS }), 
  
  joinGroup: (groupCode: string, user: User) => {
    set((state) => {
        const group = state.currentGroup || {
            id: 'g1',
            name: 'Summer 2025',
            location: 'Mallorca, ES',
            startDate: '2025-07-15',
            endDate: '2025-07-22',
            members: [],
            code: groupCode
        };
        
        return {
            currentGroup: {
                ...group,
                members: [...group.members, user]
            },
            currentUser: user
        };
    });
  },

  setFilters: (filters: Filters) => set({ filters }),

  addVote: (vote: Vote) => set((state) => ({ votes: [...state.votes, vote] })),

  getGroupListings: () => get().listings,

  getLeaderboard: () => {
    const { listings, votes } = get();
    return listings.map((listing: Listing) => {
      const listingVotes = votes.filter((v: Vote) => v.listingId === listing.id);
      const loves = listingVotes.filter((v: Vote) => v.type === 'love').length;
      const oks = listingVotes.filter((v: Vote) => v.type === 'ok').length;
      const vetos = listingVotes.filter((v: Vote) => v.type === 'veto').length;
      
      const score = (loves * 2) + (oks * 1) + (vetos * -10);
      
      return { listing, score, loves, vetos };
    }).sort((a: any, b: any) => b.score - a.score);
  }
}));
