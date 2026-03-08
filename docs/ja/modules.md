# モジュールリファレンス

本ドキュメントでは、**lifegence_industry** アプリに含まれる3つのモジュールの詳細情報を提供します。

**目次**

- [レセプト (Medical Receipt)](#レセプト)
- [貿易管理 (Trade Management)](#貿易管理)
- [マインド分析 (Mind Analyzer)](#マインド分析)

---

## レセプト

診療報酬明細書（レセプト）処理を行う医療機関向けモジュールです。患者の診療記録、自動点数計算、月次レセプト生成、バリデーション、保険請求用 CSV エクスポートを処理します。

### DocType 一覧

| DocType                    | 種別        | 説明                                         |
|----------------------------|-------------|----------------------------------------------|
| Medical Receipt Settings   | Single      | 医療機関レベルの設定                         |
| Patient Encounter          | Submittable | 個別の患者来院記録                           |
| Patient Insurance Info     | Standard    | 患者に紐づく保険情報                         |
| Encounter Service Line     | Child       | 診療内の診療行為項目                         |
| Encounter Diagnosis        | Child       | 診療に付与された傷病名                       |
| Disease Master             | Standard    | 傷病名マスタ                                 |
| Medical Service Master     | Standard    | 診療行為マスタ（点数コード）                 |
| Fee Schedule Revision      | Standard    | 点数表改定（有効日付き）                     |
| Receipt                    | Submittable | 保険請求用に生成された月次レセプト           |
| Receipt Batch              | Standard    | 一括提出用のレセプトグループ                 |
| Receipt Detail Line        | Child       | レセプト内の個別明細行                       |
| Receipt Validation Log     | Standard    | レセプトのバリデーション結果                 |

### ワークフロー

```
マスタデータ設定
  (傷病名マスタ、診療行為マスタ、点数表改定)
        |
        v
患者保険情報の登録
  (患者の保険詳細を登録)
        |
        v
Patient Encounter（診療記録）
  (診療行為と傷病名を記録)
        |
        v
診療記録の提出（Submit）
  (on_submit フックにより自動点数計算)
        |
        v
月次レセプト生成
  (提出済み診療記録をレセプトに集約)
        |
        v
レセプトバリデーション
  (5種類の自動チェック)
        |
        v
CSV エクスポート
  (保険請求提出用ファイルの生成)
```

**手順の詳細**:

1. **マスタデータの設定。** Disease Master（傷病名マスタ）、Medical Service Master（診療行為マスタ）、Fee Schedule Revision（点数表改定）のレコードを作成します。点数計算に必要です。
2. **患者保険情報の登録。** Patient Insurance Info レコードを作成し、患者と保険プランを紐づけます。
3. **診療記録の作成。** Patient Encounter を作成し、Encounter Service Line（診療行為）と Encounter Diagnosis（傷病名）を入力します。
4. **診療記録の提出。** Submit すると、有効な点数表改定と設定済みの `point_unit_price` を使用して自動的に点数計算が実行されます。
5. **月次レセプト生成。** レセプト生成 API を使用して、指定月の提出済み診療記録から Receipt ドキュメントを一括作成します。
6. **レセプトバリデーション。** 提出前にバリデーションを実行してエラーを確認します。以下の5つのチェックが実行されます。
   - 明細行が存在し有効であること
   - 傷病名が存在すること
   - 保険が有効であること
   - 保険期間が診療日をカバーしていること
   - 点数合計が整合していること
7. **CSV エクスポート。** 標準フォーマット（HE/RE/SI/SY/GO レコード構造）で提出用ファイルを生成します。

### スケジュールタスク

| スケジュール           | タスク                        | 説明                                       |
|------------------------|-------------------------------|--------------------------------------------|
| 毎月5日 午前9時       | `send_deadline_reminder`      | レセプト提出期限のメールリマインダー       |

### API リファレンス

すべてのエンドポイントは `lifegence_industry.medical_receipt.api` 配下にあります。

**fee_calculation**

| 関数                    | トリガー / 用途                          | 説明                                         |
|-------------------------|------------------------------------------|----------------------------------------------|
| `on_encounter_submit`   | Doc event: Patient Encounter `on_submit` | 提出された診療記録の点数を計算               |
| `calculate_fee`         | ホワイトリスト API                       | 点数計算を手動でトリガー                     |

**receipt_generation**

| 関数                          | 説明                                             |
|-------------------------------|--------------------------------------------------|
| `generate_monthly_receipts`   | 指定月の Receipt ドキュメントを生成              |
| `send_deadline_reminder`      | スケジュールタスク: 5日にリマインダーメールを送信 |

**receipt_validation**

| 関数                | 説明                                         |
|---------------------|----------------------------------------------|
| `validate_receipt`  | Receipt に対して5種類のバリデーションを実行  |

**receipt_export**

| 関数                 | 説明                                         |
|----------------------|----------------------------------------------|
| `export_receipt_csv` | HE/RE/SI/SY/GO 形式で CSV データをエクスポート |

### CSV エクスポートフォーマット

エクスポートでは以下のレコードタイプを含む CSV が生成されます。

| レコードコード | 名称             | 内容                                     |
|----------------|------------------|------------------------------------------|
| HE             | ヘッダー         | ファイルメタデータと医療機関情報         |
| RE             | レセプト共通     | レセプトレベルのサマリーデータ           |
| SI             | 診療行為         | 個別の診療行為明細                       |
| SY             | 傷病名           | 傷病名コードと記述                       |
| GO             | フッター         | 合計値とファイル終端                     |

### インストール時の初期データ

Medical Receipt Settings はインストール時に自動作成されません。インストール後に手動で設定する必要があります。

---

## 貿易管理

国際貿易・物流管理モジュールです。予約から通関までの船積みライフサイクル全体をカバーし、船積書類、信用状（L/C）、制裁措置スクリーニング、コンプライアンスチェック機能を提供します。

### DocType 一覧

**コア**

| DocType                | 種別        | 説明                                      |
|------------------------|-------------|-------------------------------------------|
| Trade Settings         | Single      | モジュールレベルの設定                    |
| Trade Shipment         | Submittable | 中心となる船積み記録                      |
| Trade Shipment Item    | Child       | 船積み内の品目                            |
| Trade Container        | Child       | 船積みのコンテナ情報                      |
| Trade Charge           | Child       | 船積みに関連する費用                      |
| Trade Schedule         | Child       | スケジュールマイルストーン（ETD、ETA等）  |
| Trade Document Link    | Child       | 関連船積書類へのリンク                    |

**船積書類**

| DocType                  | 種別     | 説明                                      |
|--------------------------|----------|-------------------------------------------|
| Bill of Lading           | Standard | 船荷証券（B/L）                           |
| Air Waybill              | Standard | 航空貨物運送状（AWB）                     |
| Commercial Invoice       | Standard | 商業送り状                                |
| Commercial Invoice Item  | Child    | 商業送り状の明細項目                      |
| Packing List             | Standard | 梱包明細書                                |
| Packing List Item        | Child    | 梱包明細の個別エントリ                    |
| Certificate of Origin    | Standard | 原産地証明書                              |
| COO Item                 | Child    | 原産地証明書に記載された品目              |

**通関**

| DocType                 | 種別        | 説明                                       |
|-------------------------|-------------|--------------------------------------------|
| Customs Declaration     | Submittable | 輸入/輸出/再輸出/再輸入申告               |
| Customs Declaration Item| Child       | HS コードと関税額を含む明細項目            |
| Customs Tariff Rate     | Standard    | HS コード別の関税率検索                    |
| Trade Compliance Check  | Standard    | コンプライアンス検証記録                   |
| Compliance Match Entry  | Standard    | スクリーニングの個別マッチ結果             |
| Sanctions List Entry    | Standard    | 制裁リスト/取引禁止当事者リストのエントリ  |

**ファイナンス**

| DocType          | 種別     | 説明                                                     |
|------------------|----------|----------------------------------------------------------|
| Letter of Credit | Standard | 信用状ライフサイクル: Draft→Issued→Advised→Drawn→Expired |
| LC Amendment     | Standard | 既存信用状の条件変更                                     |

**マスタ**

| DocType           | 種別     | 説明                             |
|-------------------|----------|----------------------------------|
| Port Master       | Standard | 港湾・ターミナル参照データ       |
| Vessel Master     | Standard | 船舶参照データ                   |
| Shipping Line     | Standard | 船会社参照データ                 |
| Airline Master    | Standard | 航空会社参照データ               |
| Freight Forwarder | Standard | フォワーダー参照データ           |
| Customs Broker    | Standard | 通関業者参照データ               |

### ワークフロー

**船積みライフサイクル**

```
Draft --> Booked --> Shipped --> In Transit --> Arrived --> Customs Cleared --> Delivered
（下書き → 予約済 → 船積済 → 輸送中 → 到着 → 通関済 → 配送完了）
```

**ERPNext 連携（Doc Events）**

| ERPNext DocType   | イベント    | アクション                                |
|-------------------|-------------|-------------------------------------------|
| Sales Order       | `on_submit` | 輸出用 Trade Shipment を自動作成          |
| Purchase Order    | `on_submit` | 輸入用 Trade Shipment を自動作成          |
| Delivery Note     | `on_submit` | 船積みステータスを Booked に更新          |
| Purchase Receipt  | `on_submit` | 船積みステータスを Delivered に更新        |

自動作成は Trade Settings の `auto_create_shipment_from_so` および `auto_create_shipment_from_po` フラグで制御されます。

**信用状（L/C）ライフサイクル**

```
Draft --> Issued --> Advised --> Drawn --> Expired
（下書き → 発行済 → 通知済 → 買取済 → 期限切れ）
```

### Item DocType へのカスタムフィールド

標準の ERPNext **Item** DocType に「Trade / Export Control」セクションとして以下のフィールドが追加されます。

| フィールド名             | 型    | 説明                                       |
|--------------------------|-------|--------------------------------------------|
| `export_control_class`   | Data  | 輸出管理分類（例: EAR99、3A001 等）        |
| `dual_use_flag`          | Check | デュアルユース品目かどうか                 |
| `catch_all_number`       | Data  | 経済産業省キャッチオール規制番号           |
| `export_license_required`| Check | 輸出許可が必要かどうか                     |

### スケジュールタスク

| スケジュール | タスク                | 説明                                          |
|--------------|-----------------------|-----------------------------------------------|
| 毎日         | `check_eta_alerts`    | 3日以内に到着予定の船積みアラートを送信       |
| 毎日         | `check_lc_expiry`     | 14日以内に期限切れの L/C アラートを送信       |

### サービス

**sanctions_screening**

Sanctions List Entry データベースに対してエンティティおよび船積みのスクリーニングを実行します。

**schedule**

ETA 接近および L/C 期限切れ通知の日次スケジュールチェック。

**hs_suggestion**（スタブ）

品目説明に基づく AI による HS コード提案。将来の実装に向けたプレースホルダーです。

**document_check**（スタブ）

AI による船積書類バリデーション。将来の実装に向けたプレースホルダーです。

### レポート

| レポート                | 説明                                          |
|-------------------------|-----------------------------------------------|
| Customs Duty Report     | 申告別の関税サマリー                          |
| L/C Utilization         | 信用状の利用状況とステータス追跡              |
| Trade Shipment Summary  | ステータス・航路・期間別の船積み概要          |

### インストール時の初期データ

- **Trade Settings** がデフォルト値で自動作成されます: `auto_create_landed_cost = 1`、その他の自動フラグはすべてオフ。
- **Item** へのカスタムフィールドがインストール時に自動作成されます。

---

## マインド分析

職場のウェルビーイングのための音声ベース心理分析モジュールです。個人セッションおよびミーティング中のリアルタイム音声分析、行動トリガーの検出、ウェルネスレポートの生成を行います。

### DocType 一覧

| DocType                    | 種別     | 説明                                         |
|----------------------------|----------|----------------------------------------------|
| Voice Analyzer Settings    | Single   | モジュールレベルの設定と API キー            |
| Voice Analysis Session     | Standard | アクティブまたは完了した分析セッション       |
| Individual Analysis Result | Standard | 個人分析セッションのメトリクス               |
| Meeting Analysis Result    | Standard | ミーティング分析セッションのメトリクス       |
| Voice Trigger Event        | Standard | セッション中に検出された行動トリガー         |
| Acoustic Statistics        | Standard | セッションセグメントの音響測定値             |
| Monthly Report             | Standard | 月次ウェルネスレポート（集約）               |

### 分析モード

**個人モード**

単一人物の音声を分析します。以下のメトリクスを生成します（各 0〜1 のスケール）。

| メトリクス                 | 説明                                     |
|----------------------------|------------------------------------------|
| `stress_load`              | 検出されたストレスレベル                 |
| `anxiety_uncertainty`      | 不安・不確実性の指標                     |
| `cognitive_load`           | 認知的負荷                               |
| `confidence_assertiveness` | 自信・主張性のレベル                     |
| `stability`                | 音声全体の安定性                         |

**ミーティングモード**

グループの会話を分析します。以下のメトリクスを生成します（各 0〜1 のスケール）。

| メトリクス           | 説明                                           |
|----------------------|------------------------------------------------|
| `speak_up`           | 発言意欲                                       |
| `respect_interaction`| 対話における相互尊重                           |
| `error_tolerance`    | 失敗や異なる意見への寛容性                     |
| `power_balance`      | 参加者間の発言権のバランス                     |
| `overall_ps`         | 心理的安全性の総合スコア                       |

### トリガータイプ

分析中に8種類の行動トリガーを検出します。

| トリガータイプ        | 説明                                       | デフォルト閾値           |
|-----------------------|--------------------------------------------|--------------------------|
| `silence_spike`       | 異常に長い沈黙                             | 3000 ミリ秒              |
| `apology_phrase`      | 謝罪・自己卑下のフレーズ                   | `trigger_threshold` に準拠 |
| `hedge_increase`      | ヘッジワードの増加（「たぶん」「一応」等） | 5回/分                   |
| `speech_rate_change`  | 発話速度の急激な変化                       | 30% 変化                 |
| `restart_increase`    | 文の言い直しの頻発                         | 4回/分                   |
| `interruption`        | 他の話者への割り込み                       | `trigger_threshold` に準拠 |
| `overlap`             | 話者間の発話の重なり                       | `trigger_threshold` に準拠 |
| `power_imbalance`     | 発言時間の偏り                             | `trigger_threshold` に準拠 |

### ワークフロー

```
Voice Analyzer Settings の設定
  (API キー、閾値、モード)
        |
        v
セッション開始 (API コール)
  (個人モードまたはミーティングモード)
        |
        v
音声分析 (リアルタイム API コール)
  (analysis_interval_sec 間隔で音声セグメントを送信)
        |
        v
トリガー検出
  (Voice Trigger Event が自動作成)
        |
        v
セッション終了 (API コール)
  (Individual/Meeting Analysis Result が生成)
        |
        v
月次レポート生成
  (ウェルネススコア、トレンド、AI インサイトの集約)
```

### スケジュールタスク

| スケジュール      | タスク                     | 説明                                         |
|-------------------|----------------------------|----------------------------------------------|
| 毎日              | `cleanup_old_data`         | `data_retention_days` を超えたデータを削除   |
| 6時間ごと         | `cleanup_stale_sessions`   | 24時間以上非アクティブなセッションをクローズ |

### ページ

| ページ                     | 説明                                              |
|----------------------------|---------------------------------------------------|
| Mind Analyzer Dashboard    | リアルタイムセッション表示と分析コントロール      |
| Monthly Report Viewer      | 月次ウェルネスレポートの閲覧・ブラウズ            |
| Organization Dashboard     | 組織全体のアナリティクスとトレンド                |

### ロール

| ロール                 | 権限                                              |
|------------------------|---------------------------------------------------|
| Mind Analyzer User     | 自身のセッションの開始・終了、自身の結果の閲覧   |
| Mind Analyzer Manager  | チーム分析結果と部門レポートの閲覧               |
| Mind Analyzer Admin    | 設定の変更、全データの閲覧                       |

### ユーザーデータ保護

以下の DocType が Frappe のユーザーデータ保護フレームワークに登録されています。

- **Voice Analysis Session** -- `user` フィールドでフィルタリング
- **Individual Analysis Result** -- `owner` でフィルタリング
- **Meeting Analysis Result** -- `owner` でフィルタリング

これにより、データ削除・エクスポートリクエストへの対応が確保されます。

### API リファレンス

すべてのエンドポイントは `lifegence_industry.mind_analyzer.api` 配下にあります。

**session**

| 関数                 | 説明                                              |
|----------------------|---------------------------------------------------|
| `start_session`      | 新しい分析セッションを開始（個人またはミーティング） |
| `end_session`        | アクティブなセッションを終了し結果を生成          |
| `cancel_session`     | 結果を生成せずにセッションをキャンセル            |
| `has_analyzer_access`| アプリ画面アクセスの権限チェック                  |

**analysis**

| 関数                 | 説明                                              |
|----------------------|---------------------------------------------------|
| `analyze_audio`      | リアルタイムで音声セグメントを処理                |

**reports**

| 関数                      | 説明                                          |
|---------------------------|-----------------------------------------------|
| `get_trend_data`          | ユーザーの時系列トレンドデータを取得          |

**reports_monthly**

| 関数                      | 説明                                          |
|---------------------------|-----------------------------------------------|
| 月次レポートエンドポイント | 月次レポートの生成・取得                      |

**reports_department**

| 関数                         | 説明                                      |
|------------------------------|-------------------------------------------|
| 部門分析エンドポイント       | 部門レベルの集約アナリティクス            |

**reports_summary / reports_team / reports_triggers / reports_export**

組織全体のアナリティクス、チームビュー、トリガー分析、データエクスポート用の追加レポートエンドポイント。

### サービス

| サービス             | 説明                                               |
|----------------------|----------------------------------------------------|
| `audio_processor`    | 生の音声データを分析可能なセグメントに処理         |
| `trigger_detector`   | 音声データ内の行動トリガーを検出                   |
| `individual_analyzer`| Individual Analysis Result を生成                  |
| `meeting_analyzer`   | Meeting Analysis Result を生成                     |
| `gemini_service`     | AI 分析用 Google Gemini API とのインターフェース   |
| `realtime_service`   | リアルタイムセッションイベントと更新を処理         |
| `report_generator`   | Monthly Report ドキュメントを生成                  |
| `cleanup_service`    | データ保持ポリシーの適用とスタイルセッションの整理 |

### インストール時の初期データ

- **Voice Analyzer Settings** がデフォルト値で自動作成されます: `analysis_interval_sec = 10`、`trigger_threshold = 0.3`、`data_retention_days = 90`、両モード有効。
- **ロール**（Mind Analyzer User、Manager、Admin）が自動作成されます。
