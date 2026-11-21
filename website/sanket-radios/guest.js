/** Shared guest for free Sanket relay rooms. The relay requires a sign-in even for public rooms. */
import { getToken, signIn } from "../ptt2/relay/auth.js";

export const GUEST_EMAIL = "operator@relay.local";
export const GUEST_PASSWORD = "Radio123!";

export async function ensureGuest() {
  if (!getToken()) await signIn(GUEST_EMAIL, GUEST_PASSWORD, false);
  return getToken();
}
