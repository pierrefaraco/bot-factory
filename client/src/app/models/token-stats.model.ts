export interface UserTokenStats {
  user_id: number;
  total_prompt_tokens: number;
  total_completion_tokens: number;
  total_tokens: number;
  total_requests: number;
}

export interface TokenUsageRecord {
  id: number;
  user_guest_id: number;
  bot_id: number;
  session_id: number | null;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  timestamp: string;  // Format: "DD/MM/YYYY HH:MM:SS"
  model_name: string | null;
}

export interface TokenUsageHistory {
  history: TokenUsageRecord[];
}

export interface BotTokenStats {
  bot_id: number;
  total_prompt_tokens: number;
  total_completion_tokens: number;
  total_tokens: number;
  total_requests: number;
  unique_users: number;
}

export interface TotalTokens {
  user_id: number;
  total_tokens?: number;
  total_tokens_last_24h?: number;
}

export interface UserTokenStatsLast24h {
  user_id: number;
  period: string;
  total_prompt_tokens: number;
  total_completion_tokens: number;
  total_tokens: number;
  total_requests: number;
  period_start: string;
  period_end: string;
}

export interface AllUsersStats {
  users: UserTokenStats[];
}

export interface TokenUsageWindow {
  tokens_24h: number;
  tokens_30d: number;
}

export interface AdminTokenUsageSummary {
  // Keyed by user id (string, since it comes back as JSON object keys) --
  // "accounts" is a User account's own total including its guests' usage
  // (a guest always chats under its parent's user_id server-side), while
  // "guests" isolates each guest's own usage by its own id.
  accounts: { [userId: string]: TokenUsageWindow };
  guests: { [guestId: string]: TokenUsageWindow };
}
