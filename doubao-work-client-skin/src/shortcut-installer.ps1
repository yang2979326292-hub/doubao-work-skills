param([ValidateSet('Install','Restore')][string]$Action='Install')
$ErrorActionPreference='Stop'
[Console]::OutputEncoding=New-Object Text.UTF8Encoding($false)
$root=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).ProviderPath
$data=Join-Path $root 'data'
$launcher=Join-Path $root '豆包工作-皮肤启动.exe'
$manifest=Join-Path $data 'startup-shortcuts.json'
$shell=New-Object -ComObject WScript.Shell
if($Action -eq 'Install'){
 if(-not (Test-Path -LiteralPath $launcher -PathType Leaf)){throw '皮肤启动器缺失'}
 if(Test-Path -LiteralPath $manifest -PathType Leaf){throw '启动入口已安装，未覆盖原备份。需要重装请先恢复入口。'}
 $dirs=@([Environment]::GetFolderPath('Desktop'),[Environment]::GetFolderPath('Programs'))
 $official=Join-Path $env:LOCALAPPDATA 'DoubaoWork\Application\DoubaoWork.exe'
 $targets=@();foreach($dir in $dirs){if(Test-Path -LiteralPath $dir -PathType Container){foreach($file in Get-ChildItem -LiteralPath $dir -Filter '*.lnk' -Recurse -Force){$link=$shell.CreateShortcut($file.FullName);if($link.TargetPath -ieq $official){$targets+=$file.FullName}}}}
 if($targets.Count -eq 0){throw '未找到指向真实豆包工作的桌面或开始菜单入口，未修改其他快捷方式。'}
 $backup=Join-Path $data ('启动入口备份-'+(Get-Date -Format 'yyyyMMdd-HHmmss'));New-Item -ItemType Directory -Path $backup | Out-Null
 $entries=@();$index=0
 foreach($target in $targets){$index++;$copy=Join-Path $backup ($index.ToString()+'.lnk');Copy-Item -LiteralPath $target -Destination $copy;$link=$shell.CreateShortcut($target);$entries+=[pscustomobject]@{path=$target;backup=$copy;originalHash=(Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash;installedHash='';target=$link.TargetPath;arguments=$link.Arguments;workingDirectory=$link.WorkingDirectory;icon=$link.IconLocation}}
 # Write the backup index BEFORE changing any entry, to permit recovery after interruption.
 $record=[pscustomobject]@{version=1;root=$root;launcher=$launcher;installedAt=(Get-Date).ToString('o');entries=$entries}
 [IO.File]::WriteAllText($manifest,($record|ConvertTo-Json -Depth 8),(New-Object Text.UTF8Encoding($false)))
 try{foreach($entry in $entries){$link=$shell.CreateShortcut($entry.path);$link.TargetPath=$launcher;$link.Arguments='';$link.WorkingDirectory=$root;$link.Save();$verified=$shell.CreateShortcut($entry.path);if($verified.TargetPath -ine $launcher){throw '启动入口回读不匹配'};$entry.installedHash=(Get-FileHash -LiteralPath $entry.path -Algorithm SHA256).Hash;[IO.File]::WriteAllText($manifest,($record|ConvertTo-Json -Depth 8),(New-Object Text.UTF8Encoding($false)))}}
 catch{foreach($entry in $entries){$current=$shell.CreateShortcut($entry.path);if($current.TargetPath -ieq $launcher){Copy-Item -LiteralPath $entry.backup -Destination $entry.path}};throw}
 [pscustomobject]@{installed=$true;count=$entries.Count;entries=$entries;manifest=$manifest}|ConvertTo-Json -Depth 8
}else{
 if(-not (Test-Path -LiteralPath $manifest -PathType Leaf)){throw '没有本工具的入口备份记录'}
 $record=ConvertFrom-Json -InputObject ([IO.File]::ReadAllText($manifest,(New-Object Text.UTF8Encoding($false,$true))))
 if($record.root -ine $root -or $record.launcher -ine $launcher){throw '备份不属于当前插件目录'}
 # Validate ALL candidates before restoring any; do not overwrite later user changes.
 foreach($entry in $record.entries){if(-not (Test-Path -LiteralPath $entry.backup -PathType Leaf)){throw '备份缺失'};if((Get-FileHash -LiteralPath $entry.backup -Algorithm SHA256).Hash -ne $entry.originalHash){throw '备份校验失败'};if(-not (Test-Path -LiteralPath $entry.path -PathType Leaf)){throw '入口已被移除，未自行重建'};$current=(Get-FileHash -LiteralPath $entry.path -Algorithm SHA256).Hash;if($current -ne $entry.installedHash -and $current -ne $entry.originalHash){throw '入口安装后被修改，未覆盖新改动'}}
 foreach($entry in $record.entries){Copy-Item -LiteralPath $entry.backup -Destination $entry.path;if((Get-FileHash -LiteralPath $entry.path -Algorithm SHA256).Hash -ne $entry.originalHash){throw '恢复回读失败'}}
 $history=Join-Path $data ('startup-shortcuts-restored-'+(Get-Date -Format 'yyyyMMdd-HHmmss')+'.json');Move-Item -LiteralPath $manifest -Destination $history
 [pscustomobject]@{restored=$true;count=@($record.entries).Count;history=$history}|ConvertTo-Json
}
