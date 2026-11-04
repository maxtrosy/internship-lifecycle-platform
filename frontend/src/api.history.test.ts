import { afterEach, describe, expect, it, vi } from "vitest";
import { listPlacementHistory } from "./api";

describe("placement history API", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("loads the relation-scoped endpoint with the current session", async () => {
    const payload = [{ occurred_at: "2026-10-25T12:00:00Z", action: "placement.activated" }];
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => payload });
    vi.stubGlobal("fetch", fetchMock);

    await expect(listPlacementHistory(42)).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith("/placements/42/history", expect.objectContaining({
      credentials: "same-origin",
    }));
  });

  it("treats unexpected payload shapes as empty and malformed rows safely", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ unexpected: true }) })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => [null, "bad", { action: 9 }] });
    vi.stubGlobal("fetch", fetchMock);

    await expect(listPlacementHistory(42)).resolves.toEqual([]);
    await expect(listPlacementHistory(42)).resolves.toEqual([{ occurred_at: "", action: "" }]);
  });
});
