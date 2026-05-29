# timestamp 候補生成の品質強化

状態: done
タスク種別: 機能追加

## 背景

`.workspace/plan-20260529.txt` の Phase 1 では、P1-12 として description timestamp、chat burst、keyword spike を統合し、重複排除と score 順表示を行うことが求められている。基本設計書 v0.4 でも、概要欄・チャット・盛り上がりからタイムスタンプ候補を生成する方針になっている。

## 目的

`build_timestamp_candidates` を強化し、description 由来、chat burst 由来、keyword spike 由来の候補を一つの候補リストに統合する。近接 offset の重複を代表候補へまとめ、score の高い順に表示できる deterministic な結果へ固定する。

## スコープ

- 対象: timestamp candidate helper、static export / rebuild artifacts 経路、unit test、README、作業レポート。
- 対象 P1: P1-12。
- 対象外: UI 表示完成、timestamp artifact の別 JSON export、実 YouTube / AWS / CloudFront 疎通。

## 実施計画

1. 既存 `build_timestamp_candidates` の出力 schema と利用箇所を確認する。
2. description timestamp、chat burst、keyword spike を candidate として統合する。
3. 近接 offset / source の重複をまとめ、score 順に並べる。
4. 候補に evidence terms / message count / source を保持し、既存 public detail と互換を保つ。
5. unit test と README を更新し、必要な検証を実行する。

## ドキュメント保守計画

- README に timestamp 候補の統合・重複排除・score 順方針を追記する。

## 受け入れ条件

- [x] description timestamp が候補化され、label と source が保持される。
  - 根拠: `tests/test_core_pipeline.py::test_timestamp_candidates_merge_sources_and_sort_by_score`。
- [x] chat burst が候補化され、message_count と score が付く。
  - 根拠: 同 test の `merged_sources` / `message_count`。
- [x] keyword spike が候補化され、evidence_terms と score が付く。
  - 根拠: `tests/test_core_pipeline.py::test_timestamp_candidates_include_keyword_spike` と merge/sort test。
- [x] 近接 offset の重複候補が代表候補へ統合される。
  - 根拠: merge/sort test で 125 秒近辺の description/chat_burst/keyword_spike が 1 候補へ統合されることを確認。
- [x] 候補一覧が score 降順、同点時 offset 昇順で deterministic に並ぶ。
  - 根拠: merge/sort test。
- [x] static export / rebuild artifacts の timestamp 出力が強化後の候補を使う。
  - 根拠: `export_public_data` と `rebuild_artifacts` は既存どおり `build_timestamp_candidates` を参照し、targeted pytest と `npm test` が成功。
- [x] README に timestamp 候補生成方針が反映されている。
- [x] 変更範囲に応じた tests と `npm run verify` が成功する。

## 検証計画

- `git diff --check`
- `python3 -m py_compile apps/shared/src/diopside_core/artifacts.py tests/test_core_pipeline.py tests/test_static_exporter.py`
- `PYTHONPATH=apps/shared/src:apps/api/src:apps/workers/static-exporter/src python3 -m pytest tests/test_core_pipeline.py tests/test_static_exporter.py`
- `npm test`
- `npm run verify`

## 検証結果

- `git diff --check`: pass
- `python3 -m py_compile apps/shared/src/diopside_core/artifacts.py tests/test_core_pipeline.py tests/test_static_exporter.py`: pass
- `PYTHONPATH=apps/shared/src:apps/api/src:apps/workers/static-exporter/src python3 -m pytest tests/test_core_pipeline.py tests/test_static_exporter.py`: 初回 fail（旧仕様の keyword_spike 単独 assertion）-> test を統合仕様へ更新後 pass（26 passed）
- `npm test`: pass（35 passed）
- `npm run verify`: pass

## PRレビュー観点

- timestamp の source / score / evidence が review 可能な形で残ること。
- 重複排除が description 候補を不必要に消さないこと。
- public detail の timestamp contract を壊していないこと。
- benchmark 期待語句や dataset 固有分岐を実装に入れていないこと。
- stacked branch である制約を PR 本文に明記すること。

## リスク

- この branch は PR #10 を土台にした stacked worktree であり、PR #3〜#10 が merge されるまで main 向け差分には前段 PR の変更も含まれる。
- 実視聴データでの timestamp 品質評価は未実施。
