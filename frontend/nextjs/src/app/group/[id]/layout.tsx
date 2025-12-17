"use client";

import Link from 'next/link';
import { usePathname, useParams } from 'next/navigation';
import { ThumbsUp, Trophy, Users, SlidersHorizontal } from 'lucide-react';

export default function GroupLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const pathname = usePathname();
  const { id } = useParams();
  
  // Determine active tab
  const isActive = (path: string) => {
    if (path === '' && pathname === `/group/${id}`) return true;
    return pathname === `/group/${id}/${path}`;
  };

  return (
    <div className="h-full bg-slate-50 flex flex-col">
      {/* Scroll container for all group sub-pages; reserves space for the fixed bottom nav (incl. safe-area) */}
      <div className="flex-1 overflow-y-auto overscroll-contain relative pb-[calc(80px+env(safe-area-inset-bottom))]">
        {children}
      </div>

      {/* Bottom Nav */}
      <nav className="fixed bottom-0 left-0 right-0 bg-white border-t border-slate-100 pt-4 px-6 flex justify-around items-center z-50 h-[calc(80px+env(safe-area-inset-bottom))] pb-[calc(1.5rem+env(safe-area-inset-bottom))]">
        <Link 
          href={`/group/${id}`}
          className={`flex flex-col items-center gap-1 transition-colors ${isActive('') ? 'text-rose-500' : 'text-slate-400 hover:text-slate-600'}`}
        >
          <ThumbsUp className={`w-6 h-6 ${isActive('') ? 'fill-current' : ''}`} />
          <span className="text-xs font-medium">Vote</span>
        </Link>
        
        <Link 
          href={`/group/${id}/leaderboard`} 
          className={`flex flex-col items-center gap-1 transition-colors ${isActive('leaderboard') ? 'text-rose-500' : 'text-slate-400 hover:text-slate-600'}`}
        >
          <Trophy className={`w-6 h-6 ${isActive('leaderboard') ? 'fill-current' : ''}`} />
          <span className="text-xs font-medium">Rank</span>
        </Link>

        <Link 
            href={`/group/${id}/members`}
            className={`flex flex-col items-center gap-1 transition-colors ${isActive('members') ? 'text-rose-500' : 'text-slate-400 hover:text-slate-600'}`}
        >
            <Users className={`w-6 h-6 ${isActive('members') ? 'fill-current' : ''}`} />
            <span className="text-xs font-medium">Group</span>
        </Link>

        <Link 
          href={`/group/${id}/filters`}
          className={`flex flex-col items-center gap-1 transition-colors ${isActive('filters') ? 'text-rose-500' : 'text-slate-400 hover:text-slate-600'}`}
        >
          <SlidersHorizontal className="w-6 h-6" />
          <span className="text-xs font-medium">Filters</span>
        </Link>
      </nav>
    </div>
  );
}
