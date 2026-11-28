/** Demo sign-in for the free Virtual channel. One shared account, never a login form. */
import { signIn } from "./auth.js";

export const VIRTUAL_DEMO = Object.freeze({
  email: "apple@apple.com",
  password: "12345678",
  roomId: "RM-FG7S",
  label: "Virtual",
  publicId: "virtual",
});

export function isVirtualFreeChannel(channel) {
  const id = String(channel || "").trim().toLowerCase();
  return id === VIRTUAL_DEMO.publicId || id === VIRTUAL_DEMO.roomId.toLowerCase();
}

/** Sign in for this tab only. The password is not written to localStorage. */
export async function ensureVirtualDemo() {
  await signIn(VIRTUAL_DEMO.email, VIRTUAL_DEMO.password, false);
}
