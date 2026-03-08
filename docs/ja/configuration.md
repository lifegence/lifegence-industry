# 設定リファレンス

**lifegence_industry** アプリのすべての設定項目の完全なリファレンスです。各モジュールには Frappe Desk からアクセスできる専用の Settings DocType があります。

**目次**

- [Medical Receipt Settings（レセプト設定）](#medical-receipt-settings)
- [Trade Settings（貿易管理設定）](#trade-settings)
- [Voice Analyzer Settings（音声分析設定）](#voice-analyzer-settings)
- [ロール割り当て](#ロール割り当て)

---

## Medical Receipt Settings

**DocType**: Medical Receipt Settings（Single）

**パス**: Medical Receipt Settings

| フィールド               | 型        | デフォルト   | 説明                                                            |
|--------------------------|-----------|-------------|-----------------------------------------------------------------|
| `clinic_code`            | Data      | --          | 7桁の医療機関コード                                            |
| `clinic_name`            | Data      | --          | 医療機関名                                                     |
| `clinic_prefecture`      | Select    | --          | 医療機関の所在都道府県（47都道府県から選択）                   |
| `default_insurance_type` | Select    | --          | 新規診療のデフォルト保険種別                                   |
| `point_unit_price`       | Currency  | 10          | 1点あたりの金額（円）                                          |
| `submission_method`      | Select    | --          | レセプト提出方法                                               |
| `submission_deadline_day`| Int       | 10          | 月の提出期限日                                                 |
| `auto_validate_on_generate` | Check | 0           | レセプト生成時に自動バリデーションを実行                       |

**保険種別の選択肢**

| 値                   | 日本語表記          |
|----------------------|---------------------|
| Social               | 社会保険            |
| National             | 国民健康保険        |
| Late-Stage Elderly   | 後期高齢者医療      |
| Public Expense       | 公費                |
| Self-Pay             | 自費                |

**提出方法の選択肢**

| 値          | 説明                           |
|-------------|--------------------------------|
| Electronic  | 電子請求                       |
| Paper       | 紙請求                         |

---

## Trade Settings

**DocType**: Trade Settings（Single）

**パス**: Trade Settings

### 一般設定

| フィールド                    | 型      | デフォルト | 説明                                         |
|-------------------------------|---------|-----------|----------------------------------------------|
| `default_incoterms`           | Link    | --        | 新規船積みのデフォルト Incoterms（貿易条件） |
| `default_customs_broker`      | Link    | --        | 申告用のデフォルト通関業者                   |
| `default_freight_forwarder`   | Link    | --        | 船積み用のデフォルトフォワーダー             |
| `company_importer_code`       | Data    | --        | 自社の輸入者登録コード                       |
| `company_exporter_code`       | Data    | --        | 自社の輸出者登録コード                       |

### 自動化フラグ

| フィールド                      | 型    | デフォルト | 説明                                           |
|---------------------------------|-------|-----------|------------------------------------------------|
| `auto_create_shipment_from_so`  | Check | 0         | 受注伝票の Submit 時に輸出船積みを自動作成     |
| `auto_create_shipment_from_po`  | Check | 0         | 発注伝票の Submit 時に輸入船積みを自動作成     |
| `auto_create_landed_cost`       | Check | 1         | 船積み費用からランデッドコスト伝票を自動作成   |
| `auto_compliance_check`         | Check | 0         | 船積み作成時にコンプライアンスチェックを自動実行 |

### AI 機能（スタブ）

| フィールド                    | 型    | デフォルト | 説明                                       |
|-------------------------------|-------|-----------|---------------------------------------------|
| `enable_ai_hs_suggestion`     | Check | 0         | AI HS コード提案の有効化（将来実装）        |
| `enable_ai_document_check`    | Check | 0         | AI 書類検証の有効化（将来実装）             |

---

## Voice Analyzer Settings

**DocType**: Voice Analyzer Settings（Single）

**パス**: Voice Analyzer Settings

### API キー

| フィールド             | 型       | 必須 | 説明                                     |
|------------------------|----------|------|------------------------------------------|
| `gemini_api_key`       | Password | はい | AI 分析用 Google Gemini API キー         |
| `google_speech_api_key`| Password | いいえ | 音声認識用 Google Speech API キー       |

### 一般設定

| フィールド               | 型    | デフォルト | 説明                                           |
|--------------------------|-------|-----------|------------------------------------------------|
| `analysis_interval_sec`  | Int   | 10        | 音声分析サイクルの間隔（秒）                   |
| `trigger_threshold`      | Float | 0.3       | トリガー検出の基本感度閾値（0〜1）             |
| `data_retention_days`    | Int   | 90        | 分析データの保持日数（超過分はクリーンアップ） |
| `enable_individual_mode` | Check | 1         | 個人（単一人物）分析モードの有効化             |
| `enable_meeting_mode`    | Check | 1         | ミーティング（グループ）分析モードの有効化     |

### 詳細トリガー閾値

個別のトリガータイプの感度を制御します。環境に合わせて、誤検知を減らしたり検出感度を上げたりするために調整してください。

| フィールド                           | 型    | デフォルト | 単位     | 説明                                     |
|--------------------------------------|-------|---------|----------|------------------------------------------|
| `silence_spike_threshold_ms`         | Int   | 3000    | ミリ秒   | フラグする最小沈黙時間                   |
| `hedge_words_per_min_threshold`      | Int   | 5       | 回/分    | アラートをトリガーするヘッジワード頻度   |
| `speech_rate_change_pct_threshold`   | Int   | 30      | %        | フラグする発話速度の変化率               |
| `restart_per_min_threshold`          | Int   | 4       | 回/分    | フラグする文の言い直し頻度               |

---

## ロール割り当て

### マインド分析ロール

これらのロールはインストール時に自動作成されます。**設定 > ユーザー > ロール** からユーザーに割り当ててください。

| ロール                 | Desk アクセス | 説明                                          |
|------------------------|---------------|-----------------------------------------------|
| Mind Analyzer User     | あり          | 自己分析用に音声分析を利用可能               |
| Mind Analyzer Manager  | あり          | チーム分析結果やレポートを閲覧可能           |
| Mind Analyzer Admin    | あり          | 音声分析設定の変更が可能                     |

**推奨割り当て**:

| ユーザー種別     | 割り当てるロール                                           |
|------------------|------------------------------------------------------------|
| 一般社員         | Mind Analyzer User                                         |
| チームリーダー   | Mind Analyzer User、Mind Analyzer Manager                  |
| 人事 / 管理者    | Mind Analyzer User、Mind Analyzer Manager、Mind Analyzer Admin |

### レセプト・貿易管理のロール

これらのモジュールは標準の ERPNext ロールを使用します。ユーザーに適切な権限が付与されていることを確認してください。

| モジュール      | 関連する ERPNext ロール                                     |
|-----------------|-------------------------------------------------------------|
| レセプト        | Healthcare Practitioner、Healthcare Administrator           |
| 貿易管理        | Purchase User、Purchase Manager、Sales User、Sales Manager、Accounts User |

組織の要件に応じて、**設定 > ロール権限マネージャー** から DocType 権限を調整してください。
