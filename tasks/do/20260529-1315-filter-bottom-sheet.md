# filter bottom sheet完成

状態: do

## 背景

`.workspace/plan-20260529.txt` の P3-02 に従い、タグ、年、動画長、並び順、wordcloud有無、timestamp有無で絞り込める filter bottom sheet を完成させる。閉じても状態を保持する。

## 目的

公開アーカイブ一覧を複数条件で絞り込み、bottom sheet を閉じても現在の filter 条件が画面と state に残るようにする。

## タスク種別

UI 改善

## スコープ

- `apps/web/public/index.html`
- `apps/web/public/app.js`
- `apps/web/public/styles.css`
- 必要に応じた local e2e の調整

## 計画

1. 既存 filter form と一覧 filter 関数を確認する。
2. bottom sheet に tag、year、duration、sort、wordcloud、timestamp の control を追加する。
3. filter state と form value を同期し、sheet を閉じても状態を保持する。
4. 一覧・tag chips・quick chips・clear 操作との整合を取る。
5. 検証、作業レポート、commit、PR、受け入れ条件コメント、セルフレビューを完了する。

## ドキュメント保守方針

UI の挙動追加であり README 更新は不要。変更内容と検証は作業レポートに残す。

## 受け入れ条件

- filter bottom sheet でタグを選べる。
- filter bottom sheet で年を指定できる。
- filter bottom sheet で動画長を選べる。
- filter bottom sheet で並び順を選べる。
- filter bottom sheet で wordcloud 有無を選べる。
- filter bottom sheet で timestamp 有無を選べる。
- bottom sheet を閉じても filter state と画面表示が保持される。
- clear 操作で filter state と form value が解除される。
- 本番 UI に架空値・demo fallback を混ぜない。
- 変更範囲に見合う検証と `npm test` が成功する。

## 検証計画

- `git diff --check`
- `npm test`
- `npm run build`
- `npm run e2e:local`

## リスク

- 実 CloudFront 配信でのブラウザ確認は未実施に留まる。
