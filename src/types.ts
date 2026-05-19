export type Segment = {
  id: string;
  chapter_id: string;
  position: number;
  raw_text: string;
  cleaned_text: string;
  audio_path: string;
  duration_ms: number;
  created_at: string;
  updated_at: string;
};

export type Chapter = {
  id: string;
  title: string;
  status: string;
  created_at: string;
  updated_at: string;
  segment_count: number;
  duration_ms: number;
  segments: Segment[];
};

export type Health = {
  ok: boolean;
  recognizer_ready: boolean;
  recognizer_status: string;
};

export type ExportResult = {
  chapter_id: string;
  export_path: string;
  download_url: string;
};
