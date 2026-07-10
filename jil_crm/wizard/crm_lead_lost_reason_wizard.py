from odoo import api, fields, models, _


class JilCrmLostReasonWizard(models.TransientModel):
    _name = 'jil.crm.lost.reason.wizard'
    _description = 'Lost Reason Wizard'

    lead_id = fields.Many2one('jil.crm.lead', string='Lead', required=True)
    lost_reason = fields.Text(string='Lost Reason', required=True)

    def action_confirm(self):
        self.lead_id.write({
            'lost_reason': self.lost_reason,
            'stage_id': self.env['jil.crm.stage'].search([
                ('is_lost', '=', True),
                ('team_ids', 'in', self.lead_id.team_id.ids),
            ], limit=1).id,
            'active': False,
            'date_close': fields.Datetime.now(),
        })
        return {'type': 'ir.actions.act_window_close'}
