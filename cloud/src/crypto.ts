const encoder = new TextEncoder();
const decoder = new TextDecoder();

export function base64Url(bytes: Uint8Array): string {
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary).replaceAll("+", "-").replaceAll("/", "_").replace(/=+$/g, "");
}

function ownedBytes(value: Uint8Array): Uint8Array<ArrayBuffer> {
  const copy = new Uint8Array(value.byteLength);
  copy.set(value);
  return copy;
}

export function fromBase64(value: string): Uint8Array<ArrayBuffer> {
  const normalized = value.replaceAll("-", "+").replaceAll("_", "/");
  const padded = normalized + "=".repeat((4 - normalized.length % 4) % 4);
  const binary = atob(padded);
  return ownedBytes(Uint8Array.from(binary, (character) => character.charCodeAt(0)));
}

export function randomToken(bytes = 32): string {
  return base64Url(crypto.getRandomValues(new Uint8Array(bytes)));
}

export async function sha256(value: string | Uint8Array): Promise<string> {
  const bytes = ownedBytes(typeof value === "string" ? encoder.encode(value) : value);
  return base64Url(new Uint8Array(await crypto.subtle.digest("SHA-256", bytes)));
}

export async function sha256Hex(value: string | Uint8Array): Promise<string> {
  const bytes = ownedBytes(typeof value === "string" ? encoder.encode(value) : value);
  return Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", bytes)), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

async function aesKey(base64: string): Promise<CryptoKey> {
  const raw = fromBase64(base64);
  if (raw.byteLength !== 32) throw new Error("AES-GCM key must be exactly 32 bytes");
  return crypto.subtle.importKey("raw", raw, "AES-GCM", false, ["encrypt", "decrypt"]);
}

export async function seal(plaintext: Uint8Array, keyBase64: string, associatedData: string): Promise<{ iv: string; ciphertext: string }> {
  const iv = ownedBytes(crypto.getRandomValues(new Uint8Array(12)));
  const encrypted = await crypto.subtle.encrypt(
    { name: "AES-GCM", iv, additionalData: ownedBytes(encoder.encode(associatedData)), tagLength: 128 },
    await aesKey(keyBase64),
    ownedBytes(plaintext),
  );
  return { iv: base64Url(iv), ciphertext: base64Url(new Uint8Array(encrypted)) };
}

export async function open(envelope: { iv: string; ciphertext: string }, keyBase64: string, associatedData: string): Promise<Uint8Array> {
  const plaintext = await crypto.subtle.decrypt(
    { name: "AES-GCM", iv: fromBase64(envelope.iv), additionalData: ownedBytes(encoder.encode(associatedData)), tagLength: 128 },
    await aesKey(keyBase64),
    fromBase64(envelope.ciphertext),
  );
  return new Uint8Array(plaintext);
}

export const encode = (value: string): Uint8Array => encoder.encode(value);
export const decode = (value: Uint8Array): string => decoder.decode(value);

const SECRET_KEYS = /(?:secret|token|password|credential|api[_-]?key)/i;
export function assertSecretFree(value: unknown, path = "value"): void {
  if (Array.isArray(value)) return value.forEach((item, index) => assertSecretFree(item, `${path}[${index}]`));
  if (!value || typeof value !== "object") return;
  for (const [key, child] of Object.entries(value as Record<string, unknown>)) {
    if (SECRET_KEYS.test(key)) throw new Error(`${path}.${key} is a forbidden secret field`);
    assertSecretFree(child, `${path}.${key}`);
  }
}
