from odoo import api, fields, models, _


class CrmLeadToOpportunity(models.TransientModel):
    _name = 'jil.crm.lead.to.opportunity'
    _description = 'Convert Lead to Opportunity'

    lead_id = fields.Many2one('jil.crm.lead', string='Lead', required=True)
    name = fields.Char(string='Opportunity Name', required=True)
    expected_revenue = fields.Monetary(string='Expected Revenue', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Currency',
                                   default=lambda self: self.env.company.currency_id)
    probability = fields.Float(string='Probability (%)', default=20.0)
    team_id = fields.Many2one('crm.team', string='Sales Team')
    user_id = fields.Many2one('res.users', string='Salesperson', default=lambda self: self.env.user)

    @api.model
    def default_get(self, fields_list):
        result = super().default_get(fields_list)
        if self.env.context.get('default_lead_id'):
            lead = self.env['jil.crm.lead'].browse(self.env.context['default_lead_id'])
            result.update({
                'name': lead.name,
                'expected_revenue': lead.expected_revenue,
                'probability': lead.probability or 20,
                'team_id': lead.team_id.id,
                'user_id': lead.user_id.id or self.env.user.id,
            })
        return result

    def action_convert(self):
        self.lead_id.write({
            'type': 'opportunity',
            'name': self.name,
            'expected_revenue': self.expected_revenue,
            'probability': self.probability,
            'team_id': self.team_id.id,
            'user_id': self.user_id.id,
            'stage_id': self.env['jil.crm.stage'].search([
                ('team_ids', 'in', self.team_id.ids),
            ], order='sequence', limit=1).id or self.lead_id.stage_id.id,
        })
        return {'type': 'ir.actions.act_window_close'}
