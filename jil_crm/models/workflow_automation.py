from odoo import api, fields, models, _


class WorkflowAutomation(models.Model):
    _name = 'jil.workflow.automation'
    _description = 'Workflow Automation Rule'
    _order = 'sequence, id'

    name = fields.Char(string='Rule Name', required=True)
    active = fields.Boolean(string='Active', default=True)
    sequence = fields.Integer(string='Sequence', default=10)
    model = fields.Selection([
        ('jil.crm.lead', 'Lead'),
        ('jil.crm.lead.to.opportunity', 'Lead Conversion'),
        ('jil.consultation.booking', 'Booking'),
        ('jil.project.tracking', 'Project'),
        ('jil.deal.tracking', 'Deal'),
    ], string='Target Model', required=True, default='jil.crm.lead')

    trigger_type = fields.Selection([
        ('on_create', 'On Create'),
        ('on_write', 'On Update'),
        ('stage_change', 'Stage Change'),
        ('score_threshold', 'Score Threshold'),
        ('time_based', 'Scheduled (Time Based)'),
        ('cron', 'Scheduled (Cron)'),
    ], string='Trigger', required=True, default='on_create')

    trigger_field = fields.Char(string='Trigger Field')
    trigger_operator = fields.Selection([
        ('=', '='), ('!=', '!='), ('>', '>'), ('<', '<'),
        ('>=', '>='), ('<=', '<='), ('changed', 'Changed'),
    ], string='Operator', default='=')
    trigger_value = fields.Char(string='Trigger Value')

    action_type = fields.Selection([
        ('email', 'Send Email'),
        ('create_activity', 'Create Activity'),
        ('update_field', 'Update Field'),
        ('assign_user', 'Assign User'),
        ('create_record', 'Create Record'),
        ('webhook', 'Webhook Call'),
        ('sms', 'Send SMS'),
        ('notification', 'Send Notification'),
    ], string='Action', required=True, default='email')

    # Email action
    email_template_id = fields.Many2one('mail.template', string='Email Template')
    email_to = fields.Char(string='Send To (email)')
    email_cc = fields.Char(string='CC')

    # Activity action
    activity_type_id = fields.Many2one('mail.activity.type', string='Activity Type')
    activity_summary = fields.Char(string='Activity Summary')
    activity_note = fields.Text(string='Activity Note')
    activity_user_id = fields.Many2one('res.users', string='Activity Assignee')

    # Update field action
    update_field_name = fields.Char(string='Field Name')
    update_field_value = fields.Char(string='Field Value')

    # Assign action
    assign_user_id = fields.Many2one('res.users', string='User to Assign')
    assign_team_id = fields.Many2one('crm.team', string='Team to Assign')

    # Create record action
    create_model = fields.Char(string='Model to Create')
    create_values = fields.Text(string='Create Values (JSON)')

    # Webhook
    webhook_url = fields.Char(string='Webhook URL')
    webhook_method = fields.Selection([('GET', 'GET'), ('POST', 'POST')], string='Method', default='POST')
    webhook_headers = fields.Text(string='Headers (JSON)')
    webhook_body = fields.Text(string='Body Template')

    condition_domain = fields.Text(string='Condition Domain', help='Extra domain conditions')
    cron_interval = fields.Integer(string='Cron Interval (hours)', default=24)
    last_run = fields.Datetime(string='Last Run')
    run_count = fields.Integer(string='Run Count', default=0)

