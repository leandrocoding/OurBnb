"use client";

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAppStore } from '../../store/useAppStore';
import { getAllGroupsForDemo, DemoGroupInfo, UserInfo } from '../../lib/api';
import { Loader2, Users, ChevronRight } from 'lucide-react';

export default function DemoPage() {
  const router = useRouter();
  const setCurrentUser = useAppStore((state) => state.setCurrentUser);
  
  const [groups, setGroups] = useState<DemoGroupInfo[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [loggingInUser, setLoggingInUser] = useState<number | null>(null);

  useEffect(() => {
    fetchGroups();
  }, []);

  const fetchGroups = async () => {
    try {
      const response = await getAllGroupsForDemo();
      setGroups(response.groups);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load groups');
    } finally {
      setIsLoading(false);
    }
  };

  const handleLoginAsUser = (user: UserInfo, groupId: number) => {
    setLoggingInUser(user.id);
    
    // Set the user in the store
    setCurrentUser({
      id: user.id,
      groupId: groupId,
      nickname: user.nickname,
      avatar: user.avatar,
    });

    // Navigate to the group page
    router.push(`/group/${groupId}`);
  };

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center bg-white">
        <Loader2 className="w-8 h-8 animate-spin text-rose-500" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-full flex-col items-center justify-center bg-white p-6 text-center">
        <div className="text-6xl mb-4">😕</div>
        <h1 className="text-2xl font-bold text-slate-900 mb-2">Error Loading Groups</h1>
        <p className="text-slate-600 mb-6">{error}</p>
        <button
          onClick={() => router.push('/')}
          className="bg-rose-500 text-white px-6 py-3 rounded-xl font-bold"
        >
          Go Home
        </button>
      </div>
    );
  }

  if (groups.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center bg-white p-6 text-center">
        <div className="text-6xl mb-4">🏠</div>
        <h1 className="text-2xl font-bold text-slate-900 mb-2">No Groups Yet</h1>
        <p className="text-slate-600 mb-6">Create a group to get started with the demo.</p>
        <button
          onClick={() => router.push('/create')}
          className="bg-rose-500 text-white px-6 py-3 rounded-xl font-bold"
        >
          Create Group
        </button>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col bg-white overflow-y-auto">
      {/* Header */}
      <div className="sticky top-0 bg-white border-b border-slate-100 p-6 z-10">
        <h1 className="text-2xl font-bold text-slate-900">Demo Login</h1>
        <p className="text-slate-500 mt-1">Select a user to log in as</p>
      </div>

      {/* Groups list */}
      <div className="flex-1 p-6 space-y-6">
        {groups.map((group) => (
          <div key={group.group_id} className="bg-slate-50 rounded-2xl overflow-hidden">
            {/* Group header */}
            <div className="bg-gradient-to-r from-rose-500 to-rose-600 px-5 py-4">
              <div className="flex items-center gap-3">
                <div className="bg-white/20 rounded-full p-2">
                  <Users className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h2 className="text-lg font-bold text-white">{group.group_name}</h2>
                  <p className="text-rose-100 text-sm">
                    {group.users.length} {group.users.length === 1 ? 'member' : 'members'}
                  </p>
                </div>
              </div>
            </div>

            {/* Users list */}
            {group.users.length === 0 ? (
              <div className="p-5 text-center text-slate-500">
                No users in this group yet
              </div>
            ) : (
              <div className="divide-y divide-slate-200">
                {group.users.map((user) => (
                  <button
                    key={user.id}
                    onClick={() => handleLoginAsUser(user, group.group_id)}
                    disabled={loggingInUser !== null}
                    className="w-full flex items-center gap-4 p-4 hover:bg-slate-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {/* Avatar */}
                    <div className="w-12 h-12 rounded-full overflow-hidden border-2 border-white shadow-sm flex-shrink-0">
                      <img
                        src={user.avatar || `https://api.dicebear.com/7.x/avataaars/svg?seed=${user.nickname}`}
                        alt={user.nickname}
                        className="w-full h-full object-cover"
                      />
                    </div>

                    {/* User info */}
                    <div className="flex-1 text-left">
                      <p className="font-semibold text-slate-900">{user.nickname}</p>
                      <p className="text-sm text-slate-500">User ID: {user.id}</p>
                    </div>

                    {/* Loading or arrow */}
                    {loggingInUser === user.id ? (
                      <Loader2 className="w-5 h-5 text-rose-500 animate-spin" />
                    ) : (
                      <ChevronRight className="w-5 h-5 text-slate-400" />
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Footer */}
      <div className="sticky bottom-0 bg-white border-t border-slate-100 p-4">
        <button
          onClick={() => router.push('/')}
          className="w-full py-3 rounded-xl border-2 border-slate-200 font-semibold text-slate-700 hover:bg-slate-50 transition-colors"
        >
          Back to Home
        </button>
      </div>
    </div>
  );
}
