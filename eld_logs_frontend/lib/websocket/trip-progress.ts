import type { WebSocketProgressMessage } from "@/lib/api/types";

// TYPES
export type ProgressCallback = (message: WebSocketProgressMessage) => void;
export type ErrorCallback = (error: Error) => void;
export type ConnectionCallback = (connected: boolean) => void;

interface TripProgressServiceOptions {
  onProgress: ProgressCallback;
  onError?: ErrorCallback;
  onConnectionChange?: ConnectionCallback;
  maxReconnectAttempts?: number;
  reconnectDelay?: number;
}

// WEBSOCKET SERVICE
export class TripProgressService {
  private socket: WebSocket | null = null;
  private tripId: number;
  private options: Required<TripProgressServiceOptions>;
  private reconnectAttempts = 0;
  private reconnectTimeout: NodeJS.Timeout | null = null;
  private pingInterval: NodeJS.Timeout | null = null;
  private isManualClose = false;

  constructor(tripId: number, options: TripProgressServiceOptions) {
    this.tripId = tripId;
    this.options = {
      onProgress: options.onProgress,
      onError: options.onError || (() => {}),
      onConnectionChange: options.onConnectionChange || (() => {}),
      maxReconnectAttempts: options.maxReconnectAttempts ?? 5,
      reconnectDelay: options.reconnectDelay ?? 1000,
    };
  }

  /**
   * Connect to WebSocket
   */
  connect(): void {
    if (this.socket?.readyState === WebSocket.OPEN) {
      return;
    }

    this.isManualClose = false;
    const wsBaseUrl =
      process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/ws";
    const wsUrl = `${wsBaseUrl}/trips/${this.tripId}/progress/`;

    try {
      this.socket = new WebSocket(wsUrl);

      this.socket.onopen = () => {
        console.log(`[WS] Connected to trip ${this.tripId}`);
        this.reconnectAttempts = 0;
        this.options.onConnectionChange(true);
        this.startPingInterval();
      };

      this.socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as WebSocketProgressMessage;

          if (data.type === "pong") {
            return; // Ignore pong responses
          }

          this.options.onProgress(data);
        } catch (error) {
          console.error("[WS] Failed to parse message:", error);
        }
      };

      this.socket.onclose = (event) => {
        console.log(`[WS] Disconnected from trip ${this.tripId}:`, event.code);
        this.options.onConnectionChange(false);
        this.stopPingInterval();

        // Attempt reconnection if not manually closed
        if (!this.isManualClose && !event.wasClean) {
          this.attemptReconnect();
        }
      };

      this.socket.onerror = (error) => {
        console.error("[WS] Error:", error);
        this.options.onError(new Error("WebSocket connection error"));
      };
    } catch (error) {
      this.options.onError(error as Error);
    }
  }

  /**
   * Disconnect from WebSocket
   */
  disconnect(): void {
    this.isManualClose = true;
    this.stopPingInterval();
    this.clearReconnectTimeout();

    if (this.socket) {
      this.socket.close(1000, "Client disconnecting");
      this.socket = null;
    }
  }

  /**
   * Request current status
   */
  requestStatus(): void {
    this.send({ type: "get_status" });
  }

  /**
   * Send ping to keep connection alive
   */
  ping(): void {
    this.send({ type: "ping" });
  }

  /**
   * Check if connected
   */
  isConnected(): boolean {
    return this.socket?.readyState === WebSocket.OPEN;
  }

  // PRIVATE METHODS
  private send(data: object): void {
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(data));
    }
  }

  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.options.maxReconnectAttempts) {
      console.log("[WS] Max reconnection attempts reached");
      this.options.onError(new Error("Max reconnection attempts reached"));
      return;
    }

    this.reconnectAttempts++;
    const delay =
      this.options.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);

    console.log(
      `[WS] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`
    );

    this.reconnectTimeout = setTimeout(() => {
      this.connect();
    }, delay);
  }

  private clearReconnectTimeout(): void {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
  }

  private startPingInterval(): void {
    this.stopPingInterval();
    // Ping every 30 seconds to keep connection alive
    this.pingInterval = setInterval(() => {
      this.ping();
    }, 30000);
  }

  private stopPingInterval(): void {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }
}

// POLLING FALLBACK SERVICE
export class TripProgressPoller {
  private tripId: number;
  private options: Required<TripProgressServiceOptions>;
  private intervalId: NodeJS.Timeout | null = null;
  private pollInterval: number;

  constructor(
    tripId: number,
    options: TripProgressServiceOptions,
    pollInterval = 2000
  ) {
    this.tripId = tripId;
    this.options = {
      onProgress: options.onProgress,
      onError: options.onError || (() => {}),
      onConnectionChange: options.onConnectionChange || (() => {}),
      maxReconnectAttempts: 0,
      reconnectDelay: 0,
    };
    this.pollInterval = pollInterval;
  }

  /**
   * Start polling
   */
  start(): void {
    this.options.onConnectionChange(true);
    this.poll(); // Initial poll
    this.intervalId = setInterval(() => this.poll(), this.pollInterval);
  }

  /**
   * Stop polling
   */
  stop(): void {
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }
    this.options.onConnectionChange(false);
  }

  /**
   * Check if polling is active
   */
  isActive(): boolean {
    return this.intervalId !== null;
  }

  private async poll(): Promise<void> {
    try {
      const response = await fetch(
        `${
          process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api"
        }/trips/${this.tripId}/status/`
      );

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();

      const progressMessage: WebSocketProgressMessage = {
        type: "progress",
        trip_id: this.tripId,
        status: data.status,
        progress: data.overall_progress,
        map_status: data.map_status,
        map_progress: data.map_progress,
        map_url: data.map_url,
        total_distance: data.total_distance,
        total_driving_time: data.total_driving_time,
        is_completed: data.is_completed,
        is_map_ready: data.is_map_ready,
        error: data.error_message,
      };

      this.options.onProgress(progressMessage);

      // Stop polling if completed or failed
      if (
        (data.status === "completed" && data.map_status === "completed") ||
        data.status === "failed"
      ) {
        this.stop();
      }
    } catch (error) {
      this.options.onError(error as Error);
    }
  }
}
