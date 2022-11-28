from odoo import models, fields, api, _

class AccountReport(models.AbstractModel):
    _inherit = 'account.report'
    
    @api.model
    def _get_options_journals(self, options):
        return [
            journal for journal in options.get('journals', []) if
            not journal['id'] in ('deselectall', 'selectall', 'divider', 'group') and journal['selected']
        ]
        
        
    @api.model
    def _init_filter_journals(self, options, previous_options=None):
        super(AccountReport, self)._init_filter_journals(options, previous_options)
        
        if 'journals' in options:
            options['journals'].insert(1, {'id': 'selectall', 'name': 'Select All'})
            options['journals'].insert(1, {'id': 'deselectall', 'name': 'Unselect All'})
        