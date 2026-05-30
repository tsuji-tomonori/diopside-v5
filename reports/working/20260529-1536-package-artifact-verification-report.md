# package artifact検証 作業レポート

## 受けた指示

- `.workspace/` 配下の設計書と 2026-05-29 の plan に基づいて作業する。
- `main` から pull してから、P4-02 package artifact検証を進める。
- Worktree Task PR Flow に従い、task、検証、PR コメントまで行う。

## 要件整理

- `api.zip` と `static-exporter.zip` に shared code が含まれることを CI で確認する。
- 生成 zip に不要な Python cache が入らないことを CI で確認する。
- P4-01 で追加した CI は `npm run verify` を実行するため、`npm test` に package artifact contract を追加すれば CI 対象になる。

## 検討・判断

- `tools/package_deploy.py` を直接呼ぶ pytest を追加し、実際の package 出力 zip を検査する。
- 現行の cache 除外は `__pycache__` と `.pyc` のみだったため、`.pytest_cache`、`.mypy_cache`、`.ruff_cache`、`.pyo` も明示的に除外した。
- README は既に `npm run package:deploy` と `api.zip` / `static-exporter.zip` を説明しているため、手順ドキュメント更新は不要と判断した。

## 実施作業

- `tools/package_deploy.py` に package 対象判定を追加した。
- `tests/test_package_deploy.py` を追加し、deploy package の zip contract を検証するようにした。
- P4-02 の task md を作成した。

## 成果物

- `tools/package_deploy.py`
- `tests/test_package_deploy.py`
- `tasks/do/20260529-1536-package-artifact-verification.md`
- PR: https://github.com/tsuji-tomonori/diopside-v5/pull/34
- 受け入れ条件確認コメント: https://github.com/tsuji-tomonori/diopside-v5/pull/34#issuecomment-4570658175
- セルフレビューコメント: https://github.com/tsuji-tomonori/diopside-v5/pull/34#issuecomment-4570660362

## 検証

- `git diff --check`: 成功
- `PYTHONPATH=apps/shared/src:apps/api/src:apps/workers/static-exporter/src python3 -m pytest tests/test_package_deploy.py`: 2 passed
- `npm test`: 61 passed
- `npm run verify`: 成功
  - `npm test`: 61 passed
  - `npm run build`: 成功
  - `npm run package:deploy`: 成功
  - `npm run e2e:local`: 成功
- GitHub Actions `CI / npm verify`: 成功

## fit 評価

- P4-02 の `api.zip` / `static-exporter.zip` の shared code 同梱と cache 除外の要求に対応した。
- 追加テストは `npm test` に含まれるため、P4-01 の GitHub Actions CI の `npm run verify` で実行される。

## 未対応・制約・リスク

- 実 AWS deploy artifact の S3 upload や Lambda 上での import 確認は P4-02 の対象外のため未実施。
- GitHub Apps による PR top-level comment は 403 のため、`gh pr comment` で代替した。
