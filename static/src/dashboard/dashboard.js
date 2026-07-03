/** @odoo-module */

console.info("HotelDashboard: Loading module...");

import { Component, onWillStart, onMounted, onWillUnmount, useState, useEffect, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { browser } from "@web/core/browser/browser";
import { loadBundle } from "@web/core/assets";
// import { luxon } from "@web/core/l10n/luxon"; // Potentially failing import

export class HotelDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.chartRef = useRef("chart"); // Although we have multiple charts, we access them by ID
        this.chartJsLoaded = false; // Track Chart.js loading state

        this.state = useState({
            period: "today",
            activeTab: "front_desk",
            is_refreshing: false,
            data: {
                inventory: {},
                front_desk: {},
                guest_status: {},
                housekeeping: {},
                reservations: { labels: [], data: [] },
                room_occupancy: [],
                revenue: {},
                alerts: { total_alerts: 0 },
                kpis: {},
                shift: {},
                forecast: [],
                channels: [],
                pickup: {},
                lead_time: {},
                hk_efficiency: [],
                cash_flow: {},
                expenses: {},
                risk: {},
                period_bounds: { start: "", end: "" },
                currency: "BD"
            },
            periodDropdownOpen: false,
            date_custom_from: new Date().toISOString().split('T')[0],
            date_custom_to: new Date().toISOString().split('T')[0],

            // AI State
            ai_insights: {
                occupancy_analysis: "Analyzing data...",
                revenue_analysis: "",
                action_item: "Waiting for insights...",
                loading: true
            },
            chat_history: [{
                role: 'system',
                content: 'Hello! I am your Hotel Genius. Ask me anything about your occupancy, revenue, or guests.'
            }],
            chat_open: false,
            chat_input: ""
        });

        this.charts = {}; // Store chart instances

        onWillStart(async () => {
            const savedState = browser.localStorage.getItem("atk_hotel_dashboard_state");
            if (savedState) {
                const parsed = JSON.parse(savedState);
                if (parsed.activeTab) {
                    this.state.activeTab = parsed.activeTab;
                }
            }
            await loadBundle("web.chartjs");
            this.chartJsLoaded = true;
            await this.fetchData();
            // Fetch AI independently to not block
            this.fetchAIInsights();
        });

        onMounted(() => {
            // Render charts after a small delay to ensure DOM is ready
            setTimeout(() => {
                if (this.chartJsLoaded && typeof Chart !== 'undefined') {
                    this.renderCharts();
                }
            }, 100);

            // Auto-refresh every 5 minutes
            this.refreshInterval = setInterval(() => {
                this.fetchData();
            }, 300000);
        });

        onWillUnmount(() => {
            if (this.refreshInterval) {
                clearInterval(this.refreshInterval);
            }
            this.destroyCharts();
        });

        useEffect(() => {
            if (this.chartJsLoaded && typeof Chart !== 'undefined') {
                this.renderCharts();
            }
        }, () => [this.state.activeTab, this.state.data]);
    }

    async fetchAIInsights() {
        try {
            const result = await this.orm.call("hotel.dashboard.service", "get_ai_insights", [], {
                period: this.state.period
            });
            // Result is expected to be HTML string or simple text from the engine
            this.state.ai_insights.occupancy_analysis = result;
            this.state.ai_insights.loading = false;
        } catch (e) {
            console.error("AI Fetch Error", e);
            this.state.ai_insights.occupancy_analysis = "AI Unreachable";
            this.state.ai_insights.loading = false;
        }
    }

    toggleChat() {
        this.state.chat_open = !this.state.chat_open;
    }

    async sendChatMessage() {
        const msg = this.state.chat_input;
        if (!msg.trim()) return;

        // Add user message
        this.state.chat_history.push({ role: 'user', content: msg });
        this.state.chat_input = "";

        // Add placeholder
        this.state.chat_history.push({ role: 'system', content: 'Thinking...', temp: true });

        try {
            const response = await this.orm.call("hotel.dashboard.service", "chat_with_agent", [msg]);

            // Remove temp
            this.state.chat_history = this.state.chat_history.filter(m => !m.temp);

            // Add response
            this.state.chat_history.push({ role: 'system', content: response });
        } catch (e) {
            this.state.chat_history = this.state.chat_history.filter(m => !m.temp);
            this.state.chat_history.push({ role: 'system', content: "Sorry, I encountered an error." });
        }
    }

    async fetchData() {
        this.state.is_refreshing = true;
        try {
            const result = await this.orm.call(
                "hotel.dashboard.service",
                "get_dashboard_data",
                [],
                {
                    period: this.state.period,
                    date_from: this.state.period === 'custom' ? this.state.date_custom_from : false,
                    date_to: this.state.period === 'custom' ? this.state.date_custom_to : false,
                }
            );
            if (result) {
                Object.assign(this.state.data, result);
            }
        } catch (error) {
            console.error("Hotel Dashboard Error:", error);
        } finally {
            this.state.is_refreshing = false;
        }
    }

    destroyCharts() {
        Object.values(this.charts).forEach(chart => chart.destroy());
        this.charts = {};
    }

    renderCharts() {
        // Destroy existing charts to prevent canvas reuse errors
        // Note: We only destroy charts relevant to the current tab if needed, 
        // but simple approach is destroy all implementation-wise or check existence.
        // For simplicity in this complex dashboard, we check each canvas.

        if (this.state.activeTab === 'front_desk') {
            this.renderHKWorkloadChart();
        } else if (this.state.activeTab === 'sales') {
            this.renderRevenueTrendChart();
            this.renderPickupChart();
            this.renderLeadTimeChart();
        } else if (this.state.activeTab === 'financials') {
            this.renderBudgetChart();
            this.renderProfitPieChart();
        }
    }

    _createChart(canvasId, config) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;

        if (this.charts[canvasId]) {
            this.charts[canvasId].destroy();
        }

        console.log(`Rendering Chart: ${canvasId}`); // Debug
        this.charts[canvasId] = new Chart(canvas, config);
    }

    renderHKWorkloadChart() {
        const data = this.state.data.housekeeping || {};
        const config = {
            type: 'doughnut',
            data: {
                labels: ['Clean', 'Dirty', 'Inspected'],
                datasets: [{
                    data: [data.clean || 0, data.dirty || 0, data.inspected || 0],
                    backgroundColor: ['#28a745', '#dc3545', '#17a2b8'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                legend: { position: 'right' },
                cutoutPercentage: 70
            }
        };
        this._createChart('hkWorkloadChart', config);
    }

    renderRevenueTrendChart() {
        const forecast = this.state.data.forecast || [];
        const labels = forecast.map(d => d.date);
        const occupancy = forecast.map(d => d.occupancy);
        // Placeholder for revenue in forecast, using occupancy for now as trend proxy
        // Ideally backend should provide daily revenue history not just forecast

        const config = {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Occupancy %',
                    data: occupancy,
                    borderColor: '#b8860b', // Gold
                    backgroundColor: 'rgba(184, 134, 11, 0.1)',
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    yAxes: [{ ticks: { beginAtZero: true, max: 100 } }]
                }
            }
        };
        this._createChart('revenueTrendChart', config);
    }

    renderPickupChart() {
        const pickup = this.state.data.pickup || {};
        const config = {
            type: 'bar',
            data: {
                labels: ['Today', 'Same Day Last Week'],
                datasets: [{
                    label: 'Bookings Created',
                    data: [pickup.today_count || 0, pickup.last_week_count || 0],
                    backgroundColor: ['#b8860b', '#6c757d']
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    yAxes: [{ ticks: { beginAtZero: true, stepSize: 1 } }]
                }
            }
        };
        this._createChart('bookingPickupChart', config);
    }

    renderLeadTimeChart() {
        const leadTime = this.state.data.lead_time || {};
        const buckets = leadTime.buckets || {};

        const config = {
            type: 'bar',
            data: {
                labels: ['0-3 Days', '4-7 Days', '8-14 Days', '15-30 Days', '30+ Days'],
                datasets: [{
                    label: 'Bookings',
                    data: [
                        buckets['0-3'] || 0,
                        buckets['4-7'] || 0,
                        buckets['8-14'] || 0,
                        buckets['15-30'] || 0,
                        buckets['30+'] || 0
                    ],
                    backgroundColor: '#1E1E1E' // Charcoal
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                legend: { display: false }
            }
        };
        this._createChart('leadTimeChart', config);
    }

    renderBudgetChart() {
        // Placeholder data for budget as backend doesn't support budget model yet
        const config = {
            type: 'bar',
            data: {
                labels: ['Revenue', 'Expenses', 'GOP'],
                datasets: [
                    {
                        label: 'Actual',
                        data: [
                            this.state.data.revenue?.revenue || 0,
                            this.state.data.expenses?.total || 0,
                            this.state.data.kpis?.gop || 0
                        ],
                        backgroundColor: '#b8860b'
                    },
                    {
                        label: 'Budget (Target)',
                        data: [
                            (this.state.data.revenue?.revenue || 0) * 1.1, // Mock +10%
                            (this.state.data.expenses?.total || 0) * 0.95, // Mock -5%
                            (this.state.data.kpis?.gop || 0) * 1.2
                        ], // Placeholder
                        backgroundColor: '#e0e0e0'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false
            }
        };
        this._createChart('budgetChart', config);
    }

    renderProfitPieChart() {
        const breakdown = this.state.data.expenses?.breakdown || [];
        const labels = breakdown.map(e => e.category);
        const data = breakdown.map(e => e.amount);

        const config = {
            type: 'pie',
            data: {
                labels: labels,
                datasets: [{
                    data: data,
                    backgroundColor: ['#d4af37', '#333333', '#f5f5f5', '#a9a9a9', '#8b0000', '#228b22']
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                legend: { position: 'right' }
            }
        };
        this._createChart('profitPieChart', config);
    }

    async changePeriod(period) {
        this.state.period = period;
        this.state.periodDropdownOpen = false;
        if (period !== 'custom') {
            await this.fetchData();
        }
    }

    togglePeriodDropdown() {
        this.state.periodDropdownOpen = !this.state.periodDropdownOpen;
    }

    setTab(tab) {
        this.state.activeTab = tab;
        browser.localStorage.setItem("atk_hotel_dashboard_state", JSON.stringify({ activeTab: tab }));
    }

    // --- Drill Down Methods ---
    openArrivals() {
        if (!this.state.data.period_bounds?.start) return;
        this.openBookingList([
            ["state", "=", "confirmed"],
            ["check_in", ">=", this.state.data.period_bounds.start],
            ["check_in", "<=", this.state.data.period_bounds.end]
        ]);
    }

    openInHouse() {
        this.openBookingList([["state", "=", "checked_in"]]);
    }

    openDepartures() {
        if (!this.state.data.period_bounds?.start) return;
        this.openBookingList([
            ["state", "=", "checked_in"],
            ["check_out", ">=", this.state.data.period_bounds.start],
            ["check_out", "<=", this.state.data.period_bounds.end]
        ]);
    }

    openGuestStatus(type) {
        const domain = [["state", "=", "checked_in"]];
        if (type === 'foreigner') domain.push(["partner_id.is_foreigner", "=", true]);
        if (type === 'vip') domain.push(["partner_id.is_vip", "=", true]);
        if (type === 'complimentary') domain.push(["is_complimentary", "=", true]);
        if (type === 'doctor') domain.push(["partner_id.is_doctor", "=", true]);
        if (type === 'single_lady') domain.push(["partner_id.is_single_lady", "=", true]);
        if (type === 'house_use') domain.push(["is_house_use", "=", true]);
        this.openBookingList(domain);
    }

    openHousekeeping(status) {
        this.openRoomList([["cleaning_status", "=", status]]);
    }

    openReservations(status) {
        this.openBookingList([["state", "=", status]]);
    }

    openRoomOccupancy(roomTypeId, filter) {
        if (!roomTypeId) return;
        let domain = [["room_type", "=", roomTypeId]];
        if (filter === 'sold') domain.push(["state", "=", "occupied"]);
        if (filter === 'maintenance') domain.push(["state", "=", "maintenance"]);
        if (filter === 'available') domain.push(["state", "=", "available"]);
        if (filter === 'dirty') domain.push(["state", "=", "dirty"]);
        if (filter === 'out_of_order') domain.push(["state", "=", "unavailable"]);
        this.openRoomList(domain);
    }

    openChannelBookings(channelId) {
        let domain = [["state", "!=", "cancelled"]];
        if (channelId) {
            domain.push(["booking_source_id", "=", channelId]);
        } else {
            domain.push(["booking_source_id", "=", false]);
        }

        if (this.state.data.period_bounds?.start) {
            domain.push(["check_in", ">=", this.state.data.period_bounds.start]);
            domain.push(["check_in", "<=", this.state.data.period_bounds.end]);
        }
        this.openBookingList(domain, _t("Channel Bookings"));
    }

    openADRBookings() {
        const domain = [
            ["state", "in", ["checked_in", "checked_out"]]
        ];
        if (this.state.data.period_bounds?.start) {
            domain.push(["check_in", ">=", this.state.data.period_bounds.start]);
            domain.push(["check_in", "<=", this.state.data.period_bounds.end]);
        }
        this.openBookingList(domain, _t("Revenue Bookings (ADR)"));
    }

    openCancelBookings() {
        const domain = [["state", "=", "cancelled"]];
        if (this.state.data.period_bounds?.start) {
            domain.push(["check_in", ">=", this.state.data.period_bounds.start]);
            domain.push(["check_in", "<=", this.state.data.period_bounds.end]);
        }
        this.openBookingList(domain, _t("Cancelled Bookings"));
    }

    openStayBookings() {
        const domain = [["state", "in", ["checked_in", "checked_out"]]];
        if (this.state.data.period_bounds?.start) {
            domain.push(["check_in", ">=", this.state.data.period_bounds.start]);
            domain.push(["check_in", "<=", this.state.data.period_bounds.end]);
        }
        this.openBookingList(domain, _t("Stay Analysis Bookings"));
    }

    // --- NEW Dashboard 2.0 Drill-Down Methods ---

    openStayovers() {
        if (!this.state.data.period_bounds?.start) return;
        // Stayovers = checked in before period and checking out after period
        this.openBookingList([
            ["state", "=", "checked_in"],
            ["check_in", "<", this.state.data.period_bounds.start],
            ["check_out", ">", this.state.data.period_bounds.end]
        ], _t("Stayovers"));
    }

    openEarlyCheckins() {
        // Early check-ins for today (placeholder - requires custom field)
        this.openBookingList([
            ["state", "=", "confirmed"],
            ["check_in", ">=", this.state.data.period_bounds.start],
            ["check_in", "<=", this.state.data.period_bounds.end]
        ], _t("Early Check-ins"));
    }

    openLateCheckouts() {
        // Late checkouts for today (placeholder - requires custom field)
        this.openBookingList([
            ["state", "=", "checked_in"],
            ["check_out", ">=", this.state.data.period_bounds.start],
            ["check_out", "<=", this.state.data.period_bounds.end]
        ], _t("Late Check-outs"));
    }

    openOccupancyBookings() {
        // All occupied rooms for the period
        const domain = [["state", "in", ["checked_in", "checked_out"]]];
        if (this.state.data.period_bounds?.start) {
            domain.push(["check_in", ">=", this.state.data.period_bounds.start]);
            domain.push(["check_in", "<=", this.state.data.period_bounds.end]);
        }
        this.openBookingList(domain, _t("Occupancy Analysis"));
    }

    openRevPARBookings() {
        // Same as ADR bookings (revenue-generating bookings)
        this.openADRBookings();
    }

    openGOPAnalysis() {
        // Open accounting view filtered for hotel revenue/expenses
        this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("GOP Analysis"),
            res_model: "account.move.line",
            views: [[false, 'list'], [false, 'pivot'], [false, 'graph']],
            domain: [
                ["date", ">=", this.state.data.period_bounds.start],
                ["date", "<=", this.state.data.period_bounds.end]
            ],
            target: "current",
        });
    }

    openALOSBookings() {
        // All completed stays for ALOS calculation
        const domain = [["state", "in", ["checked_in", "checked_out"]]];
        if (this.state.data.period_bounds?.start) {
            domain.push(["check_in", ">=", this.state.data.period_bounds.start]);
            domain.push(["check_in", "<=", this.state.data.period_bounds.end]);
        }
        this.openBookingList(domain, _t("Length of Stay Analysis"));
    }

    // --- Operational Alerts Drill-Down ---
    openDirtyArrivals() {
        if (!this.state.data.period_bounds?.start) return;
        const start = this.state.data.period_bounds.start;
        const end = this.state.data.period_bounds.end;

        this.openBookingList([
            ["check_in", ">=", start],
            ["check_in", "<=", end],
            ["state", "in", ["confirmed", "checked_in"]],
            ["room_id.cleaning_status", "=", "dirty"]
        ], _t("Dirty Arrivals"));
    }

    openMissingIDs() {
        if (!this.state.data.period_bounds?.start) return;
        // Show all active bookings to help staff find missing info
        // Precise "OR" domain for missing fields is complex in JS, showing active list is sufficient
        this.openBookingList([
            ["state", "in", ["confirmed", "checked_in"]]
        ], _t("Active Bookings (Check Missing IDs)"));
    }

    openOOORooms() {
        this.openRoomList([["state", "=", "unavailable"]]);
    }

    openMaintenanceTickets() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("Maintenance Requests"),
            res_model: "maintenance.request",
            views: [[false, 'list'], [false, 'form']],
            domain: [["stage_id.done", "=", false]],
            target: "current",
        });
    }

    openHeatmapDate(date) {
        // Open bookings for a specific date from heatmap
        if (!date) return;
        this.openBookingList([
            ["state", "in", ["confirmed", "checked_in"]],
            ["check_in", "<=", `${date} 23:59:59`],
            ["check_out", ">", `${date} 00:00:00`]
        ], _t(`Bookings for ${date}`));
    }

    openPendingApprovals() {
        this.openBookingList([["state", "=", "to_approve"]], _t("Pending Manager Approvals"));
    }

    openHKEfficiency(staffId) {
        // Open housekeeping tasks for specific staff member
        if (!staffId) return;
        this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("Housekeeping Tasks"),
            res_model: "hotel.cleaning.request",
            views: [[false, 'list'], [false, 'kanban'], [false, 'form']],
            domain: [["assigned_to", "=", staffId]],
            target: "current",
        });
    }

    openCashFlow(type) {
        // Open accounting entries for cash flow analysis
        let domain = [
            ["date", ">=", this.state.data.period_bounds.start],
            ["date", "<=", this.state.data.period_bounds.end]
        ];

        if (type === 'receivables') {
            domain.push(["account_id.account_type", "=", "asset_receivable"]);
        } else if (type === 'payables') {
            domain.push(["account_id.account_type", "=", "liability_payable"]);
        }

        this.action.doAction({
            type: "ir.actions.act_window",
            name: _t(`${type.charAt(0).toUpperCase() + type.slice(1)} Analysis`),
            res_model: "account.move.line",
            views: [[false, 'list'], [false, 'form']],
            domain: domain,
            target: "current",
        });
    }

    openExpenseBreakdown(category) {
        // Open expense entries for specific category
        this.action.doAction({
            type: "ir.actions.act_window",
            name: _t(`${category} Expenses`),
            res_model: "account.move.line",
            views: [[false, 'list'], [false, 'pivot']],
            domain: [
                ["date", ">=", this.state.data.period_bounds.start],
                ["date", "<=", this.state.data.period_bounds.end],
                ["account_id.name", "ilike", category]
            ],
            target: "current",
        });
    }

    openRiskDetails(riskType) {
        // Open dashboard with focus on risk metrics
        // For now, just show a notification
        this.action.doAction({
            type: 'ir.actions.client',
            tag: 'display_notification',
            params: {
                title: _t(`${riskType} Risk Details`),
                message: _t(`Risk score: ${this.state.data.risk?.[riskType] || 0}. Review operational metrics for detailed analysis.`),
                type: 'info',
                sticky: false,
            }
        });
    }

    // Revenue Panel Drill-Downs
    openTodayRevenue() {
        const today = new Date().toISOString().split('T')[0];
        this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("Today's Revenue"),
            res_model: "account.move",
            views: [[false, 'list'], [false, 'form']],
            domain: [
                ['move_type', '=', 'out_invoice'],
                ['invoice_date', '=', today],
                ['state', '=', 'posted']
            ],
            target: "current",
        });
    }

    openPaymentMethod(method) {
        const today = new Date().toISOString().split('T')[0];
        this.action.doAction({
            type: "ir.actions.act_window",
            name: _t(`${method.charAt(0).toUpperCase() + method.slice(1)} Payments Today`),
            res_model: "account.payment",
            views: [[false, 'list'], [false, 'form']],
            domain: [
                ['payment_date', '=', today],
                ['payment_method_line_id.name', 'ilike', method]
            ],
            target: "current",
        });
    }

    openPendingDeposits() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("Pending Deposits"),
            res_model: "hotel.book.history",
            views: [[false, 'list'], [false, 'form']],
            domain: [
                ['state', 'in', ['confirmed', 'checked_in']],
                ['deposit_amount', '>', 0]
            ],
            target: "current",
        });
    }

    async _triggerQuickReport(format) {
        const periodMap = {
            "today": "daily",
            "week": "weekly",
            "month": "monthly"
        };

        const wizardId = await this.orm.create("hotel.report.kit.wizard", [{
            report_type: periodMap[this.state.period] || "daily",
            period_preset: this.state.period,
            output_format: format
        }]);

        const action = await this.orm.call(
            "hotel.report.kit.wizard",
            "action_generate_report",
            [wizardId]
        );

        if (action) {
            this.action.doAction(action);
        }
    }

    async printQuickPDF() {
        await this._triggerQuickReport("pdf");
    }

    async exportQuickExcel() {
        await this._triggerQuickReport("xlsx");
    }

    openIntelligenceKit() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("Al Faris Intelligence Kit"),
            res_model: "hotel.report.kit.wizard",
            views: [[false, 'form']],
            target: "new",
        });
    }

    // --- Helper Methods ---
    formatCurrency(amount) {
        return `${this.state.data.currency} ${Number(amount || 0).toLocaleString(undefined, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        })}`;
    }

    openRoomList(domain) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: _t("Rooms"),
            res_model: "hotel.room",
            views: [[false, 'list'], [false, 'kanban'], [false, 'form']],
            domain: domain,
            target: "current",
        });
    }

    openBookingList(domain, name = _t("Bookings")) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: name,
            res_model: "hotel.book.history",
            views: [[false, 'list'], [false, 'calendar'], [false, 'form']],
            domain: domain,
            target: "current",
        });
    }
}

HotelDashboard.template = "atk_hotel.HotelDashboard";
console.info("HotelDashboard: Registering action 'atk_hotel.dashboard'");
registry.category("actions").add("atk_hotel.dashboard", HotelDashboard);
