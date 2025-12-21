export type TripStatus = "pending" | "processing" | "completed" | "failed";
export type MapStatus = "not_started" | "generating" | "completed" | "failed";

export interface TripCalculateRequest {
  current_location: string;
  pickup_location: string;
  dropoff_location: string;
  current_cycle_used: number;
}

export interface TripCalculateResponse {
  id: number;
  status: string;
  message: string;
  websocket_url: string;
  polling_url: string;
}

export interface Coordinates {
  lat: number;
  lon: number;
  name?: string;
}

export interface TripCoordinates {
  current: Coordinates;
  pickup: Coordinates;
  dropoff: Coordinates;
}

export interface RouteSegment {
  type: string;
  duration: number;
  distance: number;
  location: string;
  start_time?: number;
  end_time?: number;
}

export interface RouteData {
  segments: RouteSegment[];
  geometry?: {
    type: string;
    coordinates: [number, number][];
  };
}

export interface LogEvent {
  start: number;
  end: number;
  status: "offDuty" | "sleeper" | "driving" | "onDuty";
}

export interface LogRemark {
  time: number;
  location: string;
}

export interface DailyLog {
  date: string;
  events: LogEvent[];
  total_miles: number;
  remarks: LogRemark[];
  driver_name: string;
  carrier_name: string;
  main_office: string;
  co_driver: string;
  from_address: string;
  to_address: string;
  home_terminal_address: string;
  truck_number: string;
  shipping_doc: string;
}

export interface Trip {
  id: number;
  created_at: string;
  updated_at: string;
  current_location: string;
  pickup_location: string;
  dropoff_location: string;
  current_cycle_used: number;
  total_distance: number | null;
  total_driving_time: number | null;
  total_trip_time: number | null;
  route_data: RouteData | null;
  logs_data: DailyLog[] | null;
  coordinates: TripCoordinates | null;
  status: TripStatus;
  progress: number;
  error_message: string | null;
  map_status: MapStatus;
  map_progress: number;
  map_error_message: string | null;
  is_completed: boolean;
  is_map_ready: boolean;
  overall_progress: number;
  map_url: string | null;
}

export interface TripStatusResponse {
  id: number;
  status: TripStatus;
  progress: number;
  error_message: string | null;
  map_status: MapStatus;
  map_progress: number;
  map_error_message: string | null;
  overall_progress: number;
  is_completed: boolean;
  is_map_ready: boolean;
  total_distance: number | null;
  total_driving_time: number | null;
  map_url: string | null;
}

export interface TripSummary {
  id: number;
  status: TripStatus;
  current_location: string;
  pickup_location: string;
  dropoff_location: string;
  total_distance: number | null;
  total_driving_time: number | null;
  total_trip_time: number | null;
  num_days: number;
  map_status: MapStatus;
  is_map_ready: boolean;
  created_at: string;
}

export interface LogInfo {
  day: number;
  date: string;
  total_miles: number;
  from_address: string;
  to_address: string;
  download_url: string;
}

export interface LogsListResponse {
  trip_id: number;
  total_days: number;
  logs: LogInfo[];
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface WebSocketProgressMessage {
  type: "progress" | "status" | "error" | "pong";
  trip_id: number;
  timestamp?: string;
  stage?: string;
  status?: string;
  progress?: number;
  map_progress?: number;
  map_status?: string;
  message?: string;
  error?: string;
  total_distance?: number;
  total_driving_time?: number;
  num_days?: number;
  map_url?: string;
  overall_progress?: number;
  is_completed?: boolean;
  is_map_ready?: boolean;
}

export interface ApiError {
  error: boolean;
  status_code: number;
  message?: string;
  errors?: Record<string, string[]>;
}

export class ApiException extends Error {
  constructor(
    public statusCode: number,
    public data: ApiError
  ) {
    super(data.message || "An error occurred");
    this.name = "ApiException";
  }
}
