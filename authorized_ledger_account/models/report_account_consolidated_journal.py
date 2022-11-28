from odoo import models, fields, api
import logging

log = logging.getLogger(__name__)


class report_account_consolidated_journal(models.AbstractModel):
    _inherit = "account.consolidated.journal"
    
    def _get_account_line(self, options, current_journal, current_account, results, record):
        
        for rec in results:
            non_auth = self.env['account.nonauthorized.user'].search([('account_id', '=', rec['account_id']), ('user_id', '=', self.env.user.id)])
            if non_auth:
                rec['account_name'] = "*****"
                rec['account_code'] = "*****"
            
        return {
                'id': 'account_%s_%s' % (current_account,current_journal),
                'name': '%s %s' % (record['account_code'], record['account_name']),
                'level': 3,
                'columns': [{'name': n} for n in self._get_sum(results, lambda x: x['account_id'] == current_account)],
                'unfoldable': True,
                'unfolded': self._need_to_unfold('account_%s_%s' % (current_account, current_journal), options),
                'parent_id': 'journal_%s' % (current_journal),
            }
        
        
        
        