from odoo import api, fields, models, _


class DealTracking(models.Model):
    _name = 'jil.deal.tracking'
    _description = 'Deal Tracking'
    _order = 'create_date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Deal Name', required=True, tracking=True)
    lead_id = fields.Many2one('jil.crm.lead', string='Lead/Opportunity', tracking=True)
    partner_id = fields.Many2one('res.partner', string='Customer', tracking=True)
    user_id = fields.Many2one('res.users', string='Salesperson', tracking=True,
                              default=lambda self: self.env.user)
    team_id = fields.Many2one('crm.team', string='Sales Team', tracking=True)

    stage_id = fields.Many2one('jil.crm.stage', string='Stage', tracking=True)
    probability = fields.Float(string='Probability (%)', default=0.0, tracking=True)
    expected_revenue = fields.Monetary(string='Expected Revenue', currency_field='currency_id',
                                        tracking=True)
    currency_id = fields.Many2one('res.currency', string='Currency',
                                   default=lambda self: self.env.company.currency_id)

    expected_close = fields.Date(string='Expected Close', tracking=True)
    actual_close = fields.Date(string='Actual Close')
    days_in_pipeline = fields.Integer(string='Days in Pipeline', compute='_compute_days')

    deal_source = fields.Selection([
        ('inbound', 'Inbound'), ('outbound', 'Outbound'),
        ('referral', 'Referral'), ('existing', 'Existing Customer'),
        ('chatbot', 'Chatbot'), ('website', 'Website'),
    ], string='Deal Source', default='inbound')

    status = fields.Selection([
        ('active', 'Active'), ('won', 'Won'),
        ('lost', 'Lost'), ('stalled', 'Stalled'),
    ], string='Status', default='active', tracking=True)
    lost_reason = fields.Text(string='Lost Reason')
    notes = fields.Text(string='Notes')

    win_probability = fields.Float(string='Win Probability (%)', compute='_compute_win_prob', store=True)
    forecast_id = fields.Many2one('jil.sales.forecast', string='Forecast')

    # Context MCP
    context_id = fields.Many2one('jil.mcp.context', string='Unified Context')

    @api.depends('stage_id', 'stage_id.probability', 'days_in_pipeline')
    def _compute_win_prob(self):
        for d in self:
            base = d.stage_id.probability if d.stage_id else 0
            d.win_probability = base

    @api.depends('create_date')
    def _compute_days(self):
        for d in self:
            if d.create_date:
                d.days_in_pipeline = (fields.Datetime.now() - d.create_date).days
            else:
                d.days_in_pipeline = 0

    def action_mark_won(self):
        for d in self:
            d.write({
                'status': 'won',
                'actual_close': fields.Date.today(),
                'probability': 100,
            })

    def action_mark_lost(self):
        for d in self:
            d.write({'status': 'lost', 'probability': 0})


class SalesForecast(models.Model):
    _name = 'jil.sales.forecast'
    _description = 'Sales Forecast'
    _order = 'fiscal_year desc, period desc'

    name = fields.Char(string='Forecast Name', required=True)
    fiscal_year = fields.Char(string='Fiscal Year', required=True, default='2026')
    period = fields.Selection([
        ('q1', 'Q1'), ('q2', 'Q2'), ('q3', 'Q3'), ('q4', 'Q4'),
        ('h1', 'H1'), ('h2', 'H2'), ('year', 'Full Year'),
    ], string='Period', required=True, default='q1')
    team_id = fields.Many2one('crm.team', string='Sales Team')
    user_id = fields.Many2one('res.users', string='Salesperson')
    state = fields.Selection([
        ('draft', 'Draft'), ('confirmed', 'Confirmed'),
        ('achieved', 'Achieved'), ('missed', 'Missed'),
    ], string='State', default='draft')

    target_revenue = fields.Monetary(string='Target Revenue', currency_field='currency_id')
    weighted_forecast = fields.Monetary(string='Weighted Forecast', currency_field='currency_id',
                                         compute='_compute_forecast')
    committed_forecast = fields.Monetary(string='Committed Forecast', currency_field='currency_id',
                                          compute='_compute_forecast')
    best_case = fields.Monetary(string='Best Case', currency_field='currency_id', compute='_compute_forecast')
    pipeline_value = fields.Monetary(string='Pipeline Value', currency_field='currency_id',
                                      compute='_compute_forecast')
    currency_id = fields.Many2one('res.currency', string='Currency',
                                   default=lambda self: self.env.company.currency_id)

    deal_ids = fields.One2many('jil.deal.tracking', 'forecast_id', string='Deals')
    deal_count = fields.Integer(string='Deal Count', compute='_compute_forecast')
    achievement_rate = fields.Float(string='Achievement %', compute='_compute_forecast')

    @api.depends('deal_ids', 'deal_ids.expected_revenue', 'deal_ids.win_probability',
                 'deal_ids.probability')
    def _compute_forecast(self):
        if not self.ids:
            return
        all_deals = self.env['jil.deal.tracking'].search([('forecast_id', 'in', self.ids)])
        forecast_map = {}
        for deal in all_deals:
            fid = deal.forecast_id.id
            if fid not in forecast_map:
                forecast_map[fid] = {
                    'deals': [], 'revenues': [], 'weighted': 0,
                    'committed': 0, 'best_case': 0,
                }
            entry = forecast_map[fid]
            entry['deals'].append(deal)
            rev = deal.expected_revenue or 0
            entry['revenues'].append(rev)
            entry['weighted'] += rev * (deal.win_probability or 0) / 100
            if (deal.win_probability or 0) >= 60:
                entry['committed'] += rev
            if deal.status == 'active':
                entry['best_case'] += rev
        for f in self:
            entry = forecast_map.get(f.id, {})
            deals = entry.get('deals', [])
            f.deal_count = len(deals)
            f.pipeline_value = sum(entry.get('revenues', []))
            f.weighted_forecast = entry.get('weighted', 0)
            f.committed_forecast = entry.get('committed', 0)
            f.best_case = entry.get('best_case', 0)
            f.achievement_rate = (f.committed_forecast / f.target_revenue * 100) if f.target_revenue else 0


class AutomatedFollowUp(models.Model):
    _name = 'jil.automated.followup'
    _description = 'Automated Follow-up'
    _order = 'create_date desc'

    name = fields.Char(string='Follow-up Name', required=True)
    active = fields.Boolean(string='Active', default=True)
    stage_id = fields.Many2one('jil.crm.stage', string='Trigger Stage')
    delay_hours = fields.Integer(string='Delay After Stage (hours)', default=24)
    email_template_id = fields.Many2one('mail.template', string='Email Template',
                                         required=True)
    sms_template = fields.Text(string='SMS Template')
    create_activity = fields.Boolean(string='Create Activity', default=True)
    activity_type = fields.Many2one('mail.activity.type', string='Activity Type')
    activity_summary = fields.Char(string='Activity Summary')
    activity_user = fields.Many2one('res.users', string='Activity Assignee')
    max_followups = fields.Integer(string='Max Follow-ups', default=3)
    interval_hours = fields.Integer(string='Interval Between (hours)', default=48)
    follow_up_count = fields.Integer(string='Times Executed', default=0)

    def execute(self, lead):
        if not self.active:
            return False
        count = lead.follow_up_count
        if count >= self.max_followups:
            return False
        if self.email_template_id:
            lead.message_post_with_template(self.email_template_id.id)
        if self.create_activity and self.activity_type:
            lead.activity_schedule(
                self.activity_type.id,
                summary=self.activity_summary or f'Follow-up: {lead.name}',
                user_id=self.activity_user.id or lead.user_id.id,
            )
        lead.write({
            'follow_up_count': count + 1,
            'last_follow_up_date': fields.Datetime.now(),
        })
        self.follow_up_count += 1
        return True
