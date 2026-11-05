# audio-listener-local 使用说明

## 能做什么

在**本地 CPU** 上把音频听成可核对的结果，素材不上传：

- 分段人声转写（`sherpa-onnx SenseVoice`，中 / 英 / 日 / 韩 / 粤，带时间戳）
- 声音事件标签候选（`zipformer audio tagging`）：是否有说话、音乐、歌唱、掌声、脚步、引擎声等
- 声学测量：时长、RMS / 峰值 dBFS、近静音占比、节奏估计
- 产出 `音频识别结果.md`（人读汇总）、`transcript.txt`（纯文本）、`analysis.json`（结构化全量）

不止能听纯音频：视频文件里的音轨也能直接听，不用先手动抽音频。

## 使用前准备

1. Python 3（豆包工作在 Windows 电脑和云主机上都自带；纯 CPU 推理，无 GPU 要求）。
2. 第一次使用前装依赖与模型（都只装进 skill 自己的 `.runtime`）：

   ```powershell
   python "<skill_dir>\scripts\setup.py" --dependencies
   python "<skill_dir>\scripts\setup.py" --models
   ```

   模型默认从 `hf-mirror.com` 拉，失败回退 `huggingface.co`。
3. 自检：

   ```powershell
   python "<skill_dir>\scripts\listen.py" --doctor
   ```

   `ready: true` 才能用。

## 在豆包工作里怎么说

- “听一下这段录音说了什么，转成文字”
- “这个视频里有没有人说话？背景音乐是什么类型？”
- “音频多长、多响？有没有大段静音？”

豆包工作会跑脚本，先读 `analysis.json` / `音频识别结果.md`，再作答；不会凭标题猜内容。

## 手动调用脚本

```powershell
python "<skill_dir>\scripts\listen.py" --input "<音频或视频文件>" --output "<新目录>" --mode both --language auto
```

| 参数 | 作用 |
|---|---|
| `--mode both\|speech\|sounds` | `both`（默认）转写 + 声音标签；`speech` 只转写；`sounds` 只做声音标签 |
| `--language auto\|zh\|en\|ja\|ko\|yue` | 已知语种时显式指定更稳 |
| `--max-seconds` | 默认 1800，超长要么调大要么先切片，不会静默截断 |

输出目录必须是新目录（`OUTPUT_NOT_EMPTY`），单文件上限 1 GiB，统一重采样成 16 kHz 单声道。

## 怎么读结果（重要）

- 转写片段是**模型转写**，要和“内容事实”分开说；引用时带 `start/end` 时间戳。
- 声音标签是**候选分类**，分数不是校准概率：写“标签显示接近 Music”，而不是“这一定是某首歌”。
- `speech_chunks=0` 且标签集中在 Music / Singing 时，结论是“以音乐为主、未检出可靠人声”——这是有效结论，不是失败。
- `analysis.json` 的 `singing_hint` 非空表示检测到演唱类标签：可以说“含歌唱人声”，但**歌词转写不可靠**，不能当准确歌词引用。
- 涉及逐字准确性时用 `--mode speech` 复跑核对；`both` 模式会过滤低人声分数片段。
- `tempo_bpm_estimate` 来自能量包络周期，有半速/倍速歧义，不是拍点真值。

## 已知限制

- 不做说话人身份识别、不做曲名检索、不做情绪/健康/心理推断。
- 分块按 25 秒切，块边缘可能断句；逐字时间戳若存在为模型估计。
- 极短或强噪声素材可能得到空转写，需结合声音标签判断。
- 首次跑模型要下载约十几 MB 的权重，网络差时容易卡在下载；安装脚本会打印每个文件的字节数与 sha256 前 16 位，便于核对。

## 历史

为解决“豆包工作听不了音频”而写的第一版：先做本地转写，再补声音标签与声学测量，最后与 `douyin-video-reader` 打通——抖音作品的音轨直接交给它转写。
