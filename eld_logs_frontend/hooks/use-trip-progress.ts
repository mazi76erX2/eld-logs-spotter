// hooks/use-trip-progress.ts
"use client";

import { tripKeys } from "@/lib/api/client";
import type {
  MapStatus,
  TripStatus,
  WebSocketProgressMessage,
} from "@/lib/api/types";
import {
  TripProgressPoller,
  TripProgressService,
} from "@/lib/websocket/trip-progress";
import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useRef, useState } from "react";

// TYPES
export interface TripProgressState {
  tripId: number | null;
  status: TripStatus | null;
  progress: number;
  mapStatus: MapStatus | null;
  mapProgress: number;
  overallProgress: number;
  message: string;
  stage: string;
  error: string | null;
  totalDistance: number | null;
  totalDrivingTime: number | null;
  numDays: number | null;
  mapUrl: string | null;
  isCompleted: boolean;
  isMapReady: boolean;
  isConnected: boolean;
}

interface UseTripProgressOptions {
  useWebSocket?: boolean;
  pollInterval?: number;
  onComplete?: (tripId: number) => void;
  onError?: (error: string) => void;
}

const initialState: TripProgressState = {
  tripId: null,
  status: null,
  progress: 0,
  mapStatus: null,
  mapProgress: 0,
  overallProgress: 0,
  message: "",
  stage: "",
  error: null,
  totalDistance: null,
  totalDrivingTime: null,
  numDays: null,
  mapUrl: null,
  isCompleted: false,
  isMapReady: false,
  isConnected: false,
};

// HOOK
export function useTripProgress(
  tripId: number | null,
  options: UseTripProgressOptions = {}
) {
  const {
    useWebSocket = true,
    pollInterval = 2000,
    onComplete,
    onError,
  } = options;

  const queryClient = useQueryClient();
  const [state, setState] = useState<TripProgressState>(initialState);

  const serviceRef = useRef<TripProgressService | TripProgressPoller | null>(
    null
  );
  const onCompleteRef = useRef(onComplete);
  const onErrorRef = useRef(onError);

  // Update refs when callbacks change
  useEffect(() => {
    onCompleteRef.current = onComplete;
    onErrorRef.current = onError;
  }, [onComplete, onError]);

  const handleProgress = useCallback((message: WebSocketProgressMessage) => {
    setState((prev) => {
      const newState: TripProgressState = {
        ...prev,
        tripId: message.trip_id,
        status: (message.status as TripStatus) || prev.status,
        progress: message.progress ?? prev.progress,
        mapStatus: (message.map_status as MapStatus) || prev.mapStatus,
        mapProgress: message.map_progress ?? prev.mapProgress,
        overallProgress: message.overall_progress ?? prev.overallProgress,
        message: message.message || prev.message,
        stage: message.stage || prev.stage,
        error: message.error || null,
        totalDistance: message.total_distance ?? prev.totalDistance,
        totalDrivingTime: message.total_driving_time ?? prev.totalDrivingTime,
        numDays: message.num_days ?? prev.numDays,
        mapUrl: message.map_url || prev.mapUrl,
        isCompleted: message.is_completed ?? prev.isCompleted,
        isMapReady: message.is_map_ready ?? prev.isMapReady,
        isConnected: prev.isConnected,
      };

      // Trigger completion callback
      if (newState.isCompleted && newState.isMapReady && !prev.isMapReady) {
        setTimeout(() => {
          onCompleteRef.current?.(message.trip_id);
        }, 0);
      }

      // Trigger error callback
      if (message.error && !prev.error) {
        setTimeout(() => {
          onErrorRef.current?.(message.error!);
        }, 0);
      }

      return newState;
    });
  }, []);

  const handleError = useCallback((error: Error) => {
    console.error("[TripProgress] Error:", error);
    setState((prev) => ({
      ...prev,
      error: error.message,
    }));
    onErrorRef.current?.(error.message);
  }, []);

  const handleConnectionChange = useCallback((connected: boolean) => {
    setState((prev) => ({
      ...prev,
      isConnected: connected,
    }));
  }, []);

  // Connect/disconnect based on tripId
  useEffect(() => {
    if (!tripId) {
      setState(initialState);
      return;
    }

    // Create appropriate service
    if (useWebSocket && typeof WebSocket !== "undefined") {
      serviceRef.current = new TripProgressService(tripId, {
        onProgress: handleProgress,
        onError: handleError,
        onConnectionChange: handleConnectionChange,
      });
      serviceRef.current.connect();
    } else {
      serviceRef.current = new TripProgressPoller(
        tripId,
        {
          onProgress: handleProgress,
          onError: handleError,
          onConnectionChange: handleConnectionChange,
        },
        pollInterval
      );
      (serviceRef.current as TripProgressPoller).start();
    }

    // Cleanup
    return () => {
      if (serviceRef.current) {
        if (serviceRef.current instanceof TripProgressService) {
          serviceRef.current.disconnect();
        } else {
          serviceRef.current.stop();
        }
        serviceRef.current = null;
      }
    };
  }, [
    tripId,
    useWebSocket,
    pollInterval,
    handleProgress,
    handleError,
    handleConnectionChange,
  ]);

  // Invalidate queries when trip is completed
  useEffect(() => {
    if (state.isCompleted && state.isMapReady && tripId) {
      queryClient.invalidateQueries({ queryKey: tripKeys.detail(tripId) });
      queryClient.invalidateQueries({ queryKey: tripKeys.logs(tripId) });
      queryClient.invalidateQueries({ queryKey: tripKeys.lists() });
    }
  }, [state.isCompleted, state.isMapReady, tripId, queryClient]);

  // Manual refresh
  const refresh = useCallback(() => {
    if (serviceRef.current instanceof TripProgressService) {
      serviceRef.current.requestStatus();
    }
  }, []);

  return {
    ...state,
    refresh,
  };
}
