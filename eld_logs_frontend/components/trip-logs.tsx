"use client";

import { Calendar, Download, FileText, Loader2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { LogInfo } from "@/lib/api/types";
import { cn } from "@/lib/utils";

interface TripLogsProps {
  tripId?: number | null;
  logs: LogInfo[];
  isLoading?: boolean;
  onDownload: (day: number) => void;
  downloadingDay?: number | null;
  className?: string;
}

export function TripLogs({
  tripId,
  logs,
  isLoading = false,
  onDownload,
  downloadingDay,
  className,
}: TripLogsProps) {
  return (
    <Card className={cn("border-border", className)}>
      <CardHeader className="border-border/50 border-b">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FileText className="text-primary h-4 w-4" />
            <CardTitle className="text-sm font-medium tracking-tight uppercase">
              Compliance Logs (ELD)
            </CardTitle>
          </div>
          <Badge variant="outline" className="text-xs">
            FMCSA HOS v2.4
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="p-0">
        <div className="divide-border divide-y">
          {isLoading ? (
            <div className="text-muted-foreground flex flex-col items-center gap-3 p-12 text-center">
              <Loader2 className="h-10 w-10 animate-spin opacity-20" />
              <p className="text-sm">Loading logs...</p>
            </div>
          ) : !tripId || logs.length === 0 ? (
            <div className="text-muted-foreground flex flex-col items-center gap-3 p-12 text-center">
              <Calendar className="h-10 w-10 opacity-20" />
              <p className="text-sm">
                No daily logs generated for this session
              </p>
            </div>
          ) : (
            logs.map((log) => (
              <div
                key={log.day}
                className="hover:bg-muted/30 flex items-center justify-between p-4 transition-colors"
              >
                <div className="flex items-center gap-4">
                  <div className="bg-muted border-border flex h-10 w-10 items-center justify-center rounded border">
                    <span className="text-sm font-bold">D{log.day}</span>
                  </div>
                  <div>
                    <p className="text-sm font-medium">
                      Daily Log - Day {log.day}
                    </p>
                    <p className="text-muted-foreground text-xs">
                      {log.date} • {log.total_miles} miles
                    </p>
                    {log.from_address && log.to_address && (
                      <p className="text-muted-foreground max-w-50 truncate text-xs">
                        {log.from_address} → {log.to_address}
                      </p>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    className="border-primary/50 text-primary hover:bg-primary/10 h-8 gap-1.5 bg-transparent text-xs"
                    onClick={() => onDownload(log.day)}
                    disabled={downloadingDay === log.day}
                  >
                    {downloadingDay === log.day ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <Download className="h-3.5 w-3.5" />
                    )}
                    Download PNG
                  </Button>
                </div>
              </div>
            ))
          )}
        </div>
      </CardContent>
    </Card>
  );
}
