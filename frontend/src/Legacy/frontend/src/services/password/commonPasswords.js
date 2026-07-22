/**
 * A small subset of extremely common passwords used for client-side
 * pre-validation. This is NOT a security measure — the backend performs
 * full password validation. This set only provides instant UX feedback.
 */
const COMMON_PASSWORDS = new Set([
  "password",
  "123456",
  "12345678",
  "1234567890",
  "qwerty",
  "abc123",
  "password1",
  "111111",
  "123123",
  "admin",
  "letmein",
  "welcome",
  "monkey",
  "dragon",
  "master",
  "qwerty123",
  "login",
  "princess",
  "football",
  "shadow",
  "sunshine",
  "trustno1",
  "iloveyou",
  "batman",
  "access",
  "hello",
  "charlie",
  "donald",
  "passw0rd",
  "qwerty1",
  "654321",
  "1q2w3e4r",
  "minecraft",
]);

/**
 * Quick client-side check for obviously common passwords.
 * @param {string} password
 * @returns {boolean}
 */
export function isObviouslyCommonPassword(password) {
  if (!password) return false;
  return COMMON_PASSWORDS.has(String(password).toLowerCase().trim());
}
