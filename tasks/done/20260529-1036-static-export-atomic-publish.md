# static exporter atomic publish

状態: do
タスク種別: 機能追加

## 背景

`.workspace/plan-20260529.txt` の Phase 1 では、P1-13 として versioned data をすべて upload してから最後に `latest-manifest.json` を差し替え、途中失敗時に既存公開データが壊れないことが求められている。基本設計書 v0.4 でも、`/data/v/{export_version}` は immutable、`/data/latest-manifest.json` だけを短 TTL で差し替える方針になっている。

## 目的

static export の upload 順序を atomic publish にし、versioned data を先に公開データ bucket へ upload してから、最後に `latest-manifest.json` を差し替える。upload 途中で失敗した場合、既存 `latest-manifest.json` を更新せず、現行公開版を壊さない。

## スコープ

- 対象: static exporter の upload 処理、unit test、README、作業レポート。
- 対象 P1: P1-13。
- 対象外: 実 S3 / CloudFront deploy、CloudFront invalidation、post-deploy smoke 実行。

## 実施計画

1. 現在の `_upload_directory` の upload 順序と content type を確認する。
2. versioned data と `latest-manifest.json` を分離し、manifest を最後に upload する。
3. 失敗注入 test で、versioned upload 失敗時に manifest upload が呼ばれないことを確認する。
4. 成功 test で manifest upload が最後であることを確認する。
5. README に atomic publish 方針を追記する。

## ドキュメント保守計画

- README の public data / static export 説明に atomic publish 方針と失敗時の manifest 保護を追記する。

## 受け入れ条件

- [x] `_upload_directory` が `latest-manifest.json` 以外の versioned public data を先に upload する。
  - 根拠: `tests/test_static_exporter.py::test_upload_directory_publishes_manifest_last`。
- [x] `latest-manifest.json` は upload 順序の最後に upload される。
  - 根拠: 同 test。
- [x] versioned data upload 途中で失敗した場合、`latest-manifest.json` upload が実行されない。
  - 根拠: `tests/test_static_exporter.py::test_upload_directory_does_not_publish_manifest_after_versioned_failure`。
- [x] content type は JSON / SVG など既存どおり維持される。
  - 根拠: manifest JSON と SVG の `ContentType` assertion。
- [x] unit test が成功時の順序と失敗時の manifest 保護を検証する。
- [x] README に atomic publish 方針が反映されている。
- [x] 変更範囲に応じた tests と `npm run verify` が成功する。

## 検証計画

- `git diff --check`
- `python3 -m py_compile apps/workers/static-exporter/src/static_exporter/handler.py tests/test_static_exporter.py`
- `PYTHONPATH=apps/shared/src:apps/api/src:apps/workers/static-exporter/src python3 -m pytest tests/test_static_exporter.py`
- `npm test`
- `npm run verify`

## 検証結果

- `git diff --check`: pass
- `python3 -m py_compile apps/workers/static-exporter/src/static_exporter/handler.py tests/test_static_exporter.py`: pass
- `PYTHONPATH=apps/shared/src:apps/api/src:apps/workers/static-exporter/src python3 -m pytest tests/test_static_exporter.py`: pass（6 passed）
- `npm test`: pass（37 passed）
- `npm run verify`: pass

## PRレビュー観点

- manifest が最後に upload されること。
- versioned upload 失敗時に manifest が差し替わらないこと。
- local export / fixture export の挙動を壊していないこと。
- 実 S3 / CloudFront 確認が未実施である制約を PR に明記すること。
- stacked branch である制約を PR 本文に明記すること。

## リスク

- この branch は PR #11 を土台にした stacked worktree であり、PR #3〜#11 が merge されるまで main 向け差分には前段 PR の変更も含まれる。
- 実 S3 での upload 失敗注入や CloudFront 反映確認は未実施。
