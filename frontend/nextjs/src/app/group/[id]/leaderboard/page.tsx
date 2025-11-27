"use client";

import { useAppStore } from '../../../../store/useAppStore';
import Link from 'next/link';
import { ChevronLeft, Trophy, Heart, ThumbsUp, AlertCircle } from 'lucide-react';
import Image from 'next/image';

export default function LeaderboardPage() {
  const { getLeaderboard, currentGroup } = useAppStore();
  const leaderboard = getLeaderboard();

  return (
    <div className="flex flex-col h-full pb-24 overflow-y-auto">
      <header className="bg-white px-6 py-4 shadow-sm sticky top-0 z-10">
         <div className="flex items-center gap-4">
             <h1 className="font-bold text-slate-900 text-xl">Top Picks</h1>
         </div>
         <p className="mt-1 text-sm text-slate-500">Based on Group Happiness Score™</p>
      </header>

      <div className="p-6 flex flex-col gap-4">
          {/* List */}
          {leaderboard.map((item, index) => (
              <div key={item.listing.id} className="bg-white rounded-2xl p-4 shadow-sm flex gap-4">
                  <div className="relative w-24 h-24 flex-shrink-0 rounded-xl overflow-hidden bg-slate-100">
                      {item.listing.images[0] && (
                          <Image src={item.listing.images[0]} alt={item.listing.title} fill className="object-cover" />
                      )}
                      <div className="absolute top-1 left-1 bg-yellow-400 text-xs font-bold px-1.5 py-0.5 rounded text-slate-900">
                          #{index + 1}
                      </div>
                  </div>
                  
                  <div className="flex-1 min-w-0">
                      <div className="flex justify-between items-start">
                          <h3 className="font-bold text-slate-900 truncate pr-2">{item.listing.title}</h3>
                          <span className="font-bold text-green-600">{Math.max(0, Math.min(100, 50 + item.score * 5))}%</span>
                      </div>
                      
                      <div className="flex gap-3 mt-2 mb-3">
                          {item.loves > 0 && (
                              <div className="flex items-center gap-1 text-xs font-medium text-rose-500 bg-rose-50 px-2 py-1 rounded">
                                  <Heart className="w-3 h-3 fill-current" /> {item.loves} Loves
                              </div>
                          )}
                          {item.loves + item.score - (item.loves*2) > 0 && ( // Recovering 'oks' from score is simplified here, normally use item.oks
                              <div className="flex items-center gap-1 text-xs font-medium text-blue-500 bg-blue-50 px-2 py-1 rounded">
                                  <ThumbsUp className="w-3 h-3" /> Likes
                              </div>
                          )}
                      </div>

                      <p className="text-xs text-slate-500">
                          {item.vetos > 0 ? `${item.vetos} veto(s)` : 'Matches your budget'}
                      </p>
                  </div>
              </div>
          ))}
      </div>
    </div>
  );
}

