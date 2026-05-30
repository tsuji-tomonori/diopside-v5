# design v0.4 compliance baseline

状態: done

## 背景

ユーザーは `.workspace/plan-20260530.txt` への対応を依頼し、設計書は `.workspace/` にあると指定した。計画では `diopside_basic_design_v0.4.md` を正本として扱い、現在の `main` 実装を v0.4 へ寄せる方針が示されている。

## 目的

最初の PR として、機能追加を最小化し、v0.4 準拠管理の土台を repository 内に作る。

## タスク種別

ドキュメント更新

## スコープ

- `docs/design/diopside_basic_design_v0.4.md` を追加し、`.workspace` ではなく repo 内の正本として参照できるようにする。
- `docs/design/traceability-matrix.md` を追加し、v0.4 の主要項目と現 main の実装・テスト・状態を対応付ける。
- `reports/audit/design-v0.4-compliance-20260530.md` を追加し、P0/P1/P2 の差分監査結果を残す。
- README の設計根拠参照を `docs/design/diopside_basic_design_v0.4.md` に変更する。

## 非スコープ

- CDK 化、FastAPI 移行、Next.js static export 移行、HttpOnly cookie session 化などの実装移行はこの PR では行わない。
- 未実装 API / STATIC / BATCH の実装は後続 PR とし、この PR では traceability に状態を記録する。

## 計画

1. `origin/main` ベースの専用 worktree で作業する。
2. `.workspace/diopside_basic_design_v0.4.md` を `docs/design/` に正本化する。
3. README の設計根拠を `docs/design/diopside_basic_design_v0.4.md` に更新する。
4. v0.4 と README / 実装ファイル / テストを照合し、traceability matrix を作成する。
5. audit report と post-task report を作成する。
6. Markdown 差分検証を実行し、commit / push / PR / PR コメントまで進める。

## ドキュメント保守計画

本タスクはドキュメント更新が主成果物である。`docs/` は今回新設のため、既存 `docs/DOCS_STRUCTURE.md` は存在しない。`docs/design/` に v0.4 正本と traceability を置き、監査の時点情報は `reports/audit/` に分離する。

## 受け入れ条件

- [x] `docs/design/diopside_basic_design_v0.4.md` が存在し、v0.4 設計書の内容を保持している。
- [x] README の設計根拠が `.workspace/` ではなく `docs/design/diopside_basic_design_v0.4.md` を参照している。
- [x] `docs/design/traceability-matrix.md` に FR-GEN / FR-U / FR-A / FR-YT、NFR、API-001〜023、STATIC-001〜008、BATCH-001〜020、DynamoDB item schema、S3 bucket/path、CloudFront path、Worker、Frontend、Test/運用の行があり、各行に design_id / category / requirement / implementation_files / tests / status がある。
- [x] `reports/audit/design-v0.4-compliance-20260530.md` に v0.4 と現 main の差分、P0/P1/P2 の優先度、後続 PR 候補が記録されている。
- [x] 変更範囲に対して `git diff --check` と必要な npm 検証が実行され、未実施項目は理由を記録している。
- [x] PR 作成後、受け入れ条件確認コメントとセルフレビューコメントが日本語で投稿されている。

## 完了メモ

- PR: https://github.com/tsuji-tomonori/diopside-v5/pull/40
- 受け入れ条件確認コメント: https://github.com/tsuji-tomonori/diopside-v5/pull/40#issuecomment-4581284855
- セルフレビューコメント: https://github.com/tsuji-tomonori/diopside-v5/pull/40#issuecomment-4581285785
- 検証: `git diff --check` pass、`npm test` pass、`npm run verify` pass

## 検証計画

- `git diff --check`
- `npm test`
- 必要に応じて `npm run verify`

## PR レビュー観点

- v0.4 正本を実装に合わせて改変していないこと。
- traceability が未対応項目を実装済み扱いしていないこと。
- 実施していない検証を PR 本文・コメント・レポートで実施済み扱いしていないこと。

## リスク

- v0.4 の全項目は広いため、初版 traceability は詳細なコード証跡が不足する可能性がある。この場合は `未対応` / `差分あり` / `要追加監査` として扱い、後続 PR に分離する。
