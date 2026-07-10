from odoo import api, fields, models


class CrmLeadScoringWizard(models.TransientModel):
    _name = 'jil.crm.lead.scoring.wizard'
    _description = 'Lead Scoring Wizard'

    lead_ids = fields.Many2many('jil.crm.lead', string='Leads', required=True)
    rule_ids = fields.Many2many('jil.lead.scoring.rule', string='Scoring Rules')

    def action_recalculate(self):
        leads = self.lead_ids
        rules = self.rule_ids or self.env['jil.lead.scoring.rule'].search([('active', '=', True)])
        for lead in leads:
            total = 0
            for rule in rules:
                total += rule.evaluate(lead)
            lead.write({
                'score': min(total, 100),
                'score_last_updated': fields.Datetime.now(),
            })
            lead._compute_score_grade()
        return {'type': 'ir.actions.act_window_close'}
