# Repository Agent Instructions

このリポジトリで作業する Codex / AI agent は、以下を守る。

## 共通
- 指定 skill が利用可能一覧に出ない場合も、リポジトリローカルの明示ルールとして該当 `SKILL.md` を読む。
- `git diff`、`git status`、変更ファイル一覧、ステージ済み差分、PR 内容、作業レポートから文面を作る場合も該当 skill を適用する。
- `reports/working/*.md`、`reports/bugs/*.md`、同等の作業・障害レポートが関係する場合は本文を確認し、commit message / PR 本文に要点を反映する。
- 実施していないテスト、確認、検証を実施済みとして書かない。

## Completion Discipline
- 常時適用: 完了条件を満たすまで「完了」と報告しない。
- 実作業前にチェックリストと Done 条件（deliverables + validations）を明示する。
- 計画のみ依頼でない限り、計画作成で止まらず実装・検証まで進める。
- 検証失敗時は修正して再実行し、未解決失敗を残したまま完了扱いしない。
- ブロック時は「完了」ではなく「blocked / partially complete」として報告する。
- 不可逆操作（送金、注文、予約確定、破壊的削除など）は最終実行前に確認を要求する。
- 長時間・複雑タスクでは以下 skills の併用を推奨する。
  - `skills/task-completion-guardian/SKILL.md`
  - `skills/verification-repair-loop/SKILL.md`
  - `skills/milestone-exec-runner/SKILL.md`
  - `skills/blocker-recovery/SKILL.md`
  - `skills/completion-status-reporter/SKILL.md`

## Worktree Task PR Flow
- 常時適用: このリポジトリでファイル編集、コマンド実行、調査、検証、ドキュメント作成、commit、PR 作成などの実作業を伴う依頼は、ユーザーが明示しなくても `Worktree Task PR Flow` の対象として扱う。
- 対象: 「worktree を作成して作業」「task md を作成してから作業」「git commit + PR create to main」「PR 作成は GitHubApps / GitHub Apps を利用」など、worktree から main 向け PR まで進める依頼、および通常のリポジトリ実作業。
- 例外: 純粋な質問回答、計画のみの依頼、ユーザーが明示的に worktree / commit / PR を行わないよう指示した場合は、実施範囲に合わせてこの workflow の実行ステップを調整し、理由を報告する。
- 上記の依頼を agent が守るよう `skills` や `AGENTS.md` で設定されているか確認し、不足時に対応する依頼も同じ workflow の対象として扱う。
- 必読: `skills/worktree-task-pr-flow/SKILL.md`
- GitHub Apps / PR 作成・更新・コメントを行う場合は `skills/github-apps-pr-operator/SKILL.md` も必読とし、GitHub Apps を優先する。
- Taskfile のコマンド実行、Taskfile 経由の検証、dev server / smoke / benchmark / docs check を扱う場合は `skills/taskfile-command-runner/SKILL.md` も必読とする。
- 作業ブランチは原則 `origin/main` から専用 worktree として作成し、元 worktree の未追跡・未コミット変更を混ぜない。
- 作業前に `tasks/todo/`, `tasks/do/`, `tasks/done/` を確認または作成し、着手する task md を `tasks/do/` に置く。
- task md には作業前に「受け入れ条件」（ユーザー表記が「受け例条件」の場合も同義として扱う）を明記する。
- task md は状態に応じて `tasks/todo/`、`tasks/do/`、`tasks/done/` の間で移動し、完了時は `状態: done` または同等の状態記載へ更新する。
- PR 作成後、task md の受け入れ条件を満たしたか確認し、日本語の PR コメントとして結果を記載する。未検証・未達の項目を満たした扱いにしない。
- PR コメントまで完了してから task md を `tasks/done/` に移動し、その完了更新も同じ PR branch に commit / push する。
- PR 作成は GitHub Apps を優先する。利用できない場合は blocked として理由を報告し、代替手段を使う場合も `skills/japanese-pr-title-comment/SKILL.md` に従う。

## Git Commit Message
- 対象: Git commit message、コミットメッセージ、コミットコメント、git comment、`git commit`。ユーザーの「コメント」も Git 文脈では commit message と扱う。
- 必読: `skills/japanese-git-commit-gitmoji/SKILL.md`
- commit 前に `git diff --cached --name-only` でステージ済みファイルを確認する。
- 変更目的が複数に分かれる場合は、1 commit にまとめず目的別分割を検討する。
- 1 行目は原則 `<emoji> <type>(<scope>): <日本語の要約>`。scope 不要または不明なら省略可。
- 既存 commit message がこの形式でなくても、新規 commit ではこのルールを優先する。

## Pull Request Title and Comment
- 対象: Pull Request、PR、PR タイトル、PR 本文、PR コメント、レビューコメント、`gh pr create`。
- 必読: `skills/japanese-pr-title-comment/SKILL.md`
- GitHub Apps 操作を伴う場合は `skills/github-apps-pr-operator/SKILL.md` も必読とし、通常の PR 作成・更新・top-level comment ではユーザー確認を追加で求めず workflow を進める。
- PR タイトル、PR 本文、PR コメント、レビューコメントは日本語で書く。
- ブランチ名、ファイルパス、コマンド、API 名、型名、関数名、issue 番号は原文維持可。
- PR 本文は `.github/pull_request_template.md` の見出しを優先する。

## PR Self Review
- 対象: PR 作成、PR 更新、PR 本文更新、PR コメント、レビューコメント、PR のセルフレビュー、`git diff` や作業レポートからレビュー観点を作る作業。
- 必読: `skills/pr-review-self-review/SKILL.md`
- PR を作成または更新するたびに、変更差分・PR本文・検証結果を確認し、日本語のセルフレビュー結果を PR の top-level comment として記載する。
- セルフレビューでは特に `docs と実装の同期`、`変更範囲に見合うテスト`、`RAG の根拠性・認可境界を弱めていないこと`、`benchmark 期待語句・QA sample 固有値・dataset 固有分岐を実装へ入れていないこと` を強く確認する。
- 未実施の検証、未確認の CI、GitHub Apps や push の制約は実施済み扱いせず、PR コメントと PR 本文に理由とリスクを明記する。
- blocking 指摘がある場合は、修正または blocked / partially complete として明示するまで「完了」扱いにしない。

## Post Task Work Report
- 対象: ファイル編集、コマンド実行、調査、検証、ドキュメント作成など、リポジトリへの実作業。ユーザーが「レポート不要」「reports には出さないで」などと明示した場合のみ省略可。
- 必読: `skills/post-task-fit-report/SKILL.md`
- 主作業完了後かつ最終回答前に、タスクごとに作業完了レポートを 1 件残す。
- 保存先は原則 `reports/working/` の Markdown。なければ作成する。
- ファイル名は `YYYYMMDD-HHMM-<task-summary>.md`。summary は ASCII 小文字とハイフンで短く表す。
- レポートには、受けた指示、要件整理、検討・判断の要約、実施作業、成果物、指示への fit 評価、未対応・制約・リスクを簡潔に含める。
- 最終回答では生成したレポートの保存先パスを明示する。

## Implementation Docs Maintenance
- 対象: 実装、修正、リファクタ、設定変更、API 変更、運用手順変更など、コードまたは挙動に影響する作業。
- 必読（必要に応じて）: `skills/implementation-docs-maintainer/SKILL.md`
- 作業前後に、README、`docs/`、API 例、運用手順、`AGENTS.md` への影響を確認する。
- ドキュメント更新が必要なら同じ作業範囲で更新する。不要なら最終回答または作業レポートで理由を簡潔に示す。
- `docs/` を更新する場合は下記 Docs Update Policy を優先する。

## No Mock Product UI
- 対象: 本番 UI、API レスポンス整形、hooks、stores、ユーザー可視の画面・管理画面・操作部品の実装またはレビュー。
- 必読: `skills/no-mock-product-ui/SKILL.md`
- 本番経路では、固定フォルダ、固定件数、固定容量、固定日付、架空ユーザー、架空グループ、demo fallback、未実装操作を実データのように表示しない。
- 表示値は props、API レスポンス、永続化状態、設定、または明示的な empty/loading/error/permission state に由来させる。
- テスト fixture、Storybook、visual regression mock、ローカル開発 seed は、本番コンポーネントの fallback と分離されている場合のみ許容する。
- API や実データが存在しない値は、架空値で埋めず「未設定」「利用不可」などの正直な状態にする。推定値を表示する場合は、推定であることと根拠を UI または PR 本文に明記する。

## Implementation Test Selection
- 対象: 実装、修正、リファクタ、設定変更、ドキュメント変更の完了前。
- 必読: `skills/implementation-test-selector/SKILL.md`
- 検証コマンドの実行・再実行・権限委譲・未実施理由の報告には `skills/repository-test-runner/SKILL.md` も適用する。
- Taskfile 経由の検証コマンドには `skills/taskfile-command-runner/SKILL.md` も適用する。
- `git diff --name-only` などで変更範囲を確認し、最小十分な lint、typecheck、test、build、smoke、docs check を選ぶ。
- 実行できる検証は実行する。省略した場合は、コマンド名と理由を最終回答または作業レポートに記載する。

## Permission Delegation and Confirmation Suppression
- 対象: GitHub Apps 操作、Taskfile コマンド、テスト・lint・typecheck・build・docs check・smoke・benchmark の実行。
- 必読: `skills/github-apps-pr-operator/SKILL.md`、`skills/taskfile-command-runner/SKILL.md`、`skills/repository-test-runner/SKILL.md`
- repository 内で定義された Taskfile / npm scripts / 検証コマンドを実行する前に、実際に解決されるコマンド本文を確認する。
- `require_escalated` を使う再実行は自動化しない。必要性・影響範囲・実行コマンド（prefix を含む）を明示して、都度ユーザー確認を取る。
- 再利用可能な `prefix_rule` は、読み取り専用かつコマンド本文が固定で安全性を確認できるものに限定し、Taskfile や package script に委譲する曖昧な prefix は許可しない。
- 破壊的削除、履歴改変、PR merge/close、deploy/release/bootstrap、production/external state を変更する操作は、従来どおり確認必須とする。

## Security Access-Control Review
- 対象: API route、middleware、認証・認可、RBAC、所有者境界、管理 API、外部公開設定、機微データを返す schema/store の追加・変更。
- 必読: `skills/security-access-control-reviewer/SKILL.md`
- 新規 route は、認証境界、route-level permission、所有者・担当者制約、返却 schema の機微フィールド、store の list/get/update/delete 範囲を確認する。
- `apps/api/src/app.ts` または `apps/api/src/routes/` の保護対象 route を追加・変更する場合は、`apps/api/src/security/access-control-policy.test.ts` の静的 policy も更新し、API test を実行する。
- 意図的な public endpoint は、理由、返却データが非機微である根拠、濫用対策を PR 本文または作業レポートに明記する。

## Docs Update Policy for `docs/`
- 更新依頼では `skills/docs-swebok-template-writer/SKILL.md` を参照し、SWEBOK-lite の体裁に合わせる。
- 要求は原子性（1 要件 = 1 検証可能条件）を保つ。
- 要件ドキュメントは「1 要件 = 1 ファイル」とし、受け入れ条件を同一ファイル内に明記する。
- 新規/大規模更新は `docs/DOCS_STRUCTURE.md` の構成方針に合わせる。
- 既存単一ファイル（例: `REQUIREMENTS.md`, `ARCHITECTURE.md`）を更新する場合も、将来移行しやすいように種別メタ情報と要件IDを維持する。
- 以降の docs 修正では、可能な限り REQ/ARC/DES/OPS のディレクトリに分割して追記・修正する。
