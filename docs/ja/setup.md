# セットアップガイド

本ガイドでは、**lifegence_industry** アプリのインストールと設定手順を説明します。本アプリは Frappe/ERPNext 向けの業界特化モジュールとして、レセプト（Medical Receipt）、貿易管理（Trade Management）、マインド分析（Mind Analyzer）の3つのモジュールを提供します。

> **ライセンス**: 本ソフトウェアは [MIT ライセンス](../../LICENSE) で提供されます。

## 前提条件

| 要件             | バージョン |
|------------------|------------|
| Python           | 3.14 以上  |
| Frappe Framework | v16 以上   |
| ERPNext          | v16 以上   |

Frappe Bench 環境が構築済みで、少なくとも1つのサイトが存在することを確認してください。

## インストール

### 1. アプリの取得

```bash
bench get-app https://github.com/lifegence/lifegence-industry.git
```

### 2. サイトへのインストール

```bash
bench --site your-site install-app lifegence_industry
```

### 3. マイグレーションの実行

```bash
bench --site your-site migrate
```

`after_install` フックにより、以下の処理が自動的に実行されます。

- デフォルト値を持つ **Trade Settings** の作成。
- **Item** DocType への輸出管理用カスタムフィールドの追加（`export_control_class`、`dual_use_flag`、`catch_all_number`、`export_license_required`）。
- デフォルト値を持つ **Voice Analyzer Settings** の作成。
- マインド分析用ロールの作成: **Mind Analyzer User**、**Mind Analyzer Manager**、**Mind Analyzer Admin**。

## インストール後の設定

### レセプトモジュール

1. **Medical Receipt Settings** を開き、医療機関情報を入力します。
   - `clinic_code`（7桁の医療機関コード）
   - `clinic_name`（医療機関名）
   - `clinic_prefecture`（所在地の都道府県、47都道府県から選択）
   - `default_insurance_type`（デフォルト保険種別）
   - `point_unit_price`（点数単価、デフォルト10、1点=10円）
   - `submission_method`（提出方法：電子請求 または 紙請求）
   - `submission_deadline_day`（提出期限日、デフォルト10日）
2. **Disease Master**（傷病名マスタ）と **Medical Service Master**（診療行為マスタ）のレコードをインポートまたは作成します。
3. **Fee Schedule Revision**（点数表改定）エントリを作成し、診療報酬の自動計算を有効にします。

### 貿易管理モジュール

1. **Trade Settings** を開き、以下を設定します。
   - デフォルト Incoterms（貿易条件）
   - デフォルト通関業者・フォワーダー
   - 自社の輸入者コード・輸出者コード
   - 自動作成フラグの切り替え（`auto_create_shipment_from_so`、`auto_create_shipment_from_po`、`auto_create_landed_cost`、`auto_compliance_check`）
2. マスタデータを登録します: **Port Master**（港湾マスタ）、**Vessel Master**（船舶マスタ）、**Shipping Line**（船会社）、**Airline Master**（航空会社）、**Freight Forwarder**（フォワーダー）、**Customs Broker**（通関業者）。
3. 制裁措置スクリーニングを利用する場合は、**Sanctions List Entry**（制裁リストエントリ）レコードを登録します。
4. **Item** DocType に「Trade / Export Control」セクションのカスタムフィールドが表示されることを確認します。

### マインド分析モジュール

1. **Voice Analyzer Settings** を開き、**Gemini API キー**（必須）を入力します。
2. 必要に応じて **Google Speech API キー**（音声認識精度向上用、任意）を入力します。
3. デフォルト閾値を確認・調整します。
   - `analysis_interval_sec`（分析間隔秒数、デフォルト: 10）
   - `trigger_threshold`（トリガー検出閾値、デフォルト: 0.3）
   - `data_retention_days`（データ保持日数、デフォルト: 90）
4. ユーザーにロールを割り当てます。
   - **Mind Analyzer User** -- 自己分析用に音声分析を利用可能。
   - **Mind Analyzer Manager** -- チーム分析結果やレポートを閲覧可能。
   - **Mind Analyzer Admin** -- 設定の変更、全データの閲覧が可能。

## オプション依存関係

| 依存先             | 使用モジュール  | 用途                                       |
|--------------------|-----------------|--------------------------------------------|
| Google Gemini API  | マインド分析    | AI による音声分析とインサイト生成          |
| Google Speech API  | マインド分析    | 音声認識精度の向上（任意）                 |

これらは外部 API サービスです。**Voice Analyzer Settings** で API キーを設定してください。

## アップデート

最新バージョンへの更新手順：

```bash
cd ~/frappe-bench
bench get-app --upgrade lifegence_industry
bench --site your-site migrate
```

アップグレード後は、新しい設定フィールドやマスタデータの要件がないか確認してください。破壊的変更についてはリリースノートを参照してください。

## 次のステップ

- [モジュールリファレンス](modules.md) -- 各モジュールの詳細ドキュメント。
- [設定リファレンス](configuration.md) -- 設定フィールドの完全なリファレンス。
- [トラブルシューティング](troubleshooting.md) -- よくある問題と解決方法。
