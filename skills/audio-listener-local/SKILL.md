---
name: audio-listener-local
description: 当用户上传音频、录音、视频，或要求「听一下这段说了什么」「转写成文字」「总结语音内容」「判断里面是什么声音」「有没有人说话」「背景音乐是什么类型」「音频多长、多响」时使用：在本地 CPU 上转写人声、识别音乐/音效/环境声标签候选、测量响度与节奏，素材不上传。豆包无法直接听音频时，用本 Skill 的脚本产出可核对证据再作答。
---

# 本地音频理解（listen.py）

不上传素材，纯本地 CPU 推理：`sherpa-onnx SenseVoice`（中英日韩粤转写）+ `zipformer audio tagging`（声音事件标签）+ 声学测量。

## 何时用本 Skill

- 要转写音频/录音/视频里的说话内容，或做分段带时间戳的文字稿。
- 要判断音频里是否有说话、是否有音乐、音乐风格趋向、是否有掌声/脚步/发动机等环境声。
- 要音频时长、响度、静音比例、节奏周期这类可测量指标。
- 上游 Skill（例如 `douyin-video-reader`）已产出 `audio.wav`，需要转写与声音判断。

不适用：音色克隆、说话人身份识别、曲名检索、专业混音分析、语音情绪诊断、健康或心理推断。

## 执行流程

1. 自检运行时（首次或新机器）：

```powershell
python "<skill_dir>\scripts\listen.py" --doctor
```

`ready: true` 才继续。缺依赖或缺模型时按提示补装（只装到 Skill 内的 `.runtime`，不污染全局）：

```powershell
python "<skill_dir>\scripts\setup.py" --dependencies
python "<skill_dir>\scripts\setup.py" --models
```

模型默认从 `hf-mirror.com` 拉取，失败回退 `huggingface.co`；GitHub 在部分网络不可达，不要走 GitHub release。

2. 分析（输出目录必须是新目录，脚本不会覆盖已有文件）：

```powershell
python "<skill_dir>\scripts\listen.py" --input "<音频或视频文件>" --output "<新目录>" --mode both --language auto
```

- `--mode both`（默认）转写 + 声音标签；`speech` 只转写（怀疑被过滤漏词时复跑）；`sounds` 只做声音标签。
- `--language auto|zh|en|ja|ko|yue`，已知语种时显式指定更稳。
- `--max-seconds` 默认 1800，超长要么调大要么先切片；不会静默截断。

3. 读结果（必须实际读文件，不要凭脚本 stdout 猜内容）：

| 文件 | 内容 |
| --- | --- |
| `音频识别结果.md` | 人类可读汇总：转写、标签候选、声学测量、边界 |
| `transcript.txt` | 纯转写文本 |
| `analysis.json` | 结构化全量：`speech[]`、`sound_windows[]`、`acoustic`、`metadata` |

## 作答规则

- 转写要带时间戳引用（`analysis.json` 的 `speech[].start/end`），并把「模型转写」与「内容事实」分开表述。
- 声音标签是候选分类，分数不是校准概率；写「标签显示接近 Music」而不是「这一定是某首歌」。
- `speech_chunks=0` 且标签集中在 Music/Singing 时，结论应为「以音乐为主、未检出可靠人声」，不能说「没有声音」。
- `analysis.json` 的 `singing_hint` 非空表示检测到演唱类标签：可以说明「音频含歌唱人声」，但歌词转写不可靠，不得当作准确歌词引用。
- `both` 模式会过滤低人声分数片段；回答涉及逐字准确性时用 `--mode speech` 复跑核对。
- 节奏 `tempo_bpm_estimate` 来自能量包络周期，存在半速/倍速歧义，不得当拍点真值。
- 分块按 25 秒切分，时间戳是块区间而非强制对齐；块边缘可能断句。
- 不做说话人身份、健康、心理、情绪的推断；不做曲名检索。

## 限制与常见报错

| 报错 | 含义与处理 |
| --- | --- |
| `MODEL_MISSING` | 模型未下载，跑 `setup.py --models` |
| `OUTPUT_NOT_EMPTY` | 输出目录已有文件，换新目录 |
| `NO_AUDIO_STREAM` | 输入没有音轨（如无声视频），需换素材 |
| `DURATION_LIMIT` | 超过 `--max-seconds`，调大或切片 |
| `INPUT_TOO_LARGE` | 单文件超过 1 GiB |
| `EMPTY_AUDIO` / `NON_FINITE_AUDIO` | 音频为空或含非法采样，素材损坏 |

单文件上限 1 GiB；采样统一重采样为 16 kHz 单声道 float32。
