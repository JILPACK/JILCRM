from odoo import api, fields, models


class BpmnProcess(models.Model):
    _name = 'jil.bpmn.process'
    _description = 'BPMN Process'
    _order = 'sequence, name'

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    description = fields.Html()
    bpmn_source = fields.Text(string='BPMN Source')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('validated', 'Validated'),
    ], default='draft')
    pool_ids = fields.One2many('jil.bpmn.pool', 'process_id', string='Pools & Lanes')
    element_ids = fields.One2many('jil.bpmn.element', 'process_id', string='Elements')
    flow_ids = fields.One2many('jil.bpmn.flow', 'process_id', string='Flows')
    note_ids = fields.One2many('jil.bpmn.note', 'process_id', string='Notes')
    pool_count = fields.Integer(compute='_compute_counts')
    element_count = fields.Integer(compute='_compute_counts')
    flow_count = fields.Integer(compute='_compute_counts')

    @api.depends('pool_ids', 'element_ids', 'flow_ids')
    def _compute_counts(self):
        for rec in self:
            rec.pool_count = len(rec.pool_ids)
            rec.element_count = len(rec.element_ids)
            rec.flow_count = len(rec.flow_ids)


class BpmnPool(models.Model):
    _name = 'jil.bpmn.pool'
    _description = 'BPMN Pool / Lane'
    _order = 'process_id, sequence, name'

    process_id = fields.Many2one('jil.bpmn.process', required=True, ondelete='cascade')
    name = fields.Char(required=True)
    color = fields.Char(string='Color')
    icon = fields.Char(string='Icon')
    sequence = fields.Integer(default=10)
    element_ids = fields.One2many('jil.bpmn.element', 'pool_id', string='Elements')


class BpmnElement(models.Model):
    _name = 'jil.bpmn.element'
    _description = 'BPMN Element'
    _order = 'process_id, pool_id, sequence, name'

    process_id = fields.Many2one('jil.bpmn.process', required=True, ondelete='cascade')
    pool_id = fields.Many2one('jil.bpmn.pool', string='Pool/Lane', ondelete='cascade')
    name = fields.Char(required=True)
    element_type = fields.Selection([
        ('event', 'Event'),
        ('activity', 'Activity'),
        ('gateway', 'Gateway'),
        ('data-object', 'Data Object'),
    ], required=True, default='activity')
    icon = fields.Char(string='Icon')
    label = fields.Text(string='Label')
    sequence = fields.Integer(default=10)


class BpmnFlow(models.Model):
    _name = 'jil.bpmn.flow'
    _description = 'BPMN Flow'
    _order = 'process_id, sequence'

    process_id = fields.Many2one('jil.bpmn.process', required=True, ondelete='cascade')
    from_element_id = fields.Many2one('jil.bpmn.element', string='From Element', required=True)
    to_element_id = fields.Many2one('jil.bpmn.element', string='To Element')
    flow_type = fields.Selection([
        ('sequential', 'Sequential (same pool)'),
        ('message', 'Message (inter-pool)'),
    ], default='sequential')
    label = fields.Char(string='Label')
    sequence = fields.Integer(default=10)


class BpmnNote(models.Model):
    _name = 'jil.bpmn.note'
    _description = 'BPMN Note'
    _order = 'process_id, sequence'

    process_id = fields.Many2one('jil.bpmn.process', required=True, ondelete='cascade')
    name = fields.Char(string='Target')
    content = fields.Text(string='Note Content')
    sequence = fields.Integer(default=10)
