import { create } from "zustand";
import type { ClientMessage, Phase, PlayerView, ResultView, ServerMessage } from "./types";

interface RevealData {
  roundNum: number;
  targetImageId: string;
  results: ResultView[];
  winnerId: string | null;
  standings: PlayerView[];
}

interface GameStore {
  // connection
  connected: boolean;
  connError: string | null;
  send: (msg: ClientMessage) => void;

  // identity / room
  playerId: string | null;
  roomCode: string | null;

  // game state
  phase: Phase;
  roundNum: number;
  totalRounds: number;
  players: PlayerView[];

  // round state
  targetImageId: string | null;
  deadlineLocalMs: number | null; // skew-corrected deadline for the countdown
  submittedIds: string[];
  submitTotal: number;
  mySubmitted: boolean;
  toast: string | null;

  reveal: RevealData | null;
  gameOver: { standings: PlayerView[]; winnerId: string | null } | null;

  // actions
  setSend: (fn: (msg: ClientMessage) => void) => void;
  setConnected: (v: boolean) => void;
  setConnError: (v: string | null) => void;
  clearToast: () => void;
  handle: (msg: ServerMessage) => void;
  resetGame: () => void;
}

const initial = {
  connected: false,
  connError: null as string | null,
  playerId: null as string | null,
  roomCode: null as string | null,
  phase: "lobby" as Phase,
  roundNum: 0,
  totalRounds: 0,
  players: [] as PlayerView[],
  targetImageId: null as string | null,
  deadlineLocalMs: null as number | null,
  submittedIds: [] as string[],
  submitTotal: 0,
  mySubmitted: false,
  toast: null as string | null,
  reveal: null as RevealData | null,
  gameOver: null as { standings: PlayerView[]; winnerId: string | null } | null,
};

export const useGame = create<GameStore>((set) => ({
  ...initial,
  send: () => {},

  setSend: (fn) => set({ send: fn }),
  setConnected: (v) => set({ connected: v }),
  setConnError: (v) => set({ connError: v }),
  clearToast: () => set({ toast: null }),
  resetGame: () => set({ ...initial }),

  handle: (msg) =>
    set(() => {
      switch (msg.type) {
        case "welcome":
          return { playerId: msg.player_id, roomCode: msg.room_code };
        case "room_state":
          return {
            phase: msg.phase,
            roundNum: msg.round_num,
            totalRounds: msg.total_rounds,
            players: msg.players,
          };
        case "phase_changed": {
          const next: Partial<GameStore> = { phase: msg.phase, roundNum: msg.round_num };
          if (msg.phase === "prompting") {
            next.submittedIds = [];
            next.mySubmitted = false;
            next.reveal = null;
          }
          if (msg.phase === "generating_target") {
            next.targetImageId = null;
          }
          return next;
        }
        case "target_ready":
          return { targetImageId: msg.image_id };
        case "timer": {
          // Correct for clock skew: estimate server "now" from the message,
          // then express the deadline in our local clock.
          const serverNow = msg.deadline_ts - msg.seconds_left;
          const offset = Date.now() / 1000 - serverNow;
          return { deadlineLocalMs: (msg.deadline_ts + offset) * 1000 };
        }
        case "prompt_accepted":
          return { mySubmitted: true };
        case "submission_status":
          return { submittedIds: msg.submitted_player_ids, submitTotal: msg.total };
        case "round_reveal":
          return {
            phase: "reveal",
            players: msg.standings,
            reveal: {
              roundNum: msg.round_num,
              targetImageId: msg.target_image_id,
              results: msg.results,
              winnerId: msg.winner_id,
              standings: msg.standings,
            },
          };
        case "game_over":
          return {
            phase: "game_over",
            players: msg.standings,
            gameOver: { standings: msg.standings, winnerId: msg.winner_id },
          };
        case "error":
          return { toast: msg.detail };
        case "pong":
          return {};
        default:
          return {};
      }
    }),
}));
