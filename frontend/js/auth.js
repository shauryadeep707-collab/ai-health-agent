/* =============================================================================
   AI HEALTH AGENT — AUTH & SESSION MANAGER (auth.js)
   ============================================================================= */

const AUTH_TOKEN_KEY = "ai_health_token";
const AUTH_USER_KEY = "ai_health_user";

const Auth = {
  getToken() {
    return localStorage.getItem(AUTH_TOKEN_KEY);
  },

  setToken(token) {
    if (token) {
      localStorage.setItem(AUTH_TOKEN_KEY, token);
    } else {
      localStorage.removeItem(AUTH_TOKEN_KEY);
    }
  },

  getUser() {
    const raw = localStorage.getItem(AUTH_USER_KEY);
    try {
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  },

  setUser(user) {
    if (user) {
      localStorage.setItem(AUTH_USER_KEY, JSON.stringify(user));
    } else {
      localStorage.removeItem(AUTH_USER_KEY);
    }
  },

  isAuthenticated() {
    return Boolean(this.getToken() && this.getUser());
  },

  async fetchWithAuth(url, options = {}) {
    options.headers = options.headers || {};
    const token = this.getToken();
    if (token) {
      options.headers["Authorization"] = `Bearer ${token}`;
    }
    // Set Content-Type only if not sending FormData
    if (!(options.body instanceof FormData) && !options.headers["Content-Type"]) {
      options.headers["Content-Type"] = "application/json";
    }

    try {
      const response = await fetch(url, options);
      if (response.status === 401) {
        // Token expired or invalid
        this.logout();
        window.location.href = "/patient-login.html?expired=1";
        return null;
      }
      return response;
    } catch (err) {
      console.error("Network request error:", err);
      throw err;
    }
  },

  async login(email, password, role) {
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password, role })
    });
    const data = await res.json();
    if (res.ok && data.success) {
      this.setToken(data.token);
      this.setUser(data.user);
      return { success: true, user: data.user };
    }
    return { success: false, error: data.error || "Login failed." };
  },

  async logout() {
    try {
      await fetch("/api/auth/logout", { method: "POST" });
    } catch (e) {
      // Ignore network errors on logout
    }
    localStorage.removeItem(AUTH_TOKEN_KEY);
    localStorage.removeItem(AUTH_USER_KEY);
    window.location.href = "/";
  },

  guardPage(expectedRole) {
    const user = this.getUser();
    const token = this.getToken();
    if (!token || !user) {
      const redirect = expectedRole === "DOCTOR" ? "/doctor-login.html" : "/patient-login.html";
      window.location.href = `${redirect}?redirect=${encodeURIComponent(window.location.pathname)}`;
      return false;
    }

    if (expectedRole && user.role !== expectedRole) {
      alert(`Access denied. This page is only for ${expectedRole.toLowerCase()}s.`);
      window.location.href = user.role === "DOCTOR" ? "/doctor-dashboard.html" : "/patient-dashboard.html";
      return false;
    }

    return true;
  },

  updateHeaderNav() {
    const user = this.getUser();
    const navActions = document.getElementById("nav-actions");
    if (!navActions) return;

    if (user) {
      const dashboardUrl = user.role === "DOCTOR" ? "/doctor-dashboard.html" : "/patient-dashboard.html";
      navActions.innerHTML = `
        <span style="font-size:0.9rem; font-weight:600; color:var(--dark);">
          👤 ${user.full_name} (${user.role})
        </span>
        <a href="${dashboardUrl}" class="btn btn-primary btn-sm">Dashboard</a>
        <button onclick="Auth.logout()" class="btn btn-outline btn-sm">Log Out</button>
      `;
    }
  },

  async checkDatabasePersistence() {
    const alertBox = document.getElementById("alert-box");
    if (!alertBox) return;

    const host = window.location.hostname;
    const isLocal = host === "127.0.0.1" || host === "localhost" || host === "";
    if (isLocal) return;

    try {
      const res = await fetch("/api/health");
      if (!res.ok) return;
      const data = await res.json();
      if (data && data.is_persistent_cloud_db === false) {
        let banner = document.getElementById("cloud-db-warning");
        if (!banner) {
          banner = document.createElement("div");
          banner.id = "cloud-db-warning";
          banner.style.cssText =
            "background:#fffbeb;border:1px solid #f59e0b;color:#92400e;border-radius:8px;padding:0.8rem 1rem;margin-bottom:1rem;font-size:0.83rem;line-height:1.45;";
          alertBox.parentNode.insertBefore(banner, alertBox);
        }
        banner.innerHTML = `
          <strong>⚠️ Temporary Storage Mode Active:</strong> Cloud PostgreSQL (<code>DATABASE_URL</code>) is not connected yet, so new accounts reset when the server restarts.<br>
          <span style="color:#78350f;">Fix: Add a PostgreSQL <code>DATABASE_URL</code> in Render Environment Variables &amp; redeploy for permanent storage.</span>
        `;
      }
    } catch (e) {
      // Ignore silent health check errors
    }
  }
};

document.addEventListener("DOMContentLoaded", () => {
  Auth.updateHeaderNav();
  Auth.checkDatabasePersistence();
});
