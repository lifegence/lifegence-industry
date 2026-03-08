# トラブルシューティング

**lifegence_industry** アプリのよくある問題と解決方法です。ここに記載されていない問題が発生した場合は、**ヘルプ > エラーログ** または bench コンソール出力を確認してください。

**目次**

- [レセプト](#レセプト)
- [貿易管理](#貿易管理)
- [マインド分析](#マインド分析)
- [共通](#共通)

---

## レセプト

### レセプトバリデーションで「明細行なし」エラー

**症状**: バリデーションチェックで、レセプトに明細行がないと報告される。

**原因**: レセプトに含まれる Patient Encounter に Encounter Service Line が存在しないか、レセプト生成時に対象の診療記録が取得されなかった。

**解決方法**:
1. 関連する Patient Encounter を開き、Encounter Service Line が存在し入力されていることを確認する。
2. 診療記録が「Submitted（提出済み）」ステータスであることを確認する。
3. 対象月のレセプトを再生成する。

### レセプトバリデーションで「傷病名なし」エラー

**症状**: バリデーションで傷病名の欠落が報告される。

**解決方法**: レセプトに紐づく Patient Encounter を開き、少なくとも1つの Encounter Diagnosis レコードを追加する。その後、レセプトを再生成する。

### レセプトバリデーションで「保険未有効」または「保険期間不一致」エラー

**症状**: 患者の保険が有効でない、または診療日をカバーしていないとバリデーションが報告する。

**解決方法**:
1. 対象患者の **Patient Insurance Info** レコードを開く。
2. 保険ステータスが有効であることを確認する。
3. 保険の有効期間が Patient Encounter の日付をカバーしていることを確認する。
4. データを修正し、レセプトを再生成する。

### レセプトバリデーションで「点数不整合」エラー

**症状**: レセプトの合計点数と明細行の点数合計が一致しない。

**原因**: レセプト生成後に点数計算が更新されたか、手動編集により不整合が発生した。

**解決方法**:
1. レセプトを開き、ヘッダーの合計と Receipt Detail Line の点数合計を比較する。
2. 元の診療記録がレセプト生成後に変更された場合は、レセプトを再生成する。

### 点数計算がゼロまたは想定外の金額を返す

**症状**: Patient Encounter の Submit 後、計算された点数がゼロまたは不正確。

**原因**: 点数表データが未設定または設定誤り。

**解決方法**:
1. **Fee Schedule Revision** レコードが存在し、少なくとも1つの有効日が診療日以前であることを確認する。
2. 診療記録の Service Line で参照されている **Medical Service Master** レコードに有効な点数コードがあることを確認する。
3. **Medical Receipt Settings** の `point_unit_price` が正しく設定されていることを確認する（デフォルト 10、1点 = 10円）。
4. エラーログで計算例外を確認する。

### 提出期限リマインダーメールが届かない

**症状**: 毎月5日にメールが届かない。

**解決方法**:
1. Frappe スケジューラが稼働していることを確認する: `bench doctor` またはスケジューラログを確認。
2. **設定 > メールアカウント** でメール設定が構成されていることを確認する。
3. `send_deadline_reminder` の失敗についてエラーログを確認する。

---

## 貿易管理

### 受注伝票 / 発注伝票から Trade Shipment が自動作成されない

**症状**: Sales Order または Purchase Order を Submit しても Trade Shipment が作成されない。

**原因**: 自動作成フラグがデフォルトで無効になっている。

**解決方法**:
1. **Trade Settings** を開く。
2. 該当するフラグを有効にする:
   - Sales Order の場合: `auto_create_shipment_from_so`
   - Purchase Order の場合: `auto_create_shipment_from_po`
3. 設定を保存して再試行する。

### Delivery Note / Purchase Receipt の Submit 時に船積みステータスが更新されない

**症状**: Delivery Note または Purchase Receipt を Submit しても、紐づく船積みのステータスが変更されない。

**解決方法**:
1. Delivery Note または Purchase Receipt が Trade Shipment にリンクされていることを確認する（参照フィールドまたはカスタムリンクを確認）。
2. Doc event ハンドラ（`delivery_note.on_submit` または `purchase_receipt.on_submit`）の例外についてエラーログを確認する。
3. Trade Shipment がキャンセル済みまたは完了済みなど、ステータス変更を妨げる状態でないことを確認する。

### 制裁措置スクリーニングで結果が返らない

**症状**: コンプライアンスチェックまたは制裁措置スクリーニングを実行しても、既知の制裁対象エンティティに対してもマッチが見つからない。

**原因**: **Sanctions List Entry** DocType が空。

**解決方法**:
1. Desk で **Sanctions List Entry** に移動する。
2. 事業に関連する制裁リスト / 取引禁止当事者リストのエントリをインポートまたは手動作成する。
3. データ登録後にスクリーニングを再実行する。

### Item DocType にカスタムフィールドが表示されない

**症状**: Item レコードに「Trade / Export Control」セクションが表示されない。

**解決方法**:
1. マイグレーションを実行してカスタムフィールドが適用されていることを確認する:
   ```bash
   bench --site your-site migrate
   ```
2. ブラウザキャッシュをクリアしてページをリロードする。
3. それでも表示されない場合は、インストールフックを手動で実行する:
   ```bash
   bench --site your-site console
   ```
   ```python
   from lifegence_industry.install import after_install
   after_install()
   ```

### ETA アラートや L/C 期限切れ通知が送信されない

**症状**: ETA 接近や信用状期限切れの日次アラートメールが届かない。

**解決方法**:
1. スケジューラが稼働していることを確認する。
2. Trade Shipment の Schedule エントリに ETA 日付が設定されていること、Letter of Credit に有効期限が設定されていることを確認する。
3. `check_eta_alerts` または `check_lc_expiry` の例外についてエラーログを確認する。

---

## マインド分析

### Gemini API エラー（認証またはクォータ）

**症状**: 分析が API エラーで失敗する。エラーログに認証失敗またはクォータ超過が表示される。

**解決方法**:
1. **Voice Analyzer Settings** を開き、`gemini_api_key` が正しく入力されていることを確認する。
2. Google Cloud Console で API キーが有効で失効していないことを確認する。
3. Gemini API のクォータを確認する。超過している場合は、リセットを待つか増加をリクエストする。
4. アプリ外で API キーが動作することをテストする。

### セッションがアクティブ状態のまま停止

**症状**: Voice Analysis Session がアクティブ表示だが、実際には使用されていない。ダッシュボードにスタイルセッションが表示される。

**原因**: セッションが正しく終了されなかった（例: セッション終了操作なしにブラウザを閉じた）。

**解決方法**:
- **自動**: システムは6時間ごとに `cleanup_stale_sessions` を実行し、24時間以上非アクティブなセッションをクローズする。
- **手動**: API でセッションを終了する:
  ```python
  from lifegence_industry.mind_analyzer.api.session import end_session
  end_session(session_name="VOICE-SESSION-XXXXX")
  ```
  またはキャンセルする:
  ```python
  from lifegence_industry.mind_analyzer.api.session import cancel_session
  cancel_session(session_name="VOICE-SESSION-XXXXX")
  ```

### セッション中に音声データが受信されない

**症状**: セッションが開始されたが分析結果が生成されない。Acoustic Statistics レコードが空。

**解決方法**:
1. ブラウザがマイクアクセス権限を持っていることを確認する。
2. 設定された間隔（`analysis_interval_sec`）で `analyze_audio` API エンドポイントに音声が送信されていることを確認する。
3. 音声フォーマットが audio_processor サービスでサポートされていることを確認する。
4. Mind Analyzer Dashboard ページでブラウザのデベロッパーコンソールに JavaScript エラーがないか確認する。

### 月次レポートが生成されない

**症状**: 対象期間の Monthly Report ドキュメントが表示されない。

**解決方法**:
1. 対象月に完了した分析セッションが存在することを確認する。
2. API または Monthly Report Viewer ページから手動でレポート生成をトリガーする。
3. `report_generator` サービスの例外についてエラーログを確認する。

### 分析結果が不正確に見える

**症状**: メトリクススコアが会話の内容と一致しない。

**解決方法**:
1. **Voice Analyzer Settings** の閾値を確認する。デフォルトの `trigger_threshold`（0.3）が環境に対して敏感すぎるまたは鈍すぎる場合がある。
2. 観察された行動に基づいて詳細トリガー閾値（沈黙スパイク、ヘッジワード、発話速度変化、言い直し頻度）を調整する。
3. 音声品質が十分であることを確認する -- 背景ノイズ、マイク音量の低さ、圧縮アーティファクトが分析精度に影響する場合がある。
4. `analysis_interval_sec` が適切であることを確認する。間隔が短すぎるとノイズの多い結果が出る可能性があり、長すぎると一時的なイベントを見逃す可能性がある。

---

## 共通

### データ保持とクリーンアップ

マインド分析モジュールは、設定された `data_retention_days`（デフォルト: 90日）を超えた分析データを自動的に削除します。これは日次スケジュールタスクとして実行されます。

保持期間を調整するには:
1. **Voice Analyzer Settings** を開く。
2. `data_retention_days` を希望する値に変更する。
3. 保存する。

クリーンアップで削除されるデータには、Voice Analysis Session、Individual/Meeting Analysis Result、Voice Trigger Event、Acoustic Statistics の閾値を超えたものが含まれます。

### スケジューラが稼働していない

全モジュールのスケジュールタスクが実行されない場合:

1. スケジューラの状態を確認する:
   ```bash
   bench doctor
   ```
2. サイトでスケジューラが有効であることを確認する:
   ```bash
   bench --site your-site enable-scheduler
   ```
3. バックグラウンドワーカーが稼働していることを確認する:
   ```bash
   bench --site your-site scheduler status
   ```

### 権限エラー

ユーザーが「Permission Denied」エラーを受け取る場合:

1. ユーザーに必要なロールが割り当てられていることを確認する（[設定リファレンス](configuration.md#ロール割り当て) を参照）。
2. マインド分析の場合、ユーザーに少なくとも **Mind Analyzer User** ロールがあることを確認する。
3. **設定 > ロール権限マネージャー** で DocType 権限を確認し、必要に応じて調整する。
