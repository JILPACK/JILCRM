import logging
import ast
from datetime import datetime, timedelta

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class CrmDashboard(models.Model):
    _name = 'jil.crm.dashboard'
    _description = 'CRM Dashboard'
    _order = 'sequence, id'

    name = fields.Char(string='Dashboard Name', required=True)
    active = fields.Boolean(string='Active', default=True)
    sequence = fields.Integer(string='Sequence', default=10)
    user_id = fields.Many2one('res.users', string='Owner', default=lambda self: self.env.user)
    shared = fields.Boolean(string='Shared with Team', default=False)
    dashboard_type = fields.Selection([
        ('executive', 'Executive Overview'),
        ('sales', 'Sales Performance'),
        ('marketing', 'Marketing'),
        ('support', 'Support'),
        ('project', 'Project'),
        ('custom', 'Custom'),
    ], string='Type', default='sales')

    widget_ids = fields.One2many('jil.crm.dashboard.widget', 'dashboard_id', string='Widgets')
    widget_count = fields.Integer(string='Widget Count', compute='_compute_widget_count')

    @api.depends('widget_ids')
    def _compute_widget_count(self):
        for d in self:
            d.widget_count = len(d.widget_ids)


class CrmDashboardWidget(models.Model):
    _name = 'jil.crm.dashboard.widget'
    _description = 'Dashboard Widget'
    _order = 'dashboard_id, sequence, id'

    dashboard_id = fields.Many2one('jil.crm.dashboard', string='Dashboard',
                                    required=True, ondelete='cascade')
    name = fields.Char(string='Widget Name', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    widget_type = fields.Selection([
        ('kpi_card', 'KPI Card'),
        ('bar_chart', 'Bar Chart'),
        ('line_chart', 'Line Chart'),
        ('pie_chart', 'Pie Chart'),
        ('funnel', 'Sales Funnel'),
        ('list', 'List'),
        ('metric', 'Metric'),
    ], string='Widget Type', required=True, default='kpi_card')
    size = fields.Selection([
        ('small', 'Small (1/4)'),
        ('medium', 'Medium (1/2)'),
        ('large', 'Large (3/4)'),
        ('full', 'Full Width'),
    ], string='Size', default='medium')

    model_name = fields.Char(string='Source Model')
    field_name = fields.Char(string='Field Name')
    domain = fields.Text(string='Domain (JSON)')
    group_by = fields.Char(string='Group By Field')
    measure = fields.Char(string='Measure Field')
    aggregation = fields.Selection([
        ('count', 'Count'), ('sum', 'Sum'),
        ('avg', 'Average'), ('min', 'Min'), ('max', 'Max'),
    ], string='Aggregation', default='count')

    color = fields.Char(string='Color', default='#7c7bad')
    icon = fields.Char(string='Icon')
    refresh_interval = fields.Integer(string='Refresh Interval (min)', default=30)


class CrmKpi(models.Model):
    _name = 'jil.crm.kpi'
    _description = 'CRM KPI Definition'
    _order = 'sequence, id'

    name = fields.Char(string='KPI Name', required=True)
    active = fields.Boolean(string='Active', default=True)
    sequence = fields.Integer(string='Sequence', default=10)
    kpi_type = fields.Selection([
        ('revenue', 'Revenue'),
        ('conversion', 'Conversion Rate'),
        ('leads', 'Lead Generation'),
        ('pipeline', 'Pipeline Value'),
        ('sales_cycle', 'Sales Cycle Length'),
        ('activity', 'Activity Rate'),
        ('satisfaction', 'Customer Satisfaction'),
        ('retention', 'Retention Rate'),
        ('custom', 'Custom'),
    ], string='KPI Type', default='revenue')

    model_name = fields.Char(string='Source Model', default='jil.crm.lead')
    measure_field = fields.Char(string='Measure Field', default='expected_revenue')
    aggregation = fields.Selection([
        ('count', 'Count'), ('sum', 'Sum'),
        ('avg', 'Average'), ('ratio', 'Ratio'),
    ], string='Aggregation', default='sum')

    target_value = fields.Float(string='Target Value')
    target_type = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
    ], string='Target Period', default='monthly')
    current_value = fields.Float(string='Current Value', compute='_compute_current')
    achievement = fields.Float(string='Achievement %', compute='_compute_current')
    unit = fields.Char(string='Unit', default='$')

    domain = fields.Text(string='Domain (JSON)')
    date_field = fields.Char(string='Date Field', default='create_date',
                              help='Field used for period filtering in previous-value computation')
    compare_to_previous = fields.Boolean(string='Compare to Previous', default=True)
    previous_value = fields.Float(string='Previous Value', compute='_compute_previous')
    trend = fields.Selection([
        ('up', 'Up'), ('down', 'Down'), ('stable', 'Stable'),
    ], string='Trend', compute='_compute_trend')

    def _safe_parse_domain(self, domain_str):
        if not domain_str:
            return []
        try:
            parsed = ast.literal_eval(domain_str)
            if isinstance(parsed, (list, tuple)):
                return parsed
            _logger.warning("KPI domain is not a list: %s", domain_str)
            return []
        except (ValueError, SyntaxError, MemoryError) as e:
            _logger.error("Invalid KPI domain: %s — %s", domain_str, e)
            return []

    @api.depends('target_value', 'aggregation', 'measure_field', 'domain', 'model_name')
    def _compute_current(self):
        for kpi in self:
            try:
                domain = self._safe_parse_domain(kpi.domain)
                model = self.env.get(kpi.model_name)
                if model:
                    records = model.search(domain)
                    if kpi.aggregation == 'count':
                        kpi.current_value = len(records)
                    elif kpi.aggregation == 'sum' and kpi.measure_field:
                        kpi.current_value = sum(records.mapped(kpi.measure_field) or [0])
                    elif kpi.aggregation == 'avg' and kpi.measure_field:
                        vals = records.mapped(kpi.measure_field) or [0]
                        kpi.current_value = sum(vals) / len(vals) if vals else 0
                    else:
                        kpi.current_value = 0
                else:
                    kpi.current_value = 0
                kpi.achievement = (kpi.current_value / kpi.target_value * 100) if kpi.target_value else 0
            except Exception:
                _logger.exception("KPI compute error for %s", kpi.name)
                kpi.current_value = 0
                kpi.achievement = 0

    def _period_boundaries(self, target_type, ref_date=None):
        today = ref_date or datetime.today()
        if target_type == 'monthly':
            curr_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if curr_start.month == 1:
                prev_start = curr_start.replace(year=curr_start.year - 1, month=12)
            else:
                prev_start = curr_start.replace(month=curr_start.month - 1)
            if curr_start.month == 12:
                curr_end = curr_start.replace(year=curr_start.year + 1, month=1)
            else:
                curr_end = curr_start.replace(month=curr_start.month + 1)
            prev_end = curr_start
        elif target_type == 'quarterly':
            q = (today.month - 1) // 3
            curr_start = today.replace(month=q * 3 + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
            if q == 0:
                prev_start = curr_start.replace(year=curr_start.year - 1, month=10)
            else:
                prev_start = curr_start.replace(month=curr_start.month - 3)
            if q == 3:
                curr_end = curr_start.replace(year=curr_start.year + 1, month=1)
            else:
                curr_end = curr_start.replace(month=curr_start.month + 3)
            prev_end = curr_start
        else:  # yearly
            curr_start = today.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            prev_start = curr_start.replace(year=curr_start.year - 1)
            curr_end = curr_start.replace(year=curr_start.year + 1)
            prev_end = curr_start
        return curr_start, curr_end, prev_start, prev_end

    @api.depends('compare_to_previous', 'target_type', 'date_field', 'domain', 'aggregation', 'measure_field', 'model_name')
    def _compute_previous(self):
        for kpi in self:
            if not kpi.compare_to_previous or not kpi.model_name:
                kpi.previous_value = 0
                continue
            try:
                date_field = kpi.date_field or 'create_date'
                model = self.env.get(kpi.model_name)
                if not model or date_field not in model._fields or not isinstance(model._fields[date_field], (fields.Date, fields.Datetime)):
                    kpi.previous_value = kpi.current_value * 0.85
                    continue
                _, _, prev_start, prev_end = self._period_boundaries(kpi.target_type)
                domain = self._safe_parse_domain(kpi.domain)
                domain += [(date_field, '>=', fields.Datetime.to_string(prev_start)),
                           (date_field, '<', fields.Datetime.to_string(prev_end))]
                records = model.search(domain)
                if kpi.aggregation == 'count':
                    kpi.previous_value = len(records)
                elif kpi.aggregation == 'sum' and kpi.measure_field:
                    kpi.previous_value = sum(records.mapped(kpi.measure_field) or [0])
                elif kpi.aggregation == 'avg' and kpi.measure_field:
                    vals = records.mapped(kpi.measure_field) or [0]
                    kpi.previous_value = sum(vals) / len(vals) if vals else 0
                else:
                    kpi.previous_value = 0
            except Exception:
                _logger.exception("KPI previous compute error for %s", kpi.name)
                kpi.previous_value = 0

    @api.depends('current_value', 'previous_value')
    def _compute_trend(self):
        for kpi in self:
            if kpi.current_value > kpi.previous_value:
                kpi.trend = 'up'
            elif kpi.current_value < kpi.previous_value:
                kpi.trend = 'down'
            else:
                kpi.trend = 'stable'


class CrmConversionMetrics(models.Model):
    _name = 'jil.crm.conversion.metrics'
    _description = 'Conversion Metrics'
    _order = 'create_date desc'

    name = fields.Char(string='Period', required=True)
    date_from = fields.Date(string='From')
    date_to = fields.Date(string='To')
    period_type = fields.Selection([
        ('daily', 'Daily'), ('weekly', 'Weekly'),
        ('monthly', 'Monthly'), ('yearly', 'Yearly'),
    ], string='Period Type')
    total_leads = fields.Integer(string='Total Leads')
    qualified_leads = fields.Integer(string='Qualified')
    converted_opportunities = fields.Integer(string='Converted')
    won_deals = fields.Integer(string='Won')
    lost_deals = fields.Integer(string='Lost')
    lead_to_qualification_rate = fields.Float(string='Lead→Qualified %')
    qualification_to_opportunity_rate = fields.Float(string='Qualified→Opp %')
    opportunity_to_won_rate = fields.Float(string='Opp→Won %')
    overall_conversion = fields.Float(string='Overall Conversion %')
    total_revenue = fields.Float(string='Total Revenue')
    avg_deal_size = fields.Float(string='Avg Deal Size')

    @api.model
    def compute_metrics(self, date_from=None, date_to=None):
        today = datetime.today()
        if not date_from:
            date_from = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if not date_to:
            if today.month == 12:
                date_to = today.replace(year=today.year + 1, month=1, day=1)
            else:
                date_to = today.replace(month=today.month + 1, day=1)
        domain = [('create_date', '>=', fields.Datetime.to_string(date_from)),
                  ('create_date', '<', fields.Datetime.to_string(date_to))]
        leads = self.env['jil.crm.lead'].search(domain)
        total = len(leads)
        qualified = len(leads.filtered(lambda l: l.stage_id and l.stage_id.probability >= 20))
        converted = len(leads.filtered(lambda l: l.type == 'opportunity'))
        won = len(leads.filtered(lambda l: l.stage_id and l.stage_id.is_won))
        lost = len(leads.filtered(lambda l: l.stage_id and l.stage_id.is_lost))
        revenues = [l.expected_revenue or 0 for l in leads if l.stage_id and l.stage_id.is_won]
        total_rev = sum(revenues)
        self.create({
            'name': 'Conversion %s - %s' % (date_from.strftime('%Y-%m-%d'), date_to.strftime('%Y-%m-%d')),
            'period_type': 'monthly',
            'date_from': date_from,
            'date_to': date_to,
            'total_leads': total,
            'qualified_leads': qualified,
            'converted_opportunities': converted,
            'won_deals': won,
            'lost_deals': lost,
            'lead_to_qualification_rate': round(qualified / total * 100, 2) if total else 0,
            'qualification_to_opportunity_rate': round(converted / qualified * 100, 2) if qualified else 0,
            'opportunity_to_won_rate': round(won / converted * 100, 2) if converted else 0,
            'overall_conversion': round(won / total * 100, 2) if total else 0,
            'total_revenue': total_rev,
            'avg_deal_size': round(total_rev / won, 2) if won else 0,
        })
        _logger.info("Conversion metrics computed for %s - %s", date_from, date_to)
        return True
