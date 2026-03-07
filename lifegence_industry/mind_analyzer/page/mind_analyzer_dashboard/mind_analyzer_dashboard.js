frappe.pages['mind-analyzer-dashboard'].on_page_load = function(wrapper) {
    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Mind Analyzer',
        single_column: true
    });

    // Load the dashboard
    $(frappe.render_template('mind_analyzer_dashboard')).appendTo(page.body);

    // Initialize the controller
    new MindAnalyzerDashboard(page);
};

class MindAnalyzerDashboard {
    constructor(page) {
        this.page = page;
        this.$wrapper = $(page.body);
        this.selectedSession = null;

        this.init();
    }

    init() {
        this.bindEvents();
        this.loadSummary();
        this.loadSessions();
        this.loadRecentTriggers();
        this.setupRealtime();
    }

    bindEvents() {
        const self = this;

        // Refresh button
        this.$wrapper.find('.va-refresh-btn').on('click', () => {
            this.refresh();
        });

        // Filter changes
        this.$wrapper.find('.va-mode-filter, .va-period-filter').on('change', () => {
            this.loadSessions();
        });

        // Session click
        this.$wrapper.on('click', '.va-session-item', function() {
            const sessionName = $(this).data('name');
            self.showSessionDetail(sessionName);
        });

        // Close detail
        this.$wrapper.find('.va-close-detail').on('click', () => {
            this.hideSessionDetail();
        });
    }

    refresh() {
        this.loadSummary();
        this.loadSessions();
        this.loadRecentTriggers();
        frappe.show_alert({ message: '更新しました', indicator: 'green' });
    }

    async loadSummary() {
        try {
            const response = await frappe.call({
                method: 'lifegence_mind_analyzer.api.reports.get_summary',
                args: { days: 30 }
            });

            const summary = response.message || {};
            this.$wrapper.find('[data-summary="total_sessions"]').text(summary.total_sessions || 0);
            this.$wrapper.find('[data-summary="avg_stress"]').text(
                summary.avg_stress ? Math.round(summary.avg_stress * 100) + '%' : '--'
            );
            this.$wrapper.find('[data-summary="avg_ps"]').text(
                summary.avg_ps ? Math.round(summary.avg_ps * 100) + '%' : '--'
            );
            this.$wrapper.find('[data-summary="total_triggers"]').text(summary.total_triggers || 0);
        } catch (error) {
            console.error('Failed to load summary:', error);
        }
    }

    async loadSessions() {
        const mode = this.$wrapper.find('.va-mode-filter').val();
        const period = this.$wrapper.find('.va-period-filter').val();

        try {
            const response = await frappe.call({
                method: 'lifegence_mind_analyzer.api.session.get_session_history',
                args: {
                    limit: 50,
                    mode: mode || null,
                    days: period === 'all' ? null : parseInt(period)
                }
            });

            const sessions = response.message.sessions || [];
            const $list = this.$wrapper.find('.va-sessions-list');

            if (sessions.length === 0) {
                $list.html('<p class="va-no-sessions">セッションがありません</p>');
                return;
            }

            const html = sessions.map(s => `
                <div class="va-session-item" data-name="${s.name}">
                    <div class="va-session-info">
                        <span class="va-session-mode ${s.mode === 'Individual' ? 'va-mode-individual' : 'va-mode-meeting'}">
                            ${s.mode === 'Individual' ? '個人' : '会議'}
                        </span>
                        <span class="va-session-source">${s.source || 'chat'}</span>
                        <span class="va-session-date">${frappe.datetime.str_to_user(s.start_time)}</span>
                    </div>
                    <div class="va-session-metrics">
                        ${s.mode === 'Individual' ? `
                            <span class="va-metric">
                                <span class="va-metric-label">ストレス</span>
                                <span class="va-metric-value ${this.getStressClass(s.avg_stress_load)}">${s.avg_stress_load ? Math.round(s.avg_stress_load * 100) + '%' : '--'}</span>
                            </span>
                        ` : `
                            <span class="va-metric">
                                <span class="va-metric-label">PS</span>
                                <span class="va-metric-value ${this.getPsClass(s.avg_ps_score)}">${s.avg_ps_score ? Math.round(s.avg_ps_score * 100) + '%' : '--'}</span>
                            </span>
                        `}
                        <span class="va-metric">
                            <span class="va-metric-label">時間</span>
                            <span class="va-metric-value">${s.duration_seconds ? this.formatDuration(s.duration_seconds) : '--'}</span>
                        </span>
                        <span class="va-metric">
                            <span class="va-metric-label">トリガー</span>
                            <span class="va-metric-value">${s.trigger_count || 0}</span>
                        </span>
                    </div>
                </div>
            `).join('');

            $list.html(html);
        } catch (error) {
            console.error('Failed to load sessions:', error);
            this.$wrapper.find('.va-sessions-list').html('<p class="va-error">読み込みに失敗しました</p>');
        }
    }

    async loadRecentTriggers() {
        try {
            const response = await frappe.call({
                method: 'lifegence_mind_analyzer.api.reports.get_recent_triggers',
                args: { limit: 10 }
            });

            const triggers = response.message || [];
            const $list = this.$wrapper.find('.va-triggers-list');

            if (triggers.length === 0) {
                $list.html('<p class="va-no-triggers">トリガーは検出されていません</p>');
                return;
            }

            const html = triggers.map(t => `
                <div class="va-trigger-item" data-severity="${this.getSeverityClass(t.severity)}">
                    <div class="va-trigger-header">
                        <span class="va-trigger-type">${this.getTriggerLabel(t.trigger_type)}</span>
                        <span class="va-trigger-time">${frappe.datetime.prettyDate(t.timestamp)}</span>
                    </div>
                    <div class="va-trigger-evidence">${t.evidence || ''}</div>
                </div>
            `).join('');

            $list.html(html);
        } catch (error) {
            console.error('Failed to load triggers:', error);
        }
    }

    async showSessionDetail(sessionName) {
        try {
            const response = await frappe.call({
                method: 'lifegence_mind_analyzer.api.session.get_session_detail',
                args: { session_name: sessionName }
            });

            const session = response.message;
            if (!session) return;

            this.selectedSession = sessionName;
            const $detail = this.$wrapper.find('.va-detail-content');

            let metricsHtml = '';
            if (session.mode === 'Individual') {
                metricsHtml = `
                    <div class="va-detail-metrics">
                        <h4>個人分析結果</h4>
                        <div class="va-metrics-grid">
                            ${this.renderMetricBar('ストレス負荷', session.avg_stress_load, true)}
                            ${this.renderMetricBar('不安・不確実性', session.avg_anxiety, true)}
                            ${this.renderMetricBar('認知負荷', session.avg_cognitive_load, true)}
                            ${this.renderMetricBar('自信・主張性', session.avg_confidence, false)}
                            ${this.renderMetricBar('安定性', session.avg_stability, false)}
                        </div>
                    </div>
                `;
            } else {
                metricsHtml = `
                    <div class="va-detail-metrics">
                        <h4>会議分析結果 (心理的安全性)</h4>
                        <div class="va-ps-score-display">
                            <span class="va-ps-big-number">${session.avg_ps_score ? Math.round(session.avg_ps_score * 100) : '--'}</span>
                            <span class="va-ps-label">PS Score</span>
                        </div>
                        <div class="va-metrics-grid">
                            ${this.renderMetricBar('発言の自由度', session.avg_speak_up, false)}
                            ${this.renderMetricBar('対人尊重', session.avg_respect, false)}
                            ${this.renderMetricBar('失敗許容度', session.avg_error_tolerance, false)}
                            ${this.renderMetricBar('権力バランス', session.avg_power_balance, false)}
                        </div>
                    </div>
                `;
            }

            const triggersHtml = session.triggers && session.triggers.length > 0
                ? session.triggers.map(t => `
                    <div class="va-trigger-item" data-severity="${this.getSeverityClass(t.severity)}">
                        <span class="va-trigger-type">${this.getTriggerLabel(t.trigger_type)}</span>
                        <span class="va-trigger-evidence">${t.evidence || ''}</span>
                    </div>
                `).join('')
                : '<p class="va-no-triggers">トリガーなし</p>';

            $detail.html(`
                <div class="va-detail-header-info">
                    <span class="va-session-mode ${session.mode === 'Individual' ? 'va-mode-individual' : 'va-mode-meeting'}">
                        ${session.mode === 'Individual' ? '個人分析' : '会議分析'}
                    </span>
                    <span class="va-detail-date">${frappe.datetime.str_to_user(session.start_time)}</span>
                    <span class="va-detail-duration">${session.duration_seconds ? this.formatDuration(session.duration_seconds) : '--'}</span>
                </div>
                ${session.meeting_title ? `<h4 class="va-meeting-title">${session.meeting_title}</h4>` : ''}
                ${metricsHtml}
                <div class="va-detail-triggers">
                    <h4>検出されたトリガー (${session.triggers ? session.triggers.length : 0}件)</h4>
                    ${triggersHtml}
                </div>
            `);

            this.$wrapper.find('.va-detail-panel').show();
        } catch (error) {
            console.error('Failed to load session detail:', error);
            frappe.msgprint(__('セッション詳細の読み込みに失敗しました'));
        }
    }

    hideSessionDetail() {
        this.selectedSession = null;
        this.$wrapper.find('.va-detail-panel').hide();
    }

    renderMetricBar(label, value, isNegative) {
        const percentage = value ? Math.round(value * 100) : 0;
        let colorClass = 'va-color-neutral';
        if (value !== null && value !== undefined) {
            if (isNegative) {
                colorClass = value > 0.7 ? 'va-color-danger' : value > 0.4 ? 'va-color-warning' : 'va-color-success';
            } else {
                colorClass = value > 0.7 ? 'va-color-success' : value > 0.4 ? 'va-color-warning' : 'va-color-danger';
            }
        }
        return `
            <div class="va-metric-bar-container">
                <div class="va-metric-bar-header">
                    <span class="va-metric-bar-label">${label}</span>
                    <span class="va-metric-bar-value">${value ? percentage + '%' : '--'}</span>
                </div>
                <div class="va-metric-bar">
                    <div class="va-metric-bar-fill ${colorClass}" style="width: ${percentage}%"></div>
                </div>
            </div>
        `;
    }

    setupRealtime() {
        const self = this;

        // Listen for new analysis results
        frappe.realtime.on('mind_analyzer_session_complete', (data) => {
            self.refresh();
        });

        // Listen for new triggers
        frappe.realtime.on('mind_analyzer_trigger', (data) => {
            self.loadRecentTriggers();
        });
    }

    // Helper methods
    getStressClass(value) {
        if (!value) return '';
        if (value > 0.7) return 'va-color-danger';
        if (value > 0.4) return 'va-color-warning';
        return 'va-color-success';
    }

    getPsClass(value) {
        if (!value) return '';
        if (value > 0.7) return 'va-color-success';
        if (value > 0.4) return 'va-color-warning';
        return 'va-color-danger';
    }

    getSeverityClass(severity) {
        if (severity > 0.7) return 'high';
        if (severity > 0.4) return 'medium';
        return 'low';
    }

    getTriggerLabel(type) {
        const labels = {
            'silence_spike': '沈黙急増',
            'apology_phrase': '謝罪表現',
            'hedge_increase': 'ヘッジ増加',
            'speech_rate_change': '話速変化',
            'restart_increase': '言い直し増加',
            'interruption': '遮り',
            'overlap': '重複発話',
            'power_imbalance': '権力不均衡'
        };
        return labels[type] || type;
    }

    formatDuration(seconds) {
        if (seconds < 60) return `${seconds}秒`;
        if (seconds < 3600) return `${Math.round(seconds / 60)}分`;
        const hours = Math.floor(seconds / 3600);
        const mins = Math.round((seconds % 3600) / 60);
        return `${hours}時間${mins}分`;
    }
}
