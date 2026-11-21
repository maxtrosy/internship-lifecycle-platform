import { expect, test, type Page } from "@playwright/test";
import { join } from "node:path";

type Role = "STUDENT" | "HOST_ORG_MEMBER" | "PROGRAM_COORDINATOR" | "LEGAL_REVIEWER" | "EXPERIENTIAL_COORDINATOR" | "WORKPLACE_SUPERVISOR" | "FACULTY_SUPERVISOR";

const roleDashboards: { role: Role; variant: string; eyebrow: string }[] = [
  { role: "STUDENT", variant: "student", eyebrow: "TU PRÁCTICA" },
  { role: "HOST_ORG_MEMBER", variant: "employer", eyebrow: "ORGANIZACIÓN ANFITRIONA" },
  { role: "PROGRAM_COORDINATOR", variant: "academic", eyebrow: "COORDINACIÓN ACADÉMICA" },
  { role: "LEGAL_REVIEWER", variant: "legal", eyebrow: "REVISIÓN DOCUMENTAL" },
  { role: "EXPERIENTIAL_COORDINATOR", variant: "experiential", eyebrow: "COORDINACIÓN EXPERIENCIAL" },
  { role: "WORKPLACE_SUPERVISOR", variant: "workplace", eyebrow: "SUPERVISIÓN LABORAL" },
  { role: "FACULTY_SUPERVISOR", variant: "faculty", eyebrow: "SUPERVISIÓN DOCENTE" },
];

const operationalRoutes = [
  "opportunities", "applications", "academic", "policies", "documents",
  "docreview", "activation", "dossier", "notifications", "reports",
];

async function captureVisual(page: Page, name: string) {
  const directory = process.env.VISUAL_CAPTURE_DIR;
  if (!directory) return;
  await page.screenshot({ path: join(directory, `${name}.png`), fullPage: true });
}

function userFor(role: Role | "ALL_ROLES") {
  const roles: Role[] = role === "ALL_ROLES" ? roleDashboards.map((item) => item.role) : [role];
  return {
    id: 41,
    username: "visual-fixture",
    display_name: "Vista de interfaz",
    email: null,
    roles: roles.map((item) => ({
      role: item,
      program_id: item === "PROGRAM_COORDINATOR" ? 1 : null,
      host_org_id: item === "HOST_ORG_MEMBER" || item === "WORKPLACE_SUPERVISOR" ? 1 : null,
    })),
  };
}

async function mockEmptyApi(page: Page, user: ReturnType<typeof userFor>) {
  await page.route("**/*", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (!(["fetch", "xhr"].includes(request.resourceType()))) return route.continue();

    if (url.pathname === "/auth/me") {
      return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(user) });
    }
    if (url.pathname === "/opportunities/catalogs") {
      return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ organizations: [], programs: [] }) });
    }
    if (url.pathname === "/reports/operations") {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          placements_by_state: [], opportunities_by_state: [], applications_by_state: [],
          active_placements: 0, mandatory_documents_pending: 0, reported_incidents: 0,
          expected_end_dates: [], by_program: [], by_organization: [],
        }),
      });
    }

    if (request.method() === "GET" && /^\/(applications|notifications|placements|policies|opportunities)(\/|$)/.test(url.pathname)) {
      return route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
    }
    return route.continue();
  });
}

async function expectNoHorizontalOverflow(page: Page, width: number) {
  await page.setViewportSize({ width, height: 844 });
  await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);
}

async function expectDarkThemeSettled(page: Page) {
  await expect.poll(() => page.evaluate(() => getComputedStyle(document.body).backgroundColor)).toBe("rgb(17, 26, 24)");
}

test("login no autenticado mantiene tema y controles legibles en móvil y oscuro", async ({ page }) => {
  await page.route("**/auth/me", (route) => route.fulfill({ status: 401, contentType: "application/json", body: JSON.stringify({ detail: "UNAUTHORIZED" }) }));
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Iniciar sesión" })).toBeVisible();
  await expect(page.getByLabel("Correo electrónico o nombre de usuario")).toBeVisible();
  await expect(page.getByLabel("Contraseña")).toBeVisible();
  await page.getByLabel("Apariencia").selectOption("dark");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await expect.poll(() => page.locator('meta[name="theme-color"]').getAttribute("content")).toBe("#111a18");
  await expectDarkThemeSettled(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await captureVisual(page, "login-dark-mobile");
  await page.getByRole("button", { name: "Ingresar" }).click();
  await expect(page.getByLabel("Correo electrónico o nombre de usuario")).toBeFocused();
  expect(await page.getByLabel("Correo electrónico o nombre de usuario").evaluate((element) => (element as HTMLInputElement).validity.valueMissing)).toBe(true);

  const primaryButtonContrast = await page.locator(".login-submit").evaluate((element) => {
    const color = getComputedStyle(element).color.match(/[\d.]+/g)!.map(Number);
    const background = getComputedStyle(element).backgroundColor.match(/[\d.]+/g)!.map(Number);
    const luminance = (channels: number[]) => channels.map((channel) => channel / 255)
      .map((channel) => channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4)
      .reduce((total, channel, index) => total + channel * [0.2126, 0.7152, 0.0722][index], 0);
    const values = [luminance(color), luminance(background)].sort((a, b) => b - a);
    return (values[0] + 0.05) / (values[1] + 0.05);
  });
  expect(primaryButtonContrast).toBeGreaterThanOrEqual(4.5);

  await expectNoHorizontalOverflow(page, 320);
  await expectNoHorizontalOverflow(page, 390);
  await expectNoHorizontalOverflow(page, 768);
  await expectNoHorizontalOverflow(page, 1024);
  await expectNoHorizontalOverflow(page, 1440);
  const secondaryButtonContrast = await page.locator(".login-demo-link").evaluate((element) => {
    const channels = (value: string) => value.match(/[\d.]+/g)!.map(Number);
    const luminance = (rgb: number[]) => rgb.map((channel) => channel / 255)
      .map((channel) => channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4)
      .reduce((total, channel, index) => total + channel * [0.2126, 0.7152, 0.0722][index], 0);
    const values = [luminance(channels(getComputedStyle(element).color)), luminance(channels(getComputedStyle(element).backgroundColor))].sort((a, b) => b - a);
    return (values[0] + 0.05) / (values[1] + 0.05);
  });
  expect(secondaryButtonContrast).toBeGreaterThanOrEqual(4.5);
});

test("acceso a cuentas de prueba permanece claro y responsive en entorno local", async ({ page }) => {
  await page.route("**/auth/me", (route) => route.fulfill({ status: 401, contentType: "application/json", body: JSON.stringify({ detail: "UNAUTHORIZED" }) }));
  await page.goto("/#/demo-login");
  await expect(page.getByRole("heading", { name: "Cuentas de prueba" })).toBeVisible();
  await expect(page.locator(".demo-account-card")).toHaveCount(14);
  await captureVisual(page, "demo-login-desktop");
  await expectNoHorizontalOverflow(page, 320);
  await expectNoHorizontalOverflow(page, 390);
  await expectNoHorizontalOverflow(page, 768);
  await expectNoHorizontalOverflow(page, 1024);
  await expectNoHorizontalOverflow(page, 1440);
  await page.setViewportSize({ width: 768, height: 844 });
  const tabletColumns = await page.locator(".demo-account-grid").evaluate((element) => getComputedStyle(element).gridTemplateColumns.split(" ").length);
  expect(tabletColumns).toBe(2);
  await captureVisual(page, "demo-login-tablet");
  await page.setViewportSize({ width: 390, height: 844 });
  const mobileColumns = await page.locator(".demo-account-grid").evaluate((element) => getComputedStyle(element).gridTemplateColumns.split(" ").length);
  expect(mobileColumns).toBe(1);
  await captureVisual(page, "demo-login-mobile");
});

for (const dashboard of roleDashboards) {
  test(`dashboard ${dashboard.role} tiene jerarquía de rol y responde a 390 px`, async ({ page }) => {
    await mockEmptyApi(page, userFor(dashboard.role));
    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.goto("/#/home");
    await expect(page.locator(`.dashboard-grid--${dashboard.variant}`)).toBeVisible();
    await expect(page.locator(".dashboard-hero")).toBeVisible();
    await expect(page.locator(".page-header .eyebrow")).toHaveText(dashboard.eyebrow);
    await captureVisual(page, `dashboard-${dashboard.variant}-desktop`);
    if (dashboard.variant === "student") {
      await page.keyboard.press("Tab");
      await expect(page.getByRole("link", { name: "Saltar al contenido" })).toBeFocused();
      await page.keyboard.press("Enter");
      await expect(page.locator("main")).toBeFocused();
      await expect(page).toHaveURL(/#\/home$/);
    }
    await expectNoHorizontalOverflow(page, 1440);
    await expectNoHorizontalOverflow(page, 768);
    await expectNoHorizontalOverflow(page, 390);
    await expectNoHorizontalOverflow(page, 320);
    await expectNoHorizontalOverflow(page, 1024);
    await page.setViewportSize({ width: 390, height: 844 });
    const mobileMenu = page.getByRole("button", { name: "Abrir menú de navegación" });
    await expect(mobileMenu).toBeVisible();
    await expect(page.locator(".sidebar-nav")).toBeHidden();
    expect(await page.locator(".sidebar").evaluate((element) => element.getBoundingClientRect().height)).toBeLessThan(160);
    await mobileMenu.click();
    await expect(page.locator('.sidebar .nav[aria-current="page"]')).toBeVisible();
    await expect(page.getByRole("button", { name: "Cerrar menú de navegación" })).toHaveAttribute("aria-expanded", "true");
    if (dashboard.variant === "student") await captureVisual(page, "dashboard-student-mobile-menu-open");
    await page.keyboard.press("Escape");
    await expect(page.getByRole("button", { name: "Abrir menú de navegación" })).toBeFocused();
    await expect(page.locator(".sidebar-nav")).toBeHidden();
    await captureVisual(page, `dashboard-${dashboard.variant}-mobile`);
    const mobileColumns = await page.locator(".dashboard-grid").evaluate((element) => getComputedStyle(element).gridTemplateColumns.split(" ").length);
    expect(mobileColumns).toBe(2);
    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.getByLabel("Apariencia").selectOption("dark");
    await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
    await expectDarkThemeSettled(page);
    if (dashboard.variant === "student") {
      const contrast = await page.locator(".dashboard-opportunities button.btn.secondary").evaluate((element) => {
        const channels = (value: string) => value.match(/[\d.]+/g)!.map(Number);
        const luminance = (rgb: number[]) => rgb.map((channel) => channel / 255)
          .map((channel) => channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4)
          .reduce((total, channel, index) => total + channel * [0.2126, 0.7152, 0.0722][index], 0);
        const values = [luminance(channels(getComputedStyle(element).color)), luminance(channels(getComputedStyle(element).backgroundColor))].sort((a, b) => b - a);
        return (values[0] + 0.05) / (values[1] + 0.05);
      });
      expect(contrast).toBeGreaterThanOrEqual(4.5);
    }
    await captureVisual(page, `dashboard-${dashboard.variant}-dark`);
  });
}

test("rutas operativas conservan su navegación, estado vacío y layout móvil", async ({ page }) => {
  const pageErrors: string[] = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
  await mockEmptyApi(page, userFor("ALL_ROLES"));

  for (const route of operationalRoutes) {
    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.goto(`/#/${route}`);
    await expect(page.locator(".page-stack")).toBeVisible();
    await expect(page.locator(".topbar-context .topbar-title")).not.toBeEmpty();
    await expect(page.locator("main h1")).toHaveCount(1);
    await expect(page.locator('.sidebar .nav[aria-current="page"]')).toBeVisible();
    await captureVisual(page, `route-${route}-desktop`);
    await expectNoHorizontalOverflow(page, 1440);
    await expectNoHorizontalOverflow(page, 1024);
    await expectNoHorizontalOverflow(page, 768);
    await expectNoHorizontalOverflow(page, 390);
    await expectNoHorizontalOverflow(page, 320);
    await page.setViewportSize({ width: 390, height: 844 });
    await expect(page.locator(".sidebar-nav")).toBeHidden();
    await page.getByRole("button", { name: "Abrir menú de navegación" }).click();
    await expect(page.locator('.sidebar .nav[aria-current="page"]')).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(page.locator(".sidebar-nav")).toBeHidden();
    await captureVisual(page, `route-${route}-mobile`);
  }

  const reportsLinks = page.locator('.sidebar .nav').filter({ hasText: "Reportes operativos" });
  await expect(reportsLinks).toHaveCount(1);
  await page.getByLabel("Apariencia").selectOption("dark");
  for (const route of operationalRoutes) {
    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.goto(`/#/${route}`);
    await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
    await expect.poll(() => page.locator("html").evaluate((element) => getComputedStyle(element).colorScheme)).toBe("dark");
    await expectDarkThemeSettled(page);
    if (["opportunities", "documents", "dossier", "notifications", "reports"].includes(route)) {
      await captureVisual(page, `route-${route}-dark`);
    }
  }
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  expect(pageErrors).toEqual([]);
});
