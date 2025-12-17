"use client";

import { useState, useEffect } from 'react';
import { motion, useMotionValue, useTransform, useAnimate, AnimatePresence } from 'framer-motion';
import { Listing, VoteValue, VOTE_VETO, VOTE_LOVE, OtherVote } from '../types';
import { PriceDisplayMode } from '../store/useAppStore';
import { ThumbsDown, ThumbsUp, Star, ChevronLeft, ChevronRight, MapPin, ExternalLink, Ban, X } from 'lucide-react';

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
  onVote: (vote: VoteValue, reason?: string) => void;
  onDragProgress?: (progress: number) => void; // 0 = centered, 1 = at vote threshold
  onVoteStart?: () => void; // Called immediately when vote animation starts
  otherVotes?: OtherVote[];
  location?: string;
  isBackground?: boolean;
  numberOfNights?: number;
  numberOfAdults?: number;
  priceMode?: PriceDisplayMode;
  onPriceModeChange?: (mode: PriceDisplayMode) => void;
  onKeyboardNavigation?: (action: 'prevImage' | 'nextImage' | 'dislike' | 'veto' | 'like' | 'togglePrice') => void;
}

export function VotingCard({ listing, onVote, onDragProgress, onVoteStart, otherVotes = [], location, isBackground = false, numberOfNights = 1, numberOfAdults = 1, priceMode = 'total', onPriceModeChange, onKeyboardNavigation }: VotingCardProps) {
  const [imageIndex, setImageIndex] = useState(0);
  const [scope, animate] = useAnimate();
  const [isAnimating, setIsAnimating] = useState(false);
  const [showVetoModal, setShowVetoModal] = useState(false);
  const [vetoReason, setVetoReason] = useState('');
  
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

  // Handle veto button click - show modal for reason
  const handleVetoClick = () => {
    if (isAnimating) return;
    setShowVetoModal(true);
  };

  // Submit veto with reason
  const handleVetoSubmit = async () => {
    if (isAnimating || !vetoReason.trim()) return;
    setShowVetoModal(false);
    setIsAnimating(true);
    
    // Notify parent immediately so background card can start animating
    onVoteStart?.();
    
    await animate(scope.current, {
      scale: 0.8,
      opacity: 0,
    }, {
      duration: 0.3,
      ease: "easeOut",
    });
    
    onVote(VOTE_VETO, vetoReason.trim());
    setVetoReason('');
  };

  // Cancel veto
  const handleVetoCancel = () => {
    setShowVetoModal(false);
    setVetoReason('');
  };

  // Handle dislike (veto without reason)
  const handleDislike = async () => {
    if (isAnimating) return;
    
    setIsAnimating(true);
    
    // Notify parent immediately so background card can start animating
    onVoteStart?.();
    
    const exitX = -1 * window.innerWidth; // Dislike goes left
    const exitRotation = -20;
    
    await animate(scope.current, {
      x: exitX,
      rotate: exitRotation,
      opacity: 0,
    }, {
      duration: 0.3,
      ease: "easeOut",
    });
    
    // Submit veto without reason (dislike)
    onVote(VOTE_VETO);
  };

  // Animate card off screen and then call onVote
  const handleVote = async (vote: VoteValue) => {
    if (isAnimating) return;
    
    // For veto button (with reason), show modal instead
    if (vote === VOTE_VETO) {
      handleVetoClick();
      return;
    }
    
    setIsAnimating(true);
    
    // Notify parent immediately so background card can start animating
    onVoteStart?.();
    
    const direction = 1; // Like goes right
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

  // Derived likes/loves (vote values: 2=love, 3=super_love)
  const likers = otherVotes.filter(v => v.vote >= VOTE_LOVE);

  const nextImage = (e?: React.MouseEvent) => {
    e?.stopPropagation();
    if (imageIndex < listing.images.length - 1) setImageIndex(prev => prev + 1);
  };

  const prevImage = (e?: React.MouseEvent) => {
    e?.stopPropagation();
    if (imageIndex > 0) setImageIndex(prev => prev - 1);
  };

  // Keyboard-only cycling (wraps around)
  const cycleNextImage = () => {
    if (listing.images.length <= 1) return;
    setImageIndex((prev) => (prev + 1) % listing.images.length);
  };

  const cyclePrevImage = () => {
    if (listing.images.length <= 1) return;
    setImageIndex((prev) => (prev - 1 + listing.images.length) % listing.images.length);
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

  // Calculate prices based on mode
  const getPriceDisplay = () => {
    const totalPrice = listing.price;
    const pricePerNight = totalPrice / Math.max(1, numberOfNights);
    const pricePerPerson = pricePerNight / Math.max(1, numberOfAdults);

    switch (priceMode) {
      case 'total':
        return {
          price: formatPrice(totalPrice),
          label: 'total',
        };
      case 'perNight':
        return {
          price: formatPrice(pricePerNight),
          label: '/night',
        };
      case 'perPerson':
        return {
          price: formatPrice(pricePerPerson),
          label: '/night/person',
        };
    }
  };

  // Toggle price display mode
  const togglePriceMode = () => {
    const nextMode: PriceDisplayMode = 
      priceMode === 'total' ? 'perNight' : 
      priceMode === 'perNight' ? 'perPerson' : 
      'total';
    onPriceModeChange?.(nextMode);
  };

  // Handle keyboard shortcuts
  useEffect(() => {
    if (isBackground || showVetoModal) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't handle shortcuts when typing in inputs/textareas
      const target = e.target as HTMLElement;
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable) {
        return;
      }

      // Ignore key repeat to avoid accidental multi-votes
      if (e.repeat) return;

      switch (e.key) {
        case 'ArrowLeft':
          e.preventDefault();
          handleDislike();
          onKeyboardNavigation?.('dislike');
          break;
        case 'ArrowRight':
          e.preventDefault();
          handleVote(VOTE_LOVE);
          onKeyboardNavigation?.('like');
          break;
        case 'ArrowDown':
          e.preventDefault();
          handleVetoClick();
          onKeyboardNavigation?.('veto');
          break;
        case ' ':
          // Space
          e.preventDefault(); // prevent page scroll
          if (e.shiftKey) {
            cyclePrevImage();
            onKeyboardNavigation?.('prevImage');
          } else {
            cycleNextImage();
            onKeyboardNavigation?.('nextImage');
          }
          break;
        case 'a':
        case 'A':
          e.preventDefault();
          handleDislike();
          onKeyboardNavigation?.('dislike');
          break;
        case 'd':
        case 'D':
          e.preventDefault();
          handleVote(VOTE_LOVE);
          onKeyboardNavigation?.('like');
          break;
        case 'v':
        case 'V':
          e.preventDefault();
          handleVetoClick();
          onKeyboardNavigation?.('veto');
          break;
        case 'p':
        case 'P':
          e.preventDefault();
          togglePriceMode();
          onKeyboardNavigation?.('togglePrice');
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isBackground, showVetoModal, listing.images.length, onKeyboardNavigation, priceMode, onPriceModeChange]);

  // Handle keyboard shortcuts in veto modal
  useEffect(() => {
    if (!showVetoModal) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.repeat) return;
      // Avoid interfering with IME composition
      if ((e as unknown as { isComposing?: boolean }).isComposing) return;

      switch (e.key) {
        case 'Escape':
          e.preventDefault();
          handleVetoCancel();
          break;
        case 'Enter':
          // In textarea: Enter submits, Shift+Enter inserts newline
          if (e.shiftKey) return;
          e.preventDefault();
          if (vetoReason.trim()) {
            handleVetoSubmit();
          }
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [showVetoModal, vetoReason]);

  const priceDisplay = getPriceDisplay();

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
                    <span className="text-3xl font-bold text-slate-900">{priceDisplay.price}</span>
                    <span className="text-sm text-slate-500 font-medium ml-1.5">{priceDisplay.label}</span>
                </div>
                <div className="flex items-center gap-1 text-slate-700 font-bold text-lg">
                    <Star className="w-5 h-5 fill-yellow-400 text-yellow-400" />
                    {formatRating(listing.rating)}
                    {listing.reviewCount != null && listing.reviewCount > 0 && (
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
            
            <div className="mt-auto flex items-center justify-center gap-4 pt-2">
                 <div className="w-14 h-14 rounded-full bg-white border-2 border-orange-200 shadow-lg flex items-center justify-center text-orange-400">
                     <ThumbsDown className="w-6 h-6" />
                 </div>
                 <div className="h-14 px-5 rounded-full bg-red-400 shadow-lg flex items-center justify-center gap-2 text-white font-bold text-sm uppercase tracking-wider">
                     <Ban className="w-5 h-5" />
                     VETO
                 </div>
                 <div className="w-14 h-14 rounded-full bg-white border-2 border-emerald-200 shadow-lg flex items-center justify-center text-emerald-400">
                     <ThumbsUp className="w-6 h-6" />
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
        if (offset.x > 100) handleVote(VOTE_LOVE); // Swipe right = like
        else if (offset.x < -100) handleDislike(); // Swipe left = dislike (veto)
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
          <div className="border-4 border-emerald-500 text-emerald-500 font-bold text-4xl px-4 py-2 rounded-lg bg-white/20 backdrop-blur-sm uppercase tracking-wider">
              LIKE
          </div>
      </motion.div>
      <motion.div style={{ opacity: nopeOpacity }} className="absolute top-8 left-8 z-30 pointer-events-none transform -rotate-12">
          <div className="border-4 border-orange-500 text-orange-500 font-bold text-4xl px-4 py-2 rounded-lg bg-white/20 backdrop-blur-sm uppercase tracking-wider">
              DISLIKE
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
            <div 
              onClick={togglePriceMode}
              className="cursor-pointer group"
            >
                <span className="text-3xl font-bold text-slate-900">{priceDisplay.price}</span>
                <span className="text-sm text-slate-500 font-medium ml-1.5">{priceDisplay.label}</span>
            </div>
            <div className="flex items-center gap-1 text-slate-700 font-bold text-lg">
                <Star className="w-5 h-5 fill-yellow-400 text-yellow-400" />
                {formatRating(listing.rating)}
                {listing.reviewCount != null && listing.reviewCount > 0 && (
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

        <div className="mt-auto flex items-center justify-center gap-4 pt-2">
             {/* Dislike button (left) - backend id 0 (veto without reason) */}
             <button 
                onClick={handleDislike}
                disabled={isAnimating || showVetoModal}
                className="w-14 h-14 rounded-full bg-white border-2 border-orange-200 shadow-lg flex items-center justify-center text-orange-500 hover:bg-orange-50 hover:border-orange-300 hover:scale-105 transition-all disabled:opacity-50"
             >
                 <ThumbsDown className="w-6 h-6" />
             </button>

             {/* Veto button (middle) - backend id 0 */}
             <button 
                onClick={handleVetoClick}
                disabled={isAnimating || showVetoModal}
                className="h-14 px-5 rounded-full bg-red-500 shadow-lg shadow-red-500/25 flex items-center justify-center gap-2 text-white font-bold text-sm uppercase tracking-wider hover:bg-red-600 hover:scale-105 transition-all disabled:opacity-50"
             >
                 <Ban className="w-5 h-5" />
                 VETO
             </button>

             {/* Like button (right) - backend id 2 */}
             <button 
                onClick={() => handleVote(VOTE_LOVE)}
                disabled={isAnimating || showVetoModal}
                className="w-14 h-14 rounded-full bg-white border-2 border-emerald-200 shadow-lg flex items-center justify-center text-emerald-500 hover:bg-emerald-50 hover:border-emerald-300 hover:scale-105 transition-all disabled:opacity-50"
             >
                 <ThumbsUp className="w-6 h-6" />
             </button>
        </div>
      </div>

      {/* Veto Reason Modal */}
      <AnimatePresence>
        {showVetoModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm rounded-3xl"
            onClick={handleVetoCancel}
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-white rounded-2xl p-6 mx-4 w-full max-w-sm shadow-2xl"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2 text-red-500">
                  <Ban className="w-6 h-6" />
                  <h3 className="text-lg font-bold">Veto this listing</h3>
                </div>
                <button
                  onClick={handleVetoCancel}
                  className="p-1 rounded-full hover:bg-slate-100 transition-colors"
                >
                  <X className="w-5 h-5 text-slate-400" />
                </button>
              </div>
              
              <p className="text-slate-600 text-sm mb-4">
                This listing won&apos;t be shown to anyone else in your group. Please provide a reason:
              </p>
              
              <textarea
                value={vetoReason}
                onChange={(e) => setVetoReason(e.target.value)}
                placeholder="Type a reason..."
                className="w-full h-24 px-4 py-3 border border-slate-200 rounded-xl resize-none focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-transparent text-slate-700 placeholder:text-slate-400"
                autoFocus
              />
              
              <div className="flex gap-3 mt-4">
                <button
                  onClick={handleVetoCancel}
                  className="flex-1 py-3 rounded-xl border border-slate-200 text-slate-600 font-medium hover:bg-slate-50 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleVetoSubmit}
                  disabled={!vetoReason.trim()}
                  className="flex-1 py-3 rounded-xl bg-red-500 text-white font-bold hover:bg-red-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Confirm Veto
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
