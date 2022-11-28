from odoo import models
import logging

log = logging.getLogger(__name__)

class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'
    
    def _prepare_payment_vals(self, invoices):
        values = super(AccountPaymentRegister, self)._prepare_payment_vals(invoices)
        values['account_amount'] = values['amount']
        values['account_currency_id'] = values['currency_id']
        
        return values
