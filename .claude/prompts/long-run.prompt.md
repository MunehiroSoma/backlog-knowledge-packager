---
mode: agent
description: 長時間の実装タスクを中断せず自走で完遂する
---

# long-run — 長時間自走実装

長時間の実装タスクを、不要な確認待ちを挟まずに継続実行する。

## 実行前提

- 明示的な停止指示があるまで実装・検証・修正を継続する
- マイルストーンごとに進捗を共有するが「続けてよいか」の確認は原則しない
- 判断が必要な箇所は影響が小さい側に倒して前進する

## ブランチ運用

```bash
# 1. main から feature ブランチを切る
git checkout main && git pull origin main
git checkout -b feature/<task-slug>

# 2. 実装・検証・修正を繰り返す

# 3. 完了したら push して PR を作成する
git push origin feature/<task-slug>
gh pr create ...
```

> `autopilot/` プレフィックスは使用しない。ブランチ命名規則: `feature/` `fix/` `chore/` 等。

## 実行ループ

1. 目的と完了条件を確認する
1. 影響範囲を調査し、最短で価値が出る順に実装する
1. 実装後に検証を実行する
   ```bash
   cd backend && pre-commit run --all-files && pytest
   cd frontend && npm run lint
   ```
1. 失敗したら自己修正して再実行する（通るまで繰り返す）
1. 完了条件を満たしたら結果・未解決事項・次の推奨アクションを報告する

## ブロック時の動き

- 10 分以上進捗が止まる場合は代替案を先に試す
- 解消しない場合のみ、質問は 1 回・短文で行う
