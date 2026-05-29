# 履歴/お気に入りUI

状態: do

## 背景

`.workspace/plan-20260529.txt` の P3-04 に従い、localStorage で閲覧履歴とお気に入りを保存し、UI から再表示できるようにする。

## 目的

既に保存している `favorites` と `history` を、ホーム上の導線から再表示・再選択できるようにする。

## タスク種別

UI 改善

## スコープ

- `apps/web/public/index.html`
- `apps/web/public/app.js`
- `apps/web/public/styles.css`

## 計画

1. 既存の localStorage 保存処理を確認する。
2. お気に入りと閲覧履歴の UI section を追加する。
3. 保存済み ID を現在の public video list と照合し、存在する動画だけ表示する。
4. お気に入り toggle、詳細表示、履歴追加後に UI を再描画する。
5. 検証、作業レポート、commit、PR、受け入れ条件コメント、セルフレビューを完了する。

## ドキュメント保守方針

UI 表示の改善であり README 更新は不要。変更内容と検証は作業レポートに残す。

## 受け入れ条件

- localStorage にお気に入りが保存される。
- localStorage に閲覧履歴が保存される。
- お気に入りを UI から再表示できる。
- 閲覧履歴を UI から再表示できる。
- 保存済み ID が現 public data にない場合は架空動画を表示しない。
- 変更範囲に見合う検証と `npm test` が成功する。

## 検証計画

- `git diff --check`
- `npm test`
- `npm run build`
- `npm run e2e:local`

## リスク

- 実 CloudFront 配信でのブラウザ確認は未実施に留まる。
