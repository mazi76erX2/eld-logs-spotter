import { z } from "zod";

const envSchema = z.object({
  NEXT_PUBLIC_API_URL: z.string().url().min(1, "API URL is required"),
  NEXT_PUBLIC_WS_URL: z.string().min(1, "WebSocket URL is required"),
});

function validateEnv() {
  const parsed = envSchema.safeParse({
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
    NEXT_PUBLIC_WS_URL: process.env.NEXT_PUBLIC_WS_URL,
  });

  if (!parsed.success) {
    console.error(
      "Invalid environment variables:",
      parsed.error.flatten().fieldErrors
    );
    throw new Error("Invalid environment variables");
  }

  return parsed.data;
}

export const env = validateEnv();

// Export individual variables for convenience
export const API_URL = env.NEXT_PUBLIC_API_URL;
export const WS_URL = env.NEXT_PUBLIC_WS_URL;
