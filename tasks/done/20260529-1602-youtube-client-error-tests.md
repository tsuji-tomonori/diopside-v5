# YouTube client error test

状態: done

## 背景

`.workspace/plan-20260529.txt` の P4-05 に従い、YouTube client の quota exceeded、403、404、network timeout、malformed response をテストする。

## 目的

YouTube API 呼び出し失敗時の例外情報を contract として固定し、worker が原因を失わずに failed job debug へ渡せるようにする。

## タスク種別

test / error handling

## スコープ

- `apps/shared/src/diopside_core/youtube.py`
- `apps/shared/src/diopside_core/__init__.py`
- `tests/test_core_pipeline.py`

## 計画

1. 現行 `YouTubeClient` の HTTP / JSON error 挙動を確認する。
2. status code、reason、retryable を持つ client error を追加する。
3. quota exceeded、403、404、network timeout、malformed response の test を追加する。
4. `npm test` / `npm run verify` で CI 対象に入ることを確認する。
5. 作業レポート、commit、PR、受け入れ条件コメント、セルフレビューまで完了する。

## ドキュメント保守方針

内部 client error handling の強化であり README 更新は不要の見込み。例外 contract と検証内容は task md と作業レポートに残す。

## 受け入れ条件

- quota exceeded が reason と retryable 情報つきで検出される。
- 403 が status code と reason つきで検出される。
- 404 が status code と reason つきで検出される。
- network timeout が retryable な network error として検出される。
- malformed JSON / malformed response が non-retryable な malformed response として検出される。
- 追加テストが `npm test`、ひいては CI の `npm run verify` で実行される。
- 変更範囲に見合う検証が成功する。

## 検証計画

- `git diff --check`
- targeted pytest
- `npm test`
- `npm run verify`

## 完了結果

- PR: https://github.com/tsuji-tomonori/diopside-v5/pull/37
- 受け入れ条件確認コメント: https://github.com/tsuji-tomonori/diopside-v5/pull/37#issuecomment-4570838958
- セルフレビューコメント: https://github.com/tsuji-tomonori/diopside-v5/pull/37#issuecomment-4570841285
- GitHub Actions `CI / npm verify`: 成功

## 検証結果

- `git diff --check`: 成功
- `PYTHONPATH=apps/shared/src:apps/api/src:apps/workers/static-exporter/src python3 -m pytest tests/test_core_pipeline.py -k youtube_client`: 7 passed
- `npm test`: 69 passed
- `npm run verify`: 成功
- GitHub Actions `CI / npm verify`: 成功

## リスク

- 実 YouTube API への通信は行わず、urllib response / exception mock による client contract 固定に限定する。
