import { afterEach, describe, expect, it, vi } from "vitest";
import { assignWorkPlanItem, listWorkPlan, reportPlacementIncident, submitCompletionEvidence, submitPlacementEvaluation, submitProgressReport } from "./api";

describe("follow-up lifecycle API", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("persists progress reports, narrative evaluations, and incident/change reports", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 201, json: async () => ({ revision: 1 }) });
    vi.stubGlobal("fetch", fetchMock);

    await submitProgressReport(12, "Avance registrado.");
    await submitPlacementEvaluation(12, "FINAL", "Observaciones narrativas.");
    await reportPlacementIncident(12, "CHANGE", "Cambio de horario", "Se comunica el cambio solicitado.");

    expect(fetchMock).toHaveBeenNthCalledWith(1, "/placements/12/progress-reports", expect.objectContaining({
      method: "POST", credentials: "same-origin", body: JSON.stringify({ content: "Avance registrado." }),
    }));
    expect(fetchMock).toHaveBeenNthCalledWith(2, "/placements/12/evaluations", expect.objectContaining({
      method: "POST", body: JSON.stringify({ kind: "FINAL", narrative: "Observaciones narrativas." }),
    }));
    expect(fetchMock).toHaveBeenNthCalledWith(3, "/placements/12/incidents", expect.objectContaining({
      method: "POST", body: JSON.stringify({ kind: "CHANGE", summary: "Cambio de horario", description: "Se comunica el cambio solicitado." }),
    }));
  });

  it("reads and assigns narrative work-plan activities through the placement endpoints", async () => {
    const payload = [{
      revision: 1, title: "Preparar inventario", description: "Documentar el proceso de inventario.",
      assigned_at: "2026-11-02T12:00:00Z", assigned_by: "Supervisor laboral",
    }];
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => payload })
      .mockResolvedValueOnce({ ok: true, status: 201, json: async () => ({ revision: 2, assigned_at: "2026-11-02T12:01:00Z" }) });
    vi.stubGlobal("fetch", fetchMock);

    await expect(listWorkPlan(12)).resolves.toEqual(payload);
    await expect(assignWorkPlanItem(12, "Preparar inventario", "Documentar el proceso de inventario."))
      .resolves.toEqual({ revision: 2, assigned_at: "2026-11-02T12:01:00Z" });

    expect(fetchMock).toHaveBeenNthCalledWith(1, "/placements/12/work-plan", expect.objectContaining({
      credentials: "same-origin",
    }));
    expect(fetchMock).toHaveBeenNthCalledWith(2, "/placements/12/work-plan", expect.objectContaining({
      method: "POST", credentials: "same-origin",
      body: JSON.stringify({ title: "Preparar inventario", description: "Documentar el proceso de inventario." }),
    }));
  });

  it("sends final evidence bytes to the versioned storage endpoint", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true, status: 201, json: async () => ({ kind: "FINAL_REPORT", revision: 1 }),
    });
    vi.stubGlobal("fetch", fetchMock);
    const file = new File(["%PDF-1.7"], "informe final.pdf", { type: "application/pdf" });

    await submitCompletionEvidence(12, file);

    expect(fetchMock).toHaveBeenCalledWith(
      "/placements/12/completion-evidence/FINAL_REPORT?filename=informe+final.pdf",
      expect.objectContaining({
        method: "POST", credentials: "same-origin", body: file,
        headers: expect.objectContaining({ "Content-Type": "application/pdf" }),
      }),
    );
  });
});
