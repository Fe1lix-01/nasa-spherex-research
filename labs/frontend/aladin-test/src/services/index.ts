import { apiService } from "./api";
import { mockService } from "./mock";
import type { SkyDataService } from "./types";

/**
 * Elige de dónde salen los datos. Por defecto usa los JSON simulados mientras el back no
 * esté listo. Para usar el back real, define NEXT_PUBLIC_USE_MOCK=false en .env.local.
 */
const useMock = process.env.NEXT_PUBLIC_USE_MOCK !== "false";

export const skyData: SkyDataService = useMock ? mockService : apiService;