# 抖音创作者中心操作 SOP

低自由度流程：以下步骤均来自真实验证，按顺序执行；选择器类名若随平台改版失效，先用快照重新定位再操作。

## 目录
1. 环境与登录
2. 视口修复
3. 上传图片
4. 输入正文与绑定话题
5. 绑定 BGM
6. 设置公开与发布
7. 读取真实数据
8. 已验证的死路与对策

## 1. 环境与登录

- 浏览器模块：本地 Windows 用 `aha_browser_use`；云主机 Linux 用 `seed_browser_use`（接口同构；注意 `get_page_text()` 不带 `max_chars` 参数）。代码统一在 `computer_use_tool(plane="bu")` 内 `import ... as bu`。
- 登录、扫码、短信/安全验证只能用户本人完成：出现登录拦截时调用 `interaction.request_action`（type=browserControl），不要用文字代替、不要反复重试。
- 云端与本地浏览器登录态不互通；换环境后首次通常需要重新登录。

## 2. 视口修复

若点击全部落空、`elementFromPoint` 返回 null，先查 `window.innerWidth`。异常窄（如 197px）时用 CDP 恢复：

```python
bu.cdp("Emulation.setDeviceMetricsOverride", {"width":1280,"height":881,"mobile":False})
```

切换标签后可能需要重新设置。

## 3. 上传图片

1. 从首页点"发布图文"进入 `/content/upload?default-tab=3`（直接导航发布 URL 时主 DOM 没有 file input，必须从首页卡片进入）。
2. 上传：

```python
bu.upload_file('input[type="file"]', 绝对路径)
```

## 4. 输入正文与绑定话题

- 描述区是自研 contenteditable 引擎，中文必须用：

```python
bu.js("document.execCommand('insertText', false, 文本)")
```

直接赋值 innerText 不会触发话题识别。
- 话题：在正文末尾输入 `#词`，平台弹出候选后选中，使其成为可点击话题；单条稳定上限 5 个，第 6 个会替换第 5 个。
- 描述区 1000 字硬上限，正文控制在 950 字内。

## 5. 绑定 BGM

1. 视口正常时，用 JS 点击 `span.action-Q1y01k` 打开音乐面板。
2. 进入「热门榜」分类，从榜单挑符合图文意境的曲目（不关键词搜索）。
3. 点目标歌曲卡片内的"使用"按钮；绑定后回读歌曲名核对，防止误绑。

## 6. 设置公开与发布

- "谁可以看"等单选/复选：可点元素是 `label.radio-d4zkru`，其内部隐藏原生 `input.radio-native`。坐标点 label 不生效，直接对原生 input 执行 `.click()`：

```python
bu.js("document.querySelector('input.radio-native').click()")
```

- 确认图、正文、5 话题、BGM、公开权限无误后点"发布"。若弹出安全验证，交用户本人完成。
- 发布后到内容管理页确认状态"已发布"、作品总数 +1。

## 7. 读取真实数据

- 内容管理页：每条作品的播放、点赞、评论、分享、收藏、划走率/2 秒跳出、文案展开率、完播率、平均浏览图片数、吸粉量。
- 首页：账号累计关注、粉丝、获赞；数据中心图表（统计周期与更新时间以页面标注为准）。
- 不同页面同一指标可能因实时更新略有差异，统一以内容管理页为准。

## 8. 已验证的死路与对策

| 现象 | 原因 | 对策 |
|---|---|---|
| 坐标点击全空、elementFromPoint=null | 视口被缩到极窄 | setDeviceMetricsOverride 恢复 |
| 直接打开发布 URL 找不到 file input | 主 DOM 未初始化 | 从首页"发布图文"进入 |
| 输入中文不触发话题 | 直接赋值不触发引擎 | execCommand insertText |
| 点 label 没反应 | 原生 input 隐藏 | 对 input.radio-native .click() |
| 绑错歌曲 | 卡片"使用"按钮混淆 | 绑定后回读核对 |
| 系统文件对话框阻塞自动化 | 触发原生选择器 | 新开标签绕过；文件类操作优先用 upload_file |
| 登录/验证无法自动通过 | 需本人 | interaction.request_action 交用户 |
