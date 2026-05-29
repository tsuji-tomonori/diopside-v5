# quota usageの可視化

状態: do

## 背景

`.workspace/plan-20260529.txt` の P1-15 に従い、YouTube API quota usage を method、units、video_count、channel_id、job_id 付きで記録し、管理UI/APIで確認できるようにする。

## 受け入れ条件

- metadata sync / live status scan の YouTube API 呼び出しで `QuotaUsage` に `method`、`units`、`video_count`、`channel_id`、`job_id` を記録する。
- `GET /api/admin/quota-usage` が上記 field を top-level で返し、既存 `details` のみへの依存を避ける。
- 管理UIの quota usage 表示で method、units、video_count、channel_id、job_id を確認できる。
- 既存の repository test / API test / UI script が quota usage schema を検証する。
- README の quota usage 説明を更新する。
- 変更範囲に見合う検証と `npm run verify` が成功する。
