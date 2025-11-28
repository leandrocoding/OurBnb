"use client";

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAppStore } from '../../store/useAppStore';
import Image from 'next/image';

export default function JoinGroupPage() {
  const router = useRouter();
  const joinGroup = useAppStore((state) => state.joinGroup);
  
  const [userName, setUserName] = useState('');
  const [groupCode, setGroupCode] = useState('');

  const handleJoin = () => {
    if (!userName) {
      alert('Please enter your name');
      return;
    }

    const user = {
      id: Math.random().toString(36).substring(7),
      name: userName,
      avatar: `https://api.dicebear.com/7.x/avataaars/svg?seed=${userName}`
    };

    joinGroup(groupCode, user);
    router.push(`/group/g1`); // Redirect to mocked group ID
  };

  return (
    <div className="flex h-full flex-col bg-white p-6 text-center overflow-y-auto pb-8">
      <h1 className="mt-4 mb-2 text-3xl font-bold text-slate-900">Vincent invited you to</h1>
      <h2 className="mb-12 text-4xl font-bold text-slate-900">Group Name</h2>

      <div className="relative mb-12 flex h-64 w-full items-center justify-center">
        {/* Mock avatars floating */}
        <div className="absolute left-1/2 top-1/2 h-32 w-32 -translate-x-1/2 -translate-y-1/2 overflow-hidden rounded-full border-4 border-white shadow-xl">
           <Image src="https://api.dicebear.com/7.x/avataaars/svg?seed=Vincent" alt="Vincent" width={128} height={128} />
        </div>
        
        <div className="absolute left-1/4 top-1/3 h-20 w-20 -translate-x-1/2 -translate-y-1/2 overflow-hidden rounded-full border-4 border-white shadow-lg bg-emerald-400 flex items-center justify-center text-white font-bold text-xl">
           SK
        </div>

        <div className="absolute right-1/4 top-2/3 h-24 w-24 -translate-x-1/2 -translate-y-1/2 overflow-hidden rounded-full border-4 border-white shadow-lg">
           <Image src="https://images.unsplash.com/photo-1500648767791-00dcc994a43e?ixlib=rb-4.0.3&auto=format&fit=facearea&facepad=2&w=256&h=256&q=80" alt="User" width={96} height={96} />
        </div>
        
        <div className="absolute right-1/3 top-1/4 h-24 w-24 -translate-x-1/2 -translate-y-1/2 overflow-hidden rounded-full border-4 border-white shadow-lg">
           <Image src="https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?ixlib=rb-4.0.3&auto=format&fit=facearea&facepad=2&w=256&h=256&q=80" alt="User" width={96} height={96} />
        </div>

         <div className="absolute left-1/3 bottom-0 h-24 w-24 -translate-x-1/2 -translate-y-1/2 overflow-hidden rounded-full border-4 border-white shadow-lg bg-purple-500 flex items-center justify-center text-white font-bold text-xl">
           VF
        </div>
      </div>

      <div className="flex flex-col gap-6 mt-auto">
        <input
            type="text"
            value={userName}
            onChange={(e) => setUserName(e.target.value)}
            placeholder="Enter your name"
            className="w-full rounded-xl border-0 bg-slate-50 p-4 text-slate-900 ring-1 ring-inset ring-slate-200 placeholder:text-slate-400 focus:ring-2 focus:ring-inset focus:ring-blue-500"
        />
        
        <button
          onClick={handleJoin}
          className="flex h-14 w-full items-center justify-center rounded-xl bg-blue-600 text-lg font-bold text-white shadow-lg transition-colors hover:bg-blue-700"
        >
          Join
        </button>
      </div>
    </div>
  );
}

