# local e2e拡張

状態: done

## 背景

`.workspace/plan-20260529.txt` の P3-08 に従い、検索、タグfilter、詳細、wordcloud表示、timestamp link、admin job dry-run をブラウザ相当で検証する。

## 目的

既存の local e2e を、HTTP/API 契約確認だけでなく headless Chrome の DOM 操作確認まで拡張する。

## タスク種別

テスト強化

## スコープ

- `tools/run-local-e2e.mjs`

## 計画

1. 既存 local e2e の static/API/admin dry-run 確認を把握する。
2. local static server から `/api/*` を local API server へ proxy する。
3. headless Chrome CDP でホームを開き、検索、タグ filter、詳細、wordcloud、timestamp link、管理 dry-run を DOM 操作で確認する。
4. `npm run e2e:local` と `npm test` を実行する。
5. 作業レポート、commit、PR、受け入れ条件コメント、セルフレビューを完了する。

## ドキュメント保守方針

テスト強化であり README 更新は不要。検証範囲は作業レポートと PR に明記する。

## 受け入れ条件

- 検索操作をブラウザ相当で検証する。
- タグ filter 操作をブラウザ相当で検証する。
- 詳細表示をブラウザ相当で検証する。
- wordcloud 表示をブラウザ相当で検証する。
- timestamp link をブラウザ相当で検証する。
- admin job dry-run をブラウザ相当で検証する。
- 変更範囲に見合う検証と `npm test` が成功する。

## 検証計画

- `git diff --check`
- `npm run e2e:local`
- `npm test`

## リスク

- headless Chrome がローカル環境に存在する前提の検証になる。

## 完了記録

- PR: https://github.com/tsuji-tomonori/diopside-v5/pull/32
- 受け入れ条件確認コメント: https://github.com/tsuji-tomonori/diopside-v5/pull/32#issuecomment-4570495138
- セルフレビューコメント: https://github.com/tsuji-tomonori/diopside-v5/pull/32#issuecomment-4570495143
- 作業レポート: `reports/working/20260529-1500-local-e2e-web-flows-report.md`

## 検証結果

- `git diff --check`: 成功
- `npm run e2e:local`: 成功
- `npm test`: 59 passed
- `npm run build`: 成功
