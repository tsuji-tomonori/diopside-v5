# package artifact検証

状態: done

## 背景

`.workspace/plan-20260529.txt` の P4-02 に従い、`api.zip` と `static-exporter.zip` に shared code が含まれ、不要な cache が入らないことを CI で確認する。

## 目的

deploy package の zip contract をテストで固定し、PR CI の `npm run verify` 内で package artifact の欠落や cache 混入を検出できるようにする。

## タスク種別

test / CI quality gate

## スコープ

- `tests/`
- 必要に応じて `tools/package_deploy.py`

## 計画

1. `tools/package_deploy.py` の出力 zip 構造を確認する。
2. `api.zip` と `static-exporter.zip` の shared code 同梱を検証する pytest を追加する。
3. `__pycache__`、`.pyc`、pytest cache など不要 cache が zip に入らないことを検証する。
4. `npm test` / `npm run verify` で CI 経由の検証対象に入ることを確認する。
5. 作業レポート、commit、PR、受け入れ条件コメント、セルフレビューまで完了する。

## ドキュメント保守方針

CI/テスト追加であり README 手順の変更は不要の見込み。package artifact の検証内容は task md と作業レポートに残す。

## 受け入れ条件

- `api.zip` に `diopside_api` と `diopside_core` が含まれることをテストで確認する。
- `static-exporter.zip` に `static_exporter` と `diopside_core` が含まれることをテストで確認する。
- 生成 zip に `__pycache__` や `.pyc` が含まれないことをテストで確認する。
- 上記テストが `npm test`、ひいては CI の `npm run verify` で実行される。
- 変更範囲に見合う検証が成功する。

## 検証計画

- `git diff --check`
- targeted pytest
- `npm test`
- `npm run verify`

## 完了結果

- PR: https://github.com/tsuji-tomonori/diopside-v5/pull/34
- 受け入れ条件確認コメント: https://github.com/tsuji-tomonori/diopside-v5/pull/34#issuecomment-4570658175
- セルフレビューコメント: https://github.com/tsuji-tomonori/diopside-v5/pull/34#issuecomment-4570660362
- GitHub Actions `CI / npm verify`: 成功

## 検証結果

- `git diff --check`: 成功
- `PYTHONPATH=apps/shared/src:apps/api/src:apps/workers/static-exporter/src python3 -m pytest tests/test_package_deploy.py`: 2 passed
- `npm test`: 61 passed
- `npm run verify`: 成功
- GitHub Actions `CI / npm verify`: 成功

## リスク

- 実 AWS deploy artifact のアップロードや Lambda 上での import 確認は P4-02 の対象外。zip の静的 contract と CI 実行で確認する。
