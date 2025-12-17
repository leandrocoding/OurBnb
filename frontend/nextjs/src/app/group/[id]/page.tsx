"use client";

import { useEffect, useState, useCallback, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAppStore } from '../../../store/useAppStore';
import { VotingCard, preloadImages } from '../../../components/VotingCard';
import { submitVote, getGroupInfo, GroupInfo, GroupVote, RecommendationListing } from '../../../lib/api';
import { VoteValue, Listing, OtherVote, VOTE_VETO, VOTE_LOVE } from '../../../types';
import { Loader2, Search, Home } from 'lucide-react';
import { motion, useMotionValue, useTransform, animate } from 'framer-motion';
import Link from 'next/link';

// Convert RecommendationListing to component Listing format
function toComponentListing(rec: RecommendationListing): Listing {
  return {
    id: rec.airbnb_id,
    title: rec.title || 'Untitled Property',
    price: rec.price || 0,
    rating: rec.rating,
    reviewCount: rec.review_count,
    images: rec.images.length > 0 ? rec.images : ['https://placehold.co/400x300?text=No+Image'],
    amenities: rec.amenities,
    propertyType: rec.property_type,
    bedrooms: rec.bedrooms,
    beds: rec.beds,
    bathrooms: rec.bathrooms,
    bookingLink: rec.booking_link,
    location: rec.location,
  };
}

// Calculate number of nights between two dates
function calculateNights(dateStart: string, dateEnd: string): number {
  const start = new Date(dateStart);
  const end = new Date(dateEnd);
  const diffTime = Math.abs(end.getTime() - start.getTime());
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  return Math.max(1, diffDays);
}

// Convert API other_votes to OtherVote format
function toOtherVotes(votes: GroupVote[]): OtherVote[] {
  return votes.map(v => ({
    userId: v.user_id,
    userName: v.user_name,
    vote: v.vote as VoteValue,
  }));
}

// Loading messages to cycle through
const LOADING_MESSAGES = [
  "Searching for the perfect stays...",
  "Checking availability in your destinations...",
  "Finding places that match your filters...",
  "Almost there, gathering options...",
  "Discovering hidden gems...",
];

export default function GroupPage() {
  const { id } = useParams();
  const router = useRouter();
  const { 
    currentUser, 
    isHydrated,
    recommendations,
    currentIndex,
    totalRemaining,
    hasMore,
    isLoadingRecommendations,
    recommendationsError,
    recommendationsVersion,
    fetchRecommendations,
    advanceToNextCard,
    priceDisplayMode,
    setPriceDisplayMode,
  } = useAppStore();
  
  const [groupInfo, setGroupInfo] = useState<GroupInfo | null>(null);
  const [isInitialLoading, setIsInitialLoading] = useState(true);
  const [isWaitingForListings, setIsWaitingForListings] = useState(false);
  const [isVoting, setIsVoting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loadingMessageIndex, setLoadingMessageIndex] = useState(0);
  // Vote counter to force VotingCard re-mount after each vote (resets isAnimating state)
  const [voteCount, setVoteCount] = useState(0);
  
  const pollingRef = useRef<NodeJS.Timeout | null>(null);
  const mountedRef = useRef(true);
  const initialFetchDoneRef = useRef(false);
  
  // Motion value for background card animation (0 = background position, 1 = foreground position)
  const bgProgress = useMotionValue(0);
  const bgScale = useTransform(bgProgress, [0, 1], [0.95, 1]);
  const bgY = useTransform(bgProgress, [0, 1], [16, 0]);

  const groupId = typeof id === 'string' ? parseInt(id, 10) : null;

  // Check if user needs to be redirected (only after hydration)
  useEffect(() => {
    if (!isHydrated) return; // Wait for localStorage to be loaded
    
    if (!currentUser) {
      // If no user, redirect to join page
      if (groupId) {
        router.push(`/join?group=${groupId}`);
      } else {
        router.push('/');
      }
    } else if (currentUser.groupId !== groupId) {
      // User is in a different group, redirect to their group
      router.push(`/group/${currentUser.groupId}`);
    }
  }, [currentUser, groupId, router, isHydrated]);

  // Cycle loading messages
  useEffect(() => {
    if (!isWaitingForListings) return;
    
    const interval = setInterval(() => {
      setLoadingMessageIndex(prev => (prev + 1) % LOADING_MESSAGES.length);
    }, 3000);
    
    return () => clearInterval(interval);
  }, [isWaitingForListings]);

  // Fetch group info and initial recommendations
  useEffect(() => {
    if (!currentUser || !groupId || !isHydrated || initialFetchDoneRef.current) return;
    
    const fetchInitialData = async () => {
      setIsInitialLoading(true);
      setError(null);
      
      try {
        // Fetch group info
        const groupResponse = await getGroupInfo(groupId);
        if (mountedRef.current) {
          setGroupInfo(groupResponse);
        }
        
        // Fetch initial recommendations (force fetch)
        await fetchRecommendations(true);
        
        initialFetchDoneRef.current = true;
      } catch (err) {
        if (mountedRef.current) {
          setError(err instanceof Error ? err.message : 'Failed to load data');
        }
      } finally {
        if (mountedRef.current) {
          setIsInitialLoading(false);
        }
      }
    };
    
    fetchInitialData();
  }, [currentUser, groupId, isHydrated, fetchRecommendations]);

  // Refetch recommendations when version changes (filter/group settings changed)
  useEffect(() => {
    if (!initialFetchDoneRef.current || !currentUser) return;
    
    // Force refetch when version changes
    fetchRecommendations(true);
  }, [recommendationsVersion, fetchRecommendations, currentUser]);

  // Set up mounted ref
  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  // Determine if we're waiting for listings (no recommendations and no more to fetch)
  useEffect(() => {
    if (isInitialLoading || isLoadingRecommendations) return;
    
    const currentListing = recommendations[currentIndex];
    if (!currentListing && totalRemaining === 0 && !hasMore) {
      // Check if there are any listings at all by looking at the state
      // If totalRemaining is 0 and we have no recommendations, we might be waiting
      setIsWaitingForListings(recommendations.length === 0 && currentIndex === 0);
    } else {
      setIsWaitingForListings(false);
    }
  }, [recommendations, currentIndex, totalRemaining, hasMore, isInitialLoading, isLoadingRecommendations]);

  // Preload images for next listing
  useEffect(() => {
    const nextListing = recommendations[currentIndex + 1];
    if (nextListing && nextListing.images.length > 0) {
      preloadImages(nextListing.images);
    }
  }, [recommendations, currentIndex]);

  // Reset background card progress when current listing changes
  const currentListing = recommendations[currentIndex];
  useEffect(() => {
    bgProgress.set(0);
  }, [currentListing?.airbnb_id, bgProgress]);

  // Handle drag progress from active card - animate background card in sync
  const handleDragProgress = useCallback((progress: number) => {
    bgProgress.set(progress);
  }, [bgProgress]);

  // Handle vote start - animate background card to foreground immediately
  const handleVoteStart = useCallback(() => {
    animate(bgProgress, 1, { duration: 0.3, ease: "easeOut" });
  }, [bgProgress]);

  // Poll for listings when waiting
  useEffect(() => {
    if (!isWaitingForListings || !mountedRef.current) {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
      return;
    }

    // Poll every 5 seconds
    pollingRef.current = setInterval(() => {
      if (mountedRef.current) {
        fetchRecommendations(true);
      }
    }, 5000);

    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    };
  }, [isWaitingForListings, fetchRecommendations]);

  const handleVote = async (vote: VoteValue) => {
    if (!currentUser || !currentListing || isVoting) return;

    setIsVoting(true);
    
    try {
      // Submit vote to backend
      await submitVote(currentUser.id, currentListing.airbnb_id, vote);

      // Advance to next card in local buffer (this will trigger refetch if needed)
      advanceToNextCard();
      
      // Increment vote count to force VotingCard re-mount (resets isAnimating)
      setVoteCount(prev => prev + 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit vote');
    } finally {
      setIsVoting(false);
    }
  };

  const handleRetry = useCallback(() => {
    setError(null);
    initialFetchDoneRef.current = false;
    fetchRecommendations(true);
  }, [fetchRecommendations]);

  // Loading state (including hydration)
  if (!isHydrated || isInitialLoading) {
    return (
      <div className="flex h-full items-center justify-center bg-slate-50">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-rose-500 mx-auto mb-4" />
          <p className="text-slate-600">Loading...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error || recommendationsError) {
    return (
      <div className="flex h-full flex-col items-center justify-center bg-slate-50 p-6 text-center">
        <div className="text-5xl mb-4">😕</div>
        <h2 className="text-xl font-bold text-slate-900 mb-2">Something went wrong</h2>
        <p className="text-slate-600 mb-6">{error || recommendationsError}</p>
        <button
          onClick={handleRetry}
          className="bg-rose-500 text-white px-6 py-3 rounded-full font-bold shadow-lg"
        >
          Try Again
        </button>
      </div>
    );
  }

  // No user state (shouldn't happen due to redirect, but just in case)
  if (!currentUser) {
    return (
      <div className="flex h-full items-center justify-center bg-slate-50">
        <Loader2 className="w-8 h-8 animate-spin text-rose-500" />
      </div>
    );
  }

  // Waiting for listings state
  if (isWaitingForListings) {
    return (
      <div className="min-h-full flex flex-col items-center justify-center bg-gradient-to-b from-rose-50 to-white p-6 text-center">
        <div className="relative mb-8">
          {/* Animated search icon */}
          <div className="w-24 h-24 rounded-full bg-rose-100 flex items-center justify-center animate-pulse">
            <Search className="w-12 h-12 text-rose-500" />
          </div>
          {/* Orbiting homes */}
          <div className="absolute inset-0 animate-spin" style={{ animationDuration: '8s' }}>
            <Home className="w-6 h-6 text-rose-400 absolute -top-2 left-1/2 -translate-x-1/2" />
          </div>
          <div className="absolute inset-0 animate-spin" style={{ animationDuration: '8s', animationDelay: '-2.67s' }}>
            <Home className="w-6 h-6 text-rose-300 absolute -top-2 left-1/2 -translate-x-1/2" />
          </div>
          <div className="absolute inset-0 animate-spin" style={{ animationDuration: '8s', animationDelay: '-5.33s' }}>
            <Home className="w-6 h-6 text-rose-200 absolute -top-2 left-1/2 -translate-x-1/2" />
          </div>
        </div>
        
        <h2 className="text-2xl font-bold text-slate-900 mb-3">Finding Airbnbs for you</h2>
        <p className="text-slate-600 mb-2 max-w-xs">
          {LOADING_MESSAGES[loadingMessageIndex]}
        </p>
        <p className="text-slate-400 text-sm mb-8">
          This usually takes 30-60 seconds
        </p>
        
        {/* Progress dots */}
        <div className="flex gap-2 mb-8">
          {[0, 1, 2].map((i) => (
            <div 
              key={i}
              className="w-2 h-2 rounded-full bg-rose-300 animate-bounce"
              style={{ animationDelay: `${i * 0.15}s` }}
            />
          ))}
        </div>
        
        <p className="text-xs text-slate-400">
          You can also check the{' '}
          <Link href={`/group/${id}/leaderboard`} className="text-rose-500 underline">
            leaderboard
          </Link>
          {' '}while you wait
        </p>
      </div>
    );
  }

  // Get current and next listings from recommendations
  const currentRec = recommendations[currentIndex];
  const nextRec = recommendations[currentIndex + 1];
  
  const currentListingDisplay = currentRec ? toComponentListing(currentRec) : null;
  const nextListingDisplay = nextRec ? toComponentListing(nextRec) : null;

  // No listings / all caught up
  if (!currentListingDisplay) {
    return (
      <div className="min-h-full flex flex-col items-center justify-center bg-slate-50 p-6 text-center">
        <div className="text-6xl mb-4">🎉</div>
        <h2 className="text-2xl font-bold text-slate-900 mb-2">All caught up!</h2>
        <p className="text-slate-600 mb-6">You&apos;ve voted on all available listings.</p>
        <Link 
          href={`/group/${id}/leaderboard`}
          className="bg-rose-500 text-white px-6 py-3 rounded-full font-bold shadow-lg"
        >
          View Leaderboard
        </Link>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-slate-50">
      {/* Main Content */}
      <main className="flex-1 flex items-center justify-center p-4 overflow-hidden relative" style={{ paddingBottom: '80px' }}>
        <div className="relative w-full max-w-md h-[65vh]">
          {/* Background Card - animated via motion values */}
          {nextListingDisplay && (
            <motion.div
              key={`bg-${nextListingDisplay.id}`}
              className="absolute inset-0"
              style={{ scale: bgScale, y: bgY }}
            >
              <VotingCard 
                listing={nextListingDisplay}
                onVote={() => {}} // No-op for background card
                location={nextListingDisplay.location}
                isBackground={true}
                numberOfNights={groupInfo ? calculateNights(groupInfo.date_start, groupInfo.date_end) : 1}
                numberOfAdults={groupInfo?.adults || 1}
                priceMode={priceDisplayMode}
              />
            </motion.div>
          )}
          
          {/* Active Card - include voteCount in key to force re-mount after each vote */}
          <VotingCard 
            key={`${currentListingDisplay.id}-${voteCount}`}
            listing={currentListingDisplay}
            onVote={handleVote}
            onDragProgress={handleDragProgress}
            onVoteStart={handleVoteStart}
            otherVotes={currentRec?.other_votes ? toOtherVotes(currentRec.other_votes) : []}
            location={currentListingDisplay.location}
            numberOfNights={groupInfo ? calculateNights(groupInfo.date_start, groupInfo.date_end) : 1}
            numberOfAdults={groupInfo?.adults || 1}
            priceMode={priceDisplayMode}
            onPriceModeChange={setPriceDisplayMode}
          />
          
          {/* Loading indicator when fetching more */}
          {isLoadingRecommendations && (
            <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2">
              <div className="bg-white/90 backdrop-blur px-3 py-1 rounded-full shadow text-xs text-slate-500 flex items-center gap-2">
                <Loader2 className="w-3 h-3 animate-spin" />
                Loading more...
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
