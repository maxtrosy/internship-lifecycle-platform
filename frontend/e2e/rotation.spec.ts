import { expect, test, type Page } from "@playwright/test";

// CR-05 (Evaluación 4) browser check on the isolated populated fixture:
// "una transferencia conserva horas aceptadas; el supervisor previo queda sin acceso automático".
// The runner exports an active practice that no other populated check modifies.
const password = process.env.E2E_DEMO_PASSWORD ?? "Demo-Only-2026!";
const scenarioTitle = "activa-sin-informe";

async function login(page: Page, username: string) {
  await page.context().clearCookies();
  await page.goto("/#/login");
  await page.reload();
  await page.getByLabel("Correo electrónico o nombre de usuario").fill(username);
  await page.getByLabel("Contraseña").fill(password);
  await page.getByRole("button", { name: "Ingresar" }).click();
  await expect(page.getByRole("button", { name: "Cerrar sesión" })).toBeVisible();
}

async function openScenarioDossier(page: Page) {
  await page.locator(".sidebar-nav").getByRole("link", { name: "Expedientes", exact: true }).click();
  // Wait for the list (several visible practices) or the single detail before choosing.
  await expect(page.locator(".dossier-list-item, .dossier-detail").first()).toBeVisible();
  const item = page.locator(".dossier-list-item").filter({ hasText: scenarioTitle });
  if (await item.count()) await item.click();
  const detail = page.locator(".dossier-detail").filter({ hasText: scenarioTitle });
  await expect(detail.locator(".segment-card")).toBeVisible();
  return detail;
}

async function api(page: Page, path: string) {
  return page.evaluate(async (url) => {
    const response = await fetch(url);
    return { status: response.status, body: response.ok ? await response.json() : null };
  }, path);
}

function isoInDays(days: number) {
  const date = new Date();
  date.setDate(date.getDate() + days);
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 10);
}

test("[@populated] CR-05: la transferencia conserva horas aceptadas y retira el acceso del supervisor anterior", async ({ page }) => {
  test.skip(!process.env.E2E_ROTATION_ID, "Requiere el generador PostgreSQL aislado --populated.");
  test.setTimeout(180_000);
  const pid = process.env.E2E_ROTATION_ID!;
  const dossierPath = `/placements/${pid}/dossier`;

  // 1. Only reviewed hours count (BR-04): the configured reviewer accepts the reported entries.
  await login(page, process.env.E2E_ROTATION_REVIEWER!);
  const reviewerDetail = await openScenarioDossier(page);
  const reviewForms = reviewerDetail.getByRole("form", { name: /^Revisar horas/ });
  const pending = await reviewForms.count();
  expect(pending).toBeGreaterThan(0);
  for (let remaining = pending; remaining > 0; remaining -= 1) {
    await reviewForms.first().getByRole("button", { name: "Registrar revisión" }).click();
    await expect(reviewForms).toHaveCount(remaining - 1);
  }
  const reviewed = (await api(page, dossierPath)).body;
  const acceptedBefore = Number(reviewed.hours_summary.accepted_total);
  expect(acceptedBefore).toBeGreaterThan(0);
  expect(acceptedBefore).toBe(Number(reviewed.hours_summary.reported_total));

  // 2. The segment manager records the transfer as one operation (BR-05).
  await login(page, "ec1");
  const ecDetail = await openScenarioDossier(page);
  const segments = ecDetail.getByRole("list", { name: "Segmentos de la práctica" });
  await segments.locator(".segment-active").getByRole("button", { name: "Transferir" }).click();
  const drawer = page.getByRole("dialog", { name: "Transferir segmento" });
  await expect(drawer).toBeVisible();
  await drawer.getByLabel("Motivo visible para las personas relacionadas").fill("Rotación sintética a otra organización.");
  await drawer.getByLabel("Motivo confidencial (opcional)").fill("Nota interna sintética de la transferencia.");
  await drawer.getByLabel("Organización").selectOption({ label: process.env.E2E_ROTATION_DEST_ORGANIZATION! });
  await drawer.getByLabel("Supervisor laboral").selectOption({ label: process.env.E2E_ROTATION_DEST_SUPERVISOR_NAME! });
  await drawer.getByLabel("Unidad o área").fill("Unidad sintética de destino");
  await drawer.getByLabel("Modalidad").selectOption("HYBRID");
  await drawer.getByLabel("Fin", { exact: true }).fill(isoInDays(30));
  await drawer.getByLabel("Responsabilidades").fill("Responsabilidades sintéticas del segmento destino.");
  await drawer.getByRole("button", { name: "Registrar transferencia" }).click();
  await expect(page.getByText("Transferencia registrada.", { exact: false })).toBeVisible();
  await expect(segments.locator(".segment-transferred")).toContainText("Transferido");
  const planned = segments.locator(".segment-planned");
  await expect(planned).toContainText("Planificado");

  // Rejection: the destination cannot be activated before its own enablement conditions (BR-02).
  const activate = planned.getByRole("button", { name: "Activar segmento" });
  const hasConditions = await activate.isDisabled();
  if (hasConditions) {
    await expect(planned.locator(".disabled-reason")).toContainText("Para activar falta confirmar");
    // 3. Documentary evidence (0019): the student uploads a real file for the destination's
    // condition through the document module and legal review approves it.
    await login(page, process.env.E2E_ROTATION_USER!);
    await page.locator(".sidebar-nav").getByRole("link", { name: "Mis documentos", exact: true }).click();
    const placementDocs = page.locator(".document-placement").filter({ hasText: scenarioTitle });
    const evidenceRow = placementDocs.locator("tr").filter({ hasText: "segmento 2" }).first();
    await expect(evidenceRow).toContainText("Habilita el segmento 2");
    await evidenceRow.locator('input[type="file"]').setInputFiles({
      name: "poliza-segmento-2.pdf", mimeType: "application/pdf", buffer: Buffer.from("%PDF-1.7 evidencia sintética E2E"),
    });
    await evidenceRow.getByRole("button", { name: "Enviar" }).click();
    await expect(page.getByText("Documento enviado como versión 1.")).toBeVisible();

    await login(page, "legal1");
    await page.locator(".sidebar-nav").getByRole("link", { name: "Revisión documental", exact: true }).click();
    const card = page.locator(".document-review-card").filter({ hasText: scenarioTitle }).first();
    await card.getByRole("button", { name: "Ver documentos" }).click();
    const reviewRow = card.locator("tr").filter({ hasText: "segmento 2" }).first();
    await expect(reviewRow).toContainText("Al aprobarlo se cumple la condición de habilitación del segmento 2");
    await reviewRow.getByRole("textbox").fill("Póliza sintética vigente para el segmento 2.");
    await reviewRow.getByRole("button", { name: "Aprobar" }).click();
    await page.getByRole("button", { name: "Aprobar documento" }).click();
    // On an active placement an approved document stays listed so it can be revoked (E3 rule).
    await expect(reviewRow.getByRole("button", { name: "Revocar aprobación" })).toBeVisible();
    const afterEvidence = (await api(page, dossierPath)).body;
    const destinationConditions = afterEvidence.segments[1].conditions as { kind: string; status: string; reference: string | null; evidence_status: string | null }[];
    const documentCondition = destinationConditions.find((c) => c.evidence_status !== null && c.evidence_status !== undefined)!;
    expect(documentCondition.status).toBe("SATISFIED");
    expect(documentCondition.evidence_status).toBe("APPROVED");
    expect(documentCondition.reference).toContain("poliza-segmento-2.pdf");

    // Any remaining non-documentary condition is still confirmed by reference.
    const legalDetail = await openScenarioDossier(page);
    const legalPlanned = legalDetail.getByRole("list", { name: "Segmentos de la práctica" }).locator(".segment-planned");
    await legalPlanned.locator("summary").click();
    for (const field of await legalPlanned.getByLabel("Referencia verificada").all()) {
      await field.fill("Póliza sintética POL-E2E-01");
      await legalPlanned.getByRole("button", { name: "Confirmar condición" }).first().click();
      await expect(page.getByText("Condición confirmada.")).toBeVisible();
    }
    await login(page, "ec1");
    await openScenarioDossier(page);
  }
  await page.getByRole("list", { name: "Segmentos de la práctica" }).locator(".segment-planned")
    .getByRole("button", { name: "Activar segmento" }).click();
  await expect(page.getByText("Segmento activado.")).toBeVisible();

  // 4a. Explicit temporary exception (CR-05 §6.3): extend the active destination segment.
  const activeSegment = page.getByRole("list", { name: "Segmentos de la práctica" }).locator(".segment-active");
  await activeSegment.getByRole("button", { name: "Cambiar fecha de fin" }).click();
  const scheduleDrawer = page.getByRole("dialog", { name: "Cambiar periodo del segmento" });
  await expect(scheduleDrawer.getByLabel("Inicio")).toBeDisabled();
  await scheduleDrawer.getByLabel("Nueva fecha de fin").fill(isoInDays(45));
  await scheduleDrawer.getByLabel("Motivo visible para las personas relacionadas").fill("Extensión sintética acordada.");
  await scheduleDrawer.getByRole("button", { name: "Guardar nuevo periodo" }).click();
  await expect(page.getByText("Periodo del segmento actualizado", { exact: false })).toBeVisible();
  await activeSegment.locator("summary").click();
  await expect(activeSegment.getByRole("list", { name: /Cambios de periodo/ })).toContainText("Extensión sintética acordada.");

  // 4b. Administrative adjustment (0019): an active segment keeps its organization, unit and
  // supervisor (those need a transfer) but its modality and expected hours can change with history.
  await activeSegment.getByRole("button", { name: "Ajustar datos" }).click();
  const editDrawer = page.getByRole("dialog", { name: "Ajustar datos del segmento" });
  await expect(editDrawer).toContainText("Para cambiarlos registra una transferencia.");
  await expect(editDrawer.getByLabel("Unidad o área")).toHaveCount(0);
  await editDrawer.getByLabel("Modalidad").selectOption("REMOTE");
  await editDrawer.getByLabel("Horas esperadas").fill("120");
  await editDrawer.getByLabel("Motivo visible para las personas relacionadas").fill("Modalidad remota acordada (sintético).");
  await editDrawer.getByRole("button", { name: "Guardar ajuste" }).click();
  await expect(page.getByText("Datos del segmento actualizados", { exact: false })).toBeVisible();
  await expect(activeSegment.getByRole("list", { name: /Ajustes de datos/ })).toContainText("Modalidad remota acordada (sintético).");

  // 4. Internal roles see the confidential reason. (The experiential coordinator does not read
  // hours under the E3 rules, so the hours check runs as the reviewer and the student below.)
  const afterTransfer = (await api(page, dossierPath)).body;
  expect(afterTransfer.segments.map((s: { status: string }) => s.status)).toEqual(["TRANSFERRED", "ACTIVE"]);
  expect(afterTransfer.segments[0].work_recognition).toBe("ACCEPTED_HOURS_RECOGNIZED");
  expect(afterTransfer.transfers).toHaveLength(1);
  expect(afterTransfer.segments[1].end_date).toBe(isoInDays(45));
  expect(afterTransfer.segments[1].schedule_changes).toHaveLength(1);
  expect(afterTransfer.segments[1].schedule_changes[0].from_end_date).toBe(isoInDays(30));
  expect(afterTransfer.transfers[0].reason_internal).toBe("Nota interna sintética de la transferencia.");
  expect(afterTransfer.segments[1].modality).toBe("REMOTE");
  expect(afterTransfer.segments[1].revisions).toHaveLength(1);
  expect(afterTransfer.segments[1].revisions[0].changed_fields).toEqual(["modality", "expected_hours"]);

  // 5. The previous supervisor has no automatic access (BR-06); the new one sees only their segment.
  await login(page, process.env.E2E_ROTATION_ORIGIN_SUPERVISOR!);
  expect((await api(page, dossierPath)).status).toBe(404);
  await login(page, process.env.E2E_ROTATION_DEST_SUPERVISOR!);
  const destination = await api(page, dossierPath);
  expect(destination.status).toBe(200);
  expect(destination.body.segments.map((s: { sequence_no: number }) => s.sequence_no)).toEqual([2]);
  expect(JSON.stringify(destination.body)).not.toContain("Nota interna sintética");
  const destinationInbox = (await api(page, "/notifications")).body;
  expect(destinationInbox.map((n: { category: string }) => n.category)).toContain("SEGMENT_CHANGED");

  // 6. The student keeps the history without the confidential reason (BR-09) and is notified.
  await login(page, process.env.E2E_ROTATION_USER!);
  const student = (await api(page, dossierPath)).body;
  expect(Number(student.hours_summary.accepted_total)).toBe(acceptedBefore);
  expect(student.transfers[0].reason_internal).toBeUndefined();
  expect(student.transfers[0].reason_shared).toBe("Rotación sintética a otra organización.");
  const studentDetail = await openScenarioDossier(page);
  await expect(studentDetail.getByRole("list", { name: "Segmentos de la práctica" }).locator(".segment-transferred"))
    .toContainText("Rotación sintética a otra organización.");
  await expect(studentDetail).not.toContainText("Nota interna sintética");
  const studentInbox = (await api(page, "/notifications")).body;
  expect(studentInbox.map((n: { category: string }) => n.category)).toContain("SEGMENT_CHANGED");

  // 7. The CR-05 report counts the transfer within the coordinator's scope.
  await login(page, process.env.E2E_ROTATION_REVIEWER!);
  const reviewerAfter = (await api(page, dossierPath)).body;
  expect(Number(reviewerAfter.hours_summary.accepted_total)).toBe(acceptedBefore);
  expect(reviewerAfter.hours_summary.segments.map((s: { accepted: number | string }) => Number(s.accepted)))
    .toEqual([acceptedBefore]);
  await page.locator(".sidebar-nav").getByRole("link", { name: "Reportes operativos", exact: true }).click();
  const rotation = page.locator(".rotation-report");
  await expect(rotation.getByRole("heading", { name: "Rotaciones y transferencias" })).toBeVisible();
  const transfersMetric = rotation.locator(".rotation-metrics .bento-metric").filter({ hasText: "Transferencias" }).locator(".metric-value");
  await expect(transfersMetric).not.toHaveText("0");
  expect((await api(page, "/reports/rotations")).body.transfers).toBeGreaterThanOrEqual(1);
});
