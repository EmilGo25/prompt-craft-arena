import { useEffect, useRef } from "react";
import { wsUrl } from "./config";
import { useGame } from "./store";
import type { ClientMessage, ServerMessage } from "./types";

/**
 * Opens a WebSocket to a room and wires it to the game store. Sends a periodic
 * ping to keep the connection alive. Returns nothing — screens read state from
 * the store and call store.send().
 */
export function useGameSocket(code: string | null, name: string | null): void {
  const handle = useGame((s) => s.handle);
  const setSend = useGame((s) => s.setSend);
  const setConnected = useGame((s) => s.setConnected);
  const setConnError = useGame((s) => s.setConnError);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!code || !name) return;
    const ws = new WebSocket(wsUrl(code, name));
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      setConnError(null);
    };
    ws.onmessage = (ev) => {
      try {
        handle(JSON.parse(ev.data) as ServerMessage);
      } catch {
        /* ignore malformed frames */
      }
    };
    ws.onclose = (ev) => {
      setConnected(false);
      if (ev.code === 4404) setConnError("conn.notFound");
    };
    ws.onerror = () => setConnError("conn.problem");

    setSend((msg: ClientMessage) => {
      if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(msg));
    });

    const ping = window.setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: "ping" }));
    }, 20000);

    return () => {
      window.clearInterval(ping);
      ws.close();
    };
  }, [code, name, handle, setSend, setConnected, setConnError]);
}
