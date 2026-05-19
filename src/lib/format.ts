export function formatDuration(ms: number): string {
  const totalSeconds = Math.max(0, Math.round(ms / 1000));
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}:${seconds.toString().padStart(2, "0")}`;
}

export function chapterDuration(chapter: { duration_ms?: number; segments?: { duration_ms: number }[] }): string {
  const value = chapter.duration_ms ?? chapter.segments?.reduce((sum, segment) => sum + segment.duration_ms, 0) ?? 0;
  return formatDuration(value);
}
