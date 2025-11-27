import Link from 'next/link';

export default function LandingPage() {
  return (
    <div className="flex h-full flex-col items-center justify-center bg-white p-4 text-center overflow-y-auto pb-8">
      <h1 className="mb-2 text-4xl font-bold text-slate-900">Plan a Trip</h1>
      <p className="mb-8 text-slate-600">Create a group to start voting.</p>
      
      <div className="flex w-full max-w-xs flex-col gap-4">
        <Link 
          href="/create"
          className="flex h-12 w-full items-center justify-center rounded-full bg-rose-500 font-semibold text-white transition-colors hover:bg-rose-600"
        >
          Create Group
        </Link>
        
        <Link 
          href="/join"
          className="flex h-12 w-full items-center justify-center rounded-full border-2 border-slate-200 font-semibold text-slate-700 transition-colors hover:bg-slate-50"
        >
          Join Group
        </Link>
      </div>
    </div>
  );
}
