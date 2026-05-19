import { render, screen, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";

const mockChapters = [
  {
    id: "chapter-1",
    title: "第一章",
    status: "draft",
    created_at: "2026-05-19",
    updated_at: "2026-05-19",
    segment_count: 0,
    duration_ms: 0,
    segments: []
  }
];

describe("App", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const url = input.toString();
        if (url.endsWith("/api/health")) {
          return Promise.resolve(
            new Response(
              JSON.stringify({ ok: true, recognizer_ready: false, recognizer_status: "模型未加载" }),
              { status: 200, headers: { "Content-Type": "application/json" } }
            )
          );
        }
        if (url.endsWith("/api/chapters")) {
          return Promise.resolve(
            new Response(JSON.stringify(mockChapters), {
              status: 200,
              headers: { "Content-Type": "application/json" }
            })
          );
        }
        return Promise.resolve(new Response("{}", { status: 200 }));
      })
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders the chapter workspace", async () => {
    render(<App />);
    await waitFor(() => expect(screen.getByDisplayValue("第一章")).toBeInTheDocument());
    expect(screen.getByRole("button", { name: "开始录音" })).toBeInTheDocument();
  });
});
