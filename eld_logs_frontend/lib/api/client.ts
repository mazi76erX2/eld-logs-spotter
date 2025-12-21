import {
  ApiException,
  type ApiError,
  type LogsListResponse,
  type PaginatedResponse,
  type Trip,
  type TripCalculateRequest,
  type TripCalculateResponse,
  type TripStatusResponse,
  type TripSummary,
} from "./types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

interface FetchOptions extends RequestInit {
  params?: Record<string, string | number | boolean | undefined>;
}

async function apiFetch<T>(
  endpoint: string,
  options: FetchOptions = {}
): Promise<T> {
  const { params, ...fetchOptions } = options;

  // Build URL with query params
  let url = `${API_BASE_URL}${endpoint}`;
  if (params) {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) {
        searchParams.append(key, String(value));
      }
    });
    const queryString = searchParams.toString();
    if (queryString) {
      url += `?${queryString}`;
    }
  }

  // Default headers
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...fetchOptions.headers,
  };

  const response = await fetch(url, {
    ...fetchOptions,
    headers,
  });

  // Handle non-JSON responses (like file downloads)
  const contentType = response.headers.get("content-type");
  if (
    contentType?.includes("image/") ||
    contentType?.includes("application/octet-stream")
  ) {
    if (!response.ok) {
      throw new ApiException(response.status, {
        error: true,
        status_code: response.status,
        message: "Failed to download file",
      });
    }
    return response.blob() as unknown as T;
  }

  // Parse JSON response
  let data: T | ApiError;
  try {
    data = await response.json();
  } catch {
    throw new ApiException(response.status, {
      error: true,
      status_code: response.status,
      message: "Invalid response from server",
    });
  }

  // Handle error responses
  if (!response.ok) {
    throw new ApiException(response.status, data as ApiError);
  }

  return data as T;
}

// TRIP API
export const tripApi = {
  /**
   * List all trips with pagination
   */
  list: async (page = 1): Promise<PaginatedResponse<Trip>> => {
    return apiFetch<PaginatedResponse<Trip>>("/trips/", {
      params: { page },
    });
  },

  /**
   * Get a single trip by ID
   */
  get: async (tripId: number): Promise<Trip> => {
    return apiFetch<Trip>(`/trips/${tripId}/`);
  },

  /**
   * Calculate a new trip route
   */
  calculate: async (
    data: TripCalculateRequest
  ): Promise<TripCalculateResponse> => {
    return apiFetch<TripCalculateResponse>("/trips/calculate/", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  /**
   * Get trip calculation result
   */
  getResult: async (tripId: number): Promise<Trip> => {
    return apiFetch<Trip>(`/trips/${tripId}/result/`);
  },

  /**
   * Get trip status (for polling)
   */
  getStatus: async (tripId: number): Promise<TripStatusResponse> => {
    return apiFetch<TripStatusResponse>(`/trips/${tripId}/status/`);
  },

  /**
   * Get trip summary
   */
  getSummary: async (tripId: number): Promise<TripSummary> => {
    return apiFetch<TripSummary>(`/trips/${tripId}/summary/`);
  },

  /**
   * List daily logs for a trip
   */
  listLogs: async (tripId: number): Promise<LogsListResponse> => {
    return apiFetch<LogsListResponse>(`/trips/${tripId}/logs/`);
  },

  /**
   * Download daily log image
   */
  downloadLog: async (tripId: number, day: number): Promise<Blob> => {
    return apiFetch<Blob>(`/trips/${tripId}/download-log/`, {
      params: { day },
    });
  },

  /**
   * Download route map image
   */
  downloadMap: async (
    tripId: number
  ): Promise<
    Blob | { status: string; progress?: number; message?: string }
  > => {
    const response = await fetch(
      `${API_BASE_URL}/trips/${tripId}/download-map/`
    );

    // Check if map is still generating (202 response)
    if (response.status === 202) {
      return response.json();
    }

    if (!response.ok) {
      const error = await response.json();
      throw new ApiException(response.status, error);
    }

    return response.blob();
  },

  /**
   * Retry failed map generation
   */
  retryMap: async (
    tripId: number
  ): Promise<{ id: number; message: string; map_task_id: string }> => {
    return apiFetch(`/trips/${tripId}/retry-map/`, {
      method: "POST",
    });
  },

  /**
   * Delete a trip
   */
  delete: async (tripId: number): Promise<void> => {
    await apiFetch(`/trips/${tripId}/`, {
      method: "DELETE",
    });
  },
};

// UTILITY FUNCTIONS
/**
 * Download a blob as a file
 */
export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

/**
 * Format distance for display
 */
export function formatDistance(miles: number | null | undefined): string {
  if (miles === null || miles === undefined) return "--";
  return `${miles.toLocaleString(undefined, { maximumFractionDigits: 1 })} mi`;
}

/**
 * Format duration for display
 */
export function formatDuration(hours: number | null | undefined): string {
  if (hours === null || hours === undefined) return "--";
  const h = Math.floor(hours);
  const m = Math.round((hours - h) * 60);
  if (h === 0) return `${m}m`;
  if (m === 0) return `${h}h`;
  return `${h}h ${m}m`;
}

/**
 * Format trip duration in days from a Trip object or hours
 */
export function formatTripDays(
  tripOrHours: Trip | number | null | undefined
): string {
  if (tripOrHours === null || tripOrHours === undefined) return "--";

  let hours: number | null | undefined;

  if (typeof tripOrHours === "number") {
    hours = tripOrHours;
  } else {
    hours = tripOrHours.total_trip_time;
  }

  if (hours === null || hours === undefined) return "--";

  const days = Math.ceil(hours / 24);
  return `${days} day${days !== 1 ? "s" : ""}`;
}

// Query Keys for React Query
export const tripKeys = {
  all: ["trips"] as const,
  lists: () => [...tripKeys.all, "list"] as const,
  list: (page: number) => [...tripKeys.lists(), { page }] as const,
  details: () => [...tripKeys.all, "detail"] as const,
  detail: (id: number) => [...tripKeys.details(), id] as const,
  status: (id: number) => [...tripKeys.all, "status", id] as const,
  summary: (id: number) => [...tripKeys.all, "summary", id] as const,
  logs: (id: number) => [...tripKeys.all, "logs", id] as const,
};
