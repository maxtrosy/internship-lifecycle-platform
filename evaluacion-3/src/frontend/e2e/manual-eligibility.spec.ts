import { expect, test, type Page } from "@playwright/test";

const demoPassword = process.env.E2E_DEMO_PASSWORD ?? "Demo-Only-2026!";

async function login(page: Page, username: string) {
  await page.goto("/");
  await page.getByLabel("Correo electrónico o nombre de usuario").fill(username);
  await page.getByLabel("Contraseña").fill(demoPassword);
  await page.getByRole("button", { name: "Ingresar" }).click();
  await expect(page.getByRole("button", { name: "Cerrar sesión" })).toBeVisible();
}

async function logout(page: Page) {
  await page.getByRole("button", { name: "Cerrar sesión" }).click();
  await expect(page.getByLabel("Correo electrónico o nombre de usuario")).toBeVisible();
}

async function navigate(page: Page, label: string) {
  await page.locator(".sidebar-nav").getByRole("button", { name: label, exact: true }).click();
}

test("manual eligibility review waits for the related coordinator and persists the decision", async ({ page }) => {
  test.setTimeout(120_000);
  const title = `E2E manual review ${Date.now()}`;

  await login(page, "pc_sys");
  await navigate(page, "Políticas");
  await page.locator("#eligibility-programs").fill("");
  await page.locator("#eligibility-min-level").fill("");
  await page.locator("#eligibility-min-credits").fill("");
  await page.locator("#eligibility-prerequisites").fill("");
  await page.getByLabel("Motivo", { exact: false }).fill("Configuración de demostración sintética; revisión manual sin umbrales académicos inventados.");
  await page.getByLabel("Requiere decisión manual de coordinación antes de mostrar la postulación a la organización", { exact: true }).check();
  await page.getByRole("button", { name: "Crear versión de elegibilidad" }).click();
  await expect(page.locator(".alert.success")).toContainText("versión de política de Elegibilidad creada");
  const persistedPolicy = await page.evaluate(async () => {
    const programs = await (await fetch("/policies")).json();
    return programs.find((program: { code: string }) => program.code === "ING-SIS")?.policies?.ELIGIBILITY;
  });
  expect(persistedPolicy.conditions).toEqual([{ type: "MANUAL_REVIEW", value: true }]);
  expect(persistedPolicy.created_reason).toBe("Configuración de demostración sintética; revisión manual sin umbrales académicos inventados.");
  expect(persistedPolicy.created_by_name).toEqual(expect.any(String));
  await page.evaluate(() => window.scrollTo(0, 0));
  if (process.env.VISUAL_CAPTURE_DIR) {
    await page.screenshot({ path: `${process.env.VISUAL_CAPTURE_DIR}/policy-audit-desktop.png`, fullPage: true, animations: "disabled" });
  }
  await page.setViewportSize({ width: 390, height: 844 });
  await page.evaluate(() => window.scrollTo(0, 0));
  await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
  if (process.env.VISUAL_CAPTURE_DIR) {
    await page.screenshot({ path: `${process.env.VISUAL_CAPTURE_DIR}/policy-audit-mobile.png`, fullPage: true, animations: "disabled" });
  }
  await page.setViewportSize({ width: 1280, height: 900 });
  await logout(page);

  await login(page, "hm_alfa");
  await navigate(page, "Oportunidades");
  await page.locator("#opp-title").fill(title);
  await page.locator("#opp-org").selectOption({ label: "Org Alfa (synthetic)" });
  await page.locator("#opp-prog").selectOption({ label: "Systems Engineering (synthetic) · ING-SIS" });
  await page.getByRole("button", { name: "Guardar borrador" }).click();
  const draft = page.getByRole("row").filter({ hasText: title });
  await expect(draft).toContainText("Borrador");
  await draft.getByRole("button", { name: "Enviar a revisión" }).click();
  await expect(page.locator(".alert.success")).toContainText("Oportunidad enviada a revisión.");
  await logout(page);

  await login(page, "ec1");
  await navigate(page, "Oportunidades");
  const review = page.getByRole("row").filter({ hasText: title });
  await expect(review).toContainText("En revisión");
  await review.getByRole("button", { name: "Aprobar para publicación" }).click();
  const approved = page.getByRole("row").filter({ hasText: title });
  await approved.getByRole("button", { name: "Publicar oportunidad" }).click();
  await expect(page.locator(".alert.success")).toContainText("Oportunidad publicada.");
  await logout(page);

  await login(page, "s1");
  await navigate(page, "Oportunidades");
  const published = page.getByRole("row").filter({ hasText: title });
  await expect(published).toContainText("Publicada");
  await published.getByRole("button", { name: "Postular" }).click();
  await expect(page.locator(".alert.success")).toContainText("revisión académica pendiente");
  const applicationId = await page.evaluate(async (opportunityTitle) => {
    const rows = await (await fetch("/applications")).json();
    return rows.find((row: { title: string }) => row.title === opportunityTitle)?.id as number | undefined;
  }, title);
  expect(applicationId).toBeGreaterThan(0);
  await navigate(page, "Mis postulaciones");
  const applicationRow = page.getByRole("row").filter({ hasText: title });
  await expect(applicationRow).toContainText("Revisión académica pendiente");
  await page.reload();
  await navigate(page, "Mis postulaciones");
  await expect(page.getByRole("row").filter({ hasText: title })).toContainText("Revisión académica pendiente");
  await logout(page);

  await login(page, "hm_alfa");
  await navigate(page, "Oportunidades");
  await page.getByRole("row").filter({ hasText: title }).getByRole("button", { name: "Postulaciones" }).click();
  await expect(page.getByRole("heading", { name: `Postulaciones recibidas — ${title}` })).toBeVisible();
  await expect(page.getByText("No hay postulaciones.", { exact: true })).toBeVisible();
  await logout(page);

  await login(page, "pc_adm");
  const crossProgramQueue = await page.evaluate(async () => (await fetch("/applications/pending-eligibility-review")).json());
  expect(crossProgramQueue.some((row: { id: number }) => row.id === applicationId)).toBe(false);
  const crossProgramDecision = await page.evaluate(async (id) => (await fetch(`/applications/${id}/eligibility-review`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ decision: "ELIGIBLE", rationale: "cross-program attempt" }),
  })).status, applicationId);
  expect(crossProgramDecision).toBe(403);
  await logout(page);

  await login(page, "pc_sys");
  await navigate(page, "Revisión académica");
  const pending = page.getByRole("row").filter({ hasText: title });
  await expect(pending).toContainText("Student One");
  await expect(pending).toContainText("105 créditos");
  await expect(pending).toContainText(/Política v\d+/);
  const queueProjection = await page.evaluate(async (opportunityTitle) => {
    const queue = await (await fetch("/applications/pending-eligibility-review")).json();
    return queue.find((item: { opportunity_title: string }) => item.opportunity_title === opportunityTitle);
  }, title);
  expect(queueProjection).toHaveProperty("policy_version");
  expect(queueProjection).not.toHaveProperty("policy_version_id");
  await pending.getByLabel("Fundamento de la decisión").fill("Validación sintética registrada por coordinación.");
  await page.evaluate(() => window.scrollTo(0, 0));
  if (process.env.VISUAL_CAPTURE_DIR) {
    await page.screenshot({ path: `${process.env.VISUAL_CAPTURE_DIR}/eligibility-review-desktop.png`, fullPage: true, animations: "disabled" });
  }
  await page.setViewportSize({ width: 390, height: 844 });
  await page.evaluate(() => window.scrollTo(0, 0));
  await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
  if (process.env.VISUAL_CAPTURE_DIR) {
    await page.screenshot({ path: `${process.env.VISUAL_CAPTURE_DIR}/eligibility-review-mobile.png`, fullPage: true, animations: "disabled" });
  }
  await page.setViewportSize({ width: 1280, height: 900 });
  page.once("dialog", (dialog) => dialog.accept());
  await pending.getByRole("button", { name: "Marcar elegible" }).click();
  await expect(page.locator(".alert.success")).toContainText("Se registró la decisión académica");
  await logout(page);

  await login(page, "s1");
  await navigate(page, "Mis postulaciones");
  const decided = page.getByRole("row").filter({ hasText: title });
  await expect(decided).toContainText("Enviada");
  await expect(decided).toContainText("Decisión académica: Validación sintética registrada por coordinación.");
  const exposedReviewerId = await page.evaluate(async (opportunityTitle) => {
    const rows = await (await fetch("/applications")).json();
    const application = rows.find((row: { title: string }) => row.title === opportunityTitle);
    return application?.eligibility_result?.manual_review?.reviewed_by;
  }, title);
  expect(exposedReviewerId).toBeUndefined();
  await page.reload();
  await navigate(page, "Mis postulaciones");
  await expect(page.getByRole("row").filter({ hasText: title })).toContainText("Decisión académica: Validación sintética registrada por coordinación.");
});
