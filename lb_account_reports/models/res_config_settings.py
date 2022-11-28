from odoo import api, fields, models, _

class ResCompany(models.Model):
    _inherit = 'res.company'
    
    split_account_in_excel = fields.Boolean(string="Split Account's name/code in Accounting Reports Excel")
    remove_exchange_journal = fields.Boolean(string="Remove Exchange Journals From Partner Ledger and Partner Ledger Ac Reports")
    add_invoice_customer = fields.Boolean(string="Add Customer Reference and Invoice date into Partner Ledger/AC  Views and Reports")
class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    split_account_in_excel = fields.Boolean(related='company_id.split_account_in_excel', readonly=False)
    remove_exchange_journal = fields.Boolean(related='company_id.remove_exchange_journal', readonly=False)
    add_invoice_customer = fields.Boolean(related='company_id.add_invoice_customer', readonly=False)