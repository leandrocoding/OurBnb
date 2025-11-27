"use client";

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAppStore } from '../../../store/useAppStore';
import { VotingCard } from '../../../components/VotingCard';
import { VoteType } from '../../../types';
import { Settings, Trophy, MapPin } from 'lucide-react';
import Link from 'next/link';
import Image from 'next/image';

export default function GroupPage() {
  const { id } = useParams();
  const router = useRouter();
  const { currentGroup, currentUser, listings, addVote, votes } = useAppStore();

  // Local state for current listing index
  const [currentIndex, setCurrentIndex] = useState(0);

  // If no group/user, redirect (simple auth guard)
  useEffect(() => {
    if (!currentGroup || !currentUser) {
       // For development/demo, we might want to allow direct access by creating a dummy user
       // But properly we should redirect to join
       // router.push('/join');
    }
  }, [currentGroup, currentUser, router]);

  const handleVote = (type: VoteType) => {
    if (!currentUser || !currentGroup) return;

    const currentListing = listings[currentIndex];
    if (!currentListing) return;

    addVote({
      userId: currentUser.id,
      listingId: currentListing.id,
      type,
      reason: type === 'veto' ? 'Not my style' : undefined
    });

    // Move to next
    setCurrentIndex(prev => prev + 1);
  };

  if (!currentGroup) {
      return <div className="p-6 text-center">Group not found. Please join or create a group. <Link href="/" className="text-blue-500">Go Home</Link></div>;
  }

  if (currentIndex >= listings.length) {
      return (
          <div className="min-h-screen flex flex-col items-center justify-center bg-slate-50 p-6 text-center">
              <h2 className="text-2xl font-bold text-slate-900 mb-2">All caught up!</h2>
              <p className="text-slate-600 mb-6">You've voted on all available listings.</p>
              <Link 
                href={`/group/${id}/leaderboard`}
                className="bg-rose-500 text-white px-6 py-3 rounded-full font-bold shadow-lg"
              >
                  View Leaderboard
              </Link>
          </div>
      );
  }

  const currentListing = listings[currentIndex];
  const nextListing = listings[currentIndex + 1];

  // Get other votes for this listing to display "Liked by..."
  const listingVotes = votes.filter(v => v.listingId === currentListing.id && v.userId !== currentUser?.id)
    .map(v => ({
        name: currentGroup.members.find(m => m.id === v.userId)?.name || 'Someone',
        type: v.type
    }));

  return (
    <div className="flex flex-col h-full bg-slate-50">
      {/* Main Content */}
      <main className="flex-1 flex items-center justify-center p-4 overflow-hidden relative" style={{ paddingBottom: '80px' }}>
         <div className="relative w-full max-w-md h-[65vh]">
             {/* Background Card */}
             {nextListing && (
                 <VotingCard 
                    key={nextListing.id}
                    listing={nextListing}
                    onVote={() => {}} // No-op for background card
                    location={currentGroup.location.split(',')[0]}
                    isBackground={true}
                 />
             )}
             
             {/* Active Card */}
             <VotingCard 
                key={currentListing.id} // Key change forces remount/reset of animation
                listing={currentListing}
                onVote={handleVote}
                otherVotes={listingVotes}
                location={currentGroup.location.split(',')[0]}
             />
         </div>
      </main>
    </div>
  );
}

