import logging
from datetime import datetime

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ChatbotFlow(models.Model):
    _name = 'jil.chatbot.flow'
    _description = 'Chatbot Conversation Flow'
    _order = 'sequence, id'

    name = fields.Char(string='Flow Name', required=True)
    active = fields.Boolean(string='Active', default=True)
    sequence = fields.Integer(string='Sequence', default=10)
    trigger_intent = fields.Many2one('jil.chatbot.intent', string='Trigger Intent')
    trigger_keywords = fields.Text(string='Trigger Keywords')
    description = fields.Text(string='Description')

    flow_type = fields.Selection([
        ('lead_capture', 'Lead Capture'),
        ('qualification', 'Lead Qualification'),
        ('booking', 'Consultation Booking'),
        ('support', 'Support/FAQ'),
        ('nurturing', 'Nurturing'),
        ('sales', 'Sales Assist'),
        ('custom', 'Custom Flow'),
    ], string='Flow Type', default='lead_capture')

    step_ids = fields.One2many('jil.chatbot.flow.step', 'flow_id', string='Flow Steps',
                                copy=True)
    step_count = fields.Integer(string='Step Count', compute='_compute_step_count')
    session_count = fields.Integer(string='Sessions', default=0)
    completion_rate = fields.Float(string='Completion Rate (%)', default=0.0)

    @api.depends('step_ids')
    def _compute_step_count(self):
        for f in self:
            f.step_count = len(f.step_ids)


class ChatbotFlowStep(models.Model):
    _name = 'jil.chatbot.flow.step'
    _description = 'Chatbot Flow Step'
    _order = 'flow_id, sequence, id'

    flow_id = fields.Many2one('jil.chatbot.flow', string='Flow', required=True,
                               ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=10)
    name = fields.Char(string='Step Name', required=True)
    step_type = fields.Selection([
        ('message', 'Send Message'),
        ('question', 'Ask Question'),
        ('condition', 'Condition'),
        ('api_call', 'API Call'),
        ('create_lead', 'Create Lead'),
        ('book_consultation', 'Book Consultation'),
        ('end', 'End Flow'),
    ], string='Step Type', required=True, default='message')

    message_text = fields.Text(string='Message Text')
    message_type = fields.Selection([
        ('text', 'Text'), ('quick_reply', 'Quick Replies'),
        ('carousel', 'Carousel'), ('form', 'Form'),
    ], string='Message Type', default='text')

    question_field = fields.Char(string='Question Field')
    question_label = fields.Char(string='Question Label')
    options_json = fields.Text(string='Options (JSON)')
    validation_regex = fields.Char(string='Validation Regex')
    validation_error = fields.Char(string='Validation Error Message')
    required = fields.Boolean(string='Required', default=True)

    condition_variable = fields.Char(string='Condition Variable')
    condition_operator = fields.Selection([
        ('=', '='), ('!=', '!='), ('in', 'In'), ('contains', 'Contains'),
    ], string='Operator', default='=')
    condition_value = fields.Char(string='Condition Value')
    step_if_true = fields.Many2one('jil.chatbot.flow.step', string='Next Step (True)')
    step_if_false = fields.Many2one('jil.chatbot.flow.step', string='Next Step (False)')

    api_endpoint = fields.Char(string='API Endpoint')
    api_method = fields.Selection([('GET', 'GET'), ('POST', 'POST')], string='Method', default='GET')
    api_body = fields.Text(string='API Body')
    next_step_id = fields.Many2one('jil.chatbot.flow.step', string='Next Step')

    lead_field_map = fields.Text(string='Lead Field Mapping (JSON)')


class ChatbotIntent(models.Model):
    _name = 'jil.chatbot.intent'
    _description = 'Chatbot Intent'
    _order = 'name'

    name = fields.Char(string='Intent Name', required=True)
    active = fields.Boolean(string='Active', default=True)
    description = fields.Text(string='Description')
    confidence_threshold = fields.Float(string='Confidence Threshold', default=0.6)
    training_phrases = fields.Text(string='Training Phrases (one per line)',
                                    help='Example phrases for training')
    response_template = fields.Text(string='Default Response')
    flow_id = fields.Many2one('jil.chatbot.flow', string='Link to Flow')
    category = fields.Selection([
        ('greeting', 'Greeting'), ('lead', 'Lead Related'),
        ('booking', 'Booking'), ('support', 'Support'),
        ('pricing', 'Pricing/Quote'), ('product', 'Product Info'),
        ('status', 'Status Check'), ('farewell', 'Farewell'),
        ('fallback', 'Fallback'),
    ], string='Category', default='greeting')
    match_count = fields.Integer(string='Times Matched', default=0)
    last_matched = fields.Datetime(string='Last Matched')
    use_count = fields.Integer(string='Use Count', default=0)

    def match(self, message):
        self.ensure_one()
        if not self.training_phrases or not self.active:
            return 0.0
        phrases = [p.strip().lower() for p in self.training_phrases.split('\n') if p.strip()]
        msg_lower = message.lower()
        matches = sum(1 for p in phrases if p in msg_lower)
        score = matches / len(phrases) if phrases else 0
        if score >= self.confidence_threshold:
            self.write({
                'match_count': self.match_count + 1,
                'last_matched': fields.Datetime.now(),
            })
        return score


class ChatbotMessage(models.Model):
    _name = 'jil.chatbot.message'
    _description = 'Chatbot Message'
    _order = 'create_date desc'

    session_id = fields.Many2one('jil.chatbot.session', string='Session', required=True,
                                  ondelete='cascade')
    direction = fields.Selection([
        ('incoming', 'Visitor Message'),
        ('outgoing', 'Bot Response'),
    ], string='Direction', required=True)
    message_type = fields.Selection([
        ('text', 'Text'), ('quick_reply', 'Quick Reply'),
        ('form', 'Form'), ('carousel', 'Carousel'),
    ], string='Message Type', default='text')
    content = fields.Text(string='Content', required=True)
    intent_id = fields.Many2one('jil.chatbot.intent', string='Matched Intent')
    confidence = fields.Float(string='Confidence')
    metadata = fields.Text(string='Metadata (JSON)')
    create_date = fields.Datetime(string='Date', default=fields.Datetime.now)

    # Personalization
    personalized = fields.Boolean(string='Personalized', default=False)
    personalization_context = fields.Text(string='Personalization Context')

    # Analytics
    response_time_ms = fields.Integer(string='Response Time (ms)')
    engagement_score = fields.Float(string='Engagement Score', default=0.0)


class ChatbotSession(models.Model):
    _name = 'jil.chatbot.session'
    _description = 'Chatbot Session'
    _order = 'create_date desc'

    name = fields.Char(string='Session ID', required=True)
    visitor_id = fields.Char(string='Visitor ID')
    partner_id = fields.Many2one('res.partner', string='Customer')
    lead_id = fields.Many2one('jil.crm.lead', string='Linked Lead')
    flow_id = fields.Many2one('jil.chatbot.flow', string='Current Flow')
    current_step_id = fields.Many2one('jil.chatbot.flow.step', string='Current Step')

    state = fields.Selection([
        ('active', 'Active'), ('completed', 'Completed'),
        ('abandoned', 'Abandoned'), ('transferred', 'Transferred to Human'),
    ], string='State', default='active')

    source_url = fields.Char(string='Source URL')
    source_page = fields.Char(string='Source Page')
    user_agent = fields.Char(string='User Agent')
    ip_address = fields.Char(string='IP Address')

    message_ids = fields.One2many('jil.chatbot.message', 'session_id', string='Messages')
    message_count = fields.Integer(string='Message Count', compute='_compute_message_count')
    duration_seconds = fields.Integer(string='Duration (s)', compute='_compute_duration')
    start_time = fields.Datetime(string='Start Time', default=fields.Datetime.now)
    end_time = fields.Datetime(string='End Time')

    context_data = fields.Text(string='Session Context (JSON)')
    collected_data = fields.Text(string='Collected Data (JSON)')
    satisfaction_score = fields.Float(string='Satisfaction Score', default=0.0)
    lead_captured = fields.Boolean(string='Lead Captured', default=False)
    booking_made = fields.Boolean(string='Booking Made', default=False)

    context_id = fields.Many2one('jil.mcp.context', string='Unified Context')

    @api.depends('message_ids')
    def _compute_message_count(self):
        for s in self:
            s.message_count = len(s.message_ids)

    @api.depends('start_time', 'end_time')
    def _compute_duration(self):
        for s in self:
            if s.start_time and s.end_time:
                s.duration_seconds = int((s.end_time - s.start_time).total_seconds())
            else:
                s.duration_seconds = 0

    def action_end_session(self):
        self.write({
            'state': 'completed',
            'end_time': fields.Datetime.now(),
        })

    def action_abandon_session(self):
        self.write({
            'state': 'abandoned',
            'end_time': fields.Datetime.now(),
        })


class ChatbotAnalytics(models.Model):
    _name = 'jil.chatbot.analytics'
    _description = 'Chatbot Analytics'
    _order = 'create_date desc'

    name = fields.Char(string='Period', required=True)
    date_from = fields.Date(string='From')
    date_to = fields.Date(string='To')
    total_sessions = fields.Integer(string='Total Sessions')
    completed_sessions = fields.Integer(string='Completed')
    abandoned_sessions = fields.Integer(string='Abandoned')
    total_messages = fields.Integer(string='Total Messages')
    avg_messages_per_session = fields.Float(string='Avg Messages/Session')
    avg_satisfaction = fields.Float(string='Avg Satisfaction')
    lead_capture_rate = fields.Float(string='Lead Capture Rate (%)')
    booking_rate = fields.Float(string='Booking Rate (%)')
    avg_response_time = fields.Float(string='Avg Response Time (ms)')
    engagement_rate = fields.Float(string='Engagement Rate')

    @api.model
    def compute_analytics(self, date_from=None, date_to=None):
        today = datetime.today()
        if not date_from:
            date_from = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if not date_to:
            if today.month == 12:
                date_to = today.replace(year=today.year + 1, month=1, day=1)
            else:
                date_to = today.replace(month=today.month + 1, day=1)
        domain = [('create_date', '>=', fields.Datetime.to_string(date_from)),
                  ('create_date', '<', fields.Datetime.to_string(date_to))]
        sessions = self.env['jil.chatbot.session'].search(domain)
        total = len(sessions)
        completed = len(sessions.filtered(lambda s: s.state == 'completed'))
        abandoned = len(sessions.filtered(lambda s: s.state == 'abandoned'))
        total_msgs = sum(s.message_count for s in sessions)
        avg_msgs = round(total_msgs / total, 2) if total else 0
        satisfactions = [s.satisfaction_score for s in sessions if s.satisfaction_score]
        avg_sat = round(sum(satisfactions) / len(satisfactions), 2) if satisfactions else 0
        lead_captured = len(sessions.filtered(lambda s: s.lead_captured))
        bookings = len(sessions.filtered(lambda s: s.booking_made))
        resp_times = [m.response_time_ms for s in sessions for m in s.message_ids if m.response_time_ms]
        avg_resp = round(sum(resp_times) / len(resp_times), 2) if resp_times else 0
        engaged = len(sessions.filtered(lambda s: s.message_count >= 3))
        engagement = round(engaged / total * 100, 2) if total else 0

        self.create({
            'name': 'Chatbot %s - %s' % (date_from.strftime('%Y-%m-%d'), date_to.strftime('%Y-%m-%d')),
            'date_from': date_from,
            'date_to': date_to,
            'total_sessions': total,
            'completed_sessions': completed,
            'abandoned_sessions': abandoned,
            'total_messages': total_msgs,
            'avg_messages_per_session': avg_msgs,
            'avg_satisfaction': avg_sat,
            'lead_capture_rate': round(lead_captured / total * 100, 2) if total else 0,
            'booking_rate': round(bookings / total * 100, 2) if total else 0,
            'avg_response_time': avg_resp,
            'engagement_rate': engagement,
        })
        _logger.info("Chatbot analytics computed for %s - %s", date_from, date_to)
        return True
