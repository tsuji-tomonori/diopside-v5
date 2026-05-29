# public data contract強化

状態: do

## 背景

`.workspace/plan-20260529.txt` の P1-14 に従い、public data contract検証を manifest、video list、tags、video detail、wordcloud、timestamp、artifact path まで強化する。

## 受け入れ条件

- `tools/check-public-contract.mjs` が manifest の schema、export_version、versioned base path、index/search path を検証する。
- video list と video detail の `video_id`、`detail_path`、`wordcloud_available`、`timestamp_available` が相互に矛盾しないことを検証する。
- tags index の schema と item 形状、tag label と video_count の型を検証する。
- wordcloud artifact の path、content_type、detail 内 URL、SVG 実体の存在と内容を検証する。
- timestamp candidate の必須 field、数値 field、score/evidence/message_count を検証する。
- fixture と static exporter output の両方に対して contract check が実行される。
- post-deploy smoke が取得した public data に同じ contract check を適用していることを確認する。
- 変更範囲に見合うテストと `npm run verify` が成功する。
