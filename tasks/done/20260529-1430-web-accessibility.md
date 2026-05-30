# アクセシビリティ改善

状態: done

## 背景

`.workspace/plan-20260529.txt` の P3-07 に従い、主要 button に `aria-label`、filter chip に `aria-pressed`、dialog にラベル、focus-visible、44px 以上の tap target を入れる。

## 目的

公開 UI と管理 panel の主要操作を、スクリーンリーダーとキーボード操作で追いやすくする。

## タスク種別

UI 改善

## スコープ

- `apps/web/public/index.html`
- `apps/web/public/app.js`
- `apps/web/public/styles.css`

## 計画

1. 既存 button、dialog、chip、focus/tap target の状態を確認する。
2. 主要 static button に `aria-label` を追加する。
3. dynamic button に用途が分かる `aria-label` を追加する。
4. dialog に `aria-labelledby` を追加する。
5. tap target が 44px 未満の操作要素を補正する。
6. 検証、作業レポート、commit、PR、受け入れ条件コメント、セルフレビューを完了する。

## ドキュメント保守方針

UI 属性・style の改善であり README 更新は不要。変更内容と検証は作業レポートに残す。

## 受け入れ条件

- 主要 button に `aria-label` がある。
- filter chip に `aria-pressed` がある。
- dialog にラベルがある。
- focus-visible がある。
- 主要 tap target が 44px 以上である。
- 変更範囲に見合う検証と `npm test` が成功する。

## 検証計画

- `git diff --check`
- `npm test`
- `npm run build`
- `npm run e2e:local`

## リスク

- 実スクリーンリーダーでの手動確認は未実施に留まる。

## 完了記録

- PR: https://github.com/tsuji-tomonori/diopside-v5/pull/31
- 受け入れ条件確認コメント: https://github.com/tsuji-tomonori/diopside-v5/pull/31#issuecomment-4570453539
- セルフレビューコメント: https://github.com/tsuji-tomonori/diopside-v5/pull/31#issuecomment-4570453537
- 作業レポート: `reports/working/20260529-1430-web-accessibility-report.md`

## 検証結果

- `git diff --check`: 成功
- `npm test`: 59 passed
- `npm run build`: 成功
- `npm run e2e:local`: 成功
