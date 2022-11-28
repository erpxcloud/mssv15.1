from odoo import models, fields, api, _
from odoo.exceptions import Warning as UserError


class StockLocation(models.Model):
    _inherit = 'stock.location'

    is_partner_location = fields.Boolean(default=False)
    