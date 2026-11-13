// Independent implementation: Node.js built-ins only, no code shared with the Python kit.
// Runs the same vectors: node conformance/run.js
const fs = require("fs"), crypto = require("crypto"), path = require("path");
const V = JSON.parse(fs.readFileSync(path.join(__dirname, "vectors.json"), "utf8"));
const u16 = s => Buffer.from(s, "utf16le").swap16();
function jstr(s) { let o = '"'; for (const ch of s) { const c = ch.codePointAt(0);
  if (ch === '"') o += '\\"'; else if (ch === "\\") o += "\\\\"; else if (ch === "\b") o += "\\b"; else if (ch === "\t") o += "\\t";
  else if (ch === "\n") o += "\\n"; else if (ch === "\f") o += "\\f"; else if (ch === "\r") o += "\\r";
  else if (c < 0x20) o += "\\u" + c.toString(16).padStart(4, "0"); else o += ch; } return o + '"'; }
function jcs(v) { if (v === null) return "null"; if (v === true) return "true"; if (v === false) return "false";
  if (typeof v === "number") { if (!Number.isSafeInteger(v)) throw new Error("unsafe"); return String(v); }
  if (typeof v === "string") return jstr(v); if (Array.isArray(v)) return "[" + v.map(jcs).join(",") + "]";
  const k = Object.keys(v).sort((a, b) => Buffer.compare(u16(a), u16(b)));
  return "{" + k.map(x => jstr(x) + ":" + jcs(v[x])).join(",") + "}"; }
const sha = b => crypto.createHash("sha256").update(b).digest("hex");
const oid = o => "sha256:" + sha(Buffer.from(jcs(o), "utf8"));
function verify(env, pinned, type = "WHP-STANDING-MARK-v1") {
  let der; try { der = Buffer.from(pinned, "base64"); } catch { return { valid: false, reason: "PINNED_KEY_UNREADABLE" }; }
  const kid = sha(der);
  if (!env || typeof env.protected !== "object" || env.payload === undefined || env.signature === undefined) return { valid: false, reason: "ENVELOPE_INCOMPLETE" };
  const p = env.protected;
  if (p.algorithm !== "Ed25519") return { valid: false, reason: "ALGORITHM_MISMATCH" };
  if (p.canonicalization !== "WHP-JCS-I1") return { valid: false, reason: "CANONICALIZATION_MISMATCH" };
  if (type && p.type !== type) return { valid: false, reason: "TYPE_MISMATCH" };
  if (p.key_id !== kid) return { valid: false, reason: "KEY_NOT_PINNED" };
  const key = crypto.createPublicKey({ key: der, format: "der", type: "spki" });
  const ok = crypto.verify(null, Buffer.from(jcs({ protected: p, payload: env.payload }), "utf8"), key, Buffer.from(env.signature, "base64"));
  return { valid: ok, reason: ok ? "OK" : "SIGNATURE_INVALID" };
}
function request(i) {
  for (const [n, k] of [["claim", "CLAIM"], ["data", "DATA"]]) {
    if (i[n] === undefined || i[n] === null) return { ok: false, code: "MISSING_" + k };
    if (typeof i[n] !== "string") return { ok: false, code: "NOT_A_STRING" };
    if (!i[n].trim()) return { ok: false, code: "EMPTY_" + k };
  }
  const body = { claim: i.claim, data: i.data, requested_operation: "INFORM" };
  return { ok: true, body_jcs: jcs(body), material_bytes: Buffer.byteLength(i.data, "utf8") };
}
function evidence(env, pinned, now) {
  const v = verify(env, pinned), p = env.payload, problems = v.valid ? [] : ["SIGNATURE:" + v.reason];
  const em = p.object_binding.examined_material, q = p.object_binding.examined_question;
  const subst = Number.isInteger(em.bytes) && em.bytes > 0 && em.fallback === false && !!q ? "SUBSTANTIVE" : "NOT_SUBSTANTIVE";
  const fresh = now < p.expires_at ? "CURRENT" : "EXPIRED"; if (fresh === "EXPIRED") problems.push("EXPIRED");
  if (subst !== "SUBSTANTIVE") problems.push("EXAMINATION_NOT_SUBSTANTIVE");
  return { mark_verified: v.valid, outcome: p.standing.outcome, substantive: subst, freshness: fresh, problems };
}
const FORB = new Set(["accepted", "acceptance", "authorized", "authorization", "approved", "agreed", "allow", "deny", "decision"]);
const keys = o => Array.isArray(o) ? o.flatMap(keys) : (o && typeof o === "object") ? Object.entries(o).flatMap(([k, v]) => [k, ...keys(v)]) : [];
function receipt(env, pinned, mark) {
  const s = verify(env, pinned, "WHP-STANDING-RECEIPT-v1"), pr = s.valid ? [] : ["SIGNATURE:" + s.reason], p = env.payload;
  const DNE = ["RECEIVER_UNDERSTANDING", "RECEIVER_AGREEMENT", "RECEIVER_ACCEPTANCE", "AUTHORIZATION_OF_ANY_ACTION", "SUBSTANTIVE_CORRECTNESS_OF_THE_EXAMINATION"];
  const EST = ["AUTHENTICATED_RECEPTION_EVENT", "CORRESPONDENCE_OF_RECEIVED_TO_ISSUED_OBJECT"];
  if (p.type !== "WHP-STANDING-RECEIPT-v1") pr.push("PAYLOAD_TYPE");
  if (!DNE.every(x => (p.does_not_establish || []).includes(x))) pr.push("MISSING_LIMITS");
  if (!(p.establishes || []).length || !(p.establishes || []).every(x => EST.includes(x))) pr.push("OVERCLAIMS");
  const { acknowledgment, ...scan } = p; if (keys(scan).some(k => FORB.has(k))) pr.push("CLAIMS_ACCEPTANCE_OR_AUTHORIZATION");
  const h = sha(Buffer.from(jcs(mark), "utf8"));
  if ((p.mark_ref || {}).envelope_sha256 !== h) pr.push("MARK_REF_MISMATCH");
  if ((p.correspondence || {}).received_object_sha256 !== h) pr.push("CORRESPONDENCE_MISMATCH");
  return { valid: pr.length === 0, problems: pr };
}
const AFTER = { request: [], mark: ["request"], reception_event: ["mark"], receipt: ["reception_event"], receiver_response: ["receipt", "reception_event", "mark"] };
function chain(recs) { const pr = [], seen = {};
  recs.forEach((r, i) => { if (oid(r.object) !== r.object_id) pr.push(i + ":OBJECT_ALTERED");
    for (const p of r.prior_ids) { if (!(p in seen)) pr.push(i + ":PRIOR_MISSING"); else if (!AFTER[r.kind].includes(seen[p])) pr.push(i + ":ILLEGAL_LINK " + seen[p] + "->" + r.kind); }
    if (r.kind !== "request" && !r.prior_ids.length) pr.push(i + ":UNLINKED"); seen[r.object_id] = r.kind; }); return pr; }
function bind(mark, reqText) {
  const v = JSON.parse(reqText); const d = typeof v === "string" ? sha(Buffer.from(v, "utf8")) : sha(Buffer.from(jcs(v), "utf8"));
  return d === mark.payload.object_binding.submitted_bytes_sha256 ? "CORRESPONDS" : "DOES_NOT_CORRESPOND"; }
let fail = 0, n = 0;
const eq = (name, g, w) => { n++; if (jcs(g) !== jcs(w)) { fail++; console.log("FAIL", name, JSON.stringify(g), JSON.stringify(w)); } };
V.jcs.forEach((c, i) => eq("jcs" + i, jcs(c.input), c.expected));
V.object_id.forEach((c, i) => eq("oid" + i, oid(c.input), c.expected));
V.signature.forEach(c => eq("sig:" + c.id, verify(c.envelope, c.pinned, c.expected_type ?? "WHP-STANDING-MARK-v1"), c.expected));
V.request.forEach(c => eq("req:" + c.id, request(c.input), c.expected));
V.evidence.forEach(c => eq("ev:" + c.id, evidence(c.envelope, c.pinned, c.now), c.expected));
V.receipt.forEach(c => eq("rcpt:" + c.id, receipt(c.receipt, c.pinned, c.mark), c.expected));
V.binding.forEach(c => eq("bind:" + c.id, bind(c.mark, c.request), c.expected));
V.chain.forEach(c => eq("chain:" + c.id, chain(c.records), c.expected));
console.log("node independent verifier: " + n + " conformance cases, " + fail + " failed"); process.exit(fail ? 1 : 0);
