param([ValidateSet('Inspect','PortOwner')][string]$Action='Inspect',[int]$Port=9342)
$ErrorActionPreference='Stop'
[Console]::OutputEncoding=New-Object Text.UTF8Encoding($false)
$rows=@(Get-CimInstance Win32_Process -Filter "Name='DoubaoWork.exe'" | Where-Object {$_.ExecutablePath})
$main=@($rows|Where-Object {$_.CommandLine -and $_.CommandLine -notmatch '--type='})
$known=Join-Path $env:LOCALAPPDATA 'DoubaoWork\Application\app\DoubaoWork.exe'
$exe=if($main.Count -eq 1){$main[0].ExecutablePath}elseif(Test-Path -LiteralPath $known -PathType Leaf){$known}else{throw '未找到当前豆包工作桌面客户端'}
$exe=(Resolve-Path -LiteralPath $exe).ProviderPath
if($Action -eq 'Inspect'){
 $ports=@();$net=& netstat.exe -ano -p tcp
 foreach($line in $net){$parts=$line.Trim() -split '\s+';if($parts.Count -ge 5 -and $parts[0] -eq 'TCP' -and $parts[2] -match ':0$' -and [int]$parts[4] -in @($rows.ProcessId)){if($parts[1] -match ':(\d+)$'){$ports+=[int]$Matches[1]}}}
 $debugPort=0;if($main.Count -eq 1 -and $main[0].CommandLine -match '--remote-debugging-port=(\d+)'){$debugPort=[int]$Matches[1]}
 [pscustomobject]@{executable=$exe;running=($rows.Count -gt 0);mainDebugPort=$debugPort;ports=@($ports|Select-Object -Unique);version=(Get-Item -LiteralPath $exe).VersionInfo.ProductVersion}|ConvertTo-Json -Depth 4 -Compress
}else{
 if($Port -lt 1 -or $Port -gt 65535){throw '端口无效'}
 $owners=@();$net=& netstat.exe -ano -p tcp
 foreach($line in $net){$parts=$line.Trim() -split '\s+';if($parts.Count -ge 5 -and $parts[0] -eq 'TCP' -and $parts[2] -match ':0$' -and $parts[1] -match ":$Port`$"){
  if($parts[1] -notmatch '^(127\.0\.0\.1|\[::1\]):'){throw '调试端口不是仅本机回环监听，拒绝连接'}
  $owners+=[int]$parts[4]
 }}
 if($owners.Count -eq 0){throw '未找到调试端口监听进程'}
 foreach($owner in @($owners|Select-Object -Unique)){$p=Get-CimInstance Win32_Process -Filter "ProcessId=$owner";if(-not $p.ExecutablePath -or $p.ExecutablePath -ine $exe){throw '端口不属于已定位的豆包工作客户端'}}
 [pscustomobject]@{ok=$true;executable=$exe;port=$Port}|ConvertTo-Json -Compress
}
