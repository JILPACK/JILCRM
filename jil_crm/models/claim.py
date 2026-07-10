from odoo import api, fields, models, _


class JilClaim(models.Model):
    _name = 'jil.claim'
    _description = 'Claim / Reclamation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Claim Number', required=True, default='NEW', tracking=True)
    claim_type = fields.Selection([
        ('reclamation', 'Reclamation'),
        ('retour', 'Retour Marchandise'),
    ], string='Type', default='reclamation', tracking=True)
    order_id = fields.Many2one('sale.order', string='Order')
    client_id = fields.Many2one('res.partner', string='Client', required=True, tracking=True,
                                domain="[('is_company', '=', True)]")
    description = fields.Text(string='Description', required=True)
    product_name = fields.Char(string='Product')
    status = fields.Selection([
        ('ouverte', 'Ouverte'), ('en_cours', 'En Cours'),
        ('acceptee', 'Acceptee'), ('refusee', 'Refusee'), ('resolue', 'Resolue'),
    ], string='Status', default='ouverte', tracking=True)
    decision = fields.Text(string='Decision / Resolution')
    decision_date = fields.Date(string='Decision Date')
    notes = fields.Text(string='Notes')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    user_id = fields.Many2one('res.users', string='Assigned to', tracking=True, default=lambda self: self.env.user)

    @api.model
    def create(self, vals):
        if vals.get('name', 'NEW') == 'NEW':
            vals['name'] = self.env['ir.sequence'].next_by_code('jil.claim') or 'REC-0001'
        return super().create(vals)

