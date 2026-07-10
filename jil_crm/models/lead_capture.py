from odoo import api, fields, models


class LeadCaptureForm(models.Model):
    _name = 'jil.lead.capture.form'
    _description = 'Lead Capture Form'
    _order = 'create_date desc'

    name = fields.Char(string='Form Name', required=True)
    active = fields.Boolean(string='Active', default=True)
    form_type = fields.Selection([
        ('website', 'Website Form'),
        ('landing_page', 'Landing Page'),
        ('popup', 'Popup Form'),
        ('embedded', 'Embedded Widget'),
        ('api', 'API Endpoint'),
    ], string='Form Type', default='website')
    form_code = fields.Char(string='Form Code/ID')
    description = fields.Text(string='Description')
    team_id = fields.Many2one('crm.team', string='Default Sales Team')
    user_id = fields.Many2one('res.users', string='Default Salesperson')
    stage_id = fields.Many2one('jil.crm.stage', string='Default Stage')
    tag_ids = fields.Many2many('crm.tag', string='Default Tags')
    scoring_rule_ids = fields.Many2many('jil.lead.scoring.rule', string='Scoring Rules')
    assignment_rule_id = fields.Many2one('jil.lead.assignment.rule', string='Assignment Rule')
    auto_reply_template = fields.Many2one('mail.template', string='Auto Reply Email')
    confirmation_message = fields.Html(string='Confirmation Message')
    fields_json = fields.Text(string='Form Fields (JSON)')
    lead_count = fields.Integer(string='Leads Captured', compute='_compute_lead_count')
    capture_count = fields.Integer(string='Submissions', default=0)
    conversion_rate = fields.Float(string='Conversion Rate (%)', compute='_compute_conversion_rate')

    @api.depends('lead_count', 'capture_count')
    def _compute_conversion_rate(self):
        for f in self:
            f.conversion_rate = (f.lead_count / f.capture_count * 100) if f.capture_count else 0

    def _compute_lead_count(self):
        if not self.ids:
            return
        codes = [f.form_code for f in self if f.form_code]
        if not codes:
            for f in self:
                f.lead_count = 0
            return
        data = self.env['jil.crm.lead'].read_group(
            [('capture_form_id', 'in', codes)],
            ['capture_form_id'], ['capture_form_id']
        )
        data_map = {r['capture_form_id']: r['capture_form_id_count'] for r in data}
        for f in self:
            f.lead_count = data_map.get(f.form_code, 0)

    def action_capture_lead(self, vals):
        lead = self.env['jil.crm.lead'].create({
            'name': vals.get('name', 'Web Lead'),
            'email_from': vals.get('email_from'),
            'phone': vals.get('phone'),
            'partner_name': vals.get('partner_name'),
            'description': vals.get('description'),
            'capture_source': 'website',
            'capture_form_id': self.form_code,
            'capture_url': vals.get('capture_url'),
            'consent_given': vals.get('consent', True),
            'team_id': self.team_id.id or self.env.context.get('default_team_id'),
            'user_id': self.user_id.id or self.env.context.get('default_user_id'),
            'stage_id': self.stage_id.id or self.env['jil.crm.stage'].search([
                ('is_default', '=', True),
            ], limit=1).id,
            'tag_ids': [(6, 0, self.tag_ids.ids)],
        })
        if self.scoring_rule_ids:
            total_score = 0
            for rule in self.scoring_rule_ids:
                total_score += rule.evaluate(lead)
            lead.score = min(total_score, 100)
            lead.score_last_updated = fields.Datetime.now()
            lead._compute_score_grade()
        if self.assignment_rule_id:
            self.assignment_rule_id._try_assign_lead(lead)
        self.capture_count += 1
        return lead
