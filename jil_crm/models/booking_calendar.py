from odoo import api, fields, models, _


class ConsultationBooking(models.Model):
    _name = 'jil.consultation.booking'
    _description = 'Consultation Booking'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'booking_date desc, booking_time desc'

    name = fields.Char(string='Booking Reference', required=True, default='NEW', tracking=True)
    lead_id = fields.Many2one('jil.crm.lead', string='Lead', tracking=True)
    partner_id = fields.Many2one('res.partner', string='Customer', tracking=True)
    partner_name = fields.Char(string='Customer Name', tracking=True)
    partner_email = fields.Char(string='Email', tracking=True)
    partner_phone = fields.Char(string='Phone', tracking=True)

    booking_date = fields.Date(string='Booking Date', required=True, tracking=True)
    booking_time = fields.Float(string='Time', required=True, tracking=True)
    duration = fields.Float(string='Duration (hours)', default=1.0)
    end_time = fields.Float(string='End Time', compute='_compute_end_time')

    consultant_id = fields.Many2one('res.users', string='Consultant', tracking=True,
                                    default=lambda self: self.env.user)
    booking_type = fields.Selection([
        ('discovery', 'Discovery Call'),
        ('demo', 'Product Demo'),
        ('proposal', 'Proposal Review'),
        ('follow_up', 'Follow-up'),
        ('support', 'Support'),
        ('site_visit', 'Site Visit'),
    ], string='Type', default='discovery', tracking=True)

    status = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show'),
    ], string='Status', default='draft', tracking=True)

    notes = fields.Text(string='Notes')
    internal_notes = fields.Text(string='Internal Notes')
    source = fields.Selection([
        ('chatbot', 'Chatbot'),
        ('website', 'Website'),
        ('email', 'Email'),
        ('phone', 'Phone'),
        ('manual', 'Manual'),
    ], string='Source', default='manual')

    confirmation_sent = fields.Boolean(string='Confirmation Sent', default=False)
    reminder_sent = fields.Boolean(string='Reminder Sent', default=False)
    reminder_sent_date = fields.Datetime(string='Reminder Sent At')
    calendar_event_id = fields.Many2one('calendar.event', string='Calendar Event')

    satisfaction_score = fields.Selection([
        ('1', '1 - Poor'), ('2', '2 - Fair'),
        ('3', '3 - Good'), ('4', '4 - Very Good'), ('5', '5 - Excellent'),
    ], string='Satisfaction')

    # Context MCP
    context_id = fields.Many2one('jil.mcp.context', string='Unified Context')
    context_sync_status = fields.Selection([
        ('synced', 'Synced'), ('pending', 'Pending'), ('failed', 'Failed'),
    ], string='Context Status', default='pending')

    @api.depends('booking_time', 'duration')
    def _compute_end_time(self):
        for b in self:
            b.end_time = b.booking_time + b.duration

    @api.model
    def create(self, vals):
        if vals.get('name', 'NEW') == 'NEW':
            vals['name'] = self.env['ir.sequence'].next_by_code('jil.consultation.booking') or 'BK-0001'
        return super().create(vals)

    def action_confirm(self):
        for b in self:
            b.write({'status': 'confirmed'})
            if b.partner_email and not b.confirmation_sent:
                template = self.env.ref('jil_crm.email_template_booking_confirmation', raise_if_not_found=False)
                if template:
                    template.send_mail(b.id, force_send=True)
                b.confirmation_sent = True

    def action_complete(self):
        self.write({'status': 'completed'})

    def action_cancel(self):
        self.write({'status': 'cancelled'})

    def action_send_reminder(self):
        for b in self:
            if b.partner_email:
                template = self.env.ref('jil_crm.email_template_booking_reminder', raise_if_not_found=False)
                if template:
                    template.send_mail(b.id, force_send=True)
                b.write({
                    'reminder_sent': True,
                    'reminder_sent_date': fields.Datetime.now(),
                })

    def _create_calendar_event(self):
        self.ensure_one()
        if not self.booking_date or not self.booking_time:
            return
        start_hour = int(self.booking_time)
        start_min = int((self.booking_time % 1) * 60)
        end_hour = int(self.end_time)
        end_min = int((self.end_time % 1) * 60)
        start_dt = fields.Datetime.from_string(f'{self.booking_date} {start_hour:02d}:{start_min:02d}:00')
        end_dt = fields.Datetime.from_string(f'{self.booking_date} {end_hour:02d}:{end_min:02d}:00')
        event = self.env['calendar.event'].create({
            'name': f'Consultation: {self.partner_name or self.name}',
            'start': start_dt,
            'stop': end_dt,
            'partner_ids': [(4, self.partner_id.id)] if self.partner_id else [],
            'user_id': self.consultant_id.id or self.env.user.id,
            'description': self.notes or '',
        })
        self.calendar_event_id = event.id
        return event


class ConsultantAvailability(models.Model):
    _name = 'jil.consultant.availability'
    _description = 'Consultant Availability'
    _order = 'user_id, day_of_week, start_time'

    name = fields.Char(string='Name')
    user_id = fields.Many2one('res.users', string='Consultant', required=True)
    day_of_week = fields.Selection([
        ('0', 'Monday'), ('1', 'Tuesday'), ('2', 'Wednesday'),
        ('3', 'Thursday'), ('4', 'Friday'), ('5', 'Saturday'), ('6', 'Sunday'),
    ], string='Day of Week', required=True)
    start_time = fields.Float(string='Start Time', required=True)
    end_time = fields.Float(string='End Time', required=True)
    slot_duration = fields.Integer(string='Slot Duration (min)', default=60)
    active = fields.Boolean(string='Active', default=True)
    max_bookings_per_slot = fields.Integer(string='Max per Slot', default=1)

    _sql_constraints = [
        ('check_times', 'CHECK(start_time < end_time)',
         'Start time must be before end time'),
    ]

    def get_available_slots(self, date, consultant_id=None):
        domain = [('active', '=', True)]
        if consultant_id:
            domain.append(('user_id', '=', consultant_id))
        availabilities = self.search(domain)
        day_of_week = str(date.weekday())
        slots = []
        for a in availabilities.filtered(lambda x: x.day_of_week == day_of_week):
            current = a.start_time
            while current < a.end_time:
                end_slot = min(current + a.slot_duration / 60, a.end_time)
                booked = self.env['jil.consultation.booking'].search_count([
                    ('consultant_id', '=', a.user_id.id),
                    ('booking_date', '=', date),
                    ('booking_time', '>=', current),
                    ('booking_time', '<', end_slot),
                    ('status', 'not in', ['cancelled']),
                ])
                if booked < a.max_bookings_per_slot:
                    slots.append({
                        'consultant_id': a.user_id.id,
                        'consultant_name': a.user_id.name,
                        'start_time': current,
                        'end_time': end_slot,
                        'date': date,
                    })
                current = end_slot
        return slots


class BookingReminder(models.Model):
    _name = 'jil.booking.reminder'
    _description = 'Booking Reminder'
    _order = 'reminder_hours_before'

    name = fields.Char(string='Reminder Name', required=True)
    active = fields.Boolean(string='Active', default=True)
    reminder_type = fields.Selection([
        ('email', 'Email'),
        ('notification', 'In-App Notification'),
        ('both', 'Email + Notification'),
    ], string='Reminder Type', default='email', required=True)
    reminder_hours_before = fields.Integer(string='Hours Before', default=24, required=True)
    email_template_id = fields.Many2one('mail.template', string='Email Template')
    notification_message = fields.Text(string='Notification Message')

    def action_send_reminders(self):
        now = fields.Datetime.now()
        for reminder in self.search([('active', '=', True)]):
            target_time = fields.Datetime.add(now, hours=reminder.reminder_hours_before)
            target_date = target_time.date()
            target_hour = target_time.hour + target_time.minute / 60
            bookings = self.env['jil.consultation.booking'].search([
                ('status', '=', 'confirmed'),
                ('reminder_sent', '=', False),
                ('booking_date', '=', target_date),
                ('booking_time', '<=', target_hour),
                ('booking_time', '>', target_hour - 0.5),
            ])
            for booking in bookings:
                if reminder.reminder_type in ('email', 'both') and reminder.email_template_id:
                    reminder.email_template_id.send_mail(booking.id, force_send=True)
                if reminder.reminder_type in ('notification', 'both') and booking.user_id:
                    booking.user_id.notify_success(
                        message=reminder.notification_message or f'Reminder: Consultation with {booking.partner_name}'
                    )
                booking.write({
                    'reminder_sent': True,
                    'reminder_sent_date': now,
                })
