import { expect, test, type Page } from "@playwright/test";

const password = process.env.E2E_DEMO_PASSWORD ?? "Demo-Only-2026!";
const titleClosed = "Práctica sintética 01 · cierre-completo";
const titleIncident = "Práctica sintética 04 · activa-con-incidente-y-cambio";

async function login(page: Page, username: string) {
  // Each role check starts with a fresh browser cookie jar so an expired local
  // navigation state cannot leak the previous actor into the next assertion.
  await page.context().clearCookies();
  await page.goto("/#/login");
  await page.reload();
  await expect(page.getByLabel("Correo electrónico o nombre de usuario")).toBeVisible();
  await page.getByLabel("Correo electrónico o nombre de usuario").fill(username);
  await page.getByLabel("Contraseña").fill(password);
  await page.getByRole("button", { name: "Ingresar" }).click();
  await expect(page.getByRole("button", { name: "Cerrar sesión" })).toBeVisible();
}

async function openDossiers(page: Page) {
  await page.locator(".sidebar-nav").getByRole("button", { name: "Expedientes", exact: true }).click();
}

async function dossier(page: Page, placementId: string) {
  return page.evaluate(async (id) => {
    const response = await fetch(`/placements/${id}/dossier`);
    return { status: response.status, body: response.ok ? await response.json() : null };
  }, placementId);
}

test("[@populated] expediente cerrado mantiene documentos, relaciones, horas e historial tras recargar", async ({ page }) => {
  test.skip(!process.env.E2E_SCENARIO_CLOSED_USER, "Requiere el generador PostgreSQL aislado --populated.");
  const placementId = process.env.E2E_SCENARIO_CLOSED_ID!;
  await login(page, process.env.E2E_SCENARIO_CLOSED_USER!);

  const detail = await dossier(page, placementId);
  expect(detail.status).toBe(200);
  expect(detail.body.placement.state).toBe("CLOSED");
  expect(detail.body.application.state).toBe("SELECTED");
  expect(detail.body.opportunity.title).toBe(titleClosed);
  expect(detail.body.current_version.workplace_supervisor_name).toBe("Workplace Sup Alfa");
  expect(detail.body.responsibles.faculty_supervisors).toContain("Faculty Sup 1");
  expect(Number(detail.body.hours_total)).toBe(100);
  expect(detail.body.progress_reports.length).toBeGreaterThan(0);
  expect(detail.body.evaluations).toEqual(expect.arrayContaining([
    expect.objectContaining({ kind: "FINAL", evaluator: "Workplace Sup Alfa" }),
  ]));
  expect(detail.body.completion_evidence).toEqual(expect.arrayContaining([
    expect.objectContaining({ kind: "FINAL_REPORT", original_filename: "informe-final-sintetico.pdf", revision: 1 }),
  ]));
  expect(detail.body.work_plan.length).toBeGreaterThan(0);
  const insurance = detail.body.documents.find((item: { kind: string }) => item.kind === "DOC_INSURANCE");
  expect(insurance.versions).toEqual(expect.arrayContaining([
    expect.objectContaining({ original_filename: "synthetic-insurance.pdf", revision: 1, decision: "APPROVED" }),
  ]));
  const actions = detail.body.activity.map((event: { action: string }) => event.action);
  for (const action of ["placement.completed", "placement.closed", "evaluation.submitted",
    "completion_evidence.submitted", "work_plan.activity_assigned"]) {
    expect(actions).toContain(action);
  }

  await openDossiers(page);
  const closedDossier = page.locator(".dossier-detail").filter({ hasText: titleClosed });
  await expect(closedDossier.locator(".dossier-hero")).toContainText("Cerrada");
  await expect(closedDossier).toContainText("synthetic-insurance.pdf · versión 1");
  await expect(closedDossier).toContainText("Evaluación final · versión 1");
  await expect(closedDossier.locator(".dossier-hours-summary")).toContainText("100 h");
  await expect(closedDossier).toContainText("Actividad del ciclo de vida");
  await page.screenshot({ path: process.env.E2E_POPULATED_DESKTOP_SCREENSHOT, fullPage: true, animations: "disabled" });
  await page.getByLabel("Apariencia").selectOption("dark");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await expect.poll(() => page.evaluate(() => getComputedStyle(document.body).backgroundColor)).toBe("rgb(17, 26, 24)");
  await page.screenshot({ path: process.env.E2E_POPULATED_DARK_DESKTOP_SCREENSHOT, fullPage: true, animations: "disabled" });

  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await openDossiers(page);
  const afterReload = page.locator(".dossier-detail").filter({ hasText: titleClosed });
  await expect(afterReload.locator(".dossier-hero")).toContainText("Cerrada");
  await expect(afterReload).toContainText("synthetic-insurance.pdf · versión 1");
  await expect(afterReload.locator(".placement-history-list")).toContainText("Práctica cerrada");
  await page.setViewportSize({ width: 390, height: 844 });
  await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
  await page.getByLabel("Apariencia").selectOption("light");
  await page.screenshot({ path: process.env.E2E_POPULATED_MOBILE_SCREENSHOT, fullPage: true, animations: "disabled" });
  await page.getByLabel("Apariencia").selectOption("dark");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.screenshot({ path: process.env.E2E_POPULATED_DARK_MOBILE_SCREENSHOT, fullPage: true, animations: "disabled" });
});

test("[@populated] aprobación, documentos faltantes, revisión jurídica y corrección conservan sus estados", async ({ page }) => {
  test.skip(!process.env.E2E_SCENARIO_MISSING_USER, "Requiere el generador PostgreSQL aislado --populated.");

  await login(page, process.env.E2E_SCENARIO_MISSING_USER!);
  const missing = await dossier(page, process.env.E2E_SCENARIO_MISSING_ID!);
  expect(missing.body.placement.state).toBe("DOCUMENTATION_PENDING");
  expect(missing.body.documents.find((item: { kind: string }) => item.kind === "DOC_INSURANCE").status).toBe("REQUIRED");
  await openDossiers(page);
  const missingCard = page.locator(".dossier-detail").filter({ hasText: "Práctica sintética 07 · documentacion-pendiente" });
  await expect(missingCard).toContainText("Seguro");
  await expect(missingCard).toContainText("Pendiente");

  await login(page, "ec1");
  const activateMissing = await page.evaluate(async (id) => {
    const response = await fetch(`/placements/${id}/activate`, { method: "POST" });
    return { status: response.status, body: await response.json() };
  }, process.env.E2E_SCENARIO_MISSING_ID!);
  expect(activateMissing.status).toBe(409);
  expect((await dossier(page, process.env.E2E_SCENARIO_MISSING_ID!)).body.placement.state).toBe("DOCUMENTATION_PENDING");

  await login(page, process.env.E2E_SCENARIO_REVIEW_USER!);
  const pendingReview = await dossier(page, process.env.E2E_SCENARIO_REVIEW_ID!);
  const pendingInsurance = pendingReview.body.documents.find((item: { kind: string }) => item.kind === "DOC_INSURANCE");
  expect(pendingReview.body.placement.state).toBe("DOCUMENTATION_PENDING");
  expect(pendingInsurance.versions).toEqual(expect.arrayContaining([
    expect.objectContaining({ revision: 1, decision: null }),
  ]));

  await login(page, process.env.E2E_SCENARIO_CORRECTION_USER!);
  const correction = await dossier(page, process.env.E2E_SCENARIO_CORRECTION_ID!);
  const correctionInsurance = correction.body.documents.find((item: { kind: string }) => item.kind === "DOC_INSURANCE");
  expect(correction.body.placement.state).toBe("DOCUMENTATION_PENDING");
  expect(correctionInsurance.versions).toEqual(expect.arrayContaining([
    expect.objectContaining({ revision: 1, decision: "REJECTED" }),
    expect.objectContaining({ revision: 2, decision: null }),
  ]));

  await login(page, process.env.E2E_SCENARIO_PENDING_USER!);
  const pendingAcademic = await dossier(page, process.env.E2E_SCENARIO_PENDING_ID!);
  expect(pendingAcademic.body.placement.state).toBe("PENDING_ACADEMIC_APPROVAL");
  expect(pendingAcademic.body.placement.activation_requirements_instantiated).toBe(false);
  await login(page, "ec1");
  const prematureActivation = await page.evaluate(async (id) => (
    await fetch(`/placements/${id}/activate`, { method: "POST" })
  ).status, process.env.E2E_SCENARIO_PENDING_ID!);
  expect(prematureActivation).toBe(409);
});

test("[@populated] seguimiento e incidente/cambio no habilitan un cierre incompleto", async ({ page }) => {
  test.skip(!process.env.E2E_SCENARIO_INCIDENT_USER, "Requiere el generador PostgreSQL aislado --populated.");
  const placementId = process.env.E2E_SCENARIO_INCIDENT_ID!;
  await login(page, process.env.E2E_SCENARIO_INCIDENT_USER!);
  const initial = await dossier(page, placementId);
  expect(initial.body.placement.state).toBe("ACTIVE");
  expect(initial.body.progress_reports.length).toBeGreaterThan(0);
  expect(initial.body.incidents.map((entry: { kind: string }) => entry.kind)).toEqual(expect.arrayContaining(["INCIDENT", "CHANGE"]));
  expect(initial.body.incidents.every((entry: { status: string }) => entry.status === "REPORTED")).toBe(true);
  const historyActions = initial.body.activity.map((event: { action: string }) => event.action);
  expect(historyActions).toContain("placement.incident_reported");
  expect(historyActions).toContain("placement.change_reported");

  await openDossiers(page);
  const incidentDossier = page.locator(".dossier-detail").filter({ hasText: titleIncident });
  await expect(incidentDossier).toContainText("Consulta sobre acceso al espacio de trabajo");
  await expect(incidentDossier).toContainText("Ajuste de responsabilidades solicitado");
  await expect(incidentDossier).toContainText("Reportado");
  await page.reload();
  await openDossiers(page);
  await expect(page.locator(".dossier-detail").filter({ hasText: titleIncident })).toContainText("Ajuste de responsabilidades solicitado");

  await login(page, "pc_adm");
  const closeWithoutEvidence = await page.evaluate(async (id) => {
    const response = await fetch(`/placements/${id}/confirm-completion`, { method: "POST" });
    return { status: response.status, body: await response.json() };
  }, placementId);
  expect(closeWithoutEvidence.status).toBe(409);
  expect((await dossier(page, placementId)).body.placement.state).toBe("ACTIVE");
});

test("[@populated] cada consulta conserva alcance por organización, programa y supervisión", async ({ page }) => {
  test.skip(!process.env.E2E_SCENARIO_ACTIVE_USER, "Requiere el generador PostgreSQL aislado --populated.");
  const placementId = process.env.E2E_SCENARIO_ACTIVE_ID!;

  await login(page, process.env.E2E_SCENARIO_ACTIVE_USER!);
  const student = await dossier(page, placementId);
  expect(student.status).toBe(200);
  expect(student.body.placement.state).toBe("ACTIVE");
  expect(student.body.work_plan.length).toBeGreaterThan(0);
  expect(student.body.progress_reports.length).toBeGreaterThan(0);
  await page.locator(".sidebar-nav").getByRole("button", { name: "Notificaciones", exact: true }).click();
  const inbox = await page.evaluate(async () => (await fetch("/notifications")).json());
  expect(inbox.some((notice: { category: string; placement_id: number | null }) =>
    notice.category === "APPLICATION_SELECTED" && notice.placement_id === Number(placementId))).toBe(true);
  await page.reload();
  expect((await dossier(page, placementId)).body.progress_reports.length).toBeGreaterThan(0);

  await login(page, "demo_host_01");
  const host = await dossier(page, placementId);
  expect(host.status).toBe(200);
  expect(Object.keys(host.body.student).sort()).toEqual(["display_name", "program_code"]);
  expect(host.body.hours).toBeNull();
  expect(host.body.evaluations).toBeNull();
  expect(await page.evaluate(async (id) => (
    await fetch(`/placements/${id}/hours`, { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ hours: 1 }) })
  ).status, placementId)).toBe(403);

  await login(page, "demo_supervisor_01");
  const workplaceSupervisor = await dossier(page, placementId);
  expect(workplaceSupervisor.status).toBe(200);
  expect(workplaceSupervisor.body.work_plan.length).toBeGreaterThan(0);
  expect(workplaceSupervisor.body.progress_reports.length).toBeGreaterThan(0);
  expect(workplaceSupervisor.body.hours).toBeNull();
  expect(await page.evaluate(async (id) => (
    await fetch(`/placements/${id}/messages?audience=ACADEMIC`)
  ).status, placementId)).toBe(403);

  await login(page, "demo_faculty_02");
  expect((await dossier(page, placementId)).status).toBe(200);

  await login(page, "pc_sys");
  expect((await dossier(page, placementId)).status).toBe(200);
  expect(await page.evaluate(async (id) => (
    await fetch(`/placements/${id}/faculty-supervisors`)
  ).status, placementId)).toBe(200);

  await login(page, "pc_adm");
  expect((await dossier(page, placementId)).status).toBe(403);

  await login(page, "hm_beta");
  expect((await dossier(page, placementId)).status).toBe(404);

  await login(page, "ws_beta");
  expect((await dossier(page, placementId)).status).toBe(404);

  await login(page, "s2");
  expect((await dossier(page, placementId)).status).toBe(403);

  await login(page, "legal1");
  const legal = await dossier(page, placementId);
  expect(legal.status).toBe(200);
  expect(legal.body.documents).not.toBeNull();
  expect(legal.body.hours).toBeNull();

  await login(page, "ec1");
  expect((await dossier(page, placementId)).status).toBe(200);
});
