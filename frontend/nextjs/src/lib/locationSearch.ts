/**
 * Location search using Photon (Komoot) API
 * - No API key required
 * - Based on OpenStreetMap data
 * - Designed for autocomplete/typeahead use
 * - Free and battle-tested
 */

export interface LocationSuggestion {
  name: string;
  city?: string;
  state?: string;
  country?: string;
  displayName: string;
  lat: number;
  lon: number;
}

interface PhotonFeature {
  type: string;
  geometry: {
    coordinates: [number, number]; // [lon, lat]
    type: string;
  };
  properties: {
    name?: string;
    city?: string;
    state?: string;
    country?: string;
    county?: string;
    type?: string;
    osm_type?: string;
    osm_id?: number;
  };
}

interface PhotonResponse {
  type: string;
  features: PhotonFeature[];
}

/**
 * Search for location suggestions using the Photon API
 * @param query - The search query (e.g., "Paris", "New York")
 * @param limit - Maximum number of results (default: 5)
 * @returns Array of location suggestions
 */
export async function searchLocations(
  query: string,
  limit: number = 5
): Promise<LocationSuggestion[]> {
  // Don't search for very short queries
  if (!query || query.trim().length < 2) {
    return [];
  }

  try {
    const url = new URL('https://photon.komoot.io/api/');
    url.searchParams.set('q', query.trim());
    url.searchParams.set('limit', limit.toString());
    url.searchParams.set('lang', 'en');

    const response = await fetch(url.toString());

    if (!response.ok) {
      console.error('Photon API error:', response.status);
      return [];
    }

    const data: PhotonResponse = await response.json();

    return data.features.map((feature) => {
      const props = feature.properties;
      
      // Build a nice display name
      const parts = [
        props.name,
        props.city && props.city !== props.name ? props.city : null,
        props.state,
        props.country,
      ].filter(Boolean);
      
      const displayName = parts.join(', ');

      return {
        name: props.name || displayName,
        city: props.city,
        state: props.state,
        country: props.country,
        displayName,
        lat: feature.geometry.coordinates[1],
        lon: feature.geometry.coordinates[0],
      };
    });
  } catch (error) {
    console.error('Location search error:', error);
    return [];
  }
}

/**
 * Debounce helper for search input
 */
export function debounce<T extends (...args: Parameters<T>) => ReturnType<T>>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: ReturnType<typeof setTimeout> | null = null;

  return (...args: Parameters<T>) => {
    if (timeout) {
      clearTimeout(timeout);
    }
    timeout = setTimeout(() => func(...args), wait);
  };
}
