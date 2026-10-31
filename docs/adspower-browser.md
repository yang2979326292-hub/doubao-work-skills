# adspower-browser 使用说明

让豆包工作通过 AdsPower 客户端的 Local API 管理指纹浏览器。改写自 AdsPower 官方的 [AdsPower/adspower-browser](https://github.com/AdsPower/adspower-browser)（MIT）：原版通过 npm 包调用，这个版本改成一个 PowerShell 7 脚本，直接请求 Local API，不需要安装 Node 包。命令名和参数与原 CLI 一致。

## 能做什么

- 浏览器环境：打开、关闭、新建、修改、删除、查询，回收站恢复，移动分组，读取 Cookie 和 UA，重新生成指纹，清理缓存，分享给其他账号
- 分组、标签、代理（包括动态代理流量查询）、团队成员管理
- 浏览器内核的查询和下载，客户端补丁更新

不包含网页内的点击、输入、截图等页面自动化。

## 使用前准备

1. 在**豆包工作连接的那台 Windows 电脑**上安装并启动 AdsPower 客户端，在 设置 → Local API 中开启（默认端口 50325）。
2. 告诉豆包工作你的 API Key（在 AdsPower 的 Local API 设置页可以看到）。豆包工作会把它保存到你电脑的用户环境变量 `ADS_API_KEY`，不会写进任何文件。也可以自己在 PowerShell 里设置：

   ```powershell
   [Environment]::SetEnvironmentVariable('ADS_API_KEY', '<你的 API Key>', 'User')
   ```

3. 端口不是 50325 时，再设置环境变量 `ADS_API_PORT`。

## 在豆包工作里怎么说

- “列出我所有的 AdsPower 环境”
- “打开名字叫 XXX 的环境” / “打开 3 号环境”
- “新建一个环境，放到 XXX 分组，不用代理”
- “把这几个环境移到 XXX 分组”
- “关闭所有已打开的环境”

删除环境、删除成员、重置密码、分享环境等不可逆操作，如果你没有点名具体对象，豆包工作会先列出受影响的对象，等你确认后再执行。

## 手动调用脚本

需要 PowerShell 7（`pwsh`），Windows 自带的 Windows PowerShell 5.1 不支持。

```powershell
$ads = '<skill目录>\scripts\adspower-api.ps1'
& $ads check-status                              # 检查 Local API 是否可用
& $ads get-browser-list                          # 列出环境（默认每页 200 条）
& $ads open-browser 3                            # 打开编号为 3 的环境
& $ads delete-browser '{"profile_id":["id1"]}' -DryRun   # 只预览请求，不执行
& $ads -ListCommands                             # 列出全部 41 个命令
```

退出码：0 成功；1 接口返回错误；2 用法错误或连不上 Local API。

## 和原版的区别

- 不依赖 Node.js 和 npm 包，只需要 PowerShell 7。
- 保留了原 CLI 的行为：简写参数、`get-browser-list` 默认 `limit=200`、新建环境时按本机系统补 UA、回收站恢复的参数转换。
- 新增：触发限流时自动重试（最多 4 次）、`-DryRun` 预览、`download-kernel -Poll` 跟踪下载进度，以及明确的退出码。

## 已知限制

- `get-dynamic-proxy-traffic` 在 AdsPower Global 8.4.3 上返回 404，需要更新的客户端。
- 实测环境：Windows 11 + PowerShell 7.6 + AdsPower Global 8.4.3，读取类命令实际调用成功，写入类命令（打开、新建、删除等）只用 `-DryRun` 检查过请求内容。Linux 上的 PowerShell 7 能解析和预览请求，但 AdsPower 必须在本机运行，所以云主机上无法实际使用。macOS 没有实测。

## 历史

最早单独发布在 [adspower-browser-skill](https://github.com/yang2979326292-hub/adspower-browser-skill)，现在迁移到本合集，以后只在这里更新。
