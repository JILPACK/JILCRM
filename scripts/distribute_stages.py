"""
Distribute opportunities across pipeline stages.
Run: python odoo-bin shell -c odoo.conf -d odoo_jil_crm < scripts/distribute_stages.py
"""
import logging
import random

_logger = logging.getLogger(__name__)


def run(env):
    Stage = env['jil.crm.stage']
    Lead = env['jil.crm.lead']

    stages = Stage.search([], order='sequence')
    _logger.info("Stages: %s", [(s.id, s.name) for s in stages])

    opportunities = Lead.search([('type', '=', 'opportunity')], order='id')
    total = len(opportunities)
    _logger.info("Total opportunities: %d, stages: %d", total, len(stages))

    rnd = random.Random(42)
    for i, opp in enumerate(opportunities):
        stage = stages[i % len(stages)]
        prob = stage.probability or 0
        if stage.is_won:
            prob = 100
        if stage.is_lost:
            prob = 0
        opp.write({'stage_id': stage.id, 'probability': prob})

    env.cr.commit()
    _logger.info("Distributed %d opportunities across %d stages", total, len(stages))


if __name__ == '__main__':
    run(env)
