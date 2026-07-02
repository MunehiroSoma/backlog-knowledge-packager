---
mode: agent
description: main を最新に同期し、現在のブランチをリベースする
---

# sync-main — main 同期 & リベース

main を最新に同期し、現在の作業ブランチをリベースする。

## 手順

1. 現在のブランチを確認する

   ```bash
   git branch --show-current
   ```

1. main を最新に更新する

   ```bash
   git fetch origin
   git checkout main && git pull origin main
   ```

1. 元のブランチに戻ってリベースする

   ```bash
   git checkout <元のブランチ>
   git rebase main
   ```

1. コンフリクトがあれば内容を確認してユーザーに報告する

## 注意

- リベース後に push が必要な場合は `git push --force-with-lease` を使う
- コンフリクトが複雑な場合はユーザーに確認してから進める
