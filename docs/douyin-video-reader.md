# douyin-video-reader 使用说明

## 能做什么

把一条抖音链接变成一份可核对的本地证据目录：

- 文案、作者、发布时间、话题、互动数、配乐信息（标题 / 作者 / 时长 / 是否原声）
- 图文作品：全部图片落盘（转 JPEG，长边 ≤1600）
- 视频作品：原片 `source.mp4`、均匀抽帧 `frames/`、拼版联系图 `contact_XX.jpg`
- 音轨 `audio.wav` + 转写（自动调用 `audio-listener-local`）
- `证据.md`：一段现成的汇总，可以直接当回答骨架

支持分享文案、`v.douyin.com` 短链、`www.douyin.com/video/<id>`、`www.douyin.com/note/<id>`。全程不弹窗、不登录、不需要扫码；碰到登录/验证墙直接报 `AUTH_REQUIRED` 停下，不绕过。

## 使用前准备

1. 本机要有 **Google Chrome**（脚本用它的无窗口模式，不下载浏览器包）。
2. Python 3 环境（豆包工作在 Windows 电脑上自带）。
3. 第一次使用前装依赖，只装进 skill 自己的 `.runtime`：

   ```powershell
   python "<skill_dir>\scripts\setup.py" --dependencies
   ```

4. 自检：

   ```powershell
   python "<skill_dir>\scripts\douyin_reader.py" --doctor
   ```

   `ready: true` 才继续。视频/图文的音轨转写还要兄弟 skill `audio-listener-local` 的模型，缺模型时跑：

   ```powershell
   python "<skill_dir>\..\audio-listener-local\scripts\setup.py" --models
   ```

## 在豆包工作里怎么说

直接粘链接就行：

- “看看这条抖音讲什么 https://v.douyin.com/xxxxxx/”
- “这个抖音视频/图文是什么内容”
- “识别一下这个抖音链接，把图片和配乐都拿出来”

豆包工作会调用脚本，得到证据目录后先读证据、再读图片或联系图，然后才描述画面。

## 手动调用脚本

```powershell
python "<skill_dir>\scripts\douyin_reader.py" --link "<抖音分享文案或链接>" --output "<新目录>"
```

常用参数：

| 参数 | 作用 |
|---|---|
| `--interval 2.0 --max-frames 60` | 抽帧间隔与帧数上限（均匀概览，不是逐帧检查） |
| `--audio-mode both\|speech\|sounds` | 转写给音频分析的模式，`speech` 只转写 |
| `--resolve-only` | 只解析短链落点，打印 `kind` 与 `aweme_id` |
| `--aweme-id <id> --kind video\|note --item-only` | 只要结构化数据，不下载媒体 |
| `--debug` | 打印 `flight_hit` / `api_hit` 诊断，链路异常时先用它 |

输出目录必须是新目录，已有内容会报 `OUTPUT_NOT_EMPTY`，脚本不会覆盖你已有的文件。

## 数据通道

| 通道 | 说明 |
|---|---|
| 纯 HTTP | 短链跳转解析；少数页面 HTML 里仍带作品 JSON |
| `headless:flight` | 图文页把作品对象放在服务端渲染数据里，拼接 `__pace_f` 片段后按 aweme_id 精确匹配 |
| `headless:api` | 视频页由页面自己去请求 `/aweme/v1/web/aweme/detail/`，截这个响应取 `aweme_detail` |

作品 ID 一定要精确匹配：页面上还有推荐流的其他作品，不匹配就会拿错人的数据。

## 已知限制

- 抽帧是均匀概览，没被抽到的秒数不等于“视频里没有”；回答只能说“抽到的 N 个时间点里看到…”。
- 站点结构一变，flight / 接口通道可能失效：先 `--debug` 看命中情况，再用 `--aweme-id --kind ... --item-only` 单独验证数据层。
- 作品已删除、私密或地区受限时报 `ITEM_DATA_UNAVAILABLE`。
- 只读单个作品，不抓评论列表、不抓关注关系、不做批量刷取。
- 互动数随抓取时刻变化，引用时要注明抓取时间。
- 转写是 25 秒分块的结果，时间戳是块区间而非强制对齐，块边缘可能断句。

## 历史

`douyin-video-reader` 和 `audio-listener-local` 是在豆包工作里“识别不了抖音链接、听不了音频”的实际问题上开发出来的第一批本地理解 skill，先在 Windows 电脑上跑通图文与视频两种作品，再整理入库。
