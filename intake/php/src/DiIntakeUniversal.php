<?php
/**
 * Universal Intake and Interpretation Layer, WHP-INTAKE-1.3.0 (PHP port of standing_intake/intake.py).
 *
 * Additive and deterministic. Never calls the examination engine and never changes it.
 * Not wired to anything by this file: the caller decides, behind a default-OFF flag.
 * No model, no network, no state, no I/O. Standard library only (json/mbstring/pcre/hash).
 */

final class DiIuBad extends Exception {}
final class DiIuDup extends Exception {}

/** Ordered JSON object (keys may be numeric strings, so PHP arrays are not used). */
final class DiIuObj {
    public array $order = [];
    public array $map = [];
    public function has(string $k): bool { return array_key_exists('k' . $k, $this->map); }
    public function get(string $k) { return $this->map['k' . $k] ?? null; }
    public function set(string $k, $v): void {
        if (!$this->has($k)) { $this->order[] = $k; }
        $this->map['k' . $k] = $v;
    }
    public function keys(): array { return $this->order; }
    public static function of(array $a): DiIuObj { $o = new DiIuObj(); foreach ($a as $k => $v) { $o->set((string)$k, $v); } return $o; }
}
final class DiIuInt { public function __construct(public string $digits) {} }
final class DiIuFloat { public function __construct(public float $f) {} }

final class DiIuJson {
    private string $s; private int $i = 0; private int $n;
    public static function parse(string $s) {
        $p = new self(); $p->s = $s; $p->n = strlen($s);
        $p->ws(); $v = $p->value(0); $p->ws();
        if ($p->i !== $p->n) { throw new DiIuBad('extra data'); }
        return $v;
    }
    private function ws(): void { while ($this->i < $this->n && strpos(" \t\n\r", $this->s[$this->i]) !== false) { $this->i++; } }
    private function value(int $d) {
        if ($d > 900) { throw new DiIuBad('recursion'); }
        if ($this->i >= $this->n) { throw new DiIuBad('eof'); }
        $c = $this->s[$this->i];
        if ($c === '{') { return $this->object($d); }
        if ($c === '[') { return $this->arr($d); }
        if ($c === '"') { return $this->str(); }
        if (substr($this->s, $this->i, 4) === 'true') { $this->i += 4; return true; }
        if (substr($this->s, $this->i, 5) === 'false') { $this->i += 5; return false; }
        if (substr($this->s, $this->i, 4) === 'null') { $this->i += 4; return null; }
        return $this->num();
    }
    private function num() {
        if (!preg_match('/\G-?(?:0|[1-9][0-9]*)(\.[0-9]+)?([eE][+-]?[0-9]+)?/', $this->s, $m, 0, $this->i)) { throw new DiIuBad('number'); }
        $this->i += strlen($m[0]);
        if ((isset($m[1]) && $m[1] !== '') || (isset($m[2]) && $m[2] !== '')) { return new DiIuFloat((float)$m[0]); }
        $t = $m[0]; if ($t === '-0') { $t = '0'; }
        return new DiIuInt($t);
    }
    private function str(): string {
        $this->i++; $out = '';
        while (true) {
            if ($this->i >= $this->n) { throw new DiIuBad('unterminated'); }
            $c = $this->s[$this->i];
            if ($c === '"') { $this->i++; return $out; }
            if (ord($c) < 0x20) { throw new DiIuBad('control'); }
            if ($c !== '\\') { $out .= $c; $this->i++; continue; }
            $this->i++;
            if ($this->i >= $this->n) { throw new DiIuBad('escape'); }
            $e = $this->s[$this->i++];
            $map = ['"' => '"', '\\' => '\\', '/' => '/', 'b' => "\x08", 'f' => "\x0c", 'n' => "\n", 'r' => "\r", 't' => "\t"];
            if (isset($map[$e])) { $out .= $map[$e]; continue; }
            if ($e !== 'u') { throw new DiIuBad('escape'); }
            $cp = $this->hex4();
            if ($cp >= 0xD800 && $cp <= 0xDBFF) {
                if (substr($this->s, $this->i, 2) === '\\u') {
                    $this->i += 2; $lo = $this->hex4();
                    if ($lo < 0xDC00 || $lo > 0xDFFF) { throw new DiIuBad('surrogate'); }
                    $cp = 0x10000 + (($cp - 0xD800) << 10) + ($lo - 0xDC00);
                } else { throw new DiIuBad('surrogate'); }
            } elseif ($cp >= 0xDC00 && $cp <= 0xDFFF) { throw new DiIuBad('surrogate'); }
            $out .= mb_chr($cp, 'UTF-8');
        }
    }
    private function hex4(): int {
        $h = substr($this->s, $this->i, 4);
        if (strlen($h) !== 4 || !ctype_xdigit($h)) { throw new DiIuBad('hex'); }
        $this->i += 4; return hexdec($h);
    }
    private function arr(int $d): array {
        $this->i++; $out = []; $this->ws();
        if ($this->i < $this->n && $this->s[$this->i] === ']') { $this->i++; return $out; }
        while (true) {
            $this->ws(); $out[] = $this->value($d + 1); $this->ws();
            if ($this->i >= $this->n) { throw new DiIuBad('eof'); }
            $c = $this->s[$this->i++];
            if ($c === ']') { return $out; }
            if ($c !== ',') { throw new DiIuBad('array'); }
        }
    }
    private function object(int $d): DiIuObj {
        $this->i++; $pairs = []; $this->ws();
        if ($this->i < $this->n && $this->s[$this->i] === '}') { $this->i++; return new DiIuObj(); }
        while (true) {
            $this->ws();
            if ($this->i >= $this->n || $this->s[$this->i] !== '"') { throw new DiIuBad('key'); }
            $k = $this->str(); $this->ws();
            if ($this->i >= $this->n || $this->s[$this->i] !== ':') { throw new DiIuBad('colon'); }
            $this->i++; $this->ws();
            $pairs[] = [$k, $this->value($d + 1)]; $this->ws();
            if ($this->i >= $this->n) { throw new DiIuBad('eof'); }
            $c = $this->s[$this->i++];
            if ($c === '}') { break; }
            if ($c !== ',') { throw new DiIuBad('object'); }
        }
        $o = new DiIuObj();
        foreach ($pairs as [$k, $v]) { if ($o->has($k)) { throw new DiIuDup($k); } $o->set($k, $v); }
        return $o;
    }
}

final class DiIuRec {
    public array $source; public array $extracted = []; public array $interpreted = []; public array $inferred = []; public array $issues = [];
    public array $contradictions = []; public array $alternatives = []; public array $ignored = [];
    public DiIuObj $trace; public ?string $claim = null; public ?string $data = null; public ?string $src = null; public ?string $warrant = null;
    public $op = null; public array $evidence = []; public array $multi = []; public array $parts = [];
    public $passthrough = null; public ?string $fbKey = null;
    public function __construct(string $rawSha, int $bytes, string $media) {
        $this->trace = new DiIuObj();
        $this->source = ['original_sha256' => $rawSha, 'bytes' => $bytes, 'media_type' => $media, 'caller_fields' => new DiIuObj()];
    }
    public function ext(string $kind, string $text, string $pointer, string $rule): string {
        $i = 'x' . (count($this->extracted) + 1);
        $this->extracted[] = ['id' => $i, 'kind' => $kind, 'text' => $text, 'pointer' => $pointer, 'rule' => $rule]; return $i;
    }
    public function interp(string $what, string $ref, string $rule): void { $this->interpreted[] = ['what' => $what, 'from' => $ref, 'rule' => $rule]; }
    public function infer(string $what, string $value, string $why): void { $this->inferred[] = ['what' => $what, 'value' => $value, 'why' => $why, 'is_evidence' => false]; }
    public function issue(string $code, string $detail): void { $this->issues[] = ['code' => $code, 'detail' => $detail]; }
}

final class DiIntakeUniversal {
    public const VERSION = 'WHP-INTAKE-1.3.0';
    public const MAX_BYTES = 262144;
    public const MAX_DEPTH = 64;
    // WHP-INTAKE-1.2.0 (2026-11-20, operator-approved): the gate keeps no fixed operation list.
    // Any operation name is taken as given; the gate may refuse a missing object or a non-string
    // operation, never an operation outside a predetermined container.
    // WHP-INTAKE-1.3.0 (2026-11-20, operator-approved): distinct conflicting values across the
    // proposition alias fields are refused, never silently sorted into roles. The door refuses
    // before payment with 400 AMBIGUOUS_INPUT_ALIASES; the intake records NOT_EXAMINABLE.
    private const CLAIM_KEYS = ['claim', 'proposition', 'statement', 'question', 'assertion'];
    // The published input schema's proposition aliases (WHP-INPUT-SCHEMA-1.4.x): distinct values
    // across these fields are a caller error. question/assertion are not refusal aliases; a
    // distinct value there is preserved as an alternative, matching the live door's alias set.
    private const PROPOSITION_ALIAS_KEYS = ['claim', 'text', 'prompt', 'content', 'statement', 'proposition'];
    private const MATERIAL_KEYS = ['data', 'material', 'text', 'document', 'content', 'body', 'evidence', 'record', 'payload', 'transaction', 'event', 'prompt', 'input'];
    private const STANDING = ['established_fact', 'established', 'source_grade', 'epistemic_status', 'attested', 'attestation', 'signature',
        'verified', 'authorized', 'approved', 'standing', 'outcome', 'determination', 'permitted_operations', 'trusted'];
    private const LABELS = ['claim' => 'claim', 'proposition' => 'claim', 'question' => 'claim', 'evidence' => 'material', 'material' => 'material',
        'data' => 'material', 'source' => 'source', 'warrant' => 'warrant', 'operation' => 'op', 'requested operation' => 'op'];
    private const SRC_OPT = 'SOURCE_REFERENCE(optional: examination will name an unresolved source)';

    /** Process one submission. $raw is the exact bytes received. Returns the Intake Record (see toJson). */
    public static function intake(string $raw, ?string $mediaType = null): array {
        $sha = hash('sha256', $raw);
        $media = $mediaType ?? self::guessMedia($raw);
        $r = new DiIuRec($sha, strlen($raw), $media);
        $obj = null; $text = null;
        if (strlen($raw) > self::MAX_BYTES) { $r->issue('TOO_LARGE', strlen($raw) . ' bytes, limit ' . self::MAX_BYTES); }
        elseif (trim($raw, " \t\n\r\x0b\x0c") === '') { $r->issue('EMPTY_SUBMISSION', 'no content'); }
        else {
            if (mb_check_encoding($raw, 'UTF-8')) { $text = $raw; } else { $r->issue('NOT_UTF8', 'submission is not valid UTF-8; original preserved'); }
            if ($text !== null) {
                if ($media === 'application/json') {
                    try {
                        $obj = DiIuJson::parse($text);
                        if (self::depth($obj, 1) > self::MAX_DEPTH) { $r->issue('TOO_DEEP', 'nesting over ' . self::MAX_DEPTH); $obj = null; }
                    } catch (DiIuDup $e) { $r->issue('DUPLICATE_KEY', $e->getMessage()); }
                    catch (DiIuBad $e) { $r->issue('MALFORMED_JSON', 'not parseable as JSON'); }
                }
                if ($obj !== null) { self::fromJson($r, $obj); }
                elseif (count($r->issues) === 0) { self::fromText($r, $text); }
            }
        }
        $statements = array_map(fn($p) => $p[1], $r->parts);
        foreach ($r->parts as [$p, $t]) { $r->ext('material', $t, $p, 'R-MATERIAL'); }
        if (count($statements) > 0) { $r->data = implode("\n", $statements); }
        if (count($r->evidence) > 0 && ($r->data === null || $r->data === '')) { $r->data = implode("\n", $r->evidence); }

        $op = $r->op;
        if ($op === null) { $op = 'INFORM'; $r->infer('requested_operation', 'INFORM', 'caller named none; INFORM is the least consequential default'); }
        elseif (!is_string($op)) {
            $r->issue('UNSUPPORTED_OPERATION', 'requested operation ' . self::pyRepr($op) . ' is not a string; operation names are taken as given'); $op = null;
        }
        $missing = [];
        $hasClaim = $r->claim !== null && $r->claim !== '';
        if (!$hasClaim && count($r->multi) < 2) { $missing[] = 'PROPOSITION'; }
        if ($r->data === null || $r->data === '') { $missing[] = 'MATERIAL'; }
        if ($r->src === null) { $missing[] = self::SRC_OPT; }
        $hard = count($r->issues) > 0;
        $blocking = array_values(array_filter($missing, fn($m) => strpos($m, 'SOURCE') !== 0));
        if ($hard || (count($blocking) > 0 && !$hasClaim && count($r->multi) === 0)) { $level = 'NOT_EXAMINABLE'; }
        elseif (in_array('MATERIAL', $blocking, true)) { $level = 'EXAMINABLE_WITH_LIMITS'; }
        else { $level = 'EXAMINABLE'; }
        if (in_array('PROPOSITION', $blocking, true) && !$hard) { $level = 'NOT_EXAMINABLE'; }
        $notes = [];
        if ($level === 'EXAMINABLE_WITH_LIMITS') { $notes[] = 'Proposition without separate material: the engine examines the proposition text alone (fallback). Not a substantive examination of supporting material.'; }
        if (count($r->contradictions) > 0) { $notes[] = 'Submitted material contradicts itself on: ' . implode(', ', array_map(fn($c) => $c['key'], $r->contradictions)) . '. Both values are preserved; neither is selected.'; }
        if (count($r->ignored) > 0) { $notes[] = 'Caller assertions of standing were recorded and ignored: ' . implode(', ', array_map(fn($c) => $c['field'], $r->ignored)) . '.'; }
        if (in_array(self::SRC_OPT, $missing, true)) { $notes[] = 'No source reference was supplied; none was manufactured. Expect the examination to name the source as unresolved.'; }

        $canon = [];
        if ($level !== 'NOT_EXAMINABLE' && $op !== null) {
            $claims = $hasClaim ? [$r->claim] : array_map(fn($m) => $m[0], $r->multi);
            foreach ($claims as $c) {
                $b = new DiIuObj(); $b->set('claim', $c); $b->set('requested_operation', $op);
                if ($r->data !== null && $r->data !== '') { $b->set('data', $r->data); }
                if ($r->src !== null) {
                    $b->set('source', $r->src);
                    $pv = new DiIuObj(); $pv->set('source', $r->src);
                    if (count($r->evidence) > 0) { $pv->set('evidence', $r->evidence); }
                    $b->set('provenance', $pv);
                } elseif (count($r->evidence) > 0) { $pv = new DiIuObj(); $pv->set('evidence', $r->evidence); $b->set('provenance', $pv); }
                if ($r->warrant !== null && $r->warrant !== '') { $b->set('warrant', $r->warrant); }
                $canon[] = $b;
            }
        } elseif ($level !== 'NOT_EXAMINABLE') { $level = 'NOT_EXAMINABLE'; }
        if ($r->passthrough !== null) {
            $missing = []; $level = 'EXAMINABLE'; $canon = [$r->passthrough];
            $notes[] = 'Engine-native submission passed through unchanged; intake did not inspect its nodes. The examination decides what is established.';
        }
        $cj = array_map(fn($c) => self::dumps($c, true, true, false), $canon);
        $gate = ['NOT_EXAMINABLE' => 'NO_QUOTE', 'EXAMINABLE_WITH_LIMITS' => 'QUOTE_ONLY_WITH_DISCLOSURE_AND_INFORMED_CHOICE', 'EXAMINABLE' => 'QUOTE_ALLOWED'];
        $record = [
            'intake_version' => self::VERSION,
            'source' => $r->source, 'extracted' => $r->extracted, 'interpreted' => $r->interpreted, 'inferred' => $r->inferred,
            'canonical_trace' => $r->trace,
            'preserved' => ['contradictions' => $r->contradictions, 'alternatives' => $r->alternatives, 'ignored_caller_assertions' => $r->ignored],
            'examinability' => ['level' => $level, 'missing' => $missing, 'issues' => $r->issues, 'disclosures' => $notes, 'quote_gate' => $gate[$level]],
            'canonical_submissions' => $canon,
            'canonical_sha256' => array_map(fn($c) => hash('sha256', $c), $cj),
            'does_not_establish' => ['correctness of the proposition', 'truth of any submitted material', 'authenticity of any source', 'authority of any party', 'any standing: that is the engine\'s examination'],
        ];
        $record['record_sha256'] = hash('sha256', self::dumps($record, true, true, false));
        return $record;
    }

    /** Canonical record text: sorted keys, compact, non-ASCII kept. Identical to the Python reference. */
    public static function toJson(array $record): string { return self::dumps($record, true, true, false); }

    private static function guessMedia(string $raw): string {
        $s = substr(ltrim($raw, " \t\n\r\x0b\x0c"), 0, 1);
        return ($s === '{' || $s === '[') ? 'application/json' : 'text/plain';
    }
    private static function pytrim(string $s): string {
        return (string)preg_replace('/^[\s\x{1c}-\x{1f}\x{85}\x{a0}\x{1680}\x{2000}-\x{200a}\x{2028}\x{2029}\x{202f}\x{205f}\x{3000}]+|[\s\x{1c}-\x{1f}\x{85}\x{a0}\x{1680}\x{2000}-\x{200a}\x{2028}\x{2029}\x{202f}\x{205f}\x{3000}]+$/u', '', $s);
    }
    private static function isStr($v): bool { return is_string($v) && self::pytrim($v) !== ''; }
    private static function isDigits(string $s): bool { return $s !== '' && preg_match('/^\p{Nd}+$/u', $s) === 1; }
    private static function depth($o, int $n): int {
        if ($n > self::MAX_DEPTH) { return $n; }
        $m = $n;
        if ($o instanceof DiIuObj) { foreach ($o->keys() as $k) { $m = max($m, self::depth($o->get($k), $n + 1)); } }
        elseif (is_array($o)) { foreach ($o as $v) { $m = max($m, self::depth($v, $n + 1)); } }
        return $m;
    }
    private static function scalarText($o): string {
        if (is_string($o)) { return $o; }
        return self::dumps($o, false, false, true);
    }
    /** Verbatim scalar leaves as [pointer, text]. */
    private static function flatten($o, string $ptr): array {
        $out = [];
        if ($o instanceof DiIuObj) {
            foreach ($o->keys() as $k) { $out = array_merge($out, self::flatten($o->get($k), $ptr . '/' . str_replace('/', '~1', str_replace('~', '~0', $k)))); }
        } elseif (is_array($o)) {
            foreach ($o as $i => $v) { $out = array_merge($out, self::flatten($v, $ptr . '/' . $i)); }
        } elseif ($o !== null) { $out[] = [$ptr, self::scalarText($o)]; }
        return $out;
    }
    private static function lab(string $ptr, string $t): string {
        $segs = explode('/', $ptr); $last = end($segs);
        return (self::isDigits($last) || in_array($last, ['text', 'data', 'content'], true) || substr_count($ptr, '/') === 1) ? $t : $last . ': ' . $t;
    }
    private static function typeName($v): string {
        if ($v instanceof DiIuObj) { return 'dict'; } if (is_array($v)) { return 'list'; } if (is_bool($v)) { return 'bool'; }
        if ($v instanceof DiIuInt) { return 'int'; } if ($v instanceof DiIuFloat) { return 'float'; } return 'str';
    }

    private static function fromJson(DiIuRec $r, $obj): void {
        if (is_array($obj)) {
            $r->interp('submission is an evidence package (list)', '', 'R-PKG-LIST');
            $w = new DiIuObj(); $w->set('items', $obj); $obj = $w;
        }
        if (is_string($obj)) {
            if (trim($obj) === '') { $r->issue('EMPTY_SUBMISSION', 'top-level JSON string is empty'); return; }
            $r->claim = $obj;
            $i = $r->ext('proposition', $obj, '/', 'R-JSON-TOP-STRING'); $r->trace->set('claim', $i);
            $r->interp('proposition is the top-level JSON string (the documented bare-string shape)', '/', 'R-JSON-TOP-STRING');
            return;
        }
        if (!($obj instanceof DiIuObj)) { $r->issue('UNSUPPORTED_SHAPE', 'top-level JSON is a scalar'); return; }
        if ($obj->get('version') === 'WHP-STANDING-SUBMISSION-v1' && is_array($obj->get('nodes')) && count($obj->get('nodes')) > 0) {
            $r->passthrough = $obj;
            $r->interp('submission is already an engine-native WHP-STANDING-SUBMISSION-v1 object; passed through unchanged', '', 'R-SUBMISSION-V1-PASSTHROUGH');
            return;
        }
        foreach ($obj->keys() as $k) {
            if (in_array(mb_strtolower($k, 'UTF-8'), self::STANDING, true)) {
                $r->source['caller_fields']->set($k, $obj->get($k));
                $r->ignored[] = ['field' => $k, 'reason' => 'caller assertion of standing; recorded, never evidence'];
            }
        }
        // proposition alias conflict: refused, never sorted into roles (R-JSON-ALIAS-CONFLICT-REFUSED)
        $aliasVals = [];
        foreach (self::PROPOSITION_ALIAS_KEYS as $k) {
            if (!$obj->has($k)) { continue; }
            $v = $obj->get($k);
            if (self::isStr($v)) { $aliasVals[] = [$k, trim($v)]; }
        }
        $distinctVals = [];
        foreach ($aliasVals as [$ak, $av]) { $distinctVals[$av] = true; }
        if (count($distinctVals) > 1) {
            $r->issue('AMBIGUOUS_INPUT_ALIASES', 'distinct conflicting values across proposition alias fields (' . implode(', ', array_map(fn($p) => '/' . $p[0], $aliasVals)) . '); supply one proposition field or make every alias carry the same value');
            $r->interp('conflicting proposition aliases refused; no value is assigned a role', '', 'R-JSON-ALIAS-CONFLICT-REFUSED');
            return;
        }
        foreach (self::CLAIM_KEYS as $k) {
            if (!$obj->has($k)) { continue; }
            $v = $obj->get($k);
            if (self::isStr($v)) {
                if ($r->claim === null) {
                    $r->claim = $v; $i = $r->ext('proposition', $v, '/' . $k, 'R-JSON-CLAIM-STRING'); $r->trace->set('claim', $i);
                    $r->interp("proposition is the caller's $k string", '/' . $k, 'R-JSON-CLAIM-STRING');
                } elseif ($v !== $r->claim) { $r->alternatives[] = ['kind' => 'proposition', 'pointer' => '/' . $k, 'text' => $v]; }
            } elseif ($v instanceof DiIuObj && self::isStr($v->get('statement'))) {
                if ($r->claim === null) {
                    $r->claim = $v->get('statement'); $i = $r->ext('proposition', $r->claim, "/$k/statement", 'R-JSON-CLAIM-NESTED'); $r->trace->set('claim', $i);
                    $r->interp('proposition is claim.statement (previously documented nested shape)', "/$k/statement", 'R-JSON-CLAIM-NESTED');
                }
                foreach ($v->keys() as $x) { if ($x !== 'statement' && $x !== 'type') { $r->ext('claim_attribute', self::dumps($v->get($x), false, false, true), "/$k/$x", 'R-NOT-CLAIM-TEXT'); } }
            } elseif (is_array($v)) {
                $n = 0;
                foreach ($v as $x) { if (self::isStr($x)) { $r->multi[] = [$x, "/$k/$n"]; $n++; } }
            } elseif ($v !== null && !is_string($v)) {
                $r->issue('PROPOSITION_NOT_TEXT', "/$k is " . self::typeName($v) . ', not text');
            }
        }
        if (count($r->multi) > 1) {
            foreach ($r->multi as [$x, $p]) { $r->ext('proposition', $x, $p, 'R-JSON-CLAIM-LIST'); }
            $r->interp(count($r->multi) . ' separate propositions supplied by the caller; each is examined separately', '', 'R-MULTI-PROPOSITION');
        } elseif (count($r->multi) === 1 && $r->claim === null) {
            $r->claim = $r->multi[0][0]; $r->trace->set('claim', $r->ext('proposition', $r->claim, $r->multi[0][1], 'R-JSON-CLAIM-LIST'));
        }
        if ($r->claim === null && count($r->multi) === 0 && count($r->issues) === 0) {
            // Contract precedence (WHP-INPUT-SCHEMA-1.3.0): claim aliases (claim, text, prompt,
            // content, statement, proposition) beat subject; subject beats object.id. The
            // text/prompt/content aliases are handled by the fallback loop below, so subject
            // and object.id are read only when none of those alias strings is present.
            $hasAlias = false;
            foreach (['text', 'prompt', 'content'] as $k) { if (self::isStr($obj->get($k))) { $hasAlias = true; break; } }
            if (!$hasAlias) {
                $subj = $obj->get('subject');
                $ob = $obj->get('object');
                if (self::isStr($subj)) {
                    $r->claim = $subj; $r->trace->set('claim', $r->ext('proposition', $subj, '/subject', 'R-JSON-SUBJECT'));
                    $r->interp('no claim alias string; the subject string is mapped to the proposition', '/subject', 'R-JSON-SUBJECT');
                } elseif ($ob instanceof DiIuObj && self::isStr($ob->get('id'))) {
                    $r->claim = $ob->get('id'); $r->trace->set('claim', $r->ext('proposition', $r->claim, '/object/id', 'R-JSON-OBJECT-ID'));
                    $r->interp('no claim alias or subject string; object.id is the proposition', '/object/id', 'R-JSON-OBJECT-ID');
                }
            }
        }
        if ($r->claim === null && count($r->multi) === 0 && count($r->issues) === 0) {
            foreach (['data', 'text', 'prompt', 'content', 'input'] as $k) {
                if (self::isStr($obj->get($k))) {
                    $r->claim = $obj->get($k); $r->fbKey = $k;
                    $r->trace->set('claim', $r->ext('proposition', $r->claim, '/' . $k, 'R-JSON-PROPOSITION-FALLBACK'));
                    $r->interp("no claim field; the string in $k is read as the proposition (the examination engine's documented fallback order: data, text, prompt, content, input)", '/' . $k, 'R-JSON-PROPOSITION-FALLBACK');
                    break;
                }
            }
        }
        $parts = [];
        foreach (self::MATERIAL_KEYS as $k) {
            if ($obj->has($k) && $k !== $r->fbKey) {
                $v = $obj->get($k);
                if (self::isStr($v)) { $parts[] = ['/' . $k, $v]; }
                elseif ($v instanceof DiIuObj || is_array($v)) { foreach (self::flatten($v, '/' . $k) as [$ptr, $t]) { $parts[] = [$ptr, self::lab($ptr, $t)]; } }
            }
        }
        if ($obj->has('items')) { foreach (self::flatten($obj->get('items'), '/items') as [$ptr, $t]) { $parts[] = [$ptr, self::lab($ptr, $t)]; } }
        if ($obj->has('files') && is_array($obj->get('files'))) {
            foreach ($obj->get('files') as $n => $f) { if ($f instanceof DiIuObj && self::isStr($f->get('text'))) { $parts[] = ["/files/$n/text", $f->get('text')]; } }
        }
        foreach (['source', 'source_url', 'url'] as $k) {
            if (self::isStr($obj->get($k)) && $r->src === null) { $r->src = $obj->get($k); $r->trace->set('source', $r->ext('source', $r->src, '/' . $k, 'R-JSON-SOURCE')); }
        }
        $prov = $obj->get('provenance');
        if ($prov instanceof DiIuObj) {
            if (self::isStr($prov->get('source')) && $r->src === null) { $r->src = $prov->get('source'); $r->trace->set('source', $r->ext('source', $r->src, '/provenance/source', 'R-JSON-SOURCE')); }
            if (is_array($prov->get('evidence'))) { $r->evidence = array_values(array_filter($prov->get('evidence'), fn($e) => self::isStr($e))); }
            if (self::isStr($prov->get('authority')) && !self::isStr($obj->get('warrant'))) { $r->warrant = $prov->get('authority'); }
        }
        $mat = $obj->get('material');
        if ($mat instanceof DiIuObj && self::isStr($mat->get('source_url')) && $r->src === null) {
            $r->src = $mat->get('source_url'); $r->trace->set('source', $r->ext('source', $r->src, '/material/source_url', 'R-JSON-SOURCE'));
        }
        if (self::isStr($obj->get('warrant'))) { $r->warrant = $obj->get('warrant'); }
        if ($r->warrant !== null && $r->warrant !== '') { $r->trace->set('warrant', $r->ext('warrant', $r->warrant, '/warrant', 'R-JSON-WARRANT')); }
        foreach (['requested_operation', 'operation'] as $k) { if ($obj->has($k)) { $r->op = $obj->get($k); } }
        // contradictions
        $d = $obj->has('items') ? $obj->get('items') : ($obj->has('material') ? $obj->get('material') : ($obj->has('data') ? $obj->get('data') : new DiIuObj()));
        $seen = [];
        if (!is_string($obj->get('data'))) {
            foreach (self::flatten($d, '') as [$ptr, $t]) {
                $segs = explode('/', $ptr); $key = end($segs);
                if (!self::isDigits($key)) { $seen['k' . $key][] = [$ptr, $t, $key]; }
            }
        }
        foreach ($seen as $vals) {
            if (count(array_unique(array_map(fn($x) => $x[1], $vals))) > 1) {
                $r->contradictions[] = ['key' => $vals[0][2], 'values' => array_map(fn($x) => ['pointer' => $x[0], 'text' => $x[1]], $vals)];
            }
        }
        $r->parts = array_values(array_filter($parts, fn($pt) => !(substr($pt[0], -11) === '/source_url' && $r->src !== null && strpos($pt[1], $r->src) !== false)));
    }

    private static function fromText(DiIuRec $r, string $text): void {
        $lines = explode("\n", $text); $cur = null;
        $b = ['claim' => [], 'material' => [], 'source' => [], 'warrant' => [], 'op' => []]; $labeled = false; $unl = [];
        foreach ($lines as $n => $ln) {
            if (preg_match('/^\s*(claim|proposition|question|evidence|material|data|source|warrant|requested operation|operation)\s*:\s*(.*)$/iu', $ln, $m)) {
                $labeled = true; $cur = self::LABELS[mb_strtolower($m[1], 'UTF-8')];
                if (self::pytrim($m[2]) !== '') { $b[$cur][] = [$n, self::pytrim($m[2])]; }
            } elseif (self::pytrim($ln) !== '') {
                if ($cur !== null) { $b[$cur][] = [$n, self::pytrim($ln)]; } else { $unl[] = [$n, self::pytrim($ln)]; }
            }
        }
        if ($labeled) {
            $r->interp('labeled sections (Claim/Evidence/Source/...) read by label', '', 'R-TEXT-LABELS');
            $cl = $b['claim'];
            if (count($cl) > 0) {
                $r->claim = implode(' ', array_map(fn($x) => $x[1], $cl));
                $r->trace->set('claim', $r->ext('proposition', $r->claim, 'lines ' . ($cl[0][0] + 1) . '-' . (end($cl)[0] + 1), 'R-TEXT-LABEL-CLAIM'));
            }
            $r->parts = [];
            foreach (array_merge($b['material'], $unl) as [$n, $t]) { $r->parts[] = ['line ' . ($n + 1), $t]; }
            if (count($b['source']) > 0) { $r->src = $b['source'][0][1]; $r->trace->set('source', $r->ext('source', $r->src, 'line ' . ($b['source'][0][0] + 1), 'R-TEXT-LABEL-SOURCE')); }
            if (count($b['warrant']) > 0) { $r->warrant = implode(' ', array_map(fn($x) => $x[1], $b['warrant'])); $r->trace->set('warrant', $r->ext('warrant', $r->warrant, 'labeled', 'R-TEXT-LABEL-WARRANT')); }
            if (count($b['op']) > 0) { $r->op = mb_strtoupper($b['op'][0][1], 'UTF-8'); }
        } else {
            $stmts = array_map(fn($x) => $x[1], $unl); $r->parts = [];
            if (count($stmts) === 1 && mb_strlen($stmts[0], 'UTF-8') < 600) {
                $r->claim = $stmts[0]; $r->trace->set('claim', $r->ext('proposition', $r->claim, 'line 1', 'R-TEXT-SINGLE-STATEMENT'));
                $r->interp('a lone statement is read as the proposition; no material accompanies it', 'line 1', 'R-TEXT-SINGLE-STATEMENT');
            } elseif (count($stmts) > 0) {
                $r->interp('unlabeled multi-line text is read as material; no proposition is identified', '', 'R-TEXT-DOCUMENT');
                foreach ($unl as [$n, $t]) { $r->parts[] = ['line ' . ($n + 1), $t]; }
                foreach (array_slice($unl, 0, 5) as [$n, $t]) {
                    if (substr($t, -1) === '?') { $r->alternatives[] = ['kind' => 'candidate_proposition_inferred', 'pointer' => 'line ' . ($n + 1), 'text' => $t, 'selected' => false]; }
                }
            }
        }
    }

    // ---- Python-compatible serialisation ----
    private static function pyFloat(float $f): string {
        if ($f == 0.0) { return (strpos(sprintf('%.1f', $f), '-') === 0 || fdiv(1.0, $f) < 0) ? '-0.0' : '0.0'; }
        if (is_infinite($f)) { return $f > 0 ? 'Infinity' : '-Infinity'; }
        $sign = $f < 0 ? '-' : ''; $a = abs($f); $p = 0;
        for ($p = 0; $p <= 16; $p++) { if ((float)sprintf('%.' . $p . 'e', $a) === $a) { break; } }
        [$mant, $ex] = explode('e', sprintf('%.' . $p . 'e', $a)); $ex = (int)$ex;
        $digits = str_replace('.', '', $mant); $digits = rtrim($digits, '0'); if ($digits === '') { $digits = '0'; }
        if ($ex < -4 || $ex >= 16) {
            $m = $digits[0] . (strlen($digits) > 1 ? '.' . substr($digits, 1) : '');
            return $sign . $m . 'e' . ($ex < 0 ? '-' : '+') . str_pad((string)abs($ex), 2, '0', STR_PAD_LEFT);
        }
        if ($ex >= 0) {
            $ip = str_pad(substr($digits, 0, $ex + 1), $ex + 1, '0'); $fp = strlen($digits) > $ex + 1 ? substr($digits, $ex + 1) : '0';
            return $sign . $ip . '.' . $fp;
        }
        return $sign . '0.' . str_repeat('0', -$ex - 1) . $digits;
    }
    private static function jstr(string $s, bool $ascii): string {
        $fl = JSON_UNESCAPED_SLASHES | ($ascii ? 0 : (JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_LINE_TERMINATORS));
        return json_encode($s, $fl);
    }
    public static function dumps($v, bool $sort, bool $compact, bool $ascii): string {
        if ($v === null) { return 'null'; }
        if ($v === true) { return 'true'; } if ($v === false) { return 'false'; }
        if ($v instanceof DiIuInt) { return $v->digits; }
        if ($v instanceof DiIuFloat) { return self::pyFloat($v->f); }
        if (is_int($v)) { return (string)$v; }
        if (is_string($v)) { return self::jstr($v, $ascii); }
        $isep = $compact ? ',' : ', '; $ksep = $compact ? ':' : ': ';
        if ($v instanceof DiIuObj) { $keys = $v->keys(); $get = fn($k) => $v->get($k); }
        elseif (is_array($v) && !array_is_list($v)) { $keys = array_map('strval', array_keys($v)); $get = fn($k) => $v[$k]; }
        else { return '[' . implode($isep, array_map(fn($x) => self::dumps($x, $sort, $compact, $ascii), $v)) . ']'; }
        if ($sort) { usort($keys, 'strcmp'); }
        $parts = [];
        foreach ($keys as $k) { $parts[] = self::jstr((string)$k, $ascii) . $ksep . self::dumps($get($k), $sort, $compact, $ascii); }
        return '{' . implode($isep, $parts) . '}';
    }
    private static function pyRepr($v): string {
        if ($v === null) { return 'None'; } if ($v === true) { return 'True'; } if ($v === false) { return 'False'; }
        if ($v instanceof DiIuInt) { return $v->digits; } if ($v instanceof DiIuFloat) { return self::pyFloat($v->f); }
        if (is_string($v)) {
            $q = (strpos($v, "'") !== false && strpos($v, '"') === false) ? '"' : "'"; $o = $q;
            foreach (preg_split('//u', $v, -1, PREG_SPLIT_NO_EMPTY) as $ch) {
                $c = mb_ord($ch, 'UTF-8');
                if ($ch === $q || $ch === '\\') { $o .= '\\' . $ch; }
                elseif ($ch === "\n") { $o .= '\\n'; } elseif ($ch === "\r") { $o .= '\\r'; } elseif ($ch === "\t") { $o .= '\\t'; }
                elseif ($c < 0x20 || $c === 0x7f || ($c >= 0x80 && $c < 0xa0)) { $o .= sprintf('\\x%02x', $c); }
                else { $o .= $ch; }
            }
            return $o . $q;
        }
        if ($v instanceof DiIuObj) { $p = []; foreach ($v->keys() as $k) { $p[] = self::pyRepr($k) . ': ' . self::pyRepr($v->get($k)); } return '{' . implode(', ', $p) . '}'; }
        return '[' . implode(', ', array_map(fn($x) => self::pyRepr($x), $v)) . ']';
    }
}
