from odoo import fields, models,api
import logging

log = logging.getLogger(__name__)

class Users(models.Model):
    _inherit = 'res.users'
    
    division_ids = fields.Many2many('azk_sales_division.division','rel_salesperson_divisions', string='Divisions', help='Divisions')