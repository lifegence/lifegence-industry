frappe.pages['monthly-report-viewer'].on_page_load = function(wrapper) {
    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: __('Monthly Wellness Report'),
        single_column: true
    });

    // Load the page template
    $(frappe.render_template('monthly_report_viewer')).appendTo(page.body);

    // Initialize the controller
    new MonthlyReportViewer(page);
};

class MonthlyReportViewer {
    constructor(page) {
        this.page = page;
        this.$wrapper = $(page.body);
        this.currentReport = null;
        this.charts = {};

        this.init();
    }

    init() {
        this.bindEvents();
        this.loadAvailableMonths();
    }

    bindEvents() {
        const self = this;

        // Report month selector
        this.$wrapper.find('#report-month-select').on('change', function() {
            const reportName = $(this).val();
            if (reportName) {
                self.loadReport(reportName);
            } else {
                self.showNoReport();
            }
        });

        // Generate report button
        this.$wrapper.find('#generate-report-btn').on('click', function() {
            self.showGenerateDialog();
        });
    }

    loadAvailableMonths() {
        const self = this;

        frappe.call({
            method: 'lifegence_industry.mind_analyzer.api.reports.get_available_report_months',
            callback: function(r) {
                if (r.message && r.message.success) {
                    self.populateMonthSelector(r.message.months);
                }
            }
        });

        // Also load existing reports
        frappe.call({
            method: 'lifegence_industry.mind_analyzer.api.reports.get_my_monthly_reports',
            callback: function(r) {
                if (r.message && r.message.success && r.message.reports.length > 0) {
                    self.addReportsToSelector(r.message.reports);
                    // Auto-load the latest report
                    const latestReport = r.message.reports[0];
                    self.$wrapper.find('#report-month-select').val(latestReport.name).trigger('change');
                }
            }
        });
    }

    populateMonthSelector(months) {
        const $select = this.$wrapper.find('#report-month-select');
        $select.empty();
        $select.append('<option value="">' + __('Select a report...') + '</option>');

        // Add months that have data but no report yet
        months.forEach(month => {
            if (!month.has_report) {
                $select.append(
                    `<option value="generate:${month.month}" data-generate="true">
                        ${month.month_display} (${month.session_count} ${__('sessions')}) - ${__('Generate')}
                    </option>`
                );
            }
        });
    }

    addReportsToSelector(reports) {
        const $select = this.$wrapper.find('#report-month-select');

        // Add existing reports at the top
        reports.forEach(report => {
            const scoreDisplay = report.overall_score ? ` - ${__('Score')}: ${report.overall_score}` : '';
            $select.prepend(
                `<option value="${report.name}">
                    ${report.report_month_display}${scoreDisplay}
                </option>`
            );
        });
    }

    loadReport(reportNameOrAction) {
        const self = this;

        // Check if this is a generate action
        if (reportNameOrAction.startsWith('generate:')) {
            const month = reportNameOrAction.replace('generate:', '');
            this.generateReport(month);
            return;
        }

        this.showLoading();

        frappe.call({
            method: 'lifegence_industry.mind_analyzer.api.reports.get_monthly_report_detail',
            args: { report_name: reportNameOrAction },
            callback: function(r) {
                self.hideLoading();
                if (r.message && r.message.success) {
                    self.currentReport = r.message.report;
                    self.renderReport();
                } else {
                    self.showNoReport();
                    frappe.msgprint(r.message.message || __('Failed to load report'));
                }
            },
            error: function() {
                self.hideLoading();
                self.showNoReport();
            }
        });
    }

    generateReport(month) {
        const self = this;

        frappe.confirm(
            __('Generate a report for {0}?', [month]),
            function() {
                self.showLoading();

                frappe.call({
                    method: 'lifegence_industry.mind_analyzer.api.reports.generate_monthly_report',
                    args: { report_month: month },
                    callback: function(r) {
                        self.hideLoading();
                        if (r.message && r.message.success) {
                            frappe.msgprint(__('Report generated successfully!'));
                            self.currentReport = r.message.report;
                            self.renderReport();
                            // Refresh the selector
                            self.loadAvailableMonths();
                        } else {
                            frappe.msgprint(r.message.message || __('Failed to generate report'));
                        }
                    },
                    error: function() {
                        self.hideLoading();
                        frappe.msgprint(__('Failed to generate report'));
                    }
                });
            }
        );
    }

    showGenerateDialog() {
        const self = this;

        frappe.call({
            method: 'lifegence_industry.mind_analyzer.api.reports.get_available_report_months',
            callback: function(r) {
                if (!r.message || !r.message.success) {
                    frappe.msgprint(__('Failed to load available months'));
                    return;
                }

                const months = r.message.months.filter(m => !m.has_report);

                if (months.length === 0) {
                    frappe.msgprint(__('All months already have reports generated.'));
                    return;
                }

                const options = months.map(m =>
                    `${m.month}|${m.month_display} (${m.session_count} ${__('sessions')})`
                ).join('\n');

                const d = new frappe.ui.Dialog({
                    title: __('Generate Monthly Report'),
                    fields: [
                        {
                            fieldname: 'month',
                            fieldtype: 'Select',
                            label: __('Select Month'),
                            options: options,
                            reqd: 1
                        }
                    ],
                    primary_action_label: __('Generate'),
                    primary_action: function(values) {
                        d.hide();
                        const month = values.month.split('|')[0];
                        self.generateReport(month);
                    }
                });

                d.show();
            }
        });
    }

    renderReport() {
        const report = this.currentReport;
        if (!report) return;

        this.$wrapper.find('#report-content').show();
        this.$wrapper.find('#no-report-message').hide();

        // Header
        this.$wrapper.find('#report-month-title').text(report.report_month_display);

        // Executive Summary
        this.$wrapper.find('#overall-score').text(report.overall_score);
        this.setTrendIndicator('#overall-trend', report.overall_trend);
        this.$wrapper.find('#total-sessions').text(report.total_sessions);
        this.$wrapper.find('#total-time').text(report.total_analysis_time_minutes);
        this.$wrapper.find('#total-triggers').text(report.trigger_analysis.total_triggers);

        // AI Insights
        this.$wrapper.find('#ai-summary').text(report.ai_insights.summary || __('No AI summary available'));
        this.$wrapper.find('#ai-advice').text(report.ai_insights.advice || __('No recommendations available'));
        this.renderFocusAreas(report.ai_insights.focus_areas);

        // Individual Metrics
        this.renderIndividualMetrics(report.individual_metrics);

        // Meeting Metrics
        this.renderMeetingMetrics(report.meeting_metrics);

        // Trigger Analysis
        this.renderTriggerAnalysis(report.trigger_analysis, report.chart_data.trigger_breakdown);

        // Render simple charts (no Chart.js dependency)
        this.renderSimpleCharts(report.chart_data);
    }

    setTrendIndicator(selector, trend) {
        const $el = this.$wrapper.find(selector);
        $el.removeClass('improving stable declining');

        if (trend === 'Improving') {
            $el.addClass('improving').html('<i class="fa fa-arrow-up"></i> ' + __('Improving'));
        } else if (trend === 'Declining') {
            $el.addClass('declining').html('<i class="fa fa-arrow-down"></i> ' + __('Declining'));
        } else {
            $el.addClass('stable').html('<i class="fa fa-minus"></i> ' + __('Stable'));
        }
    }

    renderFocusAreas(areas) {
        const $container = this.$wrapper.find('#focus-areas');
        $container.empty();

        if (areas && areas.length > 0) {
            areas.forEach(area => {
                $container.append(`<span class="focus-tag">${area}</span>`);
            });
        }
    }

    renderIndividualMetrics(metrics) {
        // Stress (inverted - lower is better)
        this.setMetricBar('#stress-bar', '#stress-value', metrics.avg_stress_load, true);
        // Anxiety (inverted)
        this.setMetricBar('#anxiety-bar', '#anxiety-value', metrics.avg_anxiety, true);
        // Cognitive Load (inverted)
        this.setMetricBar('#cognitive-bar', '#cognitive-value', metrics.avg_cognitive_load, true);
        // Confidence (higher is better)
        this.setMetricBar('#confidence-bar', '#confidence-value', metrics.avg_confidence, false);
        // Stability (higher is better)
        this.setMetricBar('#stability-bar', '#stability-value', metrics.avg_stability, false);
    }

    renderMeetingMetrics(metrics) {
        if (metrics.meeting_count === 0) {
            this.$wrapper.find('#meeting-section').hide();
            return;
        }

        this.$wrapper.find('#meeting-section').show();
        this.$wrapper.find('#ps-score').text(metrics.avg_ps_score);
        this.$wrapper.find('#meeting-count').text(metrics.meeting_count);

        this.setPSBar('#speak-up-bar', '#speak-up-value', metrics.avg_speak_up);
        this.setPSBar('#respect-bar', '#respect-value', metrics.avg_respect);
        this.setPSBar('#error-tolerance-bar', '#error-tolerance-value', metrics.avg_error_tolerance);
    }

    renderTriggerAnalysis(analysis, breakdown) {
        this.$wrapper.find('#trigger-total').text(analysis.total_triggers);
        this.$wrapper.find('#trigger-high').text(analysis.high_severity_triggers);
        this.$wrapper.find('#trigger-common').text(this.translateTriggerType(analysis.most_common_trigger) || '--');
    }

    setMetricBar(barSelector, valueSelector, value, inverted) {
        const $bar = this.$wrapper.find(barSelector);
        const $value = this.$wrapper.find(valueSelector);

        $value.text(value + '%');
        $bar.css('width', value + '%');

        // Color based on value
        $bar.removeClass('good warning bad');
        if (inverted) {
            // Lower is better
            if (value < 30) $bar.addClass('good');
            else if (value < 60) $bar.addClass('warning');
            else $bar.addClass('bad');
        } else {
            // Higher is better
            if (value > 70) $bar.addClass('good');
            else if (value > 40) $bar.addClass('warning');
            else $bar.addClass('bad');
        }
    }

    setPSBar(barSelector, valueSelector, value) {
        const $bar = this.$wrapper.find(barSelector);
        const $value = this.$wrapper.find(valueSelector);

        $value.text(value + '%');
        $bar.css('width', value + '%');

        // PS scores - higher is better
        $bar.removeClass('good warning bad');
        if (value > 70) $bar.addClass('good');
        else if (value > 50) $bar.addClass('warning');
        else $bar.addClass('bad');
    }

    renderSimpleCharts(chartData) {
        // Render daily stress as a simple bar chart
        const $stressChart = this.$wrapper.find('#stress-trend-chart');
        if (chartData.daily_stress && chartData.daily_stress.length > 0) {
            let html = '<div class="simple-bar-chart">';
            const maxStress = Math.max(...chartData.daily_stress.map(d => d.stress));
            chartData.daily_stress.forEach(d => {
                const height = maxStress > 0 ? (d.stress / maxStress * 100) : 0;
                const date = d.date.substring(5); // MM-DD
                html += `
                    <div class="bar-item" title="${d.date}: ${(d.stress * 100).toFixed(1)}%">
                        <div class="bar" style="height: ${height}%"></div>
                        <div class="bar-label">${date}</div>
                    </div>
                `;
            });
            html += '</div>';
            $stressChart.html(html);
        } else {
            $stressChart.html('<div class="text-muted text-center" style="padding: 50px;">No data available</div>');
        }

        // Render trigger breakdown as simple pills
        const $triggerChart = this.$wrapper.find('#trigger-chart');
        if (chartData.trigger_breakdown && Object.keys(chartData.trigger_breakdown).length > 0) {
            let html = '<div class="trigger-breakdown-list">';
            const total = Object.values(chartData.trigger_breakdown).reduce((a, b) => a + b, 0);
            Object.entries(chartData.trigger_breakdown).forEach(([type, count]) => {
                const pct = total > 0 ? Math.round(count / total * 100) : 0;
                html += `
                    <div class="trigger-breakdown-item">
                        <span class="trigger-type-label">${this.translateTriggerType(type)}</span>
                        <div class="trigger-bar-container">
                            <div class="trigger-bar" style="width: ${pct}%"></div>
                        </div>
                        <span class="trigger-count">${count}</span>
                    </div>
                `;
            });
            html += '</div>';
            $triggerChart.html(html);
        } else {
            $triggerChart.html('<div class="text-muted text-center" style="padding: 50px;">No triggers detected</div>');
        }

        // Render weekly trend as simple table
        const $weeklyChart = this.$wrapper.find('#weekly-trend-chart');
        if (chartData.weekly_summary && chartData.weekly_summary.length > 0) {
            let html = '<table class="weekly-trend-table"><thead><tr>';
            html += `<th>${__('Week')}</th><th>${__('Stress')}</th><th>${__('Stability')}</th><th>${__('PS Score')}</th><th>${__('Sessions')}</th>`;
            html += '</tr></thead><tbody>';
            chartData.weekly_summary.forEach(w => {
                html += `<tr>
                    <td>${__('Week')} ${w.week}</td>
                    <td>${w.avg_stress ? (w.avg_stress * 100).toFixed(0) + '%' : '--'}</td>
                    <td>${w.avg_stability ? (w.avg_stability * 100).toFixed(0) + '%' : '--'}</td>
                    <td>${w.avg_ps_score ? (w.avg_ps_score * 100).toFixed(0) + '%' : '--'}</td>
                    <td>${w.session_count}</td>
                </tr>`;
            });
            html += '</tbody></table>';
            $weeklyChart.html(html);
        } else {
            $weeklyChart.html('<div class="text-muted text-center" style="padding: 50px;">No weekly data available</div>');
        }
    }

    translateTriggerType(type) {
        const translations = {
            'silence_spike': __('Silence Spike'),
            'apology_phrase': __('Apology Phrase'),
            'hedge_increase': __('Hedge Words'),
            'speech_rate_change': __('Speech Rate Change'),
            'restart_increase': __('Speech Restarts'),
            'interruption': __('Interruption'),
            'overlap': __('Overlap'),
            'power_imbalance': __('Power Imbalance')
        };
        return translations[type] || type;
    }

    showLoading() {
        this.$wrapper.find('#loading-indicator').show();
        this.$wrapper.find('#report-content').hide();
        this.$wrapper.find('#no-report-message').hide();
    }

    hideLoading() {
        this.$wrapper.find('#loading-indicator').hide();
    }

    showNoReport() {
        this.$wrapper.find('#report-content').hide();
        this.$wrapper.find('#no-report-message').show();
    }
}
