# 配置与个性化定制指南

## 目录
1. 三步上线
2. 如何定制运营方向
3. 如何定制内容（母题 / 视觉 / 文案 / BGM）
4. 配置加载与冲突处理

## 1. 三步上线

1. 复制 `assets/operator-config.yaml` 到用户的工作目录（建议放在项目根，命名仍为 `operator-config.yaml`）。
2. 至少填好 `account`（昵称、抖音号）和 `goal.primary`，其余按需调整；不填则用默认。
3. 首次运行先打开创作者中心完成登录（扫码/验证码只能用户本人做），之后按 `schedule` 自动备稿、发布。

## 2. 如何定制运营方向

运营方向由两个字段共同决定：

- `goal.primary`：当前阶段第一优先级
  - `followers` 涨粉优先：强化关注理由、系列化、结尾引导关注。
  - `traffic` 流量优先：强化开头钩子与话题，争取更大公域推荐。
  - `monetize` 变现优先：在已有粉丝基础上调整内容与转化路径。
- `topics`：账号讲什么。可启用、停用、新增任意母题，并用 `weight` 控制各母题的排期比例。

排期规则：按 `weight` 做加权轮换，`enabled: false` 的母题不参与；同一母题避免连续出现超过 2 次，保持内容新鲜度。

## 3. 如何定制内容

### 新增一个母题
在 `topics` 下照现有格式追加：`name / subject / angle / structure / ending / sources`。`structure` 是该母题的文案骨架，按数组顺序组织段落。

### 视觉
`visual.style_keywords` 直接决定图片生成提示词；改 `aspect_ratio` 可切换横竖屏，但需同步调整 `resolution`。

### 文案
- `max_chars` 必须 ≤950（平台 1000 字硬上限，超出会截断丢结尾）。
- `hashtags_count` 保持 5，实测第 6 个话题会替换第 5 个。
- 打开 `comment_prompt` / `follow_reason` 可分别针对"评论为 0""吸粉为 0"的问题。

### BGM
`bgm.pick_method` 固定 `hot_chart`：从音乐面板「热门榜」挑符合意境的曲目，不做关键词搜索、避开冷门曲；`by_theme` 为各母题指定曲风。

## 4. 配置加载与冲突处理

- 每次执行先读用户工作目录的 `operator-config.yaml`；读不到再回退到 `assets/operator-config.yaml` 的默认模板。
- 用户在对话中给出的**最新口头指令优先级高于配置文件**；若与配置冲突，以最新指令为准，并回写配置保持一致。
- 所有账号数据只来自创作者中心真实页面，配置文件不用于编造任何数字。
