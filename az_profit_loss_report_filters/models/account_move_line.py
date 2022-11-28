
from odoo import models, api

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"
    
    @api.model
    def _query_get(self, domain=None):
        
        self.check_access_rights('read')

        context = dict(self._context or {})
        
        if context.get('division_ids'):
            domain += [('x_studio_division', 'in', context['division_ids'].ids)]
            
        if context.get('end_user_ids'):
            domain += [('x_studio_field_k7cLJ', 'in', context['end_user_ids'].ids)]
        
        return super(AccountMoveLine, self)._query_get(domain)
    