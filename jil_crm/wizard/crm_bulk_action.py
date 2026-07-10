from odoo import api, fields, models


class CrmBulkAction(models.TransientModel):
    _name = 'jil.crm.bulk.action'
    _description = 'CRM Bulk Action Wizard'

    lead_ids = fields.Many2many('jil.crm.lead', string='Leads', required=True)
    action_type = fields.Selection([
        ('assign', 'Assign To'),
        ('stage', 'Change Stage'),
        ('tag', 'Add Tags'),
        ('delete', 'Delete'),
    ], string='Action', required=True, default='assign')
    user_id = fields.Many2one('res.users', string='Assign To')
    team_id = fields.Many2one('crm.team', string='Sales Team')
    stage_id = fields.Many2one('jil.crm.stage', string='Stage')
    tag_ids = fields.Many2many('crm.tag', string='Tags')

    def action_execute(self):
        leads = self.lead_ids
        if self.action_type == 'assign':
            data = {}
            if self.user_id:
                data['user_id'] = self.user_id.id
            if self.team_id:
                data['team_id'] = self.team_id.id
            leads.write(data)
        elif self.action_type == 'stage' and self.stage_id:
            leads.write({'stage_id': self.stage_id.id})
        elif self.action_type == 'tag' and self.tag_ids:
            for lead in leads:
                lead.tag_ids = [(4, t.id) for t in self.tag_ids]
        elif self.action_type == 'delete':
            leads.unlink()
        return {'type': 'ir.actions.act_window_close'}
