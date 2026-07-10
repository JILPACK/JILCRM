from odoo import api, fields, models


class NotificationTrigger(models.Model):
    _name = 'jil.notification.trigger'
    _description = 'Notification Trigger'
    _order = 'sequence, id'

    name = fields.Char(string='Trigger Name', required=True)
    active = fields.Boolean(string='Active', default=True)
    model = fields.Selection([
        ('jil.crm.lead', 'Lead'),
        ('jil.consultation.booking', 'Booking'),
        ('jil.project.tracking', 'Project'),
        ('jil.deal.tracking', 'Deal'),
        ('jil.chatbot.session', 'Chatbot Session'),
    ], string='Model', required=True, default='jil.crm.lead')

    trigger_on = fields.Selection([
        ('create', 'On Create'),
        ('write', 'On Update'),
        ('field_change', 'On Field Change'),
        ('score', 'Score Threshold'),
        ('stage', 'Stage Change'),
    ], string='Trigger On', required=True, default='create')

    field_name = fields.Char(string='Field Name')
    operator = fields.Selection([
        ('=', '='), ('!=', '!='), ('>', '>'), ('<', '<'),
        ('changed', 'Changed'),
    ], string='Operator', default='=')
    value = fields.Char(string='Value')

    notification_type = fields.Selection([
        ('in_app', 'In-App Notification'),
        ('email', 'Email'),
        ('both', 'Both'),
    ], string='Notification Type', default='in_app')
    title = fields.Char(string='Notification Title', required=True)
    message = fields.Text(string='Notification Message', required=True)
    notify_user = fields.Many2one('res.users', string='Notify Specific User')
    notify_role = fields.Selection([
        ('salesperson', 'Salesperson'),
        ('manager', 'Manager'),
        ('team', 'Sales Team'),
        ('admin', 'Administrator'),
    ], string='Notify Role', default='salesperson')
    email_template_id = fields.Many2one('mail.template', string='Email Template')

    last_triggered = fields.Datetime(string='Last Triggered')
    trigger_count = fields.Integer(string='Trigger Count', default=0)

    def action_trigger(self, record):
        if not self.active:
            return False
        users = self._get_target_users(record)
        for user in users:
            if self.notification_type in ('in_app', 'both'):
                formatted_msg = self._format_message(record)
                user.notify_success(message=formatted_msg, title=self.title)
            if self.notification_type in ('email', 'both') and self.email_template_id:
                self.email_template_id.send_mail(record.id, force_send=True)
        self.write({
            'trigger_count': self.trigger_count + 1,
            'last_triggered': fields.Datetime.now(),
        })
        return True

    def _get_target_users(self, record):
        if self.notify_user:
            return self.notify_user
        if self.notify_role == 'salesperson' and hasattr(record, 'user_id') and record.user_id:
            return record.user_id
        if self.notify_role == 'manager':
            return self.env['res.users'].search([('share', '=', False), ('id', 'in', self.env.ref('sales_team.group_sale_manager').users.ids)])
        if self.notify_role == 'admin':
            return self.env['res.users'].search([('share', '=', False), ('id', 'in', self.env.ref('base.group_system').users.ids)])
        if self.notify_role == 'team' and hasattr(record, 'team_id') and record.team_id:
            return record.team_id.member_ids
        return self.env.user

    def _format_message(self, record):
        name = record.display_name if hasattr(record, 'display_name') else str(record)
        return self.message.replace('{name}', name).replace('{id}', str(record.id))
