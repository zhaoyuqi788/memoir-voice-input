import { describe, expect, it } from "vitest";
import { formatDuration } from "./format";

describe("formatDuration", () => {
  it("formats milliseconds as minutes and seconds", () => {
    expect(formatDuration(65000)).toBe("1:05");
  });
});
