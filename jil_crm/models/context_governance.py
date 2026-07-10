from odoo import api, fields, models, _


class McpGovernance(models.Model):
    _name = 'jil.mcp.governance'
    _description = 'Context Governance Rule'
    _order = 'sequence, id'

    name = fields.Char(string='Rule Name', required=True)
    active = fields.Boolean(string='Active', default=True)
    sequence = fields.Integer(string='Sequence', default=10)
    rule_type = fields.Selection([
        ('validation', 'Data Validation'),
        ('required_field', 'Required Field'),
        ('format_check', 'Format Check'),
        ('duplicate_check', 'Duplicate Detection'),
        ('integrity', 'Context Integrity'),
        ('audit', 'Audit Policy'),
    ], string='Rule Type', required=True)
    severity = fields.Selection([
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('critical', 'Critical'),
    ], string='Severity', default='warning')
    field_name = fields.Char(string='Field Name')
    validation_regex = fields.Char(string='Validation Regex')
    validation_message = fields.Text(string='Validation Message')
    auto_fix = fields.Boolean(string='Auto-Fix', default=False)
    auto_fix_value = fields.Char(string='Auto-Fix Value')

    def validate_context(self, context):
        results = []
        violations = 0
        missing = []
        for rule in self.search([('active', '=', True)]):
            result = rule._evaluate(context)
            if not result['passed']:
                violations += 1
                if rule.field_name:
                    missing.append(rule.field_name)
            results.append(result)
        context.write({
            'missing_fields': str(missing) if missing else False,
            'data_quality_score': max(0, 100 - (violations * 10)),
            'validation_status': 'error' if violations > 2 else 'warning' if violations > 0 else 'valid',
        })
        return results

    def _evaluate(self, context):
        self.ensure_one()
        result = {'rule': self.name, 'passed': True, 'message': ''}
        try:
            if self.rule_type == 'required_field':
                val = getattr(context, self.field_name, None)
                if not val:
                    result.update({'passed': False, 'message': self.validation_message or f'{self.field_name} is required'})
                    if self.auto_fix and self.auto_fix_value:
                        context.write({self.field_name: self.auto_fix_value})
                        result['message'] += ' (auto-fixed)'
            elif self.rule_type == 'format_check' and self.validation_regex:
                import re
                val = str(getattr(context, self.field_name, '') or '')
                if not re.match(self.validation_regex, val):
                    result.update({'passed': False, 'message': self.validation_message or f'{self.field_name} format invalid'})
            elif self.rule_type == 'duplicate_check':
                if context.partner_email:
                    dupes = self.env['jil.mcp.context'].search([
                        ('partner_email', '=', context.partner_email),
                        ('id', '!=', context.id),
                    ])
                    if dupes:
                        result.update({'passed': False, 'message': f'Duplicate email found in {len(dupes)} other context(s)'})
            elif self.rule_type == 'integrity':
                if context.lifecycle_state in ('customer', 'active_client') and not context.partner_id:
                    result.update({'passed': False, 'message': 'Customer must have linked partner'})
        except Exception as e:
            result.update({'passed': False, 'message': str(e)})
        return result


class McpAuditLog(models.Model):
    _name = 'jil.mcp.audit.log'
    _description = 'Context Audit Log'
    _order = 'create_date desc'

    name = fields.Char(string='Log ID', required=True, default='NEW')
    context_id = fields.Many2one('jil.mcp.context', string='Context')
    partner_id = fields.Many2one('res.partner', string='Client')
    action = fields.Selection([
        ('create', 'Create'),
        ('update', 'Update'),
        ('sync', 'Sync'),
        ('merge', 'Merge'),
        ('validate', 'Validate'),
        ('ai_analyze', 'AI Analysis'),
        ('delete', 'Delete'),
        ('error', 'Error'),
    ], string='Action', required=True)
    field_changed = fields.Char(string='Field Changed')
    old_value = fields.Text(string='Old Value')
    new_value = fields.Text(string='New Value')
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user)
    ip_address = fields.Char(string='IP Address')
    create_date = fields.Datetime(string='Timestamp', default=fields.Datetime.now)
    details = fields.Text(string='Details')

    @api.model
    def create_from_context(self, context, action, field_changed=None, old_val=None, new_val=None):
        return self.create({
            'name': self.env['ir.sequence'].next_by_code('jil.mcp.audit.log') or 'AUD-0001',
            'context_id': context.id,
            'partner_id': context.partner_id.id,
            'action': action,
            'field_changed': field_changed,
            'old_value': old_val,
            'new_value': new_val,
        })


class McpMissingDataHandler(models.Model):
    _name = 'jil.mcp.missing.data'
    _description = 'Missing Data Handler'

    name = fields.Char(string='Handler Name', required=True)
    active = fields.Boolean(string='Active', default=True)
    model = fields.Char(string='Model', default='jil.mcp.context')
    field_name = fields.Char(string='Field Name', required=True)
    fallback_type = fields.Selection([
        ('default_value', 'Default Value'),
        ('compute_from', 'Compute from Other Field'),
        ('ask_user', 'Ask User'),
        ('ignore', 'Ignore'),
    ], string='Fallback Type', required=True, default='ignore')
    default_value = fields.Char(string='Default Value')
    compute_source = fields.Char(string='Compute From Field')
    compute_formula = fields.Text(string='Compute Formula')
    notification_template = fields.Many2one('mail.template', string='Notification Template')
