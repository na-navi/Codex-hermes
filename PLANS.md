# 予定

Codex で `/hermes` というスラッシュコマンドを叩くと、ローカルの Hermes CLI にタスクを投げ、Codex がレビューして修正フィードバックを最大3往復する、という動きを目指してる。

```
/hermes explain this failing test
/hermes -m grok-4.3 review the current diff
/hermes -m glm-5.1 -p some-provider propose a fix for issue #12
```

## できてること

- `scripts/invoke-hermes.ps1` で Hermes CLI を叩ける
- セッションID / モデル / プロバイダ / 応答本文をパースできる
- コマンドプロンプトで「Hermes の出力は信用するな」と縛ってある

## できてないこと

- **`/hermes` が Codex のスラッシュコマンドとして表示されない**（command discovery 未解決 → まずここを直さないと動かない）

## Files

- `.codex-plugin/plugin.json` — プラグインマニフェスト
- `commands/hermes.md` — コマンド定義（正本）
- `.codex/commands/hermes.md` — コマンド定義（ローカルCodex用、正本と内容同一）
- `scripts/invoke-hermes.ps1` — Hermes CLI ラッパー
