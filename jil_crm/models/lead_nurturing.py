from odoo import api, fields, models


class NurturingCampaign(models.Model):
    _name = 'jil.nurturing.campaign'
    _description = 'Nurturing Campaign'
    _order = 'create_date desc'

    name = fields.Char(string='Campaign Name', required=True)
    active = fields.Boolean(string='Active', default=True)
    campaign_type = fields.Selection([
        ('email', 'Email Drip'),
        ('content', 'Content Marketing'),
        ('social', 'Social Media'),
        ('multi_channel', 'Multi-Channel'),
    ], string='Campaign Type', default='email')
    description = fields.Text(string='Description')
    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')
    team_id = fields.Many2one('crm.team', string='Sales Team')
    tag_ids = fields.Many2many('crm.tag', string='Target Tags')
    min_score = fields.Integer(string='Min Score', default=10)
    max_score = fields.Integer(string='Max Score', default=80)
    step_ids = fields.One2many('jil.nurturing.step', 'campaign_id', string='Campaign Steps',
                                copy=True)
    lead_ids = fields.One2many('jil.crm.lead', 'nurturing_campaign_id', string='Leads')
    lead_count = fields.Integer(string='Lead Count', compute='_compute_lead_count')
    converted_count = fields.Integer(string='Converted', compute='_compute_converted')
    conversion_rate = fields.Float(string='Conversion Rate', compute='_compute_conversion_rate')

    @api.depends('lead_ids')
    def _compute_lead_count(self):
        for c in self:
            c.lead_count = len(c.lead_ids)

    @api.depends('lead_ids')
    def _compute_converted(self):
        for c in self:
            c.converted_count = len(c.lead_ids.filtered(lambda l: l.type == 'opportunity'))

    @api.depends('lead_count', 'converted_count')
    def _compute_conversion_rate(self):
        for c in self:
            c.conversion_rate = (c.converted_count / c.lead_count * 100) if c.lead_count else 0

    def action_enroll_leads(self):
        leads = self.env['jil.crm.lead'].search([
            ('score', '>=', self.min_score),
            ('score', '<=', self.max_score),
            ('type', '=', 'lead'),
            ('nurturing_status', '=', 'none'),
        ])
        if self.tag_ids:
            leads = leads.filtered(lambda l: any(t in l.tag_ids for t in self.tag_ids))
        leads.write({
            'nurturing_campaign_id': self.id,
            'nurturing_status': 'active',
            'nurturing_start_date': fields.Date.today(),
        })
        return leads


class NurturingStep(models.Model):
    _name = 'jil.nurturing.step'
    _description = 'Nurturing Campaign Step'
    _order = 'campaign_id, sequence, id'

    campaign_id = fields.Many2one('jil.nurturing.campaign', string='Campaign',
                                   required=True, ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=10)
    name = fields.Char(string='Step Name', required=True)
    step_type = fields.Selection([
        ('email', 'Send Email'),
        ('wait', 'Wait/Delay'),
        ('condition', 'Conditional Branch'),
        ('score_update', 'Update Score'),
        ('tag', 'Add Tag'),
        ('assign', 'Assign Salesperson'),
        ('stage', 'Change Stage'),
    ], string='Step Type', required=True, default='email')
    delay_days = fields.Integer(string='Delay (Days)', default=1)
    email_template_id = fields.Many2one('mail.template', string='Email Template')
    condition_field = fields.Char(string='Condition Field')
    condition_operator = fields.Selection([
        ('=', '='), ('!=', '!='), ('>', '>'), ('<', '<'),
    ], string='Condition Operator', default='=')
    condition_value = fields.Char(string='Condition Value')
    score_change = fields.Integer(string='Score Change', default=0)
    tag_id = fields.Many2one('crm.tag', string='Tag to Add')
    stage_id = fields.Many2one('jil.crm.stage', string='Stage to Set')
    active = fields.Boolean(string='Active', default=True)
