# VideoMonthIndex read model

## 背景

`.workspace/plan-20260530.txt` は v0.4 DDB item schema への準拠を検収基準に戻す方針を示している。
v0.4 の `VideoMonthIndex` は `pk=VID#{video_id}`, `sk=INDEX#MONTH#{yyyyMM}` で月別カレンダー用 read model を保持し、GSI1 の `VIDEO#MONTH#{yyyyMM}` query で Scan なしに月別 browse を取得する設計である。
現状の archive calendar は公開動画一覧を走査して年月を集計しているため、DDB schema audit では `VideoMonthIndex` が未対応のまま残っている。

## 目的

動画保存時に `VideoMonthIndex` を更新し、`GET /api/archive-calendar` と static export の calendar 生成が repository の月別 read model を利用できる状態にする。

## タスク種別

機能追加

## スコープ

- repository に `VideoMonthIndex` item type、writer、query path を追加する。
- `put_video` 時に公開動画の月別 index を upsert し、非公開化または公開月変更時に stale index を削除する。
- archive calendar API が DynamoDB repository 利用時に `VideoMonthIndex` query path を優先できるようにする。
- static exporter が repository の calendar read model を使える場合はそれを利用し、ない場合は既存の動画一覧集計 fallback を維持する。
- repository/API/static export tests、README、traceability、DDB audit、compliance audit を更新する。

## 対象外

- v0.4 key prefix の `VID#` / `VIDEO#` 全面移行。
- 既存 DynamoDB data の `VideoMonthIndex` backfill job。
- Calendar UI の新規実装。

## 受け入れ条件

- [x] `VideoMonthIndex` item が `pk=VID#{video_id}`, `sk=INDEX#MONTH#{yyyyMM}` で保存される。
- [x] item に `video_id`、`yyyy_mm`、`published_at`、`title`、`thumbnail_url`、`duration_sec`、`archive_state` が含まれる。
- [x] item は `gsi1pk=VIDEO#MONTH#{yyyyMM}`, `gsi1sk=PUB#{published_at}#{video_id}` を持つ。
- [x] `put_video` により公開動画の index が更新され、非公開化または公開月変更時に stale index が削除される。
- [x] `GET /api/archive-calendar` が repository 利用時に `VideoMonthIndex` read model を利用する。
- [x] static export の `/data/calendar/{year}.json` が repository の calendar read model を利用できる。
- [x] README、traceability、DDB schema audit、compliance audit が更新される。
- [x] targeted tests、docs consistency、whitespace check、必要に応じて `npm run verify` が pass する。
- [x] PR #40 に受け入れ条件確認コメントとセルフレビューコメントを追加する。

## 実装計画

1. repository に `video_month_index_item`、`list_video_month_indexes`、月別 index 更新処理を追加する。
2. API archive calendar と static exporter の calendar 生成を read model 優先に変更する。
3. repository/API/static exporter tests を追加・更新する。
4. README、traceability、DDB audit、compliance audit を更新する。
5. 検証、レポート、commit、push、PR コメント、task done 移動まで行う。

## ドキュメント保守計画

- README の DDB schema と archive calendar 説明を更新する。
- `docs/design/dynamodb-schema-audit.md` の `VideoMonthIndex` を未対応から部分実装へ更新する。
- `docs/design/traceability-matrix.md` と `reports/audit/design-v0.4-compliance-20260530.md` に今回の範囲と残課題を反映する。

## 検証計画

- `python3 -m py_compile apps/shared/src/diopside_core/repository.py apps/api/src/diopside_api/handler.py apps/workers/static-exporter/src/static_exporter/handler.py`
- `PYTHONPATH=apps/shared/src:apps/api/src:apps/workers/static-exporter/src python3 -m pytest tests/test_repository_schema_contract.py tests/test_api_handler.py tests/test_static_exporter.py`
- `node tools/check-docs-consistency.mjs`
- `git diff --check`
- 変更範囲に応じて `npm run verify`

## PRレビュー観点

- archive calendar が public video 以外を含まないこと。
- 月変更・非公開化で stale `VideoMonthIndex` が残らないこと。
- `VideoMonthIndex` がない既存環境でも既存 fallback が動くこと。
- backfill 未実装を完了扱いしないこと。

## リスク

- 既存 DynamoDB data の backfill は未実装。
- `Video` key prefix は現行 `VIDEO#` のままで、`VideoMonthIndex` の v0.4 key shape だけを部分実装する。

## 検証結果

- `python3 -m py_compile apps/shared/src/diopside_core/repository.py apps/api/src/diopside_api/handler.py apps/workers/static-exporter/src/static_exporter/handler.py`: pass
- `PYTHONPATH=apps/shared/src:apps/api/src:apps/workers/static-exporter/src python3 -m pytest tests/test_repository_schema_contract.py tests/test_api_handler.py tests/test_static_exporter.py`: pass（44 tests）
- `node tools/check-docs-consistency.mjs`: pass
- `git diff --check`: pass
- `npm run verify`: pass（108 tests + build/package/local e2e）

## PR コメント

- 受け入れ条件確認: https://github.com/tsuji-tomonori/diopside-v5/pull/40#issuecomment-4581669969
- セルフレビュー: https://github.com/tsuji-tomonori/diopside-v5/pull/40#issuecomment-4581670154

## 状態

done
