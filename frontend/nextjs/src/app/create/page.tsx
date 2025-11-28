"use client";

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAppStore } from '../../store/useAppStore';
import { Group } from '../../types';
import { Calendar, MapPin } from 'lucide-react';

export default function CreateGroupPage() {
  const router = useRouter();
  const createGroup = useAppStore((state) => state.createGroup);
  const setCurrentUser = useAppStore((state) => state.setCurrentUser);
  
  const [groupName, setGroupName] = useState('Summer 2025 ☀️');
  const [location, setLocation] = useState('Mallorca, ES');
  const [startDate, setStartDate] = useState('2025-07-15');
  const [endDate, setEndDate] = useState('2025-07-22');
  const [userName, setUserName] = useState('');

  const handleCreate = () => {
    if (!userName) {
      alert('Please enter your name');
      return;
    }

    const user = {
      id: Math.random().toString(36).substring(7),
      name: userName,
      avatar: `https://api.dicebear.com/7.x/avataaars/svg?seed=${userName}`
    };

    setCurrentUser(user);

    const newGroup: Group = {
      id: Math.random().toString(36).substring(7),
      name: groupName,
      location,
      startDate,
      endDate,
      members: [user],
      code: Math.random().toString(36).substring(2, 8).toUpperCase()
    };

    createGroup(newGroup);
    router.push(`/group/${newGroup.id}`);
  };

  return (
    <div className="flex h-full flex-col bg-white p-6 overflow-y-auto pb-8">
      <h1 className="mt-4 mb-2 text-3xl font-bold text-slate-900">Plan a Trip</h1>
      <p className="mb-8 text-slate-600">Create a group to start voting.</p>

      <div className="flex flex-col gap-6">
        <div>
          <label className="mb-2 block font-medium text-slate-700">Your Name</label>
          <input
            type="text"
            value={userName}
            onChange={(e) => setUserName(e.target.value)}
            placeholder="Enter your name"
            className="w-full rounded-xl border-0 bg-slate-50 p-4 text-slate-900 ring-1 ring-inset ring-slate-200 placeholder:text-slate-400 focus:ring-2 focus:ring-inset focus:ring-rose-500"
          />
        </div>

        <div>
          <label className="mb-2 block font-medium text-slate-700">Group Name</label>
          <input
            type="text"
            value={groupName}
            onChange={(e) => setGroupName(e.target.value)}
            className="w-full rounded-xl border-0 bg-slate-50 p-4 text-slate-900 ring-1 ring-inset ring-slate-200 focus:ring-2 focus:ring-inset focus:ring-rose-500"
          />
        </div>

        <div>
          <label className="mb-2 block font-medium text-slate-700">Destination(s)</label>
          <div className="flex items-center rounded-xl bg-rose-100 px-3 py-1 w-fit mb-2">
            <span className="text-rose-600 font-medium">{location}</span>
            <button className="ml-2 text-rose-400 hover:text-rose-600">×</button>
          </div>
          <div className="relative">
             <MapPin className="absolute left-4 top-4 h-5 w-5 text-slate-400" />
            <input
              type="text"
              placeholder="Add another destination..."
              className="w-full rounded-xl border-0 bg-slate-50 p-4 pl-12 text-slate-900 ring-1 ring-inset ring-slate-200 placeholder:text-slate-400 focus:ring-2 focus:ring-inset focus:ring-rose-500"
            />
          </div>
        </div>

        <div>
          <label className="mb-2 block font-medium text-slate-700">Dates</label>
          <div className="grid grid-cols-2 gap-4">
            <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Calendar className="h-5 w-5 text-slate-400" />
                </div>
                <input
                  type="date"
                  value={startDate}
                  min={new Date().toISOString().split('T')[0]}
                  onChange={(e) => {
                    const newStart = e.target.value;
                    setStartDate(newStart);
                    if (endDate && newStart > endDate) {
                      setEndDate(newStart);
                    }
                  }}
                  className="w-full rounded-xl border-0 bg-slate-50 p-4 pl-10 text-slate-900 ring-1 ring-inset ring-slate-200 focus:ring-2 focus:ring-inset focus:ring-rose-500"
                />
            </div>
            <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Calendar className="h-5 w-5 text-slate-400" />
                </div>
                <input
                  type="date"
                  value={endDate}
                  min={startDate || new Date().toISOString().split('T')[0]}
                  onChange={(e) => setEndDate(e.target.value)}
                  className="w-full rounded-xl border-0 bg-slate-50 p-4 pl-10 text-slate-900 ring-1 ring-inset ring-slate-200 focus:ring-2 focus:ring-inset focus:ring-rose-500"
                />
            </div>
          </div>
        </div>
      </div>

      <div className="mt-auto pt-8">
        <button
          onClick={handleCreate}
          className="flex h-14 w-full items-center justify-center rounded-xl bg-rose-500 text-lg font-bold text-white shadow-lg transition-colors hover:bg-rose-600"
        >
          Create Group
        </button>
      </div>
    </div>
  );
}

