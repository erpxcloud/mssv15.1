from odoo import models, fields, api


class ResCompany(models.Model):
    _inherit = 'res.company'

    defualt_customer_foc_location = fields.Many2one('stock.location')
    defualt_customer_real_stock_location = fields.Many2one('stock.location')
    defualt_customer_consignment_stock_location = fields.Many2one('stock.location')
    defualt_customer_demo_stock_location = fields.Many2one('stock.location')
    defualt_customer_tender_stock_location = fields.Many2one('stock.location')