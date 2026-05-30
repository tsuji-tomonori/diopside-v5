# VideoStateEvent item 対応

## 背景

`.workspace/plan-20260530.txt` の v0.4 設計準拠対応では、DDB item schema の差分解消が残っている。`docs/design/dynamodb-schema-audit.md` では `VideoStateEvent` が `VID#{video_id}` / `EVT#STATE#{occurred_at}#{event_id}` として設計されている一方、現行実装は `Video.live_state` の read model 更新のみで状態遷移履歴を保存していない。

## 目的

live / archive 状態遷移を `VideoStateEvent` として append-only に保存し、v0.4 の状態遷移履歴 item を部分実装する。

## タスク種別

機能追加

## スコープ

- `apps/shared/src/diopside_core/repository.py` の `VideoStateEvent` helper / writer。
- `apps/workers/static-exporter/src/static_exporter/pipeline.py` の `live_status_scan` / `archive_finalize` 接続。
- `tests/test_repository_schema_contract.py` と `tests/test_core_pipeline.py` の contract。
- `README.md` と `docs/design/dynamodb-schema-audit.md` の `VideoStateEvent` 記述。
- 作業レポート、PR コメント、task done 更新。

## スコープ外

- 既存 DynamoDB data の backfill。
- 高並列時の event_id 条件付き一意性。
- VideoStateEvent の API / UI 表示。

## 受け入れ条件

- [x] `append_video_state_event` が `pk=VID#{video_id}` / `sk=EVT#STATE#{occurred_at}#{event_id}` の `VideoStateEvent` item を保存する。
- [x] `VideoStateEvent` item が `event_id`、`video_id`、`event_name`、`from_state`、`to_state`、`source_job_id`、`occurred_at`、`payload` を持つ。
- [x] `live_status_scan` が状態遷移時に `VideoStateEvent` を保存する。
- [x] `archive_finalize` が archive finalization の状態 event を保存する。
- [x] `README.md` と `docs/design/dynamodb-schema-audit.md` が実装済み形状に同期している。
- [x] 選定した検証コマンドが pass し、未実施の検証がある場合は理由を記録する。
- [x] PR に受け入れ条件確認コメントとセルフレビューコメントを日本語で追加する。

## 検証計画

- `python3 -m py_compile apps/shared/src/diopside_core/repository.py apps/workers/static-exporter/src/static_exporter/pipeline.py`
- `PYTHONPATH=apps/shared/src python3 -m pytest tests/test_repository_schema_contract.py`
- `PYTHONPATH=apps/shared/src:apps/workers/static-exporter/src python3 -m pytest tests/test_core_pipeline.py`
- `node tools/check-docs-consistency.mjs`
- `git diff --check`
- `npm run verify`

## リスク

- 既存状態の backfill は未実施。
- event_id は deterministic helper で作るが、実 DynamoDB の条件付き重複防止は未実装。

## 実施結果

- `video_state_event_item`、`append_video_state_event` を追加し、`VideoStateEvent` を `VID#{video_id}` / `EVT#STATE#{occurred_at}#{event_id}` に保存するようにした。
- `live_status_scan` が状態遷移時に event を append するようにした。
- `archive_finalize` が archive finalization event を append するようにした。
- README と `docs/design/dynamodb-schema-audit.md` を実装済み形状に同期した。
- 作業レポートを `reports/working/20260530-1624-video-state-event.md` に作成した。

## 検証結果

- `git diff --check`: pass
- `python3 -m py_compile apps/shared/src/diopside_core/repository.py apps/workers/static-exporter/src/static_exporter/pipeline.py`: pass
- `PYTHONPATH=apps/shared/src python3 -m pytest tests/test_repository_schema_contract.py`: 28 passed
- `PYTHONPATH=apps/shared/src:apps/workers/static-exporter/src python3 -m pytest tests/test_core_pipeline.py`: 43 passed
- `node tools/check-docs-consistency.mjs`: pass
- `npm run verify`: 129 tests passed + build/package/local e2e passed

## PR コメント

- 受け入れ条件確認: https://github.com/tsuji-tomonori/diopside-v5/pull/40#issuecomment-4582066342
- セルフレビュー: https://github.com/tsuji-tomonori/diopside-v5/pull/40#issuecomment-4582066344

## 状態

done
