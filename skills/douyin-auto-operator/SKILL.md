---
name: douyin-auto-operator
description: 抖音账号自动运营：用户想把抖音账号交给 AI 自动或半自动运营，或要制作并发布「横屏氛围图+深度长文案+话题+BGM」图文、读取创作者中心真实数据复盘、定时备稿和发布时使用。覆盖账号定位、内容制作、创作者中心网页发布、数据复盘与定时排期（如每天 20:00 发布、前一天 22:00 备稿）；运营方向、内容母题、视觉风格、BGM、发布时间都可在 operator-config.yaml 里个性化定制，也适用于历史人文、未来星际等故事型 AIGC 账号。
---

# 抖音自动运营（Douyin Auto Operator）

把一个抖音账号按既定定位持续运营：读配置 → 登录 → 备稿 → 发布 → 读真实数据复盘，形成日更闭环。所有运营方向与内容都以配置文件为准，可被用户随时改写。

## 0. 前置条件

- 用户已有抖音账号，并能在浏览器里登录抖音创作者中心 https://creator.douyin.com/ 。首次登录、扫码、短信验证只能由用户本人完成。
- 浏览器操作通过豆包工作的浏览器能力完成：先读取当前环境里的浏览器自动化 skill（`browser-use-automation`）再操作。
- 指标脚本需要 Python 3，只用标准库（豆包工作在电脑和云主机上都自带 Python）。找不到 Python 时，按第 5 节的公式手算，不要因此中断运营。
- 定时备稿、发布需要豆包工作的定时任务能力；云端任务和用户电脑上的浏览器登录态不互通，换环境后首次运行需用户重新登录。
- 发布的是 AI 生成的图文，发布前在平台的内容声明里勾选「含有 AI 生成内容」（按平台当前提供的标识功能操作）。

## 1. 首次使用：先加载配置

1. 让用户复制并填写 `assets/operator-config.yaml`（至少填账号昵称、抖音号、阶段目标）。配置字段含义见 `references/configuration.md`。
2. 每次执行先读用户工作目录的 `operator-config.yaml`；读不到再回退本技能 assets 内的默认模板。
3. 用户在对话中的**最新口头指令优先级高于配置**；冲突时以最新指令为准，并回写配置保持一致。

## 2. 标准工作流

### 备稿（默认前一天 22:00）
1. 打开创作者中心，确认登录态；视口异常先修复（见第 3 节）。
2. 读取当日作品真实数据，用 `scripts/calc_metrics.py` 计算比率并与历史、阈值对比。
3. 数据与复盘追加写入运营日志，输出简洁汇报。
4. 按 `topics` 的权重轮换确定次日母题，制作：横屏图（图片生成遵循 `visual`）+ ≤950 字长文案（遵循 `copywriting`）+ 5 个真实话题 + 热门榜 BGM，保存为草稿。

### 发布（默认每天 20:00）
1. 打开当天草稿，逐项核对：图、正文结尾完整、5 个可点击话题、BGM 已绑定、"谁可以看"为公开。
2. 核对无误后点发布；触发安全验证则交用户本人完成。
3. 到内容管理页确认"已发布"、作品数 +1。

`workflow.review_before_publish` 为 true 时，发布前必须先送审、得到用户确认；为 false 时按计划自动发布，但用户在发布前始终可干预。

## 3. 网页操作要点

完整、低自由度的操作步骤与选择器见 `references/creator-center-sop.md`，关键几条：

- 浏览器模块：本地 Windows 用 `aha_browser_use`，云主机 Linux 用 `seed_browser_use`，均在 `computer_use_tool(plane="bu")` 内 `import ... as bu`。
- 视口被缩到极窄导致点击落空：用 CDP `Emulation.setDeviceMetricsOverride(width=1280,height=881,mobile=False)` 恢复。
- 上传从首页"发布图文"进入 `/content/upload?default-tab=3`，用 `bu.upload_file('input[type="file"]', 绝对路径)`。
- 描述区中文用 `document.execCommand('insertText', false, 文本)` 才能触发话题识别；话题稳定上限 5 个。
- BGM 从音乐面板「热门榜」选，JS 点 `span.action-Q1y01k` 打开面板，绑定后回读核对。
- 单选/复选对隐藏的 `input.radio-native` 执行 `.click()`，点 label 无效。

## 4. 内容方法与定时排期

- 内容公式、钩子写法、两大母题模板、按数据反馈优化：见 `references/content-playbook.md`。
- 定时任务（备稿/发布两个 cron）的创建步骤与可复用 query 模板：见 `references/scheduling.md`。
- 定期用视频提取能力学习同赛道高赞作品，沉淀开头钩子、结构、史料/设问、画面与 BGM，再经自家数据验证。

## 5. 指标脚本

脚本在本 SKILL.md 同目录下的 `scripts/calc_metrics.py`，数字一律取自创作者中心页面（下面是示例值）：

```bash
python scripts/calc_metrics.py --plays 1000 --likes 35 --comments 2 --shares 1 --favorites 6 --swipe 48.5
```

输出点赞率、评论率、分享率、收藏率（JSON），并给出合格/优质、健康/偏高判断。默认阈值是点赞率 3%/5%、划走率 55%；配置里改了 `goal.benchmark` 时，用 `--like-good`、`--like-great`、`--swipe-healthy` 传入同样的值。播放为 0 时比率输出 null、判断为"无数据"。

没有 Python 时手算：点赞率 = 点赞 ÷ 播放 × 100（保留两位小数），评论率、分享率、收藏率同理；划走率直接取页面数值。

## 6. 硬纪律

- 登录、扫码、短信/安全验证只能用户本人完成，用 `interaction.request_action` 交接，不反复重试、不绕过。
- 所有数据只来自创作者中心真实页面，禁止杜撰任何数字；不同页面口径不一致时以内容管理页为准。
- 当日未发布或草稿不合格要如实说明，不虚报、不临时凑内容。
- 正文始终 ≤950 字、每条必配 BGM、话题恰好 5 个，缺任一项视为不合格。
- AI 生成的图文按平台要求主动声明「含有 AI 生成内容」，不删除、不隐藏平台或生成工具加上的 AI 标识。
