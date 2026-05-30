# design v0.4 compliance audit

| 項目 | 内容 |
|---|---|
| 作成日 | 2026-05-30 |
| 対象設計 | `docs/design/diopside_basic_design_v0.4.md` |
| 照合対象 | `origin/main` 由来の現 worktree |
| 方針 | v0.4 を正本とし、実装差分は未対応または差分ありとして扱う。 |

## 1. 要約

`.workspace/plan-20260530.txt` の最初の PR 方針に沿って、v0.4 設計書を repository 内に正本化し、現在の `main` 実装との初版 traceability を作成した。

現 main は CloudFront + S3 + Lambda + DynamoDB + SQS + EventBridge という低コスト serverless の大枠に近い。一方で、v0.4 が正本とする AWS CDK、FastAPI on Lambda、Next.js static export、BATCH-006/BATCH-017 などには差分または未対応が残る。STATIC-001〜008 は同 PR 内の追加 commit で alias path と manifest checksum の contract 対応を進めたが、wordcloud PNG は未対応で JSON/SVG を先行サポートとしている。API-007/API-022/API-023 は既存 Lambda handler に追加し、FastAPI 移行は後続課題として残す。ADMIN-SESSION は HttpOnly cookie + CSRF を追加し、CLI / automation 向け Bearer fallback は維持した。

## 2. 正本化

| 項目 | 結果 |
|---|---|
| v0.4 設計書 | `docs/design/diopside_basic_design_v0.4.md` に配置 |
| README 設計根拠 | `.workspace/diopside_basic_design_v0.4.md` から `docs/design/diopside_basic_design_v0.4.md` へ変更 |
| traceability | `docs/design/traceability-matrix.md` に作成 |

## 3. P0 準拠ブロッカー

| ID | 項目 | 現状 | 判定 | 次アクション |
|---|---|---|---|---|
| P0-01 | 設計正本化 | v0.4 を `docs/design/` に配置し README 参照を更新 | 対応 | 今後の設計変更は別 PR で扱う |
| P0-02 | Traceability | 初版 matrix を作成し、要求/API/STATIC/BATCH/Data/Infra/UI/Test を分類 | 対応 | 詳細コード証跡は後続 PR で補強 |
| P0-03 | IaC | 現 main は `infra/cloudformation/diopside.yaml` 中心 | 差分あり | `infra/cdk-parity` で CDK synth と contract test を追加 |
| P0-04 | API 基盤 | 現 main は Python Lambda handler 中心。API-001〜023 の route coverage は進んだが FastAPI/OpenAPI は未対応 | 差分あり | `api/fastapi-v04-contract` で FastAPI + OpenAPI へ移行 |
| P0-05 | 管理認証 | HttpOnly cookie + CSRF を追加。Bearer token + CSRF は CLI / automation fallback として維持 | 対応済 | session API と管理 UI cookie 保護を追加済み |
| P0-06 | API-001〜023 | API-007/API-022/API-023 を追加。FastAPI/OpenAPI と一部 route の詳細 contract は後続 | 部分対応 | `api/fastapi-v04-contract` で framework と OpenAPI 証跡を追加 |
| P0-07 | STATIC-001〜008 | v0.4 alias path、versioned path、manifest checksum を static exporter と contract check に追加。wordcloud PNG は未対応 | 部分対応 | PNG が必要な場合は後続 `static/wordcloud-png-artifact` で対応 |
| P0-08 | DDB schema | README と repository に single-table 実装があるが v0.4 全 item との一致は未証明 | 要追加監査 | schema item ごとの contract test を追加 |
| P0-09 | Worker coverage | job_type は統合実装。BATCH-006/BATCH-017 などが不足 | 差分あり | `worker/batch-v04-coverage` で handler/job/queue/test 対応を埋める |
| P0-10 | Dev deploy rehearsal | 実 dev 環境で YouTube 実データ 1 件の end-to-end 確認はこの PR では未実施 | 未検証 | credentials と dev stack がある環境で別途実施 |

## 4. P1 / P2 主要差分

| priority | 項目 | 判定 | 補足 |
|---|---|---|---|
| P1 | チャンネル設定管理 | 部分対応 | `GET /api/admin/channels` と `PUT /api/admin/channels/{channel_id}` を追加。管理 UI は未対応 |
| P1 | タグ補正 | 未対応 | 手動タグ追加・削除 API/UI と static export 反映がない |
| P1 | Archive calendar | 部分対応 | `/data/calendar/{year}.json` と `GET /api/archive-calendar` を追加。UI は未対応 |
| P1 | Presigned URL | 対応 | `POST /api/admin/artifacts/presigned-url` を追加。private S3 artifact のみ署名対象 |
| P1 | NotificationPlan | 未対応 | 配信 30 分前・開始時刻・archive_available 候補の保存がない |
| P1 | wordcloud artifact | 部分対応 | JSON alias と既存 SVG を出力。PNG は未対応 |
| P1 | timestamp standalone | 対応 | `/data/artifacts/timestamps/{video_id}.json` を出力 |
| P2 | worker 分割 | 差分あり | `static_exporter.pipeline` に複数責務が統合されている |
| P2 | packages 分割 | 差分あり | `packages/domain` や `packages/youtube-client` 分割は未実施 |
| P2 | Next.js static export | 差分あり | 現 main は静的 SPA |
| P2 | FastAPI 移行 | 差分あり | 現 main は hand-written Lambda routing |
| P2 | CDK Construct 化 | 差分あり | 現 main は CloudFormation template |
| P2 | Cost regression | 部分実装 | cost guard 系 tool はあるが v0.4 全観点の継続証跡は未確認 |

## 5. 後続 PR 推奨順

1. `api/fastapi-v04-contract`
   - 既存 route coverage を FastAPI/OpenAPI へ移行し、API-001〜023 の schema 証跡を生成する。
2. `admin/cookie-csrf-session`
   - 管理 UI の正式保護方式を v0.4 に合わせる。
3. `worker/batch-v04-coverage`
   - BATCH-001〜020 を job_type、queue、入力/出力 schema、テストに紐付ける。
4. `static/wordcloud-png-artifact`
   - v0.4 の `{png|json}` のうち、未対応の PNG wordcloud を追加する。
5. `infra/cdk-parity`
   - CloudFormation から CDK 正本へ移行する。
6. `web/next-static-export-v04`
   - 現 UI 仕様を維持しつつ Next.js static export へ移行する。

## 6. 未対応・制約・リスク

- この監査は repository 内の README、主要実装、テスト、v0.4 設計書に基づく初版であり、AWS dev 環境や CloudFront 実応答は確認していない。
- traceability の `実装済` は local code/test の証跡に基づく。dev deploy rehearsal や CI green を意味しない。
- v0.4 設計書本文は正本としてコピーし、現 main に合わせた改変は行っていない。
- `docs/` は今回新設であり、既存 `docs/DOCS_STRUCTURE.md` は存在しないため、`docs/design/` 直下に配置した。
