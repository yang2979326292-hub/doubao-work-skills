---
name: adspower-browser
description: "用户提到 AdsPower、指纹浏览器，或要打开、关闭、新建、修改、删除、查询浏览器环境（profile、配置文件），管理分组、标签、代理、团队成员时使用：通过本机 AdsPower 客户端的 Local API 完成操作。也覆盖回收站、Cookie、UA、指纹、缓存、动态代理流量、内核下载、客户端补丁和 API 状态检查。脚本为 PowerShell 7，必须在用户的 Windows 电脑上执行，云主机连不到本机 AdsPower；不负责网页内的点击、输入等页面自动化。"
---

# AdsPower 指纹浏览器（Local API）

改写自 AdsPower 官方 `adspower-browser` CLI（MIT，见 LICENSE.txt）。命令名和参数与原 CLI 一致，由 `scripts/adspower-api.ps1` 直接请求本机 Local API。

## 前置条件

- 必须在用户本机的 Windows 环境执行。AdsPower 客户端和 Local API（127.0.0.1）都在用户电脑上，云主机连不到；当前执行环境是云主机时，先切换到用户电脑。
- AdsPower 客户端已启动，并在 设置 → Local API 中开启（默认端口 50325）。
- 需要 PowerShell 7（`pwsh`）。豆包工作在电脑上执行命令时用的就是它自带的 PowerShell 7；Windows 自带的 Windows PowerShell 5.1 不支持，脚本会直接报错。
- API Key 按 `-ApiKey` → 进程环境变量 `ADS_API_KEY` → 用户级 / 系统级环境变量 `ADS_API_KEY` 的顺序读取。还没配置时，请用户提供 Key，再写入用户环境变量：
  `[Environment]::SetEnvironmentVariable('ADS_API_KEY', '<key>', 'User')`
  端口不是默认值时，设置 `ADS_API_PORT` 或传 `-Port`。
- 不要在回复里回显 API Key，也不要把它写进任何文件。

## 调用方式

脚本在本 SKILL.md 同目录下的 `scripts/adspower-api.ps1`。先把 `<skill目录>` 换成本 SKILL.md 所在目录的绝对路径：

```powershell
$ads = Join-Path '<skill目录>' 'scripts\adspower-api.ps1'
& $ads check-status
& $ads get-browser-list                          # 默认 page=1, limit=200
& $ads open-browser abcd1234                     # 简写：非纯数字 → profile_id
& $ads open-browser 3                            # 简写：纯数字 → profile_no
& $ads create-browser '{"group_id":"0","name":"新环境","user_proxy_config":{"proxy_soft":"no_proxy"}}'
& $ads create-browser -ParamsFile C:\path\params.json     # 大段 JSON 写到 UTF-8 文件
& $ads delete-browser '{"profile_id":["id1"]}' -DryRun    # 只打印将发送的请求，不调用
& $ads -ListCommands                             # 列出全部 41 个命令及 HTTP 路径
```

- stdout 是接口返回的完整 JSON（`code` / `msg` / `data`），提示和进度写到 stderr。
- 退出码：0 成功；1 接口返回 code≠0 或 HTTP 错误；2 用法错误或连不上 Local API。
- JSON 用 PowerShell 单引号包裹；值里有单引号时写成 `''`，或改用 `-ParamsFile`。
- 支持简写的命令：open-browser、close-browser、get-profile-cookies、get-browser-active、get-profile-ua、new-fingerprint。

## 命令速查

### 浏览器环境

| 命令 | 关键参数 |
|---|---|
| `open-browser` | `profile_id` 或 `profile_no`；可选 `ip_tab`、`launch_args`、`headless`、`last_opened_tabs`、`proxy_detection`、`password_filling`、`password_saving`、`cdp_mask`、`delete_cache`、`device_scale`（开关类取 `"0"`/`"1"`） |
| `close-browser` | `profile_id` 或 `profile_no` |
| `get-opened-browser` / `close-all-profiles` | 无参数 |
| `get-browser-list` | `group_id`、`page`、`limit`(1–200)、`profile_id[]`、`profile_no[]`、`sort_type`、`sort_order`、`tag_ids`、`tags_filter`、`name`、`name_filter` |
| `create-browser` | `group_id` 必填（`"0"` 为未分组）；`proxyid` 或 `user_proxy_config` 二选一，未指定代理时用 `{"proxy_soft":"no_proxy"}`；可选 `name`、`remark`、`tabs[]`、`platform`、`profile_tag_ids[]`、`fingerprint_config` 等 |
| `update-browser` | `profile_id` 必填，其余只传要改的字段 |
| `delete-browser` | `profile_id[]` |
| `get-recycle-bin-list` | `page`、`limit`(1–100)，仅近 30 天 |
| `restore-recycle-bin` | `profile_id[]` 或 `profile_no[]`，`group_id` 必填 |
| `move-browser` | `group_id`、`user_ids[]` |
| `get-profile-cookies` / `get-browser-active` | `profile_id` 或 `profile_no` |
| `get-profile-ua` / `new-fingerprint` | `profile_id[]` 或 `profile_no[]`（每次最多 10 个） |
| `delete-cache-v2` | `profile_id[]`、`type[]`（local_storage / indexeddb / extension_cache / cookie / history / image_file），需先关闭环境 |
| `share-profile` | `profile_id[]`、`receiver`；可选 `share_type`、`content[]` |
| `get-cloud-active` | `user_ids`（逗号分隔字符串，最多 100 个） |

### 分组、标签、代理、成员及其他

| 命令 | 关键参数 |
|---|---|
| `get-group-list` / `create-group` / `update-group` | `group_name`、`page`、`page_size` / `group_name`、`remark` / `group_id`、`group_name` |
| `get-tag-list` / `create-tag` / `update-tag` / `delete-tag` | `ids`、`page`、`limit` / `tags:[{name,color}]` / `tags:[{id,name?,color?}]` / `ids[]` |
| `get-proxy-list` / `create-proxy` / `update-proxy` / `delete-proxy` | `page`、`limit`、`proxy_id[]` / 顶层数组 `[{type,host,port,...}]` / `proxy_id` 加要改的字段 / `proxy_id[]`（最多 100 个） |
| `get-dynamic-proxy-traffic` | 可选 `start_date`、`end_date`（YYYY-MM-DD） |
| `get-member-list` / `get-member-group-list` | `user_group_id`、`user_id[]`、`email[]`、`page`、`limit` / `page`、`limit` |
| `create-member` / `update-member` | `user_group_id`、`email`、`password`、`identity`(2 管理员、3 经理、4 员工) / `user_id` 加要改的字段 |
| `reset-member-password` / `delete-member` | `user_id` |
| `get-application-list` | `category_id`、`page`、`limit` |
| `get-kernel-list` / `download-kernel` | 可选 `kernel_type` / `kernel_type`(Chrome、Firefox)、`kernel_version` |
| `update-patch` | 可选 `version_type`(stable、beta) |
| `check-status` | 无参数 |

## 执行规则

1. 先执行 `check-status`。退出码为 2 时，提示用户打开 AdsPower 客户端并开启 Local API，不要反复重试。
2. 用户给的是环境名称、分组名称或标签名称时，先查询换成 ID：环境用 `get-browser-list` 加 `name` 过滤，分组用 `get-group-list` 加 `group_name`，标签用 `get-tag-list`。匹配到多个结果时列出来让用户选择。
3. 要取全量数据时：`get-browser-list` 检查 `data.total_pages`，大于 1 就用相同过滤条件逐页请求。对一组环境执行操作前，先收集全部 profile_id。Local API 有每秒请求数限制（返回 `Too many request per second`），脚本会自动重试最多 4 次；批量调用时仍要在两次调用之间间隔约 1 秒。
4. 以下操作不可逆或影响范围大：delete-browser、delete-member、reset-member-password、delete-proxy、delete-tag、share-profile、close-all-profiles、delete-cache-v2、update-patch。用户没有明确点名对象时，先列出受影响的对象请用户确认，可以用 `-DryRun` 预览请求。delete-member 无法恢复；reset-member-password 返回的新密码只告知用户本人。
5. create-browser 没有指定 `fingerprint_config.random_ua.ua_system_version` 时，脚本会按本机系统自动补上（例如 Windows 11 补 `Windows 11`），与原 CLI 行为一致。需要其他系统的 UA 时显式传入，取值见 references/ua-system-version.md。
6. 常见错误（脚本会在 stderr 给出提示）：
   - `Require api-key` 或 `API Key mismatch`：请用户在 AdsPower 设置中核对 API Key，并更新用户环境变量 `ADS_API_KEY`。
   - `SunBrowser|FlowerBrowser N is not ready`：内核还没下载。执行 `download-kernel '{"kernel_type":"Chrome","kernel_version":"N"}' -Poll`（FlowerBrowser 对应 Firefox），完成后重试 open-browser。
   - close-browser 返回 `Profile does not exist`：用 get-opened-browser 查看当前已打开的环境。
   - 某个命令返回 `HTTP 404 Not Found`：当前客户端版本还没有这个接口。已知 `get-dynamic-proxy-traffic` 在 AdsPower Global 8.4.3 上会返回 404（2026-10-31 实测）。告诉用户需要升级客户端，不要换路径猜测。
7. `download-kernel` 加 `-Poll` 会每 3 秒轮询一次，直到状态为 completed 或 failed（默认最长 240 秒，可用 `-PollTimeoutSec` 调整）。超时后再次执行同一命令即可查看进度。
8. `update-patch` 会让客户端更新补丁。原 CLI 更新后会等待 60 秒并重启它自带的 runtime；桌面客户端由客户端自己处理，之后用 check-status 确认已恢复。
9. 本 skill 只负责环境和账号层面的管理。打开环境后的网页操作（点击、输入、截图）不在脚本范围内；确有需要时，可通过 open-browser 返回的调试地址用 CDP 连接（如 Playwright `connect_over_cdp`），或使用原仓库的 local-api-mcp。

## 参考文档

需要精确字段或枚举值时再读：

| 文档 | 内容 |
|---|---|
| references/tool-intent-map.md | 中英文说法与命令的对应关系 |
| references/browser-profile-management.md | 浏览器环境类命令的完整参数 |
| references/user-proxy-config.md | `user_proxy_config` 字段 |
| references/fingerprint-config.md | `fingerprint_config` 字段 |
| references/browser-kernel-config.md | `browser_kernel_config` 的 type 与 version |
| references/ua-system-version.md | `ua_system_version` 枚举 |
| references/chrome-tls-cipher.md | TLS 指纹配置 |
| references/country-code.md | 国家代码 |
| references/group-management.md | 分组参数 |
| references/browser-tag-management.md | 标签参数 |
| references/proxy-management.md | 代理参数与动态代理流量 |
| references/member-management.md | 团队成员参数 |
| references/application-management.md | check-status、应用分类 |
| references/browser-kernel-management.md、references/browser-kernel-download-management.md | 内核列表与下载 |
| references/client-patch-management.md | 客户端补丁 |
