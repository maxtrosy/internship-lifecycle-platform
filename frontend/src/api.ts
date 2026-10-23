export type User = {
  id: number;
  display_name: string;
  email: string | null;
  roles: { role: string; program_id: number | null; host_org_id: number | null }[];
};

export type Opportunity = {
  id: number;
  host_org_id: number;
  program_id: number;
  title: string;
  state: string;
  program_code: string;
  host_name: string;
};

export type Application = {
  id: number;
  opportunity_id: number;
  state: string;
  eligibility_result: Record<string, unknown> | null;
  title: string;
};

const TOKEN_KEY = "dh05_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null): void {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string> | undefined),
  };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  const resp = await fetch(path, { ...options, headers });
  if (!resp.ok) {
    let detail = resp.statusText;
    try {
      const body = await resp.json();
      detail = body.error ?? body.detail ?? JSON.stringify(body);
    } catch {
      /* ignore */
    }
    throw new Error(detail as string);
  }
  if (resp.status === 204) return undefined as T;
  return (await resp.json()) as T;
}

export function login(user_id: number): Promise<{ access_token: string }> {
  return request<{ access_token: string }>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ user_id }),
  });
}

export function me(): Promise<User> {
  return request<User>("/auth/me");
}

export function listOpportunities(): Promise<Opportunity[]> {
  return request<Opportunity[]>("/opportunities");
}

export function createOpportunity(body: {
  host_org_id: number;
  program_id: number;
  title: string;
}): Promise<{ id: number }> {
  return request<{ id: number }>("/opportunities", { method: "POST", body: JSON.stringify(body) });
}

export function apply(opportunity_id: number): Promise<Record<string, unknown>> {
  return request<Record<string, unknown>>(`/opportunities/${opportunity_id}/apply`, { method: "POST" });
}

export function listApplications(): Promise<Application[]> {
  return request<Application[]>("/applications");
}
