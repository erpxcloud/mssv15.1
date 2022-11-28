from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
import logging

log = logging.getLogger(__name__)

class HrPayslipLine(models.Model):
    _inherit = 'hr.payslip.line'

    payroll_currency_id = fields.Many2one(related="slip_id.company_id.payroll_currency_id")