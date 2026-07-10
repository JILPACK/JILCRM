from odoo import fields, models


class McpContextEvent(models.Model):
    _name = 'jil.mcp.context.event'
    _description = 'Context Timeline Event'
    _order = 'timestamp desc, id'

    context_id = fields.Many2one('jil.mcp.context', string='Context',
                                  required=True, ondelete='cascade')
    timestamp = fields.Datetime(string='Timestamp', default=fields.Datetime.now, required=True)
    event_type = fields.Selection([
        ('lead_created', 'Lead Created'),
        ('lead_scored', 'Lead Scored'),
        ('lead_assigned', 'Lead Assigned'),
        ('lead_converted', 'Lead Converted'),
        ('lead_lost', 'Lead Lost'),
        ('booking_created', 'Booking Created'),
        ('booking_confirmed', 'Booking Confirmed'),
        ('booking_completed', 'Booking Completed'),
        ('chat_session', 'Chatbot Session'),
        ('deal_updated', 'Deal Updated'),
        ('deal_won', 'Deal Won'),
        ('deal_lost', 'Deal Lost'),
        ('project_created', 'Project Created'),
        ('project_updated', 'Project Updated'),
        ('email_sent', 'Email Sent'),
        ('activity_completed', 'Activity Completed'),
        ('stage_changed', 'Stage Changed'),
        ('sync_completed', 'Sync Completed'),
        ('sync_failed', 'Sync Failed'),
        ('ai_analysis', 'AI Analysis'),
        ('validation', 'Validation'),
        ('system', 'System Event'),
    ], string='Event Type', required=True)
    summary = fields.Text(string='Summary', required=True)
    source = fields.Char(string='Source')
    user_id = fields.Many2one('res.users', string='User')
    metadata = fields.Text(string='Metadata (JSON)')
