---
name: douyin-video-reader
description: 当用户粘贴抖音链接（分享文案、v.douyin.com 短链、www.douyin.com/video|note），或要求「看看这条抖音讲什么」「这个抖音视频/图文是什么内容」「识别一下这个抖音链接」时使用：程序化取回文案、作者、发布时间、话题、互动数据和配乐信息，把图文图片或视频 mp4 落盘、均匀抽帧生成联系图，音轨交给 audio-listener-local 转写并产出可核对的证据目录。全程无可见浏览器、不需要登录、不需要用户接管。
---

# 抖音作品读取（douyin_reader.py）

一条命令把抖音作品变成可核对的本地证据：结构化数据 + 图片/视频帧 + 配乐音轨 + 声音转写。

## 前置

播放能力依赖本机 Chrome（无窗口模式）与已装好的本地音频模型：

```powershell
python "<skill_dir>\scripts\douyin_reader.py" --doctor
```

`ready: true` 才继续。缺 playwright 时：

```powershell
python "<skill_dir>\scripts\setup.py" --dependencies
```

音频模型缺失时用兄弟 Skill 的安装脚本：`python "<skill_dir>\..\audio-listener-local\scripts\setup.py" --models`。

## 用法

```powershell
python "<skill_dir>\scripts\douyin_reader.py" --link "<抖音分享文案或链接>" --output "<新目录>"
```

- `--output` 必须是新目录；脚本不会覆盖已有文件（已有内容会报 `OUTPUT_NOT_EMPTY`）。
- 默认 `--interval 2.0 --max-frames 60`：均匀抽帧做概览联系图，不是逐帧检查。
- `--audio-mode both|speech|sounds` 透传给音频分析（`both` 转写 + 声音标签）。
- `--aweme-id <id> --kind video|note --item-only`：只要结构化数据，不下载媒体。
- `--resolve-only`：只解析短链落点，输出 `kind` 与 `aweme_id`。
- `--debug`：打印页面与通道诊断，链路异常时先用它。

## 产出（全部在 `--output` 目录）

| 文件 | 内容 |
| --- | --- |
| `item.json` | 作品结构化数据：文案、作者、创建时间、话题、互动、图片/视频地址、配乐 |
| `evidence.json` | 上述数据 + 媒体落盘清单 + 抽帧清单 + 音频分析指针 + 边界说明 |
| `证据.md` | 人类可读汇总，可直接作为回答骨架 |
| `images/img_NN.jpg` | 图文作品的全部图片（已转 JPEG，长边 ≤1600） |
| `source.mp4` | 视频作品原片 |
| `frames/`、`contact_XX.jpg` | 视频抽帧与联系图 |
| `audio.wav`、`audio_analysis/` | 16 kHz 单声道音轨与转写/声音标签/声学测量 |

## 作答规则（重要）

- 先 `Read` 证据文件，再 `Read` 图片或联系图，然后才描述画面；不得凭标题或文案臆测画面。
- 时间、数据、互动数一律以 `item.json` / `evidence.json` 为准，不四舍五入、不改口径。
- 抽帧是均匀概览：可以说「抽到的 NN 个时间点里看到…」，不得说「视频里没有…」。
- 图文作品没有视频画面与运镜，只能谈图片内容与配乐，不要编造动态描述。
- 声音结论必须来自 `audio_analysis/`，并与「配乐标题」区分开：标题是平台字段，转写才是听出来的内容。
- 转写为空且标签集中在 Music/Singing 时，写「以音乐为主、未检出可靠人声」；这本身是有效结论，不是失败。
- 回答里要说明数据通道与时间基准：`extraction` 字段会写 `chrome-headless:flight` 或 `chrome-headless:api(...)`。

## 数据通道与已知边界

| 通道 | 说明 |
| --- | --- |
| 纯 HTTP | 短链跳转解析；少数页面 HTML 里直接带作品 JSON |
| `headless:flight` | 图文页把作品对象放在服务端渲染数据里，拼接 `__pace_f` 片段后按 aweme_id 精确匹配 |
| `headless:api` | 视频页由页面自己请求 `/aweme/v1/web/aweme/detail/`，捕获该响应取 `aweme_detail` |

- 只用无窗口浏览器，不弹窗、不登录、不需要扫码；出现登录/验证墙时直接报 `AUTH_REQUIRED` 并停止，不绕过。
- 站点结构变化会让 flight/接口通道失效：此时先用 `--debug` 看 `flight_hit` / `api_hit`，再考虑改用 `--aweme-id --kind --item-only` 单独验证数据层。
- 作品已删除、私密或地区受限时报 `ITEM_DATA_UNAVAILABLE`。
- 不解析评论列表、不抓关注关系、不做批量刷取；单次一个作品。

## 常见报错

| 报错 | 处理 |
| --- | --- |
| `LINK_REQUIRED` | 分享文案里没找到抖音链接 |
| `UNSUPPORTED_PAGE` | 落点不是 `/video/` 或 `/note/`（如直播、合集页） |
| `AUTH_REQUIRED` | 页面要求登录/验证，停止，不绕过 |
| `ITEM_DATA_UNAVAILABLE` | 作品不可见或通道失效，用 `--debug` 复核 |
| `PLAYWRIGHT_MISSING` | 跑 `setup.py --dependencies` |
| `NO_PLAYABLE_MEDIA` | 作品没有可下载播放地址 |
| `OUTPUT_NOT_EMPTY` | 换新目录 |
