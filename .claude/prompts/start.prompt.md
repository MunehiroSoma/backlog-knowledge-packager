---
mode: agent
description: 作業開始時に GitHub Issues を確認し、ブランチ作成まで一括実行する
---

# start — 作業開始

新しい作業を始める前に GitHub Issues を確認し、取り掛かる Issue を選んでブランチを切る。

## 手順

0. 事前チェック

   ```bash
   gh auth status
   ```

1. Open な Issue 一覧を取得する

   ```bash
   gh issue list --repo MunehiroSoma/pc-lending-manager --state open
   ```

1. ラベル・マイルストーンを確認して作業候補を提示し、ユーザーに選んでもらう

1. 選ばれた Issue の詳細を確認する

   ```bash
   gh issue view <番号> --repo MunehiroSoma/pc-lending-manager
   ```

1. Issue 種別に応じたブランチを切る

   ```bash
   git checkout main && git pull origin main
   git checkout -b <prefix>/<issue-slug>
   ```

1. 作業開始コメントを Issue に残す（任意）

   ```bash
   gh issue comment <番号> --body "作業開始します。ブランチ: <ブランチ名>"
   ```

## ブランチ命名規則

| プレフィックス | 用途             |
| -------------- | ---------------- |
| `feature/`     | 新機能           |
| `fix/`         | バグ修正         |
| `hotfix/`      | 緊急の本番修正   |
| `chore/`       | 設定・依存関係   |
| `refactor/`    | リファクタリング |

すべて kebab-case（英小文字・ハイフン区切り）。
