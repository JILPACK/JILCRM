from odoo import api, fields, models


class JilTransport(models.Model):
    _name = 'jil.transport'
    _description = 'Transport / Logistics'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Transport Number', required=True, default='NEW', tracking=True)
    order_id = fields.Many2one('sale.order', string='Order')
    client_id = fields.Many2one('res.partner', string='Client', tracking=True,
                                domain="[('is_company', '=', True)]")
    mode = fields.Selection([
        ('routier', 'Routier'), ('maritime', 'Maritime'),
        ('aerien', 'Aérien'), ('ferroviaire', 'Ferroviaire'),
    ], string='Mode', default='routier', tracking=True)
    incoterm = fields.Selection([
        ('EXW', 'EXW'), ('FCA', 'FCA'), ('CPT', 'CPT'), ('CIP', 'CIP'),
        ('DAP', 'DAP'), ('DPU', 'DPU'), ('DDP', 'DDP'),
        ('FOB', 'FOB'), ('CFR', 'CFR'), ('CIF', 'CIF'),
    ], string='Incoterm', default='EXW')
    carrier = fields.Char(string='Carrier')
    bl_number = fields.Char(string='BL / Connaissement')
    status = fields.Selection([
        ('planifie', 'Planifié'), ('en_cours', 'En Cours'),
        ('termine', 'Terminé'), ('annule', 'Annulé'),
    ], string='Status', default='planifie', tracking=True)
    departure_city = fields.Char(string='Departure City')
    departure_date = fields.Date(string='Departure Date')
    arrival_city = fields.Char(string='Arrival City')
    arrival_date = fields.Date(string='Arrival Date')
    eta = fields.Date(string='ETA')
    origin = fields.Char(string='Origin')
    destination = fields.Char(string='Destination')
    documents = fields.Text(string='Documents')
    notes = fields.Text(string='Notes')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    user_id = fields.Many2one('res.users', string='Responsible', tracking=True, default=lambda self: self.env.user)

    @api.model
    def create(self, vals):
        if vals.get('name', 'NEW') == 'NEW':
            vals['name'] = self.env['ir.sequence'].next_by_code('jil.transport') or 'TRP-0001'
        return super().create(vals)
