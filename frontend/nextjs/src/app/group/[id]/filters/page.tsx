"use client";

import { useState, useEffect, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAppStore } from '../../../../store/useAppStore';
import { getUserFilters, updateUserFilters, getGroupInfo } from '../../../../lib/api';
import { Minus, Plus, Check, AlertCircle, Loader2 } from 'lucide-react';
import { Amenity, RoomType } from '../../../../types';
import Slider from 'rc-slider';
import 'rc-slider/assets/index.css';

// Default fallback values
const DEFAULT_PRICE_MIN = 0;
const DEFAULT_PRICE_MAX = 1000;

export default function FiltersPage() {
  const { id } = useParams();
  const router = useRouter();
  const { currentUser, isHydrated, invalidateRecommendations } = useAppStore();

  // Price range bounds from group destinations
  const [priceRangeMin, setPriceRangeMin] = useState(DEFAULT_PRICE_MIN);
  const [priceRangeMax, setPriceRangeMax] = useState(DEFAULT_PRICE_MAX);

  const [priceMin, setPriceMin] = useState(DEFAULT_PRICE_MIN);
  const [priceMax, setPriceMax] = useState(DEFAULT_PRICE_MAX);
  const [priceMinInput, setPriceMinInput] = useState(String(DEFAULT_PRICE_MIN));
  const [priceMaxInput, setPriceMaxInput] = useState(String(DEFAULT_PRICE_MAX));
  const [minBedrooms, setMinBedrooms] = useState(0);
  const [minBeds, setMinBeds] = useState(0);
  const [minBathrooms, setMinBathrooms] = useState(0);
  const [roomType, setRoomType] = useState<RoomType | undefined>(undefined);
  const [selectedAmenities, setSelectedAmenities] = useState<Amenity[]>([]);

  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);

  const groupId = typeof id === 'string' ? parseInt(id, 10) : null;

  // Load price range from group and existing filters
  const loadFilters = useCallback(async () => {
    if (!currentUser || !groupId) return;

    setIsLoading(true);
    setError(null);

    try {
      // Fetch group info to get price range
      const groupInfo = await getGroupInfo(groupId);
      
      // Use group-level price range (calculated at group creation)
      const rangeMin = groupInfo.price_range_min ?? DEFAULT_PRICE_MIN;
      const rangeMax = groupInfo.price_range_max ?? DEFAULT_PRICE_MAX;
      
      setPriceRangeMin(rangeMin);
      setPriceRangeMax(rangeMax);

      // Fetch user's existing filters
      const filters = await getUserFilters(currentUser.id);

      // Use saved filter values if they exist, otherwise use the range bounds
      const savedMin = filters.min_price ?? rangeMin;
      const savedMax = filters.max_price ?? rangeMax;
      
      setPriceMin(savedMin);
      setPriceMax(savedMax);
      setPriceMinInput(String(savedMin));
      setPriceMaxInput(String(savedMax));
      setMinBedrooms(filters.min_bedrooms || 0);
      setMinBeds(filters.min_beds || 0);
      setMinBathrooms(filters.min_bathrooms || 0);

      if (filters.property_type) {
        if (filters.property_type === RoomType.ENTIRE_HOME) {
          setRoomType(RoomType.ENTIRE_HOME);
        } else if (filters.property_type === RoomType.PRIVATE_ROOM) {
          setRoomType(RoomType.PRIVATE_ROOM);
        }
      }

      setSelectedAmenities(filters.amenities || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load filters');
    } finally {
      setIsLoading(false);
    }
  }, [currentUser, groupId]);

  useEffect(() => {
    loadFilters();
  }, [loadFilters]);

  const toggleAmenity = (amenity: Amenity) => {
    if (selectedAmenities.includes(amenity)) {
      setSelectedAmenities(selectedAmenities.filter(a => a !== amenity));
    } else {
      setSelectedAmenities([...selectedAmenities, amenity]);
    }
  };

  const handleReset = () => {
    setPriceMin(priceRangeMin);
    setPriceMax(priceRangeMax);
    setPriceMinInput(String(priceRangeMin));
    setPriceMaxInput(String(priceRangeMax));
    setMinBedrooms(0);
    setMinBeds(0);
    setMinBathrooms(0);
    setRoomType(undefined);
    setSelectedAmenities([]);
  };

  const handleSave = async () => {
    if (!currentUser) return;

    setIsSaving(true);
    setError(null);
    setSaveSuccess(false);

    try {
      await updateUserFilters(currentUser.id, {
        min_price: priceMin,
        max_price: priceMax,
        min_bedrooms: minBedrooms || undefined,
        min_beds: minBeds || undefined,
        min_bathrooms: minBathrooms || undefined,
        property_type: roomType,
        amenities: selectedAmenities,
      });
      
      // Invalidate recommendations so they get re-fetched with new filters
      invalidateRecommendations();
      
      setSaveSuccess(true);
      setTimeout(() => {
        router.push(`/group/${groupId}`);
      }, 500);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save filters');
    } finally {
      setIsSaving(false);
    }
  };

  if (!isHydrated || isLoading) {
    return (
      <div className="flex h-full items-center justify-center bg-white">
        <Loader2 className="w-8 h-8 animate-spin text-rose-500" />
      </div>
    );
  }

  return (
    <div className="bg-white min-h-full">
      <header className="bg-white px-6 py-4 flex items-center justify-between sticky top-0 z-50 border-b border-slate-100 shadow-sm">
        <h1 className="font-bold text-slate-900 text-xl">My Preferences</h1>
        <button
          onClick={handleReset}
          className="text-rose-500 font-medium text-sm"
        >
          Reset
        </button>
      </header>

      {/* Onboarding message */}
      <div className="mx-6 mt-4 p-4 bg-blue-50 border border-blue-200 rounded-xl">
        <p className="text-blue-800 text-sm">
          <strong>Set your preferences</strong> to help us find the best Airbnbs for your group.
          After you save, we&apos;ll start searching for listings that match everyone&apos;s criteria.
        </p>
      </div>

      {error && (
        <div className="mx-6 mt-4 p-3 bg-red-50 border border-red-200 rounded-xl text-red-600 text-sm flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          {error}
        </div>
      )}

      <div className="p-6 flex flex-col gap-8">

        {/* Price Range */}
        <div>
          <div className="flex justify-between mb-4">
            <h3 className="font-bold text-slate-900">Price Range</h3>
            <span className="font-bold text-rose-500">CHF {priceMin} - {priceMax}</span>
          </div>

          {/* rc-slider Range */}
          <div className="px-2 mb-6">
            <Slider
              range
              min={priceRangeMin}
              max={priceRangeMax}
              allowCross={false}
              step={10}
              value={[priceMin, priceMax]}
              onChange={(value: number | number[]) => {
                if (Array.isArray(value)) {
                  setPriceMin(value[0]);
                  setPriceMax(value[1]);
                  setPriceMinInput(String(value[0]));
                  setPriceMaxInput(String(value[1]));
                }
              }}
              styles={{
                track: { backgroundColor: '#f43f5e', height: 6 },
                rail: { backgroundColor: '#e2e8f0', height: 6 },
                handle: {
                  backgroundColor: 'white',
                  borderColor: '#f43f5e',
                  borderWidth: 2,
                  height: 24,
                  width: 24,
                  marginTop: -9,
                  opacity: 1,
                  boxShadow: '0 1px 3px 0 rgb(0 0 0 / 0.1)',
                },
              }}
            />
          </div>

          <div className="px-2 flex gap-4">
            <div className="flex-1">
              <label className="text-xs text-slate-500 mb-1 block">Min Price</label>
              <input
                type="text"
                inputMode="numeric"
                pattern="[0-9]*"
                value={priceMinInput}
                onChange={(e) => {
                  const filtered = e.target.value.replace(/[^0-9]/g, '');
                  setPriceMinInput(filtered);
                  const val = parseInt(filtered);
                  if (!isNaN(val)) setPriceMin(val);
                }}
                onBlur={() => {
                  const val = parseInt(priceMinInput);
                  let finalMin = isNaN(val) || priceMinInput === '' ? priceRangeMin : Math.max(priceRangeMin, Math.min(priceRangeMax, val));
                  if (finalMin > priceMax) {
                    setPriceMax(finalMin);
                    setPriceMaxInput(String(finalMin));
                  }
                  setPriceMin(finalMin);
                  setPriceMinInput(String(finalMin));
                }}
                className="w-full p-2 border border-slate-200 rounded-lg text-slate-900 disabled:bg-slate-100 disabled:text-slate-400"
              />
            </div>
            <div className="flex-1">
              <label className="text-xs text-slate-500 mb-1 block">Max Price</label>
              <input
                type="text"
                inputMode="numeric"
                pattern="[0-9]*"
                value={priceMaxInput}
                onChange={(e) => {
                  const filtered = e.target.value.replace(/[^0-9]/g, '');
                  setPriceMaxInput(filtered);
                  const val = parseInt(filtered);
                  if (!isNaN(val)) setPriceMax(val);
                }}
                onBlur={() => {
                  const val = parseInt(priceMaxInput);
                  let finalMax = isNaN(val) || priceMaxInput === '' ? priceRangeMax : Math.max(priceRangeMin, Math.min(priceRangeMax, val));
                  if (finalMax < priceMin) {
                    setPriceMin(finalMax);
                    setPriceMinInput(String(finalMax));
                  }
                  setPriceMax(finalMax);
                  setPriceMaxInput(String(finalMax));
                }}
                className="w-full p-2 border border-slate-200 rounded-lg text-slate-900 disabled:bg-slate-100 disabled:text-slate-400"
              />
            </div>
          </div>
          <p className="mt-2 text-sm text-slate-400 px-2">Total price for stay</p>
        </div>

        {/* Room Type */}
        <div>
          <h3 className="font-bold text-slate-900 mb-4">Room Type</h3>
          <div className="flex gap-2">
            <button
              onClick={() => setRoomType(roomType === RoomType.ENTIRE_HOME ? undefined : RoomType.ENTIRE_HOME)}
              className={`flex-1 p-3 rounded-xl border text-sm font-medium transition-colors ${roomType === RoomType.ENTIRE_HOME ? 'border-rose-500 bg-rose-50 text-rose-600' : 'border-slate-200 bg-white text-slate-600'}`}
            >
              Entire Home
            </button>
            <button
              onClick={() => setRoomType(roomType === RoomType.PRIVATE_ROOM ? undefined : RoomType.PRIVATE_ROOM)}
              className={`flex-1 p-3 rounded-xl border text-sm font-medium transition-colors ${roomType === RoomType.PRIVATE_ROOM ? 'border-rose-500 bg-rose-50 text-rose-600' : 'border-slate-200 bg-white text-slate-600'}`}
            >
              Private Room
            </button>
          </div>
        </div>

        {/* Rooms and Beds */}
        <div>
          <h3 className="font-bold text-slate-900 mb-4">Rooms and Beds</h3>

          {/* Bedrooms */}
          <div className="flex items-center justify-between mb-4">
            <span className="text-slate-700">Bedrooms</span>
            <div className="flex items-center gap-3">
              <button
                onClick={() => setMinBedrooms(Math.max(0, minBedrooms - 1))}
                className="w-8 h-8 rounded-full border border-slate-300 flex items-center justify-center text-slate-500 hover:border-slate-800 hover:text-slate-800"
              >
                <Minus className="w-4 h-4" />
              </button>
              <span className="w-8 text-center text-slate-900">{minBedrooms || 'Any'}</span>
              <button
                onClick={() => setMinBedrooms(minBedrooms + 1)}
                className="w-8 h-8 rounded-full border border-slate-300 flex items-center justify-center text-slate-500 hover:border-slate-800 hover:text-slate-800"
              >
                <Plus className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Beds */}
          <div className="flex items-center justify-between mb-4">
            <span className="text-slate-700">Beds</span>
            <div className="flex items-center gap-3">
              <button
                onClick={() => setMinBeds(Math.max(0, minBeds - 1))}
                className="w-8 h-8 rounded-full border border-slate-300 flex items-center justify-center text-slate-500 hover:border-slate-800 hover:text-slate-800"
              >
                <Minus className="w-4 h-4" />
              </button>
              <span className="w-8 text-center text-slate-900">{minBeds || 'Any'}</span>
              <button
                onClick={() => setMinBeds(minBeds + 1)}
                className="w-8 h-8 rounded-full border border-slate-300 flex items-center justify-center text-slate-500 hover:border-slate-800 hover:text-slate-800"
              >
                <Plus className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Bathrooms */}
          <div className="flex items-center justify-between">
            <span className="text-slate-700">Bathrooms</span>
            <div className="flex items-center gap-3">
              <button
                onClick={() => setMinBathrooms(Math.max(0, minBathrooms - 1))}
                className="w-8 h-8 rounded-full border border-slate-300 flex items-center justify-center text-slate-500 hover:border-slate-800 hover:text-slate-800"
              >
                <Minus className="w-4 h-4" />
              </button>
              <span className="w-8 text-center text-slate-900">{minBathrooms || 'Any'}</span>
              <button
                onClick={() => setMinBathrooms(minBathrooms + 1)}
                className="w-8 h-8 rounded-full border border-slate-300 flex items-center justify-center text-slate-500 hover:border-slate-800 hover:text-slate-800"
              >
                <Plus className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>

        {/* Amenities */}
        <div>
          <h3 className="font-bold text-slate-900 mb-4">Amenities</h3>
          <div className="grid grid-cols-2 gap-3">
            {[
              { label: 'Wifi', value: Amenity.WIFI },
              { label: 'Kitchen', value: Amenity.KITCHEN },
              { label: 'Washer', value: Amenity.WASHER },
              { label: 'Workspace', value: Amenity.DEDICATED_WORKSPACE },
              { label: 'TV', value: Amenity.TV },
              { label: 'Pool', value: Amenity.POOL },
              { label: 'Hot Tub', value: Amenity.HOT_TUB },
              { label: 'Free Parking', value: Amenity.FREE_PARKING },
              { label: 'EV Charger', value: Amenity.EV_CHARGER },
              { label: 'Crib', value: Amenity.CRIB },
              { label: 'King Bed', value: Amenity.KING_BED },
              { label: 'Gym', value: Amenity.GYM },
              { label: 'BBQ Grill', value: Amenity.BBQ_GRILL },
              { label: 'Breakfast', value: Amenity.BREAKFAST },
              { label: 'Fireplace', value: Amenity.INDOOR_FIREPLACE },
              { label: 'Smoking Allowed', value: Amenity.SMOKING_ALLOWED },
              { label: 'Smoke Alarm', value: Amenity.SMOKE_ALARM },
              { label: 'CO Alarm', value: Amenity.CARBON_MONOXIDE_ALARM },
              { label: 'AC', value: Amenity.AC },
            ].map((item) => {
              const isSelected = selectedAmenities.includes(item.value);
              return (
                <button
                  key={item.label}
                  onClick={() => toggleAmenity(item.value)}
                  className={`p-4 rounded-xl border flex items-center justify-between transition-colors ${isSelected ? 'border-rose-500 bg-rose-50 text-rose-600' : 'border-slate-200 bg-white text-slate-600'}`}
                >
                  <span className="font-medium">{item.label}</span>
                  {isSelected && <Check className="w-4 h-4" />}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      <div className="fixed bottom-[calc(80px+env(safe-area-inset-bottom)+1rem)] left-1/2 -translate-x-1/2 z-40">
        <button
          onClick={handleSave}
          disabled={isSaving}
          className="bg-rose-500 text-white px-8 py-3 rounded-full font-bold shadow-lg flex items-center gap-2 hover:bg-rose-600 transition-colors disabled:opacity-50"
        >
          {isSaving ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              <span>Saving...</span>
            </>
          ) : saveSuccess ? (
            <>
              <Check className="w-5 h-5" />
              <span>Saved!</span>
            </>
          ) : (
            <>
              <Check className="w-5 h-5" />
              <span>Save Filters</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
}
