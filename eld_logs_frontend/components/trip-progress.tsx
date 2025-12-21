"use client";

import {
  CheckCircle2,
  FileText,
  Loader2,
  MapIcon,
  Route,
  Wifi,
  WifiOff,
  XCircle,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import type { TripProgressState } from "@/hooks/use-trip-progress";
import { cn } from "@/lib/utils";

interface TripProgressProps {
  progress: TripProgressState;
  className?: string;
}

export function TripProgress({ progress, className }: TripProgressProps) {
  const {
    status,
    overallProgress,
    mapStatus,
    mapProgress,
    message,
    stage,
    error,
    isConnected,
    isCompleted,
    isMapReady,
  } = progress;

  // Determine status colors and icons
  const getStatusBadge = () => {
    if (error) {
      return (
        <Badge variant="destructive" className="gap-1">
          <XCircle className="h-3 w-3" />
          Failed
        </Badge>
      );
    }

    if (isCompleted && isMapReady) {
      return (
        <Badge variant="default" className="gap-1 bg-green-600">
          <CheckCircle2 className="h-3 w-3" />
          Complete
        </Badge>
      );
    }

    if (status === "processing" || mapStatus === "generating") {
      return (
        <Badge variant="secondary" className="gap-1">
          <Loader2 className="h-3 w-3 animate-spin" />
          Processing
        </Badge>
      );
    }

    return (
      <Badge variant="outline" className="gap-1">
        Pending
      </Badge>
    );
  };

  // Stage indicators
  const stages = [
    {
      id: "geocoding",
      label: "Geocoding",
      icon: MapIcon,
      complete: (progress.progress ?? 0) >= 25,
    },
    {
      id: "routing",
      label: "Route Calculation",
      icon: Route,
      complete: (progress.progress ?? 0) >= 50,
    },
    {
      id: "hos_calculation",
      label: "HOS Compliance",
      icon: FileText,
      complete: (progress.progress ?? 0) >= 75,
    },
    {
      id: "map_generation",
      label: "Map Generation",
      icon: MapIcon,
      complete: isMapReady,
    },
  ];

  if (!progress.tripId) {
    return null;
  }

  return (
    <Card className={cn("border-primary/20 bg-primary/5", className)}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium">Processing Trip</CardTitle>
          <div className="flex items-center gap-2">
            {isConnected ? (
              <Wifi className="h-3 w-3 text-green-500" />
            ) : (
              <WifiOff className="text-muted-foreground h-3 w-3" />
            )}
            {getStatusBadge()}
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Overall Progress */}
        <div className="space-y-2">
          <div className="flex justify-between text-xs">
            <span className="text-muted-foreground">Overall Progress</span>
            <span className="font-medium">{overallProgress}%</span>
          </div>
          <Progress value={overallProgress} className="h-2" />
        </div>

        {/* Status Message */}
        {message && (
          <p className="text-muted-foreground truncate text-xs">{message}</p>
        )}

        {/* Error Message */}
        {error && (
          <div className="bg-destructive/10 rounded-md p-2">
            <p className="text-destructive text-xs">{error}</p>
          </div>
        )}

        {/* Stage Indicators */}
        <div className="grid grid-cols-4 gap-2">
          {stages.map((stageItem) => {
            const Icon = stageItem.icon;
            const isActive = stage === stageItem.id;
            const isComplete = stageItem.complete;

            return (
              <div
                key={stageItem.id}
                className={cn(
                  "flex flex-col items-center gap-1 rounded-md p-2 text-center transition-colors",
                  isActive && "bg-primary/10",
                  isComplete && "text-green-600"
                )}
              >
                {isComplete ? (
                  <CheckCircle2 className="h-4 w-4" />
                ) : isActive ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Icon className="text-muted-foreground h-4 w-4" />
                )}
                <span className="text-[10px] leading-tight">
                  {stageItem.label}
                </span>
              </div>
            );
          })}
        </div>

        {/* Map Generation Progress */}
        {mapStatus === "generating" && (
          <div className="border-border/50 space-y-2 border-t pt-2">
            <div className="flex justify-between text-xs">
              <span className="text-muted-foreground">Map Generation</span>
              <span className="font-medium">{mapProgress}%</span>
            </div>
            <Progress value={mapProgress} className="h-1.5" />
          </div>
        )}
      </CardContent>
    </Card>
  );
}
