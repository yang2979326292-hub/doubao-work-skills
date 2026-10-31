# doubao-work-skills

适配 **豆包工作**（豆包办公）的 Agent skill 合集。这里收录的 skill 都在豆包工作里实际跑过，并按豆包工作的运行环境写好了调用方式：

- 豆包工作在你的 Windows 电脑上执行命令时，用的是它自带的 **PowerShell 7**，不是 bash，也不是 Windows 自带的 PowerShell 5.1。
- 本合集的脚本只用 PowerShell 7 或 Node.js（豆包工作自带 Node 22），不依赖 git、Python 或其他需要另外安装的软件。
- 需要操作本机软件（比如 AdsPower）的 skill，要在豆包工作连接的**你的电脑**上运行，云主机上用不了。

## Skill 列表

| Skill | 用途 | 运行环境 | 使用说明 |
|---|---|---|---|
| [adspower-browser](skills/adspower-browser) | 通过 AdsPower 的 Local API 管理指纹浏览器：打开、关闭、新建、修改、删除、查询环境，以及分组、标签、代理、团队成员、内核下载 | Windows 电脑（需要本机运行 AdsPower） | [docs/adspower-browser.md](docs/adspower-browser.md) |

## 安装到豆包工作

> 只想下载文件的话，直接点：[下载整个合集 ZIP](https://codeload.github.com/yang2979326292-hub/doubao-work-skills/zip/refs/heads/main)，解压后在 `skills` 文件夹里取需要的 skill。下面是三种安装方式。

### 方法一：让豆包工作帮你装（推荐）

在豆包工作里直接说：

> 帮我把 https://github.com/yang2979326292-hub/doubao-work-skills 里的 adspower-browser 安装到我的豆包工作用户 skill 目录

豆包工作会把 skill 下载到它的用户 skill 目录，下一轮对话就能用了。

### 方法二：手动安装

1. 点上面的 [下载合集 ZIP](https://codeload.github.com/yang2979326292-hub/doubao-work-skills/zip/refs/heads/main)（或在本页点 **Code → Download ZIP**），下载后解压。
2. 把 `skills` 文件夹里你要用的 skill 文件夹（比如 `adspower-browser`）整个复制到豆包工作的用户 skill 目录：

   ```
   %LOCALAPPDATA%\DoubaoWork\User Data\Default\.doubaowork\agent_mode\workspace\.user_skills\
   ```

   放在这里的 skill 会在下一轮对话生效，也会同步到豆包工作的云主机。
3. 在豆包工作里提到这个 skill 的用途（比如“列出我的 AdsPower 环境”），确认它被调用。

### 方法三：用 skills CLI 安装（同时装给其他 Agent）

```bash
npx skills add https://github.com/yang2979326292-hub/doubao-work-skills --skill adspower-browser -g -y --copy
```

- skills CLI 从 GitHub 下载时要用到 **git**。电脑上没装 git 会报 `spawn git ENOENT`。
- 它会把 skill 复制到 `~/.agents/skills` 和很多其他 Agent 的目录，但不会放进上面的豆包工作用户 skill 目录。只给豆包工作用的话，请用方法一或方法二。

## 目录结构

```
skills/<skill名>/      每个 skill 一个文件夹，Agent 只读取这里面的内容
  SKILL.md             名称、触发说明和执行步骤
  scripts/             可执行脚本
  references/          需要时才读的参考资料
docs/<skill名>.md      给人看的使用说明（不会被 Agent 加载）
tools/validate-skills.mjs   提交前的检查脚本
```

## 新增 skill

要求和步骤见 [CONTRIBUTING.md](CONTRIBUTING.md)。提交前运行下面的检查（需要 Node.js；豆包工作自带 Node 22，可以直接让它帮你运行）：

```bash
node tools/validate-skills.mjs
```

## 许可证

本仓库为 MIT 许可证，见 [LICENSE](LICENSE)。改写自其他开源项目的 skill，会在各自文件夹里保留原作者的许可证（例如 `skills/adspower-browser/LICENSE.txt`）。
