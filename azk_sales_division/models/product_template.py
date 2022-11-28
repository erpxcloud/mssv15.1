from odoo import fields, models 
import logging

log = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    division_ids = fields.Many2many('azk_sales_division.division', string='Divisions', help='Divisions')