---
mode: agent
description: 実装完了判定チェックリストを実行し、テスト記録テンプレートを提供する
---

# test-check — 実装完了チェック

実装完了判定チェックリストを実行する。以下をすべて満たすまで「完了」としない。

## 完了判定チェックリスト

### Backend

- [ ] `cd backend && pytest` 通過
- [ ] `cd backend && ruff check . && mypy .` エラーなし
- [ ] `cd backend && black --check . && ruff format --check .` 差分なし

### Frontend

- [ ] `cd frontend && npm run lint` エラーなし
- [ ] `cd frontend && npm run format:check` 差分なし

### 正常系

- [ ] 期待通りの出力・レスポンスが返る
- [ ] DB にレコードが正しく保存される（DB 操作がある場合）

### 異常系

- [ ] 不正入力で適切なエラーコードが返る（422/400/409/404 等）
- [ ] ドメイン制約（二重貸出禁止・返却論理削除・パスワードハッシュ等）が守られている

## テストケース記録テンプレート

`docs/test/TC_<機能名>.md` に以下の形式で記録する。

```markdown
# TC_<機能名>

## 実施情報
- 実施日: YYYY-MM-DD
- 実施者: <名前>

## 正常系
| ケース | 手順 | 期待結果 | 結果 |
|---|---|---|---|
| | | | Pass/Fail |

## 異常系
| ケース | 手順 | 期待エラー | 結果 |
|---|---|---|---|
| | | | Pass/Fail |

## 備考
```
