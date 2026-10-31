# doubao-work-skills

适配 **豆包工作**（豆包办公）的 Agent skill 合集。这里收录的 skill 都在豆包工作里实际跑过，并按豆包工作的运行环境写好了调用方式：

- 豆包工作在你的 Windows 电脑上执行命令时，用的是它自带的 **PowerShell 7**，不是 bash，也不是 Windows 自带的 PowerShell 5.1。
- 本合集的脚本用 PowerShell 7、Node.js 或只用标准库的 Python 3 编写：Windows 电脑上这三样豆包工作都自带；云主机上自带 Node.js 和 Python 3，没有 PowerShell。不需要另外安装 git 或其他软件。
- 需要操作本机软件（比如 AdsPower）的 skill，要在豆包工作连接的**你的电脑**上运行，云主机上用不了。

## Skill 列表

| Skill | 用途 | 运行环境 | 使用说明 |
|---|---|---|---|
| [adspower-browser](skills/adspower-browser) | 通过 AdsPower 的 Local API 管理指纹浏览器：打开、关闭、新建、修改、删除、查询环境，以及分组、标签、代理、团队成员、内核下载 | Windows 电脑（需要本机运行 AdsPower） | [docs/adspower-browser.md](docs/adspower-browser.md) |
| [douyin-auto-operator](skills/douyin-auto-operator) | 抖音账号自动运营：读取创作者中心真实数据复盘、制作「横屏氛围图 + 长文案 + 5 个话题 + 热门榜 BGM」图文、定时备稿和发布；运营方向、主题、风格、发布时间都可在配置文件里定制 | 电脑或云主机（需要能登录抖音创作者中心） | [docs/douyin-auto-operator.md](docs/douyin-auto-operator.md) |

## 下载

- **整个合集（ZIP）**：[点击下载](https://codeload.github.com/yang2979326292-hub/doubao-work-skills/zip/refs/heads/main)，解压后在 `skills` 文件夹里取需要的 skill。
- 单独查看某个 skill 的文件：点上面表格里的 skill 名。

## 安装到豆包工作

### 方法一：让豆包工作帮你装（推荐）

在豆包工作里直接说（把 skill 名换成你要装的那个）：

> 帮我把 https://github.com/yang2979326292-hub/doubao-work-skills 里的 douyin-auto-operator 安装到我的豆包工作用户 skill 目录

豆包工作会把 skill 下载到它的用户 skill 目录，下一轮对话就能用了。

### 方法二：手动安装

1. 点上面的 [下载合集 ZIP](https://codeload.github.com/yang2979326292-hub/doubao-work-skills/zip/refs/heads/main)（或在本页点 **Code → Download ZIP**），下载后解压。
2. 把 `skills` 文件夹里你要用的 skill 文件夹（比如 `douyin-auto-operator`）整个复制到豆包工作的用户 skill 目录：

   ```
   %LOCALAPPDATA%\DoubaoWork\User Data\Default\.doubaowork\agent_mode\workspace\.user_skills\
   ```

   放在这里的 skill 会在下一轮对话生效，也会同步到豆包工作的云主机。
3. 在豆包工作里提到这个 skill 的用途（比如“帮我运营抖音账号”），确认它被调用。

### 方法三：用 skills CLI 安装（同时装给其他 Agent）

```bash
npx skills add https://github.com/yang2979326292-hub/doubao-work-skills --skill douyin-auto-operator -g -y --copy
```

- skills CLI 从 GitHub 下载时要用到 **git**。电脑上没装 git 会报 `spawn git ENOENT`。
- 它会把 skill 复制到 `~/.agents/skills` 和很多其他 Agent 的目录，但不会放进上面的豆包工作用户 skill 目录。只给豆包工作用的话，请用方法一或方法二。

## 目录结构

```
skills/<skill名>/      每个 skill 一个文件夹，Agent 只读取这里面的内容
  SKILL.md             名称、触发说明和执行步骤
  scripts/             可执行脚本
  references/          需要时才读的参考资料
  assets/              模板、配置等素材
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
