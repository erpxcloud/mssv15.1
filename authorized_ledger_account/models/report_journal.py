from odoo import models, fields, api
import logging

log = logging.getLogger(__name__)


class ReportJournalInherited(models.AbstractModel):
    _inherit = "report.account.report_journal"
    
    @api.model
    def _get_report_values(self, docids, data=None):
        
        res = super(ReportJournalInherited, self)._get_report_values(docids, data)
        res['data']['masked_accounts'] = {}
        
        for recs_id in res['lines']:
            for move_line in res['lines'][recs_id]:
                non_auth = self.env['account.nonauthorized.user'].search([('account_id', '=', move_line.account_id.id), ('user_id', '=', self.env.user.id)])
                
                if non_auth: 
                    acc_code = "*****"
                    acc_name = "*****"
                else: 
                    acc_code = move_line.account_id.code
                    acc_name = move_line.account_id.name
                
                res['data']['masked_accounts'][move_line.account_id.id] = {'name': acc_name, 'code': acc_code}
        
        return res