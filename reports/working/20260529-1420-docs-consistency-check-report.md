# docs consistency check 作業レポート

## 受けた指示

- `.workspace/` 配下の設計書と 2026-05-29 の plan に基づいて作業する。
- `main` から pull してから、P4-07 docs consistency を進める。
- Worktree Task PR Flow に従い、task、検証、PR コメントまで行う。

## 要件整理

- README と設計書で、実装済み job/API/path/schema が一致していることをチェックできる必要がある。
- CI の `npm run verify` に含まれる `npm test` で退行検出できる必要がある。
- `.workspace` は gitignore 対象のため、CI では tracked README を検証し、ローカルでは `DIOPSIDE_DESIGN_DOC` 指定時に設計書の主要前提も確認する。

## 検討・判断

- 実装済み契約は `apps/api/src/diopside_api/handler.py`、`apps/workers/static-exporter/src/static_exporter/handler.py`、`apps/workers/static-exporter/src/static_exporter/pipeline.py`、`apps/shared/src/diopside_core/chat.py` を正とした。
- README に実装済み API route、response schema、public data path、worker job type、normalized chat key を明記した。
- `.workspace/diopside_basic_design_v0.4.md` は repository に commit しない方針を維持し、環境変数で指定された場合に補助検証する設計にした。

## 実施作業

- `tools/check-docs-consistency.mjs` を追加した。
- `npm test` に docs consistency check を組み込んだ。
- README の実装済み API/schema、public data schema、worker job、normalized chat schema 記述を更新した。
- P4-07 の task md を作成した。
- PR #39 を作成し、受け入れ条件確認とセルフレビューを top-level comment として投稿した。
- GitHub Apps の comment 投稿は 403 のため、`gh pr comment` にフォールバックした。

## 成果物

- `tools/check-docs-consistency.mjs`
- `README.md`
- `package.json`
- `tasks/done/20260529-1420-docs-consistency-check.md`
- PR: https://github.com/tsuji-tomonori/diopside-v5/pull/39
- 受け入れ条件コメント: https://github.com/tsuji-tomonori/diopside-v5/pull/39#issuecomment-4570953542
- セルフレビューコメント: https://github.com/tsuji-tomonori/diopside-v5/pull/39#issuecomment-4570955341

## 検証

- `git diff --check`: 成功
- `node tools/check-docs-consistency.mjs`: 成功
- `DIOPSIDE_DESIGN_DOC=/home/t-tsuji/project/diopside-v5/.workspace/diopside_basic_design_v0.4.md node tools/check-docs-consistency.mjs`: 成功
- `npm test`: 70 passed
- `npm run verify`: 成功
  - `npm test`: 70 passed
  - `npm run build`: 成功
  - `npm run package:deploy`: 成功
  - `npm run e2e:local`: 成功
- GitHub Actions `CI / npm verify`: 成功

## fit 評価

- P4-07 の docs consistency 要求に対応し、README と実装済み契約の差分を CI 対象で検出できるようにした。
- `.workspace` 設計書は gitignore 対象のため CI で直接検証しないが、ローカルでは明示指定により主要設計前提を検証できる。
- 総合fit: 4.5 / 5.0。主要要件は満たしたが、設計書本文が tracked file ではない制約により CI の直接検証対象は README に限定される。

## 未対応・制約・リスク

- `.workspace/diopside_basic_design_v0.4.md` は `.gitignore` 対象のため PR に含めていない。
- docs consistency check は実装済み契約の存在確認に限定し、完全な schema validation は既存の `tools/check-public-contract.mjs` と Python tests に委ねる。
- GitHub Apps の top-level comment は 403 で利用できなかったため、`gh pr comment` で代替した。
