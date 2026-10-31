#Requires -Version 7.0
<#
.SYNOPSIS
    AdsPower Local API 调用脚本。

.DESCRIPTION
    改写自 AdsPower/adspower-browser 的 CLI（MIT License，见 ../LICENSE.txt）。
    命令名与参数和原 CLI 一致，直接请求本机 AdsPower 客户端的 Local API，无需 Node.js / npm。

    参数形式:
      1) JSON:  adspower-api.ps1 open-browser '{"profile_id":"abcd1234","ip_tab":"0"}'
      2) 简写:  adspower-api.ps1 open-browser abcd1234      纯数字视为 profile_no
                支持简写的命令: open-browser, close-browser, get-profile-cookies,
                get-browser-active, get-profile-ua, new-fingerprint
      3) 文件:  adspower-api.ps1 create-browser -ParamsFile C:\path\params.json   (UTF-8)

    API Key 读取顺序: -ApiKey > 进程环境变量 ADS_API_KEY > 用户级 / 系统级环境变量 ADS_API_KEY
    端口读取顺序:     -Port > 环境变量 ADS_API_PORT > 50325

    输出: stdout 为接口返回的完整 JSON；提示、进度写入 stderr。
    退出码: 0 成功；1 接口返回 code != 0 或 HTTP 错误；2 用法错误或无法连接 Local API。

.EXAMPLE
    & .\adspower-api.ps1 check-status
.EXAMPLE
    & .\adspower-api.ps1 get-browser-list '{"group_id":"0"}'
.EXAMPLE
    & .\adspower-api.ps1 delete-browser '{"profile_id":["abc"]}' -DryRun
.EXAMPLE
    & .\adspower-api.ps1 download-kernel '{"kernel_type":"Chrome","kernel_version":"141"}' -Poll
#>
[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [string]$Command,

    [Parameter(Position = 1)]
    [string]$Params,

    [string]$ParamsFile,

    [int]$Port = 0,

    [string]$ApiKey,

    # 仅 download-kernel: 每 3 秒轮询直到 completed / failed
    [switch]$Poll,

    [int]$PollTimeoutSec = 240,

    # 只打印将要发送的请求，不调用接口
    [switch]$DryRun,

    [switch]$ListCommands
)

$ErrorActionPreference = 'Stop'

# 命令 -> HTTP 方法与路径（来源: packages/core/src/constants/localApiContracts.ts）
$Contracts = [ordered]@{
    'check-status'              = @('GET',  '/status')
    'get-application-list'      = @('GET',  '/api/v2/category/list')
    'open-browser'              = @('POST', '/api/v2/browser-profile/start')
    'close-browser'             = @('POST', '/api/v2/browser-profile/stop')
    'create-browser'            = @('POST', '/api/v2/browser-profile/create')
    'update-browser'            = @('POST', '/api/v2/browser-profile/update')
    'delete-browser'            = @('POST', '/api/v2/browser-profile/delete')
    'get-recycle-bin-list'      = @('POST', '/api/v2/browser-profile/recycle-bin/list')
    'restore-recycle-bin'       = @('POST', '/api/v2/browser-profile/recycle-bin/restore')
    'get-browser-list'          = @('POST', '/api/v2/browser-profile/list')
    'get-opened-browser'        = @('GET',  '/api/v1/browser/local-active')
    'move-browser'              = @('POST', '/api/v1/user/regroup')
    'get-profile-cookies'       = @('GET',  '/api/v2/browser-profile/cookies')
    'get-profile-ua'            = @('POST', '/api/v2/browser-profile/ua')
    'close-all-profiles'        = @('POST', '/api/v2/browser-profile/stop-all')
    'new-fingerprint'           = @('POST', '/api/v2/browser-profile/new-fingerprint')
    'delete-cache-v2'           = @('POST', '/api/v2/browser-profile/delete-cache')
    'share-profile'             = @('POST', '/api/v2/browser-profile/share')
    'get-browser-active'        = @('GET',  '/api/v2/browser-profile/active')
    'get-cloud-active'          = @('POST', '/api/v1/browser/cloud-active')
    'create-group'              = @('POST', '/api/v1/group/create')
    'update-group'              = @('POST', '/api/v1/group/update')
    'get-group-list'            = @('GET',  '/api/v1/group/list')
    'create-member'             = @('POST', '/api/v2/user/create')
    'update-member'             = @('POST', '/api/v2/user/update')
    'reset-member-password'     = @('POST', '/api/v2/user/reset_password')
    'delete-member'             = @('POST', '/api/v2/user/delete')
    'get-member-list'           = @('GET',  '/api/v2/user/list')
    'get-member-group-list'     = @('GET',  '/api/v2/user-group/list')
    'create-proxy'              = @('POST', '/api/v2/proxy-list/create')
    'update-proxy'              = @('POST', '/api/v2/proxy-list/update')
    'get-dynamic-proxy-traffic' = @('POST', '/api/v2/proxy/dynamic-proxy-traffic')
    'get-proxy-list'            = @('POST', '/api/v2/proxy-list/list')
    'delete-proxy'              = @('POST', '/api/v2/proxy-list/delete')
    'get-tag-list'              = @('POST', '/api/v2/browser-tags/list')
    'create-tag'                = @('POST', '/api/v2/browser-tags/create')
    'update-tag'                = @('POST', '/api/v2/browser-tags/update')
    'delete-tag'                = @('POST', '/api/v2/browser-tags/delete')
    'download-kernel'           = @('POST', '/api/v2/browser-profile/download-kernel')
    'get-kernel-list'           = @('GET',  '/api/v2/browser-profile/kernels')
    'update-patch'              = @('POST', '/api/v2/browser-profile/update-patch')
}

# 与原 CLI 一致的简写规则（packages/adspower-browser/src/cli.ts）
$SingleIdCommands      = @('open-browser', 'close-browser', 'get-profile-cookies', 'get-browser-active')
$SingleIdArrayCommands = @('get-profile-ua', 'new-fingerprint')

function Write-Err([string]$Message) {
    [Console]::Error.WriteLine($Message)
}

function ConvertFrom-JsonText([string]$Text) {
    $splat = @{ AsHashtable = $true; NoEnumerate = $true }
    if ((Get-Command ConvertFrom-Json).Parameters.ContainsKey('DateKind')) {
        # 防止 "2026-10-01" 之类的字符串被自动转成 DateTime
        $splat['DateKind'] = 'String'
    }
    return , ($Text | ConvertFrom-Json @splat)
}

function Get-Setting([string]$Name) {
    $value = [Environment]::GetEnvironmentVariable($Name, 'Process')
    if ([string]::IsNullOrWhiteSpace($value) -and $IsWindows) {
        $value = [Environment]::GetEnvironmentVariable($Name, 'User')
    }
    if ([string]::IsNullOrWhiteSpace($value) -and $IsWindows) {
        $value = [Environment]::GetEnvironmentVariable($Name, 'Machine')
    }
    return $value
}

# 与原 CLI 的 getUaSystemVersionFromOs 一致（packages/core/src/utils/systemVer.ts）
function Get-UaSystemVersion {
    if ($IsWindows) {
        $v = [Environment]::OSVersion.Version
        if ($v.Major -eq 6 -and $v.Minor -eq 1) { return 'Windows 7' }
        if ($v.Major -eq 6 -and $v.Minor -in 2, 3) { return 'Windows 8' }
        if ($v.Major -eq 10 -and $v.Minor -eq 0) {
            if ($v.Build -ge 22000) { return 'Windows 11' }
            return 'Windows 10'
        }
        return 'Windows'
    }
    if ($IsLinux) { return 'Linux' }
    if ($IsMacOS) {
        $darwinMajor = 0
        [void][int]::TryParse(((& uname -r) -split '\.')[0], [ref]$darwinMajor)
        if ($darwinMajor -lt 20) { return 'Mac OS X 10' }
        $map = @{ 20 = 'Mac OS X 11'; 21 = 'Mac OS X 12'; 22 = 'Mac OS X 13'; 23 = 'Mac OS X 14'; 24 = 'Mac OS X 15'; 25 = 'Mac OS X 26' }
        if ($map.ContainsKey($darwinMajor)) { return $map[$darwinMajor] }
        return 'Mac OS X'
    }
    return $null
}

# ---------- 命令校验 ----------
if ($ListCommands -or [string]::IsNullOrWhiteSpace($Command)) {
    foreach ($name in $Contracts.Keys) {
        '{0,-26} {1,-4} {2}' -f $name, $Contracts[$name][0], $Contracts[$name][1]
    }
    if ($ListCommands) { exit 0 }
    Write-Err "用法: adspower-api.ps1 <command> [<profile_id|profile_no|JSON>] [-ParamsFile path] [-Port n] [-ApiKey key] [-DryRun] [-Poll]"
    exit 2
}

if (-not $Contracts.Contains($Command)) {
    Write-Err "未知命令: $Command。可用 -ListCommands 查看全部命令。"
    exit 2
}

# ---------- 参数解析 ----------
$raw = $null
if ($ParamsFile) {
    if (-not (Test-Path -LiteralPath $ParamsFile -PathType Leaf)) {
        Write-Err "参数文件不存在: $ParamsFile"
        exit 2
    }
    try {
        $raw = [IO.File]::ReadAllText((Resolve-Path -LiteralPath $ParamsFile).ProviderPath, [Text.UTF8Encoding]::new($false, $true))
    } catch {
        Write-Err "参数文件不是有效的 UTF-8 文本: $($_.Exception.Message)"
        exit 2
    }
} elseif ($PSBoundParameters.ContainsKey('Params')) {
    $raw = $Params
}

$trimmed = if ($null -eq $raw) { '' } else { $raw.Trim() }

if ($trimmed -eq '') {
    $p = [ordered]@{}
} elseif ($trimmed.StartsWith('{') -or $trimmed.StartsWith('[')) {
    try {
        $p = ConvertFrom-JsonText $trimmed
    } catch {
        Write-Err "参数不是合法 JSON: $($_.Exception.Message)"
        exit 2
    }
} elseif ($Command -in $SingleIdCommands) {
    $field = if ($trimmed -match '^\d+$') { 'profile_no' } else { 'profile_id' }
    $p = [ordered]@{ $field = $trimmed }
} elseif ($Command -in $SingleIdArrayCommands) {
    $field = if ($trimmed -match '^\d+$') { 'profile_no' } else { 'profile_id' }
    $p = [ordered]@{ $field = @($trimmed) }
} else {
    Write-Err "命令 $Command 需要 JSON 参数，例如: '{""key"":""value""}'"
    exit 2
}

if ($Command -eq 'create-proxy') {
    # Local API 要求顶层数组；传单个对象时自动包成数组
    if ($p -is [System.Collections.IDictionary]) {
        $p = @($p)
    } elseif ($p -isnot [System.Collections.IList]) {
        Write-Err 'create-proxy 需要 JSON 数组，例如: [{"type":"http","host":"1.2.3.4","port":"8080"}]'
        exit 2
    }
} elseif ($p -isnot [System.Collections.IDictionary]) {
    Write-Err "命令 $Command 需要 JSON 对象参数（以 { 开头）"
    exit 2
}

# ---------- 与原 CLI 一致的默认值与转换 ----------
switch ($Command) {
    'get-browser-list' {
        # Local API 不传 limit 时只返回 1 条，原 CLI 默认 page=1, limit=200
        if (-not $p.Contains('page'))  { $p['page'] = 1 }
        if (-not $p.Contains('limit')) { $p['limit'] = 200 }
    }
    'create-browser' {
        # 未指定 ua_system_version 时按本机系统补上
        $fp = $p['fingerprint_config']
        if ($fp -isnot [System.Collections.IDictionary]) {
            $fp = [ordered]@{}
            $p['fingerprint_config'] = $fp
        }
        $ru = $fp['random_ua']
        if ($ru -isnot [System.Collections.IDictionary]) {
            $ru = [ordered]@{}
            $fp['random_ua'] = $ru
        }
        $current = $ru['ua_system_version']
        if ($null -eq $current -or ($current -is [string] -and $current -eq '')) {
            $osVersion = Get-UaSystemVersion
            if ($osVersion) { $ru['ua_system_version'] = @($osVersion) }
        }
    }
    'restore-recycle-bin' {
        # Local API 要求逗号分隔字符串
        foreach ($k in @('profile_id', 'profile_no')) {
            if ($p[$k] -is [System.Collections.IList]) {
                $p[$k] = (@($p[$k]) | ForEach-Object { [string]$_ }) -join ','
            }
        }
    }
}

# ---------- 构造请求 ----------
if ($Port -le 0) {
    $portSetting = Get-Setting 'ADS_API_PORT'
    $Port = if ($portSetting -match '^\d+$') { [int]$portSetting } else { 50325 }
}

$key = if ($ApiKey) { $ApiKey } else { Get-Setting 'ADS_API_KEY' }
$headers = @{}
if (-not [string]::IsNullOrWhiteSpace($key)) {
    $key = $key.Trim()
    $headers['Authorization'] = "Bearer $key"
}

$method = $Contracts[$Command][0]
$path   = $Contracts[$Command][1]
$uri    = "http://127.0.0.1:$Port$path"
$bodyBytes = $null

if ($method -eq 'GET') {
    $pairs = [System.Collections.Generic.List[string]]::new()
    foreach ($k in @($p.Keys)) {
        $v = $p[$k]
        if ($null -eq $v) { continue }
        if ($v -is [System.Collections.IList]) {
            $v = (@($v) | ForEach-Object { [string]$_ }) -join ','
        } elseif ($v -is [bool]) {
            $v = $v.ToString().ToLowerInvariant()
        }
        $pairs.Add(('{0}={1}' -f [uri]::EscapeDataString([string]$k), [uri]::EscapeDataString([string]$v)))
    }
    if ($pairs.Count -gt 0) {
        $uri = "${uri}?" + ($pairs -join '&')
    }
} else {
    $bodyJson  = ConvertTo-Json -InputObject $p -Depth 50 -Compress
    $bodyBytes = [Text.Encoding]::UTF8.GetBytes($bodyJson)
}

if ($DryRun) {
    $preview = [ordered]@{}
    $preview['method']  = $method
    $preview['url']     = $uri
    $preview['api_key'] = if ($key) { '****' + $key.Substring([Math]::Max(0, $key.Length - 4)) } else { '(none)' }
    if ($method -eq 'POST') { $preview['body'] = $p }
    ConvertTo-Json -InputObject $preview -Depth 50
    exit 0
}

function Invoke-AdsRequest {
    $req = @{
        Uri                = $uri
        Method             = $method
        Headers            = $headers
        SkipHttpErrorCheck = $true
        TimeoutSec         = 120
    }
    if ($null -ne $bodyBytes) {
        $req['Body'] = $bodyBytes
        $req['ContentType'] = 'application/json; charset=utf-8'
    }
    try {
        $resp = Invoke-WebRequest @req
    } catch {
        Write-Err "无法连接 AdsPower Local API ($uri): $($_.Exception.Message)"
        Write-Err "请确认 AdsPower 客户端已启动，并在 设置 > Local API 中已开启（端口 $Port）。"
        exit 2
    }
    $text = [Text.Encoding]::UTF8.GetString($resp.RawContentStream.ToArray())
    $parsed = $null
    try { $parsed = ConvertFrom-JsonText $text } catch { $parsed = $null }
    return [pscustomobject]@{ Status = [int]$resp.StatusCode; Text = $text; Body = $parsed }
}

# Local API 有每秒请求数限制；被限流的请求未被执行，按递增间隔有限次重试是安全的
function Invoke-AdsRequestWithRetry {
    $maxRetry = 4
    for ($attempt = 0; ; $attempt++) {
        $r = Invoke-AdsRequest
        $limited = $r.Body -is [System.Collections.IDictionary] -and $r.Body['code'] -ne 0 -and ([string]$r.Body['msg']) -match '(?i)too many request'
        if (-not $limited -or $attempt -ge $maxRetry) { return $r }
        $waitMs = 1100 * ($attempt + 1)
        Write-Err "触发 Local API 限流，${waitMs}ms 后重试（第 $($attempt + 1)/$maxRetry 次）"
        Start-Sleep -Milliseconds $waitMs
    }
}

# ---------- 发送请求（download-kernel -Poll 时轮询） ----------
$deadline = (Get-Date).AddSeconds([Math]::Max(1, $PollTimeoutSec))
while ($true) {
    $res = Invoke-AdsRequestWithRetry
    if (-not ($Poll -and $Command -eq 'download-kernel')) { break }
    if ($res.Body -isnot [System.Collections.IDictionary] -or $res.Body['code'] -ne 0) { break }
    $data = $res.Body['data']
    $state = if ($data -is [System.Collections.IDictionary]) { [string]$data['status'] } else { '' }
    if ($state -notin @('pending', 'downloading', 'installing')) { break }
    if ((Get-Date) -ge $deadline) {
        Write-Err "轮询超时（${PollTimeoutSec}s），最后状态: $state。稍后再次执行同一命令可查看进度。"
        break
    }
    Write-Err "内核下载中: status=$state progress=$($data['progress'])"
    Start-Sleep -Seconds 3
}

# ---------- 输出与退出码 ----------
if ($res.Body -is [System.Collections.IDictionary]) {
    ConvertTo-Json -InputObject $res.Body -Depth 50
} else {
    $res.Text
}

if ($res.Status -lt 200 -or $res.Status -ge 300) {
    Write-Err "HTTP $($res.Status)"
    exit 1
}
if ($res.Body -isnot [System.Collections.IDictionary]) {
    Write-Err '响应不是 JSON 对象'
    exit 1
}

$code = $res.Body['code']
$msg  = [string]$res.Body['msg']
$inner = $res.Body['data']
if ($Command -eq 'close-all-profiles' -and $inner -is [System.Collections.IDictionary] -and $inner.Contains('code')) {
    # 原 CLI 对该接口检查 data.code
    $code = $inner['code']
    if ($inner['msg']) { $msg = [string]$inner['msg'] }
}

if ($code -ne 0) {
    Write-Err "接口返回错误: code=$code msg=$msg"
    if ($msg -match '(?i)api[- ]?key') {
        Write-Err '提示: 需要有效的 API Key。设置用户环境变量 ADS_API_KEY，或传入 -ApiKey。'
    }
    if ($msg -match '(SunBrowser|FlowerBrowser) (\d+) is not ready') {
        $kernelType = if ($Matches[1] -eq 'FlowerBrowser') { 'Firefox' } else { 'Chrome' }
        Write-Err "提示: 内核未下载。执行 download-kernel '{""kernel_type"":""$kernelType"",""kernel_version"":""$($Matches[2])""}' -Poll 后重试 open-browser。"
    }
    if ($Command -eq 'close-browser' -and $msg -match 'Profile does not exist') {
        Write-Err '提示: 该环境可能未打开，可用 get-opened-browser 查看当前已打开的环境。'
    }
    exit 1
}

exit 0
