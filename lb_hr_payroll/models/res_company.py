from odoo import models, fields, api
import logging

log = logging.getLogger(__name__)

class CompanyInherited(models.Model):
    _inherit = 'res.company'

    payroll_currency_id = fields.Many2one('res.currency', string="Payroll Currency")