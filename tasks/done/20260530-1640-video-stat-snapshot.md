# VideoStatSnapshot item 対応

## 背景

`.workspace/plan-20260530.txt` の v0.4 設計準拠対応では、DDB item schema の差分解消が残っている。`docs/design/dynamodb-schema-audit.md` では `VideoStatSnapshot` が `VID#{video_id}` / `STAT#{yyyyMMddHH}` として設計されている一方、現行実装は統計値を `Video.statistics` read model に寄せている。

## 目的

YouTube metadata の統計値を `VideoStatSnapshot` として保存し、v0.4 の時系列 snapshot item を部分実装する。

## スコープ

- `apps/shared/src/diopside_core/repository.py` の `VideoStatSnapshot` helper / writer。
- `put_video` から統計値が存在する場合に snapshot を upsert する経路。
- `tests/test_repository_schema_contract.py` の schema contract。
- `README.md` と `docs/design/dynamodb-schema-audit.md` の `VideoStatSnapshot` 記述。
- 作業レポート、PR コメント、task done 更新。

## スコープ外

- 既存 DynamoDB data の backfill。
- 統計 snapshot の API / UI 表示。
- 高頻度抑止や dedicated scheduler。

## 受け入れ条件

- [x] `put_video_stat_snapshot` が `pk=VID#{video_id}` / `sk=STAT#{yyyyMMddHH}` の `VideoStatSnapshot` item を保存する。
- [x] `VideoStatSnapshot` item が `video_id`、`sampled_at`、`view_count`、`like_count`、`comment_count`、`concurrent_viewers`、`raw_s3_uri` を持てる。
- [x] `put_video` が `statistics` を含む metadata 保存時に snapshot を作成する。
- [x] 既存 `Video` read model / public export contract を壊さない。
- [x] `README.md` と `docs/design/dynamodb-schema-audit.md` が実装済み形状に同期している。
- [x] 選定した検証コマンドが pass し、未実施の検証がある場合は理由を記録する。
- [x] PR に受け入れ条件確認コメントとセルフレビューコメントを日本語で追加する。

## 検証計画

- `python3 -m py_compile apps/shared/src/diopside_core/repository.py`
- `PYTHONPATH=apps/shared/src python3 -m pytest tests/test_repository_schema_contract.py`
- `node tools/check-docs-consistency.mjs`
- `git diff --check`
- `npm run verify`

## リスク

- 既存統計の backfill は未実施。
- 同一時間帯 snapshot は `STAT#{yyyyMMddHH}` に upsert される。

## 実施結果

- `video_stat_snapshot_item`、`put_video_stat_snapshot` を追加し、`VideoStatSnapshot` を `VID#{video_id}` / `STAT#{yyyyMMddHH}` に保存するようにした。
- `put_video` が `statistics` を含む場合に snapshot を upsert するようにした。
- README と `docs/design/dynamodb-schema-audit.md` を実装済み形状に同期した。
- 作業レポートを `reports/working/20260530-1640-video-stat-snapshot.md` に作成した。

## 検証結果

- `git diff --check`: pass
- `python3 -m py_compile apps/shared/src/diopside_core/repository.py`: pass
- `PYTHONPATH=apps/shared/src python3 -m pytest tests/test_repository_schema_contract.py`: 29 passed
- `node tools/check-docs-consistency.mjs`: pass
- `npm run verify`: 130 tests passed + build/package/local e2e passed

## PR コメント

- 受け入れ条件確認: https://github.com/tsuji-tomonori/diopside-v5/pull/40#issuecomment-4582090663
- セルフレビュー: https://github.com/tsuji-tomonori/diopside-v5/pull/40#issuecomment-4582090659

## 状態

done
