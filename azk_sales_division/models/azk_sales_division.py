from odoo import fields, models 
import logging

log = logging.getLogger(__name__)

class Division(models.Model):
    _name = 'azk_sales_division.division'
    _description = 'Division'
    
    name = fields.Char('Name', required=True)
    description = fields.Char('Description')
    product_ids = fields.Many2many('product.template', string='Products')
    salesperson_ids = fields.Many2many('res.users','rel_salesperson_divisions', string='SalesPersons') 