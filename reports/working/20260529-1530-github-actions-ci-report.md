# GitHub Actions CI追加 作業レポート

## 受けた指示

- `.workspace/` 配下の設計書と 2026-05-29 の plan に基づいて作業する。
- `main` から pull してから、P4-01 GitHub Actions CI追加を進める。
- リポジトリの Worktree Task PR Flow に従い、task、検証、PR コメントまで行う。

## 要件整理

- PR で `npm run verify`、CloudFormation parse/contract、public contract、unit tests が実行される CI を追加する。
- 現在の `npm run verify` は `npm test`、build、package、local e2e を実行する。
- `npm test` は CloudFormation contract、public contract、unit tests を含む。

## 検討・判断

- GitHub Actions workflow は `pull_request` と `main` push で起動する。
- Runtime は `package.json` の engines に合わせて Node 22 / Python 3.13 を指定した。
- `npm ci` 後に `npm run verify` を実行する 1 job 構成にした。
- CI runner には Python テスト依存が無いため、`requirements-dev.txt` を追加し、`pytest`、`PyYAML`、`boto3`、`botocore` を固定した。

## 実施作業

- `.github/workflows/ci.yml` を追加した。
- `requirements-dev.txt` を追加した。
- CI job で checkout、Node setup、Python setup、`npm ci`、Python dev 依存導入、`npm run verify` を実行するようにした。
- P4-01 の task md を作成した。
- PR #33 作成後、GitHub Actions の失敗ログを確認し、Python dev 依存不足を修正した。
- PR 本文、受け入れ条件確認コメント、セルフレビューコメントを実 CI 成功後の内容へ更新した。

## 成果物

- `.github/workflows/ci.yml`
- `requirements-dev.txt`
- `tasks/do/20260529-1530-github-actions-ci.md`
- PR: https://github.com/tsuji-tomonori/diopside-v5/pull/33
- 受け入れ条件確認コメント: https://github.com/tsuji-tomonori/diopside-v5/pull/33#issuecomment-4570608154
- セルフレビューコメント: https://github.com/tsuji-tomonori/diopside-v5/pull/33#issuecomment-4570609947

## 検証

- `git diff --check`: 成功
- `python3 -c "import boto3, botocore, pytest, yaml; print(boto3.__version__, botocore.__version__, pytest.__version__, yaml.__version__)"`: 成功
- `npm test`: 59 passed
- `npm run verify`: 成功
  - `npm test`: 59 passed
  - `npm run build`: 成功
  - `npm run package:deploy`: 成功
  - `npm run e2e:local`: 成功
- GitHub Actions `CI / npm verify`: 成功

補足:

- `python3 -m pip install -r requirements-dev.txt` はローカルでは依存がすべて満たされていることを確認した後、環境固有の `pyenv` shim 書き込み不可で exit 1 になった。CI の hosted runner では同 step が成功した。

## fit 評価

- plan P4-01 の PR CI、`npm run verify`、CloudFormation contract、public contract、unit tests 実行要求に対応した。
- 実 GitHub Actions 上でも `CI / npm verify` の成功を確認した。

## 未対応・制約・リスク

- 実 AWS deploy / CloudFront 実環境確認は P4-01 の対象外のため未実施。
- GitHub Actions の annotation として `actions/checkout@v4`、`actions/setup-node@v4`、`actions/setup-python@v5` の Node.js 20 runtime deprecation warning が出ている。CI は成功済みだが、将来 action version 更新の検討余地がある。
