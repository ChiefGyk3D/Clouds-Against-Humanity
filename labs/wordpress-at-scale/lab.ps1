# SPDX-License-Identifier: Apache-2.0
# PowerShell twin of lab.sh (Windows PowerShell 5.1 or PowerShell 7; needs curl.exe, which ships with
# current Windows, and Docker Desktop or Podman with Compose). Written from the Bash script and NOT
# run on Windows by the author (est.). Usage: .\lab.ps1 up | status | cache | bypass | stampede | waf |
# uploads | drill | redis-drill | origin | down
param([Parameter(Position = 0)][string]$Cmd = "help")
$ErrorActionPreference = "Stop"
$Lab = $PSScriptRoot
$Edge = "http://127.0.0.1:8080"
$Naive = "http://127.0.0.1:8081"
$script:Fails = 0

function Compose { docker compose --project-directory $Lab -f "$Lab/compose.yaml" --env-file "$Lab/.env" @args }
function Header([string]$Url, [string[]]$Extra = @()) { (curl.exe -s -D - -o NUL @Extra $Url) -replace "`r", "" }
function HVal($Lines, [string]$Name) { ($Lines | Where-Object { $_ -match "^${Name}:" } | Select-Object -First 1) -replace "^[^:]*:\s*", "" }
function Check([string]$What, [bool]$Ok) { if ($Ok) { "PASS  $What" } else { "FAIL  $What"; $script:Fails++ } }
function Rand { Get-Random -Maximum 1000000 }
function DbQueries { (curl.exe -s "$Edge/stats?x=$(Rand)" | ConvertFrom-Json).db_queries }
function Burst([string]$Base, [string]$Key) {
    1..20 | ForEach-Object { Start-Job { param($u) curl.exe -s $u -o NUL } -ArgumentList "$Base/slow?k=$Key" } | Wait-Job | Remove-Job
}
function CountNodes {
    $n = 1..12 | ForEach-Object { HVal (Header "$Edge/?n=$(Rand)$_") "X-Node" }
    ($n | Group-Object | ForEach-Object { "$($_.Count) $($_.Name)" }) -join "  "
}

switch ($Cmd) {
    "up" {
        # ORIGIN_SECRET is required. The shell environment wins over .env (as in compose). A value that is
        # empty or a placeholder stops the lab; only a missing or empty one gets a random value. This pattern
        # is the one rule of scripts/secret_rule.py (PLACEHOLDER_RE2); tests pin it. The value is never printed.
        $pattern = '(?i)(^(your[_-]|changeme|change-me|replace[_-]with|xxx|dp[.]st[.]your|(todo|tbd|admin|password|secret|test)$)|^<.*>$|example|placeholder|changeme)'
        $v = $env:ORIGIN_SECRET
        $file = "$Lab/.env"
        if (-not $v -and (Test-Path $file)) {
            $m = Select-String -Path $file -Pattern '^ORIGIN_SECRET=(.*)$' | Select-Object -Last 1
            if ($m) { $v = $m.Matches[0].Groups[1].Value }
        }
        if ($v) {
            if ($v.Trim() -eq "" -or $v -match $pattern) {
                throw "refusing to start: ORIGIN_SECRET is empty or a placeholder (clear it in .env to get a random one)"
            }
        } else {
            $bytes = New-Object byte[] 16
            [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
            $new = (($bytes | ForEach-Object { $_.ToString("x2") }) -join "")
            if ((Test-Path $file) -and (Select-String -Path $file -Pattern '^ORIGIN_SECRET=' -Quiet)) {
                (Get-Content $file) -replace '^ORIGIN_SECRET=.*$', "ORIGIN_SECRET=$new" | Set-Content $file -Encoding ascii
            } else {
                Add-Content -Path $file -Value "ORIGIN_SECRET=$new" -Encoding ascii
            }
        }
        Compose up -d
        1..30 | ForEach-Object { if (curl.exe -sf "$Edge/" -o NUL) { return }; Start-Sleep 1 }
        curl.exe -s "$Edge/"
    }
    "status" { Compose ps; curl.exe -s "$Edge/stats?x=$(Rand)" }
    "cache" {
        curl.exe -s -X POST "$Edge/reset-stats" -o NUL
        $u = "$Edge/?page=$(Rand)"
        "--- first request"; Header $u | Select-String -Pattern "^(HTTP|x-cache-status|x-node|x-obj-cache)" 
        "--- second request"; Header $u | Select-String -Pattern "^(HTTP|x-cache-status|x-node|age)"
    }
    "bypass" {
        $u = "$Edge/?bypass=$(Rand)"
        curl.exe -s $u -o NUL
        $a = HVal (Header $u) "X-Cache-Status"
        Check "anonymous visitor: second request is a HIT (got $a)" ($a -eq "HIT")
        $b = HVal (Header $u @("-H", "Cookie: wordpress_logged_in_demo=1")) "X-Cache-Status"
        Check "logged-in cookie: cache is BYPASSed (got $b)" ($b -eq "BYPASS")
        Check "logged-in visitor sees the private page" ((curl.exe -s $u -H "Cookie: wordpress_logged_in_demo=1") -match "Welcome back")
        Check "the next anonymous visitor does NOT see it" (-not ((curl.exe -s $u) -match "Welcome back"))
        $v = "$Naive/?leak=$(Rand)"
        curl.exe -s $v -H "Cookie: wordpress_logged_in_demo=1" -o NUL
        if ((curl.exe -s $v) -match "Welcome back") { "LEAK  careless edge served the logged-in page to an anonymous visitor" }
        if ($script:Fails) { "$($script:Fails) check(s) failed"; exit 1 } else { "all checks passed" }
    }
    "stampede" {
        curl.exe -s -X POST "$Edge/reset-stats" -o NUL
        $k = Rand; Burst $Edge "good$k"
        "careful edge (cache lock on): 20 simultaneous cold requests -> $(DbQueries) origin queries"
        curl.exe -s -X POST "$Edge/reset-stats" -o NUL
        Burst $Naive "naive$k"
        "careless edge (no lock):      20 simultaneous cold requests -> $(DbQueries) origin queries"
    }
    "waf" {
        foreach ($p in "/?q=1", "/?q=1%20union%20select%201", "/?q=%3Cscript%3E", "/?q=uni%6fn%20select%201") {
            "{0,-34} -> {1}" -f $p, (curl.exe -s -o NUL -w "%{http_code}" "$Edge$p")
        }
        "--- 8 quick logins from one address (limit: 1 per second, burst 3)"
        (1..8 | ForEach-Object { curl.exe -s -o NUL -w "%{http_code}" -X POST "$Edge/wp-login.php" }) -join " "
    }
    "uploads" {
        function Reads($path) { (1..6 | ForEach-Object { curl.exe -s -o NUL -w "%{http_code}" "$Edge/$path?x=$(Rand)$_" }) -join " " }
        "--- one upload written to ONE node's own disk, then read 6 times:"
        curl.exe -s -X POST --data "hello" "$Edge/upload-local?name=a.txt"
        "status codes: " + (Reads "local-files/a.txt")
        "--- one upload written to the shared volume, then read 6 times:"
        curl.exe -s -X POST --data "hello" "$Edge/upload-shared?name=b.txt"
        "status codes: " + (Reads "shared-files/b.txt")
    }
    "drill" {
        "both nodes up:   $(CountNodes)"
        Compose kill web1 | Out-Null
        $errs = 0
        1..12 | ForEach-Object { if ((curl.exe -s -o NUL -w "%{http_code}" "$Edge/?n=$(Rand)$_") -ne "200") { $errs++ } }
        "web1 killed:     $(CountNodes)   errors out of 12 requests: $errs"
        Compose start web1 | Out-Null; Start-Sleep 8
        "web1 restarted:  $(CountNodes)"
    }
    "redis-drill" {
        Compose stop redis | Out-Null
        "object cache stopped: " + ((Header "$Edge/?n=$(Rand)" | Select-String -Pattern "^(HTTP|x-obj-cache)") -join " ")
        Compose start redis | Out-Null; Start-Sleep 2
        "object cache back:    " + ((Header "$Edge/?n=$(Rand)" | Select-String -Pattern "^(HTTP|x-obj-cache)") -join " ")
    }
    "origin" {
        "--- from inside the web tier, call the balancer WITHOUT the edge's secret header:"
        Compose exec -T web1 python -I -c 'import urllib.request,urllib.error
try: print(urllib.request.urlopen("http://lb/").status)
except urllib.error.HTTPError as e: print(e.code, e.read().decode().strip())'
        "--- published ports:"
        Compose ps --format "{{.Service}} {{.Ports}}"
    }
    "down" { Compose down -v; Remove-Item "$Lab/.env" -ErrorAction SilentlyContinue }
    default { Get-Content $PSCommandPath -TotalCount 6 | Select-Object -Skip 1; exit 2 }
}
