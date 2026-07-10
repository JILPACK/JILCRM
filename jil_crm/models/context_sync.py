from odoo import api, fields, models


class McpContextSync(models.Model):
    _name = 'jil.mcp.sync'
    _description = 'Context Synchronization Log'
    _order = 'create_date desc'

    name = fields.Char(string='Sync ID', required=True, default='NEW')
    context_id = fields.Many2one('jil.mcp.context', string='Context')
    sync_type = fields.Selection([
        ('website_crm', 'Website → CRM'),
        ('crm_website', 'CRM → Website'),
        ('chatbot_state', 'Chatbot State Sync'),
        ('persistent_context', 'Persistent Context'),
        ('automation', 'Automation Integration'),
        ('supabase', 'Supabase Sync'),
    ], string='Sync Type', required=True)
    status = fields.Selection([
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ], string='Status', default='pending')
    direction = fields.Selection([
        ('push', 'Push'), ('pull', 'Pull'), ('bidirectional', 'Bi-Directional'),
    ], string='Direction', default='push')

    source_system = fields.Char(string='Source System')
    target_system = fields.Char(string='Target System')
    data_payload = fields.Text(string='Data Payload (JSON)')
    response_data = fields.Text(string='Response Data (JSON)')
    error_message = fields.Text(string='Error Message')
    duration_seconds = fields.Integer(string='Duration (s)')
    create_date = fields.Datetime(string='Created', default=fields.Datetime.now)

    def sync_to_website(self, context):
        data = {
            'id': context.name,
            'partner_name': context.partner_name,
            'partner_email': context.partner_email,
            'partner_phone': context.partner_phone,
            'lifecycle_state': context.lifecycle_state,
            'score': context.lifecycle_score,
            'last_activity': str(context.last_activity or ''),
            'ai_insights': context.ai_insights,
            'ai_recommendation': context.ai_recommendation,
        }
        self.write({
            'status': 'completed',
            'data_payload': str(data),
            'duration_seconds': 1,
        })
        return data

    def sync_chatbot_state(self, context):
        state = {
            'context_id': context.id,
            'lifecycle': context.lifecycle_state,
            'name': context.partner_name or context.name,
            'email': context.partner_email,
            'phone': context.partner_phone,
            'ai_score': context.ai_lead_score,
            'recent_interactions': context.total_interactions,
        }
        return state

    def sync_persistent_context(self, context):
        try:
            import json
            payload = {
                'context_id': context.id,
                'partner_id': context.partner_id.id if context.partner_id else None,
                'name': context.partner_name,
                'email': context.partner_email,
                'phone': context.partner_phone,
                'lifecycle': context.lifecycle_state,
                'score': context.ai_lead_score,
                'insights': context.ai_insights,
                'events': [{
                    'type': e.event_type,
                    'timestamp': str(e.timestamp),
                    'summary': e.summary,
                } for e in context.context_timeline_ids[:20]],
                'timestamp': str(fields.Datetime.now()),
            }
            self.write({
                'status': 'completed',
                'data_payload': json.dumps(payload),
                'duration_seconds': 1,
            })
            return payload
        except Exception as e:
            self.write({'status': 'failed', 'error_message': str(e)})
            return None


class McpSyncConfig(models.Model):
    _name = 'jil.mcp.sync.config'
    _description = 'Context Sync Configuration'

    name = fields.Char(string='Config Name', required=True)
    active = fields.Boolean(string='Active', default=True)
    source_system = fields.Selection([
        ('odoo', 'Odoo CRM'),
        ('website', 'Website'),
        ('chatbot', 'Chatbot'),
        ('supabase', 'Supabase'),
        ('external', 'External System'),
    ], string='Source System', required=True)
    target_system = fields.Selection([
        ('odoo', 'Odoo CRM'),
        ('supabase', 'Supabase'),
        ('external', 'External System'),
    ], string='Target System', required=True)
    sync_direction = fields.Selection([
        ('push', 'Push Only'),
        ('pull', 'Pull Only'),
        ('bidirectional', 'Bi-Directional'),
    ], string='Direction', default='bidirectional')

    model_ids = fields.Many2many('ir.model', string='Models to Sync')
    field_ids = fields.Many2many('ir.model.fields', string='Fields to Sync')
    cron_interval = fields.Integer(string='Cron Interval (min)', default=60)
    conflict_resolution = fields.Selection([
        ('source_wins', 'Source Wins'),
        ('target_wins', 'Target Wins'),
        ('latest_wins', 'Latest Wins'),
        ('manual', 'Manual Review'),
    ], string='Conflict Resolution', default='latest_wins')
    last_sync = fields.Datetime(string='Last Sync')
    sync_status = fields.Selection([
        ('idle', 'Idle'),
        ('running', 'Running'),
        ('error', 'Error'),
    ], string='Status', default='idle')
