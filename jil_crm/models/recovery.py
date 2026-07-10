from odoo import api, fields, models


class JilRecovery(models.Model):
    _name = 'jil.recovery'
    _description = 'Recovery / Recouvrement'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Recovery Number', required=True, default='NEW', tracking=True)
    invoice_id = fields.Many2one('account.move', string='Invoice')
    invoice_number = fields.Char(string='Invoice Number')
    client_id = fields.Many2one('res.partner', string='Client', required=True, tracking=True,
                                domain="[('is_company', '=', True)]")
    amount = fields.Monetary(string='Amount', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    status = fields.Selection([
        ('en_attente', 'En Attente'), ('relance_email', 'Relance Email'),
        ('relance_telephone', 'Relance Téléphone'), ('accord', 'Accord'),
        ('contentieux', 'Contentieux'), ('resolu', 'Résolu'),
    ], string='Status', default='en_attente', tracking=True)
    contact_type = fields.Selection([
        ('email', 'Email'), ('telephone', 'Téléphone'),
    ], string='Contact Type', default='email')
    contact_date = fields.Date(string='Contact Date')
    email_sent = fields.Boolean(string='Email Sent')
    phone_called = fields.Boolean(string='Phone Called')
    agreement_date = fields.Date(string='Agreement Date')
    notes = fields.Text(string='Notes')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    user_id = fields.Many2one('res.users', string='Assigned to', tracking=True, default=lambda self: self.env.user)

    @api.model
    def create(self, vals):
        if vals.get('name', 'NEW') == 'NEW':
            vals['name'] = self.env['ir.sequence'].next_by_code('jil.recovery') or 'RECV-0001'
        return super().create(vals)
