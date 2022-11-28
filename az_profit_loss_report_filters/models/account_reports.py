
from odoo import models, api

class AccountReport(models.AbstractModel):
    _inherit = "account.report"
    
    filter_division = None
    filter_end_user = None
 
    @api.model
    def _init_filter_division(self, options, previous_options=None):
        if not self.filter_division:
            return

        options['divisions'] = True
        options['division_ids'] = previous_options and previous_options.get('division_ids') or []
        selected_division_ids = [int(division) for division in options['division_ids']]
        selected_division = selected_division_ids and self.env['azk_sales_division.division'].browse(selected_division_ids) or self.env['azk_sales_division.division']
        options['selected_division_ids'] = selected_division.mapped('name')
    
    @api.model
    def _init_filter_end_user(self, options, previous_options=None):
        if not self.filter_end_user:
            return

        options['end_users'] = True
        options['end_user_ids'] = previous_options and previous_options.get('end_user_ids') or []
        selected_end_user_ids = [int(user) for user in options['end_user_ids']]
        selected_end_user_ids = selected_end_user_ids and self.env['res.partner'].browse(selected_end_user_ids) or self.env['res.partner']
        options['selected_end_user_ids'] = selected_end_user_ids.mapped('name')
        
    @api.model
    def _get_options_divisions_domain(self, options):
        domain = []
        if options.get('division_ids'):
            division_ids = [int(division) for division in options['division_ids']]
            domain.append(('x_studio_division', 'in', division_ids))
        return domain
    
    @api.model
    def _get_options_end_user_domain(self, options):
        domain = []
        if options.get('end_user_ids'):
            end_user_ids = [int(user) for user in options['end_user_ids']]
            domain.append(('x_studio_field_k7cLJ', 'in', end_user_ids))
        return domain
    
    @api.model
    def _get_options_domain(self, options):
        domain = super(AccountReport, self)._get_options_domain(options)
        domain += self._get_options_divisions_domain(options)
        domain += self._get_options_end_user_domain(options)
        return domain
    
    def _set_context(self, options):
        """This method will set information inside the context based on the options dict as some options need to be in context for the query_get method defined in account_move_line"""
        ctx = super(AccountReport, self)._set_context(options)

        if options.get('division_ids'):
            ctx['division_ids'] = self.env['azk_sales_division.division'].browse([int(division) for division in options['division_ids']])
        
        if options.get('end_user_ids'):
            ctx['end_user_ids'] = self.env['res.partner'].browse([int(user) for user in options['end_user_ids']])
        return ctx
    
    def get_report_informations(self, options):
        options = self._get_options(options)
        if options.get('divisions'):
            options['selected_division_ids'] = [self.env['azk_sales_division.division'].browse(int(division)).name for division in options['division_ids']]
            
        if options.get('end_users'):
            options['selected_end_user_ids'] = [self.env['res.partner'].browse(int(user)).name for user in options['end_user_ids']]
         
        info = super(AccountReport, self).get_report_informations(options)
        return info
    