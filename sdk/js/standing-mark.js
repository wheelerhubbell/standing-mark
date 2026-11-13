// Standing Mark client SDK (Node.js 18+, standard library only).
// Free surface: contract, issuer key pinning, examination quotes, remote and
// offline signature checks. The paid retry is the caller's decision: this
// SDK never pays. Live contract is the source of truth.

const crypto = require("node:crypto");

const DEFAULT_BASE = "https://decisionintegrity.wheelerhubbellpublishing.com";

class QuoteRequired extends Error {
  constructor(quote, raw) {
    super(`payment required: ${quote.amount_units} units to ${quote.pay_to}, quote ${quote.quote_id}`);
    this.quote = quote; this.raw = raw;
  }
}

function jcsString(s) {
  let out = '"';
  for (const ch of s) {
    const o = ch.codePointAt(0);
    if (ch === '"') out += '\\"';
    else if (ch === "\\") out += "\\\\";
    else if (ch === "\b") out += "\\b";
    else if (ch === "\t") out += "\\t";
    else if (ch === "\n") out += "\\n";
    else if (ch === "\f") out += "\\f";
    else if (ch === "\r") out += "\\r";
    else if (o < 0x20) out += "\\u" + o.toString(16).padStart(4, "0");
    else out += ch;
  }
  return out + '"';
}

function jcs(v) {
  if (v === null) return "null";
  if (v === true) return "true";
  if (v === false) return "false";
  if (typeof v === "number") {
    if (!Number.isSafeInteger(v)) throw new Error("non-integer or unsafe integer: rejected by WHP-JCS-I1");
    return String(v);
  }
  if (typeof v === "string") return jcsString(v);
  if (Array.isArray(v)) return "[" + v.map(jcs).join(",") + "]";
  if (typeof v === "object") {
    const keys = Object.keys(v).sort(); // UTF-16 code unit order
    return "{" + keys.map((k) => jcsString(k) + ":" + jcs(v[k])).join(",") + "}";
  }
  throw new TypeError(typeof v);
}

async function req(method, base, path, body, headers) {
  const resp = await fetch(base + path, {
    method,
    headers: { "Content-Type": "application/json", ...(headers || {}) },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  return [resp.status, await resp.json()];
}

class StandingMark {
  constructor(base = DEFAULT_BASE) { this.base = base.replace(/\/$/, ""); }

  async contract() { return (await req("GET", this.base, "/v1/contract"))[1]; }

  async issuer() { return (await req("GET", this.base, "/.well-known/whp-issuer.json"))[1]; }

  async pinnedKey() {
    const iss = await this.issuer();
    const der = Buffer.from(iss.public_key, "base64");
    const kid = crypto.createHash("sha256").update(der).digest("hex");
    if (kid !== iss.key_id_sha256) throw new Error("published key does not pin to published key id");
    return { der, kid };
  }

  async requestExamination(claim, { quoteId, paymentTx } = {}) {
    const headers = (quoteId && paymentTx) ? { "X-WHP-Quote": quoteId, "X-WHP-Payment-Tx": paymentTx } : {};
    const [status, body] = await req("POST", this.base, "/v1/evaluate", claim, headers);
    if (status === 402) throw new QuoteRequired(body.payment_required || {}, body);
    if (status !== 200) throw new Error(`examination failed: HTTP ${status} ${JSON.stringify(body)}`);
    return body;
  }

  async verifyRemote(signedResult, publicKeyB64) {
    const pk = publicKeyB64 || (await this.issuer()).public_key;
    return (await req("POST", this.base, "/v1/verification", { envelope: signedResult, public_key: pk }))[1];
  }

  async verifyLocal(signedResult) {
    const { der, kid } = await this.pinnedKey();
    const p = signedResult.protected || {};
    if (p.key_id !== kid || p.algorithm !== "Ed25519" || p.canonicalization !== "WHP-JCS-I1")
      throw new Error("protected header does not match the pinned key and method");
    const bytes = Buffer.from(jcs({ protected: signedResult.protected, payload: signedResult.payload }), "utf8");
    const key = crypto.createPublicKey({ key: der, format: "der", type: "spki" });
    return crypto.verify(null, bytes, key, Buffer.from(signedResult.signature, "base64"));
  }
}

module.exports = { StandingMark, QuoteRequired, jcs, DEFAULT_BASE };
