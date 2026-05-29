# PR コメントに基づく post-deploy smoke 補強

## 背景

ユーザーから「PRのコメントをもとに修正して」と依頼された。

PR #2 の GraphQL reviewThreads は 0 件で、inline review comment も存在しない。一方で top-level PR コメントのセルフレビューには、deploy 後に確認すべき suggestion が複数残っている。

## 目的

PR コメントに記載された post-deploy 確認 suggestion を、実行可能な smoke ツールと README 手順へ落とし込み、deploy 後に実データ E2E を確認できる状態を強くする。

## スコープ

- CloudFront/public API/public data contract の post-deploy smoke。
- 管理 API の job 起動、job 一覧、job 詳細確認。
- README への実行手順追記。
- 検証と作業レポート。

## タスク種別

機能追加

## 受け入れ条件

- [x] PR コメントの suggestion が実行手順またはツールに反映されている。
- [x] post-deploy smoke ツールが `DIOPSIDE_E2E_BASE_URL` を受け取り、public UI/API/data を確認できる。
- [x] admin token/CSRF がある場合、管理 job 起動、job list、job detail を確認できる。
- [x] public data contract checker を post-deploy 取得データに適用できる。
- [x] README に post-deploy smoke の使い方を記載する。
- [x] `npm test`、`npm run verify`、`git diff --check` が成功する。
- [x] 作業レポートを `reports/working/` に追加する。
- [x] PR に対応結果をコメントする。

## 検証計画

- `npm test`
- `npm run verify`
- `git diff --check`

## 状態

done
