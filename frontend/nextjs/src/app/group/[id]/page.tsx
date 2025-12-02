"use client";

import { useEffect, useState, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAppStore } from '../../../store/useAppStore';
import { VotingCard } from '../../../components/VotingCard';
import { getVotingQueue, submitVote, getGroupInfo, QueuedListing, GroupInfo } from '../../../lib/api';
import { VoteValue, Listing, OtherVote } from '../../../types';
import { Loader2 } from 'lucide-react';
import Link from 'next/link';

// Convert API QueuedListing to component Listing format
function toComponentListing(queued: QueuedListing): Listing {
  return {
    id: queued.airbnb_id,
    title: queued.title || 'Untitled Property',
    price: queued.price || 0,
    rating: queued.rating,
    reviewCount: queued.review_count,
    images: queued.images.length > 0 ? queued.images : ['https://placehold.co/400x300?text=No+Image'],
    amenities: queued.amenities,
    propertyType: queued.property_type,
    bedrooms: queued.bedrooms,
    beds: queued.beds,
    bathrooms: queued.bathrooms,
  };
}

// Convert API other_votes to OtherVote format
function toOtherVotes(votes: QueuedListing['other_votes']): OtherVote[] {
  return votes.map(v => ({
    userId: v.user_id,
    userName: v.user_name,
    vote: v.vote as VoteValue,
  }));
}

export default function GroupPage() {
  const { id } = useParams();
  const router = useRouter();
  const { currentUser } = useAppStore();
  
  const [queue, setQueue] = useState<QueuedListing[]>([]);
  const [groupInfo, setGroupInfo] = useState<GroupInfo | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isVoting, setIsVoting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const groupId = typeof id === 'string' ? parseInt(id, 10) : null;

  // Check if user needs to be redirected
  useEffect(() => {
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
  }, [currentUser, groupId, router]);

  // Fetch queue and group info
  const fetchData = useCallback(async () => {
    if (!currentUser || !groupId) return;

    setIsLoading(true);
    setError(null);

    try {
      const [queueResponse, groupResponse] = await Promise.all([
        getVotingQueue(currentUser.id, 10),
        getGroupInfo(groupId),
      ]);
      
      setQueue(queueResponse.queue);
      setGroupInfo(groupResponse);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load listings');
    } finally {
      setIsLoading(false);
    }
  }, [currentUser, groupId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleVote = async (vote: VoteValue) => {
    if (!currentUser || queue.length === 0 || isVoting) return;

    const currentListing = queue[0];
    setIsVoting(true);

    try {
      await submitVote(
        currentUser.id,
        currentListing.airbnb_id,
        vote,
        undefined // No reason for now
      );

      // Remove the voted listing from queue
      setQueue(prev => prev.slice(1));

      // If queue is getting low, fetch more
      if (queue.length <= 3) {
        const newQueue = await getVotingQueue(currentUser.id, 10);
        setQueue(newQueue.queue);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit vote');
    } finally {
      setIsVoting(false);
    }
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center bg-slate-50">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-rose-500 mx-auto mb-4" />
          <p className="text-slate-600">Loading listings...</p>
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
          onClick={fetchData}
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

  // No listings / all caught up
  if (queue.length === 0) {
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

  const currentListing = queue[0];
  const nextListing = queue[1];
  const location = groupInfo?.destinations[0]?.name.split(',')[0] || '';

  return (
    <div className="flex flex-col h-full bg-slate-50">
      {/* Main Content */}
      <main className="flex-1 flex items-center justify-center p-4 overflow-hidden relative" style={{ paddingBottom: '80px' }}>
        <div className="relative w-full max-w-md h-[65vh]">
          {/* Background Card */}
          {nextListing && (
            <VotingCard 
              key={`bg-${nextListing.airbnb_id}`}
              listing={toComponentListing(nextListing)}
              onVote={() => {}} // No-op for background card
              location={location}
              isBackground={true}
            />
          )}
          
          {/* Active Card */}
          <VotingCard 
            key={currentListing.airbnb_id}
            listing={toComponentListing(currentListing)}
            onVote={handleVote}
            otherVotes={toOtherVotes(currentListing.other_votes)}
            location={location}
          />
          
          {/* Voting indicator */}
          {isVoting && (
            <div className="absolute inset-0 flex items-center justify-center bg-white/50 rounded-3xl z-50">
              <Loader2 className="w-8 h-8 animate-spin text-rose-500" />
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
