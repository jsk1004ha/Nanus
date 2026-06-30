const configuredApiBase = (import.meta.env.VITE_NANUS_API_BASE as string | undefined)?.replace(/\/$/, "") ?? "";

export const backendEnabled = Boolean(configuredApiBase) || import.meta.env.VITE_NANUS_BACKEND_AUTO === "true";

export const backendApiUrl = (path: string) => `${configuredApiBase}${path}`;

export function backendWebSocketUrl(path: string) {
  if (configuredApiBase.startsWith("https://")) return `${configuredApiBase.replace(/^https:/, "wss:")}${path}`;
  if (configuredApiBase.startsWith("http://")) return `${configuredApiBase.replace(/^http:/, "ws:")}${path}`;
  return `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.host}${path}`;
}
