from odoo import api, fields, models


class JilCrmStage(models.Model):
    _name = 'jil.crm.stage'
    _description = 'JIL CRM Stage'
    _order = 'sequence, id'

    name = fields.Char(string='Stage Name', required=True, translate=True)
    sequence = fields.Integer(string='Sequence', default=10)
    probability = fields.Float(string='Probability (%)', default=0.0)
    is_won = fields.Boolean(string='Is Won Stage', default=False)
    is_lost = fields.Boolean(string='Is Lost Stage', default=False)
    is_default = fields.Boolean(string='Default Stage', default=False)
    color = fields.Integer(string='Color Index', default=0)
    team_ids = fields.Many2many('crm.team', string='Sales Teams')
    pipeline_category = fields.Selection([
        ('lead', 'Lead Pipeline'),
        ('opportunity', 'Opportunity Pipeline'),
        ('booking', 'Booking Pipeline'),
        ('project', 'Project Pipeline'),
    ], string='Pipeline Category', default='lead')
    stage_type = fields.Selection([
        ('active', 'Active'),
        ('won', 'Won'),
        ('lost', 'Lost'),
    ], string='Stage Type', default='active')
    automation_email_template = fields.Many2one('mail.template', string='Auto Email Template')
    automation_delay_hours = fields.Integer(string='Auto Email Delay (hours)', default=0)
    require_follow_up = fields.Boolean(string='Require Follow-up', default=False)
    follow_up_days = fields.Integer(string='Follow-up Days', default=3)
    lead_count = fields.Integer(string='Lead Count', compute='_compute_lead_count')

    _sql_constraints = [
        ('name_uniq', 'UNIQUE(name)', 'Stage name must be unique.'),
    ]

    def _compute_lead_count(self):
        data = self.env['jil.crm.lead'].read_group(
            [('stage_id', 'in', self.ids)], ['stage_id'], ['stage_id']
        )
        data_map = {item['stage_id'][0]: item['stage_id_count'] for item in data}
        for stage in self:
            stage.lead_count = data_map.get(stage.id, 0)
