# codex-hermes

语言: 简体中文 | [English](README.md) | [日本語](README.ja.md)

这是一个实验性的 Codex plugin，用于把 Codex App 中的任务转交给本地
Hermes CLI，然后由 Codex 审查 Hermes 返回的结果，再继续处理。

目标很简单：把这个仓库安装为 Codex plugin，然后从任意 Codex workspace
运行 Hermes 任务，并看到 Hermes 返回的回复。

## 最新版本

- [v0.1.2 - Public metadata cleanup for installable-first distribution](https://github.com/na-navi/Codex-hermes/releases/tag/v0.1.2)
- [v0.1.1 - Initial verified Codex App <-> Hermes CLI bridge](https://github.com/na-navi/Codex-hermes/releases/tag/v0.1.1)
- 目前还没有附带二进制文件或 bundle。请直接使用仓库源码。

## 前置条件

- Codex App
- 已安装并可通过 `PATH` 调用的 `hermes` CLI
- 已 clone 到本地的本仓库

## 安装

1. 先在终端中确认 Hermes 可以正常运行。

```text
hermes --help
```

如果这个命令失败，请先修复 Hermes。没有可用的 Hermes CLI 时，这个 plugin
无法与 Hermes 通信。

2. 将 plugin 安装到 Codex plugin 目录。

```powershell
$pluginRoot = "$env:USERPROFILE\.codex\plugins\codex-hermes"
New-Item -ItemType Directory -Force -Path $pluginRoot | Out-Null
Copy-Item -Recurse -Force .codex-plugin, skills, commands, scripts, README.md, LICENSE $pluginRoot
```

3. 重启 Codex App，或打开一个新 thread，以刷新 plugin skill 列表。

4. 在本仓库中运行 validator。

```text
python scripts/validate-plugin.py
```

5. 如果要在本仓库中开发，可以选择启用本地 Git hook。

```text
git config core.hooksPath .githooks
```

## 开发模式

当本仓库是当前 Codex workspace 时，Codex 也可以发现
`.agents/skills/hermes/SKILL.md` 中的 repo-local skill。这对开发 plugin
很有用，但不足以支持在其他文件夹中使用。

如果要从其他 workspace 使用，请把它安装为 plugin，让 Codex 能够加载：

```text
%USERPROFILE%\.codex\plugins\codex-hermes\skills\hermes\SKILL.md
```

## 测试 Hermes 连接

1. 在任意 workspace 中，通过 Codex 调用 Hermes skill 执行一个短任务。

```text
$hermes say hello
```

2. 等待运行完成。
3. 确认输出中包含以下内容。

- `MODEL=...`
- `SESSION_ID=...`
- `RESPONSE_BEGIN`
- `RESPONSE_BEGIN` 后面的 Hermes 回复

如果看到 `Hermes CLI was not found on PATH`，说明 CLI 没有安装，或者当前 shell
无法找到它。

如果没有看到 `SESSION_ID`，说明 Hermes 没有返回 session marker。不过返回的回复
本身仍然可能是有效的。

## 重要文件

- [`.codex-plugin/plugin.json`](.codex-plugin/plugin.json)
- [`skills/hermes/SKILL.md`](skills/hermes/SKILL.md)
- [`.agents/skills/hermes/SKILL.md`](.agents/skills/hermes/SKILL.md)
- [`scripts/invoke-hermes.py`](scripts/invoke-hermes.py)
- [`scripts/validate-plugin.py`](scripts/validate-plugin.py)
