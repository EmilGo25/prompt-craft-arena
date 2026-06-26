import { API_BASE } from "./config";

export interface CreateRoomResult {
  code: string;
  total_rounds: number;
  round_seconds: number;
}

export async function createRoom(
  rounds: number,
  roundSeconds: number,
): Promise<CreateRoomResult> {
  const res = await fetch(`${API_BASE}/rooms`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ rounds, round_seconds: roundSeconds }),
  });
  if (!res.ok) throw new Error("Could not create the game.");
  return res.json();
}

export async function roomExists(code: string): Promise<boolean> {
  const res = await fetch(`${API_BASE}/rooms/${code}`);
  if (!res.ok) return false;
  const data = await res.json();
  return Boolean(data.exists);
}
