"use client";

import { useAppStore } from '../../../../store/useAppStore';
import { User, Calendar, MapPin, Wallet } from 'lucide-react';
import Image from 'next/image';

export default function MembersPage() {
  const { currentGroup, currentUser } = useAppStore();

  if (!currentGroup) {
      return <div className="p-6 text-center">Group not found.</div>;
  }

  // Mock data for budgets since it's not in the User type yet
  const getMemberBudget = (userId: string) => {
      // Deterministic pseudo-random budget based on ID
      const seed = userId.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
      return 150 + (seed % 350);
  };

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
                    <h1 className="font-bold text-slate-900 text-3xl mb-2">{currentGroup.name}</h1>
                    <div className="flex items-center gap-2 text-slate-600">
                        <span className="bg-white/60 backdrop-blur px-3 py-1 rounded-full font-mono text-xs font-medium border border-rose-100">#{currentGroup.code}</span>
                    </div>
                </div>
                <div className="bg-white p-3 rounded-2xl shadow-sm text-center min-w-[80px]">
                    <span className="block text-2xl font-bold text-rose-500 leading-none">{currentGroup.members.length}</span>
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
                          <p className="text-slate-900 font-bold text-lg leading-tight">{currentGroup.location}</p>
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
                              {new Date(currentGroup.startDate).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} - {new Date(currentGroup.endDate).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
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
                  {currentGroup.members.map((member) => (
                      <div key={member.id} className="bg-white rounded-xl p-4 shadow-sm flex items-center gap-4 border border-slate-100">
                          <div className="w-12 h-12 rounded-full bg-slate-200 overflow-hidden relative flex-shrink-0 ring-2 ring-white shadow-sm">
                              {member.avatar ? (
                                  <Image src={member.avatar} alt={member.name} fill className="object-cover" />
                              ) : (
                                  <div className="w-full h-full flex items-center justify-center text-slate-400 font-bold bg-slate-100">
                                      {member.name[0]}
                                  </div>
                              )}
                          </div>
                          
                          <div className="flex-1 min-w-0">
                              <div className="flex justify-between items-center mb-1">
                                  <h3 className="font-bold text-slate-900 truncate text-base">
                                      {member.name}
                                      {member.id === currentUser?.id && <span className="ml-2 text-xs font-normal text-rose-500 bg-rose-50 px-2 py-0.5 rounded-full">You</span>}
                                  </h3>
                              </div>
                              <div className="flex items-center gap-1.5 text-sm text-slate-500">
                                  <Wallet className="w-3.5 h-3.5 text-slate-400" />
                                  <span className="font-medium text-slate-600">${getMemberBudget(member.id)}</span> <span className="text-xs">/ night</span>
                              </div>
                          </div>
                      </div>
                  ))}
              </div>
          </div>
          
          {/* Invite Code */}
          <div className="mt-4 bg-slate-900 text-white rounded-2xl p-6 text-center shadow-lg mx-2 relative overflow-hidden">
               <div className="absolute top-0 right-0 w-32 h-32 bg-white/5 rounded-full -mr-10 -mt-10 pointer-events-none"></div>
               <div className="relative z-10">
                  <p className="text-slate-300 text-sm mb-3 font-medium">Invite friends with this code</p>
                  <button 
                    onClick={() => navigator.clipboard.writeText(currentGroup.code)}
                    className="bg-white/10 hover:bg-white/20 text-white px-8 py-3 rounded-xl font-mono text-xl tracking-[0.2em] font-bold active:scale-95 transition-all border border-white/10"
                  >
                      {currentGroup.code}
                  </button>
                  <p className="text-xs text-slate-400 mt-2">Tap to copy</p>
              </div>
          </div>

      </div>
    </div>
  );
}

