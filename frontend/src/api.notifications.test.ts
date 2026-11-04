import { afterEach, describe, expect, it, vi } from "vitest";
import { listNotifications, listPlacementMessages, markNotificationRead, sendPlacementMessage } from "./api";

describe("notifications and contextual messages API", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("loads and acknowledges only through the notification endpoints", async () => {
    const rows = [{ id: 7, category: "PROGRESS_REPORTED", placement_id: 12, opportunity_id: 4,
      created_at: "2026-11-02T12:00:00Z", read_at: null, is_read: false }];
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => rows })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ id: 7, read_at: "2026-11-02T12:01:00Z" }) });
    vi.stubGlobal("fetch", fetchMock);

    await expect(listNotifications()).resolves.toEqual(rows);
    await expect(markNotificationRead(7)).resolves.toHaveProperty("id", 7);
    expect(fetchMock).toHaveBeenNthCalledWith(1, "/notifications", expect.objectContaining({ credentials: "same-origin" }));
    expect(fetchMock).toHaveBeenNthCalledWith(2, "/notifications/7/read", expect.objectContaining({ method: "POST" }));
  });

  it("addresses the selected audience and persists message content", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => [] })
      .mockResolvedValueOnce({ ok: true, status: 201, json: async () => ({ id: 9, audience: "ACADEMIC", author_name: "Student", content: "Consulta", created_at: "2026-11-02T12:00:00Z" }) });
    vi.stubGlobal("fetch", fetchMock);

    await listPlacementMessages(12, "ACADEMIC");
    await sendPlacementMessage(12, "ACADEMIC", "Consulta");
    expect(fetchMock).toHaveBeenNthCalledWith(1, "/placements/12/messages?audience=ACADEMIC", expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(2, "/placements/12/messages", expect.objectContaining({
      method: "POST", body: JSON.stringify({ audience: "ACADEMIC", content: "Consulta" }),
    }));
  });
});
