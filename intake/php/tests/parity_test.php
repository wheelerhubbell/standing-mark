<?php
// Run: php tests/parity_test.php   (exit 0 = all cases byte-identical to the Python reference)
require __DIR__ . '/../src/DiIntakeUniversal.php';
$fx = json_decode(file_get_contents(__DIR__ . '/parity_fixtures.json'), true);
$fail = 0; $n = 0;
foreach ($fx['cases'] as $c) {
    $n++;
    $raw = base64_decode($c['raw_b64'], true);
    $got = DiIntakeUniversal::toJson(DiIntakeUniversal::intake($raw, $c['media_type']));
    if ($got === $c['expected']) { echo "ok   {$c['name']}\n"; continue; }
    $fail++; echo "FAIL {$c['name']}\n";
    $l = min(strlen($got), strlen($c['expected'])); $i = 0;
    while ($i < $l && $got[$i] === $c['expected'][$i]) { $i++; }
    echo "  first diff at byte $i\n  php: " . substr($got, max(0, $i - 60), 160) . "\n  py : " . substr($c['expected'], max(0, $i - 60), 160) . "\n";
}
// flag-off contract: the module has no side effects on load and never reads config
echo ($fail === 0 ? "PARITY PASS" : "PARITY FAIL") . " $n cases, $fail failed\n";
exit($fail === 0 ? 0 : 1);
