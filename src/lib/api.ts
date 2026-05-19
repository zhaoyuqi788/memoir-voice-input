import type { Chapter, ExportResult, Health, Segment } from "../types";

const apiBase = import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8000";
export const wsBase = import.meta.env.VITE_WS_BASE ?? "ws://127.0.0.1:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBase}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers
    }
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json() as Promise<T>;
}

export function audioUrl(segmentId: string): string {
  return `${apiBase}/api/segments/${segmentId}/audio`;
}

export function exportUrl(path: string): string {
  return `${apiBase}${path}`;
}

export const api = {
  health: () => request<Health>("/api/health"),
  chapters: () => request<Chapter[]>("/api/chapters"),
  createChapter: (title: string) =>
    request<Chapter>("/api/chapters", {
      method: "POST",
      body: JSON.stringify({ title })
    }),
  updateChapter: (id: string, payload: Partial<Pick<Chapter, "title" | "status">>) =>
    request<Chapter>(`/api/chapters/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload)
    }),
  updateSegment: (id: string, payload: Partial<Pick<Segment, "raw_text" | "cleaned_text">>) =>
    request<Segment>(`/api/segments/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload)
    }),
  completeChapter: (id: string) =>
    request<ExportResult>(`/api/chapters/${id}/complete`, {
      method: "POST"
    })
};
