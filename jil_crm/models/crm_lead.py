from odoo import api, fields, models, _


class JilCrmLead(models.Model):
    _name = 'jil.crm.lead'
    _description = 'JIL CRM Lead'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'priority desc, create_date desc'

    name = fields.Char(string='Subject', required=True, tracking=True)
    email_from = fields.Char(string='Email', tracking=True)
    phone = fields.Char(string='Phone', tracking=True)
    mobile = fields.Char(string='Mobile', tracking=True)

    partner_id = fields.Many2one('res.partner', string='Customer', tracking=True, index=True)
    partner_name = fields.Char(string='Customer Name', tracking=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, index=True)
    user_id = fields.Many2one('res.users', string='Salesperson', tracking=True, default=lambda self: self.env.user, index=True)
    team_id = fields.Many2one('crm.team', string='Sales Team', tracking=True, index=True)

    stage_id = fields.Many2one('jil.crm.stage', string='Stage', tracking=True, index=True,
                                domain="[('team_ids', 'in', team_id)]",
                                default=lambda self: self._default_stage_id())

    priority = fields.Selection([
        ('0', 'Low'), ('1', 'Medium'), ('2', 'High'), ('3', 'Very High'),
    ], string='Priority', default='1', tracking=True)
    probability = fields.Float(string='Probability (%)', aggregator='avg', default=0.0)
    expected_revenue = fields.Monetary(string='Expected Revenue', currency_field='currency_id', tracking=True)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)

    description = fields.Html(string='Notes')
    lost_reason = fields.Text(string='Lost Reason')
    date_open = fields.Datetime(string='Open Date', default=fields.Datetime.now, index=True)
    date_deadline = fields.Date(string='Expected Closing', tracking=True)
    date_close = fields.Datetime(string='Close Date')
    date_last_stage_update = fields.Datetime(string='Last Stage Update', default=fields.Datetime.now)
    tag_ids = fields.Many2many('crm.tag', string='Tags')
    color = fields.Integer(string='Color Index', default=0)

    type = fields.Selection([
        ('lead', 'Lead'), ('opportunity', 'Opportunity'),
    ], string='Type', default='lead', tracking=True, required=True, index=True)

    # Lead Capture
    active = fields.Boolean(string='Active', default=True, index=True)
    capture_source = fields.Selection([
        ('website', 'Website'), ('chatbot', 'AI Chatbot'),
        ('manual', 'Manual Entry'), ('email', 'Email'),
        ('referral', 'Referral'), ('api', 'API Import'),
        ('social', 'Social Media'), ('event', 'Event'),
    ], string='Capture Source', default='manual', tracking=True)
    capture_url = fields.Char(string='Capture URL')
    capture_form_id = fields.Char(string='Form ID')
    consent_given = fields.Boolean(string='Consent Given', default=True)
    consent_date = fields.Datetime(string='Consent Date')

    # Lead Scoring
    score = fields.Integer(string='Score', default=0, index=True)
    score_engagement = fields.Integer(string='Engagement Score', default=0)
    score_behavior = fields.Integer(string='Behavior Score', default=0)
    score_demographic = fields.Integer(string='Demographic Score', default=0)
    score_last_updated = fields.Datetime(string='Score Last Updated')
    score_grade = fields.Selection([
        ('a', 'A - Hot'), ('b', 'B - Warm'), ('c', 'C - Cold'), ('d', 'D - Inactive'),
    ], string='Score Grade', compute='_compute_score_grade', store=True)

    # Lead Assignment
    assignment_rule_id = fields.Many2one('jil.lead.assignment.rule', string='Assignment Rule')
    assignment_date = fields.Datetime(string='Assignment Date')
    assignment_auto = fields.Boolean(string='Auto Assigned', default=False)

    # Nurturing
    nurturing_campaign_id = fields.Many2one('jil.nurturing.campaign', string='Nurturing Campaign')
    nurturing_status = fields.Selection([
        ('none', 'Not in Campaign'), ('active', 'Active'),
        ('completed', 'Completed'), ('unsubscribed', 'Unsubscribed'),
    ], string='Nurturing Status', default='none')
    nurturing_start_date = fields.Date(string='Nurturing Start')
    nurturing_last_action = fields.Date(string='Last Nurturing Action')

    # Automated Follow-ups
    follow_up_count = fields.Integer(string='Follow-ups', default=0)
    last_follow_up_date = fields.Datetime(string='Last Follow-up')
    next_follow_up_date = fields.Datetime(string='Next Follow-up')
    automated_email_sent = fields.Boolean(string='Automated Email Sent', default=False)

    # Deal Tracking
    deal_value = fields.Monetary(string='Deal Value', currency_field='currency_id')
    deal_close_probability = fields.Float(string='Close Probability (%)', default=0.0)
    deal_expected_close = fields.Date(string='Expected Close Date')
    deal_stage_duration = fields.Integer(string='Days in Stage', compute='_compute_stage_duration')
    deal_age = fields.Integer(string='Deal Age (days)', compute='_compute_deal_age')
    deal_forecast_id = fields.Many2one('jil.sales.forecast', string='Forecast Entry')
    communication_ids = fields.One2many('jil.crm.communication', 'lead_id', string='Communications')
    communication_count = fields.Integer(string='Comm. Count', compute='_compute_communication_count')

    # Context MCP
    context_id = fields.Many2one('jil.mcp.context', string='Unified Context')
    context_last_sync = fields.Datetime(string='Last Context Sync')
    context_sync_status = fields.Selection([
        ('synced', 'Synced'), ('pending', 'Pending Sync'), ('failed', 'Sync Failed'),
    ], string='Context Sync', default='pending')

    # Vente / Sales
    quotation_ref = fields.Char(string='Quotation Ref')
    bc_ref = fields.Char(string='BC Ref')
    bc_date = fields.Date(string='BC Date')
    bc_validated = fields.Boolean(string='BC Validated')
    correction_bc = fields.Boolean(string='BC Correction')
    delivery_note_ref = fields.Char(string='Delivery Note Ref')

    # Logistique / Logistics
    transport_mode = fields.Selection([
        ('maritime', 'Maritime'), ('aerien', 'Aérien'),
        ('terrestre', 'Terrestre'), ('ferroviaire', 'Ferroviaire'),
    ], string='Transport Mode')
    incoterm = fields.Char(string='Incoterm')
    incoterm_place = fields.Char(string='Incoterm Place')
    tracking_ref = fields.Char(string='Tracking Ref')
    bl_ref = fields.Char(string='BL Ref')
    estimated_delivery = fields.Date(string='Estimated Delivery')
    delivery_date = fields.Date(string='Delivery Date')
    warehouse_location = fields.Char(string='Warehouse Location')
    customs_cleared = fields.Boolean(string='Customs Cleared')
    customs_date = fields.Date(string='Customs Clearance Date')
    shipping_notes = fields.Text(string='Shipping Notes')

    # Comptabilité / Accounting
    invoice_ref = fields.Char(string='Invoice Ref')
    invoice_date = fields.Date(string='Invoice Date')
    invoice_due_date = fields.Date(string='Invoice Due Date')
    payment_status = fields.Selection([
        ('unpaid', 'Unpaid'), ('partial', 'Partial'), ('paid', 'Paid'),
    ], string='Payment Status', default='unpaid')
    payment_date = fields.Date(string='Payment Date')
    payment_method = fields.Char(string='Payment Method')
    relance_stage = fields.Selection([
        ('none', 'No Reminder'), ('first', '1st Reminder'),
        ('second', '2nd Reminder'), ('final', 'Final Notice'),
    ], string='Reminder Stage', default='none')
    relance_date = fields.Date(string='Last Reminder Date')
    accounting_notes = fields.Text(string='Accounting Notes')

    # Direction / Management
    decision_ref = fields.Char(string='Decision Ref')
    decision_date = fields.Date(string='Decision Date')
    decision_type = fields.Selection([
        ('approval', 'Approval'), ('rejection', 'Rejection'),
        ('delegation', 'Delegation'), ('arbitrage', 'Arbitrage'),
    ], string='Decision Type')
    approved_by_dg = fields.Boolean(string='DG Approved')
    approval_date = fields.Date(string='Approval Date')
    reclamation_date = fields.Date(string='Claim Date')
    reclamation_status = fields.Selection([
        ('ouverte', 'Open'), ('en_cours', 'In Progress'),
        ('traitee', 'Processed'), ('cloturee', 'Closed'),
    ], string='Claim Status', default='ouverte')
    reclamation_resolution = fields.Text(string='Claim Resolution')
    direction_notes = fields.Text(string='Management Notes')

    # Achats / Purchasing
    supplier_id = fields.Many2one('res.partner', string='Supplier')
    purchase_order_ref = fields.Char(string='PO Ref')
    purchase_need_date = fields.Date(string='Need By Date')
    purchase_priority = fields.Selection([
        ('low', 'Low'), ('normal', 'Normal'), ('high', 'High'), ('urgent', 'Urgent'),
    ], string='Purchase Priority', default='normal')
    purchase_stock_security = fields.Integer(string='Stock Security Days')
    purchase_notes = fields.Text(string='Purchase Notes')

    _sql_constraints = [
        ('name_uniq_per_partner', 'UNIQUE(name, partner_id)', 'A lead with this name already exists for this customer.'),
    ]

    @api.model
    def _default_stage_id(self):
        return self.env['jil.crm.stage'].search([
            ('team_ids', 'in', self.team_id.ids or []),
        ], order='sequence', limit=1).id

    @api.depends('score')
    def _compute_score_grade(self):
        for r in self:
            if r.score >= 80:
                r.score_grade = 'a'
            elif r.score >= 50:
                r.score_grade = 'b'
            elif r.score >= 20:
                r.score_grade = 'c'
            else:
                r.score_grade = 'd'

    @api.depends('communication_ids')
    def _compute_communication_count(self):
        for lead in self:
            lead.communication_count = len(lead.communication_ids)

    @api.depends('stage_id', 'date_last_stage_update')
    def _compute_stage_duration(self):
        for lead in self:
            if lead.date_last_stage_update:
                lead.deal_stage_duration = (fields.Datetime.now() - lead.date_last_stage_update).days
            else:
                lead.deal_stage_duration = 0

    @api.depends('date_open')
    def _compute_deal_age(self):
        for lead in self:
            if lead.date_open:
                lead.deal_age = (fields.Datetime.now() - lead.date_open).days
            else:
                lead.deal_age = 0

    def action_set_lost(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Lost Reason'),
            'res_model': 'jil.crm.lost.reason.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_lead_id': self.id},
        }

    def action_set_won(self):
        for lead in self:
            stage = self.env['jil.crm.stage'].search([
                ('is_won', '=', True), ('team_ids', 'in', lead.team_id.ids),
            ], limit=1)
            lead.write({
                'stage_id': stage.id,
                'probability': 100, 'date_close': fields.Datetime.now(),
                'type': 'opportunity',
            })

    def action_convert_to_opportunity(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Convert to Opportunity'),
            'res_model': 'jil.crm.lead.to.opportunity',
            'view_mode': 'form', 'target': 'new',
            'context': {'default_lead_id': self.id},
        }

    def action_view_communications(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Communications'),
            'res_model': 'jil.crm.communication',
            'view_mode': 'tree,form',
            'domain': [('lead_id', '=', self.id)],
            'context': {'default_lead_id': self.id},
        }

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            self.partner_name = self.partner_id.name
            self.email_from = self.partner_id.email
            self.phone = self.partner_id.phone
            self.mobile = self.partner_id.mobile

    def write(self, vals):
        if 'stage_id' in vals:
            vals['date_last_stage_update'] = fields.Datetime.now()
        return super().write(vals)

    def action_recalculate_score(self):
        for lead in self:
            lead._compute_lead_score()

    def _compute_lead_score(self):
        score = 0
        if self.expected_revenue and self.expected_revenue > 0:
            if self.expected_revenue > 100000:
                score += 30
            elif self.expected_revenue > 50000:
                score += 20
            else:
                score += 10
        if self.email_from:
            score += 5
        if self.phone:
            score += 5
        if self.partner_id:
            score += 10
        if self.description:
            score += 5
        if self.communication_count > 5:
            score += 15
        elif self.communication_count > 2:
            score += 10
        if self.tag_ids:
            score += 5
        grade_map = {'0': 0, '1': 5, '2': 10, '3': 15}
        score += grade_map.get(self.priority, 0)
        self.score = min(score, 100)

    def action_assign_to_rule(self):
        rules = self.env['jil.lead.assignment.rule'].search([
            ('active', '=', True),
            ('team_id', 'in', self.team_id.ids),
        ], order='priority desc, id')
        for rule in rules:
            assigned = rule._try_assign_lead(self)
            if assigned:
                break


class JilCrmCommunication(models.Model):
    _name = 'jil.crm.communication'
    _description = 'JIL CRM Communication'
    _order = 'date desc'

    lead_id = fields.Many2one('jil.crm.lead', string='Lead', required=True, ondelete='cascade')
    communication_type = fields.Selection([
        ('call', 'Phone Call'), ('email', 'Email'), ('meeting', 'Meeting'),
        ('site_visit', 'Site Visit'), ('demo', 'Product Demo'),
        ('chatbot', 'Chatbot Interaction'), ('other', 'Other'),
    ], string='Type', required=True, default='call')
    date = fields.Datetime(string='Date', default=fields.Datetime.now, required=True)
    summary = fields.Text(string='Summary', required=True)
    user_id = fields.Many2one('res.users', string='Assigned to', default=lambda self: self.env.user)
    next_action = fields.Text(string='Next Action')
    next_action_date = fields.Date(string='Next Action Date')



