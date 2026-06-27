// Mirror of server/realtime/protocol.py. Keep in sync with the backend.

export type Phase =
  | "lobby"
  | "generating_target"
  | "prompting"
  | "scoring"
  | "reveal"
  | "game_over";

export interface LeaderboardEntry {
  rank: number;
  name: string;
  avg: number;
  best: number;
  games: number;
}

export interface PlayerView {
  id: string;
  name: string;
  score: number;
  connected: boolean;
  is_host: boolean;
  picture_url: string | null;
}

export interface ResultView {
  player_id: string;
  player_name: string;
  prompt: string;
  image_id: string | null;
  score: number | null;
  similarity: number | null;
  speed_bonus: number | null;
  rationale: string | null;
  dimensions: Record<string, number> | null;
}

// Server -> client messages (discriminated on `type`)
export type ServerMessage =
  | { type: "welcome"; player_id: string; room_code: string }
  | {
      type: "room_state";
      phase: Phase;
      round_num: number;
      total_rounds: number;
      players: PlayerView[];
    }
  | { type: "phase_changed"; phase: Phase; round_num: number }
  | { type: "target_ready"; image_id: string; round_num: number }
  | { type: "timer"; seconds_left: number; deadline_ts: number }
  | { type: "prompt_accepted" }
  | { type: "submission_status"; submitted_player_ids: string[]; total: number }
  | {
      type: "round_reveal";
      round_num: number;
      target_image_id: string;
      results: ResultView[];
      winner_id: string | null;
      standings: PlayerView[];
    }
  | { type: "game_over"; standings: PlayerView[]; winner_id: string | null }
  | { type: "error"; detail: string }
  | { type: "pong" };

// Client -> server messages
export type ClientMessage =
  | { type: "start_game" }
  | { type: "submit_prompt"; prompt: string; lang?: string }
  | { type: "play_again" }
  | { type: "ping" };
