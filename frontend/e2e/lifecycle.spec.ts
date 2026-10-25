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

test("login errors and protected student routes stay scoped", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Correo electrónico o nombre de usuario").fill("s1");
  await page.getByLabel("Contraseña").fill("incorrecta");
  await page.getByRole("button", { name: "Ingresar" }).click();
  await expect(page.getByRole("alert")).toHaveText("El correo/usuario o la contraseña no son correctos.");

  await page.getByLabel("Contraseña").fill(demoPassword);
  await page.getByRole("button", { name: "Ingresar" }).click();
  await expect(page.getByRole("button", { name: "Cerrar sesión" })).toBeVisible();
  await page.goto("/#/activation");
  await expect(page).toHaveURL(/#\/home$/);

  const responseStatus = await page.evaluate(async () => (await fetch("/placements/pending-activation")).status);
  expect(responseStatus).toBe(403);
});

test("student, employer, coordinator, legal reviewer and experiential coordinator complete the lifecycle", async ({ page }) => {
  test.setTimeout(120_000);
  const opportunityTitle = `E2E Internship ${Date.now()}`;

  // Configure policies through the coordinator's authorized UI before creating an application.
  await login(page, "pc_sys");
  await navigate(page, "Políticas");
  const eligibilityCard = page.locator(".policy-card").filter({ hasText: "Elegibilidad" }).first();
  await eligibilityCard.locator('input[type="number"]').nth(1).fill("100");
  await page.getByRole("button", { name: "Crear versión de elegibilidad" }).click();
  await expect(page.locator(".alert.success")).toContainText("versión de política de Elegibilidad creada");
  await page.getByLabel("Exigir supervisor del lugar asignado").uncheck();
  await page.getByRole("button", { name: "Crear versión de activación" }).click();
  await expect(page.locator(".alert.success")).toContainText("versión de política de Activación creada");
  await logout(page);

  // Employer creates the opportunity; a student applies and can inspect the legible result.
  await login(page, "hm_alfa");
  await navigate(page, "Oportunidades");
  await page.locator("#opp-title").fill(opportunityTitle);
  await page.locator("#opp-org").fill("1");
  await page.locator("#opp-prog").fill("1");
  await page.getByRole("button", { name: "Publicar" }).click();
  await expect(page.locator(".alert.success")).toContainText("Oportunidad creada y publicada.");
  await logout(page);

  await login(page, "s1");
  await navigate(page, "Oportunidades");
  const opportunityRow = page.getByRole("row").filter({ hasText: opportunityTitle });
  await opportunityRow.getByRole("button", { name: "Postular" }).click();
  await expect(page.locator(".alert.success")).toContainText("Resultado de elegibilidad: elegible.");
  await navigate(page, "Mis postulaciones");
  await expect(page.locator(".applications-table")).toContainText("Elegible");
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await logout(page);

  // Employer can see its own application and select the eligible candidate.
  await page.setViewportSize({ width: 1280, height: 900 });
  await login(page, "hm_alfa");
  await navigate(page, "Oportunidades");
  await page.getByRole("row").filter({ hasText: opportunityTitle })
    .getByRole("button", { name: "Postulaciones" }).click();
  await expect(page.getByText("Student One", { exact: true })).toBeVisible();
  const receivedRow = page.getByRole("row").filter({ hasText: "Student One" });
  await receivedRow.getByRole("button", { name: "Seleccionar" }).click();
  await receivedRow.locator('input[type="date"]').nth(0).fill("2026-11-02");
  await receivedRow.locator('input[type="date"]').nth(1).fill("2027-02-26");
  await receivedRow.locator(".field").filter({ hasText: "Ubicación" }).locator("input").fill("Sede de demostración");
  await receivedRow.locator("textarea").fill("Actividades sintéticas de demostración.");
  page.once("dialog", (dialog) => dialog.accept());
  await receivedRow.getByRole("button", { name: "Confirmar" }).click();
  await expect(page.locator(".alert.success")).toContainText("pendiente de aprobación académica");
  await logout(page);

  // Coordinator approves; student uploads; legal reviewer rejects with a reason.
  await login(page, "pc_sys");
  await navigate(page, "Revisión académica");
  const pendingRow = page.getByRole("row").filter({ hasText: opportunityTitle });
  await expect(pendingRow).toContainText("Student One");
  page.once("dialog", (dialog) => dialog.accept());
  await pendingRow.getByRole("button", { name: "Aprobar" }).click();
  await expect(page.locator(".alert.success")).toContainText("Se aprobó la selección");
  await logout(page);

  await login(page, "s1");
  await navigate(page, "Mis documentos");
  const insuranceRow = page.getByRole("row").filter({ hasText: "Seguro" });
  await insuranceRow.getByLabel("Archivo para Seguro").setInputFiles({
    name: "insurance.pdf", mimeType: "application/pdf", buffer: Buffer.from("%PDF-1.7 synthetic insurance"),
  });
  await insuranceRow.getByRole("button", { name: "Enviar" }).click();
  await expect(page.locator(".alert.success")).toContainText("versión 1");
  await logout(page);

  await login(page, "legal1");
  await navigate(page, "Revisión documental");
  const legalCard = page.locator(".document-review-card").filter({ hasText: opportunityTitle });
  await legalCard.getByRole("button", { name: "Ver documentos" }).click();
  const legalRow = legalCard.getByRole("row").filter({ hasText: "Seguro" });
  await legalRow.getByLabel("Motivo para Seguro").fill("El archivo de prueba requiere corrección.");
  page.once("dialog", (dialog) => dialog.accept());
  await legalRow.getByRole("button", { name: "Rechazar" }).click();
  await expect(page.locator(".alert.success")).toContainText("rechazado con motivo registrado");
  await logout(page);

  // Student re-submits the rejected item; legal approves the next revision.
  await login(page, "s1");
  await navigate(page, "Mis documentos");
  const rejectedRow = page.getByRole("row").filter({ hasText: "Seguro" });
  await expect(rejectedRow).toContainText("Rechazado");
  await rejectedRow.getByLabel("Archivo para Seguro").setInputFiles({
    name: "insurance-corrected.pdf", mimeType: "application/pdf", buffer: Buffer.from("%PDF-1.7 corrected"),
  });
  await rejectedRow.getByRole("button", { name: "Reenviar" }).click();
  await expect(page.locator(".alert.success")).toContainText("versión 2");
  await logout(page);

  await login(page, "legal1");
  await navigate(page, "Revisión documental");
  const approvedCard = page.locator(".document-review-card").filter({ hasText: opportunityTitle });
  await approvedCard.getByRole("button", { name: "Ver documentos" }).click();
  const submittedRow = approvedCard.getByRole("row").filter({ hasText: "Seguro" });
  await submittedRow.getByLabel("Motivo para Seguro").fill("La nueva versión es legible para esta demostración.");
  page.once("dialog", (dialog) => dialog.accept());
  await submittedRow.getByRole("button", { name: "Aprobar" }).click();
  await expect(page.locator(".alert.success")).toContainText("Documento aprobado.");
  await logout(page);

  // Only the experiential coordinator can activate after backend gates pass.
  await login(page, "ec1");
  await navigate(page, "Activación");
  const activationCard = page.locator(".activation-card").filter({ hasText: opportunityTitle });
  await expect(activationCard.getByRole("button", { name: "Activar" })).toBeEnabled();
  page.once("dialog", (dialog) => dialog.accept());
  await activationCard.getByRole("button", { name: "Activar" }).click();
  await expect(page.locator(".alert.success")).toContainText("fue activada");
  await logout(page);

  await login(page, "s1");
  await navigate(page, "Mis postulaciones");
  await expect(page.locator(".applications-table")).toContainText("Activa");
});
