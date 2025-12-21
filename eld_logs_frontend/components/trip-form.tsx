"use client";

import { useForm } from "@tanstack/react-form";
import { ChevronRight, Clock, Loader2, MapPin, Navigation } from "lucide-react";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { TripCalculateRequest } from "@/lib/api/types";

// VALIDATION SCHEMAS
const locationSchema = z
  .string()
  .min(3, "Location must be at least 3 characters")
  .max(255, "Location must be less than 255 characters");

const cycleSchema = z
  .number()
  .min(0, "Cycle hours cannot be negative")
  .max(70, "Cycle hours cannot exceed 70");

interface TripFormProps {
  onSubmit: (data: TripCalculateRequest) => Promise<void>;
  isLoading?: boolean;
  disabled?: boolean;
}

export function TripForm({
  onSubmit,
  isLoading = false,
  disabled = false,
}: TripFormProps) {
  const form = useForm({
    defaultValues: {
      current_location: "",
      pickup_location: "",
      dropoff_location: "",
      current_cycle_used: 0,
    },
    onSubmit: async ({ value }) => {
      await onSubmit(value);
    },
  });

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        e.stopPropagation();
        form.handleSubmit();
      }}
      className="space-y-4"
    >
      {/* Current Location */}
      <form.Field
        name="current_location"
        validators={{
          onChange: ({ value }) => {
            const result = locationSchema.safeParse(value);
            return result.success ? undefined : result.error.errors[0]?.message;
          },
        }}
      >
        {(field) => (
          <div className="space-y-2">
            <Label htmlFor={field.name}>Current Location</Label>
            <div className="relative">
              <MapPin className="text-muted-foreground absolute top-3 left-3 h-4 w-4" />
              <Input
                id={field.name}
                name={field.name}
                placeholder="e.g. Los Angeles, CA"
                className="bg-background/50 border-border pl-9"
                disabled={isLoading || disabled}
                value={field.state.value}
                onBlur={field.handleBlur}
                onChange={(e) => field.handleChange(e.target.value)}
              />
            </div>
            {field.state.meta.isTouched &&
              field.state.meta.errors.length > 0 && (
                <p className="text-destructive text-sm font-medium">
                  {field.state.meta.errors.join(", ")}
                </p>
              )}
          </div>
        )}
      </form.Field>

      {/* Pickup Location */}
      <form.Field
        name="pickup_location"
        validators={{
          onChange: ({ value }) => {
            const result = locationSchema.safeParse(value);
            return result.success ? undefined : result.error.errors[0]?.message;
          },
        }}
      >
        {(field) => (
          <div className="space-y-2">
            <Label htmlFor={field.name}>Pickup Location</Label>
            <div className="relative">
              <Navigation className="text-muted-foreground absolute top-3 left-3 h-4 w-4" />
              <Input
                id={field.name}
                name={field.name}
                placeholder="e.g. Phoenix, AZ"
                className="bg-background/50 border-border pl-9"
                disabled={isLoading || disabled}
                value={field.state.value}
                onBlur={field.handleBlur}
                onChange={(e) => field.handleChange(e.target.value)}
              />
            </div>
            {field.state.meta.isTouched &&
              field.state.meta.errors.length > 0 && (
                <p className="text-destructive text-sm font-medium">
                  {field.state.meta.errors.join(", ")}
                </p>
              )}
          </div>
        )}
      </form.Field>

      {/* Dropoff Location */}
      <form.Field
        name="dropoff_location"
        validators={{
          onChange: ({ value }) => {
            const result = locationSchema.safeParse(value);
            return result.success ? undefined : result.error.errors[0]?.message;
          },
        }}
      >
        {(field) => (
          <div className="space-y-2">
            <Label htmlFor={field.name}>Dropoff Location</Label>
            <div className="relative">
              <ChevronRight className="text-muted-foreground absolute top-3 left-3 h-4 w-4" />
              <Input
                id={field.name}
                name={field.name}
                placeholder="e.g. Dallas, TX"
                className="bg-background/50 border-border pl-9"
                disabled={isLoading || disabled}
                value={field.state.value}
                onBlur={field.handleBlur}
                onChange={(e) => field.handleChange(e.target.value)}
              />
            </div>
            {field.state.meta.isTouched &&
              field.state.meta.errors.length > 0 && (
                <p className="text-destructive text-sm font-medium">
                  {field.state.meta.errors.join(", ")}
                </p>
              )}
          </div>
        )}
      </form.Field>

      {/* Current Cycle Used */}
      <form.Field
        name="current_cycle_used"
        validators={{
          onChange: ({ value }) => {
            const result = cycleSchema.safeParse(value);
            return result.success ? undefined : result.error.errors[0]?.message;
          },
        }}
      >
        {(field) => (
          <div className="space-y-2">
            <Label htmlFor={field.name}>Current Cycle Used (hrs)</Label>
            <div className="relative">
              <Clock className="text-muted-foreground absolute top-3 left-3 h-4 w-4" />
              <Input
                id={field.name}
                name={field.name}
                type="number"
                step="0.5"
                min="0"
                max="70"
                placeholder="0"
                className="bg-background/50 border-border pl-9"
                disabled={isLoading || disabled}
                value={field.state.value}
                onBlur={field.handleBlur}
                onChange={(e) =>
                  field.handleChange(parseFloat(e.target.value) || 0)
                }
              />
            </div>
            {field.state.meta.isTouched &&
              field.state.meta.errors.length > 0 && (
                <p className="text-destructive text-sm font-medium">
                  {field.state.meta.errors.join(", ")}
                </p>
              )}
          </div>
        )}
      </form.Field>

      <form.Subscribe
        selector={(state) => [state.canSubmit, state.isSubmitting]}
      >
        {([canSubmit, isSubmitting]) => (
          <Button
            type="submit"
            className="bg-primary hover:bg-primary/90 w-full"
            disabled={!canSubmit || isLoading || disabled || isSubmitting}
          >
            {isLoading || isSubmitting ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Calculating...
              </>
            ) : (
              "Calculate Route"
            )}
          </Button>
        )}
      </form.Subscribe>
    </form>
  );
}
