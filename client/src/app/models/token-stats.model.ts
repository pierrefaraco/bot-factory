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
