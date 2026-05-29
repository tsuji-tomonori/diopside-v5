# replay parser golden fixtures 作業レポート

## 受けた指示

- `.workspace/` 配下の設計書と 2026-05-29 の plan に基づいて作業する。
- `main` から pull してから、P4-04 replay parser golden fixtures を進める。
- Worktree Task PR Flow に従い、task、検証、PR コメントまで行う。

## 要件整理

- 既知 renderer、paid、sticker、emoji、unknown、offset 実構造の fixture を追加する。
- 追加テストは `npm test`、ひいては CI の `npm run verify` で実行される必要がある。

## 検討・判断

- `data/fixtures/replay-parser/golden-actions.json` に replay action の代表構造を置いた。
- `data/fixtures/replay-parser/golden-expected.json` に normalized output の重要 projection を置いた。
- full raw 全フィールド一致ではなく、parser contract として重要な message type、renderer type、offset、paid/sticker/emoji/unknown 保持を固定した。

## 実施作業

- replay parser golden input fixture を追加した。
- replay parser expected projection fixture を追加した。
- `tests/test_core_pipeline.py` に golden fixture contract test を追加した。
- P4-04 の task md を作成した。

## 成果物

- `data/fixtures/replay-parser/golden-actions.json`
- `data/fixtures/replay-parser/golden-expected.json`
- `tests/test_core_pipeline.py`
- `tasks/do/20260529-1554-replay-parser-golden-fixtures.md`
- PR: https://github.com/tsuji-tomonori/diopside-v5/pull/36
- 受け入れ条件確認コメント: https://github.com/tsuji-tomonori/diopside-v5/pull/36#issuecomment-4570786601
- セルフレビューコメント: https://github.com/tsuji-tomonori/diopside-v5/pull/36#issuecomment-4570789230

## 検証

- `git diff --check`: 成功
- `PYTHONPATH=apps/shared/src:apps/api/src:apps/workers/static-exporter/src python3 -m pytest tests/test_core_pipeline.py -k replay_parser_golden`: 1 passed
- `npm test`: 63 passed
- `npm run verify`: 成功
  - `npm test`: 63 passed
  - `npm run build`: 成功
  - `npm run package:deploy`: 成功
  - `npm run e2e:local`: 成功
- GitHub Actions `CI / npm verify`: 成功

## fit 評価

- P4-04 の replay parser golden fixtures 追加要求に対応した。
- 追加テストは `npm test` に含まれるため、P4-01 の GitHub Actions CI の `npm run verify` で実行される。

## 未対応・制約・リスク

- 実 YouTube からの新規データ取得は行わず、既知構造を再現した fixture による parser contract 固定に限定した。
- GitHub Apps による PR top-level comment は 403 のため、`gh pr comment` で代替した。
