// env.d.ts
declare namespace NodeJS {
  interface ProcessEnv {
    readonly NODE_ENV: "development" | "production" | "test";
    readonly NEXT_PUBLIC_API_URL: string;
    readonly NEXT_PUBLIC_WS_URL: string;
  }
}
