# normalized chat schema 固定

状態: do
タスク種別: 機能追加

## 背景

`.workspace/plan-20260529.txt` の Phase 1 では、P1-09 として live/replay/paid/sticker/emoji/unknown を統一 schema へ正規化し、contract test を追加することが求められている。基本設計書 v0.4 でも、YouTube live chat/replay chat の差異を吸収した共通 ChatMessage schema が必要とされている。

## 目的

live chat と replay chat の正規化結果を、後続の集計・wordcloud・timestamp 生成が同じ構造で扱える stable schema に固定する。既知の text / paid / sticker / emoji と unknown renderer を同じ必須キー集合で表現し、contract test で退行を検出できるようにする。

## スコープ

- 対象: chat 正規化 schema、normalize 関数、contract test、README、作業レポート。
- 対象 P1: P1-09。
- 対象外: wordcloud SVG 生成、timestamp 品質強化、実 YouTube / AWS 疎通、UI 表示変更。

## 実施計画

1. 既存の `normalize_live_chat_items` / `normalize_replay_actions` と集計の利用キーを確認する。
2. ChatMessage の必須キーと type 値を定義し、正規化関数が全 message type で同じ schema を返すようにする。
3. paid / sticker / emoji / unknown の replay fixture と live fixture を含む contract test を追加する。
4. README に normalized chat schema の固定項目と扱いを追記する。
5. targeted pytest、`npm test`、`npm run verify` を実行する。

## ドキュメント保守計画

- README に normalized chat JSONL の必須キーと message_type 方針を追記する。
- `docs/` への分割要件更新はこのリポジトリではまだ既存構成がないため、README に実装 contract として記録する。

## 受け入れ条件

- [x] live chat text message が固定 ChatMessage schema の必須キーをすべて持つ。
  - 根拠: `tests/test_core_pipeline.py::test_normalized_chat_message_schema_contract_for_live_and_replay_variants`。
- [x] replay text message が固定 ChatMessage schema の必須キーをすべて持つ。
  - 根拠: 同 contract test。
- [x] paid message / paid sticker / emoji run / unknown renderer が同じ schema で表現される。
  - 根拠: 同 contract test。
- [x] `message_type` が `text`、`paid`、`sticker`、`unknown` のいずれかに正規化される。
  - 根拠: 同 contract test。
- [x] contract test が schema 必須キー、nullable key、raw renderer summary の境界を検証する。
  - 根拠: `CHAT_MESSAGE_REQUIRED_KEYS`、`author`、`paid`、`raw_renderer` の assertion。
- [x] README に normalized chat schema と raw body 境界が反映されている。
- [x] 変更範囲に応じた tests と `npm run verify` が成功する。

## 検証計画

- `git diff --check`
- `python3 -m py_compile apps/shared/src/diopside_core/chat.py tests/test_core_pipeline.py`
- `PYTHONPATH=apps/shared/src:apps/api/src:apps/workers/static-exporter/src python3 -m pytest tests/test_core_pipeline.py`
- `npm test`
- `npm run verify`

## 検証結果

- `git diff --check`: pass
- `python3 -m py_compile apps/shared/src/diopside_core/chat.py apps/shared/src/diopside_core/__init__.py tests/test_core_pipeline.py`: pass
- `PYTHONPATH=apps/shared/src:apps/api/src:apps/workers/static-exporter/src python3 -m pytest tests/test_core_pipeline.py`: pass（19 passed）
- `npm test`: pass（31 passed）
- `npm run verify`: pass

## PRレビュー観点

- message type ごとに必須キーの欠落がないこと。
- unknown renderer の raw body を必要以上に DynamoDB item へ載せないこと。
- 既存の aggregate / timestamp 入力との互換性を壊していないこと。
- benchmark 期待語句や dataset 固有分岐を実装に入れていないこと。
- stacked branch である制約を PR 本文に明記すること。

## リスク

- この branch は PR #7 を土台にした stacked worktree であり、PR #3〜#7 が merge されるまで main 向け差分には前段 PR の変更も含まれる。
- 実 YouTube / AWS 疎通は行わず、unit test と local artifact 経路で検証する。
