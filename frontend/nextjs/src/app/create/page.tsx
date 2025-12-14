"use client";

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAppStore } from '../../store/useAppStore';
import { createGroup, joinGroup } from '../../lib/api';
import { MapPin, X, Plus, Users, Loader2, ChevronLeft, ChevronRight } from 'lucide-react';
import {
  DateRangePicker,
  Label,
  Group,
  DateInput,
  DateSegment,
  Button,
  Popover,
  Dialog,
  RangeCalendar,
  CalendarGrid,
  CalendarGridHeader,
  CalendarHeaderCell,
  CalendarGridBody,
  CalendarCell,
} from 'react-aria-components';
import { today, getLocalTimeZone } from '@internationalized/date';
import type { DateRange } from 'react-aria-components';

// Calculate default dates: one month from now, spanning one week
function getDefaultDateRange(): DateRange {
  const now = today(getLocalTimeZone());
  const startDate = now.add({ months: 1 });
  const endDate = startDate.add({ days: 7 });
  return { start: startDate, end: endDate };
}

export default function CreateGroupPage() {
  const router = useRouter();
  const setCurrentUser = useAppStore((state) => state.setCurrentUser);
  
  const [groupName, setGroupName] = useState('Summer 2025');
  const [destinations, setDestinations] = useState<string[]>(['Mallorca, ES']);
  const [newDestination, setNewDestination] = useState('');
  const [dateRange, setDateRange] = useState<DateRange>(getDefaultDateRange);
  const [userName, setUserName] = useState('');
  const [adults, setAdults] = useState<number | string>(2);
  const [children, setChildren] = useState<number | string>(0);
  const [infants, setInfants] = useState<number | string>(0);
  const [pets, setPets] = useState<number | string>(0);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isDatePickerOpen, setIsDatePickerOpen] = useState(false);

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
        date_start: dateRange.start.toString(),
        date_end: dateRange.end.toString(),
        adults: Number(adults) || 1,
        children: Number(children) || 0,
        infants: Number(infants) || 0,
        pets: Number(pets) || 0,
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

        <DateRangePicker
          value={dateRange}
          onChange={(value) => value && setDateRange(value)}
          minValue={today(getLocalTimeZone())}
          shouldCloseOnSelect={false}
          isOpen={isDatePickerOpen}
          onOpenChange={setIsDatePickerOpen}
          className="flex flex-col gap-2"
        >
          <Label className="font-medium text-slate-700">Dates</Label>
          <Button className="flex items-center gap-3 w-full rounded-xl border-0 bg-slate-50 p-4 text-slate-900 ring-1 ring-inset ring-slate-200 cursor-pointer hover:ring-slate-300 hover:bg-slate-100 transition-colors outline-none focus:ring-2 focus:ring-rose-500">
            <DateInput slot="start" className="flex pointer-events-none">
              {(segment) => (
                <DateSegment
                  segment={segment}
                  className="rounded outline-none data-[placeholder]:text-slate-400 tabular-nums"
                />
              )}
            </DateInput>
            <span className="text-slate-400">–</span>
            <DateInput slot="end" className="flex pointer-events-none">
              {(segment) => (
                <DateSegment
                  segment={segment}
                  className="rounded outline-none data-[placeholder]:text-slate-400 tabular-nums"
                />
              )}
            </DateInput>
            <ChevronRight className="ml-auto w-5 h-5 text-slate-400" />
          </Button>
          <Popover className="bg-white rounded-2xl shadow-xl border border-slate-200 p-4 max-h-[70vh] overflow-hidden max-sm:fixed max-sm:inset-0 max-sm:max-h-none max-sm:rounded-none max-sm:border-0 max-sm:z-50 max-sm:flex max-sm:flex-col">
            <Dialog className="outline-none max-sm:flex max-sm:flex-col max-sm:h-full">
              <RangeCalendar className="w-fit max-sm:flex max-sm:flex-col max-sm:h-full max-sm:w-full" visibleDuration={{ months: 12 }}>
                <header className="hidden max-sm:flex items-center mb-4 sticky top-0 bg-white z-10 pt-3 px-2 border-b border-slate-200 pb-3">
                  <button
                    type="button"
                    className="p-2 rounded-lg hover:bg-slate-100 transition-colors -ml-1"
                    onClick={() => setIsDatePickerOpen(false)}
                  >
                    <ChevronLeft className="w-6 h-6 text-slate-600" />
                  </button>
                </header>
                <div className="overflow-y-auto max-h-[calc(70vh-60px)] space-y-6 pr-2 max-sm:max-h-none max-sm:flex-1 max-sm:px-4 max-sm:flex max-sm:flex-col max-sm:items-center">
                  {Array.from({ length: 12 }, (_, i) => {
                    const monthDate = today(getLocalTimeZone()).add({ months: i });
                    const monthName = monthDate.toDate(getLocalTimeZone()).toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
                    return (
                      <div key={i} className="max-sm:w-fit">
                        <h3 className="font-semibold text-slate-900 text-center mb-3">{monthName}</h3>
                        <CalendarGrid offset={{ months: i }} className="border-separate border-spacing-1">
                          <CalendarGridHeader>
                            {(day) => (
                              <CalendarHeaderCell className="w-10 h-8 text-xs font-medium text-slate-500">
                                {day}
                              </CalendarHeaderCell>
                            )}
                          </CalendarGridHeader>
                          <CalendarGridBody>
                            {(date) => (
                              <CalendarCell
                                date={date}
                                className="w-10 h-10 rounded-lg flex items-center justify-center text-sm text-slate-900 outline-none
                                  hover:bg-slate-100 transition-colors cursor-pointer
                                  data-[selected]:bg-rose-500 data-[selected]:text-white data-[selected]:hover:bg-rose-600
                                  data-[selection-start]:rounded-l-lg data-[selection-end]:rounded-r-lg
                                  data-[outside-month]:invisible
                                  data-[disabled]:text-slate-300 data-[disabled]:pointer-events-none data-[disabled]:cursor-not-allowed
                                  data-[unavailable]:text-slate-300 data-[unavailable]:line-through data-[unavailable]:cursor-not-allowed
                                  focus:ring-2 focus:ring-rose-500 focus:ring-offset-1"
                              />
                            )}
                          </CalendarGridBody>
                        </CalendarGrid>
                      </div>
                    );
                  })}
                </div>
              </RangeCalendar>
            </Dialog>
          </Popover>
        </DateRangePicker>

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
                onChange={(e) => setAdults(e.target.value === '' ? '' : parseInt(e.target.value))}
                onBlur={() => setAdults(Number(adults) || 1)}
                className="w-full rounded-xl border-0 bg-slate-50 p-3 text-slate-900 ring-1 ring-inset ring-slate-200 focus:ring-2 focus:ring-inset focus:ring-rose-500"
              />
            </div>
            <div>
              <label className="text-xs text-slate-500 mb-1 block">Children (2-12)</label>
              <input
                type="number"
                min={0}
                value={children}
                onChange={(e) => setChildren(e.target.value === '' ? '' : parseInt(e.target.value))}
                onBlur={() => setChildren(Number(children) || 0)}
                className="w-full rounded-xl border-0 bg-slate-50 p-3 text-slate-900 ring-1 ring-inset ring-slate-200 focus:ring-2 focus:ring-inset focus:ring-rose-500"
              />
            </div>
            <div>
              <label className="text-xs text-slate-500 mb-1 block">Infants ({"<"}2)</label>
              <input
                type="number"
                min={0}
                value={infants}
                onChange={(e) => setInfants(e.target.value === '' ? '' : parseInt(e.target.value))}
                onBlur={() => setInfants(Number(infants) || 0)}
                className="w-full rounded-xl border-0 bg-slate-50 p-3 text-slate-900 ring-1 ring-inset ring-slate-200 focus:ring-2 focus:ring-inset focus:ring-rose-500"
              />
            </div>
            <div>
              <label className="text-xs text-slate-500 mb-1 block">Pets</label>
              <input
                type="number"
                min={0}
                value={pets}
                onChange={(e) => setPets(e.target.value === '' ? '' : parseInt(e.target.value))}
                onBlur={() => setPets(Number(pets) || 0)}
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
