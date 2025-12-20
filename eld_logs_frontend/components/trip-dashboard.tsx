"use client";

import * as React from "react";
import {
  Truck,
  MapPin,
  History,
  FileText,
  Download,
  Search,
  ChevronRight,
  Clock,
  Navigation,
  Activity,
  Calendar,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useToast } from "@/hooks/use-toast";

export function TripDashboard() {
  const { toast } = useToast();
  const [isCalculating, setIsCalculating] = React.useState(false);
  const [currentTrip, setCurrentTrip] = React.useState<any>(null);

  const handleCalculate = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setIsCalculating(true);

    // Simulate API call to /api/trips/calculate/
    setTimeout(() => {
      setIsCalculating(false);
      setCurrentTrip({
        id: "TRP-8921",
        status: "processing",
        current_location: "Los Angeles, CA",
        pickup_location: "Phoenix, AZ",
        dropoff_location: "Dallas, TX",
        created_at: new Date().toISOString(),
      });
      toast({
        title: "Calculation Started",
        description: "Your trip route and HOS logs are being generated.",
      });
    }, 1500);
  };

  return (
    <div className="flex flex-col min-h-screen">
      <header className="border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 sticky top-0 z-50">
        <div className="container flex h-16 items-center justify-between px-4">
          <div className="flex items-center gap-2">
            <div className="bg-primary p-1.5 rounded-lg">
              <Truck className="h-6 w-6 text-primary-foreground" />
            </div>
            <span className="text-xl font-bold tracking-tight">ELD Logs</span>
          </div>
          <nav className="hidden md:flex items-center gap-6 text-sm font-medium">
            <a href="#" className="text-primary transition-colors">
              Dashboard
            </a>
            <a
              href="#"
              className="text-muted-foreground hover:text-foreground transition-colors"
            >
              Trips
            </a>
            <a
              href="#"
              className="text-muted-foreground hover:text-foreground transition-colors"
            >
              Compliance
            </a>
            <a
              href="#"
              className="text-muted-foreground hover:text-foreground transition-colors"
            >
              Settings
            </a>
          </nav>
          <div className="flex items-center gap-4">
            <Button variant="outline" size="sm">
              Feedback
            </Button>
            <Button size="sm" className="bg-primary hover:bg-primary/90">
              Get Started
            </Button>
          </div>
        </div>
      </header>

      <div className="flex-1 container grid md:grid-cols-[350px_1fr] gap-6 p-4 md:p-6 max-w-7xl mx-auto">
        {/* Left Column: Form and Status */}
        <aside className="space-y-6">
          <Card className="bg-card/50 border-border">
            <CardHeader>
              <CardTitle className="text-lg">Calculate New Trip</CardTitle>
              <CardDescription>
                Enter locations to generate HOS compliant route
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleCalculate} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="current">Current Location</Label>
                  <div className="relative">
                    <MapPin className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                    <Input
                      id="current"
                      placeholder="e.g. Los Angeles, CA"
                      className="pl-9 bg-background/50 border-border"
                      required
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="pickup">Pickup Location</Label>
                  <div className="relative">
                    <Navigation className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                    <Input
                      id="pickup"
                      placeholder="e.g. Phoenix, AZ"
                      className="pl-9 bg-background/50 border-border"
                      required
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="dropoff">Dropoff Location</Label>
                  <div className="relative">
                    <ChevronRight className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                    <Input
                      id="dropoff"
                      placeholder="e.g. Dallas, TX"
                      className="pl-9 bg-background/50 border-border"
                      required
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="cycle">Current Cycle Used (hrs)</Label>
                  <div className="relative">
                    <Clock className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                    <Input
                      id="cycle"
                      type="number"
                      defaultValue="0"
                      className="pl-9 bg-background/50 border-border"
                    />
                  </div>
                </div>
                <Button
                  type="submit"
                  className="w-full bg-primary hover:bg-primary/90"
                  disabled={isCalculating}
                >
                  {isCalculating ? (
                    <>
                      <Activity className="mr-2 h-4 w-4 animate-spin" />
                      Calculating...
                    </>
                  ) : (
                    "Calculate Route"
                  )}
                </Button>
              </form>
            </CardContent>
          </Card>

          {currentTrip && (
            <Card className="border-primary/20 bg-primary/5">
              <CardContent className="pt-6 space-y-4">
                <div className="flex items-center justify-between">
                  <div className="space-y-1">
                    <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                      Current Job
                    </p>
                    <h4 className="font-bold">{currentTrip.id}</h4>
                  </div>
                  <Badge
                    variant="outline"
                    className="bg-background border-primary text-primary"
                  >
                    {currentTrip.status}
                  </Badge>
                </div>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">From</span>
                    <span className="font-medium">
                      {currentTrip.current_location}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">To</span>
                    <span className="font-medium">
                      {currentTrip.dropoff_location}
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                  <History className="h-4 w-4 text-primary" />
                  Recent Trips
                </CardTitle>
                <Button variant="ghost" size="icon" className="h-8 w-8">
                  <Search className="h-4 w-4" />
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[200px] pr-4">
                {[1, 2, 3].map((i) => (
                  <div
                    key={i}
                    className="mb-4 last:mb-0 border-b border-border pb-3 last:border-0"
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium">TRP-482{i}</span>
                      <span className="text-xs text-muted-foreground">
                        2 days ago
                      </span>
                    </div>
                    <p className="text-xs text-muted-foreground truncate">
                      Seattle, WA → Miami, FL
                    </p>
                  </div>
                ))}
              </ScrollArea>
            </CardContent>
          </Card>
        </aside>

        {/* Right Column: Visualization and Logs */}
        <section className="space-y-6">
          {/* Map Placeholder - Inspired by the blueprint truck visual */}
          <Card className="overflow-hidden border-border bg-slate-950">
            <CardHeader className="bg-background/40 backdrop-blur-sm border-b border-border/50">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Navigation className="h-4 w-4 text-primary" />
                  <CardTitle className="text-sm font-medium uppercase tracking-tight">
                    Route Visualization
                  </CardTitle>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-8 text-xs gap-1.5 border border-border/50"
                >
                  <Download className="h-3.5 w-3.5" />
                  Download Map
                </Button>
              </div>
            </CardHeader>
            <CardContent className="p-0 relative aspect-video flex items-center justify-center bg-[url('/blueprint-style-highway-map-dark-blue.jpg')] bg-cover bg-center">
              <div className="absolute inset-0 bg-blue-950/20 backdrop-brightness-75" />
              <div className="relative z-10 text-center">
                {!currentTrip ? (
                  <div className="space-y-2 opacity-50">
                    <Navigation className="h-12 w-12 mx-auto text-primary/40" />
                    <p className="text-sm text-primary/60 font-medium">
                      Enter details to see route geometry
                    </p>
                  </div>
                ) : (
                  <div className="flex items-center justify-center h-full w-full">
                    <div className="p-4 bg-background/80 backdrop-blur rounded-lg border border-primary/20 shadow-2xl">
                      <Activity className="h-8 w-8 text-primary animate-pulse mx-auto mb-2" />
                      <p className="text-xs font-mono text-primary uppercase tracking-widest">
                        Processing Geodata...
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            <Card className="bg-card/50">
              <CardHeader className="pb-2">
                <CardDescription className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  Total Distance
                </CardDescription>
                <CardTitle className="text-2xl font-bold">-- mi</CardTitle>
              </CardHeader>
            </Card>
            <Card className="bg-card/50">
              <CardHeader className="pb-2">
                <CardDescription className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  Driving Time
                </CardDescription>
                <CardTitle className="text-2xl font-bold">-- hrs</CardTitle>
              </CardHeader>
            </Card>
            <Card className="bg-card/50 sm:col-span-2 lg:col-span-1">
              <CardHeader className="pb-2">
                <CardDescription className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  Trip Duration
                </CardDescription>
                <CardTitle className="text-2xl font-bold">-- days</CardTitle>
              </CardHeader>
            </Card>
          </div>

          <Card className="border-border">
            <CardHeader className="border-b border-border/50">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <FileText className="h-4 w-4 text-primary" />
                  <CardTitle className="text-sm font-medium uppercase tracking-tight">
                    Compliance Logs (ELD)
                  </CardTitle>
                </div>
                <Badge variant="outline" className="text-xs">
                  FMCSA HOS v2.4
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="p-0">
              <div className="divide-y divide-border">
                {!currentTrip ? (
                  <div className="p-12 text-center text-muted-foreground flex flex-col items-center gap-3">
                    <Calendar className="h-10 w-10 opacity-20" />
                    <p className="text-sm">
                      No daily logs generated for this session
                    </p>
                  </div>
                ) : (
                  [1, 2].map((day) => (
                    <div
                      key={day}
                      className="flex items-center justify-between p-4 hover:bg-muted/30 transition-colors"
                    >
                      <div className="flex items-center gap-4">
                        <div className="h-10 w-10 rounded bg-muted flex items-center justify-center border border-border">
                          <span className="font-bold text-sm">D{day}</span>
                        </div>
                        <div>
                          <p className="font-medium text-sm">
                            Daily Log - Day {day}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            Generated on {new Date().toLocaleDateString()}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-8 text-xs"
                        >
                          View Data
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          className="h-8 text-xs gap-1.5 border-primary/50 text-primary hover:bg-primary/10 bg-transparent"
                        >
                          <Download className="h-3.5 w-3.5" />
                          Download PNG
                        </Button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </CardContent>
          </Card>
        </section>
      </div>

      {/* Footer Branding */}
      <footer className="mt-auto border-t border-border bg-card/30 p-6">
        <div className="container max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center gap-4">
          <p className="text-xs text-muted-foreground">
            © 2025 ELD Logs Systems. All rights reserved. FMCSA & ELD Compliant
            Infrastructure.
          </p>
          <div className="flex gap-4">
            <span className="text-[10px] font-mono text-muted-foreground uppercase tracking-widest bg-muted px-2 py-0.5 rounded">
              Build 12.20.25
            </span>
            <span className="text-[10px] font-mono text-primary uppercase tracking-widest bg-primary/10 px-2 py-0.5 rounded border border-primary/20">
              System Normal
            </span>
          </div>
        </div>
      </footer>
    </div>
  );
}
