---
mode: agent
description: 新しいブランチを main から切って開発を開始する
---

# new-feature — ブランチ作成

新しいブランチを main から切って開発を開始する。

## 使い方

```
@new-feature feature/user-authentication
@new-feature fix/login-redirect-error
```

## 手順

1. main を最新に更新する

   ```bash
   git checkout main && git pull origin main
   ```

1. ブランチを作成する

   ```bash
   git checkout -b <prefix>/<ブランチ名>
   ```

## ブランチ命名規則

| プレフィックス | 用途                   | 例                               |
| -------------- | ---------------------- | -------------------------------- |
| `feature/`     | 新機能                 | `feature/user-authentication`    |
| `fix/`         | バグ修正               | `fix/login-redirect-error`       |
| `hotfix/`      | 緊急の本番修正         | `hotfix/token-null-pointer`      |
| `chore/`       | 設定・ビルド・依存関係 | `chore/update-deps`              |
| `refactor/`    | リファクタリング       | `refactor/extract-service-layer` |

すべて kebab-case（英小文字・ハイフン区切り）。日本語・スペース・アンダースコア禁止。
