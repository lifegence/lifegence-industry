frappe.pages['organization-dashboard'].on_page_load = function(wrapper) {
    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Organization Dashboard',
        single_column: true
    });

    // Load ECharts from CDN
    function loadECharts() {
        return new Promise((resolve, reject) => {
            if (typeof echarts !== 'undefined') {
                resolve();
                return;
            }
            const script = document.createElement('script');
            script.src = 'https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js';
            script.onload = resolve;
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }

    loadECharts().then(() => {
        $(frappe.render_template('organization_dashboard')).appendTo(page.body);
        new OrganizationDashboard(page);
    }).catch(err => {
        console.error('Failed to load ECharts:', err);
        frappe.msgprint('Failed to load charting library');
    });
};

class OrganizationDashboard {
    constructor(page) {
        this.page = page;
        this.$wrapper = $(page.body);
        this.currentDepartment = '';
        this.currentPeriod = 'month';
        this.charts = {};
        this.data = {
            summary: {},
            team: {},
            triggers: {},
            timeseries: [],
            deptTimeseries: {},
            deptComparison: {}
        };

        this.init();
    }

    init() {
        this.bindEvents();
        this.loadDepartments();
        this.loadData();
    }

    bindEvents() {
        const self = this;

        // Tab switching
        this.$wrapper.find('.tab').on('click', function() {
            const tabId = $(this).data('tab');
            self.switchTab(tabId);
        });

        // Filters
        this.$wrapper.find('#department-filter').on('change', function() {
            self.currentDepartment = $(this).val();
            self.loadData();
        });

        this.$wrapper.find('#period-filter').on('change', function() {
            self.currentPeriod = $(this).val();
            self.loadData();
        });

        // Refresh button
        this.$wrapper.find('#refresh-btn').on('click', function() {
            self.loadData();
            frappe.show_alert({message: 'Data refreshed', indicator: 'green'});
        });

        // Window resize for charts
        $(window).on('resize', () => {
            Object.values(this.charts).forEach(chart => chart && chart.resize());
        });
    }

    switchTab(tabId) {
        this.$wrapper.find('.tab').removeClass('active');
        this.$wrapper.find(`.tab[data-tab="${tabId}"]`).addClass('active');
        this.$wrapper.find('.tab-content').removeClass('active');
        this.$wrapper.find(`#tab-${tabId}`).addClass('active');

        // Resize charts when showing chart tabs
        setTimeout(() => {
            Object.values(this.charts).forEach(chart => chart && chart.resize());
        }, 100);
    }

    loadDepartments() {
        const self = this;

        frappe.call({
            method: 'frappe.client.get_list',
            args: {
                doctype: 'Department',
                filters: { is_group: 0 },
                fields: ['name'],
                limit_page_length: 0
            },
            callback: function(r) {
                if (r.message) {
                    const $select = self.$wrapper.find('#department-filter');
                    r.message.forEach(dept => {
                        $select.append(`<option value="${dept.name}">${dept.name}</option>`);
                    });
                }
            }
        });
    }

    loadData() {
        this.showLoading();

        Promise.all([
            this.loadTeamAnalysis(),
            this.loadTriggerAnalysis(),
            this.loadDepartmentSummary(),
            this.loadDepartmentTimeseries(),
            this.loadDepartmentComparison()
        ]).then(() => {
            this.hideLoading();
            this.renderOverview();
            this.renderCharts();
            this.generateAlerts();
        }).catch(err => {
            this.hideLoading();
            console.error('Failed to load data:', err);
        });
    }

    loadTeamAnalysis() {
        const self = this;

        return new Promise((resolve, reject) => {
            frappe.call({
                method: 'lifegence_mind_analyzer.api.reports.get_organization_team_analysis',
                args: {
                    period: this.currentPeriod,
                    department: this.currentDepartment || null
                },
                callback: function(r) {
                    if (r.message) {
                        self.data.team = r.message;
                    }
                    resolve();
                },
                error: function() {
                    self.data.team = { team_size: 0, members: [] };
                    resolve();
                }
            });
        });
    }

    loadTriggerAnalysis() {
        const self = this;

        return new Promise((resolve, reject) => {
            frappe.call({
                method: 'lifegence_mind_analyzer.api.reports.get_trigger_analysis',
                args: {
                    period: this.currentPeriod,
                    department: this.currentDepartment || null
                },
                callback: function(r) {
                    if (r.message) {
                        self.data.triggers = r.message;
                    }
                    resolve();
                },
                error: resolve
            });
        });
    }

    loadDepartmentSummary() {
        const self = this;

        if (!this.currentDepartment) {
            return Promise.resolve();
        }

        return new Promise((resolve, reject) => {
            frappe.call({
                method: 'lifegence_mind_analyzer.api.reports.get_department_summary',
                args: {
                    department: this.currentDepartment,
                    period: this.currentPeriod
                },
                callback: function(r) {
                    if (r.message) {
                        self.data.summary = r.message;
                    }
                    resolve();
                },
                error: resolve
            });
        });
    }

    loadDepartmentTimeseries() {
        const self = this;

        return new Promise((resolve, reject) => {
            frappe.call({
                method: 'lifegence_mind_analyzer.api.reports.get_department_timeseries',
                args: {
                    period: this.currentPeriod
                },
                callback: function(r) {
                    if (r.message) {
                        self.data.deptTimeseries = r.message;
                    }
                    resolve();
                },
                error: function() {
                    self.data.deptTimeseries = { departments: [], dates: [], series: {} };
                    resolve();
                }
            });
        });
    }

    loadDepartmentComparison() {
        const self = this;

        return new Promise((resolve, reject) => {
            frappe.call({
                method: 'lifegence_mind_analyzer.api.reports.get_department_comparison',
                callback: function(r) {
                    if (r.message) {
                        self.data.deptComparison = r.message;
                    }
                    resolve();
                },
                error: function() {
                    self.data.deptComparison = { departments: [] };
                    resolve();
                }
            });
        });
    }

    renderOverview() {
        const team = this.data.team;
        const triggers = this.data.triggers;

        // Stats bar
        this.$wrapper.find('#stat-employees').text(team.team_size || 0);
        this.$wrapper.find('#stat-sessions').text(triggers.total_sessions || 0);
        this.$wrapper.find('#stat-triggers').text(triggers.total_triggers || 0);
        this.$wrapper.find('#stat-period').text(this.getPeriodLabel());

        // Calculate averages from team data
        let avgStress = 0, avgPs = 0, activeCount = 0;
        if (team.members && team.members.length > 0) {
            const stressValues = team.members.filter(m => m.avg_stress != null).map(m => m.avg_stress);
            const psValues = team.members.filter(m => m.avg_ps != null).map(m => m.avg_ps);
            activeCount = team.active_members || 0;

            if (stressValues.length > 0) {
                avgStress = stressValues.reduce((a, b) => a + b, 0) / stressValues.length;
            }
            if (psValues.length > 0) {
                avgPs = psValues.reduce((a, b) => a + b, 0) / psValues.length;
            }
        }

        // KPI cards
        const stressPercent = Math.round(avgStress * 100);
        const psPercent = Math.round(avgPs * 100);
        const participationRate = team.team_size > 0 ? Math.round(activeCount / team.team_size * 100) : 0;

        this.$wrapper.find('#kpi-stress').text(stressPercent + '%')
            .removeClass('high medium low')
            .addClass(this.getStressClass(avgStress));

        this.$wrapper.find('#kpi-ps').text(psPercent + '%')
            .removeClass('high medium low')
            .addClass(this.getPsClass(avgPs));

        this.$wrapper.find('#kpi-participation').text(participationRate + '%');
        this.$wrapper.find('#kpi-triggers-per-session').text(triggers.triggers_per_session || 0);

        // Team count
        this.$wrapper.find('#member-count').text(`${activeCount} / ${team.team_size || 0} members`);

        // Summary table
        this.renderSummaryTable();

        // Team grid
        this.renderTeamGrid();

        // Trigger breakdown
        this.renderTriggerBreakdown();
    }

    renderSummaryTable() {
        const team = this.data.team;
        const $tbody = this.$wrapper.find('#summary-table-body');
        $tbody.empty();

        if (!team.members || team.members.length === 0) {
            $tbody.html(`
                <tr>
                    <td colspan="6" style="text-align: center; color: #94a3b8; padding: 2rem;">
                        No team data available
                    </td>
                </tr>
            `);
            return;
        }

        team.members.forEach(member => {
            const stress = member.avg_stress != null ? Math.round(member.avg_stress * 100) : '--';
            const ps = member.avg_ps != null ? Math.round(member.avg_ps * 100) : '--';
            const stressClass = this.getScoreBadgeClass(member.avg_stress, true);
            const psClass = this.getScoreBadgeClass(member.avg_ps, false);
            const status = this.getMemberStatus(member);

            $tbody.append(`
                <tr>
                    <td>
                        <strong>${member.employee_name || member.employee}</strong><br>
                        <small style="color: #94a3b8;">${member.designation || ''}</small>
                    </td>
                    <td>${member.total_sessions || 0}</td>
                    <td><span class="score-badge ${stressClass}">${stress}%</span></td>
                    <td><span class="score-badge ${psClass}">${ps}%</span></td>
                    <td>${member.total_sessions ? Math.round((member.total_sessions || 0) * 1.5) : '--'}</td>
                    <td><span class="status-badge ${status.class}">${status.label}</span></td>
                </tr>
            `);
        });
    }

    renderTeamGrid() {
        const team = this.data.team;
        const $grid = this.$wrapper.find('#team-grid');
        $grid.empty();

        if (!team.members || team.members.length === 0) {
            $grid.html(`
                <div style="text-align: center; padding: 2rem; color: #94a3b8;">
                    No team members found
                </div>
            `);
            return;
        }

        team.members.forEach(member => {
            const stress = member.avg_stress != null ? Math.round(member.avg_stress * 100) : '--';
            const ps = member.avg_ps != null ? Math.round(member.avg_ps * 100) : '--';
            const stressLevelClass = this.getStressLevelClass(member.avg_stress);

            $grid.append(`
                <div class="team-member-card ${stressLevelClass}">
                    <div class="member-header">
                        <div>
                            <div class="member-name">${member.employee_name || member.employee}</div>
                            <div class="member-role">${member.designation || ''}</div>
                        </div>
                    </div>
                    <div class="member-metrics">
                        <div class="member-metric">
                            <div class="member-metric-value ${this.getStressClass(member.avg_stress)}">${stress}%</div>
                            <div class="member-metric-label">Stress</div>
                        </div>
                        <div class="member-metric">
                            <div class="member-metric-value ${this.getPsClass(member.avg_ps)}">${ps}%</div>
                            <div class="member-metric-label">PS</div>
                        </div>
                        <div class="member-metric">
                            <div class="member-metric-value info">${member.total_sessions || 0}</div>
                            <div class="member-metric-label">Sessions</div>
                        </div>
                    </div>
                </div>
            `);
        });
    }

    renderTriggerBreakdown() {
        const triggers = this.data.triggers;
        const $list = this.$wrapper.find('#trigger-breakdown-list');
        $list.empty();

        // Trigger KPIs
        this.$wrapper.find('#trigger-total').text(triggers.total_triggers || 0);
        this.$wrapper.find('#trigger-per-session').text(triggers.triggers_per_session || 0);

        if (!triggers.by_type || Object.keys(triggers.by_type).length === 0) {
            $list.html(`
                <div style="text-align: center; padding: 2rem; color: #94a3b8;">
                    No triggers detected
                </div>
            `);
            this.$wrapper.find('#trigger-most-common').text('--');
            this.$wrapper.find('#trigger-high-severity').text('0');
            return;
        }

        const maxCount = Math.max(...Object.values(triggers.by_type).map(t => t.count));
        let mostCommon = '';
        let mostCommonCount = 0;
        let highSeverityCount = 0;

        Object.entries(triggers.by_type).forEach(([type, info]) => {
            const pct = maxCount > 0 ? (info.count / maxCount * 100) : 0;
            const severityClass = info.avg_severity > 0.6 ? 'severity-high' : info.avg_severity > 0.3 ? 'severity-medium' : 'severity-low';
            const severityLabel = info.avg_severity > 0.6 ? 'High' : info.avg_severity > 0.3 ? 'Medium' : 'Low';

            if (info.count > mostCommonCount) {
                mostCommonCount = info.count;
                mostCommon = type;
            }

            if (info.avg_severity > 0.6) {
                highSeverityCount += info.count;
            }

            $list.append(`
                <div class="trigger-breakdown-item">
                    <span class="trigger-type-label">${this.translateTriggerType(type)}</span>
                    <div class="trigger-bar-container">
                        <div class="trigger-bar ${severityClass}" style="width: ${pct}%"></div>
                    </div>
                    <span class="trigger-count">${info.count}</span>
                    <span class="trigger-severity ${severityClass.replace('severity-', 'score-')}">${severityLabel}</span>
                </div>
            `);
        });

        this.$wrapper.find('#trigger-most-common').text(this.translateTriggerType(mostCommon));
        this.$wrapper.find('#trigger-high-severity').text(highSeverityCount);
    }

    renderCharts() {
        this.renderGaugeCharts();
        this.renderTimelineChart();
        this.renderTriggersBarChart();
        this.renderRadarChart();
        this.renderDeptComparisonChart();
        this.renderDeptTimeseriesChart();
        this.renderDeptPsTimeseriesChart();
        this.renderSessionHeatmap();
    }

    renderGaugeCharts() {
        const team = this.data.team;
        let avgStress = 0, avgPs = 0, participation = 0;

        if (team.members && team.members.length > 0) {
            const stressValues = team.members.filter(m => m.avg_stress != null).map(m => m.avg_stress);
            const psValues = team.members.filter(m => m.avg_ps != null).map(m => m.avg_ps);

            if (stressValues.length > 0) {
                avgStress = stressValues.reduce((a, b) => a + b, 0) / stressValues.length * 100;
            }
            if (psValues.length > 0) {
                avgPs = psValues.reduce((a, b) => a + b, 0) / psValues.length * 100;
            }
            participation = team.team_size > 0 ? (team.active_members || 0) / team.team_size * 100 : 0;
        }

        // Stress Gauge
        this.renderGauge('gauge-stress', avgStress, '#f87171', true);
        // PS Gauge
        this.renderGauge('gauge-ps', avgPs, '#4ade80', false);
        // Participation Gauge
        this.renderGauge('gauge-participation', participation, '#60a5fa', false);
    }

    renderGauge(elementId, value, color, inverted) {
        const el = document.getElementById(elementId);
        if (!el) return;

        if (this.charts[elementId]) {
            this.charts[elementId].dispose();
        }

        this.charts[elementId] = echarts.init(el);

        const option = {
            backgroundColor: 'transparent',
            series: [{
                type: 'gauge',
                startAngle: 180,
                endAngle: 0,
                min: 0,
                max: 100,
                splitNumber: 4,
                radius: '90%',
                center: ['50%', '75%'],
                axisLine: {
                    lineStyle: {
                        width: 15,
                        color: [
                            [inverted ? 0.3 : 0.3, inverted ? '#4ade80' : '#f87171'],
                            [inverted ? 0.6 : 0.6, '#fbbf24'],
                            [1, inverted ? '#f87171' : '#4ade80']
                        ]
                    }
                },
                pointer: {
                    icon: 'path://M12.8,0.7l12,40.1H0.7L12.8,0.7z',
                    length: '60%',
                    width: 8,
                    itemStyle: { color: '#fff' }
                },
                axisTick: { show: false },
                splitLine: { show: false },
                axisLabel: { show: false },
                detail: {
                    valueAnimation: true,
                    formatter: '{value}%',
                    color: '#fff',
                    fontSize: 20,
                    fontWeight: 'bold',
                    offsetCenter: [0, '30%']
                },
                data: [{ value: Math.round(value) }]
            }]
        };

        this.charts[elementId].setOption(option);
    }

    renderTimelineChart() {
        const el = document.getElementById('chart-stress-timeline');
        if (!el) return;

        if (this.charts.stressTimeline) {
            this.charts.stressTimeline.dispose();
        }

        this.charts.stressTimeline = echarts.init(el);

        // Generate sample data based on team members
        const team = this.data.team;
        const members = team.members || [];
        const labels = members.map(m => m.employee_name || m.employee).slice(0, 10);
        const stressData = members.map(m => m.avg_stress != null ? Math.round(m.avg_stress * 100) : 0).slice(0, 10);
        const psData = members.map(m => m.avg_ps != null ? Math.round(m.avg_ps * 100) : 0).slice(0, 10);

        const option = {
            backgroundColor: 'transparent',
            tooltip: {
                trigger: 'axis',
                backgroundColor: 'rgba(30, 41, 59, 0.95)',
                borderColor: 'rgba(255, 255, 255, 0.1)',
                textStyle: { color: '#e4e4e7' }
            },
            legend: {
                data: ['Stress', 'PS Score'],
                textStyle: { color: '#94a3b8' },
                top: 10
            },
            grid: { left: '3%', right: '4%', bottom: '10%', containLabel: true },
            xAxis: {
                type: 'category',
                data: labels,
                axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.1)' } },
                axisLabel: { color: '#94a3b8', rotate: 30, fontSize: 10 }
            },
            yAxis: {
                type: 'value',
                max: 100,
                axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.1)' } },
                axisLabel: { color: '#94a3b8', formatter: '{value}%' },
                splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.1)' } }
            },
            series: [
                {
                    name: 'Stress',
                    type: 'bar',
                    data: stressData,
                    itemStyle: { color: '#f87171' },
                    barWidth: '30%'
                },
                {
                    name: 'PS Score',
                    type: 'bar',
                    data: psData,
                    itemStyle: { color: '#4ade80' },
                    barWidth: '30%'
                }
            ]
        };

        this.charts.stressTimeline.setOption(option);
    }

    renderTriggersBarChart() {
        const el = document.getElementById('chart-triggers-bar');
        if (!el) return;

        if (this.charts.triggersBar) {
            this.charts.triggersBar.dispose();
        }

        this.charts.triggersBar = echarts.init(el);

        const triggers = this.data.triggers;
        if (!triggers.by_type || Object.keys(triggers.by_type).length === 0) {
            this.charts.triggersBar.setOption({
                backgroundColor: 'transparent',
                title: {
                    text: 'No trigger data',
                    left: 'center',
                    top: 'center',
                    textStyle: { color: '#94a3b8', fontSize: 14 }
                }
            });
            return;
        }

        const types = Object.keys(triggers.by_type);
        const counts = types.map(t => triggers.by_type[t].count);
        const severities = types.map(t => triggers.by_type[t].avg_severity);
        const labels = types.map(t => this.translateTriggerType(t));

        const option = {
            backgroundColor: 'transparent',
            tooltip: {
                trigger: 'axis',
                backgroundColor: 'rgba(30, 41, 59, 0.95)',
                borderColor: 'rgba(255, 255, 255, 0.1)',
                textStyle: { color: '#e4e4e7' },
                formatter: function(params) {
                    const idx = params[0].dataIndex;
                    return `${labels[idx]}<br/>
                            Count: ${counts[idx]}<br/>
                            Avg Severity: ${Math.round(severities[idx] * 100)}%`;
                }
            },
            grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
            xAxis: {
                type: 'category',
                data: labels,
                axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.1)' } },
                axisLabel: { color: '#94a3b8', rotate: 45, fontSize: 10 }
            },
            yAxis: {
                type: 'value',
                axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.1)' } },
                axisLabel: { color: '#94a3b8' },
                splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.1)' } }
            },
            series: [{
                type: 'bar',
                data: counts.map((count, idx) => ({
                    value: count,
                    itemStyle: {
                        color: severities[idx] > 0.6 ? '#f87171' : severities[idx] > 0.3 ? '#fbbf24' : '#4ade80'
                    }
                })),
                barWidth: '50%'
            }]
        };

        this.charts.triggersBar.setOption(option);
    }

    renderRadarChart() {
        const el = document.getElementById('chart-radar');
        if (!el) return;

        if (this.charts.radar) {
            this.charts.radar.dispose();
        }

        this.charts.radar = echarts.init(el);

        const team = this.data.team;
        const members = (team.members || []).slice(0, 5); // Top 5 members

        if (members.length === 0) {
            this.charts.radar.setOption({
                backgroundColor: 'transparent',
                title: {
                    text: 'No team data',
                    left: 'center',
                    top: 'center',
                    textStyle: { color: '#94a3b8', fontSize: 14 }
                }
            });
            return;
        }

        const indicators = [
            { name: 'Stress', max: 100 },
            { name: 'PS Score', max: 100 },
            { name: 'Sessions', max: Math.max(...members.map(m => m.total_sessions || 1)) * 1.2 },
            { name: 'Stability', max: 100 },
            { name: 'Activity', max: 10 }
        ];

        const colors = ['#f87171', '#4ade80', '#60a5fa', '#fbbf24', '#a78bfa'];

        const series = members.map((member, idx) => ({
            value: [
                Math.round((member.avg_stress || 0) * 100),
                Math.round((member.avg_ps || 0) * 100),
                member.total_sessions || 0,
                Math.round((1 - (member.avg_stress || 0)) * 100),
                Math.min(member.total_sessions || 0, 10)
            ],
            name: member.employee_name || member.employee,
            lineStyle: { color: colors[idx % colors.length] },
            itemStyle: { color: colors[idx % colors.length] },
            areaStyle: { color: colors[idx % colors.length], opacity: 0.1 }
        }));

        const option = {
            backgroundColor: 'transparent',
            tooltip: {
                trigger: 'item',
                backgroundColor: 'rgba(30, 41, 59, 0.95)',
                borderColor: 'rgba(255, 255, 255, 0.1)',
                textStyle: { color: '#e4e4e7' }
            },
            legend: {
                data: members.map(m => m.employee_name || m.employee),
                textStyle: { color: '#94a3b8' },
                bottom: 10
            },
            radar: {
                indicator: indicators,
                shape: 'polygon',
                splitNumber: 4,
                axisName: { color: '#94a3b8', fontSize: 11 },
                splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.1)' } },
                splitArea: { areaStyle: { color: ['rgba(255, 255, 255, 0.02)', 'rgba(255, 255, 255, 0.05)'] } },
                axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.1)' } }
            },
            series: [{
                type: 'radar',
                data: series
            }]
        };

        this.charts.radar.setOption(option);
    }

    renderDeptComparisonChart() {
        const el = document.getElementById('chart-dept-comparison');
        if (!el) return;

        if (this.charts.deptComparison) {
            this.charts.deptComparison.dispose();
        }

        this.charts.deptComparison = echarts.init(el);

        const data = this.data.deptComparison;
        if (!data.departments || data.departments.length === 0) {
            this.charts.deptComparison.setOption({
                backgroundColor: 'transparent',
                title: {
                    text: 'No department data',
                    left: 'center',
                    top: 'center',
                    textStyle: { color: '#94a3b8', fontSize: 14 }
                }
            });
            return;
        }

        const depts = data.departments.map(d => d.department.replace(' - LG', ''));
        const stressData = data.departments.map(d => d.avg_stress || 0);
        const psData = data.departments.map(d => d.avg_ps || 0);

        const option = {
            backgroundColor: 'transparent',
            tooltip: {
                trigger: 'axis',
                axisPointer: { type: 'shadow' },
                backgroundColor: 'rgba(30, 41, 59, 0.95)',
                borderColor: 'rgba(255, 255, 255, 0.1)',
                textStyle: { color: '#e4e4e7' },
                formatter: function(params) {
                    const idx = params[0].dataIndex;
                    const dept = data.departments[idx];
                    return `<strong>${dept.department}</strong><br/>
                        Stress: ${dept.avg_stress || '--'}%<br/>
                        PS Score: ${dept.avg_ps || '--'}%<br/>
                        Sessions: ${dept.total_sessions}<br/>
                        Employees: ${dept.employee_count}`;
                }
            },
            legend: {
                data: ['Stress', 'PS Score'],
                textStyle: { color: '#94a3b8' },
                top: 10
            },
            grid: { left: '3%', right: '4%', bottom: '10%', top: '15%', containLabel: true },
            xAxis: {
                type: 'value',
                max: 100,
                axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.1)' } },
                axisLabel: { color: '#94a3b8', formatter: '{value}%' },
                splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.1)' } }
            },
            yAxis: {
                type: 'category',
                data: depts,
                axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.1)' } },
                axisLabel: { color: '#94a3b8', fontSize: 11 }
            },
            series: [
                {
                    name: 'Stress',
                    type: 'bar',
                    data: stressData,
                    itemStyle: { color: '#f87171' },
                    barWidth: '35%'
                },
                {
                    name: 'PS Score',
                    type: 'bar',
                    data: psData,
                    itemStyle: { color: '#4ade80' },
                    barWidth: '35%'
                }
            ]
        };

        this.charts.deptComparison.setOption(option);
    }

    renderDeptTimeseriesChart() {
        const el = document.getElementById('chart-dept-timeseries');
        if (!el) return;

        if (this.charts.deptTimeseries) {
            this.charts.deptTimeseries.dispose();
        }

        this.charts.deptTimeseries = echarts.init(el);

        const data = this.data.deptTimeseries;
        if (!data.departments || data.departments.length === 0 || !data.dates || data.dates.length === 0) {
            this.charts.deptTimeseries.setOption({
                backgroundColor: 'transparent',
                title: {
                    text: 'No time series data',
                    left: 'center',
                    top: 'center',
                    textStyle: { color: '#94a3b8', fontSize: 14 }
                }
            });
            return;
        }

        const colors = ['#f87171', '#fbbf24', '#4ade80', '#60a5fa', '#a78bfa', '#f472b6', '#34d399', '#fb923c'];

        const series = data.departments.map((dept, idx) => {
            const deptData = data.series[dept];
            const values = data.dates.map(date => deptData.stress[date] || null);

            return {
                name: dept.replace(' - LG', ''),
                type: 'line',
                smooth: true,
                data: values,
                lineStyle: { color: colors[idx % colors.length], width: 2 },
                itemStyle: { color: colors[idx % colors.length] },
                areaStyle: { color: colors[idx % colors.length], opacity: 0.1 },
                connectNulls: true
            };
        });

        const option = {
            backgroundColor: 'transparent',
            tooltip: {
                trigger: 'axis',
                backgroundColor: 'rgba(30, 41, 59, 0.95)',
                borderColor: 'rgba(255, 255, 255, 0.1)',
                textStyle: { color: '#e4e4e7' }
            },
            legend: {
                data: data.departments.map(d => d.replace(' - LG', '')),
                textStyle: { color: '#94a3b8' },
                top: 10,
                type: 'scroll'
            },
            grid: { left: '3%', right: '4%', bottom: '15%', top: '15%', containLabel: true },
            xAxis: {
                type: 'category',
                data: data.dates,
                axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.1)' } },
                axisLabel: { color: '#94a3b8', rotate: 45, fontSize: 10 }
            },
            yAxis: {
                type: 'value',
                max: 100,
                name: 'Stress %',
                nameTextStyle: { color: '#94a3b8' },
                axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.1)' } },
                axisLabel: { color: '#94a3b8', formatter: '{value}%' },
                splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.1)' } }
            },
            series: series
        };

        this.charts.deptTimeseries.setOption(option);
    }

    renderDeptPsTimeseriesChart() {
        const el = document.getElementById('chart-dept-ps-timeseries');
        if (!el) return;

        if (this.charts.deptPsTimeseries) {
            this.charts.deptPsTimeseries.dispose();
        }

        this.charts.deptPsTimeseries = echarts.init(el);

        const data = this.data.deptTimeseries;
        if (!data.departments || data.departments.length === 0 || !data.dates || data.dates.length === 0) {
            this.charts.deptPsTimeseries.setOption({
                backgroundColor: 'transparent',
                title: {
                    text: 'No PS score data',
                    left: 'center',
                    top: 'center',
                    textStyle: { color: '#94a3b8', fontSize: 14 }
                }
            });
            return;
        }

        const colors = ['#4ade80', '#60a5fa', '#a78bfa', '#f472b6', '#34d399', '#fb923c', '#f87171', '#fbbf24'];

        const series = data.departments.map((dept, idx) => {
            const deptData = data.series[dept];
            const values = data.dates.map(date => deptData.ps[date] || null);

            return {
                name: dept.replace(' - LG', ''),
                type: 'line',
                smooth: true,
                data: values,
                lineStyle: { color: colors[idx % colors.length], width: 2 },
                itemStyle: { color: colors[idx % colors.length] },
                areaStyle: { color: colors[idx % colors.length], opacity: 0.1 },
                connectNulls: true
            };
        });

        const option = {
            backgroundColor: 'transparent',
            tooltip: {
                trigger: 'axis',
                backgroundColor: 'rgba(30, 41, 59, 0.95)',
                borderColor: 'rgba(255, 255, 255, 0.1)',
                textStyle: { color: '#e4e4e7' }
            },
            legend: {
                data: data.departments.map(d => d.replace(' - LG', '')),
                textStyle: { color: '#94a3b8' },
                top: 10,
                type: 'scroll'
            },
            grid: { left: '3%', right: '4%', bottom: '15%', top: '15%', containLabel: true },
            xAxis: {
                type: 'category',
                data: data.dates,
                axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.1)' } },
                axisLabel: { color: '#94a3b8', rotate: 45, fontSize: 10 }
            },
            yAxis: {
                type: 'value',
                max: 100,
                name: 'PS Score %',
                nameTextStyle: { color: '#94a3b8' },
                axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.1)' } },
                axisLabel: { color: '#94a3b8', formatter: '{value}%' },
                splitLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.1)' } }
            },
            series: series
        };

        this.charts.deptPsTimeseries.setOption(option);
    }

    renderSessionHeatmap() {
        const el = document.getElementById('chart-session-heatmap');
        if (!el) return;

        if (this.charts.sessionHeatmap) {
            this.charts.sessionHeatmap.dispose();
        }

        this.charts.sessionHeatmap = echarts.init(el);

        const data = this.data.deptTimeseries;
        if (!data.departments || data.departments.length === 0 || !data.dates || data.dates.length === 0) {
            this.charts.sessionHeatmap.setOption({
                backgroundColor: 'transparent',
                title: {
                    text: 'No session data',
                    left: 'center',
                    top: 'center',
                    textStyle: { color: '#94a3b8', fontSize: 14 }
                }
            });
            return;
        }

        // Build heatmap data: [dateIndex, deptIndex, value]
        const heatmapData = [];
        let maxSessions = 0;

        data.departments.forEach((dept, deptIdx) => {
            const deptData = data.series[dept];
            data.dates.forEach((date, dateIdx) => {
                const sessions = deptData.sessions[date] || 0;
                if (sessions > maxSessions) maxSessions = sessions;
                heatmapData.push([dateIdx, deptIdx, sessions]);
            });
        });

        const option = {
            backgroundColor: 'transparent',
            tooltip: {
                position: 'top',
                backgroundColor: 'rgba(30, 41, 59, 0.95)',
                borderColor: 'rgba(255, 255, 255, 0.1)',
                textStyle: { color: '#e4e4e7' },
                formatter: function(params) {
                    const dateIdx = params.data[0];
                    const deptIdx = params.data[1];
                    const value = params.data[2];
                    return `${data.departments[deptIdx].replace(' - LG', '')}<br/>
                        ${data.dates[dateIdx]}<br/>
                        Sessions: ${value}`;
                }
            },
            grid: { left: '15%', right: '10%', bottom: '20%', top: '10%' },
            xAxis: {
                type: 'category',
                data: data.dates,
                axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.1)' } },
                axisLabel: { color: '#94a3b8', rotate: 45, fontSize: 9, interval: Math.floor(data.dates.length / 10) },
                splitArea: { show: true, areaStyle: { color: ['rgba(255, 255, 255, 0.02)', 'transparent'] } }
            },
            yAxis: {
                type: 'category',
                data: data.departments.map(d => d.replace(' - LG', '')),
                axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.1)' } },
                axisLabel: { color: '#94a3b8', fontSize: 10 },
                splitArea: { show: true, areaStyle: { color: ['rgba(255, 255, 255, 0.02)', 'transparent'] } }
            },
            visualMap: {
                min: 0,
                max: maxSessions || 10,
                calculable: true,
                orient: 'horizontal',
                left: 'center',
                bottom: '0%',
                textStyle: { color: '#94a3b8' },
                inRange: {
                    color: ['#1e293b', '#3b82f6', '#22c55e', '#fbbf24', '#ef4444']
                }
            },
            series: [{
                name: 'Sessions',
                type: 'heatmap',
                data: heatmapData,
                label: { show: false },
                emphasis: {
                    itemStyle: {
                        shadowBlur: 10,
                        shadowColor: 'rgba(0, 0, 0, 0.5)'
                    }
                }
            }]
        };

        this.charts.sessionHeatmap.setOption(option);
    }

    generateAlerts() {
        const $alertsCard = this.$wrapper.find('#alerts-card');
        const $noAlertsCard = this.$wrapper.find('#no-alerts-card');
        const $alertsList = this.$wrapper.find('#alerts-list');
        const alerts = [];

        const team = this.data.team;
        const triggers = this.data.triggers;

        // Check individual team members
        if (team.members) {
            team.members.forEach(member => {
                if (member.avg_stress && member.avg_stress > 0.7) {
                    alerts.push({
                        critical: true,
                        text: `<strong>${member.employee_name || member.employee}</strong> has high stress level (${Math.round(member.avg_stress * 100)}%)`
                    });
                }
                if (member.avg_ps && member.avg_ps < 0.4) {
                    alerts.push({
                        critical: true,
                        text: `<strong>${member.employee_name || member.employee}</strong> has low psychological safety score (${Math.round(member.avg_ps * 100)}%)`
                    });
                }
            });
        }

        // Check trigger frequency
        if (triggers.triggers_per_session && triggers.triggers_per_session > 3) {
            alerts.push({
                critical: false,
                text: `High trigger frequency detected: ${triggers.triggers_per_session} triggers per session`
            });
        }

        // Check participation
        if (team.team_size > 0 && team.active_members / team.team_size < 0.3) {
            alerts.push({
                critical: false,
                text: `Low participation rate: ${Math.round(team.active_members / team.team_size * 100)}% of team members active`
            });
        }

        if (alerts.length === 0) {
            $alertsCard.hide();
            $noAlertsCard.show();
        } else {
            $alertsCard.show();
            $noAlertsCard.hide();
            $alertsList.empty();

            alerts.forEach(alert => {
                $alertsList.append(`
                    <li class="evidence-item">
                        <span class="evidence-icon ${alert.critical ? 'critical' : ''}">!</span>
                        <span class="evidence-text">${alert.text}</span>
                    </li>
                `);
            });
        }
    }

    // Helper methods
    getStressClass(value) {
        if (value == null) return '';
        if (value > 0.6) return 'high';
        if (value > 0.3) return 'medium';
        return 'low';
    }

    getPsClass(value) {
        if (value == null) return '';
        if (value > 0.7) return 'low';
        if (value > 0.4) return 'medium';
        return 'high';
    }

    getStressLevelClass(value) {
        if (value == null) return '';
        if (value > 0.6) return 'stress-high';
        if (value > 0.3) return 'stress-medium';
        return 'stress-low';
    }

    getScoreBadgeClass(value, isStress) {
        if (value == null) return 'score-medium';
        if (isStress) {
            if (value > 0.6) return 'score-high';
            if (value > 0.3) return 'score-medium';
            return 'score-low';
        } else {
            if (value > 0.7) return 'score-low';
            if (value > 0.4) return 'score-medium';
            return 'score-high';
        }
    }

    getMemberStatus(member) {
        if (!member.total_sessions || member.total_sessions === 0) {
            return { class: 'status-warning', label: 'Inactive' };
        }
        if (member.avg_stress && member.avg_stress > 0.6) {
            return { class: 'status-alert', label: 'High Stress' };
        }
        if (member.avg_ps && member.avg_ps < 0.5) {
            return { class: 'status-warning', label: 'Low PS' };
        }
        return { class: 'status-good', label: 'Normal' };
    }

    getPeriodLabel() {
        const labels = {
            'week': '7 Days',
            'month': '30 Days',
            'quarter': '90 Days'
        };
        return labels[this.currentPeriod] || '30 Days';
    }

    translateTriggerType(type) {
        const translations = {
            'silence_spike': 'Silence Spike',
            'apology_phrase': 'Apology Phrase',
            'hedge_increase': 'Hedge Words',
            'speech_rate_change': 'Speech Rate',
            'restart_increase': 'Restarts',
            'interruption': 'Interruption',
            'overlap': 'Overlap',
            'power_imbalance': 'Power Imbalance'
        };
        return translations[type] || type;
    }

    showLoading() {
        this.$wrapper.find('#loading-overlay').addClass('active');
    }

    hideLoading() {
        this.$wrapper.find('#loading-overlay').removeClass('active');
    }
}
