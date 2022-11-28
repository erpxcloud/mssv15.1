from odoo import models, fields, api

import logging
log = logging.getLogger(__name__)

class Account(models.Model):
    _inherit = "account.account"
    
    display_name_computed = fields.Char(compute='_compute_display_name_computed', store=True)
    
    @api.depends('name')
    def _compute_display_name_computed(self):
        for record in self:
            record.display_name_computed = record.display_name if record.display_name else record.name