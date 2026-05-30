# RandomBucket random videos API

## 背景

`.workspace/plan-20260530.txt` は v0.4 DDB item schema への準拠を検収基準に戻す方針を示している。
v0.4 の `RandomBucket` は `pk=RANDOM#DEFAULT`, `sk=VID#{bucket_no}#{video_id}` の事前シャッフル bucket として `/api/random-videos` から利用する設計だが、現状は動画一覧を時刻で rotate するだけで、DDB item が存在しない。

## 目的

公開動画保存時に `RandomBucket` item を生成し、`GET /api/random-videos` が repository の RandomBucket を優先して seed/count/tag/year 条件で安定抽出できるようにする。

## タスク種別

機能追加

## スコープ

- repository に `RandomBucket` item type、writer、query path を追加する。
- `put_video` 時に公開動画の RandomBucket を作成し、非公開化時は stale item を削除する。
- `GET /api/random-videos` を `count` / `seed` / `tag` / `year` に対応し、RandomBucket を優先利用する。
- API / repository contract tests、README、traceability、DDB audit を更新する。

## 対象外

- RandomBucket の専用 rebuild job。
- v0.4 の `VID#` key prefix への Video 全面 migration。
- 公開 static export 側で RandomBucket を直接利用する変更。

## 受け入れ条件

- [ ] `RandomBucket` item が `pk=RANDOM#DEFAULT`, `sk=VID#{bucket_no}#{video_id}` で保存される。
- [ ] `bucket_no` は video_id から deterministic に決まり、`generated_at`、表示用 title/thumbnail/duration/tags/published_at を含む。
- [ ] `put_video` が公開動画の RandomBucket を upsert し、非公開動画では stale RandomBucket を削除する。
- [ ] `GET /api/random-videos` が `count` / `seed` / `tag` / `year` を validation し、seed に対して安定順序で返す。
- [ ] RandomBucket が空の場合は既存の公開動画一覧 fallback が機能する。
- [ ] README、traceability、DDB schema audit が更新される。
- [ ] targeted tests、docs consistency、whitespace check、必要に応じて `npm run verify` が pass する。
- [ ] PR #40 に受け入れ条件確認コメントとセルフレビューコメントを追加する。

## 実装計画

1. repository に RandomBucket writer/query と stale 削除を追加する。
2. API handler の `/api/random-videos` を v0.4 query contract に寄せる。
3. repository / API tests と docs consistency を更新する。
4. README、traceability、DDB audit を更新する。
5. 検証、レポート、commit、push、PR コメント、task done 移動まで行う。

## 検証計画

- `python3 -m py_compile apps/api/src/diopside_api/handler.py apps/shared/src/diopside_core/repository.py`
- `PYTHONPATH=apps/shared/src:apps/api/src python3 -m pytest tests/test_api_handler.py tests/test_repository_schema_contract.py`
- `node tools/check-docs-consistency.mjs`
- `git diff --check`
- 変更範囲に応じて `npm run verify`

## PRレビュー観点

- seed が同じなら順序が安定し、時刻依存 rotate に戻っていないこと。
- tag/year filter が RandomBucket と fallback の両方で同じ意味を持つこと。
- 非公開動画が random response に混ざらないこと。

## リスク

- RandomBucket rebuild job は未実装のため、既存データへの backfill は別途必要。
- Video key prefix migration は別タスクとして残る。

## 状態

in_progress
