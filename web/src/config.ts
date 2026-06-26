// Backend base URL. Override with VITE_API_BASE for non-local deployments.
export const API_BASE: string =
  (import.meta.env.VITE_API_BASE as string | undefined) ?? "http://localhost:8000";

export function wsUrl(code: string, name: string): string {
  const base = API_BASE.replace(/^http/, "ws");
  return `${base}/rooms/${code}/ws?name=${encodeURIComponent(name)}`;
}

export function imageUrl(code: string, imageId: string): string {
  return `${API_BASE}/rooms/${code}/images/${imageId}`;
}
