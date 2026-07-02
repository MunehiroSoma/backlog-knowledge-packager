---
mode: agent
description: PR番号またはdiffを受け取り、設計書・コーディング規約・テスト仕様に照らしてレビューする
---

# review — コードレビュー

PR 番号（または差分）を受け取り、設計書・コーディング規約・チェックリストに基づいてレビューする。

> 規約: [`docs/standards/`](../../docs/standards/) ／ チェックリスト: [`ai/review/code_review_checklist.md`](../../ai/review/code_review_checklist.md)

## 入力

- **PR 番号** を指定した場合: `gh pr view <番号>` / `gh pr diff <番号>` で変更内容を取得してレビューする
- **diff を貼り付けた場合**: そのまま下記の観点でレビューする

## 変更種別に応じた設計書との照合

変更内容に応じて、以下の設計書を参照・照合する。関係しない設計書の参照は不要。

| 変更種別             | 参照する設計書                    |
| -------------------- | --------------------------------- |
| API 追加 / 変更      | `docs/design/API設計.md`          |
| ビジネスロジック変更 | `docs/design/機能設計書.md`       |
| DB スキーマ変更      | `docs/design/DB設計.md`           |
| 要件対応確認         | `docs/requirements/要件一覧表.md` |
| テスト追加 / 変更    | `docs/test/テスト計画.md`         |

## レビュー観点

### 1. 設計整合性

- [ ] エンドポイント・HTTPメソッド・レスポンス形式が `docs/design/API設計.md` と一致するか
- [ ] ステータス遷移・業務ルール・エラーコード（400/401/404/409/422）が `docs/design/機能設計書.md` と一致するか
- [ ] DB の制約・カラム定義が `docs/design/DB設計.md` と一致するか
- [ ] 要件ID（FR-XXX / NFR-XXX）に対応した実装か

### 2. レイヤー責務

- [ ] `api` 層に DB アクセス・ビジネスロジックが直接書かれていないか
- [ ] ビジネスロジックは `services` に、DB アクセスは `repositories` に配置されているか

### 3. ドメイン制約

- [ ] 返却を物理削除していないか（`rentals.status = 'returned'` に更新する実装か）
- [ ] パスワードが平文保存・比較されていないか（bcrypt ハッシュ化必須）
- [ ] 各バリデーションのエラーコードが仕様通りか

### 4. 型・スタイル（Backend）

- [ ] 型ヒントが全関数・変数に付いているか（mypy strict）
- [ ] `ruff check` / `black --check` が通るか（line-length 120）

### 5. 型・スタイル（Frontend）

- [ ] 型注釈が付いているか（TypeScript strict）
- [ ] `eslint` / `prettier --check` が通るか（printWidth 100）

### 6. テスト

- [ ] 正常系テストがあるか
- [ ] 異常系テストがあるか（不正入力・バリデーション違反・DB制約違反）
- [ ] **テスト実行は Docker 経由**（`bash scripts/ci/test_backend.sh`）で行う

## 出力形式

```
## PR #43 レビュー結果：chore: Docker専用環境に整理

[設計] GET /api/v1/users レスポンスに is_admin が含まれていない → API設計書 3.2 と不一致
[Layer] users.py で DB 直接操作 → repositories へ移動
[Domain] 返却時に DELETE 実行 → status='returned' 更新に修正
[Test] 有効管理者退職化の 409 ケースがテストに不足
```

問題がなければ `指摘事項なし。` と出力する。
