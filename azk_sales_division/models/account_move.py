from odoo import models, fields
import logging

log = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'
    
    division_id = fields.Many2one('azk_sales_division.division', string='Division', help='Division')