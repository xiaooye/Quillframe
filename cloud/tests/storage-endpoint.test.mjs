import assert from "node:assert/strict";
import test from "node:test";

import { BoundEndpointProbe, CloudflareDnsResolver, EndpointValidationError, validateHostedEndpoint } from "../dist/endpoint-validator.js";
const stableResolver = { resolve: async (hostname) => hostname === "models.example.com" ? ["203.0.114.20", "2606:4700:4700::1111"] : ["203.0.114.21"] };
const stableProbe = { probe: async () => ({ status: 204 }) };

test("hosted endpoint validator permits stable public HTTPS only", async () => {
  const proof = await validateHostedEndpoint("https://models.example.com/v1", { resolver: stableResolver, probe: stableProbe });
  assert.equal(proof.schema, "quillframe_hosted_endpoint_validation_v1");
  assert.equal(proof.endpoint, "https://models.example.com/v1");
  assert.equal(proof.authority, false);
  assert.equal(proof.resolution_passes, 2);
});

test("hosted endpoint validator rejects schemes, credentials, local names, and private/reserved IPs", async () => {
  for (const endpoint of [
    "http://models.example.com/v1",
    "https://user:pass@models.example.com/v1",
    "https://localhost/v1",
    "https://127.0.0.1/v1",
    "https://10.0.0.8/v1",
    "https://[::1]/v1",
    "https://[fd00::1]/v1",
    "https://metadata.google.internal/v1",
  ]) {
    await assert.rejects(() => validateHostedEndpoint(endpoint, { resolver: stableResolver, probe: stableProbe }), EndpointValidationError, endpoint);
  }

  const privateResolver = { resolve: async () => ["169.254.169.254"] };
  await assert.rejects(() => validateHostedEndpoint("https://models.example.com/v1", { resolver: privateResolver, probe: stableProbe }), (error) => error.code === "endpoint_address_forbidden");
});

test("hosted endpoint validator fails closed on DNS rebinding and redirect pivots", async () => {
  let calls = 0;
  const rebindingResolver = { resolve: async () => (++calls === 1 ? ["203.0.114.20"] : ["10.0.0.8"]) };
  await assert.rejects(() => validateHostedEndpoint("https://models.example.com/v1", { resolver: rebindingResolver, probe: stableProbe }), EndpointValidationError);

  const redirectProbe = { probe: async () => ({ status: 302, location: "https://127.0.0.1/private" }) };
  await assert.rejects(() => validateHostedEndpoint("https://models.example.com/v1", { resolver: stableResolver, probe: redirectProbe }), EndpointValidationError);
});

test("hosted endpoint validator uses strict ipaddr classification for literals", async () => {
  const probeCalls = [];
  const probe = { probe: async (url, addresses, fingerprint) => {
    probeCalls.push({ url: url.href, addresses, fingerprint });
    return { status: 204 };
  } };
  const resolver = { resolve: async () => { throw new Error("literal endpoints must not use DNS"); } };

  for (const endpoint of [
    "https://127.0.0.1/v1",
    "https://[::1]/v1",
    "https://[0:0:0:0:0:0:0:1]/v1",
    "https://[::ffff:127.0.0.1]/v1",
    "https://[::ffff:10.0.0.1]/v1",
    "https://[::ffff:192.0.2.1]/v1",
    "https://[::ffff:169.254.1.1]/v1",
    "https://[::ffff:100.64.0.1]/v1",
    "https://[fe80::1]/v1",
    "https://[fc00::1]/v1",
    "https://[2001:db8::1]/v1",
    "https://[ff02::1]/v1",
    "https://[64:ff9b::1]/v1",
    "https://01.2.3.4/v1",
    "https://1.2.3/v1",
    "https://2130706433/v1",
    "https://0x7f000001/v1",
  ]) {
    await assert.rejects(
      () => validateHostedEndpoint(endpoint, { resolver, probe }),
      (error) => error instanceof EndpointValidationError && error.code === "endpoint_address_forbidden",
      endpoint,
    );
  }

  const accepted = await validateHostedEndpoint("https://[::ffff:1.1.1.1]/v1", { resolver, probe });
  assert.equal(accepted.endpoint, "https://1.1.1.1/v1");
  assert.equal(probeCalls.at(-1).addresses[0], "1.1.1.1");
  assert.equal(probeCalls.at(-1).fingerprint, accepted.resolution_fingerprint);
});

test("hosted endpoint validator does not accept URL parser backslash or empty-authority normalization", async () => {
  const resolver = { resolve: async () => ["1.1.1.1"] };
  const probe = { probe: async () => ({ status: 204 }) };
  for (const endpoint of [
    "https:\\\\127.0.0.1/v1",
    "https:////127.0.0.1/v1",
    "https:///127.0.0.1/v1",
    "https:127.0.0.1/v1",
  ]) {
    await assert.rejects(
      () => validateHostedEndpoint(endpoint, { resolver, probe }),
      (error) => error instanceof EndpointValidationError && error.code === "endpoint_url_invalid",
      endpoint,
    );
  }
});

test("hosted endpoint validator rejects invalid and mixed resolver answers before probing", async () => {
  let probes = 0;
  const probe = { probe: async () => { probes += 1; return { status: 204 }; } };
  for (const answers of [
    [],
    ["1.1.1.1", "10.0.0.1"],
    ["1.1.1.1", "01.2.3.4"],
    ["1.1.1.1", "not-an-address"],
  ]) {
    const resolver = { resolve: async () => answers };
    await assert.rejects(
      () => validateHostedEndpoint("https://models.example.com/v1", { resolver, probe }),
      (error) => error instanceof EndpointValidationError && error.code === "endpoint_address_forbidden",
    );
  }
  assert.equal(probes, 0);
});

test("hosted endpoint validator bounds resolver answer count and aggregate size", async () => {
  let probes = 0;
  const probe = { probe: async () => { probes += 1; return { status: 204 }; } };
  const tooMany = Array.from({ length: 33 }, (_, index) => `1.1.1.${(index % 254) + 1}`);
  const tooLarge = ["1.1.1.1", "8.8.8.8", "2606:4700:4700::1111".repeat(200)];
  for (const answers of [tooMany, tooLarge]) {
    const resolver = { resolve: async () => answers };
    await assert.rejects(
      () => validateHostedEndpoint("https://models.example.com/v1", { resolver, probe }),
      (error) => error instanceof EndpointValidationError && error.code === "endpoint_dns_failed",
    );
  }
  assert.equal(probes, 0);
});

test("hosted endpoint validator repeats DNS validation for every redirect hop", async () => {
  const lookups = [];
  const probes = [];
  const resolver = { resolve: async (hostname) => {
    lookups.push(hostname);
    return hostname === "models.example.com" ? ["1.1.1.1"] : ["8.8.8.8"];
  } };
  const probe = { probe: async (url, addresses, fingerprint) => {
    probes.push({ url: url.href, addresses, fingerprint });
    return probes.length === 1 ? { status: 302, location: "/v2" } : { status: 204 };
  } };
  const proof = await validateHostedEndpoint("https://models.example.com/v1", { resolver, probe });
  assert.equal(proof.endpoint, "https://models.example.com/v2");
  assert.equal(proof.redirects, 1);
  assert.deepEqual(lookups, ["models.example.com", "models.example.com", "models.example.com", "models.example.com"]);
  assert.deepEqual(probes.map(({ url }) => url), ["https://models.example.com/v1", "https://models.example.com/v2"]);
  assert.notEqual(probes[0].fingerprint, "");
});

test("hosted endpoint validator rejects private second hop, redirect credentials, and long chains", async () => {
  let probes = 0;
  const resolver = { resolve: async (hostname) => hostname === "public.example.com" ? ["1.1.1.1"] : ["10.0.0.1"] };
  const firstHopProbe = { probe: async () => { probes += 1; return { status: 302, location: "https://private.example.com/v1" }; } };
  await assert.rejects(
    () => validateHostedEndpoint("https://public.example.com/v1", { resolver, probe: firstHopProbe }),
    (error) => error instanceof EndpointValidationError && error.code === "endpoint_address_forbidden",
  );
  assert.equal(probes, 1);

  const credentialProbe = { probe: async () => ({ status: 302, location: "https://user:secret@public.example.com/v2" }) };
  const credentialError = await assert.rejects(
    () => validateHostedEndpoint("https://public.example.com/v1", { resolver, probe: credentialProbe }),
    (error) => error instanceof EndpointValidationError && error.code === "endpoint_credentials_forbidden" && !error.message.includes("secret"),
  );
  assert.equal(credentialError, undefined);

  let redirects = 0;
  const loopProbe = { probe: async () => ({ status: 302, location: `/hop-${++redirects}` }) };
  await assert.rejects(
    () => validateHostedEndpoint("https://public.example.com/v1", { resolver, probe: loopProbe }),
    (error) => error instanceof EndpointValidationError && error.code === "endpoint_redirect_invalid",
  );
  assert.equal(redirects, 4);
});

test("hosted endpoint validator rejects DNS rebind before the next probe", async () => {
  let lookups = 0;
  let probes = 0;
  const resolver = { resolve: async (hostname) => {
    lookups += 1;
    if (hostname === "public.example.com") return [lookups === 1 ? "1.1.1.1" : "8.8.8.8"];
    return ["1.1.1.1"];
  } };
  const probe = { probe: async () => { probes += 1; return { status: 204 }; } };
  await assert.rejects(
    () => validateHostedEndpoint("https://public.example.com/v1", { resolver, probe }),
    (error) => error instanceof EndpointValidationError && error.code === "endpoint_dns_rebinding",
  );
  assert.equal(probes, 0);
  assert.equal(lookups, 2);
});

test("hosted endpoint egress probe receives only the validated endpoint proof", async () => {
  let request;
  const binding = { fetch: async (value) => {
    request = value;
    return new Response(null, { status: 204 });
  } };
  await new BoundEndpointProbe(binding).probe(new URL("https://models.example.com/v1"), ["1.1.1.1"], "fingerprint");
  assert.deepEqual(await request.json(), {
    endpoint: "https://models.example.com/v1",
    expected_addresses: ["1.1.1.1"],
    resolution_fingerprint: "fingerprint",
  });
});

test("hosted endpoint DNS and probe dependency failures are typed and redacted", async () => {
  const probe = { probe: async () => { throw new Error("secret endpoint https://private.example.invalid"); } };
  const dnsError = await assert.rejects(
    () => validateHostedEndpoint("https://models.example.com/v1", { resolver: { resolve: async () => { throw new Error("secret dns host"); } }, probe }),
    (error) => error instanceof EndpointValidationError && error.code === "endpoint_dns_failed" && !error.message.includes("secret"),
  );
  assert.equal(dnsError, undefined);

  const probeError = await assert.rejects(
    () => validateHostedEndpoint("https://models.example.com/v1", { resolver: { resolve: async () => ["1.1.1.1"] }, probe }),
    (error) => error instanceof EndpointValidationError && error.code === "endpoint_probe_failed" && !error.message.includes("private"),
  );
  assert.equal(probeError, undefined);
});

test("Cloudflare DNS resolver rejects an oversized raw response before JSON decoding", async () => {
  let jsonCalls = 0;
  const body = new Response(new Uint8Array(64 * 1024 + 1));
  const resolver = new CloudflareDnsResolver(async () => ({
    ok: true,
    headers: body.headers,
    body: body.body,
    json: async () => { jsonCalls += 1; throw new Error("JSON decode must not run"); },
  }));
  await assert.rejects(
    () => resolver.resolve("models.example.com"),
    (error) => error instanceof EndpointValidationError && error.code === "endpoint_dns_failed" && !error.message.includes("JSON"),
  );
  assert.equal(jsonCalls, 0);
});

test("Cloudflare DNS resolver bounds every Answer record, including ignored record types", async () => {
  let calls = 0;
  const ignored = Array.from({ length: 33 }, (_, index) => ({
    type: [5, 2, 16][index % 3],
    data: `alias-${index}.example.com`,
  }));
  const resolver = new CloudflareDnsResolver(async () => {
    calls += 1;
    return new Response(JSON.stringify({ Answer: ignored }));
  });
  await assert.rejects(
    () => resolver.resolve("models.example.com"),
    (error) => error instanceof EndpointValidationError && error.code === "endpoint_dns_failed" && !error.message.includes("alias-"),
  );
  assert.equal(calls, 1);
});

test("Cloudflare DNS resolver bounds cumulative response bytes even below Answer count limit", async () => {
  const ignored = [
    { type: 5, data: "x".repeat(40 * 1024) },
    { type: 16, data: "y".repeat(40 * 1024) },
  ];
  const resolver = new CloudflareDnsResolver(async () => new Response(JSON.stringify({ Answer: ignored })));
  await assert.rejects(
    () => resolver.resolve("models.example.com"),
    (error) => error instanceof EndpointValidationError && error.code === "endpoint_dns_failed" && !error.message.includes("xxx"),
  );
});

test("Cloudflare DNS resolver accepts a finite CNAME plus A/AAAA response", async () => {
  const resolver = new CloudflareDnsResolver(async (request) => {
    const type = new URL(request.url).searchParams.get("type");
    const Answer = type === "A"
      ? [{ type: 5, data: "alias.example.com" }, { type: 1, data: "1.1.1.1" }]
      : [{ type: 2, data: "ns.example.com" }, { type: 28, data: "2606:4700:4700::1111" }];
    return new Response(JSON.stringify({ Answer }));
  });
  assert.deepEqual(await resolver.resolve("models.example.com"), ["1.1.1.1", "2606:4700:4700::1111"]);
});
