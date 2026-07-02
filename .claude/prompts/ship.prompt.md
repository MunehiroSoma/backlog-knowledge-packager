---
mode: agent
description: 現在のブランチの変更をコミット → push → PR 作成まで一括で行う
---

# ship — コミット・push・PR

現在のブランチの変更をコミット → push → PR 作成まで一括で行う。

> **GitHub Flow** 準拠。`main` へ直接 push せず、必ず PR 経由でマージする。
> 詳細: [`docs/standards/git運用フロー.md`](../../docs/standards/git%E9%81%8B%E7%94%A8%E3%83%95%E3%83%AD%E3%83%BC.md)

## 手順

1. 変更を確認する

   ```bash
   git status --short && git diff --stat
   ```

1. Lint・フォーマット・型チェックを通す

   ```bash
   # Backend
   cd backend && pre-commit run --all-files
   # Frontend
   cd frontend && npm run lint && npm run format:check
   ```

1. ステージングとコミット

   ```bash
   git add <関連ファイル>
   git commit -m "<type>: <概要（日本語）>"
   ```

1. push する

   ```bash
   git push origin <current-branch>
   ```

1. PR を作成する

   ```bash
   gh pr create \
     --title "<type>: <概要>" \
     --body "## 概要
   <変更内容>

   ## 関連 Issue
   Closes #<番号>

   ## 確認事項
   - [ ] 正常系確認
   - [ ] 異常系確認
   - [ ] Lint・型チェック通過"
   ```

## コミットメッセージ規則

| type       | 用途                             |
| ---------- | -------------------------------- |
| `feat`     | 新機能                           |
| `fix`      | バグ修正                         |
| `docs`     | ドキュメント                     |
| `refactor` | リファクタリング                 |
| `chore`    | 設定・依存関係更新               |
| `test`     | テスト追加・修正                 |
| `style`    | フォーマット修正（動作変更なし） |
