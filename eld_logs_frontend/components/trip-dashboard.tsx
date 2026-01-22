"use client";

import { History, Search, Truck } from "lucide-react";
import * as React from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Toaster } from "@/components/ui/toaster";
import { useToast } from "@/hooks/use-toast";

import { TripForm } from "@/components/trip-form";
import { TripLogs } from "@/components/trip-logs";
import { TripMap } from "@/components/trip-map";
import { TripProgress } from "@/components/trip-progress";

import {
  useCalculateTrip,
  useDownloadLog,
  useDownloadMap,
  useRetryMap,
  useTrip,
  useTripLogs,
  useTrips,
} from "@/hooks/use-trip";
import { useTripProgress } from "@/hooks/use-trip-progress";
import {
  formatDistance,
  formatDuration,
  formatTripDays,
} from "@/lib/api/client";
import type { TripCalculateRequest } from "@/lib/api/types";
import { wakeUpServices, type ServiceStatus } from "@/lib/wake-up-service";

export function TripDashboard() {
  const { toast } = useToast();

  // State
  const [currentTripId, setCurrentTripId] = React.useState<number | null>(null);
  const [downloadingDay, setDownloadingDay] = React.useState<number | null>(
    null
  );
  const [serviceStatus, setServiceStatus] = React.useState<ServiceStatus>({
    celery: false,
    api: false,
    isReady: false,
  });
  const [checkingServices, setCheckingServices] = React.useState(true);

  React.useEffect(() => {
    const checkServices = async () => {
      setCheckingServices(true);
      const status = await wakeUpServices();
      setServiceStatus(status);
      setCheckingServices(false);
    };

    checkServices();

    const interval = setInterval(checkServices, 30000);
    return () => clearInterval(interval);
  }, []);

  const {
    data: tripsData,
    isLoading: isLoadingTrips,
    refetch: refetchTrips,
  } = useTrips(1);

  const {
    data: currentTrip,
    isLoading: isLoadingTrip,
    refetch: refetchTrip,
  } = useTrip(currentTripId);

  const {
    data: logsData,
    isLoading: isLoadingLogs,
    refetch: refetchLogs,
  } = useTripLogs(currentTripId);

  // Mutations
  const calculateMutation = useCalculateTrip();
  const downloadLogMutation = useDownloadLog();
  const downloadMapMutation = useDownloadMap();
  const retryMapMutation = useRetryMap();

  // Derived state
  const recentTrips = tripsData?.results.slice(0, 5) ?? [];
  const logs = logsData?.logs ?? [];

  // Progress tracking via WebSocket
  const progress = useTripProgress(currentTripId, {
    onComplete: async (_tripId) => {
      toast({
        title: "Trip Complete",
        description: "Your route and HOS logs have been generated.",
      });

      // Refetch trip and logs data
      await refetchTrip();
      await refetchLogs();
      await refetchTrips();
    },
    onError: (error) => {
      toast({
        title: "Error",
        description: error,
        variant: "destructive",
      });
    },
  });

  // Handle form submission
  const handleCalculate = async (data: TripCalculateRequest) => {
    try {
      const result = await calculateMutation.mutateAsync(data);

      if (result) {
        setCurrentTripId(result.id);
        toast({
          title: "Trip Created",
          description: "Calculating your route and generating HOS logs...",
        });
      }
    } catch (error) {
      toast({
        title: "Error",
        description:
          error instanceof Error ? error.message : "Failed to calculate trip",
        variant: "destructive",
      });
    }
  };

  // Handle loading a previous trip
  const handleLoadTrip = (tripId: number) => {
    setCurrentTripId(tripId);
  };

  // Handle downloading a daily log
  const handleDownloadLog = async (day: number) => {
    if (!currentTripId) return;

    setDownloadingDay(day);
    try {
      await downloadLogMutation.mutateAsync({ tripId: currentTripId, day });
      toast({
        title: "Download Started",
        description: `Downloading log for day ${day}...`,
      });
    } catch (error) {
      toast({
        title: "Error",
        description:
          error instanceof Error ? error.message : "Failed to download log",
        variant: "destructive",
      });
    } finally {
      setDownloadingDay(null);
    }
  };

  // Handle downloading the map
  const handleDownloadMap = async () => {
    if (!currentTripId) return;

    try {
      const result = await downloadMapMutation.mutateAsync({
        tripId: currentTripId,
      });
      if (result.success) {
        toast({
          title: "Download Started",
          description: "Downloading route map...",
        });
      } else {
        toast({
          title: "Map Not Ready",
          description: result.message || "The map is still being generated.",
          variant: "destructive",
        });
      }
    } catch (error) {
      toast({
        title: "Error",
        description:
          error instanceof Error ? error.message : "Failed to download map",
        variant: "destructive",
      });
    }
  };

  // Handle retrying map generation
  const handleRetryMap = async () => {
    if (!currentTripId) return;

    try {
      await retryMapMutation.mutateAsync(currentTripId);
      toast({
        title: "Map Regeneration",
        description: "The map is being regenerated. Please wait...",
      });
    } catch (error) {
      toast({
        title: "Error",
        description:
          error instanceof Error ? error.message : "Failed to retry map",
        variant: "destructive",
      });
    }
  };

  // Computed states - fixed to properly detect completion
  const isProcessing = React.useMemo(() => {
    // Currently submitting the form
    if (calculateMutation.isPending) return true;

    // Trip is explicitly completed
    if (currentTrip?.status === "completed") return false;

    // Progress indicates completion
    if (progress.isCompleted && progress.isMapReady) return false;

    // Trip is processing
    if (currentTrip?.status === "processing") return true;

    // WebSocket says processing (and not completed)
    if (
      progress.isConnected &&
      progress.status === "processing" &&
      !progress.isCompleted
    ) {
      return true;
    }

    return false;
  }, [
    calculateMutation.isPending,
    currentTrip?.status,
    progress.isCompleted,
    progress.isMapReady,
    progress.isConnected,
    progress.status,
  ]);

  const isApiLoading =
    isLoadingTrips || isLoadingTrip || calculateMutation.isPending;

  // Get the best available map data (prefer real-time progress over cached trip data)
  const mapUrl = progress.mapUrl || currentTrip?.map_url || null;
  const mapStatus = progress.mapStatus || currentTrip?.map_status || null;
  const mapProgress = progress.mapProgress || currentTrip?.map_progress || 0;
  const isMapReady = progress.isMapReady || currentTrip?.is_map_ready || false;

  const getBadgeVariant = () => {
    if (checkingServices) return "outline";
    if (isProcessing) return "default";
    if (!serviceStatus.isReady) return "destructive";
    return "secondary";
  };

  const getBadgeText = () => {
    if (checkingServices) return "Checking...";
    if (isProcessing) return "Processing...";
    if (!serviceStatus.isReady) {
      if (!serviceStatus.api && !serviceStatus.celery) return "Services Down";
      if (!serviceStatus.api) return "API Down";
      if (!serviceStatus.celery) return "Celery Down";
    }
    return "Ready";
  };

  return (
    <div className="bg-background min-h-screen">
      <Toaster />

      {/* Header */}
      <header className="bg-card border-b">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Truck className="text-primary h-8 w-8" />
              <div>
                <h1 className="text-2xl font-bold">Trip Dashboard</h1>
                <p className="text-muted-foreground text-sm">
                  Plan routes and generate ELD logs
                </p>
              </div>
            </div>
            <Badge
              variant={getBadgeVariant()}
              className={checkingServices ? "animate-pulse" : ""}
            >
              {getBadgeText()}
            </Badge>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-6">
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          {/* Left Column - Form & Recent Trips */}
          <div className="space-y-6">
            {/* Trip Form Card */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Search className="h-5 w-5" />
                  Plan New Trip
                </CardTitle>
                <CardDescription>
                  Enter your trip details to calculate the optimal route and
                  generate HOS logs
                </CardDescription>
              </CardHeader>
              <CardContent>
                <TripForm
                  onSubmit={handleCalculate}
                  isLoading={calculateMutation.isPending || isProcessing}
                />
              </CardContent>
            </Card>

            {/* Recent Trips Card */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <History className="h-5 w-5" />
                  Recent Trips
                </CardTitle>
                <CardDescription>Click to load a previous trip</CardDescription>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-62.5">
                  {isLoadingTrips ? (
                    <div className="flex flex-col items-center justify-center py-8 text-center">
                      <div className="border-primary h-8 w-8 animate-spin rounded-full border-2 border-t-transparent" />
                      <p className="text-muted-foreground mt-2 text-sm">
                        Loading trips...
                      </p>
                    </div>
                  ) : recentTrips.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-8 text-center">
                      <Truck className="text-muted-foreground/50 mb-2 h-12 w-12" />
                      <p className="text-muted-foreground text-sm">
                        No recent trips found
                      </p>
                      <p className="text-muted-foreground text-xs">
                        Create your first trip above
                      </p>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {recentTrips.map((trip) => (
                        <Button
                          key={trip.id}
                          variant={
                            currentTripId === trip.id ? "secondary" : "ghost"
                          }
                          className="h-auto w-full justify-start px-3 py-3 text-left"
                          onClick={() => handleLoadTrip(trip.id)}
                          disabled={isApiLoading}
                        >
                          <div className="flex w-full flex-col gap-1 overflow-hidden">
                            <div className="flex items-center justify-between gap-2">
                              <span className="truncate text-sm font-medium">
                                Trip #{trip.id}
                              </span>
                              <Badge
                                variant={
                                  trip.status === "completed"
                                    ? "default"
                                    : trip.status === "failed"
                                      ? "destructive"
                                      : "secondary"
                                }
                                className="text-xs"
                              >
                                {trip.status}
                              </Badge>
                            </div>
                            <span className="text-muted-foreground truncate text-xs">
                              {trip.pickup_location}
                            </span>
                            <span className="text-muted-foreground truncate text-xs">
                              → {trip.dropoff_location}
                            </span>
                            {trip.total_distance && trip.total_driving_time && (
                              <span className="text-muted-foreground text-xs">
                                {formatDistance(trip.total_distance)} •{" "}
                                {formatDuration(trip.total_driving_time)} •{" "}
                                {formatTripDays(trip)}
                              </span>
                            )}
                          </div>
                        </Button>
                      ))}
                    </div>
                  )}
                </ScrollArea>
              </CardContent>
            </Card>
          </div>

          {/* Right Column - Map, Progress, Logs */}
          <div className="space-y-6 lg:col-span-2">
            {/* Progress Indicator - only show when actually processing */}
            {isProcessing && progress.isConnected && (
              <TripProgress progress={progress} />
            )}

            {/* Map Card */}
            <Card>
              <CardHeader>
                <CardTitle>Route Map</CardTitle>
                {currentTrip && currentTrip.total_distance && (
                  <CardDescription>
                    {formatDistance(currentTrip.total_distance)}
                    {currentTrip.total_driving_time && (
                      <> • {formatDuration(currentTrip.total_driving_time)}</>
                    )}
                    {currentTrip.status === "completed" && (
                      <> • {formatTripDays(currentTrip)}</>
                    )}
                  </CardDescription>
                )}
              </CardHeader>
              <CardContent>
                <TripMap
                  tripId={currentTripId}
                  mapUrl={mapUrl}
                  mapStatus={mapStatus}
                  mapProgress={mapProgress}
                  isMapReady={isMapReady}
                  isLoading={isProcessing && !progress.isConnected}
                  onDownload={handleDownloadMap}
                  onRetry={handleRetryMap}
                  isDownloading={downloadMapMutation.isPending}
                />
              </CardContent>
            </Card>

            {/* Logs Card */}
            {currentTrip?.status === "completed" && (
              <Card>
                <CardHeader>
                  <CardTitle>ELD Logs</CardTitle>
                  <CardDescription>
                    Daily Hours of Service logs for your trip
                    {logs.length > 0 && (
                      <>
                        {" "}
                        ({logs.length} {logs.length === 1 ? "day" : "days"})
                      </>
                    )}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <TripLogs
                    tripId={currentTripId}
                    logs={logs}
                    isLoading={isLoadingLogs}
                    onDownload={handleDownloadLog}
                    downloadingDay={downloadingDay}
                  />
                </CardContent>
              </Card>
            )}

            {/* Empty State */}
            {!currentTrip && !isProcessing && (
              <Card>
                <CardContent className="flex flex-col items-center justify-center py-16">
                  <Truck className="text-muted-foreground/30 mb-4 h-16 w-16" />
                  <h3 className="text-muted-foreground text-lg font-medium">
                    No Trip Selected
                  </h3>
                  <p className="text-muted-foreground mt-1 max-w-sm text-center text-sm">
                    Create a new trip using the form or select a recent trip to
                    view the route and logs.
                  </p>
                </CardContent>
              </Card>
            )}

            {/* Loading State for Trip Details */}
            {currentTripId && isLoadingTrip && !isProcessing && (
              <Card>
                <CardContent className="flex flex-col items-center justify-center py-16">
                  <div className="border-primary mb-4 h-12 w-12 animate-spin rounded-full border-4 border-t-transparent" />
                  <h3 className="text-muted-foreground text-lg font-medium">
                    Loading Trip Details
                  </h3>
                  <p className="text-muted-foreground mt-1 max-w-sm text-center text-sm">
                    Please wait while we fetch the trip information...
                  </p>
                </CardContent>
              </Card>
            )}

            {/* Error State */}
            {currentTrip?.status === "failed" && (
              <Card className="border-destructive/50">
                <CardContent className="flex flex-col items-center justify-center py-16">
                  <div className="bg-destructive/10 mb-4 flex h-16 w-16 items-center justify-center rounded-full">
                    <Truck className="text-destructive h-8 w-8" />
                  </div>
                  <h3 className="text-destructive text-lg font-medium">
                    Trip Calculation Failed
                  </h3>
                  <p className="text-muted-foreground mt-1 max-w-sm text-center text-sm">
                    {currentTrip.error_message ||
                      "An error occurred while calculating the route. Please try again."}
                  </p>
                  <Button
                    variant="outline"
                    className="mt-4"
                    onClick={() => setCurrentTripId(null)}
                  >
                    Start New Trip
                  </Button>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-card mt-auto border-t">
        <div className="container mx-auto px-4 py-4">
          <div className="text-muted-foreground flex items-center justify-between text-sm">
            <p>ELD Logs Dashboard</p>
            <p>FMCSA HOS Compliant</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
