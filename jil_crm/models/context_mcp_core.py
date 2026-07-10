import logging
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class McpContext(models.Model):
    _name = 'jil.mcp.context'
    _description = 'Unified JIL CRM Context (MCP)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Context ID', required=True, default='NEW')
    partner_id = fields.Many2one('res.partner', string='Client', tracking=True, index=True)
    partner_name = fields.Char(string='Client Name', tracking=True)
    partner_email = fields.Char(string='Email', tracking=True)
    partner_phone = fields.Char(string='Phone', tracking=True)

    # Lifecycle
    lifecycle_state = fields.Selection([
        ('visitor', 'Visitor'),
        ('lead', 'Lead'),
        ('qualified_lead', 'Qualified Lead'),
        ('opportunity', 'Opportunity'),
        ('customer', 'Customer'),
        ('active_client', 'Active Client'),
        ('inactive', 'Inactive'),
        ('churned', 'Churned'),
    ], string='Lifecycle State', default='visitor', tracking=True)
    lifecycle_last_change = fields.Datetime(string='Lifecycle Last Change')
    lifecycle_score = fields.Integer(string='Lifecycle Score', default=0)

    # Identity
    identity_matched = fields.Boolean(string='Identity Matched', default=False)
    identity_match_method = fields.Selection([
        ('email', 'Email Match'),
        ('phone', 'Phone Match'),
        ('cookie', 'Cookie/Device'),
        ('manual', 'Manual Merge'),
        ('ai', 'AI Match'),
    ], string='Match Method')
    identity_confidence = fields.Float(string='Identity Confidence', default=0.0)
    source_of_truth = fields.Selection([
        ('odoo', 'Odoo CRM'),
        ('website', 'Website'),
        ('chatbot', 'AI Chatbot'),
        ('supabase', 'Supabase'),
        ('external', 'External System'),
    ], string='Source of Truth', default='odoo')

    # Links to domain records
    lead_ids = fields.One2many('jil.crm.lead', 'context_id', string='Linked Leads')
    lead_id = fields.Many2one('jil.crm.lead', string='Primary Lead')
    booking_ids = fields.One2many('jil.consultation.booking', 'context_id', string='Bookings')
    project_ids = fields.One2many('jil.project.tracking', 'context_id', string='Projects')
    deal_ids = fields.One2many('jil.deal.tracking', 'context_id', string='Deals')
    chatbot_session_ids = fields.One2many('jil.chatbot.session', 'context_id', string='Chat Sessions')

    lead_count = fields.Integer(string='Leads', compute='_compute_related_counts')
    booking_count = fields.Integer(string='Booking Count', compute='_compute_related_counts')
    project_count = fields.Integer(string='Project Count', compute='_compute_related_counts')
    deal_count = fields.Integer(string='Deal Count', compute='_compute_related_counts')
    chat_count = fields.Integer(string='Chat Session Count', compute='_compute_related_counts')

    # Context Data
    context_timeline_ids = fields.One2many('jil.mcp.context.event', 'context_id',
                                            string='Timeline')
    context_data = fields.Text(string='Context Data (JSON)')
    context_summary = fields.Text(string='AI Context Summary')
    last_activity = fields.Datetime(string='Last Activity')
    total_interactions = fields.Integer(string='Total Interactions', default=0)

    # Sync status
    sync_status = fields.Selection([
        ('synced', 'Synced'),
        ('pending', 'Pending Sync'),
        ('syncing', 'Syncing'),
        ('failed', 'Sync Failed'),
        ('conflict', 'Conflict Detected'),
    ], string='Sync Status', default='pending')
    last_sync = fields.Datetime(string='Last Sync')
    last_sync_source = fields.Char(string='Last Sync Source')

    # AI fields
    ai_insights = fields.Text(string='AI Insights')
    ai_recommendation = fields.Text(string='AI Recommendation')
    ai_last_analyzed = fields.Datetime(string='Last AI Analysis')
    ai_lead_score = fields.Integer(string='AI Lead Score', default=0)
    ai_next_best_action = fields.Text(string='AI Next Best Action')
    ai_risk_score = fields.Integer(string='AI Risk Score', default=0)
    ai_churn_probability = fields.Float(string='AI Churn Probability', default=0.0)

    # Governance
    data_quality_score = fields.Integer(string='Data Quality Score', default=0)
    missing_fields = fields.Text(string='Missing Fields (JSON)')
    validation_status = fields.Selection([
        ('valid', 'Valid'),
        ('warning', 'Warning'),
        ('error', 'Error'),
    ], string='Validation Status', default='valid')
    validated_by = fields.Many2one('res.users', string='Validated By')
    validated_date = fields.Datetime(string='Validated Date')

    @api.model
    def create(self, vals):
        if vals.get('name', 'NEW') == 'NEW':
            vals['name'] = self.env['ir.sequence'].next_by_code('jil.mcp.context') or 'CTX-0001'
        return super().create(vals)

    @api.depends('lead_ids', 'booking_ids', 'project_ids', 'deal_ids', 'chatbot_session_ids')
    def _compute_related_counts(self):
        for c in self:
            c.lead_count = len(c.lead_ids)
            c.booking_count = len(c.booking_ids)
            c.project_count = len(c.project_ids)
            c.deal_count = len(c.deal_ids)
            c.chat_count = len(c.chatbot_session_ids)

    def action_sync_context(self):
        for ctx in self:
            ctx._sync_from_sources()

    def _sync_from_sources(self):
        self.write({'sync_status': 'syncing', 'last_sync': fields.Datetime.now()})
        try:
            if self.partner_id:
                leads = self.env['jil.crm.lead'].search([('partner_id', '=', self.partner_id.id)])
                if leads:
                    self.lead_ids = [(6, 0, leads.ids)]
                    self.lead_id = leads[0].id if not self.lead_id else self.lead_id
                    latest = leads.sorted('create_date', reverse=True)[0]
                    state = 'lead'
                    if latest.type == 'opportunity':
                        state = 'opportunity'
                    if latest.stage_id.is_won:
                        state = 'customer'
                    if latest.stage_id.is_lost:
                        state = 'inactive'
                    self.lifecycle_state = state
                    self.partner_name = self.partner_id.name
                    self.partner_email = self.partner_id.email
                    self.partner_phone = self.partner_id.phone
            self.sync_status = 'synced'
            self.last_sync = fields.Datetime.now()
        except Exception as e:
            _logger.error("Context sync failed for %s: %s", self.name, e, exc_info=True)
            self.sync_status = 'failed'

    def action_update_ai_insights(self):
        for ctx in self:
            ctx._compute_ai_insights()

    def _compute_ai_insights(self):
        insights = []
        score = self.lifecycle_score or 0
        if self.lead_count > 0:
            insights.append(f"Has {self.lead_count} lead(s)")
            score += 10
        if self.booking_count > 0:
            insights.append(f"Has {self.booking_count} booking(s)")
            score += 10
        if self.deal_count > 0:
            insights.append(f"Has {self.deal_count} deal(s)")
            score += 20
        if self.project_count > 0:
            insights.append(f"Has {self.project_count} project(s)")
            score += 15
        if self.chat_count > 0:
            insights.append(f"Has {self.chat_count} chatbot session(s)")
            score += 5
        if self.partner_id and self.partner_id.email:
            insights.append("Contact information available")
            score += 5
        self.write({
            'ai_insights': '\n'.join(insights) if insights else 'No significant data',
            'ai_lead_score': min(score, 100),
            'ai_last_analyzed': fields.Datetime.now(),
        })



