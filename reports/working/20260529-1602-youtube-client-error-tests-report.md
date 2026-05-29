# YouTube client error test 作業レポート

## 受けた指示

- `.workspace/` 配下の設計書と 2026-05-29 の plan に基づいて作業する。
- `main` から pull してから、P4-05 YouTube client error test を進める。
- Worktree Task PR Flow に従い、task、検証、PR コメントまで行う。

## 要件整理

- quota exceeded、403、404、network timeout、malformed response をテストする。
- YouTube API client が低レベル例外をそのまま出すと worker の failed job debug で原因分類しにくいため、client error の contract を固定する。

## 検討・判断

- `YouTubeClientError` を追加し、`status_code`、`reason`、`retryable` を保持する形にした。
- HTTP error body の `error.errors[].reason` を優先して reason にする。
- quota/rate limit/backend error と 429/5xx は retryable、403/404 の通常理由と malformed response は non-retryable とした。

## 実施作業

- `apps/shared/src/diopside_core/youtube.py` に `YouTubeClientError` と error normalization を追加した。
- `apps/shared/src/diopside_core/__init__.py` から `YouTubeClientError` を export した。
- `tests/test_core_pipeline.py` に quota exceeded、403、404、network timeout、malformed response のテストを追加した。
- P4-05 の task md を作成した。

## 成果物

- `apps/shared/src/diopside_core/youtube.py`
- `apps/shared/src/diopside_core/__init__.py`
- `tests/test_core_pipeline.py`
- `tasks/do/20260529-1602-youtube-client-error-tests.md`
- PR: https://github.com/tsuji-tomonori/diopside-v5/pull/37
- 受け入れ条件確認コメント: https://github.com/tsuji-tomonori/diopside-v5/pull/37#issuecomment-4570838958
- セルフレビューコメント: https://github.com/tsuji-tomonori/diopside-v5/pull/37#issuecomment-4570841285

## 検証

- `git diff --check`: 成功
- `PYTHONPATH=apps/shared/src:apps/api/src:apps/workers/static-exporter/src python3 -m pytest tests/test_core_pipeline.py -k youtube_client`: 7 passed
- `npm test`: 69 passed
- `npm run verify`: 成功
  - `npm test`: 69 passed
  - `npm run build`: 成功
  - `npm run package:deploy`: 成功
  - `npm run e2e:local`: 成功
- GitHub Actions `CI / npm verify`: 成功

## fit 評価

- P4-05 の YouTube client error test 追加要求に対応した。
- 追加テストは `npm test` に含まれるため、P4-01 の GitHub Actions CI の `npm run verify` で実行される。

## 未対応・制約・リスク

- 実 YouTube API への通信は行わず、urllib response / exception mock による client contract 固定に限定した。
- GitHub Apps による PR top-level comment は 403 のため、`gh pr comment` で代替した。
