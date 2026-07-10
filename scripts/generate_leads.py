"""
Generate CRM leads from existing Customers/Suppliers.
Run: python odoo-bin shell -c odoo.conf -d odoo_jil_crm < scripts/generate_leads.py
"""
import logging

_logger = logging.getLogger(__name__)


def generate_leads(env, partner_type='customer', max_count=None):
    Partner = env['res.partner']
    Lead = env['jil.crm.lead']
    Stage = env['jil.crm.stage']

    default_stage = Stage.search([], order='sequence', limit=1)
    default_team = env['crm.team'].search([], limit=1)

    domain = [('customer_rank', '>', 0)] if partner_type == 'customer' else [('supplier_rank', '>', 0)]

    partners = Partner.search(domain, limit=max_count or False)

    created = 0
    skipped = 0

    for partner in partners:
        existing = Lead.search([('partner_id', '=', partner.id)], limit=1)
        if existing:
            skipped += 1
            continue

        lead_name = partner.name or partner.commercial_company_name or f"Lead - {partner.id}"
        lead_vals = {
            'name': lead_name,
            'partner_id': partner.id,
            'partner_name': partner.name,
            'email_from': partner.email or False,
            'phone': partner.phone or False,
            'mobile': partner.mobile or False,
            'type': 'lead',
            'active': True,
            'capture_source': 'api',
            'score': 10,
            'company_id': env.company.id,
        }
        if default_stage:
            lead_vals['stage_id'] = default_stage.id
        if default_team:
            lead_vals['team_id'] = default_team.id

        try:
            Lead.create(lead_vals)
            created += 1
        except Exception as e:
            _logger.warning("Failed to create lead for partner %s (%s): %s", partner.id, partner.name, e)
            skipped += 1

        if created % 100 == 0 and created > 0:
            _logger.info("Created %d leads...", created)

    return created, skipped


def run(env):
    _logger.info("Generating Customer Leads...")
    c_created, c_skipped = generate_leads(env, 'customer')
    _logger.info("Customers: %d created, %d skipped", c_created, c_skipped)

    _logger.info("Generating Supplier Leads...")
    s_created, s_skipped = generate_leads(env, 'supplier')
    _logger.info("Suppliers: %d created, %d skipped", s_created, s_skipped)

    total = c_created + s_created
    env.cr.commit()
    _logger.info("Done! Total leads created: %d", total)


if __name__ == '__main__':
    run(env)
