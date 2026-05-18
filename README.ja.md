# codex-hermes

言語: 日本語 | [English](README.md) | [简体中文](README.zh-CN.md)

![Codex Hermes workflow hero](./assets/codex-hermes-hero.webp)

Codex App のタスクをローカルの Hermes CLI に渡し、返ってきた回答を
Codex がレビューしてから処理を続けるための実験的な Codex plugin です。

目的はシンプルです。このリポジトリを Codex plugin としてインストールし、
任意の Codex workspace から Hermes タスクを実行して、Hermes の返答を受け取れる
状態にします。

## デモ

![Codex Hermes review loop demo](./assets/demo-review-loop.webp)

このデモは、plain `hermes` と Codex Hermes の違いを示します。plain Hermes は
モデル回答を直接返します。一方で Codex Hermes は、その回答を untrusted data として
扱い、ローカルリポジトリと照合してからレビュー済みの最終回答を返します。

## 最新リリース

- [v0.1.2 - Public metadata cleanup for installable-first distribution](https://github.com/na-navi/Codex-hermes/releases/tag/v0.1.2)
- [v0.1.1 - Initial verified Codex App <-> Hermes CLI bridge](https://github.com/na-navi/Codex-hermes/releases/tag/v0.1.1)
- まだバイナリや bundle は添付していません。リポジトリのソースを直接使ってください。

## 必要なもの

- Codex App
- `PATH` から実行できる `hermes` CLI
- ローカルに clone したこのリポジトリ

## インストール

1. 先にターミナルで Hermes が動くことを確認します。

```text
hermes --help
```

このコマンドが失敗する場合は、先に Hermes 側を直してください。この plugin は
Hermes CLI が使えない環境では Hermes と通信できません。

2. Codex plugin ディレクトリに plugin をインストールします。

```powershell
$pluginRoot = "$env:USERPROFILE\.codex\plugins\codex-hermes"
Remove-Item -Recurse -Force $pluginRoot -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $pluginRoot | Out-Null
Copy-Item -Recurse -Force .codex-plugin, skills, commands, scripts, assets, README.md, README.ja.md, README.zh-CN.md, LICENSE $pluginRoot
```

3. Codex App を再起動するか、新しい thread を開いて、plugin skill 一覧を更新します。

4. このリポジトリから validator を実行します。

```text
python scripts/validate-plugin.py
```

5. このリポジトリで開発する場合は、任意で Git hook を有効にします。

```text
git config core.hooksPath .githooks
```

## 開発モード

このリポジトリを Codex workspace として開いている場合、Codex は
`.agents/skills/hermes/SKILL.md` の repo-local skill も検出できます。
これは plugin 開発中には便利ですが、別フォルダから使うには不十分です。

別 workspace から使う場合は、Codex が次の skill を読めるように plugin として
インストールしてください。

```text
%USERPROFILE%\.codex\plugins\codex-hermes\skills\hermes\SKILL.md
```

## Hermes 連携のテスト

1. 任意の workspace から、Codex で短いタスクを Hermes skill に渡します。

```text
$hermes say hello
```

2. 実行が終わるまで待ちます。
3. 出力に次の内容が含まれることを確認します。

- `MODEL=...`
- `SESSION_ID=...`
- `RESPONSE_BEGIN`
- `RESPONSE_BEGIN` の後に Hermes の返答

`Hermes CLI was not found on PATH` が出る場合は、CLI がインストールされていないか、
現在の shell から見えていません。

`SESSION_ID` が出ない場合、Hermes が session marker を返していません。ただし、
返答自体は有効な場合があります。

## 重要なファイル

- [`.codex-plugin/plugin.json`](.codex-plugin/plugin.json)
- [`skills/hermes/SKILL.md`](skills/hermes/SKILL.md)
- [`.agents/skills/hermes/SKILL.md`](.agents/skills/hermes/SKILL.md)
- [`scripts/invoke-hermes.py`](scripts/invoke-hermes.py)
- [`scripts/validate-plugin.py`](scripts/validate-plugin.py)
