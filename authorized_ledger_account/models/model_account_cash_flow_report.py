from odoo import models, fields, api
import logging

log = logging.getLogger(__name__)


class AccountCashFlowReportInherited(models.AbstractModel):
    _inherit = "account.cash.flow.report"
    
    @api.model
    def _get_lines(self, options, line_id=None):

        res = super(AccountCashFlowReportInherited, self)._get_lines(options, line_id)
        
        for rec in res:
            if rec.get('id') and type(rec['id']) == int:
                non_auth = self.env['account.nonauthorized.user'].search([('account_id', '=', rec['id']), ('user_id', '=', self.env.user.id)])
                if non_auth:
                    rec['name'] = "*****"
                
        return res
