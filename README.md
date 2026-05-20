# cormes

[日本語](README.md) / [English](README.en.md) / [简体中文](README.zh-CN.md)

![Cormes workflow hero](./assets/codex-hermes-hero.webp)

Codex App のタスクをローカルの Hermes CLI に渡し、返ってきた回答を
Codex がレビューしてから処理を続けるための実験的な Codex plugin です。

Cormes は Codex 側の wrapper です。外部の `hermes` CLI に委譲し、Hermes の回答を
untrusted data として扱って Codex がレビューします。

## デモ

![Cormes review loop demo](./assets/demo-review-loop.webp)

このデモは、plain `hermes` と Cormes の違いを示します。plain Hermes は
モデル回答を直接返します。一方で Cormes は、その回答を untrusted data として
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
$pluginRoot = "$env:USERPROFILE\.codex\plugins\cormes"
Remove-Item -Recurse -Force $pluginRoot -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $pluginRoot | Out-Null
Copy-Item -Recurse -Force .codex-plugin, skills, commands, scripts, assets, README.md, README.en.md, README.zh-CN.md, LICENSE $pluginRoot
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
`.agents/skills/cormes/SKILL.md` の repo-local skill も検出できます。
これは plugin 開発中には便利ですが、別フォルダから使うには不十分です。

別 workspace から使う場合は、Codex が次の skill を読めるように plugin として
インストールしてください。

```text
%USERPROFILE%\.codex\plugins\cormes\skills\cormes\SKILL.md
```

## Hermes 連携のテスト

1. 任意の workspace から、Codex で短いタスクを Cormes skill に渡します。

```text
$cormes say hello
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

## Doctor

`--doctor` は、ローカルの Codex / Cormes 環境について読み取り専用の JSON health snapshot を出します。
Hermes は実行せず、model cache も書き込まず、config / auth / session の中身や `.codex` 配下の再帰スキャンも行いません。

```text
python scripts/invoke-cormes.py --doctor
```

report に `fail` item が含まれていても、report を出せた場合の process exit code は `0` です。非 0 は invalid arguments や doctor 自体が安全に完走できなかった場合だけに使います。

## モデル指定

通常は Hermes の `config.yaml` にある `model.default` / `model.provider` を使います。明示的に変えたい場合は、task の先頭で指定できます。

```text
$cormes -m glm-5.1 -p zai say hello
```

優先順位は、明示指定、Cormes の model cache、Hermes `config.yaml`、`glm-5-turbo` fallback の順です。

## 互換性

`$cormes` が主要な Codex skill invocation です。legacy `$hermes` は別 skill alias としては残しません。残すと wrapper と依存先の名前衝突が続くためです。

外部 CLI binary は引き続き `hermes` です。legacy env var の `CODEX_HERMES_STATE_DIR` と `CODEX_HERMES_REPO_ROOT` は、rename 期間の fallback alias として引き続き受け付けます。

## 重要なファイル

- [`.codex-plugin/plugin.json`](.codex-plugin/plugin.json)
- [`skills/cormes/SKILL.md`](skills/cormes/SKILL.md)
- [`.agents/skills/cormes/SKILL.md`](.agents/skills/cormes/SKILL.md)
- [`scripts/invoke-cormes.py`](scripts/invoke-cormes.py)
- [`scripts/validate-plugin.py`](scripts/validate-plugin.py)
