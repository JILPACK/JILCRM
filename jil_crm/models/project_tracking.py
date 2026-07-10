from odoo import api, fields, models, _


class ProjectTracking(models.Model):
    _name = 'jil.project.tracking'
    _description = 'Project Tracking'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Project Name', required=True, tracking=True)
    lead_id = fields.Many2one('jil.crm.lead', string='Related Lead/Opportunity', tracking=True)
    partner_id = fields.Many2one('res.partner', string='Client', tracking=True)
    user_id = fields.Many2one('res.users', string='Project Manager', tracking=True,
                              default=lambda self: self.env.user)
    team_id = fields.Many2one('crm.team', string='Team')

    status = fields.Selection([
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('on_hold', 'On Hold'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='not_started', tracking=True)

    priority = fields.Selection([
        ('0', 'Low'), ('1', 'Medium'), ('2', 'High'), ('3', 'Critical'),
    ], string='Priority', default='1')

    start_date = fields.Date(string='Start Date', tracking=True)
    end_date = fields.Date(string='End Date', tracking=True)
    deadline = fields.Date(string='Deadline', tracking=True)
    duration_days = fields.Integer(string='Duration (days)', compute='_compute_duration')

    description = fields.Html(string='Description')
    notes = fields.Text(string='Notes')

    milestone_ids = fields.One2many('jil.project.milestone', 'project_id', string='Milestones')
    task_ids = fields.One2many('jil.project.task', 'project_id', string='Tasks')
    milestone_count = fields.Integer(string='Milestone Count', 
compute='_compute_counts')
    task_count = fields.Integer(string='Task Count', compute='_compute_counts')
    completed_task_count = fields.Integer(string='Completed Tasks', compute='_compute_counts')
    progress = fields.Float(string='Progress (%)', compute='_compute_progress', store=True)
    budget = fields.Monetary(string='Budget', currency_field='currency_id')
    actual_cost = fields.Monetary(string='Actual Cost', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Currency',
                                   default=lambda self: self.env.company.currency_id)

    color = fields.Integer(string='Color')

    # Context MCP
    context_id = fields.Many2one('jil.mcp.context', string='Unified Context')

    @api.depends('start_date', 'end_date')
    def _compute_duration(self):
        for p in self:
            if p.start_date and p.end_date:
                p.duration_days = (p.end_date - p.start_date).days
            else:
                p.duration_days = 0

    @api.depends('milestone_ids', 'task_ids', 'task_ids.status')
    def _compute_counts(self):
        if not self.ids:
            return
        task_data = self.env['jil.project.task'].read_group(
            [('project_id', 'in', self.ids)], ['project_id'], ['project_id']
        )
        task_map = {r['project_id'][0]: {'count': r['project_id_count']} for r in task_data}
        done_data = self.env['jil.project.task'].read_group(
            [('project_id', 'in', self.ids), ('status', '=', 'done')],
            ['project_id'], ['project_id']
        )
        done_map = {r['project_id'][0]: r['project_id_count'] for r in done_data}
        milestone_data = self.env['jil.project.milestone'].read_group(
            [('project_id', 'in', self.ids)], ['project_id'], ['project_id']
        )
        milestone_map = {r['project_id'][0]: r['project_id_count'] for r in milestone_data}
        for p in self:
            p.task_count = task_map.get(p.id, {}).get('count', 0)
            p.completed_task_count = done_map.get(p.id, 0)
            p.milestone_count = milestone_map.get(p.id, 0)

    @api.depends('task_ids', 'task_ids.status', 'task_ids.progress')
    def _compute_progress(self):
        if not self.ids:
            return
        task_progress = self.env['jil.project.task'].read_group(
            [('project_id', 'in', self.ids)],
            ['project_id', 'progress:avg'], ['project_id']
        )
        progress_map = {r['project_id'][0]: r['progress'] for r in task_progress}
        milestone_data = self.env['jil.project.milestone'].read_group(
            [('project_id', 'in', self.ids), ('status', '=', 'completed')],
            ['project_id'], ['project_id']
        )
        milestone_done = {r['project_id'][0]: r['project_id_count'] for r in milestone_data}
        milestone_total = self.env['jil.project.milestone'].read_group(
            [('project_id', 'in', self.ids)], ['project_id'], ['project_id']
        )
        milestone_all = {r['project_id'][0]: r['project_id_count'] for r in milestone_total}
        for p in self:
            task_avg = progress_map.get(p.id)
            if task_avg is not None:
                p.progress = task_avg
            elif milestone_all.get(p.id, 0) > 0:
                done = milestone_done.get(p.id, 0)
                total = milestone_all[p.id]
                p.progress = (done / total) * 100
            else:
                p.progress = 0.0

    def action_start(self):
        self.write({'status': 'in_progress', 'start_date': fields.Date.today()})

    def action_complete(self):
        self.write({'status': 'completed', 'end_date': fields.Date.today()})

    def action_hold(self):
        self.write({'status': 'on_hold'})


class ProjectMilestone(models.Model):
    _name = 'jil.project.milestone'
    _description = 'Project Milestone'
    _order = 'project_id, date, name'

    name = fields.Char(string='Milestone', required=True)
    project_id = fields.Many2one('jil.project.tracking', string='Project',
                                  required=True, ondelete='cascade')
    description = fields.Text(string='Description')
    date = fields.Date(string='Target Date')
    completed_date = fields.Date(string='Completed Date')
    status = fields.Selection([
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('delayed', 'Delayed'),
    ], string='Status', default='pending')
    assigned_to = fields.Many2one('res.users', string='Assigned To')
    deliverable = fields.Text(string='Deliverable')
    progress = fields.Float(string='Progress (%)', default=0.0)
    weight = fields.Float(string='Weight (%)', default=0.0)

    def action_complete(self):
        self.write({
            'status': 'completed',
            'completed_date': fields.Date.today(),
            'progress': 100,
        })


class ProjectTask(models.Model):
    _name = 'jil.project.task'
    _description = 'Project Task'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'project_id, priority desc, create_date'

    name = fields.Char(string='Task Name', required=True, tracking=True)
    project_id = fields.Many2one('jil.project.tracking', string='Project',
                                  required=True, ondelete='cascade')
    milestone_id = fields.Many2one('jil.project.milestone', string='Milestone')
    description = fields.Text(string='Description')
    assigned_to = fields.Many2one('res.users', string='Assigned To', tracking=True)
    status = fields.Selection([
        ('todo', 'To Do'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
        ('blocked', 'Blocked'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='todo', tracking=True)
    priority = fields.Selection([
        ('0', 'Low'), ('1', 'Medium'), ('2', 'High'), ('3', 'Urgent'),
    ], string='Priority', default='1')

    estimated_hours = fields.Float(string='Estimated Hours')
    actual_hours = fields.Float(string='Actual Hours')
    progress = fields.Float(string='Progress (%)', default=0.0)
    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')
    deadline = fields.Date(string='Deadline')

    depends_on = fields.Many2many('jil.project.task', 'task_dependency_rel',
                                   'task_id', 'depends_on_id', string='Depends On')
    dependent_ids = fields.Many2many('jil.project.task', 'task_dependency_rel',
                                      'depends_on_id', 'task_id', string='Depended By')

    color = fields.Integer(string='Color')
    sequence = fields.Integer(string='Sequence', default=10)

    def action_start(self):
        self.write({'status': 'in_progress', 'start_date': fields.Date.today()})

    def action_done(self):
        self.write({'status': 'done', 'progress': 100, 'end_date': fields.Date.today()})

    def action_block(self):
        self.write({'status': 'blocked'})
