# diopside v0.4 traceability matrix

| 項目 | 内容 |
|---|---|
| 文書種別 | 設計準拠トレーサビリティ |
| 対象設計 | `docs/design/diopside_basic_design_v0.4.md` |
| 作成日 | 2026-05-30 |
| 方針 | v0.4 を正本とし、現在の `main` は実装済み候補として照合する。 |

## status 定義

| status | 意味 |
|---|---|
| 実装済 | 現 main に該当実装があり、対応するテストまたは contract check がある。 |
| 部分実装 | 主要経路はあるが、v0.4 の path、framework、schema、保護方式、またはテストが不足している。 |
| 差分あり | 現 main の実装方針が v0.4 正本と異なる。後続 PR で修正または設計変更提案が必要。 |
| 未対応 | 現 main に該当実装が見当たらない。 |
| 要追加監査 | README またはコード上の候補はあるが、v0.4 の受け入れ条件を満たす証跡が不足している。 |

## 機能要求

| design_id | category | requirement | implementation_files | tests | status |
|---|---|---|---|---|---|
| FR-GEN-001 | Functional | 閲覧者は動画アーカイブを一覧できる。 | `apps/web/public`, `apps/api/src/diopside_api/handler.py`, `apps/workers/static-exporter/src/static_exporter/handler.py` | `tests/test_api_handler.py`, `tests/test_static_exporter.py`, `tools/run-local-e2e.mjs` | 部分実装 |
| FR-GEN-002 | Functional | 閲覧者はタグ・キーワード・期間で動画を探せる。 | `apps/web/public`, `apps/api/src/diopside_api/handler.py` | `tests/test_api_handler.py`, `tools/run-local-e2e.mjs` | 部分実装 |
| FR-GEN-003 | Functional | 閲覧者は動画詳細を確認できる。 | `apps/api/src/diopside_api/handler.py`, `apps/workers/static-exporter/src/static_exporter/handler.py` | `tests/test_api_handler.py`, `tests/test_static_exporter.py` | 実装済 |
| FR-GEN-004 | Functional | システムは YouTube 主要情報を定期取得する。 | `apps/workers/static-exporter/src/static_exporter/pipeline.py`, `infra/cloudformation/diopside.yaml` | `tests/test_core_pipeline.py`, `tests/test_cloudformation_contract.py` | 部分実装 |
| FR-GEN-005 | Functional | システムは低 quota で動画発見する。 | `apps/shared/src/diopside_core/youtube.py`, `apps/workers/static-exporter/src/static_exporter/pipeline.py` | `tests/test_core_pipeline.py` | 実装済 |
| FR-GEN-006 | Functional | システムはチャット欄を取得できる。 | `apps/workers/static-exporter/src/static_exporter/pipeline.py` | `tests/test_core_pipeline.py` | 部分実装 |
| FR-GEN-007 | Functional | システムは取得不能を安全に扱う。 | `apps/shared/src/diopside_core/youtube.py`, `apps/workers/static-exporter/src/static_exporter/pipeline.py` | `tests/test_core_pipeline.py` | 部分実装 |
| FR-GEN-008 | Functional | システムは静的成果物を生成する。 | `apps/workers/static-exporter/src/static_exporter/handler.py` | `tests/test_static_exporter.py`, `tools/check-public-contract.mjs` | 部分実装 |
| FR-GEN-009 | Functional | システムは手動再実行できる。 | `apps/api/src/diopside_api/handler.py`, `apps/workers/static-exporter/src/static_exporter/pipeline.py` | `tests/test_api_handler.py`, `tests/test_core_pipeline.py` | 部分実装 |
| FR-U-001 | UI | ホームに検索ハブを表示する。 | `apps/web/public`, `apps/api/src/diopside_api/handler.py` | `tools/run-local-e2e.mjs`, `tests/test_api_handler.py` | 部分実装 |
| FR-U-002 | UI | 片手操作しやすいフィードを表示する。 | `apps/web/public` | `tools/run-local-e2e.mjs`, `tools/check-web-dom-safety.mjs` | 部分実装 |
| FR-U-003 | UI | 動画詳細から YouTube へ遷移できる。 | `apps/web/public`, `apps/api/src/diopside_api/handler.py` | `tools/run-local-e2e.mjs`, `tests/test_api_handler.py` | 部分実装 |
| FR-U-004 | UI | タグから関連動画を探索できる。 | `apps/web/public`, `apps/api/src/diopside_api/handler.py` | `tools/run-local-e2e.mjs`, `tests/test_api_handler.py` | 部分実装 |
| FR-U-005 | UI | ワードクラウドを閲覧できる。 | `apps/web/public`, `apps/workers/static-exporter/src/static_exporter/handler.py` | `tests/test_static_exporter.py`, `tools/run-local-e2e.mjs` | 部分実装 |
| FR-U-006 | UI | タイムスタンプ候補を閲覧できる。 | `apps/web/public`, `apps/workers/static-exporter/src/static_exporter/handler.py` | `tests/test_static_exporter.py`, `tools/run-local-e2e.mjs` | 部分実装 |
| FR-U-007 | UI | ランダム動画を表示できる。 | `apps/api/src/diopside_api/handler.py`, `apps/web/public` | `tests/test_api_handler.py`, `tools/run-local-e2e.mjs` | 部分実装 |
| FR-A-001 | Admin | 対象チャンネルを設定できる。 | `apps/api/src/diopside_api/handler.py`, `apps/shared/src/diopside_core/repository.py` | なし | 未対応 |
| FR-A-002 | Admin | 手動でメタデータ同期できる。 | `apps/api/src/diopside_api/handler.py`, `apps/workers/static-exporter/src/static_exporter/pipeline.py` | `tests/test_api_handler.py`, `tests/test_core_pipeline.py` | 実装済 |
| FR-A-003 | Admin | 手動でチャット収集できる。 | `apps/api/src/diopside_api/handler.py`, `apps/workers/static-exporter/src/static_exporter/pipeline.py` | `tests/test_api_handler.py`, `tests/test_core_pipeline.py` | 部分実装 |
| FR-A-004 | Admin | 失敗ジョブを再実行できる。 | `apps/api/src/diopside_api/handler.py`, `apps/workers/static-exporter/src/static_exporter/pipeline.py` | `tests/test_api_handler.py`, `tests/test_core_pipeline.py` | 部分実装 |
| FR-A-005 | Admin | タグを補正できる。 | `apps/api/src/diopside_api/handler.py`, `apps/shared/src/diopside_core/repository.py`, `apps/workers/static-exporter/src/static_exporter/handler.py` | `tests/test_api_handler.py`, `tests/test_repository_schema_contract.py`, `tests/test_static_exporter.py` | 部分実装 |
| FR-A-006 | Admin | 生成物を再出力できる。 | `apps/api/src/diopside_api/handler.py`, `apps/workers/static-exporter/src/static_exporter/pipeline.py`, `apps/workers/static-exporter/src/static_exporter/handler.py` | `tests/test_api_handler.py`, `tests/test_static_exporter.py` | 部分実装 |
| FR-A-007 | Admin | quota 使用量を確認できる。 | `apps/api/src/diopside_api/handler.py`, `apps/shared/src/diopside_core/repository.py` | `tests/test_api_handler.py`, `tests/test_core_pipeline.py` | 実装済 |
| FR-YT-001 | YouTube | uploads playlist から新規動画を取得する。 | `apps/workers/static-exporter/src/static_exporter/pipeline.py` | `tests/test_core_pipeline.py` | 実装済 |
| FR-YT-002 | YouTube | video_id から詳細を取得する。 | `apps/shared/src/diopside_core/youtube.py`, `apps/workers/static-exporter/src/static_exporter/pipeline.py` | `tests/test_core_pipeline.py` | 実装済 |
| FR-YT-003 | YouTube | 配信予定を検知する。 | `apps/shared/src/diopside_core/youtube.py`, `apps/workers/static-exporter/src/static_exporter/pipeline.py` | `tests/test_core_pipeline.py` | 部分実装 |
| FR-YT-004 | YouTube | 配信中チャット ID を検出する。 | `apps/workers/static-exporter/src/static_exporter/pipeline.py` | `tests/test_core_pipeline.py` | 部分実装 |
| FR-YT-005 | YouTube | 公式 Live Chat API で配信中チャットを取得する。 | `apps/shared/src/diopside_core/youtube.py`, `apps/workers/static-exporter/src/static_exporter/pipeline.py` | `tests/test_core_pipeline.py` | 部分実装 |
| FR-YT-006 | YouTube | 公開リプレイチャットを取得する。 | `apps/shared/src/diopside_core/chat_parser.py`, `apps/workers/static-exporter/src/static_exporter/pipeline.py` | `tests/test_core_pipeline.py` | 部分実装 |
| FR-YT-007 | YouTube | replay chat の通常メッセージを正規化する。 | `apps/shared/src/diopside_core/chat_parser.py` | `tests/test_core_pipeline.py` | 実装済 |
| FR-YT-008 | YouTube | paid/super chat 系を正規化する。 | `apps/shared/src/diopside_core/chat_parser.py` | `tests/test_core_pipeline.py` | 実装済 |
| FR-YT-009 | YouTube | 絵文字を正規化する。 | `apps/shared/src/diopside_core/chat_parser.py` | `tests/test_core_pipeline.py` | 実装済 |
| FR-YT-010 | YouTube | 重複メッセージを除外する。 | `apps/shared/src/diopside_core/artifacts.py`, `apps/workers/static-exporter/src/static_exporter/pipeline.py` | `tests/test_core_pipeline.py` | 要追加監査 |

## 非機能要求

| design_id | category | requirement | implementation_files | tests | status |
|---|---|---|---|---|---|
| NFR-BAS-001 | Non-functional | 個人開発の維持費を最優先にする。 | `README.md`, `infra/cloudformation/diopside.yaml` | `tests/test_cloudformation_contract.py`, `tools/check-cost-estimate.js` | 部分実装 |
| NFR-BAS-002 | Non-functional | 公開閲覧は静的配信を基本にする。 | `apps/workers/static-exporter/src/static_exporter/handler.py`, `infra/cloudformation/diopside.yaml` | `tests/test_static_exporter.py`, `tools/check-public-contract.mjs` | 部分実装 |
| NFR-BAS-003 | Non-functional | 書き込み系は非同期ジョブにする。 | `apps/api/src/diopside_api/handler.py`, `infra/cloudformation/diopside.yaml` | `tests/test_api_handler.py`, `tests/test_cloudformation_contract.py` | 実装済 |
| NFR-BAS-004 | Non-functional | 生データを捨てない。 | `apps/workers/static-exporter/src/static_exporter/pipeline.py`, `infra/cloudformation/diopside.yaml` | `tests/test_core_pipeline.py` | 部分実装 |
| NFR-BAS-005 | Non-functional | YouTube quota を節約する。 | `apps/shared/src/diopside_core/youtube.py`, `apps/workers/static-exporter/src/static_exporter/pipeline.py` | `tests/test_core_pipeline.py` | 実装済 |
| NFR-BAS-006 | Non-functional | 仕様変更に強くする。 | `apps/shared/src/diopside_core/chat_parser.py` | `tests/test_core_pipeline.py` | 実装済 |
| NFR-BAS-007 | Non-functional | フロントに秘密情報を持たせない。 | `apps/api/src/diopside_api/handler.py`, `apps/web/public` | `tests/test_api_handler.py`, `tools/check-web-dom-safety.mjs` | 部分実装 |
| NFR-COST-001 | Cost | OpenSearch を初期採用しない。 | `README.md`, `infra/cloudformation/diopside.yaml` | `tests/test_cloudformation_contract.py` | 実装済 |
| NFR-COST-002 | Cost | RDB を初期採用しない。 | `README.md`, `infra/cloudformation/diopside.yaml` | `tests/test_cloudformation_contract.py` | 実装済 |
| NFR-COST-003 | Cost | Step Functions を初期採用しない。 | `README.md`, `infra/cloudformation/diopside.yaml` | `tests/test_cloudformation_contract.py` | 実装済 |
| NFR-COST-004 | Cost | YouTube API の高 quota メソッドを避ける。 | `apps/shared/src/diopside_core/youtube.py` | `tests/test_core_pipeline.py` | 実装済 |
| NFR-COST-005 | Cost | チャット全文を DynamoDB へ入れない。 | `apps/shared/src/diopside_core/repository.py`, `apps/workers/static-exporter/src/static_exporter/pipeline.py` | `tests/test_core_pipeline.py` | 実装済 |
| NFR-COST-006 | Cost | CloudWatch Logs へ本文を出さない。 | `apps/api/src/diopside_api/handler.py`, `apps/workers/static-exporter/src/static_exporter/pipeline.py` | `tests/test_api_handler.py`, `tests/test_core_pipeline.py` | 部分実装 |
| NFR-COST-007 | Cost | S3 lifecycle を必ず設定する。 | `infra/cloudformation/diopside.yaml` | `tests/test_cloudformation_contract.py` | 実装済 |
| NFR-SEC-001 | Security | YouTube API key を秘匿する。 | `infra/cloudformation/diopside.yaml`, `apps/workers/static-exporter/src/static_exporter/pipeline.py` | `tests/test_cloudformation_contract.py` | 部分実装 |
| NFR-SEC-002 | Security | 公開データのみ取得する。 | `apps/shared/src/diopside_core/youtube.py` | `tests/test_core_pipeline.py` | 部分実装 |
| NFR-SEC-003 | Security | replay 取得は best-effort に限定する。 | `apps/shared/src/diopside_core/chat_parser.py`, `apps/workers/static-exporter/src/static_exporter/pipeline.py` | `tests/test_core_pipeline.py` | 実装済 |
| NFR-SEC-004 | Security | 個人識別性を抑える。 | `apps/shared/src/diopside_core/chat_parser.py` | `tests/test_core_pipeline.py` | 部分実装 |
| NFR-SEC-005 | Security | 管理操作は保護する。 | `apps/api/src/diopside_api/handler.py` | `tests/test_api_handler.py` | 差分あり |

## API-001〜API-023

| design_id | category | requirement | implementation_files | tests | status |
|---|---|---|---|---|---|
| API-001 | API | `GET /api/health` health API。 | `apps/api/src/diopside_api/handler.py` | `tests/test_api_handler.py` | 実装済 |
| API-002 | API | `GET /api/config` 公開設定取得 API。 | `apps/api/src/diopside_api/handler.py` | `tests/test_api_handler.py`, `tools/check-docs-consistency.mjs` | 実装済 |
| API-003 | API | `GET /api/home` ホーム API。 | `apps/api/src/diopside_api/handler.py` | `tests/test_api_handler.py` | 実装済 |
| API-004 | API | `GET /api/videos` 動画一覧 API。 | `apps/api/src/diopside_api/handler.py` | `tests/test_api_handler.py` | 実装済 |
| API-005 | API | `GET /api/videos/{video_id}` 動画詳細 API。 | `apps/api/src/diopside_api/handler.py` | `tests/test_api_handler.py` | 実装済 |
| API-006 | API | `GET /api/tags` タグ一覧 API。 | `apps/api/src/diopside_api/handler.py` | `tests/test_api_handler.py` | 実装済 |
| API-007 | API | `GET /api/archive-calendar` 年/月別アーカイブ API。 | `apps/api/src/diopside_api/handler.py` | `tests/test_api_handler.py` | 実装済 |
| API-008 | API | `GET /api/random-videos` ランダム動画 API。 | `apps/api/src/diopside_api/handler.py` | `tests/test_api_handler.py` | 実装済 |
| API-009 | API | `GET /api/videos/{video_id}/artifacts` 動画成果物一覧 API。 | `apps/api/src/diopside_api/handler.py` | `tests/test_api_handler.py` | 実装済 |
| API-010 | API | `GET /api/admin/jobs` ジョブ一覧 API。 | `apps/api/src/diopside_api/handler.py` | `tests/test_api_handler.py` | 実装済 |
| API-011 | API | `GET /api/admin/jobs/{job_id}` ジョブ詳細 API。 | `apps/api/src/diopside_api/handler.py` | `tests/test_api_handler.py` | 実装済 |
| API-012 | API | `POST /api/admin/jobs/metadata-sync` メタデータ同期開始 API。 | `apps/api/src/diopside_api/handler.py` | `tests/test_api_handler.py` | 実装済 |
| API-013 | API | `POST /api/admin/jobs/live-status-scan` ライブ状態検知開始 API。 | `apps/api/src/diopside_api/handler.py` | `tests/test_api_handler.py` | 実装済 |
| API-014 | API | `POST /api/admin/jobs/chat-collect` チャット収集開始 API。 | `apps/api/src/diopside_api/handler.py` | `tests/test_api_handler.py` | 実装済 |
| API-015 | API | `POST /api/admin/jobs/chat-normalize` チャット正規化開始 API。 | `apps/api/src/diopside_api/handler.py` | `tests/test_api_handler.py` | 実装済 |
| API-016 | API | `POST /api/admin/jobs/rebuild-artifacts` 集計再生成 API。 | `apps/api/src/diopside_api/handler.py` | `tests/test_api_handler.py` | 実装済 |
| API-017 | API | `POST /api/admin/jobs/static-export` 静的 export 開始 API。 | `apps/api/src/diopside_api/handler.py` | `tests/test_api_handler.py`, `tests/test_static_exporter.py` | 実装済 |
| API-018 | API | `POST /api/admin/jobs/{job_id}/retry` 失敗ジョブ再実行 API。 | `apps/api/src/diopside_api/handler.py`, `apps/workers/static-exporter/src/static_exporter/pipeline.py` | `tests/test_api_handler.py` | 部分実装 |
| API-019 | API | `POST /api/admin/jobs/{job_id}/cancel` ジョブキャンセル API。 | `apps/api/src/diopside_api/handler.py`, `apps/workers/static-exporter/src/static_exporter/pipeline.py` | `tests/test_api_handler.py` | 実装済 |
| API-020 | API | `GET /api/admin/quota-usage` quota 使用量 API。 | `apps/api/src/diopside_api/handler.py` | `tests/test_api_handler.py` | 実装済 |
| API-021 | API | `GET /api/admin/channels` 対象チャンネル設定取得 API。 | `apps/api/src/diopside_api/handler.py` | `tests/test_api_handler.py` | 実装済 |
| API-022 | API | `PUT /api/admin/channels/{channel_id}` 対象チャンネル設定更新 API。 | `apps/api/src/diopside_api/handler.py`, `apps/shared/src/diopside_core/repository.py` | `tests/test_api_handler.py` | 実装済 |
| API-023 | API | `POST /api/admin/artifacts/presigned-url` 管理用 S3 署名 URL 発行 API。 | `apps/api/src/diopside_api/handler.py`, `apps/shared/src/diopside_core/repository.py` | `tests/test_api_handler.py` | 実装済 |

## STATIC-001〜STATIC-008

| design_id | category | requirement | implementation_files | tests | status |
|---|---|---|---|---|---|
| STATIC-001 | Static data | `/data/home.json` ホーム JSON。 | `apps/workers/static-exporter/src/static_exporter/handler.py` | `tests/test_static_exporter.py`, `tools/check-public-contract.mjs` | 実装済 |
| STATIC-002 | Static data | `/data/videos/index.json` 動画一覧 JSON。 | `apps/workers/static-exporter/src/static_exporter/handler.py` | `tests/test_static_exporter.py`, `tools/check-public-contract.mjs` | 実装済 |
| STATIC-003 | Static data | `/data/videos/{video_id}.json` 動画詳細 JSON。 | `apps/workers/static-exporter/src/static_exporter/handler.py` | `tests/test_static_exporter.py`, `tools/check-public-contract.mjs` | 実装済 |
| STATIC-004 | Static data | `/data/tags.json` タグ JSON。 | `apps/workers/static-exporter/src/static_exporter/handler.py` | `tests/test_static_exporter.py`, `tools/check-public-contract.mjs` | 実装済 |
| STATIC-005 | Static data | `/data/calendar/{year}.json` 年/月カレンダー JSON。 | `apps/workers/static-exporter/src/static_exporter/handler.py` | `tests/test_static_exporter.py`, `tools/check-public-contract.mjs` | 実装済 |
| STATIC-006 | Static data | `/data/latest-manifest.json` export manifest。 | `apps/workers/static-exporter/src/static_exporter/handler.py` | `tests/test_static_exporter.py`, `tools/check-public-contract.mjs` | 実装済 |
| STATIC-007 | Static data | `/data/artifacts/wordcloud/{video_id}.{png\|json}` ワードクラウド画像/JSON。 | `apps/workers/static-exporter/src/static_exporter/handler.py` が PNG/JSON alias と versioned path を生成し、既存 SVG を互換 artifact として維持 | `tests/test_static_exporter.py`, `tools/check-public-contract.mjs` | 対応 |
| STATIC-008 | Static data | `/data/artifacts/timestamps/{video_id}.json` タイムスタンプ候補 JSON。 | `apps/workers/static-exporter/src/static_exporter/handler.py` | `tests/test_static_exporter.py`, `tools/check-public-contract.mjs` | 実装済 |

## BATCH-001〜BATCH-020

| design_id | category | requirement | implementation_files | tests | status |
|---|---|---|---|---|---|
| BATCH-001 | Batch | 定期メタデータ同期ディスパッチ。 | `infra/cloudformation/diopside.yaml`, `apps/workers/static-exporter/src/static_exporter/pipeline.py` | `tests/test_cloudformation_contract.py`, `tests/test_core_pipeline.py` | 部分実装 |
| BATCH-002 | Batch | チャンネル情報取得。 | `apps/workers/static-exporter/src/static_exporter/pipeline.py` | なし | 要追加監査 |
| BATCH-003 | Batch | uploads playlist 差分取得。 | `apps/workers/static-exporter/src/static_exporter/pipeline.py` | `tests/test_core_pipeline.py` | 実装済 |
| BATCH-004 | Batch | 動画詳細取得。 | `apps/workers/static-exporter/src/static_exporter/pipeline.py` | `tests/test_core_pipeline.py` | 実装済 |
| BATCH-005 | Batch | ライブ状態監視。 | `infra/cloudformation/diopside.yaml`, `apps/workers/static-exporter/src/static_exporter/pipeline.py` | `tests/test_core_pipeline.py`, `tests/test_cloudformation_contract.py` | 部分実装 |
| BATCH-006 | Batch | 配信予定通知生成。 | `apps/workers/static-exporter/src/static_exporter/pipeline.py`, `docs/design/worker-batch-coverage-audit.md` | `tests/test_core_pipeline.py`, `tests/test_worker_batch_coverage_contract.py` | 部分実装 |
| BATCH-007 | Batch | 公式 Live Chat 取得。 | `apps/workers/static-exporter/src/static_exporter/pipeline.py` | `tests/test_core_pipeline.py` | 部分実装 |
| BATCH-008 | Batch | リプレイチャット初期化。 | `apps/workers/static-exporter/src/static_exporter/pipeline.py` | `tests/test_core_pipeline.py` | 部分実装 |
| BATCH-009 | Batch | リプレイチャットページ取得。 | `apps/workers/static-exporter/src/static_exporter/pipeline.py` | `tests/test_core_pipeline.py` | 部分実装 |
| BATCH-010 | Batch | チャット正規化。 | `apps/workers/static-exporter/src/static_exporter/pipeline.py`, `apps/shared/src/diopside_core/chat_parser.py` | `tests/test_core_pipeline.py` | 実装済 |
| BATCH-011 | Batch | チャット集計。 | `apps/workers/static-exporter/src/static_exporter/pipeline.py`, `apps/shared/src/diopside_core/artifacts.py` | `tests/test_core_pipeline.py` | 実装済 |
| BATCH-012 | Batch | ワードクラウド生成。 | `apps/shared/src/diopside_core/artifacts.py`, `apps/workers/static-exporter/src/static_exporter/pipeline.py`, `apps/workers/static-exporter/src/static_exporter/handler.py` | `tests/test_static_exporter.py` | 部分実装 |
| BATCH-013 | Batch | タイムスタンプ候補生成。 | `apps/workers/static-exporter/src/static_exporter/pipeline.py`, `apps/shared/src/diopside_core/artifacts.py` | `tests/test_core_pipeline.py`, `tests/test_static_exporter.py` | 部分実装 |
| BATCH-014 | Batch | ファイル出力サービス。 | `apps/workers/static-exporter/src/static_exporter/pipeline.py`, `apps/workers/static-exporter/src/static_exporter/handler.py`, `docs/design/worker-batch-coverage-audit.md` | `tests/test_core_pipeline.py`, `tests/test_static_exporter.py`, `tests/test_worker_batch_coverage_contract.py` | 部分実装 |
| BATCH-015 | Batch | 静的 JSON export。 | `apps/workers/static-exporter/src/static_exporter/handler.py` | `tests/test_static_exporter.py`, `tools/check-public-contract.mjs` | 部分実装 |
| BATCH-016 | Batch | quota 使用量ロールアップ。 | `apps/workers/static-exporter/src/static_exporter/pipeline.py`, `apps/shared/src/diopside_core/repository.py`, `infra/cloudformation/diopside.yaml` | `tests/test_core_pipeline.py`, `tests/test_repository_schema_contract.py`, `tests/test_cloudformation_contract.py` | 部分実装 |
| BATCH-017 | Batch | アーカイブ確定処理。 | `apps/workers/static-exporter/src/static_exporter/pipeline.py`, `docs/design/worker-batch-coverage-audit.md` | `tests/test_core_pipeline.py`, `tests/test_worker_batch_coverage_contract.py` | 部分実装 |
| BATCH-018 | Batch | 失敗ジョブ再投入/Redrive。 | `apps/api/src/diopside_api/handler.py`, `apps/workers/static-exporter/src/static_exporter/pipeline.py`, `README.md` | `tests/test_api_handler.py` | 部分実装 |
| BATCH-019 | Batch | 古い raw/中間成果物クリーンアップ。 | `apps/workers/static-exporter/src/static_exporter/pipeline.py`, `infra/cloudformation/diopside.yaml` | `tests/test_cloudformation_contract.py` | 部分実装 |
| BATCH-020 | Batch | 管理手動ジョブディスパッチ。 | `apps/api/src/diopside_api/handler.py` | `tests/test_api_handler.py` | 部分実装 |

## Data / Infra / UI / Operations

| design_id | category | requirement | implementation_files | tests | status |
|---|---|---|---|---|---|
| DDB-SCHEMA | DynamoDB | v0.4 item schema と key/GSI 設計。 | `apps/shared/src/diopside_core/repository.py`, `README.md`, `docs/design/dynamodb-schema-audit.md` | `tests/test_repository_schema_contract.py`, `tests/test_core_pipeline.py`, `tests/test_cloudformation_contract.py` | 監査済み・差分あり |
| S3-PATH | S3 | raw/processed/public/export artifact path。 | `apps/workers/static-exporter/src/static_exporter/handler.py`, `apps/workers/static-exporter/src/static_exporter/pipeline.py`, `infra/cloudformation/diopside.yaml` | `tests/test_static_exporter.py`, `tests/test_core_pipeline.py` | 部分実装 |
| CF-PATH | CloudFront | `/api/*`, `/data/*`, assets, SPA rewrite, OAC。 | `infra/cloudformation/diopside.yaml`, `README.md` | `tests/test_cloudformation_contract.py`, `tools/run-post-deploy-smoke.mjs` | 部分実装 |
| IAC-CDK | IaC | AWS CDK を IaC 正本にする。 | なし。現 main は `infra/cloudformation/diopside.yaml` 中心 | なし | 差分あり |
| API-FASTAPI | Backend | FastAPI on Lambda を API 正本にする。 | なし。現 main は Python Lambda handler 中心 | なし | 差分あり |
| WEB-NEXT | Frontend | Next.js static export + React client components。 | なし。現 main は `apps/web/public` の静的 SPA 中心 | `tools/run-local-e2e.mjs`, `tools/check-web-dom-safety.mjs` | 差分あり |
| ADMIN-SESSION | Security | 管理 UI/API は HttpOnly cookie + CSRF で保護する。 | `apps/api/src/diopside_api/handler.py`, `apps/web/public/app.js` | `tests/test_api_handler.py`, `tools/run-local-e2e.mjs` | 実装済 |
| WORKER-SPLIT | Worker | metadata/chat/normalize/aggregate/wordcloud/timestamp/export の責務分離。 | `apps/workers/static-exporter/src/static_exporter/pipeline.py` に統合実装、`docs/design/worker-batch-coverage-audit.md` に差分監査 | `tests/test_worker_batch_coverage_contract.py`, `tests/test_core_pipeline.py` | 監査済み・差分あり |
| TEST-UNIT | Test | parser、repository、S3 path、static schema の unit test。 | `tests/` | `npm test` | 部分実装 |
| TEST-INTEGRATION | Test | SQS message -> Lambda -> S3/DynamoDB の代表経路。 | `tests/test_core_pipeline.py`, `tests/test_static_exporter.py` | `npm test` | 部分実装 |
| TEST-E2E | Test | 公開 UI、管理 UI、CloudFront 経路の E2E/smoke。 | `tools/run-local-e2e.mjs`, `tools/run-post-deploy-smoke.mjs` | `npm run e2e:local`, `npm run smoke:post-deploy` | 部分実装 |
| OPS-DLQ | Operations | DLQ、redrive、incident 手順。 | `README.md`, `infra/cloudformation/diopside.yaml` | `tests/test_cloudformation_contract.py` | 実装済 |
| OPS-OBS | Operations | CloudWatch JSON log、Alarm、quota、lifecycle。 | `README.md`, `apps/api/src/diopside_api/handler.py`, `apps/workers/static-exporter/src/static_exporter/pipeline.py`, `infra/cloudformation/diopside.yaml` | `tests/test_api_handler.py`, `tests/test_core_pipeline.py`, `tests/test_cloudformation_contract.py` | 部分実装 |

## 後続 PR 候補

| priority | branch 候補 | 対象 |
|---|---|---|
| P0 | `infra/cdk-parity` | `IAC-CDK` を差分ありから解消する。 |
| P0 | `api/fastapi-v04-contract` | `API-FASTAPI` と API-001〜023 の未対応を解消する。 |
| P0 | `web/next-static-export-v04` | `WEB-NEXT` を差分ありから解消する。 |
| P0 | `admin/cookie-csrf-session` | `ADMIN-SESSION` と NFR-SEC-005 を v0.4 に寄せる。実装済。 |
| P1 | `static/v04-data-if` | STATIC-001〜008 の alias/materialized path を正式出力する。 |
| P1 | `worker/batch-v04-coverage` | BATCH-001〜020 の handler/job/queue/test 対応を埋める。 |
