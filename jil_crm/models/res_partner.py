from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    lead_ids = fields.One2many('jil.crm.lead', 'partner_id', string='CRM Leads')
    lead_count = fields.Integer(string='CRM Lead Count', compute='_compute_lead_count')
    context_ids = fields.One2many('jil.mcp.context', 'partner_id', string='Unified Contexts')
    context_count = fields.Integer(string='Context Count', compute='_compute_context_count')
    score = fields.Integer(string='CRM Score', default=0)
    score_grade = fields.Selection([
        ('a', 'A - VIP'), ('b', 'B - Regular'), ('c', 'C - Occasional'),
    ], string='Score Grade', default='c')
    last_interaction = fields.Datetime(string='Last Interaction')
    total_revenue = fields.Monetary(string='Total Revenue', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Currency',
                                   default=lambda self: self.env.company.currency_id)
    lifetime_value = fields.Monetary(string='Lifetime Value', currency_field='currency_id')

    @api.depends('lead_ids')
    def _compute_lead_count(self):
        for partner in self:
            partner.lead_count = len(partner.lead_ids)

    @api.depends('context_ids')
    def _compute_context_count(self):
        for partner in self:
            partner.context_count = len(partner.context_ids)

    def action_view_leads(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Leads / Opportunities',
            'res_model': 'jil.crm.lead',
            'view_mode': 'tree,form',
            'domain': [('partner_id', '=', self.id)],
        }

    def action_view_context(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Unified Context',
            'res_model': 'jil.mcp.context',
            'view_mode': 'tree,form',
            'domain': [('partner_id', '=', self.id)],
        }
