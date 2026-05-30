# 作業完了レポート

保存先: `reports/working/20260530-1429-artifact-version-hash.md`

## 1. 受けた指示

- 主な依頼: `.workspace/plan-20260530.txt` の v0.4 設計準拠対応を、`main` pull 後に継続する。
- 成果物: DDB schema gap の追加対応、task md、検証結果、PR 更新用コメント、作業レポート。
- 形式・条件: Worktree Task PR Flow、task md、受け入れ条件、検証、commit、PR コメント、作業レポートを実施する。

## 2. 要件整理

| 要件ID | 指示・要件 | 重要度 | 対応状況 |
|---|---|---:|---|
| R1 | `Artifact` item を v0.4 versioned key で保存する | 高 | 対応 |
| R2 | `artifact_version` と `content_hash` を必ず付与する | 高 | 対応 |
| R3 | 既存 artifact の読み取り fallback を維持する | 高 | 対応 |
| R4 | schema contract test と docs/audit を更新する | 高 | 対応 |
| R5 | 実施した検証だけを記録する | 高 | 対応 |

## 3. 検討・判断したこと

- v0.4 の key は `VID#{video_id}` / `ARTIFACT#{artifact_type}#{artifact_version}` のため、新規 `put_artifact` は versioned key で保存する方針にした。
- 既存 DynamoDB には `VIDEO#{video_id}` / `ARTIFACT#{artifact_type}` の item が残る可能性があるため、`list_artifacts` と `get_artifact_by_id` は新旧 prefix の fallback を残した。
- `file_output` は実 body hash を `content_hash` として渡しているため、その値を優先する。未指定の既存呼び出しでは metadata 由来の deterministic hash を補完し、required field を満たす。
- artifact payload schema の完全固定や backfill は別タスクとして扱い、今回の範囲では key/version/hash contract に絞った。

## 4. 実施した作業

- `apps/shared/src/diopside_core/repository.py` に `artifact_item` と `artifact_content_hash` helper を追加した。
- `put_artifact` が `VID#{video_id}` / `ARTIFACT#{artifact_type}#{artifact_version}` で保存するように更新した。
- `list_artifacts` と `get_artifact_by_id` が新 shape と旧 `VIDEO#...` shape の両方を扱えるようにした。
- `tests/test_repository_schema_contract.py` に v0.4 Artifact shape と旧 shape fallback の contract test を追加した。
- `tests/test_core_pipeline.py` / `tests/test_static_exporter.py` を対象検証に含め、既存 `file_output` 経路が壊れていないことを確認した。
- `README.md` と `docs/design/dynamodb-schema-audit.md` の `Artifact` 記述を実装済み状態へ同期した。

## 5. 成果物

| 成果物 | 形式 | 内容 | 指示との対応 |
|---|---|---|---|
| `apps/shared/src/diopside_core/repository.py` | Python | `Artifact` versioned writer/list/get | DDB schema gap 対応 |
| `tests/test_repository_schema_contract.py` | Python test | v0.4 shape と旧 shape fallback contract | 検証可能条件 |
| `README.md` | Markdown | DDB item schema 表の同期 | docs maintenance |
| `docs/design/dynamodb-schema-audit.md` | Markdown | audit 状態を部分実装へ更新 | traceability |
| `tasks/do/20260530-1429-artifact-version-hash.md` | Markdown | task state と受け入れ条件 | Worktree Task PR Flow |

## 6. 指示へのfit評価

| 評価軸 | 評価 | 理由 |
|---|---:|---|
| 指示網羅性 | 5 | v0.4 plan の DDB schema gap を 1 項目進め、task/report/検証まで実施した |
| 制約遵守 | 5 | main pull、worktree作業、task md、未実施検証の非記載を守った |
| 成果物品質 | 4 | versioned key と hash contract は追加済み。backfill と artifact payload schema 完全固定は後続課題 |
| 説明責任 | 5 | fallback hash と未対応範囲を docs/task/report に記録した |
| 検収容易性 | 5 | 受け入れ条件と検証コマンドを明示した |

総合fit: 4.8 / 5.0（約96%）
理由: 今回の範囲の主要要件は満たしたが、既存 DynamoDB artifact item の backfill と artifact payload schema の完全固定は後続課題として残る。

## 7. 実行した検証

- `python3 -m py_compile apps/shared/src/diopside_core/repository.py`: pass
- `PYTHONPATH=apps/shared/src python3 -m pytest tests/test_repository_schema_contract.py`: fail -> 旧 key 期待値を更新後 pass（21 tests）
- `PYTHONPATH=apps/shared/src:apps/workers/static-exporter/src python3 -m pytest tests/test_core_pipeline.py tests/test_static_exporter.py`: pass（50 tests）
- `node tools/check-docs-consistency.mjs`: pass
- `git diff --check`: pass
- `npm run verify`: pass（122 tests、build、package、local e2e）

## 8. 未対応・制約・リスク

- 既存 DynamoDB artifact item の backfill は未実施。
- `content_hash` 未指定時の fallback hash は metadata 由来であり、artifact body そのものの hash ではない。
- artifact payload schema の完全固定は別タスク。
