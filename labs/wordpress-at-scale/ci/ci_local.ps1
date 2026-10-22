# SPDX-License-Identifier: Apache-2.0
# PowerShell twin of ci_local.sh. Written from the Bash script, NOT run on Windows by the author (est.).
# Needs Python 3 on PATH as `python` or `python3`, and tar.exe (ships with current Windows).
# Usage: .\ci_local.ps1 all | negative | rollback | status | clean
param([Parameter(Position = 0)][string]$Cmd = "help")
$ErrorActionPreference = "Stop"
$Here = $PSScriptRoot
$Lab = Split-Path $Here -Parent
$State = Join-Path $Lab ".state"
$Py = if (Get-Command python3 -ErrorAction SilentlyContinue) { "python3" } else { "python" }

function Check { & $Py -I (Join-Path $Here "ci_policy_check.py") @args | Out-Host; return ($LASTEXITCODE -eq 0) }
function Pointer($env_) { $p = Join-Path $State "$env_/current"; if (Test-Path $p) { (Get-Content $p).Trim() } else { "(none)" } }
function Build {
    "`n== build one artifact"
    New-Item -ItemType Directory -Force (Join-Path $State "artifacts") | Out-Null
    tar -czf (Join-Path $State "artifacts/release.tar.gz") -C $Lab site
    $hash = (Get-FileHash (Join-Path $State "artifacts/release.tar.gz") -Algorithm SHA256).Hash.ToLower()
    $hash | Set-Content (Join-Path $State "artifacts/release.sha256") -Encoding ascii
    $script:Release = $hash.Substring(0, 12)
    "release id: $Release"
}
function Deploy($env_) {
    "`n== deploy to $env_"
    $want = (Get-Content (Join-Path $State "artifacts/release.sha256")).Trim()
    $have = (Get-FileHash (Join-Path $State "artifacts/release.tar.gz") -Algorithm SHA256).Hash.ToLower()
    if ($want -ne $have) { throw "checksum mismatch" }
    $dir = Join-Path $State "$env_/releases/$Release"
    New-Item -ItemType Directory -Force $dir | Out-Null
    tar -xzf (Join-Path $State "artifacts/release.tar.gz") -C $dir
    $cur = Join-Path $State "$env_/current"
    if (Test-Path $cur) { Copy-Item $cur (Join-Path $State "$env_/previous") -Force }
    $Release | Set-Content $cur -Encoding ascii
    "$env_ now points at $(Pointer $env_)"
}
function Smoke($env_) {
    "`n== smoke test on $env_ (structural check, plus a live request if the lab stack is up)"
    $id = Pointer $env_
    if (-not (Test-Path (Join-Path $State "$env_/releases/$id/site/composer.json"))) { throw "SMOKE FAIL: release $id has no composer.json" }
    if (-not (Check --site (Join-Path $State "$env_/releases/$id/site"))) { throw "SMOKE FAIL: site rules failed" }
    try { $r = curl.exe -s -o NUL -w "%{http_code}" "http://127.0.0.1:8080/?smoke=$(Get-Random)" } catch { $r = "" }
    if ($r -eq "200") { "live request through the edge: 200" } else { "lab stack not running: skipped the live request" }
}

switch ($Cmd) {
    "all" {
        "== policy"; if (-not (Check --workflow (Join-Path $Here "example-wordpress-ci.yml") --site (Join-Path $Lab "site"))) { exit 1 }
        Build; Deploy "staging"; Smoke "staging"
        "`n(a person approves here in a real pipeline)"
        Deploy "production"; Smoke "production"
    }
    "negative" {
        $tmp = Join-Path ([IO.Path]::GetTempPath()) ("wpscale-" + [guid]::NewGuid())
        New-Item -ItemType Directory $tmp | Out-Null
        Copy-Item (Join-Path $Lab "site") (Join-Path $tmp "site") -Recurse
        $c = Join-Path $tmp "site/composer.json"
        (Get-Content $c -Raw) -replace '"2.3.1"', '"^2.3"' | Set-Content $c -Encoding ascii
        $a = Join-Path $tmp "site/config/application.php"
        (Get-Content $a -Raw) -replace "'DISALLOW_FILE_MODS', true", "'DISALLOW_FILE_MODS', false" | Set-Content $a -Encoding ascii
        @("name: bad", "on:", "  pull_request_target:", "jobs:", "  a:", "    uses: some-owner/some-repo/.github/workflows/x.yml@main", "    secrets: inherit") |
            Set-Content (Join-Path $tmp "bad.yml") -Encoding ascii
        if (Check --workflow (Join-Path $tmp "bad.yml") --site (Join-Path $tmp "site")) { "UNEXPECTED: bad input passed"; exit 1 }
        "(a non-zero exit is the point: the bad copy was refused)"
        Remove-Item -Recurse -Force $tmp
    }
    "rollback" {
        $prev = Join-Path $State "production/previous"
        if (-not (Test-Path $prev)) { "nothing to roll back to"; exit 1 }
        Copy-Item $prev (Join-Path $State "production/current") -Force
        "production now points at $(Pointer 'production')"
    }
    "status" { "staging: $(Pointer 'staging')   production: $(Pointer 'production')" }
    "clean" { Remove-Item -Recurse -Force $State -ErrorAction SilentlyContinue }
    default { "Usage: .\ci_local.ps1 all | negative | rollback | status | clean"; exit 2 }
}
