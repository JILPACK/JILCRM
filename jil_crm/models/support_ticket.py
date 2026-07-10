from odoo import api, fields, models


class JilSupportTicket(models.Model):
    _name = 'jil.support.ticket'
    _description = 'Support Ticket / SAV'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'priority desc, create_date desc'

    name = fields.Char(string='Ticket Number', required=True, default='NEW', tracking=True)
    client_id = fields.Many2one('res.partner', string='Client', domain="[('is_company', '=', True)]")
    subject = fields.Char(string='Subject', required=True, tracking=True)
    description = fields.Text(string='Description', required=True)
    priority = fields.Selection([
        ('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('urgent', 'Urgent'),
    ], string='Priority', default='medium', tracking=True)
    status = fields.Selection([
        ('ouvert', 'Ouvert'), ('en_cours', 'En Cours'),
        ('attente', 'En Attente'), ('resolu', 'Résolu'), ('ferme', 'Fermé'),
    ], string='Status', default='ouvert', tracking=True)
    assigned_to = fields.Many2one('res.users', string='Assigned to', tracking=True)
    notes = fields.Text(string='Notes')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    @api.model
    def create(self, vals):
        if vals.get('name', 'NEW') == 'NEW':
            vals['name'] = self.env['ir.sequence'].next_by_code('jil.support.ticket') or 'TKT-0001'
        return super().create(vals)
