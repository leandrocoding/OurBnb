"use client";

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAppStore } from '../../store/useAppStore';
import { createGroup, joinGroup } from '../../lib/api';
import { Calendar, MapPin, X, Plus, Users, Loader2 } from 'lucide-react';

export default function CreateGroupPage() {
  const router = useRouter();
  const setCurrentUser = useAppStore((state) => state.setCurrentUser);
  
  const [groupName, setGroupName] = useState('Summer 2025');
  const [destinations, setDestinations] = useState<string[]>(['Mallorca, ES']);
  const [newDestination, setNewDestination] = useState('');
  const [startDate, setStartDate] = useState('2025-07-15');
  const [endDate, setEndDate] = useState('2025-07-22');
  const [userName, setUserName] = useState('');
  const [adults, setAdults] = useState(2);
  const [children, setChildren] = useState(0);
  const [infants, setInfants] = useState(0);
  const [pets, setPets] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const addDestination = () => {
    if (newDestination.trim() && !destinations.includes(newDestination.trim())) {
      setDestinations([...destinations, newDestination.trim()]);
      setNewDestination('');
    }
  };

  const removeDestination = (dest: string) => {
    setDestinations(destinations.filter(d => d !== dest));
  };

  const handleCreate = async () => {
    if (!userName.trim()) {
      setError('Please enter your name');
      return;
    }

    if (destinations.length === 0) {
      setError('Please add at least one destination');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      // Create the group
      const groupResponse = await createGroup({
        group_name: groupName,
        destinations: destinations,
        date_start: startDate,
        date_end: endDate,
        adults,
        children,
        infants,
        pets,
      });

      const groupId = groupResponse.group_id;

      // Join the group as the creator
      const avatar = `https://api.dicebear.com/7.x/avataaars/svg?seed=${encodeURIComponent(userName)}`;
      const joinResponse = await joinGroup(groupId, userName, avatar);

      // Store user in local state
      setCurrentUser({
        id: joinResponse.user_id,
        groupId: groupId,
        nickname: userName,
        avatar,
      });

      // Navigate to filters page to set preferences (triggers scraper)
      router.push(`/group/${groupId}/filters`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create group');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex h-full flex-col bg-white p-6 overflow-y-auto pb-8">
      <h1 className="mt-4 mb-2 text-3xl font-bold text-slate-900">Plan a Trip</h1>
      <p className="mb-8 text-slate-600">Create a group to start voting.</p>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-xl text-red-600 text-sm">
          {error}
        </div>
      )}

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
          <div className="flex flex-wrap gap-2 mb-2">
            {destinations.map((dest) => (
              <div key={dest} className="flex items-center rounded-xl bg-rose-100 px-3 py-1">
                <span className="text-rose-600 font-medium">{dest}</span>
                <button 
                  onClick={() => removeDestination(dest)}
                  className="ml-2 text-rose-400 hover:text-rose-600"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
          <div className="relative flex gap-2">
            <div className="relative flex-1">
              <MapPin className="absolute left-4 top-4 h-5 w-5 text-slate-400" />
              <input
                type="text"
                value={newDestination}
                onChange={(e) => setNewDestination(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && addDestination()}
                placeholder="Add a destination..."
                className="w-full rounded-xl border-0 bg-slate-50 p-4 pl-12 text-slate-900 ring-1 ring-inset ring-slate-200 placeholder:text-slate-400 focus:ring-2 focus:ring-inset focus:ring-rose-500"
              />
            </div>
            <button
              onClick={addDestination}
              className="px-4 rounded-xl bg-slate-100 text-slate-600 hover:bg-slate-200 transition-colors"
            >
              <Plus className="w-5 h-5" />
            </button>
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

        <div>
          <label className="mb-2 block font-medium text-slate-700">
            <Users className="w-4 h-4 inline mr-2" />
            Group Size
          </label>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-slate-500 mb-1 block">Adults (13+)</label>
              <input
                type="number"
                min={1}
                value={adults}
                onChange={(e) => setAdults(parseInt(e.target.value) || 1)}
                className="w-full rounded-xl border-0 bg-slate-50 p-3 text-slate-900 ring-1 ring-inset ring-slate-200 focus:ring-2 focus:ring-inset focus:ring-rose-500"
              />
            </div>
            <div>
              <label className="text-xs text-slate-500 mb-1 block">Children (2-12)</label>
              <input
                type="number"
                min={0}
                value={children}
                onChange={(e) => setChildren(parseInt(e.target.value) || 0)}
                className="w-full rounded-xl border-0 bg-slate-50 p-3 text-slate-900 ring-1 ring-inset ring-slate-200 focus:ring-2 focus:ring-inset focus:ring-rose-500"
              />
            </div>
            <div>
              <label className="text-xs text-slate-500 mb-1 block">Infants ({"<"}2)</label>
              <input
                type="number"
                min={0}
                value={infants}
                onChange={(e) => setInfants(parseInt(e.target.value) || 0)}
                className="w-full rounded-xl border-0 bg-slate-50 p-3 text-slate-900 ring-1 ring-inset ring-slate-200 focus:ring-2 focus:ring-inset focus:ring-rose-500"
              />
            </div>
            <div>
              <label className="text-xs text-slate-500 mb-1 block">Pets</label>
              <input
                type="number"
                min={0}
                value={pets}
                onChange={(e) => setPets(parseInt(e.target.value) || 0)}
                className="w-full rounded-xl border-0 bg-slate-50 p-3 text-slate-900 ring-1 ring-inset ring-slate-200 focus:ring-2 focus:ring-inset focus:ring-rose-500"
              />
            </div>
          </div>
        </div>
      </div>

      <div className="mt-auto pt-8">
        <button
          onClick={handleCreate}
          disabled={isLoading}
          className="flex h-14 w-full items-center justify-center rounded-xl bg-rose-500 text-lg font-bold text-white shadow-lg transition-colors hover:bg-rose-600 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isLoading ? (
            <>
              <Loader2 className="w-5 h-5 mr-2 animate-spin" />
              Creating...
            </>
          ) : (
            'Create Group'
          )}
        </button>
      </div>
    </div>
  );
}
