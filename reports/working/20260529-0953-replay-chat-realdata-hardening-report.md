# replay chat collector 現実データ検証 作業完了レポート

## 受けた指示

- `.workspace/` 配下の設計書と 2026-05-29 の plan をもとに、`main` を pull してから作業する。
- repository local rules に従い、worktree、task md、検証、commit、PR、PR コメント、作業レポートまで行う。

## 要件整理

| 要件 | 対応状況 |
|---|---|
| P1-08 replay chat collector の現実データ検証を進める | 対応 |
| 公開アーカイブ HTML 由来の `ytInitialData` から replay action / continuation を抽出する | 対応 |
| unknown renderer を失敗・破棄せず raw JSONL / manifest に残す | 対応 |
| README とテストを更新する | 対応 |
| 実施した検証だけを記録する | 対応 |

## 検討・判断の要約

- 実 YouTube へのネットワーク疎通は外部状態に依存するため、この task では公開アーカイブ HTML に近い `ytInitialData` fixture で検証した。
- 既存の `normalize_replay_actions` は unknown renderer を message として残すが、collector の result / manifest から action 数や unknown 数を確認できなかったため、`parser_stats` と replay 用 `next_poll` を追加した。
- 既存の action walker は `replayChatItemAction` 内の `addChatItemAction` を重複計上する可能性があったため、外側の replay action を 1 action として扱うよう修正した。

## 実施作業

- `extract_replay_continuations_from_initial_data` を追加し、`reloadContinuationData`、`timedContinuationData`、`invalidationContinuationData`、`liveChatReplayContinuationData`、`continuationCommand` の token を抽出するようにした。
- replay chat collect で `parser_stats` と replay 用 `next_poll` を manifest/result に保存するようにした。
- 公開 HTML 近似 fixture から continuation、既知 text renderer、未知 membership renderer を検証する pytest を追加した。
- README に replay chat collect の best-effort 抽出と unknown renderer 保存方針を追記した。

## 成果物

| 成果物 | 内容 |
|---|---|
| `apps/shared/src/diopside_core/youtube.py` | replay action 重複抽出修正と continuation 抽出 helper 追加 |
| `apps/workers/static-exporter/src/static_exporter/pipeline.py` | replay collector の `parser_stats` / `next_poll` 記録追加 |
| `tests/test_core_pipeline.py` | 公開 HTML 近似 replay fixture test 追加 |
| `README.md` | replay collector の unknown 保存方針追記 |
| `tasks/do/20260529-0953-replay-chat-realdata-hardening.md` | task 定義、受け入れ条件、検証結果 |

## 実行した検証

- `git diff --check`: pass
- `python3 -m py_compile apps/shared/src/diopside_core/youtube.py apps/shared/src/diopside_core/__init__.py apps/workers/static-exporter/src/static_exporter/pipeline.py tests/test_core_pipeline.py`: pass
- `PYTHONPATH=apps/shared/src:apps/api/src:apps/workers/static-exporter/src python3 -m pytest tests/test_core_pipeline.py`: 初回 fail -> 修正後 pass（18 passed）
- `npm test`: pass（30 passed）
- `npm run verify`: pass

## 指示への fit 評価

総合fit: 4.6 / 5.0（約92%）

理由: P1-08 の主要要件である公開 HTML 近似構造からの replay action / continuation 抽出、unknown renderer 保存、manifest/result での可視化、README/test 更新は満たした。一方で、実 YouTube へのネットワーク疎通と実 AWS/SQS/S3 環境での確認は未実施のため満点ではない。

## 未対応・制約・リスク

- 実 YouTube アーカイブ HTML のライブ取得は未実施。
- 実 AWS deploy、実 SQS、実 S3 での疎通は未実施。
- この branch は PR #6 の上に積んでいるため、PR #3〜#6 が main に merge されるまでは main 向け diff に先行 PR の差分も含まれる。
