// Dashboard 类型定义

export interface Video {
  id: number;
  source_type: string;
  source_id: string;
  bvid?: string; // backward compat
  title: string;
  author: string;
  duration: number;
  cover_url?: string;
  status: 'pending' | 'downloading' | 'transcribing' | 'analyzing' | 'done' | 'failed';
  summary?: string;
  created_at: string;
  processed_at?: string;
  error_message?: string;
}

export interface VideoDetail extends Video {
  transcript_path?: string;
  key_points?: string[];
  concepts?: string[];
  tags?: string[];
}

export interface TranscriptSegment {
  id: string;
  start: number;
  end: number;
  text: string;
}

export interface ChatSession {
  id: string;
  title: string;
  lastActive: string;
  messages: Message[];
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  citations?: Citation[];
}

export interface Citation {
  videoId: number;
  videoTitle: string;
  timestamp: string;
  text: string;
}

export type InputIntent = 'idle' | 'import' | 'ask' | 'search';

export interface Folder {
  id: number;
  fid: string;
  name: string;
  video_count: number;
  last_scan?: string;
}

export interface ASRConfig {
  provider: string;
  model_size: string;
  device: string;
}

export interface LLMConfig {
  provider: string;
  model: string;
  base_url?: string;
  has_api_key: boolean;
}

export interface AppConfig {
  asr: ASRConfig;
  llm: LLMConfig;
  notify: {
    wechat_enabled: boolean;
    webhook_url?: string;
  };
}
