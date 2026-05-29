# replay parser golden fixtures

状態: done

## 背景

`.workspace/plan-20260529.txt` の P4-04 に従い、既知 renderer、paid、sticker、emoji、unknown、offset 実構造の replay parser fixture を追加する。

## 目的

YouTube replay chat の代表 renderer と offset 構造を golden fixture として固定し、parser の退行を CI で検出できるようにする。

## タスク種別

test fixture / parser contract

## スコープ

- `data/fixtures/replay-parser/`
- `tests/test_core_pipeline.py`

## 計画

1. 既存 replay parser とテストを確認する。
2. replay action fixture と期待 projection fixture を追加する。
3. text / paid / sticker / ticker paid / emoji / unknown / offset の normalized output を検証する。
4. `npm test` / `npm run verify` で CI 対象に入ることを確認する。
5. 作業レポート、commit、PR、受け入れ条件コメント、セルフレビューまで完了する。

## ドキュメント保守方針

テスト fixture 追加であり README 更新は不要の見込み。fixture の範囲は task md と作業レポートに残す。

## 受け入れ条件

- 既知 replay renderer の text / paid / paid sticker / ticker paid を fixture で検証する。
- emoji run の `emoji_id`、label、custom emoji flag を fixture で検証する。
- unknown renderer が `unknown` message と `parse_warning` と raw renderer を保持することを fixture で検証する。
- replay action outer offset と renderer 内 offset の両方を fixture で検証する。
- 追加テストが `npm test`、ひいては CI の `npm run verify` で実行される。
- 変更範囲に見合う検証が成功する。

## 検証計画

- `git diff --check`
- targeted pytest
- `npm test`
- `npm run verify`

## 完了結果

- PR: https://github.com/tsuji-tomonori/diopside-v5/pull/36
- 受け入れ条件確認コメント: https://github.com/tsuji-tomonori/diopside-v5/pull/36#issuecomment-4570786601
- セルフレビューコメント: https://github.com/tsuji-tomonori/diopside-v5/pull/36#issuecomment-4570789230
- GitHub Actions `CI / npm verify`: 成功

## 検証結果

- `git diff --check`: 成功
- `PYTHONPATH=apps/shared/src:apps/api/src:apps/workers/static-exporter/src python3 -m pytest tests/test_core_pipeline.py -k replay_parser_golden`: 1 passed
- `npm test`: 63 passed
- `npm run verify`: 成功
- GitHub Actions `CI / npm verify`: 成功

## リスク

- 実 YouTube からの新規データ取得は行わず、既知構造を再現した fixture による parser contract 固定に限定する。
