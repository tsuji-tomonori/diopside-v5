# metadata sync pagination と raw response 保存

状態: done
タスク種別: 機能追加

## 背景

`.workspace/plan-20260529.txt` の Phase 1 では、本番データ pipeline 完成に向けて P1-05 metadata sync pagination 対応と P1-06 YouTube raw response 保存が必要とされている。PR #3/#4 で P0 ブロッカーと repository/job lifecycle の土台は進んだため、次に YouTube metadata 取得の実データ経路を強化する。

## 目的

`metadata_sync` worker が uploads playlist の `nextPageToken` を扱い、途中失敗時に cursor から再開でき、`playlistItems.list` と `videos.list` の raw response を S3/local artifact に保存し、DynamoDB には URI と要約だけを残す状態にする。

## スコープ

- 対象: `apps/workers/static-exporter/src/static_exporter/pipeline.py`、`tests/test_core_pipeline.py`、`README.md`、作業レポート。
- 対象 P1: P1-05、P1-06。
- 対象外: 実 YouTube API 呼び出し、実 AWS deploy、P1-07 以降の live/replay chat collector 強化。

## 実施計画

1. `metadata_sync` が `params.page_token`、または `ChannelCursor.next_page_token` を使って playlist page を取得できるようにする。
2. `playlistItems.list` と `videos.list` の raw response を `raw/youtube/metadata/...` へ保存する。
3. `ChannelCursor` に page token、next page token、raw response URI、last video ids を保存する。
4. `Video` item には raw response 本文ではなく `raw_metadata_uri` などの URI/要約だけを残す。
5. `nextPageToken` がある場合、次 page の `metadata_sync` を queue へ再投入できるようにする。
6. unit test と README を更新する。

## ドキュメント保守計画

- README の S3 path、DynamoDB item schema、metadata sync の運用説明を更新する。

## 受け入れ条件

- [x] P1-05: `playlistItems.list` の `nextPageToken` を `ChannelCursor` に保存し、明示 `page_token` がない場合は cursor から再開できる。
  - 根拠: `metadata_sync`、`tests/test_core_pipeline.py::test_metadata_sync_resumes_from_channel_cursor`。
- [x] P1-05: `nextPageToken` がある場合、次 page の `metadata_sync` payload が queue に再投入される。
  - 根拠: `tests/test_core_pipeline.py::test_metadata_sync_paginates_saves_raw_and_cursor`。
- [x] P1-06: `playlistItems.list` raw response が S3/local artifact の `raw/youtube/metadata/...` に保存される。
  - 根拠: `metadata_sync`、`tests/test_core_pipeline.py::test_metadata_sync_paginates_saves_raw_and_cursor`。
- [x] P1-06: `videos.list` raw response が S3/local artifact の `raw/youtube/metadata/...` に保存される。
  - 根拠: `metadata_sync`、`tests/test_core_pipeline.py::test_metadata_sync_paginates_saves_raw_and_cursor`。
- [x] P1-06: DynamoDB の `Video` / `ChannelCursor` には raw response 本文を保存せず、URI と件数・video ids などの要約のみを保存する。
  - 根拠: `tests/test_core_pipeline.py::test_metadata_sync_paginates_saves_raw_and_cursor`。
- [x] README に metadata raw response path と cursor 再開方針が反映されている。
- [x] 変更範囲に応じた tests と `npm run verify` が成功する。

## 検証計画

- `git diff --check`
- `PYTHONPATH=apps/shared/src:apps/api/src:apps/workers/static-exporter/src python3 -m pytest tests/test_core_pipeline.py`
- `npm test`
- `npm run verify`

## 検証結果

- `git diff --check`: pass
- `PYTHONPATH=apps/shared/src:apps/api/src:apps/workers/static-exporter/src python3 -m pytest tests/test_core_pipeline.py`: 初回 fail -> local `video_resources` 経路の raw metadata 出力を補正後 pass
- `npm test`: pass
- `npm run verify`: pass

## PRレビュー観点

- raw response 本文を DynamoDB item に保存していないこと。
- cursor 再開と明示 `page_token` の優先順位が明確なこと。
- 次 page 再投入が queue 未設定時に local test を壊さないこと。
- stacked branch である制約を PR 本文に明記すること。

## リスク

- この branch は PR #4 を土台にした stacked worktree であり、PR #3/#4 が merge されるまで main 向け差分には前段 PR の変更も含まれる。
- 実 YouTube API 呼び出しと実 S3/DynamoDB 接続は行わず、mock/local artifact で検証する。
