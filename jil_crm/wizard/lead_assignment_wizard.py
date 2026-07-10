from odoo import api, fields, models


class LeadAssignmentWizard(models.TransientModel):
    _name = 'jil.lead.assignment.wizard'
    _description = 'Lead Assignment Wizard'

    lead_ids = fields.Many2many('jil.crm.lead', string='Leads', required=True)
    user_id = fields.Many2one('res.users', string='Assign To', required=True)
    team_id = fields.Many2one('crm.team', string='Sales Team')

    def action_assign(self):
        self.lead_ids.write({
            'user_id': self.user_id.id,
            'team_id': self.team_id.id or self.lead_ids[0].team_id.id,
            'assignment_date': fields.Datetime.now(),
        })
        return {'type': 'ir.actions.act_window_close'}
