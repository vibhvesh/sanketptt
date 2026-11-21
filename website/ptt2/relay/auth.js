/** Sign-in for the Sanket channel service. The token stays in this tab. The password is saved only when Remember me is checked. */

import { SANKET_RELAY_ORIGIN } from "./config.js";

const TOKEN_KEY = "sanket.ptt2.token";
const REMEMBER_KEY = "sanket.ptt2.remember";

let memoryEmail = "";
let memoryPassword = "";

function readToken() {
  try {
    return sessionStorage.getItem(TOKEN_KEY) || "";
  } catch (e) {
    return "";
  }
}

function writeToken(token) {
  try {
    if (token) sessionStorage.setItem(TOKEN_KEY, token);
    else sessionStorage.removeItem(TOKEN_KEY);
  } catch (e) {
    /* private mode */
  }
}

export function getToken() {
  return readToken();
}

/** Email and password for transcribe basic auth. Null when this tab has not signed in. */
export function getCredentials() {
  if (memoryEmail && memoryPassword) return { email: memoryEmail, password: memoryPassword };
  try {
    const saved = JSON.parse(localStorage.getItem(REMEMBER_KEY) || "null");
    if (saved && saved.email && saved.password) return { email: saved.email, password: saved.password };
  } catch (e) {
    /* ignore */
  }
  return null;
}

export function rememberedLogin() {
  const creds = getCredentials();
  if (!creds) return null;
  try {
    if (!localStorage.getItem(REMEMBER_KEY)) return null;
  } catch (e) {
    return null;
  }
  return creds;
}

export async function signIn(email, password, remember) {
  const response = await fetch(SANKET_RELAY_ORIGIN + "/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: String(email || "").trim(), password: String(password || "") }),
  });
  const data = await response.json().catch(() => ({}));
  if (response.status === 401) {
    const error = new Error("Sign-in failed. Check the email and password.");
    error.status = 401;
    throw error;
  }
  if (!response.ok || !data.token) {
    const message = data && data.error && data.error.message ? data.error.message : "Sign-in failed (" + response.status + ").";
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }
  writeToken(data.token);
  memoryEmail = String(email || "").trim();
  memoryPassword = String(password || "");
  try {
    if (remember) localStorage.setItem(REMEMBER_KEY, JSON.stringify({ email: memoryEmail, password: memoryPassword }));
    else localStorage.removeItem(REMEMBER_KEY);
  } catch (e) {
    /* ignore */
  }
  return data;
}

export function signOut() {
  memoryEmail = "";
  memoryPassword = "";
  writeToken("");
  try {
    localStorage.removeItem(REMEMBER_KEY);
    localStorage.removeItem("sanket.ptt2.signedIn");
  } catch (e) {
    /* ignore */
  }
}

export function basicAuthHeader() {
  const creds = getCredentials();
  if (!creds) return "";
  return "Basic " + btoa(creds.email + ":" + creds.password);
}
