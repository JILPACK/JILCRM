from odoo import api, fields, models, _


class LeadAssignmentRule(models.Model):
    _name = 'jil.lead.assignment.rule'
    _description = 'Lead Assignment Rule'
    _order = 'priority desc, id'

    name = fields.Char(string='Rule Name', required=True)
    active = fields.Boolean(string='Active', default=True)
    priority = fields.Integer(string='Priority', default=0)
    team_id = fields.Many2one('crm.team', string='Sales Team')
    user_ids = fields.Many2many('res.users', string='Assignable Users')
    assignment_method = fields.Selection([
        ('round_robin', 'Round Robin'),
        ('least_busy', 'Least Busy'),
        ('territory', 'Territory Based'),
        ('revenue', 'Revenue Tier Based'),
        ('random', 'Random'),
    ], string='Assignment Method', required=True, default='round_robin')

    min_score = fields.Integer(string='Min Score', default=0)
    max_score = fields.Integer(string='Max Score', default=100)
    country_ids = fields.Many2many('res.country', string='Territories')
    max_leads_per_user = fields.Integer(string='Max Leads per User', default=50)
    auto_assign = fields.Boolean(string='Auto Assign on Create', default=True)
    assignment_count = fields.Integer(string='Assignments', compute='_compute_assignment_count')

    def _compute_assignment_count(self):
        if not self.ids:
            return
        data = self.env['jil.crm.lead'].read_group(
            [('assignment_rule_id', 'in', self.ids)],
            ['assignment_rule_id'], ['assignment_rule_id']
        )
        data_map = {r['assignment_rule_id'][0]: r['assignment_rule_id_count'] for r in data}
        for r in self:
            r.assignment_count = data_map.get(r.id, 0)

    def _try_assign_lead(self, lead):
        self.ensure_one()
        if not self.active or not self.user_ids:
            return False
        if lead.score < self.min_score or lead.score > self.max_score:
            return False
        if self.country_ids and lead.partner_id and lead.partner_id.country_id not in self.country_ids:
            return False
        user = self._select_user(lead)
        if user:
            lead.write({
                'user_id': user.id,
                'team_id': self.team_id.id,
                'assignment_rule_id': self.id,
                'assignment_date': fields.Datetime.now(),
                'assignment_auto': True,
            })
            return True
        return False

    def _select_user(self, lead):
        if not self.user_ids:
            return False
        if self.assignment_method == 'round_robin':
            assignments = self.env['jil.crm.lead'].read_group(
                [('user_id', 'in', self.user_ids.ids), ('assignment_rule_id', '=', self.id)],
                ['user_id'], ['user_id'],
            )
            counts = {a['user_id'][0]: a['user_id_count'] for a in assignments}
            sorted_users = sorted(self.user_ids, key=lambda u: counts.get(u.id, 0))
            return sorted_users[0] if sorted_users else False
        elif self.assignment_method == 'least_busy':
            assignments = self.env['jil.crm.lead'].read_group(
                [('user_id', 'in', self.user_ids.ids), ('active', '=', True)],
                ['user_id'], ['user_id'],
            )
            counts = {a['user_id'][0]: a['user_id_count'] for a in assignments}
            sorted_users = sorted(self.user_ids, key=lambda u: counts.get(u.id, 0))
            return sorted_users[0] if sorted_users else False
        elif self.assignment_method == 'random':
            import random
            return random.choice(self.user_ids)
        return self.user_ids[0]
