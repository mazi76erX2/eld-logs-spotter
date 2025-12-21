// hooks/use-trip.ts
"use client";

import { downloadBlob, tripApi, tripKeys } from "@/lib/api/client";
import type { TripCalculateRequest } from "@/lib/api/types";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

// Queries

export function useTrips(page = 1) {
  return useQuery({
    queryKey: tripKeys.list(page),
    queryFn: () => tripApi.list(page),
  });
}

export function useTrip(tripId: number | null) {
  return useQuery({
    queryKey: tripKeys.detail(tripId!),
    queryFn: () => tripApi.getResult(tripId!),
    enabled: !!tripId,
  });
}

export function useTripStatus(tripId: number | null, enabled = true) {
  return useQuery({
    queryKey: tripKeys.status(tripId!),
    queryFn: () => tripApi.getStatus(tripId!),
    enabled: !!tripId && enabled,
    refetchInterval: (query) => {
      const data = query.state.data;
      // Stop polling if completed or failed
      if (data?.status === "completed" && data?.is_map_ready) {
        return false;
      }
      if (data?.status === "failed") {
        return false;
      }
      return 2000; // Poll every 2 seconds
    },
  });
}

export function useTripSummary(tripId: number | null) {
  return useQuery({
    queryKey: tripKeys.summary(tripId!),
    queryFn: () => tripApi.getSummary(tripId!),
    enabled: !!tripId,
  });
}

export function useTripLogs(tripId: number | null) {
  return useQuery({
    queryKey: tripKeys.logs(tripId!),
    queryFn: () => tripApi.listLogs(tripId!),
    enabled: !!tripId,
  });
}

// Mutations

export function useCalculateTrip() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: TripCalculateRequest) => tripApi.calculate(data),
    onSuccess: () => {
      // Invalidate trips list to refetch
      queryClient.invalidateQueries({ queryKey: tripKeys.lists() });
    },
  });
}

export function useDeleteTrip() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (tripId: number) => tripApi.delete(tripId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: tripKeys.lists() });
    },
  });
}

export function useRetryMap() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (tripId: number) => tripApi.retryMap(tripId),
    onSuccess: (_, tripId) => {
      queryClient.invalidateQueries({ queryKey: tripKeys.status(tripId) });
      queryClient.invalidateQueries({ queryKey: tripKeys.detail(tripId) });
    },
  });
}

export function useDownloadLog() {
  return useMutation({
    mutationFn: async ({
      tripId,
      day,
      filename,
    }: {
      tripId: number;
      day: number;
      filename?: string;
    }) => {
      const blob = await tripApi.downloadLog(tripId, day);
      downloadBlob(blob, filename || `eld_log_trip_${tripId}_day_${day}.png`);
      return true;
    },
  });
}

export function useDownloadMap() {
  return useMutation({
    mutationFn: async ({
      tripId,
      filename,
    }: {
      tripId: number;
      filename?: string;
    }) => {
      const result = await tripApi.downloadMap(tripId);

      if (result instanceof Blob) {
        downloadBlob(result, filename || `route_map_trip_${tripId}.png`);
        return { success: true };
      } else {
        // Map is still generating
        return {
          success: false,
          message: result.message || "Map is still generating",
        };
      }
    },
  });
}

// Combined hook for backwards compatibility (if needed)
export function useTripActions() {
  const queryClient = useQueryClient();
  const calculateMutation = useCalculateTrip();
  const deleteMutation = useDeleteTrip();
  const retryMapMutation = useRetryMap();
  const downloadLogMutation = useDownloadLog();
  const downloadMapMutation = useDownloadMap();

  return {
    calculateTrip: calculateMutation.mutateAsync,
    isCalculating: calculateMutation.isPending,
    calculateError: calculateMutation.error,

    deleteTrip: deleteMutation.mutateAsync,
    isDeleting: deleteMutation.isPending,
    deleteError: deleteMutation.error,

    retryMap: retryMapMutation.mutateAsync,
    isRetryingMap: retryMapMutation.isPending,
    retryMapError: retryMapMutation.error,

    downloadLog: downloadLogMutation.mutateAsync,
    isDownloadingLog: downloadLogMutation.isPending,
    downloadLogError: downloadLogMutation.error,

    downloadMap: downloadMapMutation.mutateAsync,
    isDownloadingMap: downloadMapMutation.isPending,
    downloadMapError: downloadMapMutation.error,

    invalidateTrips: () =>
      queryClient.invalidateQueries({ queryKey: tripKeys.all }),
  };
}
