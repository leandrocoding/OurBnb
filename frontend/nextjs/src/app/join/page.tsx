"use client";

import { useState, useEffect, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAppStore } from '../../store/useAppStore';
import { getGroupInfo, joinGroup, GroupInfo } from '../../lib/api';
import { Loader2, MapPin, Calendar, Users } from 'lucide-react';

function JoinGroupContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const setCurrentUser = useAppStore((state) => state.setCurrentUser);

  const [userName, setUserName] = useState('');
  const [groupId, setGroupId] = useState<number | null>(null);
  const [groupInfo, setGroupInfo] = useState<GroupInfo | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isJoining, setIsJoining] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const groupParam = searchParams.get('group');
    if (groupParam) {
      const id = parseInt(groupParam, 10);
      if (!isNaN(id)) {
        setGroupId(id);
        fetchGroupInfo(id);
      } else {
        setError('Invalid group ID');
        setIsLoading(false);
      }
    } else {
      setError('No group ID provided. Use a link shared by the group creator.');
      setIsLoading(false);
    }
  }, [searchParams]);

  const fetchGroupInfo = async (id: number) => {
    try {
      const info = await getGroupInfo(id);
      setGroupInfo(info);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load group');
    } finally {
      setIsLoading(false);
    }
  };

  const handleJoin = async () => {
    if (!userName.trim()) {
      setError('Please enter your name');
      return;
    }

    if (!groupId) {
      setError('No group ID');
      return;
    }

    setIsJoining(true);
    setError(null);

    try {
      const avatar = `https://api.dicebear.com/7.x/avataaars/svg?seed=${encodeURIComponent(userName)}`;
      const response = await joinGroup(groupId, userName, avatar);

      setCurrentUser({
        id: response.user_id,
        groupId: groupId,
        nickname: userName,
        avatar,
      });

      // Navigate to filters page to set preferences (triggers scraper)
      router.push(`/group/${groupId}/filters`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to join group');
    } finally {
      setIsJoining(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center bg-white">
        <Loader2 className="w-8 h-8 animate-spin text-rose-500" />
      </div>
    );
  }

  if (!groupInfo) {
    return (
      <div className="flex h-full flex-col items-center justify-center bg-white p-6 text-center">
        <div className="text-6xl mb-4">😕</div>
        <h1 className="text-2xl font-bold text-slate-900 mb-2">Group not found</h1>
        <p className="text-slate-600 mb-6">{error || 'The group you are looking for does not exist.'}</p>
        <button
          onClick={() => router.push('/')}
          className="bg-rose-500 text-white px-6 py-3 rounded-xl font-bold"
        >
          Go Home
        </button>
      </div>
    );
  }

  // Get first member as the inviter (group creator)
  const inviter = groupInfo.users[0];
  const destinationNames = groupInfo.destinations.map(d => d.name).join(', ');

  return (
    <div className="flex h-full flex-col bg-white p-6 text-center overflow-y-auto pb-8">
      <h1 className="mt-4 mb-2 text-2xl font-bold text-slate-900">
        {inviter ? `${inviter.nickname} invited you to` : 'You are invited to'}
      </h1>
      <h2 className="mb-8 text-3xl font-bold text-slate-900">{groupInfo.group_name}</h2>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-xl text-red-600 text-sm">
          {error}
        </div>
      )}

      {/* Member avatars */}
      <div className="relative mb-8 flex h-48 w-full items-center justify-center">
        {groupInfo.users.length > 0 ? (
          <>
            {/* Center avatar (inviter) */}
            {inviter && (
              <div className="absolute left-1/2 top-1/2 h-24 w-24 -translate-x-1/2 -translate-y-1/2 overflow-hidden rounded-full border-4 border-white shadow-xl">
                <img
                  src={inviter.avatar || `https://api.dicebear.com/7.x/avataaars/svg?seed=${inviter.nickname}`}
                  alt={inviter.nickname}
                  width={96}
                  height={96}
                  className="object-cover w-full h-full"
                />
              </div>
            )}

            {/* Other members around */}
            {groupInfo.users.slice(1, 5).map((user, i) => {
              const positions = [
                { left: '25%', top: '30%' },
                { right: '25%', top: '60%' },
                { right: '30%', top: '25%' },
                { left: '30%', bottom: '10%' },
              ];
              const pos = positions[i];
              return (
                <div
                  key={user.id}
                  className="absolute h-16 w-16 overflow-hidden rounded-full border-4 border-white shadow-lg"
                  style={pos}
                >
                  <img
                    src={user.avatar || `https://api.dicebear.com/7.x/avataaars/svg?seed=${user.nickname}`}
                    alt={user.nickname}
                    width={64}
                    height={64}
                    className="object-cover w-full h-full"
                  />
                </div>
              );
            })}
          </>
        ) : (
          <div className="h-24 w-24 rounded-full bg-rose-100 flex items-center justify-center">
            <Users className="w-10 h-10 text-rose-400" />
          </div>
        )}
      </div>

      {/* Trip details */}
      <div className="bg-slate-50 rounded-2xl p-4 mb-8 text-left">
        <div className="flex items-center gap-3 mb-3">
          <MapPin className="w-5 h-5 text-rose-500 shrink-0" />
          <span className="text-slate-700 font-medium">{destinationNames || 'No destination set'}</span>
        </div>
        <div className="flex items-center gap-3 mb-3">
          <Calendar className="w-5 h-5 text-rose-500 shrink-0" />
          <span className="text-slate-700 font-medium">
            {new Date(groupInfo.date_start).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} - {new Date(groupInfo.date_end).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
          </span>
        </div>
        <div className="flex items-center gap-3">
          <Users className="w-5 h-5 text-rose-500 shrink-0" />
          <span className="text-slate-700 font-medium">
            {groupInfo.adults} adults
            {groupInfo.children > 0 && `, ${groupInfo.children} children`}
            {groupInfo.infants > 0 && `, ${groupInfo.infants} infants`}
            {groupInfo.pets > 0 && `, ${groupInfo.pets} pets`}
          </span>
        </div>
      </div>

      <div className="flex flex-col gap-4 mt-auto">
        <input
          type="text"
          value={userName}
          onChange={(e) => setUserName(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleJoin()}
          placeholder="Enter your name"
          className="w-full rounded-xl border-0 bg-slate-50 p-4 text-slate-900 ring-1 ring-inset ring-slate-200 placeholder:text-slate-400 focus:ring-2 focus:ring-inset focus:ring-rose-500"
        />

        <button
          onClick={handleJoin}
          disabled={isJoining}
          className="flex h-14 w-full items-center justify-center rounded-xl bg-rose-500 text-lg font-bold text-white shadow-lg transition-colors hover:bg-rose-600 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isJoining ? (
            <>
              <Loader2 className="w-5 h-5 mr-2 animate-spin" />
              Joining...
            </>
          ) : (
            'Join Group'
          )}
        </button>
      </div>
    </div>
  );
}

export default function JoinGroupPage() {
  return (
    <Suspense fallback={
      <div className="flex h-full items-center justify-center bg-white">
        <Loader2 className="w-8 h-8 animate-spin text-rose-500" />
      </div>
    }>
      <JoinGroupContent />
    </Suspense>
  );
}
