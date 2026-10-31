# 新增 skill 的要求

本合集只收录适配豆包工作的 skill。新增或修改 skill 时，请满足下面的要求，并在提交前运行 `node tools/validate-skills.mjs`，结果必须是“通过”。

## 1. 目录与命名

- 每个 skill 一个文件夹：`skills/<skill名>/`。
- skill 名只用小写字母、数字和连字符（例如 `adspower-browser`），不超过 64 个字符，并且和 SKILL.md 里的 `name` 一致。
- skill 文件夹里只放 Agent 需要的东西：`SKILL.md`、`scripts/`、`references/`、`assets/`、许可证。**不要**放 README、CHANGELOG 之类给人看的说明，这些写到 `docs/<skill名>.md`。

## 2. SKILL.md

- 文件开头是 YAML frontmatter，只写 `name` 和 `description`（另外允许 `license`、`allowed-tools`、`metadata`）。每个字段写在一行里，不用 `>` 或 `|` 多行写法。
- **description 的前 100 个字符要说清“做什么、什么时候用”。** 豆包工作的 skill 列表只显示 description 的前 100 个字符，Agent 靠这一段决定要不要读这个 skill。
- description 不超过 1024 个字符，不能包含 `<` 或 `>`。
- 正文写给 Agent 看：用祈使句写调用方式、执行规则和常见错误的处理方法。超过 500 行时，把细节移到 `references/`，并在正文里写明什么情况下去读哪个文件。
- 正文里提到的 `scripts/...`、`references/...`、`assets/...` 文件必须存在。

## 3. 适配豆包工作的运行环境

- **命令执行方式**：豆包工作在 Windows 电脑上用它自带的 PowerShell 7 执行命令，bash 不可用；在云主机上用 Linux bash。
  - 脚本优先用 PowerShell 7（`.ps1`，第一行写 `#Requires -Version 7.0`）或 Node.js（`.mjs`，只用 Node 自带模块）。
  - 不要依赖 git、Python 或需要另外安装的软件。确实需要的话，在 SKILL.md 的“前置条件”里写清楚，并说明缺失时 Agent 应该怎么处理。
- **路径**：不写任何个人电脑上的绝对路径（例如 `C:\Users\某某\...`）。在 SKILL.md 里写“脚本在本 SKILL.md 同目录下的 `scripts/xxx`”，由 Agent 拼出实际路径。
- **执行环境**：需要操作本机软件、文件或本机端口（`127.0.0.1`）的 skill，要在 SKILL.md 里写明“必须在用户电脑上执行；当前是云主机时先切换到用户电脑”。
- **编码与换行**：所有文本文件用无 BOM 的 UTF-8、LF 换行（`.gitattributes` 已经设置好）。脚本读写中文时显式指定 UTF-8。

## 4. 安全

- 不要把 API Key、Token、密码、Cookie 写进任何文件。需要密钥时从环境变量读取，并在 SKILL.md 里写明变量名和设置方法。
- 不要在示例里用真实的账号、环境 ID、手机号或邮箱，用 `abcd1234`、`user@example.com` 这类示例值。
- 删除、分享、重置密码之类不可逆的操作，要在 SKILL.md 里规定“先列出影响范围，请用户确认后再执行”。脚本最好提供只预览不执行的参数（例如 `-DryRun`）。

## 5. 来源与许可证

- 改写自其他项目的 skill，要在 SKILL.md 开头注明来源，并把原项目的许可证放进 skill 文件夹（例如 `LICENSE.txt`）。
- 不收录许可证不允许改写或再分发的内容。

## 6. 提交前检查

1. 运行 `node tools/validate-skills.mjs`，确认结果是“通过”。警告也要看一遍，能改的尽量改。
2. 在豆包工作里实际用一次：新开对话，用自然语言提出需求，确认 skill 被正确触发、命令能执行成功。
3. 在 README.md 的“Skill 列表”里加一行，格式：`| [skill名](skills/skill名) | 用途 | 运行环境 | [docs/skill名.md](docs/skill名.md) |`。
4. 在 `docs/` 下写一份给人看的使用说明。
