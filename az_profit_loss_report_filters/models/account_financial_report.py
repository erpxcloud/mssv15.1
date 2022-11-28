
from odoo import models

class ReportAccountFinancialReport(models.Model):
    _inherit = "account.financial.html.report"
    
    filter_division = True
    filter_end_user = True