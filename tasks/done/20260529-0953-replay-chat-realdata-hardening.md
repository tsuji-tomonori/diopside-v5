# replay chat collector 現実データ検証

状態: do
タスク種別: 機能追加

## 背景

`.workspace/plan-20260529.txt` の Phase 1 では、P1-08 として replay chat collector を公開アーカイブ HTML から取得できる範囲で検証し、構造変化時も unknown renderer として落とさず保存することが求められている。基本設計書 v0.4 でも、公開リプレイチャットは best-effort 取得とし、構造変更時は安全に扱う方針になっている。

## 目的

replay chat collect が実 YouTube アーカイブ HTML に近い初期データ構造から continuation / action を抽出でき、既知 renderer 以外が混ざっても raw JSONL と manifest に保存して後続解析へ渡せる状態にする。

## スコープ

- 対象: replay chat collector の抽出・保存処理、関連 unit test、README、作業レポート。
- 対象 P1: P1-08。
- 対象外: 実 YouTube へのネットワーク疎通、実 AWS deploy、normalized schema 固定、paid/sticker/emoji の完全正規化。

## 実施計画

1. 現在の replay chat collect / YouTube client / parser 実装を確認する。
2. 公開アーカイブ HTML 由来の `ytInitialData` / continuation から replay action を抽出できる処理を補強する。
3. unknown renderer を例外や破棄ではなく raw action と分類付き JSONL に保存する。
4. 既知 renderer と unknown renderer を含む fixture 的テストを追加する。
5. README に replay chat best-effort と unknown 保存方針を追記する。

## ドキュメント保守計画

- README の replay chat collect 説明に、公開 HTML からの continuation/action 抽出と unknown renderer 保存方針を追記する。
- `docs/` 分割要件への直接影響はないため、README 更新で足りるか確認する。

## 受け入れ条件

- [x] 公開アーカイブ HTML に近い `ytInitialData` から replay continuation または replay actions を抽出できる。
  - 根拠: `tests/test_core_pipeline.py::test_public_replay_initial_data_keeps_unknown_renderer_and_continuation`。
- [x] replay action 内の既知 text renderer が raw JSONL に保存される。
  - 根拠: 同テストで raw JSONL の `message_text` を確認。
- [x] 未知 renderer が混ざっても collector が失敗せず、unknown renderer として raw JSONL / manifest に残る。
  - 根拠: 同テストで `parse_warning=unknown_renderer`、`raw_renderer_type`、`parser_stats.unknown_count` を確認。
- [x] 構造変化時に action 抽出数や unknown 件数が manifest/result から確認できる。
  - 根拠: `parser_stats.action_count`、`unknown_count`、`continuation_count` を result と manifest で確認。
- [x] README に replay collector の best-effort 方針と unknown 保存方針が反映されている。
- [x] 変更範囲に応じた tests と `npm run verify` が成功する。

## 検証計画

- `git diff --check`
- `PYTHONPATH=apps/shared/src:apps/api/src:apps/workers/static-exporter/src python3 -m pytest tests/test_core_pipeline.py`
- `npm test`
- `npm run verify`

## 検証結果

- `git diff --check`: pass
- `python3 -m py_compile apps/shared/src/diopside_core/youtube.py apps/shared/src/diopside_core/__init__.py apps/workers/static-exporter/src/static_exporter/pipeline.py tests/test_core_pipeline.py`: pass
- `PYTHONPATH=apps/shared/src:apps/api/src:apps/workers/static-exporter/src python3 -m pytest tests/test_core_pipeline.py`: 初回 fail（`replayChatItemAction` 内の `addChatItemAction` を重複抽出）-> 抽出 helper 修正後 pass（18 passed）
- `npm test`: pass（30 passed）
- `npm run verify`: pass

## PRレビュー観点

- 実 YouTube の構造変化で collector が即失敗しないこと。
- unknown renderer を本番 UI の架空データとして扱わず、raw/debug 情報として保存していること。
- DynamoDB item に巨大な raw body を保存していないこと。
- stacked branch である制約を PR 本文に明記すること。

## リスク

- 実 YouTube HTML へのネットワーク取得は行わず、公開 HTML に近い fixture で検証する。
- この branch は PR #6 を土台にした stacked worktree であり、PR #3〜#6 が merge されるまで main 向け差分には前段 PR の変更も含まれる。
