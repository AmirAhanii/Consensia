export function getAccessToken(): string | null {
  return localStorage.getItem("consensia_access_token");
}

export function authHeaders(): Record<string, string> {
  const token = getAccessToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export function clearAuthSession(): void {
  localStorage.removeItem("consensia_access_token");
  localStorage.removeItem("consensia_token_type");
  localStorage.removeItem("consensia_user_email");
  localStorage.removeItem("consensia_user_name");
  localStorage.removeItem("consensia_is_admin");
  window.dispatchEvent(new Event("consensia-auth-changed"));
}
