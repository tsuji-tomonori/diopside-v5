# VideoStatSnapshot item 対応 作業レポート

## 受けた指示

- `.workspace/plan-20260530.txt` と `.workspace/` の設計書に沿って v0.4 設計準拠を進める。
- main を pull してから worktree / task / PR flow で作業する。

## 要件整理

- YouTube metadata の統計値を `VideoStatSnapshot` として保存する。
- key は `VID#{video_id}` / `STAT#{yyyyMMddHH}` にする。
- `put_video` が `statistics` 付き metadata を保存するときに snapshot を upsert する。
- README と schema audit を実装済み範囲に同期する。

## 検討・判断

- `video_stat_snapshot_item` と `put_video_stat_snapshot` を repository に追加した。
- `statistics` の camelCase field と snake_case field の両方を受け入れるようにした。
- 同一時間帯 snapshot は `STAT#{yyyyMMddHH}` で upsert する。高頻度抑止や dedicated scheduler は後続範囲とした。

## 実施作業

- `VideoStatSnapshot` を `ITEM_TYPES` に追加した。
- `video_stat_snapshot_item`、`put_video_stat_snapshot`、統計値抽出 helper を追加した。
- `put_video` が統計値を含む場合に snapshot を保存するよう変更した。
- repository schema contract に snapshot 保存 assertion を追加した。
- `README.md` と `docs/design/dynamodb-schema-audit.md` の `VideoStatSnapshot` 記述を更新した。

## 成果物

- `apps/shared/src/diopside_core/repository.py`
- `tests/test_repository_schema_contract.py`
- `README.md`
- `docs/design/dynamodb-schema-audit.md`
- `tasks/do/20260530-1640-video-stat-snapshot.md`

## 検証

- `git diff --check` pass
- `python3 -m py_compile apps/shared/src/diopside_core/repository.py` pass
- `PYTHONPATH=apps/shared/src python3 -m pytest tests/test_repository_schema_contract.py` pass: 29 passed
- `node tools/check-docs-consistency.mjs` pass
- `npm run verify` pass: 130 tests passed, build/package/e2e local passed

## Fit 評価

- v0.4 の `VideoStatSnapshot` key shape と主要 field を満たす snapshot item を追加した。
- `put_video` 経由の metadata 保存時に統計 snapshot が作られるため、metadata sync / live refresh / archive refresh の統計保存経路に乗る。
- docs は実装済み範囲と未対応範囲を分けて記載した。

## 未対応・制約・リスク

- 既存統計の backfill は未実施。
- 統計 snapshot の API / UI 表示は未実装。
- 高頻度抑止や dedicated scheduler は未実装。
