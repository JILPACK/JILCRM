from odoo import api, fields, models


class McpIngestion(models.Model):
    _name = 'jil.mcp.ingestion'
    _description = 'Context Ingestion Log'
    _order = 'create_date desc'

    name = fields.Char(string='Ingestion ID', required=True, default='NEW')
    source = fields.Selection([
        ('lead_submission', 'Lead Submission'),
        ('chatbot_interaction', 'Chatbot Interaction'),
        ('booking_event', 'Booking Event'),
        ('deal_update', 'Deal Update'),
        ('project_update', 'Project Update'),
        ('website_activity', 'Website Activity'),
        ('email_event', 'Email Event'),
    ], string='Source', required=True)
    context_id = fields.Many2one('jil.mcp.context', string='Context')
    partner_id = fields.Many2one('res.partner', string='Client')
    status = fields.Selection([
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ], string='Status', default='pending')

    raw_data = fields.Text(string='Raw Data')
    transformed_data = fields.Text(string='Transformed Data')
    error_message = fields.Text(string='Error Message')
    create_date = fields.Datetime(string='Created', default=fields.Datetime.now)

    def ingest_lead_submission(self, lead):
        partner = lead.partner_id
        if not partner:
            partner = self._resolve_partner_by_email(lead.email_from)

        if not partner:
            partner = self.env['res.partner'].create({
                'name': lead.partner_name or lead.email_from or 'Unknown',
                'email': lead.email_from,
                'phone': lead.phone,
                'mobile': lead.mobile,
            })

        context = self._get_or_create_context(partner)
        context.write({
            'lead_ids': [(4, lead.id)],
            'lead_id': lead.id,
            'lifecycle_state': 'lead',
            'last_activity': fields.Datetime.now(),
            'total_interactions': context.total_interactions + 1,
            'sync_status': 'pending',
        })
        lead.write({'context_id': context.id})

        self._log_event(context, 'lead_created',
                        f'Lead created from {lead.capture_source or "unknown source"}: {lead.name}',
                        source=lead.capture_source)
        return context

    def ingest_chatbot_interaction(self, session):
        partner = session.partner_id
        if not partner and session.visitor_id:
            partner = self._resolve_partner_by_visitor(session.visitor_id)

        if partner:
            context = self._get_or_create_context(partner)
            context.write({
                'chatbot_session_ids': [(4, session.id)],
                'last_activity': fields.Datetime.now(),
                'total_interactions': context.total_interactions + 1,
                'sync_status': 'pending',
            })
            session.context_id = context.id
            if session.lead_captured:
                context.lifecycle_state = 'lead'
            self._log_event(context, 'chat_session',
                            f'Chatbot session completed: {session.message_count} messages',
                            source='chatbot')

    def ingest_booking_event(self, booking):
        partner = booking.partner_id
        if not partner and booking.partner_email:
            partner = self._resolve_partner_by_email(booking.partner_email)

        if partner:
            context = self._get_or_create_context(partner)
            context.write({
                'booking_ids': [(4, booking.id)],
                'last_activity': fields.Datetime.now(),
                'total_interactions': context.total_interactions + 1,
            })
            booking.context_id = context.id
            event_type = 'booking_created'
            if booking.status == 'confirmed':
                event_type = 'booking_confirmed'
            elif booking.status == 'completed':
                event_type = 'booking_completed'
            self._log_event(context, event_type,
                            f'Booking {booking.name}: {booking.booking_type}',
                            source='booking')

    def ingest_deal_update(self, deal):
        partner = deal.partner_id
        lead = deal.lead_id
        if partner:
            context = self._get_or_create_context(partner)
            context.deal_ids = [(4, deal.id)]
            if deal.status == 'won':
                context.lifecycle_state = 'customer'
            self._log_event(context, f'deal_{deal.status}',
                            f'Deal {deal.name}: {deal.status}', source='deal')

    def _resolve_partner_by_email(self, email):
        if not email:
            return False
        partner = self.env['res.partner'].search([('email', '=', email)], limit=1)
        return partner.id if partner else False

    def _resolve_partner_by_visitor(self, visitor_id):
        return False

    def _get_or_create_context(self, partner):
        context = self.env['jil.mcp.context'].search([
            ('partner_id', '=', partner.id if isinstance(partner, int) else partner.id),
        ], limit=1)
        if not context:
            context = self.env['jil.mcp.context'].create({
                'partner_id': partner.id if isinstance(partner, int) else partner.id,
                'partner_name': partner.name,
                'partner_email': partner.email,
                'partner_phone': partner.phone,
                'lifecycle_state': 'visitor',
                'sync_status': 'pending',
            })
        return context

    def _log_event(self, context, event_type, summary, source=None):
        self.env['jil.mcp.context.event'].create({
            'context_id': context.id,
            'event_type': event_type,
            'summary': summary,
            'source': source or self.source,
        })


class McpIngestionRule(models.Model):
    _name = 'jil.mcp.ingestion.rule'
    _description = 'Context Ingestion Rule'

    name = fields.Char(string='Rule Name', required=True)
    active = fields.Boolean(string='Active', default=True)
    source = fields.Selection([
        ('lead_form', 'Lead Form Submission'),
        ('chatbot', 'Chatbot Interaction'),
        ('booking', 'Booking Event'),
        ('deal_update', 'Deal / Project Update'),
        ('website', 'Website Activity'),
        ('email', 'Email Event'),
        ('api', 'External API'),
    ], string='Source', required=True)
    model = fields.Char(string='Target Model')
    field_mapping = fields.Text(string='Field Mapping (JSON)')
    create_context = fields.Boolean(string='Auto-Create Context', default=True)
    update_existing = fields.Boolean(string='Update Existing', default=True)
    match_by = fields.Selection([
        ('email', 'Email'),
        ('phone', 'Phone'),
        ('partner', 'Partner ID'),
    ], string='Match By', default='email')

    last_ingestion = fields.Datetime(string='Last Ingestion')
    ingestion_count = fields.Integer(string='Ingestion Count', default=0)
