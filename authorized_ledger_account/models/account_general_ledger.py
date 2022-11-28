from odoo import models, fields, api
import logging

log = logging.getLogger(__name__)


class AccountGeneralLedgerReportInherited(models.AbstractModel):
    _inherit = "account.general.ledger"
    
    @api.model
    def _get_account_title_line(self, options, account, amount_currency, debit, credit, balance, has_lines):

        res = super(AccountGeneralLedgerReportInherited, self)._get_account_title_line(options, account, amount_currency, debit, credit, balance, has_lines)
        non_auth = self.env['account.nonauthorized.user'].search([('account_id', '=', account.id), ('user_id', '=', self.env.user.id)])
        
        if non_auth:
            res['name'] = "*****"
            res['title_hover'] = "*****"
            
        return res
