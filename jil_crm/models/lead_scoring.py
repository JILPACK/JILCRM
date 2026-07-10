import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class LeadScoringRule(models.Model):
    _name = 'jil.lead.scoring.rule'
    _description = 'Lead Scoring Rule'
    _order = 'sequence, id'

    name = fields.Char(string='Rule Name', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)
    score_value = fields.Integer(string='Score Value', required=True, default=5)
    apply_to = fields.Selection([
        ('lead', 'Leads Only'),
        ('opportunity', 'Opportunities Only'),
        ('both', 'All'),
    ], string='Apply To', default='both')

    rule_type = fields.Selection([
        ('field_value', 'Field Value Match'),
        ('email_domain', 'Email Domain'),
        ('tag', 'Has Tag'),
        ('revenue_range', 'Revenue Range'),
        ('country', 'Country Match'),
        ('communication', 'Communication Count'),
    ], string='Rule Type', required=True, default='field_value')

    field_name = fields.Char(string='Field Name')
    field_value = fields.Char(string='Field Value')
    operator = fields.Selection([
        ('=', 'Equals'), ('!=', 'Not Equal'),
        ('>', 'Greater Than'), ('<', 'Less Than'),
        ('>=', 'Greater or Equal'), ('<=', 'Less or Equal'),
        ('like', 'Contains'), ('in', 'In'),
    ], string='Operator', default='=')
    email_domain = fields.Char(string='Email Domain')
    tag_id = fields.Many2one('crm.tag', string='Tag')
    min_revenue = fields.Monetary(string='Min Revenue', currency_field='currency_id')
    max_revenue = fields.Monetary(string='Max Revenue', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Currency',
                                   default=lambda self: self.env.company.currency_id)
    country_id = fields.Many2one('res.country', string='Country')
    min_communications = fields.Integer(string='Min Communications', default=0)
    max_communications = fields.Integer(string='Max Communications', default=0)

    def evaluate(self, lead):
        self.ensure_one()
        try:
            if self.rule_type == 'field_value':
                val = getattr(lead, self.field_name, None)
                if self.operator == '=' and val == self.field_value:
                    return self.score_value
                elif self.operator == '!=' and val != self.field_value:
                    return self.score_value
                elif self.operator == '>' and val and float(val) > float(self.field_value):
                    return self.score_value
                elif self.operator == '<' and val and float(val) < float(self.field_value):
                    return self.score_value
            elif self.rule_type == 'email_domain':
                if lead.email_from and self.email_domain in lead.email_from:
                    return self.score_value
            elif self.rule_type == 'tag':
                if self.tag_id and self.tag_id in lead.tag_ids:
                    return self.score_value
            elif self.rule_type == 'revenue_range':
                rev = lead.expected_revenue or 0
                min_v = self.min_revenue or 0
                max_v = self.max_revenue or float('inf')
                if min_v <= rev <= max_v:
                    return self.score_value
            elif self.rule_type == 'country':
                if lead.partner_id and lead.partner_id.country_id == self.country_id:
                    return self.score_value
            elif self.rule_type == 'communication':
                count = lead.communication_count
                if self.min_communications <= count <= (self.max_communications or 999):
                    return self.score_value
        except Exception as e:
            _logger.warning("Scoring rule %s evaluation error: %s", self.name, e, exc_info=True)
        return 0
