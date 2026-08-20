import ipaddr from "ipaddr.js";

import { sha256 } from "./crypto.js";
import type { FetchBinding } from "./platform.js";

const MAX_REDIRECTS = 3;
const MAX_ENDPOINT_LENGTH = 4096;
const MAX_DNS_NAME_LENGTH = 253;
const MAX_DNS_LABEL_LENGTH = 63;
const MAX_DNS_ANSWERS = 32;
const MAX_DNS_ANSWER_BYTES = 2048;
const MAX_DNS_RESPONSE_BYTES = 64 * 1024;

export interface DnsResolver { resolve(hostname: string): Promise<string[]>; }
export interface EndpointProbe {
  probe(url: URL, expectedAddresses: string[], resolutionFingerprint: string): Promise<{ status: number; location?: string }>;
}

export type EndpointValidationCode =
  | "endpoint_url_invalid"
  | "endpoint_https_required"
  | "endpoint_credentials_forbidden"
  | "endpoint_port_forbidden"
  | "endpoint_hostname_forbidden"
  | "endpoint_address_forbidden"
  | "endpoint_dns_failed"
  | "endpoint_dns_rebinding"
  | "endpoint_probe_failed"
  | "endpoint_probe_invalid"
  | "endpoint_redirect_invalid";

export class EndpointValidationError extends Error {
  constructor(public readonly code: EndpointValidationCode, message: string) {
    super(message);
    this.name = "EndpointValidationError";
  }
}

interface ParsedEndpoint {
  url: URL;
  hostname: string;
  literalAddress?: string;
}

interface RawAuthority {
  host: string;
  bracketed: boolean;
}

function invalid(code: EndpointValidationCode, message: string): EndpointValidationError {
  return new EndpointValidationError(code, message);
}

function rawAuthority(value: string): RawAuthority | undefined {
  const authorityMatch = /^(?:[a-z][a-z\d+.-]*:)?\/\/([^/?#]*)/i.exec(value);
  if (!authorityMatch) return undefined;
  const authority = authorityMatch[1];
  const hostPort = authority.slice(authority.lastIndexOf("@") + 1);
  if (hostPort.startsWith("[")) {
    const close = hostPort.indexOf("]");
    if (close < 0) return { host: hostPort.slice(1), bracketed: true };
    return { host: hostPort.slice(1, close), bracketed: true };
  }
  const colon = hostPort.lastIndexOf(":");
  return { host: colon >= 0 ? hostPort.slice(0, colon) : hostPort, bracketed: false };
}

function strictIpv4(value: string): boolean {
  if (!/^\d+(?:\.\d+){3}$/.test(value)) return false;
  return value.split(".").every((part) => {
    if (!/^(?:0|[1-9]\d{0,2})$/.test(part)) return false;
    const number = Number(part);
    return Number.isInteger(number) && number >= 0 && number <= 255;
  });
}

function numericLookingIpv4(value: string): boolean {
  return /^[\d.]+$/.test(value) || /^0x[\da-f]+$/i.test(value);
}

function classifyPublicAddress(address: string): string {
  if (typeof address !== "string" || address.length === 0 || address !== address.trim() || /[%\u0000-\u0020\u007f]/.test(address)) {
    throw invalid("endpoint_address_forbidden", "endpoint address is invalid or not public");
  }

  if (!address.includes(":")) {
    if (numericLookingIpv4(address) && !strictIpv4(address)) {
      throw invalid("endpoint_address_forbidden", "endpoint address is invalid or not public");
    }
    if (!strictIpv4(address)) {
      throw invalid("endpoint_address_forbidden", "endpoint address is invalid or not public");
    }
  } else {
    if (address.includes(".")) {
      const dottedTail = address.slice(address.lastIndexOf(":") + 1);
      if (!strictIpv4(dottedTail)) {
        throw invalid("endpoint_address_forbidden", "endpoint address is invalid or not public");
      }
    }
    if (!/^[0-9a-f:.]+$/i.test(address)) {
      throw invalid("endpoint_address_forbidden", "endpoint address is invalid or not public");
    }
  }

  let parsed: ipaddr.IPv4 | ipaddr.IPv6;
  try {
    parsed = ipaddr.parse(address);
  } catch {
    throw invalid("endpoint_address_forbidden", "endpoint address is invalid or not public");
  }

  if (parsed.kind() === "ipv6") {
    const ipv6 = parsed as ipaddr.IPv6;
    if (ipv6.isIPv4MappedAddress()) {
      const mapped = ipv6.toIPv4Address();
      if (mapped.range() !== "unicast") {
        throw invalid("endpoint_address_forbidden", "endpoint address is invalid or not public");
      }
      return mapped.toNormalizedString();
    }
    if (ipv6.range() !== "unicast") {
      throw invalid("endpoint_address_forbidden", "endpoint address is invalid or not public");
    }
    return ipv6.toRFC5952String().toLowerCase();
  }

  const ipv4 = parsed as ipaddr.IPv4;
  if (ipv4.range() !== "unicast") {
    throw invalid("endpoint_address_forbidden", "endpoint address is invalid or not public");
  }
  return ipv4.toNormalizedString();
}

function canonicalDnsName(hostname: string): string {
  const canonical = hostname.toLowerCase();
  const withoutRootDot = canonical.endsWith(".") ? canonical.slice(0, -1) : canonical;
  if (
    !withoutRootDot ||
    withoutRootDot.length > MAX_DNS_NAME_LENGTH ||
    !withoutRootDot.includes(".") ||
    !/^[a-z0-9.-]+$/.test(withoutRootDot) ||
    withoutRootDot.startsWith(".") ||
    withoutRootDot.endsWith(".")
  ) {
    throw invalid("endpoint_hostname_forbidden", "endpoint hostname is not a public DNS name");
  }
  const labels = withoutRootDot.split(".");
  if (labels.some((label) => label.length === 0 || label.length > MAX_DNS_LABEL_LENGTH || label.startsWith("-") || label.endsWith("-") || !/^[a-z0-9-]+$/.test(label))) {
    throw invalid("endpoint_hostname_forbidden", "endpoint hostname is not a public DNS name");
  }
  if (
    withoutRootDot === "localhost" ||
    withoutRootDot.endsWith(".localhost") ||
    withoutRootDot.endsWith(".local") ||
    withoutRootDot.endsWith(".internal") ||
    withoutRootDot.endsWith(".home.arpa")
  ) {
    throw invalid("endpoint_hostname_forbidden", "local and internal endpoint names are forbidden");
  }
  return withoutRootDot;
}

function rejectNumericAuthority(raw: RawAuthority | undefined): void {
  if (!raw || raw.bracketed || !numericLookingIpv4(raw.host)) return;
  if (!strictIpv4(raw.host)) {
    throw invalid("endpoint_address_forbidden", "endpoint address is invalid or not public");
  }
}

function parseEndpoint(value: string): ParsedEndpoint {
  if (typeof value !== "string" || value.length === 0 || value.length > MAX_ENDPOINT_LENGTH || /[\u0000-\u0020\u007f]/.test(value)) {
    throw invalid("endpoint_url_invalid", "endpoint must be an absolute URL");
  }

  const raw = rawAuthority(value);
  if (!raw || !raw.host) {
    throw invalid("endpoint_url_invalid", "endpoint must be an absolute URL");
  }
  if (raw?.host.includes("%")) {
    throw invalid("endpoint_address_forbidden", "endpoint address is invalid or not public");
  }
  rejectNumericAuthority(raw);

  let url: URL;
  try {
    url = new URL(value);
  } catch {
    throw invalid("endpoint_url_invalid", "endpoint must be an absolute URL");
  }
  if (url.protocol !== "https:") throw invalid("endpoint_https_required", "hosted endpoints require HTTPS");
  if (url.username || url.password) throw invalid("endpoint_credentials_forbidden", "endpoint URL cannot contain credentials");
  if (url.port && url.port !== "443") throw invalid("endpoint_port_forbidden", "hosted endpoints use HTTPS port 443 only");

  const hostname = url.hostname.replace(/^\[/, "").replace(/\]$/, "").toLowerCase();
  if (!hostname) throw invalid("endpoint_hostname_forbidden", "endpoint hostname is not a public DNS name");

  let literalAddress: string | undefined;
  if (raw?.bracketed || strictIpv4(raw?.host ?? "")) {
    literalAddress = classifyPublicAddress(raw?.host ?? hostname);
    if (literalAddress.includes(":")) url.hostname = `[${literalAddress}]`;
    else url.hostname = literalAddress;
  } else {
    if (raw && !/^[a-z0-9.-]+$/i.test(raw.host)) {
      throw invalid("endpoint_hostname_forbidden", "endpoint hostname is not a public DNS name");
    }
    const canonical = canonicalDnsName(hostname);
    url.hostname = canonical;
    return { url: stripFragment(url), hostname: canonical };
  }

  return { url: stripFragment(url), hostname: literalAddress ?? hostname, literalAddress };
}

function stripFragment(url: URL): URL {
  url.hash = "";
  return url;
}

async function resolveAddresses(parsed: ParsedEndpoint, resolver: DnsResolver): Promise<string[]> {
  if (parsed.literalAddress) return [parsed.literalAddress];
  let values: string[];
  try {
    values = await resolver.resolve(parsed.hostname);
  } catch (error) {
    if (error instanceof EndpointValidationError) throw error;
    throw invalid("endpoint_dns_failed", "public DNS validation failed");
  }
  if (!Array.isArray(values)) throw invalid("endpoint_dns_failed", "public DNS validation failed");
  if (
    values.length > MAX_DNS_ANSWERS ||
    values.reduce((total, value) => total + (typeof value === "string" ? value.length : MAX_DNS_ANSWER_BYTES), 0) > MAX_DNS_ANSWER_BYTES
  ) {
    throw invalid("endpoint_dns_failed", "public DNS validation returned too many addresses");
  }
  const canonical = new Set<string>();
  for (const value of values) canonical.add(classifyPublicAddress(value));
  const addresses = [...canonical].sort();
  if (addresses.length === 0) throw invalid("endpoint_address_forbidden", "endpoint DNS has no public addresses");
  return addresses;
}

async function stableResolution(parsed: ParsedEndpoint, resolver: DnsResolver): Promise<{ addresses: string[]; fingerprint: string }> {
  const first = await resolveAddresses(parsed, resolver);
  const second = await resolveAddresses(parsed, resolver);
  if (first.join("\n") !== second.join("\n")) {
    throw invalid("endpoint_dns_rebinding", "endpoint DNS changed during validation");
  }
  return {
    addresses: first,
    fingerprint: await sha256(`${parsed.hostname}\n${first.join("\n")}`),
  };
}

function resolveRedirect(location: string, current: URL): string {
  if (typeof location !== "string" || location.length === 0 || location.length > MAX_ENDPOINT_LENGTH || /[\u0000-\u0020\u007f]/.test(location)) {
    throw invalid("endpoint_redirect_invalid", "endpoint redirect chain is invalid or too long");
  }
  const raw = rawAuthority(location);
  if (raw?.host.includes("%")) throw invalid("endpoint_address_forbidden", "endpoint address is invalid or not public");
  rejectNumericAuthority(raw);
  try {
    return new URL(location, current).href;
  } catch {
    throw invalid("endpoint_redirect_invalid", "endpoint redirect chain is invalid or too long");
  }
}

async function probeValidatedEndpoint(dependencies: { probe: EndpointProbe }, url: URL, addresses: string[], fingerprint: string): Promise<{ status: number; location?: string }> {
  let response: { status: number; location?: string };
  try {
    response = await dependencies.probe.probe(url, addresses, fingerprint);
  } catch (error) {
    if (error instanceof EndpointValidationError) throw error;
    throw invalid("endpoint_probe_failed", "endpoint probe failed");
  }
  if (!response || !Number.isInteger(response.status) || response.status < 100 || response.status > 599 || (response.location !== undefined && typeof response.location !== "string")) {
    throw invalid("endpoint_probe_invalid", "endpoint probe returned an invalid response");
  }
  return response;
}

export async function validateHostedEndpoint(value: string, dependencies: { resolver: DnsResolver; probe: EndpointProbe }): Promise<{
  schema: "quillframe_hosted_endpoint_validation_v1";
  endpoint: string;
  resolution_fingerprint: string;
  resolution_passes: 2;
  redirects: number;
  credential_sent: false;
  authority: false;
}> {
  let parsed = parseEndpoint(value);
  let redirects = 0;
  let finalFingerprint = "";
  while (true) {
    const resolution = await stableResolution(parsed, dependencies.resolver);
    finalFingerprint = resolution.fingerprint;
    const response = await probeValidatedEndpoint(dependencies, parsed.url, resolution.addresses, resolution.fingerprint);
    if (response.status < 300 || response.status >= 400) break;
    if (redirects >= MAX_REDIRECTS || !response.location) {
      throw invalid("endpoint_redirect_invalid", "endpoint redirect chain is invalid or too long");
    }
    parsed = parseEndpoint(resolveRedirect(response.location, parsed.url));
    redirects += 1;
  }
  return {
    schema: "quillframe_hosted_endpoint_validation_v1",
    endpoint: parsed.url.href,
    resolution_fingerprint: finalFingerprint,
    resolution_passes: 2,
    redirects,
    credential_sent: false,
    authority: false,
  };
}

export class CloudflareDnsResolver implements DnsResolver {
  constructor(private readonly fetcher: typeof globalThis.fetch = globalThis.fetch) {}
  async resolve(hostname: string): Promise<string[]> {
    const values = new Set<string>();
    let answerCount = 0;
    let answerBytes = 0;
    try {
      for (const type of ["A", "AAAA"]) {
        const url = new URL("https://cloudflare-dns.com/dns-query");
        url.search = new URLSearchParams({ name: hostname, type }).toString();
        const response = await this.fetcher(new Request(url, { headers: { accept: "application/dns-json" } }));
        if (!response.ok) throw invalid("endpoint_dns_failed", "public DNS validation failed");
        const body = await readBoundedDnsResponse(response);
        let payload: unknown;
        try {
          payload = JSON.parse(body) as unknown;
        } catch {
          throw invalid("endpoint_dns_failed", "public DNS validation failed");
        }
        if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
          throw invalid("endpoint_dns_failed", "public DNS validation failed");
        }
        const answer = (payload as { Answer?: unknown }).Answer;
        if (answer === undefined) continue;
        if (!Array.isArray(answer) || answerCount + answer.length > MAX_DNS_ANSWERS) {
          throw invalid("endpoint_dns_failed", "public DNS validation returned too many records");
        }
        answerCount += answer.length;
        for (const record of answer) {
          if (!record || typeof record !== "object" || Array.isArray(record)) {
            throw invalid("endpoint_dns_failed", "public DNS validation failed");
          }
          const recordType = (record as { type?: unknown }).type;
          const recordData = (record as { data?: unknown }).data;
          if (recordType !== 1 && recordType !== 28) continue;
          if (typeof recordData !== "string") {
            throw invalid("endpoint_dns_failed", "public DNS validation failed");
          }
          answerBytes += recordData.length;
          if (answerBytes > MAX_DNS_ANSWER_BYTES) {
            throw invalid("endpoint_dns_failed", "public DNS validation returned too many addresses");
          }
          values.add(recordData);
        }
      }
    } catch (error) {
      if (error instanceof EndpointValidationError) throw error;
      throw invalid("endpoint_dns_failed", "public DNS validation failed");
    }
    return [...values];
  }
}

async function readBoundedDnsResponse(response: Response): Promise<string> {
  const contentLength = response.headers.get("content-length");
  if (contentLength !== null) {
    const declaredLength = Number(contentLength);
    if (!/^\d+$/.test(contentLength.trim()) || !Number.isSafeInteger(declaredLength) || declaredLength > MAX_DNS_RESPONSE_BYTES) {
      throw invalid("endpoint_dns_failed", "public DNS validation response is too large");
    }
  }

  if (!response.body) return "";
  const reader = response.body.getReader();
  const chunks: Uint8Array[] = [];
  let totalBytes = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      if (!(value instanceof Uint8Array)) throw invalid("endpoint_dns_failed", "public DNS validation failed");
      totalBytes += value.byteLength;
      if (totalBytes > MAX_DNS_RESPONSE_BYTES) {
        try { await reader.cancel(); } catch { /* best-effort stream cancellation */ }
        throw invalid("endpoint_dns_failed", "public DNS validation response is too large");
      }
      chunks.push(value);
    }
  } catch (error) {
    if (error instanceof EndpointValidationError) throw error;
    throw invalid("endpoint_dns_failed", "public DNS validation failed");
  } finally {
    reader.releaseLock();
  }

  const bytes = new Uint8Array(totalBytes);
  let offset = 0;
  for (const chunk of chunks) {
    bytes.set(chunk, offset);
    offset += chunk.byteLength;
  }
  try {
    return new TextDecoder("utf-8", { fatal: true }).decode(bytes);
  } catch {
    throw invalid("endpoint_dns_failed", "public DNS validation failed");
  }
}

export class BoundEndpointProbe implements EndpointProbe {
  constructor(private readonly binding: FetchBinding) {}
  async probe(url: URL, expectedAddresses: string[], resolutionFingerprint: string): Promise<{ status: number; location?: string }> {
    const response = await this.binding.fetch(new Request("https://endpoint-egress.internal/probe", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ endpoint: url.href, expected_addresses: expectedAddresses, resolution_fingerprint: resolutionFingerprint }),
    }));
    const location = response.headers.get("location") ?? undefined;
    return { status: response.status, location };
  }
}
