"use client";

import {
  AlertCircle,
  Download,
  Loader2,
  Navigation,
  RefreshCw,
} from "lucide-react";
import Image from "next/image";
import * as React from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import type { MapStatus, Trip } from "@/lib/api/types";
import { cn } from "@/lib/utils";

// Get the base URL for media files (without /api)
const getMediaBaseUrl = (): string => {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";
  return apiUrl.replace("/api", "");
};

// Convert relative media URL to full URL
const getFullMapUrl = (mapUrl: string | null | undefined): string | null => {
  if (!mapUrl) return null;

  // If it's already a full URL, return as-is
  if (mapUrl.startsWith("http://") || mapUrl.startsWith("https://")) {
    return mapUrl;
  }

  // Prepend the media base URL
  return `${getMediaBaseUrl()}${mapUrl}`;
};

interface TripMapProps {
  tripId?: number | null;
  mapUrl?: string | null;
  mapStatus?: MapStatus | null;
  mapProgress?: number;
  isMapReady?: boolean;
  isLoading?: boolean;
  onDownload: () => void;
  onRetry: () => void;
  isDownloading?: boolean;
  className?: string;
  // Alternative: pass the full trip object
  trip?: Trip | null;
}

export function TripMap({
  tripId: propTripId,
  mapUrl: propMapUrl,
  mapStatus: propMapStatus,
  mapProgress: propMapProgress = 0,
  isMapReady: propIsMapReady,
  isLoading = false,
  onDownload,
  onRetry,
  isDownloading = false,
  className,
  trip,
}: TripMapProps) {
  // Support both individual props and trip object
  const tripId = propTripId ?? trip?.id ?? null;
  const mapUrl = propMapUrl ?? trip?.map_url ?? null;
  const mapStatus = propMapStatus ?? trip?.map_status ?? null;
  const mapProgress = propMapProgress ?? trip?.map_progress ?? 0;
  const isMapReady = propIsMapReady ?? trip?.is_map_ready ?? false;

  const [imageError, setImageError] = React.useState(false);

  // Get the full URL for the map image
  const fullMapUrl = getFullMapUrl(mapUrl);

  // Reset image error when URL changes
  React.useEffect(() => {
    setImageError(false);
  }, [mapUrl]);

  const renderContent = () => {
    // Loading state
    if (isLoading) {
      return (
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="bg-background/80 border-primary/20 space-y-3 rounded-lg border p-6 text-center shadow-2xl backdrop-blur">
            <Loader2 className="text-primary mx-auto h-8 w-8 animate-spin" />
            <p className="text-primary font-mono text-xs tracking-widest uppercase">
              Processing Trip...
            </p>
          </div>
        </div>
      );
    }

    // No trip selected
    if (!tripId) {
      return (
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="space-y-2 text-center opacity-50">
            <Navigation className="text-primary/40 mx-auto h-12 w-12" />
            <p className="text-primary/60 text-sm font-medium">
              Enter details to see route geometry
            </p>
          </div>
        </div>
      );
    }

    // Map is generating
    if (mapStatus === "generating") {
      return (
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="bg-background/80 border-primary/20 space-y-3 rounded-lg border p-6 text-center shadow-2xl backdrop-blur">
            <Loader2 className="text-primary mx-auto h-8 w-8 animate-spin" />
            <div className="space-y-1">
              <p className="text-primary font-mono text-xs tracking-widest uppercase">
                Generating Map...
              </p>
              <div className="mx-auto w-40">
                <Progress value={mapProgress} className="h-1.5" />
              </div>
              <p className="text-muted-foreground text-xs">{mapProgress}%</p>
            </div>
          </div>
        </div>
      );
    }

    // Map generation failed
    if (mapStatus === "failed") {
      return (
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="bg-background/80 border-destructive/20 space-y-3 rounded-lg border p-6 text-center shadow-2xl backdrop-blur">
            <AlertCircle className="text-destructive mx-auto h-8 w-8" />
            <div className="space-y-2">
              <p className="text-destructive text-sm font-medium">
                Map generation failed
              </p>
              <Button size="sm" variant="outline" onClick={onRetry}>
                <RefreshCw className="mr-2 h-3.5 w-3.5" />
                Retry
              </Button>
            </div>
          </div>
        </div>
      );
    }

    // Map is ready - show image with full URL
    if (isMapReady && fullMapUrl && !imageError) {
      return (
        <Image
          src={fullMapUrl}
          alt="Route Map"
          fill
          className="object-contain"
          onError={() => setImageError(true)}
          unoptimized // Required for external URLs
        />
      );
    }

    // Map not started or image failed to load
    return (
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="space-y-2 text-center opacity-50">
          <Navigation className="text-primary/40 mx-auto h-12 w-12" />
          <p className="text-primary/60 text-sm font-medium">
            {imageError ? "Failed to load map image" : "Map will appear here"}
          </p>
        </div>
      </div>
    );
  };

  return (
    <Card
      className={cn("border-border overflow-hidden bg-slate-950", className)}
    >
      <CardHeader className="bg-background/40 border-border/50 border-b backdrop-blur-sm">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Navigation className="text-primary h-4 w-4" />
            <CardTitle className="text-sm font-medium tracking-tight uppercase">
              Route Visualization
            </CardTitle>
          </div>
          <Button
            variant="ghost"
            size="sm"
            className="border-border/50 h-8 gap-1.5 border text-xs"
            onClick={onDownload}
            disabled={!isMapReady || isDownloading}
          >
            {isDownloading ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Download className="h-3.5 w-3.5" />
            )}
            Download Map
          </Button>
        </div>
      </CardHeader>
      <CardContent className="relative aspect-video bg-slate-900 p-0">
        <div className="absolute inset-0 bg-linear-to-br from-blue-950/20 to-slate-900/80" />
        {renderContent()}
      </CardContent>
    </Card>
  );
}
