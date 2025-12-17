"use client";

import { useEffect, useState, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAppStore } from '../../../../store/useAppStore';
import { getGroupInfo, deleteUser, GroupInfo } from '../../../../lib/api';
import { Calendar, MapPin, Loader2, Copy, Check, Users, LogOut } from 'lucide-react';

export default function MembersPage() {
  const { id } = useParams();
  const router = useRouter();
  const { currentUser, isHydrated, clearUser } = useAppStore();
  
  const [groupInfo, setGroupInfo] = useState<GroupInfo | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [showLeaveConfirm, setShowLeaveConfirm] = useState(false);
  const [isLeaving, setIsLeaving] = useState(false);

  const groupId = typeof id === 'string' ? parseInt(id, 10) : null;

  const fetchGroupInfo = useCallback(async () => {
    if (!groupId) return;

    setIsLoading(true);
    setError(null);

    try {
      const info = await getGroupInfo(groupId);
      setGroupInfo(info);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load group info');
    } finally {
      setIsLoading(false);
    }
  }, [groupId]);

  useEffect(() => {
    fetchGroupInfo();
  }, [fetchGroupInfo]);

  const handleCopyLink = async () => {
    if (!groupId) return;
    
    const joinUrl = `${window.location.origin}/join?group=${groupId}`;
    
    try {
      await navigator.clipboard.writeText(joinUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      // Fallback for browsers that don't support clipboard API
      const textArea = document.createElement('textarea');
      textArea.value = joinUrl;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand('copy');
      document.body.removeChild(textArea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleLeaveGroup = async () => {
    if (!currentUser?.id) return;
    
    setIsLeaving(true);
    try {
      await deleteUser(currentUser.id);
      clearUser();
      router.push('/');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to leave group');
      setIsLeaving(false);
      setShowLeaveConfirm(false);
    }
  };

  // Helper to get vote progress for a user
  const getVoteProgress = (userId: number) => {
    return groupInfo?.user_progress.find(p => p.user_id === userId);
  };

  if (!isHydrated || isLoading) {
    return (
      <div className="flex h-full items-center justify-center bg-slate-50">
        <Loader2 className="w-8 h-8 animate-spin text-rose-500" />
      </div>
    );
  }

  if (error || !groupInfo) {
    return (
      <div className="flex h-full flex-col items-center justify-center bg-slate-50 p-6 text-center">
        <div className="text-5xl mb-4">😕</div>
        <h2 className="text-xl font-bold text-slate-900 mb-2">Failed to load group</h2>
        <p className="text-slate-600 mb-6">{error}</p>
        <button
          onClick={fetchGroupInfo}
          className="bg-rose-500 text-white px-6 py-3 rounded-full font-bold shadow-lg"
        >
          Try Again
        </button>
      </div>
    );
  }

  const destinationNames = groupInfo.destinations.map(d => d.name).join(', ');

  return (
    <div className="bg-slate-50 h-full pb-24 flex flex-col overflow-y-auto">
      {/* Group Info Section with colored background */}
      <div className="bg-rose-50 px-6 pt-8 pb-10 rounded-b-[2.5rem] shadow-sm z-10 relative overflow-hidden">
        {/* Decorative circles */}
        <div className="absolute top-[-20%] right-[-10%] w-64 h-64 bg-rose-100/50 rounded-full blur-3xl pointer-events-none"></div>
        <div className="absolute bottom-[-20%] left-[-10%] w-64 h-64 bg-rose-100/50 rounded-full blur-3xl pointer-events-none"></div>

        <div className="relative z-10">
          <div className="flex justify-between items-start mb-6">
            <div>
              <h1 className="font-bold text-slate-900 text-3xl mb-2">{groupInfo.group_name}</h1>
              <div className="flex items-center gap-2 text-slate-600">
                <span className="bg-white/60 backdrop-blur px-3 py-1 rounded-full font-mono text-xs font-medium border border-rose-100">
                  ID: {groupInfo.group_id}
                </span>
              </div>
            </div>
            <div className="bg-white p-3 rounded-2xl shadow-sm text-center min-w-[80px]">
              <span className="block text-2xl font-bold text-rose-500 leading-none">{groupInfo.users.length}</span>
              <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wide">Members</span>
            </div>
          </div>

          <div className="bg-white/80 backdrop-blur rounded-2xl p-5 shadow-sm border border-rose-100 flex flex-col gap-4">
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 rounded-full bg-rose-100 flex items-center justify-center text-rose-600 flex-shrink-0">
                <MapPin className="w-5 h-5" />
              </div>
              <div>
                <p className="text-xs text-slate-500 font-bold uppercase tracking-wider">Destination</p>
                <p className="text-slate-900 font-bold text-lg leading-tight">{destinationNames || 'No destination set'}</p>
              </div>
            </div>
            
            <div className="h-px bg-slate-100 w-full"></div>

            <div className="flex items-center gap-4">
              <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center text-blue-600 flex-shrink-0">
                <Calendar className="w-5 h-5" />
              </div>
              <div>
                <p className="text-xs text-slate-500 font-bold uppercase tracking-wider">Dates</p>
                <p className="text-slate-900 font-bold text-lg leading-tight">
                  {new Date(groupInfo.date_start).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} - {new Date(groupInfo.date_end).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                </p>
              </div>
            </div>
            
            <div className="h-px bg-slate-100 w-full"></div>

            <div className="flex items-center gap-4">
              <div className="w-10 h-10 rounded-full bg-purple-100 flex items-center justify-center text-purple-600 flex-shrink-0">
                <Users className="w-5 h-5" />
              </div>
              <div>
                <p className="text-xs text-slate-500 font-bold uppercase tracking-wider">Group Size</p>
                <p className="text-slate-900 font-bold text-lg leading-tight">
                  {groupInfo.adults} adults
                  {groupInfo.children > 0 && `, ${groupInfo.children} children`}
                  {groupInfo.infants > 0 && `, ${groupInfo.infants} infants`}
                  {groupInfo.pets > 0 && `, ${groupInfo.pets} pets`}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="p-6 flex flex-col gap-6 -mt-2">
        
        {/* Members List */}
        <div>
          <h2 className="font-bold text-slate-900 text-lg mb-4 px-2">Travelers</h2>
          <div className="flex flex-col gap-3">
            {groupInfo.users.map((member) => {
              const progress = getVoteProgress(member.id);
              return (
                <div key={member.id} className="bg-white rounded-xl p-4 shadow-sm border border-slate-100">
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 rounded-full bg-slate-200 overflow-hidden relative flex-shrink-0 ring-2 ring-white shadow-sm">
                      {member.avatar ? (
                        <img 
                          src={member.avatar} 
                          alt={member.nickname} 
                          className="absolute inset-0 w-full h-full object-cover" 
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center text-slate-400 font-bold bg-slate-100">
                          {member.nickname[0].toUpperCase()}
                        </div>
                      )}
                    </div>
                    
                    <div className="flex-1 min-w-0">
                      <h3 className="font-bold text-slate-900 truncate text-base flex items-center gap-2">
                        {member.nickname}
                        {member.id === currentUser?.id && (
                          <span className="text-xs font-normal text-rose-500 bg-rose-50 px-2 py-0.5 rounded-full">You</span>
                        )}
                      </h3>
                      {progress && groupInfo.total_listings > 0 && (
                        <p className="text-xs text-slate-500 mt-0.5">
                          {progress.votes_cast}/{progress.total_listings} voted
                        </p>
                      )}
                    </div>
                  </div>
                  
                  {/* Vote progress bar */}
                  {progress && groupInfo.total_listings > 0 && (
                    <div className="mt-3">
                      <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                        <div 
                          className="h-full bg-rose-400 rounded-full transition-all duration-300"
                          style={{ width: `${Math.min(100, (progress.votes_cast / progress.total_listings) * 100)}%` }}
                        />
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
        
        {/* Invite Link */}
        <div className="mt-4 bg-slate-900 text-white rounded-2xl p-6 text-center shadow-lg mx-2 relative overflow-hidden">
          <div className="absolute top-0 right-0 w-32 h-32 bg-white/5 rounded-full -mr-10 -mt-10 pointer-events-none"></div>
          <div className="relative z-10">
            <p className="text-slate-300 text-sm mb-3 font-medium">Invite friends to join</p>
            <button 
              onClick={handleCopyLink}
              className="bg-white/10 hover:bg-white/20 text-white px-8 py-3 rounded-xl font-medium text-sm active:scale-95 transition-all border border-white/10 flex items-center gap-2 mx-auto"
            >
              {copied ? (
                <>
                  <Check className="w-4 h-4" />
                  Link Copied!
                </>
              ) : (
                <>
                  <Copy className="w-4 h-4" />
                  Copy Invite Link
                </>
              )}
            </button>
            <p className="text-xs text-slate-400 mt-3">
              Share this link with your friends
            </p>
          </div>
        </div>

        {/* Leave Group Button */}
        <div className="mt-2 mx-2">
          <button
            onClick={() => setShowLeaveConfirm(true)}
            className="w-full py-3 text-slate-500 hover:text-red-500 text-sm font-medium flex items-center justify-center gap-2 transition-colors"
          >
            <LogOut className="w-4 h-4" />
            Leave Group
          </button>
        </div>

      </div>

      {/* Leave Group Confirmation Modal */}
      {showLeaveConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-6">
          <div className="bg-white rounded-2xl p-6 max-w-sm w-full shadow-xl">
            <h3 className="text-lg font-bold text-slate-900 mb-2">Leave group?</h3>
            <p className="text-slate-600 text-sm mb-6">
              Your votes will be deleted and you&apos;ll need to rejoin to participate again.
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setShowLeaveConfirm(false)}
                disabled={isLeaving}
                className="flex-1 py-3 px-4 rounded-xl font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleLeaveGroup}
                disabled={isLeaving}
                className="flex-1 py-3 px-4 rounded-xl font-medium text-white bg-red-500 hover:bg-red-600 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {isLeaving ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  'Leave'
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
