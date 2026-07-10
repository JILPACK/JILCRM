from odoo import fields, models


class EmailSequence(models.Model):
    _name = 'jil.email.sequence'
    _description = 'Automated Email Sequence'
    _order = 'sequence, id'

    sequence = fields.Integer(string='Sequence Order', default=10)
    name = fields.Char(string='Sequence Name', required=True)
    active = fields.Boolean(string='Active', default=True)
    model = fields.Selection([
        ('lead', 'Lead'), ('booking', 'Booking'), ('project', 'Project'),
        ('deal', 'Deal'), ('general', 'General'),
    ], string='Target Model', default='lead')
    trigger_event = fields.Selection([
        ('create', 'On Create'),
        ('stage', 'On Stage Change'),
        ('score', 'On Score Threshold'),
        ('booking_confirm', 'On Booking Confirmation'),
        ('booking_reminder', 'Booking Reminder'),
        ('project_update', 'On Project Update'),
    ], string='Trigger Event', default='create')
    trigger_stage_id = fields.Many2one('jil.crm.stage', string='Trigger Stage')
    min_score = fields.Integer(string='Min Score', default=0)
    delay_hours = fields.Integer(string='Delay After Trigger (hours)', default=0)

    template_id = fields.Many2one('mail.template', string='Email Template', required=True)
    send_to = fields.Selection([
        ('partner', 'Customer'), ('salesperson', 'Salesperson'),
        ('manager', 'Manager'), ('custom', 'Custom Email'),
    ], string='Send To', default='partner')
    custom_email = fields.Char(string='Custom Email')
    cc_to = fields.Selection([
        ('none', 'No CC'), ('salesperson', 'CC Salesperson'),
        ('manager', 'CC Manager'),
    ], string='CC', default='none')
