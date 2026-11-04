import { expect, test, type Page } from "@playwright/test";

const demoPassword = process.env.E2E_DEMO_PASSWORD ?? "Demo-Only-2026!";

test("the local demo route signs in to each synthetic account with one click", async ({ page }) => {
  test.setTimeout(120_000);
  const accountNames = [
    "Student One", "Student Two", "Student Three",
    "Host Member Alfa", "Host Member Beta", "Coord Sys", "Coord Adm",
    "Experiential Coord 1", "Legal Reviewer", "Workplace Sup Alfa",
    "Workplace Sup Alfa 2", "Workplace Sup Beta", "Faculty Sup 1",
    "Dual Coordinator/Faculty",
  ];

  for (const name of accountNames) {
    await page.goto("/#/demo-login");
    const accountName = page.getByText(name, { exact: true });
    await page.locator(".demo-account-card").filter({ has: accountName }).click();
    await expect(page.getByRole("button", { name: "Cerrar sesión" })).toBeVisible();
    await expect(page.getByText(name, { exact: true })).toBeVisible();
    await page.getByRole("button", { name: "Cerrar sesión" }).click();
    await expect(page.getByLabel("Correo electrónico o nombre de usuario")).toBeVisible();
  }
});

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

async function dossierResponse(page: Page, placementId: number) {
  return page.evaluate(async (id) => {
    const response = await fetch(`/placements/${id}/dossier`);
    return { status: response.status, body: response.ok ? await response.json() : null };
  }, placementId);
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

test("assigned faculty, program and legal roles reach the isolated practice fixture", async ({ page }) => {
  const opportunityTitle = "E2E faculty assigned practice";

  await login(page, "f1");
  await expect(page.locator(".dashboard-related-placements")).toContainText(opportunityTitle);
  const facultyPlacements = await page.evaluate(async () => (await fetch("/placements")).json());
  const facultyPlacement = facultyPlacements.find((row: { opportunity_title: string }) =>
    row.opportunity_title === opportunityTitle);
  expect(facultyPlacement?.id).toBeGreaterThan(0);
  await navigate(page, "Expedientes");
  const facultyDossier = page.locator(".dossier-detail").filter({ hasText: opportunityTitle });
  await expect(facultyDossier.locator(".dossier-hero")).toContainText("Activa");
  const facultyProjection = await dossierResponse(page, facultyPlacement.id);
  expect(facultyProjection.status).toBe(200);
  expect(facultyProjection.body.capabilities.read_progress_reports).toBe(true);
  expect(facultyProjection.body.responsibles.faculty_supervisors).toContain("Faculty Sup 1");
  const academicMessage = `Academic message persisted ${Date.now()}`;
  await facultyDossier.getByRole("tab", { name: "Académico" }).click();
  await facultyDossier.getByLabel("Mensaje de la práctica").fill(academicMessage);
  await facultyDossier.getByRole("button", { name: "Enviar mensaje" }).click();
  await expect(facultyDossier.locator('.message-list[aria-label="Historial de mensajes"]')).toContainText(academicMessage);
  await page.reload();
  const reloadedFacultyDossier = page.locator(".dossier-detail").filter({ hasText: opportunityTitle });
  await expect(reloadedFacultyDossier.locator(".dossier-hero")).toContainText("Activa");
  await reloadedFacultyDossier.getByRole("tab", { name: "Académico" }).click();
  await expect(reloadedFacultyDossier.locator('.message-list[aria-label="Historial de mensajes"]')).toContainText(academicMessage);
  await logout(page);

  // This multi-role account has neither the fixture's ADM program relationship nor
  // the faculty assignment; same-role membership alone must not expose it.
  await login(page, "dual1");
  expect((await dossierResponse(page, facultyPlacement.id)).status).toBe(403);
  const crossedConversation = await page.evaluate(async (id) => (
    await fetch(`/placements/${id}/messages?audience=ACADEMIC`)
  ).status, facultyPlacement.id);
  expect(crossedConversation).toBe(403);
  const unrelatedPlacements = await page.evaluate(async () => (await fetch("/placements")).json());
  expect(unrelatedPlacements.some((row: { id: number }) => row.id === facultyPlacement.id)).toBe(false);
  await logout(page);

  await login(page, "pc_adm");
  await expect(page.locator(".dashboard-related-placements")).toContainText(opportunityTitle);
  let failOperationalReportsUntilRetry = true;
  let operationalReportFailures = 0;
  await page.route((url) => new URL(url).pathname === "/reports/operations", async (route) => {
    if (failOperationalReportsUntilRetry) {
      operationalReportFailures += 1;
      await route.fulfill({
        status: 503,
        contentType: "application/json",
        body: JSON.stringify({ detail: "temporary test failure" }),
      });
      return;
    }
    await route.continue();
  });
  await navigate(page, "Reportes operativos");
  await expect(page.getByRole("alert")).toContainText("No se pudo completar la solicitud");
  expect(operationalReportFailures).toBeGreaterThan(0);
  await expect(page.locator(".report-metrics")).toHaveCount(0);
  const operationalReportsRetry = page.waitForResponse((response) =>
    response.url().includes("/reports/operations") && response.status() === 200,
  );
  failOperationalReportsUntilRetry = false;
  await page.getByRole("button", { name: "Reintentar" }).click();
  await operationalReportsRetry;
  await expect(page.locator(".report-metrics .bento-metric").filter({ hasText: "Prácticas activas" }).locator(".metric-value")).toHaveText("1");
  await expect(page.locator(".report-tables")).toContainText("Business Admin");
  expect(await page.locator(".reports-page").innerText()).not.toContain("Student Three");
  const reportTableWrappers = page.locator(".report-table-wrap");
  await expect(reportTableWrappers).toHaveCount(4);
  expect(await reportTableWrappers.evaluateAll((elements) =>
    elements.every((element) => element.scrollWidth <= element.clientWidth),
  )).toBe(true);
  await page.screenshot({ path: process.env.E2E_REPORTS_DESKTOP_SCREENSHOT, fullPage: true, animations: "disabled" });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
  expect(await reportTableWrappers.evaluateAll((elements) =>
    elements.every((element) => element.scrollWidth <= element.clientWidth),
  )).toBe(true);
  await page.screenshot({ path: process.env.E2E_REPORTS_MOBILE_SCREENSHOT, fullPage: true, animations: "disabled" });
  await page.setViewportSize({ width: 1280, height: 900 });
  await navigate(page, "Expedientes");
  const coordinatorDossier = page.locator(".dossier-detail").filter({ hasText: opportunityTitle });
  await expect(coordinatorDossier).toContainText("Student Three");
  const assignmentPanel = coordinatorDossier.locator(".faculty-assignment-panel");
  await expect(assignmentPanel).toContainText("Faculty Sup 1");
  await assignmentPanel.getByRole("button", { name: "Retirar asignación" }).click();
  await expect(assignmentPanel.locator(".faculty-assignment-history")).toContainText("Asignación retirada");
  await expect(assignmentPanel.locator(".faculty-assignment-row")).toHaveCount(0);
  await assignmentPanel.getByLabel("Asignar supervisión docente").selectOption({ label: "Faculty Sup 1" });
  await assignmentPanel.getByRole("button", { name: "Asignar" }).click();
  await expect(assignmentPanel.locator(".faculty-assignment-row")).toContainText("Faculty Sup 1");
  await expect(assignmentPanel.locator(".faculty-assignment-history")).toContainText("Asignación registrada");
  await logout(page);

  await login(page, "s3");
  await navigate(page, "Notificaciones");
  const messageNotice = page.locator(".notification-item").filter({ hasText: "Hay un nuevo mensaje en una conversación de práctica" });
  await expect(messageNotice).toBeVisible();
  await messageNotice.getByRole("button", { name: "Abrir expediente" }).click();
  const studentDossier = page.locator(".dossier-detail").filter({ hasText: opportunityTitle });
  await expect(studentDossier.locator(".dossier-hero")).toContainText("Activa");
  await studentDossier.getByRole("tab", { name: "Académico" }).click();
  await expect(studentDossier.locator('.message-list[aria-label="Historial de mensajes"]')).toContainText(academicMessage);
  const inboxAfterReload = await page.evaluate(async () => (await fetch("/notifications")).json());
  expect(inboxAfterReload.some((notice: { category: string; is_read: boolean }) =>
    notice.category === "MESSAGE_RECEIVED" && notice.is_read)).toBe(true);
  await logout(page);

  await login(page, "ws_alfa");
  const supervisorAcademicStatus = await page.evaluate(async (id) => (
    await fetch(`/placements/${id}/messages?audience=ACADEMIC`)
  ).status, facultyPlacement.id);
  expect(supervisorAcademicStatus).toBe(403);
  const supervisorJoint = await page.evaluate(async (id) => {
    const response = await fetch(`/placements/${id}/messages?audience=JOINT`);
    return { status: response.status, body: response.ok ? await response.json() : null };
  }, facultyPlacement.id);
  expect(supervisorJoint.status).toBe(200);
  const workplaceAssignmentStatus = await page.evaluate(async (id) => {
    const me = await (await fetch("/auth/me")).json();
    return (await fetch(`/placements/${id}/faculty-supervisors`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: me.id }),
    })).status;
  }, facultyPlacement.id);
  expect(workplaceAssignmentStatus).toBe(403);
  await logout(page);

  await login(page, "hm_alfa");
  const employerReportsStatus = await page.evaluate(async () => (await fetch("/reports/operations")).status);
  expect(employerReportsStatus).toBe(403);
  await logout(page);

  await login(page, "legal1");
  await navigate(page, "Expedientes");
  const legalDossier = page.locator(".dossier-detail").filter({ hasText: opportunityTitle });
  await expect(legalDossier.locator(".dossier-hero")).toContainText("Activa");
  const legalProjection = await dossierResponse(page, facultyPlacement.id);
  expect(legalProjection.status).toBe(200);
  expect(legalProjection.body.capabilities.read_documents).toBe(true);
  expect(legalProjection.body.hours).toBeNull();
});

test("student, employer, coordinator, legal reviewer and experiential coordinator complete the lifecycle", async ({ page }) => {
  test.setTimeout(240_000);
  const opportunityTitle = `E2E Internship ${Date.now()}`;
  let placementId = 0;

  // Configure policies through the coordinator's authorized UI before creating an application.
  await login(page, "pc_sys");
  await navigate(page, "Políticas");
  await expect(page.locator(".policy-program")).toContainText("cierre v1");
  const eligibilityCard = page.locator(".policy-card").filter({ hasText: "Elegibilidad" }).first();
  const minimumCredits = eligibilityCard.getByLabel("Créditos mínimos");
  await minimumCredits.fill("100");
  await expect(minimumCredits).toHaveValue("100");
  await page.getByRole("button", { name: "Crear versión de elegibilidad" }).click();
  await expect(page.locator(".alert.success")).toContainText("versión de política de Elegibilidad creada");
  await page.getByLabel("Exigir supervisor del lugar asignado").uncheck();
  await page.getByRole("button", { name: "Crear versión de activación" }).click();
  await expect(page.locator(".alert.success")).toContainText("versión de política de Activación creada");
  await logout(page);

  // The host creates a draft and submits it; the explicitly configured institutional actor reviews and publishes.
  await login(page, "hm_alfa");
  await navigate(page, "Oportunidades");
  await page.locator("#opp-title").fill(opportunityTitle);
  const organizationField = page.locator("#opp-org");
  if (await organizationField.getAttribute("type") === "hidden") {
    await expect(organizationField).toHaveValue("1");
  } else {
    await expect(organizationField).toContainText("Org Alfa (synthetic)");
    await organizationField.selectOption("1");
  }
  const programField = page.locator("#opp-prog");
  if (await programField.getAttribute("type") === "number") {
    await programField.fill("1");
  } else {
    await expect(programField).toContainText("Systems Engineering (synthetic) · ING-SIS");
    await programField.selectOption("1");
  }
  await page.getByRole("button", { name: "Guardar borrador" }).click();
  await expect(page.locator(".alert.success")).toContainText("Borrador guardado.");
  const draftRow = page.getByRole("row").filter({ hasText: opportunityTitle });
  await expect(draftRow).toContainText("Borrador");
  await draftRow.getByRole("button", { name: "Enviar a revisión" }).click();
  await expect(page.locator(".alert.success")).toContainText("Oportunidad enviada a revisión.");
  const hostApprovalStatus = await page.evaluate(async (title) => {
    const opportunities = await (await fetch("/opportunities")).json();
    const item = opportunities.find((row: { title: string }) => row.title === title);
    return item ? (await fetch(`/opportunities/${item.id}/approve`, { method: "POST" })).status : 0;
  }, opportunityTitle);
  expect(hostApprovalStatus).toBe(403);
  await logout(page);

  await login(page, "ec1");
  await navigate(page, "Oportunidades");
  const reviewRow = page.getByRole("row").filter({ hasText: opportunityTitle });
  await expect(reviewRow).toContainText("En revisión");
  await reviewRow.getByRole("button", { name: "Aprobar para publicación" }).click();
  await expect(page.locator(".alert.success")).toContainText("Oportunidad aprobada para publicación.");
  const approvedRow = page.getByRole("row").filter({ hasText: opportunityTitle });
  await expect(approvedRow).toContainText("Aprobada");
  await approvedRow.getByRole("button", { name: "Publicar oportunidad" }).click();
  await expect(page.locator(".alert.success")).toContainText("Oportunidad publicada.");
  await logout(page);

  await login(page, "s1");
  await navigate(page, "Notificaciones");
  const publicationNotice = page.locator(".notification-item").filter({
    hasText: "Hay una nueva oportunidad publicada en tu programa",
  });
  await expect(publicationNotice).toBeVisible();
  await expect(publicationNotice).toContainText("Sin leer");
  await publicationNotice.getByRole("button", { name: "Abrir oportunidad" }).click();
  await expect(page).toHaveURL(/#\/opportunities$/);
  await navigate(page, "Notificaciones");
  await expect(page.locator(".notification-item").filter({ hasText: "Hay una nueva oportunidad publicada en tu programa" })).toContainText("Leída");
  await page.locator(".notification-item").filter({ hasText: "Hay una nueva oportunidad publicada en tu programa" })
    .getByRole("button", { name: "Abrir oportunidad" }).click();
  await expect(page.locator("#opportunity-search")).toHaveValue(opportunityTitle);
  await navigate(page, "Oportunidades");
  const opportunityRow = page.getByRole("row").filter({ hasText: opportunityTitle });
  await opportunityRow.getByRole("button", { name: "Postular" }).click();
  await expect(page.locator(".alert.success")).toContainText("Resultado de elegibilidad: elegible.");
  await navigate(page, "Mis postulaciones");
  await expect(page.locator(".applications-table")).toContainText("Elegible");
  await navigate(page, "Inicio");
  await expect(page.locator(".dashboard-hero")).toContainText("Tu postulación fue enviada");
  if (process.env.E2E_STUDENT_DASHBOARD_DESKTOP_SCREENSHOT) {
    await page.screenshot({ path: process.env.E2E_STUDENT_DASHBOARD_DESKTOP_SCREENSHOT, fullPage: true, animations: "disabled" });
  }
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  if (process.env.E2E_STUDENT_DASHBOARD_MOBILE_SCREENSHOT) {
    await page.screenshot({ path: process.env.E2E_STUDENT_DASHBOARD_MOBILE_SCREENSHOT, fullPage: true, animations: "disabled" });
  }
  await page.setViewportSize({ width: 1280, height: 900 });
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
  const supervisorField = receivedRow.getByLabel("Supervisor laboral asignado (opcional)");
  await expect(supervisorField).toContainText("Workplace Sup Alfa");
  await supervisorField.selectOption({ label: "Workplace Sup Alfa" });
  await receivedRow.locator('input[type="date"]').nth(0).fill("2026-11-02");
  await receivedRow.locator('input[type="date"]').nth(1).fill("2027-02-26");
  await receivedRow.locator(".field").filter({ hasText: "Ubicación" }).locator("input").fill("Sede de demostración");
  await receivedRow.locator("textarea").fill("Actividades sintéticas de demostración.");
  page.once("dialog", (dialog) => dialog.accept());
  await receivedRow.getByRole("button", { name: "Confirmar" }).click();
  await expect(page.locator(".alert.success")).toContainText("pendiente de aprobación académica");
  await navigate(page, "Expedientes");
  const employerDossier = page.locator(".dossier-detail").filter({ hasText: opportunityTitle });
  await expect(employerDossier).toContainText("Pendiente de aprobación académica");
  await expect(employerDossier).toContainText("Workplace Sup Alfa");
  await expect(employerDossier.getByRole("button", { name: "Gestionar mis documentos y horas" })).toHaveCount(0);
  await expect(employerDossier.getByText("Los archivos y el historial de versiones se muestran únicamente", { exact: false })).toBeVisible();
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
  const studentPlacement = page.locator(".document-placement").filter({ hasText: opportunityTitle });
  const insuranceRow = studentPlacement.getByRole("row").filter({ hasText: "Seguro" });
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
  const rejectedPlacement = page.locator(".document-placement").filter({ hasText: opportunityTitle });
  const rejectedRow = rejectedPlacement.getByRole("row").filter({ hasText: "Seguro" });
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
  const visiblePlacements = await page.evaluate(async () => (await fetch("/placements")).json());
  placementId = visiblePlacements.find((row: { opportunity_title: string }) => row.opportunity_title === opportunityTitle)?.id ?? 0;
  expect(placementId).toBeGreaterThan(0);
  await navigate(page, "Mis documentos");
  const activePlacement = page.locator(".document-placement").filter({ hasText: opportunityTitle });
  await activePlacement.getByLabel("Horas realizadas").fill("4.5");
  await activePlacement.getByRole("button", { name: "Registrar horas" }).click();
  await expect(activePlacement.locator(".metric-value")).toHaveText("4.5 h");
  await expect(activePlacement.locator(".work-log-list")).toContainText("4.5 h");
  await page.reload();
  const persistedPlacement = page.locator(".document-placement").filter({ hasText: opportunityTitle });
  await expect(persistedPlacement.locator(".metric-value")).toHaveText("4.5 h");
  await persistedPlacement.getByRole("button", { name: "Ver actividad de la práctica" }).click();
  await expect(persistedPlacement.getByText("Práctica activada", { exact: true })).toBeVisible();
  await expect(persistedPlacement.getByText("Horas registradas", { exact: true })).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.setViewportSize({ width: 1280, height: 900 });
  if (process.env.E2E_SCREENSHOT_PATH) {
    await page.screenshot({ path: process.env.E2E_SCREENSHOT_PATH, fullPage: true, animations: "disabled" });
  }
  await page.reload();
  const reloadedPlacement = page.locator(".document-placement").filter({ hasText: opportunityTitle });
  await expect(reloadedPlacement.locator(".metric-value")).toHaveText("4.5 h");
  await reloadedPlacement.getByRole("button", { name: "Ver actividad de la práctica" }).click();
  await expect(reloadedPlacement.getByText("Práctica activada", { exact: true })).toBeVisible();
  await expect(reloadedPlacement.getByText("Horas registradas", { exact: true })).toBeVisible();

  // The integrated dossier combines the persisted opportunity, application, revisions, hours and history.
  await navigate(page, "Expedientes");
  const dossier = page.locator(".dossier-detail").filter({ hasText: opportunityTitle });
  await expect(dossier.locator(".dossier-hero")).toContainText("Activa");
  await expect(dossier).toContainText("La activación se registró y no hay requisitos pendientes en la proyección.");
  await expect(dossier).toContainText("Postulación enviada");
  await expect(dossier).toContainText("Selección del empleador registrada");
  await expect(dossier).toContainText("Aprobación académica registrada");
  await expect(dossier).toContainText("Documento devuelto para corrección");
  await expect(dossier).toContainText("Documento aprobado");
  await expect(dossier).toContainText("Práctica activada");
  await expect(dossier).toContainText("insurance-corrected.pdf · versión 2");
  await expect(dossier).toContainText("El archivo de prueba requiere corrección.");
  await expect(dossier.locator(".dossier-hours-summary")).toContainText(/4[,.]5 h/);
  await expect(dossier).toContainText("Elegibilidad · política v1");
  const timeline = dossier.locator(".placement-history-list");
  await expect(timeline).toContainText("Aprobación académica registrada");
  await expect(timeline).toContainText("Documento devuelto para corrección");
  await expect(timeline).toContainText("Documento aprobado");
  await expect(timeline).toContainText("Horas registradas");
  const studentProjection = await dossierResponse(page, placementId);
  expect(studentProjection.status).toBe(200);
  expect(studentProjection.body.capabilities.read_documents).toBe(true);
  expect(studentProjection.body.capabilities.record_hours).toBe(true);
  expect(Number(studentProjection.body.hours_total)).toBe(4.5);
  const persistedInsurance = studentProjection.body.documents.find((item: { kind: string }) => item.kind === "DOC_INSURANCE");
  expect(persistedInsurance.versions[0]).toEqual(expect.objectContaining({
    original_filename: "insurance-corrected.pdf", revision: 2, decision: "APPROVED",
  }));
  const completionCard = dossier.locator(".dossier-grid .bento-card").filter({ hasText: "Progreso y finalización" });
  await expect(completionCard).toContainText("Política de finalización v1");
  await expect(completionCard).toContainText("Informe final · obligatorio");
  await expect(completionCard).toContainText("Horas mínimas · 100 h · obligatorio");
  await expect(dossier.getByRole("button", { name: "Confirmar finalización" })).toHaveCount(0);
  if (process.env.E2E_DOSSIER_DESKTOP_SCREENSHOT) {
    await page.screenshot({ path: process.env.E2E_DOSSIER_DESKTOP_SCREENSHOT, fullPage: true, animations: "disabled" });
  }
  await page.reload();
  const dossierAfterReload = page.locator(".dossier-detail").filter({ hasText: opportunityTitle });
  await expect(dossierAfterReload.locator(".dossier-hero")).toContainText("Activa");
  await expect(dossierAfterReload).toContainText("insurance-corrected.pdf · versión 2");
  await expect(dossierAfterReload.locator(".dossier-hours-summary")).toContainText(/4[,.]5 h/);
  const timelineAfterReload = dossierAfterReload.locator(".placement-history-list");
  await expect(timelineAfterReload).toContainText("Selección del empleador registrada");
  await expect(timelineAfterReload).toContainText("Documento devuelto para corrección");
  await expect(timelineAfterReload).toContainText("Documento aprobado");
  await expect(timelineAfterReload).toContainText("Horas registradas");
  const completionCardAfterReload = dossierAfterReload.locator(".dossier-grid .bento-card").filter({ hasText: "Progreso y finalización" });
  await expect(completionCardAfterReload).toContainText("Informe final · obligatorio");
  await expect(completionCardAfterReload).toContainText("Horas mínimas · 100 h · obligatorio");
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await expect(dossierAfterReload.getByText("Actividad del ciclo de vida", { exact: true })).toBeVisible();
  if (process.env.E2E_DOSSIER_MOBILE_SCREENSHOT) {
    await page.screenshot({ path: process.env.E2E_DOSSIER_MOBILE_SCREENSHOT, fullPage: true, animations: "disabled" });
  }
  await page.setViewportSize({ width: 1280, height: 900 });
  await logout(page);
  await login(page, "pc_sys");
  await navigate(page, "Expedientes");
  const coordinatorDossier = page.locator(".dossier-detail").filter({ hasText: opportunityTitle });
  await expect(coordinatorDossier.getByRole("button", { name: "Confirmar finalización" })).toBeDisabled();
  await expect(coordinatorDossier).toContainText("Informe final, Evaluación final, Horas mínimas");
  const coordinatorProjection = await dossierResponse(page, placementId);
  expect(coordinatorProjection.status).toBe(200);
  expect(coordinatorProjection.body.capabilities.confirm_completion).toBe(true);
  expect(coordinatorProjection.body.application.eligibility_result).toBe("ELIGIBLE");
  expect(coordinatorProjection.body.application.eligibility_policy_version).toBe(1);
  expect(coordinatorProjection.body.activation_policy_version).toBe(2);
  expect(coordinatorProjection.body.activation_requirements).toEqual(expect.arrayContaining([
    expect.objectContaining({ kind: "DOC_INSURANCE", mandatory: true }),
  ]));
  const persistedRequirements = coordinatorProjection.body.completion_requirements as {
    kind: string; mandatory: boolean; satisfied: boolean; threshold: number | string | null;
  }[];
  expect(persistedRequirements).toEqual(expect.arrayContaining([
    expect.objectContaining({ kind: "FINAL_REPORT", mandatory: true, satisfied: false }),
    expect.objectContaining({ kind: "FINAL_EVALUATION", mandatory: true, satisfied: false }),
  ]));
  expect(Number(persistedRequirements.find((item) => item.kind === "MIN_HOURS")?.threshold)).toBe(100);
  expect(persistedRequirements.find((item) => item.kind === "MIN_HOURS")?.satisfied).toBe(false);

  await logout(page);
  await login(page, "ws_alfa");
  await expect(page.locator(".dashboard-related-placements")).toContainText(opportunityTitle);
  if (process.env.E2E_SUPERVISOR_DASHBOARD_DESKTOP_SCREENSHOT) {
    await page.screenshot({ path: process.env.E2E_SUPERVISOR_DASHBOARD_DESKTOP_SCREENSHOT, fullPage: true, animations: "disabled" });
  }
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  if (process.env.E2E_SUPERVISOR_DASHBOARD_MOBILE_SCREENSHOT) {
    await page.screenshot({ path: process.env.E2E_SUPERVISOR_DASHBOARD_MOBILE_SCREENSHOT, fullPage: true, animations: "disabled" });
  }
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.locator(".dashboard-related-placements").getByRole("button", { name: "Abrir expedientes" }).click();
  const assignedSupervisorProjection = await dossierResponse(page, placementId);
  expect(assignedSupervisorProjection.status).toBe(200);
  expect(assignedSupervisorProjection.body.documents).toBeNull();
  expect(assignedSupervisorProjection.body.hours).toBeNull();
  expect(assignedSupervisorProjection.body.completion_requirements).toBeNull();
  expect(assignedSupervisorProjection.body.capabilities.confirm_completion).toBe(false);
  expect(assignedSupervisorProjection.body.capabilities.assign_work_plan_item).toBe(true);
  await navigate(page, "Expedientes");
  const planDossier = page.locator(".dossier-detail").filter({ hasText: opportunityTitle });
  await planDossier.getByLabel("Nombre de la actividad").fill("Preparar inventario");
  await planDossier.getByLabel("Descripción de la actividad").fill("Documentar los pasos observados en el proceso de inventario.");
  await planDossier.getByRole("button", { name: "Asignar actividad" }).click();
  await expect(planDossier).toContainText("Preparar inventario");
  const planResponse = await page.evaluate(async (id) => {
    const response = await fetch(`/placements/${id}/work-plan`);
    return { status: response.status, body: await response.json() };
  }, placementId);
  expect(planResponse.status).toBe(200);
  expect(planResponse.body).toEqual([expect.objectContaining({
    revision: 1, title: "Preparar inventario", assigned_by: "Workplace Sup Alfa",
  })]);
  const assignedDossier = await dossierResponse(page, placementId);
  expect(assignedDossier.body.work_plan[0].description).toBe("Documentar los pasos observados en el proceso de inventario.");
  expect(assignedDossier.body.activity.map((event: { action: string }) => event.action)).toContain("work_plan.activity_assigned");
  await page.reload();
  await navigate(page, "Expedientes");
  await expect(page.locator(".dossier-detail").filter({ hasText: opportunityTitle })).toContainText("Documentar los pasos observados en el proceso de inventario.");

  await logout(page);
  await login(page, "ws_beta");
  expect((await dossierResponse(page, placementId)).status).toBe(404);
  expect(await page.evaluate(async (id) => (await fetch(`/placements/${id}/work-plan`)).status, placementId)).toBe(404);

  await logout(page);
  await login(page, "hm_beta");
  expect((await dossierResponse(page, placementId)).status).toBe(404);

  await logout(page);
  await login(page, "s2");
  expect((await dossierResponse(page, placementId)).status).toBe(403);

  await logout(page);
  await login(page, "pc_adm");
  expect((await dossierResponse(page, placementId)).status).toBe(403);

  await logout(page);
  await login(page, "legal1");
  const legalProjection = await dossierResponse(page, placementId);
  expect(legalProjection.status).toBe(200);
  expect(legalProjection.body.capabilities.read_documents).toBe(true);
  expect(legalProjection.body.documents).not.toBeNull();
  expect(legalProjection.body.hours).toBeNull();
  expect(legalProjection.body.completion_requirements).toBeNull();

  await logout(page);
  await login(page, "ec1");
  const experientialProjection = await dossierResponse(page, placementId);
  expect(experientialProjection.status).toBe(200);
  expect(experientialProjection.body.capabilities.confirm_completion).toBe(false);
  expect(experientialProjection.body.capabilities.close_placement).toBe(false);
  expect(experientialProjection.body.completion_requirements).not.toBeNull();
  expect(experientialProjection.body.hours).toBeNull();

  // Student progress, incident/change reports, final report and supervisor evaluation
  // are persisted records; the completion gate remains driven by the configured policy.
  await logout(page);
  await login(page, "s1");
  await navigate(page, "Expedientes");
  const followUpDossier = page.locator(".dossier-detail").filter({ hasText: opportunityTitle });
  await expect(followUpDossier).toContainText("Preparar inventario");
  await expect(followUpDossier.locator(".work-plan-list")).toBeVisible();
  await expect(followUpDossier.getByLabel("Nombre de la actividad")).toHaveCount(0);
  await followUpDossier.getByLabel("Detalle del avance").fill("Se completó la primera etapa del trabajo asignado.");
  await followUpDossier.getByRole("button", { name: "Guardar avance" }).click();
  await expect(followUpDossier.locator(".progress-report-list")).toContainText("primera etapa");

  await followUpDossier.getByLabel("Tipo de registro").selectOption("CHANGE");
  await followUpDossier.getByLabel("Resumen de situación o cambio").fill("Ajuste de horario solicitado");
  await followUpDossier.getByLabel("Detalle de situación o cambio").fill("Se comunica un cambio para que los participantes lo revisen.");
  await followUpDossier.getByRole("button", { name: "Registrar", exact: true }).click();
  await expect(followUpDossier).toContainText("Ajuste de horario solicitado");
  await expect(followUpDossier.getByText("Reportado", { exact: true })).toBeVisible();

  await followUpDossier.getByLabel("Archivo del informe final").setInputFiles({
    name: "informe-final.pdf", mimeType: "application/pdf", buffer: Buffer.from("%PDF-1.7 synthetic final report"),
  });
  await followUpDossier.getByRole("button", { name: "Entregar informe final" }).click();
  await expect(followUpDossier).toContainText("informe-final.pdf · versión 1");
  const studentFollowUpProjection = await dossierResponse(page, placementId);
  expect(studentFollowUpProjection.body.capabilities.submit_completion_evidence).toBe(true);
  expect(studentFollowUpProjection.body.capabilities.assign_work_plan_item).toBe(false);
  expect(studentFollowUpProjection.body.work_plan[0].title).toBe("Preparar inventario");
  expect(studentFollowUpProjection.body.progress_reports[0].content).toContain("primera etapa");
  expect(studentFollowUpProjection.body.incidents[0].kind).toBe("CHANGE");
  expect(studentFollowUpProjection.body.incidents[0].status).toBe("REPORTED");
  expect(studentFollowUpProjection.body.completion_evidence[0]).toEqual(expect.objectContaining({
    kind: "FINAL_REPORT", revision: 1, original_filename: "informe-final.pdf",
  }));

  // Only the assigned workplace supervisor can submit a narrative evaluation.
  await logout(page);
  await login(page, "ws_alfa");
  await navigate(page, "Expedientes");
  const supervisorDossier = page.locator(".dossier-detail").filter({ hasText: opportunityTitle });
  await expect(supervisorDossier).toContainText("primera etapa del trabajo asignado");
  await expect(supervisorDossier).toContainText("Ajuste de horario solicitado");
  await expect(supervisorDossier.getByLabel("Detalle del avance")).toHaveCount(0);
  await expect(supervisorDossier.locator(".evaluation-form")).toHaveCount(1);
  await supervisorDossier.getByLabel("Tipo de evaluación").selectOption("FINAL");
  await supervisorDossier.getByLabel("Observaciones de la evaluación").fill("El estudiante documentó los avances de la práctica.");
  await supervisorDossier.getByRole("button", { name: "Guardar evaluación" }).click();
  await expect(supervisorDossier).toContainText("El estudiante documentó los avances de la práctica.");
  const supervisorProjection = await dossierResponse(page, placementId);
  expect(supervisorProjection.body.capabilities.read_evaluations).toBe(true);
  expect(supervisorProjection.body.completion_evidence).toBeNull();

  // A host-organization member without the direct supervisor relationship cannot see
  // progress, evaluation, incident, or final evidence content.
  await logout(page);
  await login(page, "hm_alfa");
  const hostMemberProjection = await dossierResponse(page, placementId);
  expect(hostMemberProjection.status).toBe(200);
  expect(hostMemberProjection.body.progress_reports).toBeNull();
  expect(hostMemberProjection.body.evaluations).toBeNull();
  expect(hostMemberProjection.body.incidents).toBeNull();
  expect(hostMemberProjection.body.completion_evidence).toBeNull();
  expect(hostMemberProjection.body.work_plan).toBeNull();
  expect(hostMemberProjection.body.capabilities.read_work_plan).toBe(false);

  // The student records only the hours required by the synthetic persisted policy.
  await logout(page);
  await login(page, "s1");
  await navigate(page, "Mis documentos");
  const hoursPlacement = page.locator(".document-placement").filter({ hasText: opportunityTitle });
  await hoursPlacement.getByLabel("Horas realizadas").fill("95.5");
  await hoursPlacement.getByRole("button", { name: "Registrar horas" }).click();
  await expect(hoursPlacement.locator(".metric-value")).toHaveText("100 h");
  await page.reload();
  await navigate(page, "Expedientes");
  const readyDossier = page.locator(".dossier-detail").filter({ hasText: opportunityTitle });
  await expect(readyDossier).toContainText("informe-final.pdf · versión 1");
  await expect(readyDossier).toContainText("El estudiante documentó los avances de la práctica.");
  await expect(readyDossier.locator(".dossier-hours-summary")).toContainText("100 h");
  const readyCompletion = readyDossier.locator(".dossier-grid .bento-card").filter({ hasText: "Progreso y finalización" });
  await expect(readyCompletion).toContainText("Informe final · obligatorio");
  await expect(readyCompletion).toContainText("Evaluación final · obligatorio");
  await expect(readyCompletion).toContainText("Horas mínimas · 100 h · obligatorio");
  const studentReadyProjection = await dossierResponse(page, placementId);
  expect(studentReadyProjection.body.capabilities.confirm_completion).toBe(false);
  await expect(readyDossier.getByRole("button", { name: "Confirmar finalización" })).toHaveCount(0);
  if (process.env.E2E_DOSSIER_DESKTOP_SCREENSHOT) {
    await page.screenshot({ path: process.env.E2E_DOSSIER_DESKTOP_SCREENSHOT, fullPage: true, animations: "disabled" });
  }
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  if (process.env.E2E_DOSSIER_MOBILE_SCREENSHOT) {
    await page.screenshot({ path: process.env.E2E_DOSSIER_MOBILE_SCREENSHOT, fullPage: true, animations: "disabled" });
  }
  await page.setViewportSize({ width: 1280, height: 900 });

  // Completion and closure stay with their existing internal roles and recheck the
  // policy-derived source records on the backend.
  await logout(page);
  await login(page, "pc_sys");
  await navigate(page, "Expedientes");
  const confirmDossier = page.locator(".dossier-detail").filter({ hasText: opportunityTitle });
  await expect(confirmDossier.getByRole("button", { name: "Confirmar finalización" })).toBeEnabled();
  await confirmDossier.getByRole("button", { name: "Confirmar finalización" }).click();
  await expect(confirmDossier.locator(".dossier-hero")).toContainText("Completada");
  await logout(page);

  await login(page, "ec1");
  await navigate(page, "Expedientes");
  const closeDossier = page.locator(".dossier-detail").filter({ hasText: opportunityTitle });
  await expect(closeDossier.getByRole("button", { name: "Cerrar práctica" })).toBeEnabled();
  await closeDossier.getByRole("button", { name: "Cerrar práctica" }).click();
  await expect(closeDossier.locator(".dossier-hero")).toContainText("Cerrada");
  await logout(page);

  await login(page, "s1");
  await navigate(page, "Expedientes");
  const closedDossier = page.locator(".dossier-detail").filter({ hasText: opportunityTitle });
  await expect(closedDossier.locator(".dossier-hero")).toContainText("Cerrada");
  await expect(closedDossier).toContainText("informe-final.pdf · versión 1");
  await expect(closedDossier).toContainText("El estudiante documentó los avances de la práctica.");
  await expect(closedDossier.locator(".dossier-hours-summary")).toContainText("100 h");
  const closedProjection = await dossierResponse(page, placementId);
  expect(closedProjection.body.placement.state).toBe("CLOSED");
  const closedActions = closedProjection.body.activity.map((event: { action: string }) => event.action);
  expect(closedActions).toContain("placement.completed");
  expect(closedActions).toContain("placement.closed");
  expect(closedProjection.body.completion_requirements.every((item: { satisfied: boolean }) => item.satisfied)).toBe(true);

  const studentClosedWrites = await page.evaluate(async (id) => {
    const attempts = await Promise.all([
      fetch(`/placements/${id}/hours`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ hours: 1 }),
      }),
      fetch(`/placements/${id}/progress-reports`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: "Avance posterior al cierre." }),
      }),
      fetch(`/placements/${id}/incidents`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ kind: "INCIDENT", summary: "Posterior al cierre", description: "No debe persistirse." }),
      }),
      fetch(`/placements/${id}/completion-evidence/FINAL_REPORT?filename=posterior.pdf`, {
        method: "POST", headers: { "Content-Type": "application/pdf" }, body: "%PDF-1.7 posterior al cierre",
      }),
    ]);
    return Promise.all(attempts.map(async (response) => ({
      status: response.status,
      body: response.ok ? null : await response.json(),
    })));
  }, placementId);
  expect(studentClosedWrites.map((attempt: { status: number }) => attempt.status)).toEqual([409, 409, 409, 409]);
  expect(studentClosedWrites.map((attempt: { body: { error: string } }) => attempt.body.error)).toEqual([
    "PLACEMENT_NOT_ACTIVE", "PLACEMENT_NOT_ACTIVE", "PLACEMENT_NOT_ACTIVE", "PLACEMENT_NOT_ACTIVE",
  ]);
  await page.reload();
  const closedAfterDeniedWrites = await dossierResponse(page, placementId);
  expect(Number(closedAfterDeniedWrites.body.hours_total)).toBe(100);
  expect(closedAfterDeniedWrites.body.progress_reports).toHaveLength(1);
  expect(closedAfterDeniedWrites.body.incidents).toHaveLength(1);
  expect(closedAfterDeniedWrites.body.completion_evidence).toHaveLength(1);
  await logout(page);

  await login(page, "ws_alfa");
  await navigate(page, "Expedientes");
  const closedSupervisorDossier = page.locator(".dossier-detail").filter({ hasText: opportunityTitle });
  await expect(closedSupervisorDossier).toContainText("La práctica está cerrada. El plan permanece disponible para consulta.");
  await expect(closedSupervisorDossier.getByLabel("Nombre de la actividad")).toHaveCount(0);
  const closedWorkPlanWrite = await page.evaluate(async (id) => {
    const response = await fetch(`/placements/${id}/work-plan`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: "Actividad posterior", description: "No debe persistirse." }),
    });
    return { status: response.status, body: await response.json() };
  }, placementId);
  expect(closedWorkPlanWrite.status).toBe(409);
  expect(closedWorkPlanWrite.body.error).toBe("PLACEMENT_CLOSED");
  const closedSupervisorProjection = await dossierResponse(page, placementId);
  expect(closedSupervisorProjection.body.work_plan).toHaveLength(1);
  await logout(page);

  await login(page, "pc_sys");
  const terminalFacultyChange = await page.evaluate(async (id) => {
    const response = await fetch(`/placements/${id}/faculty-supervisors`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: (await (await fetch("/auth/me")).json()).id }),
    });
    return { status: response.status, body: await response.json() };
  }, placementId);
  expect(terminalFacultyChange.status).toBe(409);
  expect(terminalFacultyChange.body.error).toBe("FACULTY_ASSIGNMENT_PLACEMENT_TERMINAL");
  const closedAfterFacultyWrite = await dossierResponse(page, placementId);
  expect(closedAfterFacultyWrite.body.responsibles.faculty_assignments).toEqual([]);
});

async function verifyRelatedPlacementRetry(page: Page, username: string) {
  let placementRequests = 0;
  let failedPlacementRequests = 0;
  let simulateTemporaryFailure = true;
  await page.route((url) => new URL(url).pathname === "/placements", async (route) => {
    placementRequests += 1;
    if (simulateTemporaryFailure) {
      failedPlacementRequests += 1;
      await route.fulfill({
        status: 503,
        contentType: "application/json",
        body: JSON.stringify({ detail: "temporary test failure" }),
      });
      return;
    }
    await route.continue();
  });

  await login(page, username);
  const listCard = page.locator(".dashboard-related-placements");
  await expect(page.getByRole("alert")).toContainText("Expedientes relacionados");
  await expect(listCard.getByRole("status")).toContainText("No se pudo cargar la lista");
  await expect(listCard.locator(".loading-line")).toHaveCount(0);
  const failedRequestCount = placementRequests;
  expect(failedRequestCount).toBeGreaterThan(0);
  expect(failedPlacementRequests).toBe(failedRequestCount);

  const retryResponse = page.waitForResponse((response) =>
    response.url().endsWith("/placements") && response.status() === 200,
  );
  simulateTemporaryFailure = false;
  await page.getByRole("button", { name: "Reintentar carga" }).click();
  await retryResponse;

  await expect(page.getByRole("alert")).toHaveCount(0);
  await expect(listCard.getByRole("status")).toHaveCount(0);
  await expect(listCard.locator(".activity-list, .empty-state")).toHaveCount(1);
  expect(placementRequests).toBeGreaterThan(failedRequestCount);
}

for (const username of ["ws_alfa", "pc_sys", "f1"]) {
  test(`relationship dashboard for ${username} reports a failed list request and retries it`, async ({ page }) => {
    await verifyRelatedPlacementRetry(page, username);
  });
}
