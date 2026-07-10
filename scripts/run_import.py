"""Run JIL CRM data import via Odoo shell."""
import logging
logging.basicConfig(level=logging.INFO)

from scripts.import_data import run
run(env)
