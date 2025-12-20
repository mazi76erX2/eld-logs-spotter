export interface TripProgress {
  trip_id: number;
  stage: string;
  status: string;
  progress: number;
  message: string;
  map_progress?: number;
  map_status?: string;
  map_url?: string;
  total_distance?: number;
  total_driving_time?: number;
  error?: string;
}

export type ProgressCallback = (progress: TripProgress) => void;
export type ErrorCallback = (error: Error) => void;

export class TripProgressService {
  private socket: WebSocket | null = null;
  private tripId: number;
  private onProgress: ProgressCallback;
  private onError: ErrorCallback;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;

  constructor(
    tripId: number,
    onProgress: ProgressCallback,
    onError: ErrorCallback
  ) {
    this.tripId = tripId;
    this.onProgress = onProgress;
    this.onError = onError;
  }

  connect(): void {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws/trips/${this.tripId}/progress/`;

    try {
      this.socket = new WebSocket(wsUrl);

      this.socket.onopen = () => {
        console.log(`WebSocket connected for trip ${this.tripId}`);
        this.reconnectAttempts = 0;
      };

      this.socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          if (data.type === "progress" || data.type === "status") {
            this.onProgress(data as TripProgress);
          } else if (data.type === "error") {
            this.onError(new Error(data.message));
          }
        } catch (e) {
          console.error("Failed to parse WebSocket message:", e);
        }
      };

      this.socket.onclose = (event) => {
        console.log(`WebSocket closed for trip ${this.tripId}:`, event.code);

        if (
          !event.wasClean &&
          this.reconnectAttempts < this.maxReconnectAttempts
        ) {
          this.reconnectAttempts++;
          const delay =
            this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
          console.log(
            `Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`
          );
          setTimeout(() => this.connect(), delay);
        }
      };

      this.socket.onerror = (error) => {
        console.error("WebSocket error:", error);
        this.onError(new Error("WebSocket connection error"));
      };
    } catch (e) {
      this.onError(e as Error);
    }
  }

  disconnect(): void {
    if (this.socket) {
      this.socket.close(1000, "Client disconnecting");
      this.socket = null;
    }
  }

  // Request current status (useful after reconnection)
  requestStatus(): void {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify({ type: "get_status" }));
    }
  }

  // Ping to keep connection alive
  ping(): void {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify({ type: "ping" }));
    }
  }
}

// Polling fallback for browsers without WebSocket support
export class TripProgressPoller {
  private tripId: number;
  private onProgress: ProgressCallback;
  private onError: ErrorCallback;
  private intervalId: number | null = null;
  private pollInterval: number;

  constructor(
    tripId: number,
    onProgress: ProgressCallback,
    onError: ErrorCallback,
    pollInterval = 2000
  ) {
    this.tripId = tripId;
    this.onProgress = onProgress;
    this.onError = onError;
    this.pollInterval = pollInterval;
  }

  start(): void {
    this.poll(); // Initial poll
    this.intervalId = window.setInterval(() => this.poll(), this.pollInterval);
  }

  stop(): void {
    if (this.intervalId !== null) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }
  }

  private async poll(): Promise<void> {
    try {
      const response = await fetch(`/api/trips/${this.tripId}/status/`);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();

      this.onProgress({
        trip_id: this.tripId,
        stage: data.status === "completed" ? "completed" : "processing",
        status: data.status,
        progress: data.overall_progress,
        message: "",
        map_status: data.map_status,
        map_progress: data.map_progress,
        map_url: data.map_url,
        total_distance: data.total_distance,
        total_driving_time: data.total_driving_time,
        error: data.error_message,
      });

      // Stop polling if completed or failed
      if (data.status === "completed" && data.map_status === "completed") {
        this.stop();
      } else if (data.status === "failed") {
        this.stop();
      }
    } catch (e) {
      this.onError(e as Error);
    }
  }
}

// React hook example
// frontend/src/hooks/useTripProgress.ts

import { useCallback, useEffect, useState } from "react";
import {
  TripProgress,
  TripProgressPoller,
  TripProgressService,
} from "../services/tripProgressService";

interface UseTripProgressOptions {
  useWebSocket?: boolean;
  pollInterval?: number;
}

interface UseTripProgressResult {
  progress: TripProgress | null;
  error: Error | null;
  isConnected: boolean;
}

export function useTripProgress(
  tripId: number | null,
  options: UseTripProgressOptions = {}
): UseTripProgressResult {
  const { useWebSocket = true, pollInterval = 2000 } = options;

  const [progress, setProgress] = useState<TripProgress | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [isConnected, setIsConnected] = useState(false);

  const handleProgress = useCallback((data: TripProgress) => {
    setProgress(data);
    setError(null);
  }, []);

  const handleError = useCallback((err: Error) => {
    setError(err);
  }, []);

  useEffect(() => {
    if (!tripId) return;

    let service: TripProgressService | TripProgressPoller;

    if (useWebSocket && "WebSocket" in window) {
      service = new TripProgressService(tripId, handleProgress, handleError);
      (service as TripProgressService).connect();
      setIsConnected(true);
    } else {
      service = new TripProgressPoller(
        tripId,
        handleProgress,
        handleError,
        pollInterval
      );
      (service as TripProgressPoller).start();
      setIsConnected(true);
    }

    return () => {
      if (service instanceof TripProgressService) {
        service.disconnect();
      } else {
        service.stop();
      }
      setIsConnected(false);
    };
  }, [tripId, useWebSocket, pollInterval, handleProgress, handleError]);

  return { progress, error, isConnected };
}
