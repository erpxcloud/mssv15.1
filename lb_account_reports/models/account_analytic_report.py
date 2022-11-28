# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, http
from odoo.http import request

import logging

log = logging.getLogger(__name__)

class analytic_report(models.AbstractModel):
    _inherit = 'account.analytic.report'
    
    filter_hierarchy_parent = False
    
    def _get_balance_for_group(self, group, analytic_line_domain):
        analytic_line_domain_for_group = list(analytic_line_domain)
        if group:
            # take into account the hierarchy on account.analytic.line
            analytic_line_domain_for_group += [('group_id', 'child_of', group.id)]
        else:
            analytic_line_domain_for_group += [('group_id', '=', False)]

        currency_obj = self.env['res.currency']
        
        cids = request.httprequest.cookies.get('cids', str(request.env.user.company_id.id))
        company_ids = [int(cid) for cid in cids.split(',')]
        user_company = self.env['res.company'].browse(company_ids[0])
        
        selected_multi_currency_id = self._context.get('selected_multi_currency')
        
        user_currency = user_company.currency_id
        if selected_multi_currency_id:
            selected_multi_currency_id = int(selected_multi_currency_id)
            if user_company.second_currency_id.id == selected_multi_currency_id:
                user_currency = user_company.second_currency_id
            elif user_company.third_currency_id.id == selected_multi_currency_id:
                user_currency = user_company.third_currency_id
        
        analytic_lines = self.env['account.analytic.line'].read_group(analytic_line_domain_for_group, ['amount', 'currency_id'], ['currency_id'])
        balance = sum([currency_obj.browse(row['currency_id'][0])._convert(
            row['amount'], user_currency, user_company, fields.Date.today()) for row in analytic_lines])
        return balance
    
    def _generate_analytic_account_lines(self, analytic_accounts, parent_id=False):
        lines = []
        
        cids = request.httprequest.cookies.get('cids', str(request.env.user.company_id.id))
        company_ids = [int(cid) for cid in cids.split(',')]
        user_company = self.env['res.company'].browse(company_ids[0])
            
        for account in analytic_accounts:
            selected_multi_currency_id = self._context.get('selected_multi_currency')
            
            user_currency = user_company.currency_id
            if selected_multi_currency_id:
                selected_multi_currency_id = int(selected_multi_currency_id)
                if user_company.second_currency_id.id == selected_multi_currency_id:
                    user_currency = user_company.second_currency_id
                elif user_company.third_currency_id.id == selected_multi_currency_id:
                    user_currency = user_company.third_currency_id
            
            account_balance = user_company.currency_id._convert(account.balance, user_currency, user_company, fields.Date.today())
            
            lines.append({
                'id': 'analytic_account_%s' % account.id,
                'name': account.name,
                'columns': [{'name': account.code},
                            {'name': account.partner_id.display_name},
                            {'name': self.format_value(account_balance)}],
                'level': 4,  # todo check redesign financial reports, should be level + 1 but doesn't look good
                'unfoldable': False,
                'caret_options': 'account.analytic.account',
                'parent_id': parent_id,  # to make these fold when the original parent gets folded
            })

        return lines