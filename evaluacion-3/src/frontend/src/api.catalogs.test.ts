import { afterEach, describe, expect, it, vi } from "vitest";
import { listOpportunityCatalogs, listWorkplaceSupervisors } from "./api";

describe("opportunity catalogs API", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("loads named organizations and programs from the authenticated catalog endpoint", async () => {
    const payload = {
      organizations: [{ id: 3, name: "Org Alfa" }],
      programs: [{ id: 8, code: "ING-SIS", name: "Ingeniería de Sistemas" }],
    };
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => payload,
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(listOpportunityCatalogs()).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith("/opportunities/catalogs", expect.objectContaining({
      credentials: "same-origin",
    }));
  });

  it("loads workplace supervisors for the selected opportunity", async () => {
    const payload = [{ id: 10, display_name: "Supervisora Alfa" }];
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => payload,
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(listWorkplaceSupervisors(42)).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith("/opportunities/42/workplace-supervisors", expect.objectContaining({
      credentials: "same-origin",
    }));
  });
});
