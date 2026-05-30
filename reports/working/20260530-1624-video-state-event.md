# VideoStateEvent item 対応 作業レポート

## 受けた指示

- `.workspace/plan-20260530.txt` と `.workspace/` の設計書に沿って v0.4 設計準拠を進める。
- main を pull してから worktree / task / PR flow で作業する。

## 要件整理

- live / archive 状態遷移を `VideoStateEvent` として append-only 保存する。
- key は `VID#{video_id}` / `EVT#STATE#{occurred_at}#{event_id}` にする。
- `live_status_scan` と `archive_finalize` の状態更新で event を記録する。
- README と schema audit を実装済み範囲に同期する。

## 検討・判断

- `video_state_event_item` と `append_video_state_event` を repository に追加した。
- event_name は `to_state` から標準名を補完し、`archive_finalize` では `video.archive_finalized` を明示する。
- `archive_finalize` は YouTube refresh 後に状態が変わるため、refresh 前の `live_state` を `from_state` として保持した。
- 既存状態 backfill、条件付き一意性、API/UI 表示は後続範囲として残した。

## 実施作業

- `VideoStateEvent` を `ITEM_TYPES` に追加した。
- `video_state_event_item`、`append_video_state_event` を追加した。
- `live_status_scan` と `archive_finalize` で状態 event を append するよう変更した。
- repository schema contract と core pipeline tests に event assertion を追加した。
- `README.md` と `docs/design/dynamodb-schema-audit.md` の `VideoStateEvent` 記述を更新した。

## 成果物

- `apps/shared/src/diopside_core/repository.py`
- `apps/workers/static-exporter/src/static_exporter/pipeline.py`
- `tests/test_repository_schema_contract.py`
- `tests/test_core_pipeline.py`
- `README.md`
- `docs/design/dynamodb-schema-audit.md`
- `tasks/do/20260530-1624-video-state-event.md`

## 検証

- `git diff --check` pass
- `python3 -m py_compile apps/shared/src/diopside_core/repository.py apps/workers/static-exporter/src/static_exporter/pipeline.py` pass
- `PYTHONPATH=apps/shared/src python3 -m pytest tests/test_repository_schema_contract.py` pass: 28 passed
- `PYTHONPATH=apps/shared/src:apps/workers/static-exporter/src python3 -m pytest tests/test_core_pipeline.py` pass: 43 passed
- `node tools/check-docs-consistency.mjs` pass
- `npm run verify` pass: 129 tests passed, build/package/e2e local passed

## Fit 評価

- v0.4 の `VideoStateEvent` key shape と必須 field を満たす append-only item を追加した。
- 状態更新の主要経路である `live_status_scan` / `archive_finalize` に接続した。
- docs は実装済み範囲と未対応範囲を分けて記載した。

## 未対応・制約・リスク

- 既存状態の backfill は未実施。
- event_id の実 DynamoDB 条件付き一意性は未実装。
- VideoStateEvent の API / UI 表示は未実装。
