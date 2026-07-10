import logging
import json
import requests
from datetime import datetime, timedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.addons.base.models.ir_cron import ir_cron

_logger = logging.getLogger(__name__)

SAGE_MODELS = [
    ('crm_lead', 'Leads'),
    ('partner', 'Customers / Suppliers'),
    ('product', 'Products'),
    ('invoice', 'Invoices'),
    ('account', 'Chart of Accounts'),
    ('sale_order', 'Sales Orders'),
    ('purchase_order', 'Purchase Orders'),
]


class SageConnector(models.Model):
    _name = 'sage.connector'
    _description = 'Sage 100 Connector Configuration'
    _order = 'sequence, id'

    name = fields.Char(string='Name', required=True)
    active = fields.Boolean(string='Active', default=True)
    sequence = fields.Integer(string='Sequence', default=10)
    company_id = fields.Many2one('res.company', string='Company',
                                  default=lambda self: self.env.company)

    sage_version = fields.Selection([
        ('100', 'Sage 100'),
        ('200', 'Sage 200'),
        ('50', 'Sage 50'),
        ('intacct', 'Sage Intacct'),
        ('cloud', 'Sage Business Cloud'),
    ], string='Sage Version', required=True, default='100')

    base_url = fields.Char(string='Base URL', required=True,
                           help='Sage 100 Web Services URL (e.g. http://sageserver:8080/sage100/api)')
    auth_type = fields.Selection([
        ('basic', 'Basic Auth'),
        ('oauth2', 'OAuth2'),
        ('api_key', 'API Key'),
        ('windows', 'Windows Auth (NTLM)'),
    ], string='Auth Type', default='basic', required=True)

    username = fields.Char(string='Username')
    password = fields.Char(string='Password')
    api_key = fields.Char(string='API Key')
    client_id = fields.Char(string='Client ID')
    client_secret = fields.Char(string='Client Secret')
    token_url = fields.Char(string='Token URL')
    access_token = fields.Text(string='Access Token')
    token_expiry = fields.Datetime(string='Token Expiry')

    sync_direction = fields.Selection([
        ('pull', 'Sage -> Odoo (Pull)'),
        ('push', 'Odoo -> Sage (Push)'),
        ('bidirectional', 'Bi-Directional'),
    ], string='Sync Direction', default='pull', required=True)

    auto_sync = fields.Boolean(string='Auto Sync', default=True)
    sync_interval = fields.Integer(string='Sync Interval (minutes)', default=60)
    sync_models = fields.Many2many('sage.connector.model', string='Models to Sync')

    last_sync = fields.Datetime(string='Last Sync')
    last_sync_status = fields.Selection([
        ('success', 'Success'),
        ('partial', 'Partial'),
        ('failed', 'Failed'),
    ], string='Last Sync Status')
    last_sync_message = fields.Text(string='Last Sync Message')
    sync_count = fields.Integer(string='Sync Count', default=0)
    error_count = fields.Integer(string='Error Count', default=0)
    connection_status = fields.Selection([
        ('untested', 'Untested'),
        ('ok', 'Connected'),
        ('error', 'Connection Error'),
    ], string='Connection Status', default='untested')

    sync_log_ids = fields.One2many('sage.connector.sync', 'connector_id', string='Sync Logs')
    mapping_ids = fields.One2many('sage.connector.mapping', 'connector_id', string='Field Mappings')
    retry_ids = fields.One2many('sage.connector.retry', 'connector_id', string='Retry Queue')
    retry_count = fields.Integer(string='Pending Retries', compute='_compute_retry_count')

    @api.depends('retry_ids')
    def _compute_retry_count(self):
        for r in self:
            r.retry_count = len(r.retry_ids)

    def _get_headers(self):
        self.ensure_one()
        headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
        if self.auth_type == 'api_key':
            headers['X-API-Key'] = self.api_key or ''
        elif self.auth_type == 'oauth2':
            if self.token_expiry and self.token_expiry > datetime.now():
                headers['Authorization'] = f'Bearer {self.access_token}'
            else:
                self._refresh_token()
                headers['Authorization'] = f'Bearer {self.access_token}'
        elif self.auth_type == 'basic':
            import base64
            token = base64.b64encode(f'{self.username}:{self.password}'.encode()).decode()
            headers['Authorization'] = f'Basic {token}'
        return headers

    def _refresh_token(self):
        if not self.token_url or not self.client_id or not self.client_secret:
            raise UserError(_('OAuth2 requires Token URL, Client ID, and Client Secret'))
        try:
            resp = requests.post(self.token_url, json={
                'grant_type': 'client_credentials',
                'client_id': self.client_id,
                'client_secret': self.client_secret,
            }, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            self.write({
                'access_token': data.get('access_token'),
                'token_expiry': datetime.now() + timedelta(seconds=data.get('expires_in', 3600)),
            })
        except Exception as e:
            raise UserError(_('Token refresh failed: %s') % str(e))

    def action_test_connection(self):
        self.ensure_one()
        try:
            headers = self._get_headers()
            resp = requests.get(f'{self.base_url.rstrip("/")}/ping', headers=headers, timeout=15)
            resp.raise_for_status()
            self.connection_status = 'ok'
            return {'type': 'ir.actions.client', 'tag': 'display_notification',
                    'params': {'title': _('Connection OK'), 'message': _('Sage 100 responded successfully'),
                               'sticky': False, 'type': 'success'}}
        except Exception as e:
            self.connection_status = 'error'
            raise UserError(_('Connection failed: %s') % str(e))

    def action_authenticate(self):
        if self.auth_type == 'oauth2':
            self._refresh_token()
        self.connection_status = 'ok'
        return {'type': 'ir.actions.client', 'tag': 'display_notification',
                'params': {'title': _('Authenticated'), 'message': _('Authentication successful'),
                           'sticky': False, 'type': 'success'}}

    def action_sync_all(self):
        self.ensure_one()
        models_to_sync = self.sync_models or self.env['sage.connector.model'].search([])
        results = {'success': 0, 'failed': 0, 'errors': []}
        for model in models_to_sync:
            try:
                result = self._sync_model(model.code)
                if result.get('status') == 'success':
                    results['success'] += 1
                else:
                    results['failed'] += 1
                    results['errors'].append(f"{model.name}: {result.get('error')}")
            except Exception as e:
                results['failed'] += 1
                results['errors'].append(f"{model.name}: {str(e)}")

        status = 'success' if results['failed'] == 0 else 'partial' if results['success'] > 0 else 'failed'
        self.write({
            'last_sync': fields.Datetime.now(),
            'last_sync_status': status,
            'last_sync_message': json.dumps(results),
            'sync_count': self.sync_count + 1,
        })
        return self._sync_result_notification(results)

    def _sync_model(self, code):
        method_map = {
            'partner': self._sync_partners,
            'product': self._sync_products,
            'invoice': self._sync_invoices,
            'account': self._sync_chart_accounts,
            'crm_lead': self._sync_leads,
            'sale_order': self._sync_sale_orders,
        }
        method = method_map.get(code)
        if not method:
            return {'status': 'failed', 'error': f'Unknown model: {code}'}
        return method()

    def _call(self, endpoint, method='GET', data=None):
        self.ensure_one()
        url = f'{self.base_url.rstrip("/")}/{endpoint.lstrip("/")}'
        headers = self._get_headers()
        for attempt in range(3):
            try:
                resp = requests.request(method, url, headers=headers, json=data, timeout=60)
                if resp.status_code == 401 and self.auth_type == 'oauth2':
                    self._refresh_token()
                    headers = self._get_headers()
                    resp = requests.request(method, url, headers=headers, json=data, timeout=60)
                resp.raise_for_status()
                return resp.json() if resp.content else {}
            except requests.exceptions.RequestException as e:
                if attempt == 2:
                    self._log_retry(endpoint, data, str(e))
                    raise
                _logger.warning("Sage call attempt %d/3 failed: %s", attempt + 1, e)

    def _log_sync(self, model, direction, status, imported=0, failed=0, error=None):
        self.env['sage.connector.sync'].create({
            'connector_id': self.id,
            'model': model,
            'direction': direction,
            'status': status,
            'records_imported': imported,
            'records_failed': failed,
            'error_message': error,
        })

    def _log_retry(self, endpoint, payload, error):
        self.env['sage.connector.retry'].create({
            'connector_id': self.id,
            'model': endpoint,
            'payload': json.dumps(payload) if payload else '',
            'error': str(error),
            'next_attempt': fields.Datetime.now() + timedelta(hours=1),
        })
        self.error_count += 1

    def _sync_partners(self):
        self.ensure_one()
        direction = 'push' if self.sync_direction == 'push' else 'pull'
        try:
            data = self._call('customers')
            imported = 0
            for sage_customer in data.get('value', data if isinstance(data, list) else []):
                partner = self._upsert_partner(sage_customer)
                if partner:
                    imported += 1
                    self._sync_to_context_mcp(partner, 'partner', 'synced')
            self._log_sync('partner', direction, 'success', imported=imported)
            return {'status': 'success', 'imported': imported}
        except Exception as e:
            self._log_sync('partner', direction, 'failed', error=str(e))
            return {'status': 'failed', 'error': str(e)}

    def _upsert_partner(self, sage_data):
        sage_id = str(sage_data.get('id', sage_data.get('CustomerNo', '')))
        if not sage_id:
            return None
        partner = self.env['res.partner'].search([('sage_id', '=', sage_id)], limit=1)
        if not partner:
            partner = self.env['res.partner'].search([
                ('email', '=', sage_data.get('email', sage_data.get('Email', '')))
            ], limit=1)
        vals = {
            'sage_id': sage_id,
            'sage_synced': True,
            'sage_sync_date': fields.Datetime.now(),
        }
        field_map = {
            'name': ('name', 'Name'),
            'email': ('email', 'Email'),
            'phone': ('phone', 'Telephone'),
            'mobile': ('mobile', 'Mobile'),
            'street': ('street', 'Address1'),
            'city': ('city', 'City'),
            'zip': ('zip', 'PostalCode'),
            'country': ('country_id', 'CountryCode'),
            'vat': ('vat', 'VatNumber'),
            'ref': ('ref', 'CustomerNo'),
        }
        for sage_field, odoo_field in field_map.values():
            if isinstance(odoo_field, str) and sage_data.get(odoo_field):
                vals[sage_field] = sage_data[odoo_field]
        if partner:
            partner.write(vals)
        else:
            company_type = 'company' if sage_data.get('IsCompany', True) else 'person'
            vals.update({
                'name': sage_data.get('Name', sage_data.get('name', 'Unknown')),
                'company_type': company_type,
                'customer_rank': 1,
            })
            partner = self.env['res.partner'].create(vals)
        return partner

    def _sync_products(self):
        self.ensure_one()
        try:
            data = self._call('products')
            imported = 0
            for sage_product in data.get('value', data if isinstance(data, list) else []):
                product = self._upsert_product(sage_product)
                if product:
                    imported += 1
            self._log_sync('product', 'pull', 'success', imported=imported)
            return {'status': 'success', 'imported': imported}
        except Exception as e:
            self._log_sync('product', 'pull', 'failed', error=str(e))
            return {'status': 'failed', 'error': str(e)}

    def _upsert_product(self, sage_data):
        sage_id = str(sage_data.get('id', sage_data.get('ItemCode', '')))
        if not sage_id:
            return None
        product = self.env['product.product'].search([('sage_id', '=', sage_id)], limit=1)
        if not product:
            product = self.env['product.product'].search([
                ('default_code', '=', sage_data.get('ItemCode', sage_id))
            ], limit=1)
        vals = {
            'sage_id': sage_id,
            'sage_synced': True,
            'sage_sync_date': fields.Datetime.now(),
            'default_code': sage_data.get('ItemCode', sage_id),
            'name': sage_data.get('Description', sage_data.get('name', sage_id)),
            'type': 'product',
            'list_price': sage_data.get('UnitPrice', sage_data.get('list_price', 0)),
            'standard_price': sage_data.get('Cost', sage_data.get('standard_price', 0)),
            'barcode': sage_data.get('Barcode', ''),
        }
        if sage_data.get('Category'):
            cat = self.env['product.category'].search([('name', '=', sage_data['Category'])], limit=1)
            if cat:
                vals['categ_id'] = cat.id
        if product:
            product.write(vals)
        else:
            product = self.env['product.product'].create(vals)
        return product

    def _sync_invoices(self):
        self.ensure_one()
        try:
            data = self._call('invoices')
            imported = 0
            for sage_inv in data.get('value', data if isinstance(data, list) else []):
                invoice = self._upsert_invoice(sage_inv)
                if invoice:
                    imported += 1
            self._log_sync('invoice', 'pull', 'success', imported=imported)
            return {'status': 'success', 'imported': imported}
        except Exception as e:
            self._log_sync('invoice', 'pull', 'failed', error=str(e))
            return {'status': 'failed', 'error': str(e)}

    def _upsert_invoice(self, sage_data):
        sage_id = str(sage_data.get('id', sage_data.get('InvoiceNo', '')))
        if not sage_id:
            return None
        inv = self.env['account.move'].search([('sage_id', '=', sage_id)], limit=1)
        if inv:
            return inv
        partner_sage_id = str(sage_data.get('CustomerNo', sage_data.get('customer_id', '')))
        partner = self.env['res.partner'].search([('sage_id', '=', partner_sage_id)], limit=1)
        if not partner:
            return None
        inv = self.env['account.move'].create({
            'sage_id': sage_id,
            'sage_synced': True,
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'invoice_date': sage_data.get('Date', sage_data.get('invoice_date', fields.Date.today())),
            'amount_total': sage_data.get('Total', sage_data.get('amount_total', 0)),
            'ref': sage_data.get('InvoiceNo', sage_id),
        })
        return inv

    def _sync_chart_accounts(self):
        self.ensure_one()
        try:
            data = self._call('accounts')
            imported = 0
            for sage_acct in data.get('value', data if isinstance(data, list) else []):
                acct = self._upsert_account(sage_acct)
                if acct:
                    imported += 1
            self._log_sync('account', 'pull', 'success', imported=imported)
            return {'status': 'success', 'imported': imported}
        except Exception as e:
            self._log_sync('account', 'pull', 'failed', error=str(e))
            return {'status': 'failed', 'error': str(e)}

    def _upsert_account(self, sage_data):
        code = str(sage_data.get('code', sage_data.get('AccountNo', '')))
        if not code:
            return None
        acct = self.env['account.account'].search([('sage_id', '=', code)], limit=1)
        if not acct:
            acct = self.env['account.account'].search([('code', '=', code)], limit=1)
        vals = {
            'sage_id': code,
            'sage_synced': True,
            'code': code,
            'name': sage_data.get('name', sage_data.get('Description', code)),
            'reconcile': sage_data.get('Reconcile', True),
        }
        if acct:
            acct.write(vals)
        else:
            acct = self.env['account.account'].create(vals)
        return acct

    def _sync_leads(self):
        self.ensure_one()
        try:
            data = self._call('leads')
            imported = 0
            for sage_lead in data.get('value', data if isinstance(data, list) else []):
                lead = self._upsert_lead(sage_lead)
                if lead:
                    imported += 1
            self._log_sync('crm_lead', 'pull', 'success', imported=imported)
            return {'status': 'success', 'imported': imported}
        except Exception as e:
            self._log_sync('crm_lead', 'pull', 'failed', error=str(e))
            return {'status': 'failed', 'error': str(e)}

    def _upsert_lead(self, sage_data):
        sage_id = str(sage_data.get('id', ''))
        partner_sage_id = str(sage_data.get('CustomerNo', ''))
        partner = self.env['res.partner'].search([('sage_id', '=', partner_sage_id)], limit=1) if partner_sage_id else None
        lead = self.env['jil.crm.lead'].search([('sage_id', '=', sage_id)], limit=1) if sage_id else self.env['jil.crm.lead']
        if lead:
            return lead
        vals = {
            'sage_id': sage_id,
            'name': sage_data.get('Subject', sage_data.get('Description', 'Sage Lead')),
            'partner_id': partner.id if partner else None,
            'expected_revenue': sage_data.get('PotentialValue', 0),
            'description': sage_data.get('Notes', ''),
        }
        if sage_data.get('Stage'):
            stage = self.env['jil.crm.stage'].search([('name', '=', sage_data['Stage'])], limit=1)
            if stage:
                vals['stage_id'] = stage.id
        return self.env['jil.crm.lead'].create(vals)

    def _sync_sale_orders(self):
        self.ensure_one()
        try:
            data = self._call('salesorders')
            imported = 0
            for sage_so in data.get('value', data if isinstance(data, list) else []):
                so = self._upsert_sale_order(sage_so)
                if so:
                    imported += 1
            self._log_sync('sale_order', 'pull', 'success', imported=imported)
            return {'status': 'success', 'imported': imported}
        except Exception as e:
            self._log_sync('sale_order', 'pull', 'failed', error=str(e))
            return {'status': 'failed', 'error': str(e)}

    def _upsert_sale_order(self, sage_data):
        sage_id = str(sage_data.get('id', sage_data.get('SalesOrderNo', '')))
        if not sage_id:
            return None
        so = self.env['sale.order'].search([('sage_id', '=', sage_id)], limit=1)
        if so:
            return so
        partner_sage_id = str(sage_data.get('CustomerNo', ''))
        partner = self.env['res.partner'].search([('sage_id', '=', partner_sage_id)], limit=1)
        if not partner:
            return None
        so = self.env['sale.order'].create({
            'sage_id': sage_id,
            'partner_id': partner.id,
            'date_order': sage_data.get('Date', fields.Datetime.now()),
            'amount_total': sage_data.get('Total', 0),
            'client_order_ref': sage_data.get('Reference', sage_id),
        })
        return so

    def _sync_to_context_mcp(self, record, model_name, action):
        if 'jil.mcp.context' not in self.env:
            return
        partner = record if model_name == 'partner' else getattr(record, 'partner_id', None)
        if not partner:
            return
        context = self.env['jil.mcp.context'].search([('partner_id', '=', partner.id)], limit=1)
        if context:
            context.write({
                'last_sync': fields.Datetime.now(),
                'last_sync_source': f'sage_{self.id}',
                'sync_status': 'synced',
            })
            self.env['jil.mcp.context.event'].create({
                'context_id': context.id,
                'event_type': 'sync_completed',
                'summary': f'{model_name} synced via Sage 100 connector',
                'source': f'sage.{self.name}',
            })

    def action_retry_failed(self):
        retries = self.env['sage.connector.retry'].search([
            ('connector_id', '=', self.id),
            ('retry_count', '<', 5),
            ('next_attempt', '<=', fields.Datetime.now()),
        ])
        count = 0
        for retry in retries:
            try:
                model = retry.model
                if model.startswith('customers'):
                    self._sync_partners()
                elif model.startswith('products'):
                    self._sync_products()
                retry.unlink()
                count += 1
            except Exception as e:
                retry.write({
                    'retry_count': retry.retry_count + 1,
                    'next_attempt': fields.Datetime.now() + timedelta(hours=2 ** retry.retry_count),
                    'last_error': str(e),
                })
        return self._sync_result_notification({'success': count, 'failed': len(retries) - count})

    def action_clear_retries(self):
        self.env['sage.connector.retry'].search([('connector_id', '=', self.id)]).unlink()

    def _sync_result_notification(self, results):
        return {'type': 'ir.actions.client', 'tag': 'display_notification',
                'params': {
                    'title': _('Sync Complete'),
                    'message': _('Success: %(ok)d, Failed: %(ko)d') % {
                        'ok': results.get('success', 0), 'ko': results.get('failed', 0)},
                    'sticky': False, 'type': 'success' if results.get('failed', 0) == 0 else 'warning',
                }}

    @api.model
    def run_scheduled_sync(self):
        connectors = self.search([('active', '=', True), ('auto_sync', '=', True)])
        for connector in connectors:
            try:
                connector.action_sync_all()
            except Exception as e:
                _logger.exception("Scheduled sync failed for connector %s: %s", connector.name, e)


class SageConnectorSync(models.Model):
    _name = 'sage.connector.sync'
    _description = 'Sage Connector Sync Log'
    _order = 'create_date desc'

    connector_id = fields.Many2one('sage.connector', string='Connector', required=True,
                                    ondelete='cascade')
    model = fields.Selection(SAGE_MODELS, string='Model', required=True)
    direction = fields.Selection([
        ('push', 'Push (Odoo -> Sage)'),
        ('pull', 'Pull (Sage -> Odoo)'),
    ], string='Direction', required=True)
    status = fields.Selection([
        ('success', 'Success'),
        ('partial', 'Partial'),
        ('failed', 'Failed'),
    ], string='Status', default='success')
    records_imported = fields.Integer(string='Imported', default=0)
    records_failed = fields.Integer(string='Failed', default=0)
    error_message = fields.Text(string='Error')
    started_at = fields.Datetime(string='Started', default=fields.Datetime.now)
    finished_at = fields.Datetime(string='Finished')
    duration = fields.Float(string='Duration (s)', compute='_compute_duration')

    @api.depends('started_at', 'finished_at')
    def _compute_duration(self):
        for s in self:
            if s.started_at and s.finished_at:
                s.duration = (s.finished_at - s.started_at).total_seconds()
            else:
                s.duration = 0


class SageConnectorModel(models.Model):
    _name = 'sage.connector.model'
    _description = 'Sage Connector Sync Model'
    _order = 'sequence, id'

    name = fields.Char(string='Name', required=True)
    code = fields.Selection(SAGE_MODELS, string='Model Code', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)
    connector_ids = fields.Many2many('sage.connector', string='Connectors')


class SageConnectorMapping(models.Model):
    _name = 'sage.connector.mapping'
    _description = 'Sage Connector Field Mapping'
    _order = 'connector_id, sage_model'

    connector_id = fields.Many2one('sage.connector', string='Connector', required=True,
                                    ondelete='cascade')
    name = fields.Char(string='Name', required=True)
    sage_model = fields.Selection(SAGE_MODELS, string='Sage Model', required=True)
    odoo_model = fields.Char(string='Odoo Model', required=True)
    active = fields.Boolean(string='Active', default=True)
    line_ids = fields.One2many('sage.connector.mapping.line', 'mapping_id', string='Field Mappings')


class SageConnectorMappingLine(models.Model):
    _name = 'sage.connector.mapping.line'
    _description = 'Sage Connector Field Mapping Line'
    _order = 'mapping_id, sequence, id'

    mapping_id = fields.Many2one('sage.connector.mapping', string='Mapping', required=True,
                                  ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=10)
    sage_field = fields.Char(string='Sage Field', required=True)
    odoo_field = fields.Char(string='Odoo Field', required=True)
    transformation = fields.Selection([
        ('direct', 'Direct'),
        ('default', 'Default Value'),
        ('expression', 'Python Expression'),
    ], string='Transformation', default='direct')
    default_value = fields.Char(string='Default Value')
    expression = fields.Text(string='Expression')
    active = fields.Boolean(string='Active', default=True)


class SageConnectorRetry(models.Model):
    _name = 'sage.connector.retry'
    _description = 'Sage Connector Retry Queue'
    _order = 'next_attempt, create_date'

    connector_id = fields.Many2one('sage.connector', string='Connector', required=True,
                                    ondelete='cascade')
    model = fields.Char(string='Model / Endpoint', required=True)
    sage_id = fields.Char(string='Sage Record ID')
    odoo_ref = fields.Reference([('res.partner', 'Partner'), ('product.product', 'Product'),
                                  ('account.move', 'Invoice'), ('sale.order', 'Sale Order'),
                                  ('jil.crm.lead', 'Lead')], string='Odoo Record')
    payload = fields.Text(string='Payload')
    error = fields.Text(string='Error')
    last_error = fields.Text(string='Last Error')
    retry_count = fields.Integer(string='Retry Count', default=0)
    max_retries = fields.Integer(string='Max Retries', default=5)
    last_attempt = fields.Datetime(string='Last Attempt')
    next_attempt = fields.Datetime(string='Next Attempt')

    def action_retry_now(self):
        for r in self:
            r.connector_id.action_retry_failed()


class ResPartner(models.Model):
    _inherit = 'res.partner'

    sage_id = fields.Char(string='Sage 100 ID', index=True, copy=False)
    sage_synced = fields.Boolean(string='Synced to Sage 100', default=False, copy=False)
    sage_sync_date = fields.Datetime(string='Sage Sync Date', copy=False)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    sage_id = fields.Char(string='Sage 100 ID', index=True, copy=False)
    sage_synced = fields.Boolean(string='Synced to Sage 100', default=False, copy=False)
    sage_sync_date = fields.Datetime(string='Sage Sync Date', copy=False)


class AccountAccount(models.Model):
    _inherit = 'account.account'

    sage_id = fields.Char(string='Sage 100 ID', index=True, copy=False)
    sage_synced = fields.Boolean(string='Synced to Sage 100', default=False, copy=False)
    sage_sync_date = fields.Datetime(string='Sage Sync Date', copy=False)


class AccountMove(models.Model):
    _inherit = 'account.move'

    sage_id = fields.Char(string='Sage 100 ID', index=True, copy=False)
    sage_synced = fields.Boolean(string='Synced to Sage 100', default=False, copy=False)
    sage_sync_date = fields.Datetime(string='Sage Sync Date', copy=False)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    sage_id = fields.Char(string='Sage 100 ID', index=True, copy=False)
    sage_synced = fields.Boolean(string='Synced to Sage 100', default=False, copy=False)
    sage_sync_date = fields.Datetime(string='Sage Sync Date', copy=False)


class CrmLead(models.Model):
    _inherit = 'jil.crm.lead'

    sage_id = fields.Char(string='Sage 100 ID', index=True, copy=False)
    sage_synced = fields.Boolean(string='Synced to Sage 100', default=False, copy=False)
    sage_sync_date = fields.Datetime(string='Sage Sync Date', copy=False)
