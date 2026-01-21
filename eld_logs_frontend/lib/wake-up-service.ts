const CELERY_HEALTH_URL = "https://eld-logs-celery.onrender.com/";
const API_HEALTH_URL = process.env.NEXT_PUBLIC_API_URL + "/health";
const TIMEOUT_MS = 30000; // 30 seconds

export interface ServiceStatus {
  celery: boolean;
  api: boolean;
  isReady: boolean;
}

/**
 * Wake up Render.com free tier services before making API calls
 */
export async function wakeUpServices(): Promise<ServiceStatus> {
  const status: ServiceStatus = {
    celery: false,
    api: false,
    isReady: false,
  };

  try {
    // Ping both services in parallel
    const [celeryResponse, apiResponse] = await Promise.allSettled([
      fetch(CELERY_HEALTH_URL, {
        method: "GET",
        signal: AbortSignal.timeout(TIMEOUT_MS),
      }),
      fetch(API_HEALTH_URL, {
        method: "GET",
        signal: AbortSignal.timeout(TIMEOUT_MS),
      }),
    ]);

    // Check Celery
    if (celeryResponse.status === "fulfilled" && celeryResponse.value.ok) {
      const text = await celeryResponse.value.text();
      status.celery = text.includes("OK");
    }

    // Check API
    if (apiResponse.status === "fulfilled" && apiResponse.value.ok) {
      status.api = true;
    }

    status.isReady = status.celery && status.api;
    return status;
  } catch (error) {
    console.error("Service wake-up failed:", error);
    return status;
  }
}

/**
 * Poll services until they're ready or timeout
 */
export async function waitForServicesReady(
  maxAttempts = 10,
  delayMs = 3000
): Promise<ServiceStatus> {
  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    console.log(`Checking services (attempt ${attempt}/${maxAttempts})...`);

    const status = await wakeUpServices();

    if (status.isReady) {
      console.log("All services ready!");
      return status;
    }

    if (attempt < maxAttempts) {
      console.log(`Services not ready. Retrying in ${delayMs / 1000}s...`);
      await new Promise((resolve) => setTimeout(resolve, delayMs));
    }
  }

  console.error("Services did not wake up in time");
  const finalStatus = await wakeUpServices();
  return finalStatus;
}
