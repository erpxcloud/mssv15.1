# -*- coding: utf-8 -*-
from odoo import models, api, http
from odoo.http import request
from odoo.tools.translate import _
from odoo.tools.misc import formatLang
import logging

log = logging.getLogger(__name__)

class generic_tax_report(models.AbstractModel):
    _inherit = 'account.generic.tax.report'
    
     
    def get_selected_company(self):
        cids = request.httprequest.cookies.get('cids', str(request.env.user.company_id.id))
        company_ids = [int(cid) for cid in cids.split(',')]
        user_company = self.env['res.company'].browse(company_ids[0])
            
        return user_company
    
    def _sql_cash_based_taxes(self):
        sql = super(generic_tax_report, self)._sql_cash_based_taxes()
        
        company = self.get_selected_company()
        selected_multi_currency_id = self.env.context.get('selected_multi_currency')
        if selected_multi_currency_id:
            selected_multi_currency = int(selected_multi_currency_id)
                        
            if selected_multi_currency == company.second_currency_id.id:
                sql = sql.replace('.balance', '.second_balance')
            elif selected_multi_currency == company.third_currency_id.id:
               sql = sql.replace('.balance', '.third_balance')
               
        return sql

    def _sql_tax_amt_regular_taxes(self):
        sql = super(generic_tax_report, self)._sql_tax_amt_regular_taxes()
        
        company = self.get_selected_company()
        selected_multi_currency_id = self.env.context.get('selected_multi_currency')
        if selected_multi_currency_id:
            selected_multi_currency = int(selected_multi_currency_id)
                        
            if selected_multi_currency == company.second_currency_id.id:
                sql = sql.replace('.debit', '.second_debit').replace('.credit', '.second_credit')
            elif selected_multi_currency == company.third_currency_id.id:
               sql = sql.replace('.debit', '.third_debit').replace('.credit', '.third_credit')
        
        return sql

    def _sql_net_amt_regular_taxes(self):
        sql = super(generic_tax_report, self)._sql_net_amt_regular_taxes()
                
        company = self.get_selected_company()
        selected_multi_currency_id = self.env.context.get('selected_multi_currency')
        if selected_multi_currency_id:
            selected_multi_currency = int(selected_multi_currency_id)
                        
            if selected_multi_currency == company.second_currency_id.id:
                sql = sql.replace('.debit', '.second_debit').replace('.credit', '.second_credit')
            elif selected_multi_currency == company.third_currency_id.id:
               sql = sql.replace('.debit', '.third_debit').replace('.credit', '.third_credit')
               
        return sql
    
    
    def _compute_from_amls_grids(self, options, dict_to_fill, period_number):
        """ Fills dict_to_fill with the data needed to generate the report, when
        the report is set to group its line by tax grid.
        """
        tables, where_clause, where_params = self.env['account.move.line']._query_get()
        sql = """SELECT account_tax_report_line_tags_rel.account_tax_report_line_id,
                        SUM(coalesce(account_move_line.balance, 0) * CASE WHEN acc_tag.tax_negate THEN -1 ELSE 1 END
                                                 * CASE WHEN account_journal.type = 'sale' THEN -1 ELSE 1 END
                                                 * CASE WHEN account_move.type in ('in_refund', 'out_refund') THEN -1 ELSE 1 END)
                        AS balance
                 FROM account_account_tag_account_move_line_rel aml_tag
                 JOIN account_move_line
                 ON aml_tag.account_move_line_id = account_move_line.id
                 JOIN account_move
                 ON account_move_line.move_id = account_move.id
                 JOIN account_journal
                 ON account_move.journal_id = account_journal.id
                 JOIN account_account_tag acc_tag
                 ON aml_tag.account_account_tag_id = acc_tag.id
                 JOIN account_tax_report_line_tags_rel
                 ON acc_tag.id = account_tax_report_line_tags_rel.account_account_tag_id
                 WHERE account_move_line.company_id IN %(company_ids)s
                 AND account_move_line.date <= %(date_to)s
                 AND account_move_line.date >= %(date_from)s
                 AND (NOT %(only_posted)s OR account_move.state = 'posted')
                 AND account_move_line.tax_exigible
                 AND account_journal.id = account_move_line.journal_id
                 GROUP BY account_tax_report_line_tags_rel.account_tax_report_line_id
        """
        
        company = self.get_selected_company()
        selected_multi_currency_id = self.env.context.get('selected_multi_currency')
        if selected_multi_currency_id:
            selected_multi_currency = int(selected_multi_currency_id)
                        
            if selected_multi_currency == company.second_currency_id.id:
                sql = sql.replace('account_move_line.balance', 'account_move_line.second_balance')
            elif selected_multi_currency == company.third_currency_id.id:
               sql = sql.replace('account_move_line.balance', 'account_move_line.third_balance')
               
        params = {'date_from': self.env.context['date_from'], 'date_to': self.env.context['date_to'], 'company_ids': tuple(self.env.context['company_ids']), 'only_posted': self.env.context.get('state') == 'posted'}
        self.env.cr.execute(sql, params)
        results = self.env.cr.fetchall()
        for result in results:
            if result[0] in dict_to_fill:
                dict_to_fill[result[0]]['periods'][period_number]['balance'] = result[1]
                dict_to_fill[result[0]]['show'] = True