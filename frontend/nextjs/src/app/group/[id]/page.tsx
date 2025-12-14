"use client";

import { useEffect, useState, useCallback, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAppStore } from '../../../store/useAppStore';
import { VotingCard, preloadImages } from '../../../components/VotingCard';
import { submitVote, getGroupInfo, getNextToVote, GroupInfo, NextToVoteResponse, GroupVote } from '../../../lib/api';
import { VoteValue, Listing, OtherVote } from '../../../types';
import { Loader2, Search, Home } from 'lucide-react';
import { motion, useMotionValue, useTransform, animate } from 'framer-motion';
import Link from 'next/link';

// Convert API NextToVoteResponse to component Listing format
function toComponentListing(response: NextToVoteResponse): Listing | null {
  if (!response.has_listing || !response.airbnb_id) return null;
  
  return {
    id: response.airbnb_id,
    title: response.title || 'Untitled Property',
    price: response.price || 0,
    rating: response.rating,
    reviewCount: response.review_count,
    images: response.images.length > 0 ? response.images : ['https://placehold.co/400x300?text=No+Image'],
    amenities: response.amenities,
    propertyType: response.property_type,
    bedrooms: response.bedrooms,
    beds: response.beds,
    bathrooms: response.bathrooms,
  };
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
  const { currentUser, isHydrated } = useAppStore();
  
  // Two-card buffer: current listing being displayed and prefetched next listing
  const [currentResponse, setCurrentResponse] = useState<NextToVoteResponse | null>(null);
  const [prefetchedResponse, setPrefetchedResponse] = useState<NextToVoteResponse | null>(null);
  
  const [groupInfo, setGroupInfo] = useState<GroupInfo | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isWaitingForListings, setIsWaitingForListings] = useState(false);
  const [isVoting, setIsVoting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loadingMessageIndex, setLoadingMessageIndex] = useState(0);
  // Vote counter to force VotingCard re-mount after each vote (resets isAnimating state)
  const [voteCount, setVoteCount] = useState(0);
  
  const pollingRef = useRef<NodeJS.Timeout | null>(null);
  const mountedRef = useRef(true);
  
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

  // Fetch initial data: current listing, prefetched listing, and group info
  const fetchData = useCallback(async (isPolling = false) => {
    if (!currentUser || !groupId || !mountedRef.current) return;

    if (!isPolling) {
      setIsLoading(true);
    }
    setError(null);

    try {
      // Fetch current listing and group info in parallel
      const [firstResponse, groupResponse] = await Promise.all([
        getNextToVote(currentUser.id),
        getGroupInfo(groupId),
      ]);
      
      if (!mountedRef.current) return;
      
      setGroupInfo(groupResponse);
      
      // Check if we got a listing
      if (!firstResponse.has_listing) {
        // No listings available - determine why
        if (firstResponse.total_listings === 0) {
          // No bnbs exist yet for this group (scraping in progress)
          setIsWaitingForListings(true);
        } else if (firstResponse.total_remaining === 0) {
          // User has voted on all existing listings
          setCurrentResponse(firstResponse);
          setPrefetchedResponse(null);
          setIsWaitingForListings(false);
        } else {
          // Listings exist but buffer couldn't be filled (edge case, treat as waiting)
          setIsWaitingForListings(true);
        }
        setIsLoading(false);
        return;
      }
      
      setCurrentResponse(firstResponse);
      setIsWaitingForListings(false);
      
      // Prefetch the next listing (exclude current one)
      if (firstResponse.airbnb_id) {
        const secondResponse = await getNextToVote(currentUser.id, [firstResponse.airbnb_id]);
        if (mountedRef.current) {
          setPrefetchedResponse(secondResponse.has_listing ? secondResponse : null);
        }
      }
    } catch (err) {
      if (mountedRef.current) {
        setError(err instanceof Error ? err.message : 'Failed to load listings');
      }
    } finally {
      if (mountedRef.current) {
        setIsLoading(false);
      }
    }
  }, [currentUser, groupId]);

  // Initial fetch
  useEffect(() => {
    mountedRef.current = true;
    fetchData();
    
    return () => {
      mountedRef.current = false;
    };
  }, [fetchData]);

  // Preload images for prefetched listing
  useEffect(() => {
    if (prefetchedResponse?.has_listing && prefetchedResponse.images.length > 0) {
      preloadImages(prefetchedResponse.images);
    }
  }, [prefetchedResponse]);

  // Reset background card progress when current listing changes
  useEffect(() => {
    bgProgress.set(0);
  }, [currentResponse?.airbnb_id, bgProgress]);

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
        fetchData(true);
      }
    }, 5000);

    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    };
  }, [isWaitingForListings, fetchData]);

  const handleVote = async (vote: VoteValue) => {
    if (!currentUser || !currentResponse?.has_listing || !currentResponse.airbnb_id || isVoting) return;

    setIsVoting(true);
    
    // Capture IDs before state changes
    const votedId = currentResponse.airbnb_id;
    const nextCurrent = prefetchedResponse;

    try {
      // Submit vote (we ignore next_listing from response - we manage our own queue)
      await submitVote(currentUser.id, votedId, vote);

      // Move prefetched to current
      if (nextCurrent?.has_listing && nextCurrent.airbnb_id) {
        setCurrentResponse(nextCurrent);
        
        // Fetch new prefetch in background (exclude voted ID + new current to avoid race conditions)
        getNextToVote(currentUser.id, [votedId, nextCurrent.airbnb_id])
          .then(response => {
            if (mountedRef.current) {
              setPrefetchedResponse(response.has_listing ? response : null);
            }
          })
          .catch(() => {
            if (mountedRef.current) setPrefetchedResponse(null);
          });
      } else {
        // No prefetched card - try to fetch a new current (exclude voted ID)
        try {
          const response = await getNextToVote(currentUser.id, [votedId]);
          if (mountedRef.current) {
            if (response.has_listing) {
              setCurrentResponse(response);
              // Fetch prefetch for the new current (exclude voted ID + new current)
              if (response.airbnb_id) {
                getNextToVote(currentUser.id, [votedId, response.airbnb_id])
                  .then(prefetchResponse => {
                    if (mountedRef.current) {
                      setPrefetchedResponse(prefetchResponse.has_listing ? prefetchResponse : null);
                    }
                  })
                  .catch(() => {});
              }
            } else {
              // No more listings
              setCurrentResponse(response);
              setPrefetchedResponse(null);
              if (response.total_listings === 0) {
                setIsWaitingForListings(true);
              }
            }
          }
        } catch {
          if (mountedRef.current) {
            setCurrentResponse({ has_listing: false, total_remaining: 0, total_listings: 0, images: [], amenities: [], other_votes: [] });
            setPrefetchedResponse(null);
          }
        }
      }
      
      // Increment vote count to force VotingCard re-mount (resets isAnimating)
      setVoteCount(prev => prev + 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit vote');
    } finally {
      setIsVoting(false);
    }
  };

  // Loading state (including hydration)
  if (!isHydrated || isLoading) {
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
  if (error) {
    return (
      <div className="flex h-full flex-col items-center justify-center bg-slate-50 p-6 text-center">
        <div className="text-5xl mb-4">😕</div>
        <h2 className="text-xl font-bold text-slate-900 mb-2">Something went wrong</h2>
        <p className="text-slate-600 mb-6">{error}</p>
        <button
          onClick={() => fetchData()}
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

  // Convert responses to component format
  const currentListing = currentResponse ? toComponentListing(currentResponse) : null;
  const nextListing = prefetchedResponse ? toComponentListing(prefetchedResponse) : null;

  // No listings / all caught up
  if (!currentListing) {
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

  const location = groupInfo?.destinations[0]?.name.split(',')[0] || '';

  return (
    <div className="flex flex-col h-full bg-slate-50">
      {/* Main Content */}
      <main className="flex-1 flex items-center justify-center p-4 overflow-hidden relative" style={{ paddingBottom: '80px' }}>
        <div className="relative w-full max-w-md h-[65vh]">
          {/* Background Card - animated via motion values */}
          {nextListing && (
            <motion.div
              key={`bg-${nextListing.id}`}
              className="absolute inset-0"
              style={{ scale: bgScale, y: bgY }}
            >
              <VotingCard 
                listing={nextListing}
                onVote={() => {}} // No-op for background card
                location={location}
                isBackground={true}
              />
            </motion.div>
          )}
          
          {/* Active Card - include voteCount in key to force re-mount after each vote */}
          <VotingCard 
            key={`${currentListing.id}-${voteCount}`}
            listing={currentListing}
            onVote={handleVote}
            onDragProgress={handleDragProgress}
            onVoteStart={handleVoteStart}
            otherVotes={currentResponse?.other_votes ? toOtherVotes(currentResponse.other_votes) : []}
            location={location}
          />
        </div>
      </main>
    </div>
  );
}
