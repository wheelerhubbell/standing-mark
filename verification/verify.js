#!/usr/bin/env node
// Independent offline verification of a signed Standing Mark result.
// Node.js 18+ standard library only (node:crypto). No dependencies.
//
// Establishes: the pinned issuer key signed this exact object.
// Does not establish: object binding to your question, current standing,
// policy acceptance, or that the key is authoritative for a given object.
//
// Usage: node verify.js signed-result.json

const crypto = require("node:crypto");
const fs = require("node:fs");

const ISSUER_URL = "https://decisionintegrity.wheelerhubbellpublishing.com/.well-known/whp-issuer.json";

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
    else out += ch; // ECMAScript escaping preserves non-ASCII and U+2028/U+2029 literally
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
    // Default JS string comparison orders by UTF-16 code units, as WHP-JCS-I1 requires.
    const keys = Object.keys(v).sort();
    return "{" + keys.map((k) => jcsString(k) + ":" + jcs(v[k])).join(",") + "}";
  }
  throw new TypeError(typeof v);
}

async function main() {
  const env = JSON.parse(fs.readFileSync(process.argv[2] || "signed_result.json", "utf8"));
  let pkDer;
  if (process.argv[3]) {
    pkDer = Buffer.from(process.argv[3], "base64");
    console.log("expected key pinned from argument:", crypto.createHash("sha256").update(pkDer).digest("hex"));
  } else {
    const issuer = await (await fetch(ISSUER_URL)).json();
    pkDer = Buffer.from(issuer.public_key, "base64");
    const kid0 = crypto.createHash("sha256").update(pkDer).digest("hex");
    if (kid0 !== issuer.key_id_sha256) throw new Error("published key does not pin to published key id");
    console.log("issuer key pinned:", kid0);
  }
  const kid = crypto.createHash("sha256").update(pkDer).digest("hex");

  const prot = env.protected;
  if (prot.algorithm !== "Ed25519") throw new Error("unexpected algorithm");
  if (prot.canonicalization !== "WHP-JCS-I1") throw new Error("unexpected canonicalization");
  if (prot.key_id !== kid) throw new Error("envelope names a different key than the pinned issuer key");
  console.log("protected header names the pinned key, Ed25519, WHP-JCS-I1");

  const signingBytes = Buffer.from(jcs({ protected: env.protected, payload: env.payload }), "utf8");
  const key = crypto.createPublicKey({ key: pkDer, format: "der", type: "spki" });
  const ok = crypto.verify(null, signingBytes, key, Buffer.from(env.signature, "base64"));
  if (!ok) { console.error("Ed25519 signature: INVALID"); process.exit(1); }
  console.log("Ed25519 signature: VALID over", signingBytes.length, "canonical bytes");
  console.log("\nEstablished: the pinned issuer key signed this exact object.");
  console.log("Not established: object binding to your own question, current standing, policy acceptance.");
}

main().catch((e) => { console.error("verification failed:", e.message); process.exit(1); });
