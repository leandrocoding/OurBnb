"use client";

import { useState, useEffect } from 'react';
import { motion, useMotionValue, useTransform, useAnimate } from 'framer-motion';
import { Listing, VoteValue, VOTE_VETO, VOTE_OK, VOTE_LOVE, OtherVote, voteNumberToType } from '../types';
import { X, ThumbsUp, Heart, Star, ChevronLeft, ChevronRight, MapPin, ExternalLink } from 'lucide-react';

// Preload a single image and return a promise
function preloadImage(src: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve();
    img.onerror = reject;
    img.src = src;
  });
}

// Preload multiple images in sequence (left to right)
export function preloadImages(images: string[]): void {
  images.forEach((src) => {
    preloadImage(src).catch(() => {
      // Silently fail for individual images
    });
  });
}

interface VotingCardProps {
  listing: Listing;
  onVote: (vote: VoteValue) => void;
  onDragProgress?: (progress: number) => void; // 0 = centered, 1 = at vote threshold
  onVoteStart?: () => void; // Called immediately when vote animation starts
  otherVotes?: OtherVote[];
  location?: string;
  isBackground?: boolean;
}

export function VotingCard({ listing, onVote, onDragProgress, onVoteStart, otherVotes = [], location, isBackground = false }: VotingCardProps) {
  const [imageIndex, setImageIndex] = useState(0);
  const [scope, animate] = useAnimate();
  const [isAnimating, setIsAnimating] = useState(false);
  
  // Preload all images for this listing when it mounts
  useEffect(() => {
    if (listing.images.length > 0) {
      preloadImages(listing.images);
    }
  }, [listing.images]);
  const x = useMotionValue(0);
  const rotate = useTransform(x, [-200, 200], [-10, 10]);
  
  // Track drag progress and report to parent
  useEffect(() => {
    if (!onDragProgress) return;
    const unsubscribe = x.on("change", (latest) => {
      // Use 200px drag distance for full progress (slower movement)
      const progress = Math.min(1, Math.abs(latest) / 200);
      onDragProgress(progress);
    });
    return () => unsubscribe();
  }, [x, onDragProgress]);
  
  // Visual feedback opacities
  const nopeOpacity = useTransform(x, [-150, -20], [1, 0]);
  const likeOpacity = useTransform(x, [20, 150], [0, 1]);

  // Animate card off screen and then call onVote
  const handleVote = async (vote: VoteValue) => {
    if (isAnimating) return;
    setIsAnimating(true);
    
    // Notify parent immediately so background card can start animating
    onVoteStart?.();
    
    const direction = vote === VOTE_VETO ? -1 : 1;
    const exitX = direction * window.innerWidth;
    const exitRotation = direction * 20;
    
    await animate(scope.current, {
      x: exitX,
      rotate: exitRotation,
      opacity: 0,
    }, {
      duration: 0.3,
      ease: "easeOut",
    });
    
    onVote(vote);
  };

  // Derived likes/loves (vote values: 1=ok, 2=love, 3=super_love)
  const likers = otherVotes.filter(v => v.vote >= VOTE_OK);

  const nextImage = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (imageIndex < listing.images.length - 1) setImageIndex(prev => prev + 1);
  };

  const prevImage = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (imageIndex > 0) setImageIndex(prev => prev - 1);
  };

  // Format price
  const formatPrice = (price: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'CHF',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(price);
  };

  // Format rating
  const formatRating = (rating?: number) => {
    if (!rating) return 'New';
    return rating.toFixed(2);
  };

  if (isBackground) {
    return (
      <div className="absolute top-0 left-0 w-full h-full bg-white rounded-3xl shadow-xl overflow-hidden flex flex-col pointer-events-none z-0">
        <div className="relative h-3/5 w-full bg-slate-200">
           {listing.images[0] && (
             <img 
                src={listing.images[0]} 
                alt={listing.title}
                className="absolute inset-0 w-full h-full object-cover"
             />
           )}
           <div className="absolute bottom-0 left-0 w-full h-32 bg-gradient-to-t from-black/80 via-black/40 to-transparent" />
           <div className="absolute bottom-4 left-4 right-4 text-white z-20">
               <h2 className="text-2xl font-bold leading-tight drop-shadow-md mb-1">{listing.title}</h2>
               {location && (
                 <div className="flex items-center gap-1 text-white/90 text-sm font-medium">
                   <MapPin className="w-4 h-4" />
                   {location}
                 </div>
               )}
           </div>
        </div>
        <div className="p-5 flex flex-col flex-1">
            <div className="flex justify-between items-end mb-2">
                <div>
                    <div className="text-3xl font-bold text-slate-900">{formatPrice(listing.price)}</div>
                </div>
                <div className="flex items-center gap-1 text-slate-700 font-bold text-lg">
                    <Star className="w-5 h-5 fill-yellow-400 text-yellow-400" />
                    {formatRating(listing.rating)}
                    {listing.reviewCount && listing.reviewCount > 0 && (
                      <span className="text-slate-400 font-normal text-sm">({listing.reviewCount})</span>
                    )}
                </div>
            </div>
            <div className="flex flex-wrap gap-2 mt-2 mb-4">
                {listing.amenities.includes(4) && <span className="px-2 py-1 bg-slate-100 text-slate-600 text-xs rounded-md">Wifi</span>}
                {listing.amenities.includes(7) && <span className="px-2 py-1 bg-slate-100 text-slate-600 text-xs rounded-md">Pool</span>}
                {listing.bedrooms && <span className="px-2 py-1 bg-slate-100 text-slate-600 text-xs rounded-md">{listing.bedrooms} Bed</span>}
                {listing.bathrooms && <span className="px-2 py-1 bg-slate-100 text-slate-600 text-xs rounded-md">{listing.bathrooms} Bath</span>}
            </div>
            
            <div className="mt-auto flex items-center justify-center gap-6 pt-2">
                 <div className="w-14 h-14 rounded-full bg-white border border-slate-200 shadow-lg flex items-center justify-center text-slate-400">
                     <X className="w-6 h-6" />
                 </div>
                 <div className="w-14 h-14 rounded-full bg-white border border-slate-200 shadow-lg flex items-center justify-center text-yellow-500">
                     <ThumbsUp className="w-6 h-6" />
                 </div>
                 <div className="w-16 h-16 rounded-full bg-rose-500 shadow-xl shadow-rose-500/30 flex items-center justify-center text-white">
                     <Heart className="w-8 h-8 fill-current" />
                 </div>
            </div>
        </div>
      </div>
    );
  }

  return (
    <motion.div
      ref={scope}
      style={{ x, rotate }}
      drag="x"
      dragConstraints={{ left: 0, right: 0 }}
      onDragEnd={(e, { offset, velocity }) => {
        if (offset.x > 100) handleVote(VOTE_OK);
        else if (offset.x < -100) handleVote(VOTE_VETO);
      }}
      className="absolute top-0 left-0 w-full h-full bg-white rounded-3xl shadow-xl overflow-hidden flex flex-col z-10"
    >
      {/* Header / Liked by */}
      {likers.length > 0 && (
        <div className="absolute top-4 left-4 z-20 bg-white/90 backdrop-blur px-3 py-1.5 rounded-full flex items-center gap-2 shadow-sm text-sm font-medium text-slate-700">
           <div className="flex -space-x-2">
              {likers.slice(0, 3).map((l, i) => (
                  <div key={i} className="w-6 h-6 rounded-full bg-blue-500 border-2 border-white flex items-center justify-center text-[10px] text-white">
                      {l.userName[0]}
                  </div>
              ))}
           </div>
           <span>Liked by {likers[0].userName} {likers.length > 1 ? `& ${likers.length - 1} others` : ''}</span>
        </div>
      )}

      {/* Open on Airbnb button */}
      <a 
        href={listing.bookingLink || `https://www.airbnb.com/rooms/${listing.id}`}
        target="_blank"
        rel="noopener noreferrer"
        onClick={(e) => e.stopPropagation()}
        className="absolute top-4 right-4 z-20 bg-white/90 backdrop-blur p-2 rounded-full shadow-sm hover:bg-white hover:shadow-md transition-all"
        title="Open on Airbnb"
      >
        <ExternalLink className="w-5 h-5 text-slate-600" />
      </a>
      
      {/* Drag Feedback Overlays */}
      <motion.div style={{ opacity: likeOpacity }} className="absolute top-8 right-8 z-30 pointer-events-none transform rotate-12">
          <div className="border-4 border-green-500 text-green-500 font-bold text-4xl px-4 py-2 rounded-lg bg-white/20 backdrop-blur-sm uppercase tracking-wider">
              LIKE
          </div>
      </motion.div>
      <motion.div style={{ opacity: nopeOpacity }} className="absolute top-8 left-8 z-30 pointer-events-none transform -rotate-12">
          <div className="border-4 border-red-500 text-red-500 font-bold text-4xl px-4 py-2 rounded-lg bg-white/20 backdrop-blur-sm uppercase tracking-wider">
              NOPE
          </div>
      </motion.div>

      {/* Image Carousel */}
      <div className="relative h-3/5 w-full bg-slate-200 group">
        {listing.images[imageIndex] && (
            <img 
                src={listing.images[imageIndex]} 
                alt={`${listing.title} image ${imageIndex + 1}`}
                className="absolute inset-0 w-full h-full object-cover"
            />
        )}
        
        {/* Navigation Overlays */}
        {listing.images.length > 1 && (
            <>
                <div 
                    className="absolute inset-y-0 left-0 w-1/4 z-10 cursor-pointer flex items-center justify-start pl-2 opacity-0 group-hover:opacity-100 transition-opacity"
                    onClick={prevImage}
                >
                    {imageIndex > 0 && <div className="p-1 bg-black/30 rounded-full text-white"><ChevronLeft className="w-6 h-6" /></div>}
                </div>
                <div 
                    className="absolute inset-y-0 right-0 w-1/4 z-10 cursor-pointer flex items-center justify-end pr-2 opacity-0 group-hover:opacity-100 transition-opacity"
                    onClick={nextImage}
                >
                    {imageIndex < listing.images.length - 1 && <div className="p-1 bg-black/30 rounded-full text-white"><ChevronRight className="w-6 h-6" /></div>}
                </div>
                
                {/* Dots */}
                <div className="absolute bottom-24 left-0 w-full flex justify-center gap-1.5 z-20">
                    {listing.images.map((_, i) => (
                        <div 
                            key={i} 
                            className={`w-1.5 h-1.5 rounded-full shadow-sm transition-colors ${i === imageIndex ? 'bg-white' : 'bg-white/40'}`} 
                        />
                    ))}
                </div>
            </>
        )}

        <div className="absolute bottom-0 left-0 w-full h-32 bg-gradient-to-t from-black/80 via-black/40 to-transparent pointer-events-none" />
        
        {/* Title and Location Overlay */}
        <div className="absolute bottom-4 left-4 right-4 text-white z-20 pointer-events-none">
            <h2 className="text-2xl font-bold leading-tight drop-shadow-md mb-1">{listing.title}</h2>
            {location && (
                <div className="flex items-center gap-1 text-white/90 text-sm font-medium">
                    <MapPin className="w-4 h-4" />
                    {location}
                </div>
            )}
        </div>
      </div>

      {/* Details */}
      <div className="p-5 flex flex-col flex-1">
        <div className="flex justify-between items-end mb-2">
            <div>
                <div className="text-3xl font-bold text-slate-900">{formatPrice(listing.price)}</div>
            </div>
            <div className="flex items-center gap-1 text-slate-700 font-bold text-lg">
                <Star className="w-5 h-5 fill-yellow-400 text-yellow-400" />
                {formatRating(listing.rating)}
                {listing.reviewCount && listing.reviewCount > 0 && (
                  <span className="text-slate-400 font-normal text-sm">({listing.reviewCount})</span>
                )}
            </div>
        </div>

        <div className="flex flex-wrap gap-2 mt-2 mb-4">
            {listing.amenities.includes(4) && <span className="px-2 py-1 bg-slate-100 text-slate-600 text-xs rounded-md">Wifi</span>}
            {listing.amenities.includes(7) && <span className="px-2 py-1 bg-slate-100 text-slate-600 text-xs rounded-md">Pool</span>}
            {listing.bedrooms && <span className="px-2 py-1 bg-slate-100 text-slate-600 text-xs rounded-md">{listing.bedrooms} Bed</span>}
            {listing.bathrooms && <span className="px-2 py-1 bg-slate-100 text-slate-600 text-xs rounded-md">{listing.bathrooms} Bath</span>}
        </div>

        <div className="mt-auto flex items-center justify-center gap-6 pt-2">
             <button 
                onClick={() => handleVote(VOTE_VETO)}
                disabled={isAnimating}
                className="w-14 h-14 rounded-full bg-white border border-slate-200 shadow-lg flex items-center justify-center text-slate-400 hover:text-red-500 hover:bg-red-50 transition-colors disabled:opacity-50"
             >
                 <X className="w-6 h-6" />
             </button>

             <button 
                onClick={() => handleVote(VOTE_OK)}
                disabled={isAnimating}
                className="w-14 h-14 rounded-full bg-white border border-slate-200 shadow-lg flex items-center justify-center text-yellow-500 hover:bg-yellow-50 transition-colors disabled:opacity-50"
             >
                 <ThumbsUp className="w-6 h-6" />
             </button>

             <button 
                onClick={() => handleVote(VOTE_LOVE)}
                disabled={isAnimating}
                className="w-16 h-16 rounded-full bg-rose-500 shadow-xl shadow-rose-500/30 flex items-center justify-center text-white hover:bg-rose-600 transition-colors disabled:opacity-50"
             >
                 <Heart className="w-8 h-8 fill-current" />
             </button>
        </div>
      </div>
    </motion.div>
  );
}
