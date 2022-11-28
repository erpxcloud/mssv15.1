# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, _, fields, http
from odoo.http import request
from odoo.tools import float_is_zero
from odoo.tools.misc import format_date
from datetime import datetime, timedelta

import logging

log = logging.getLogger(__name__)

class ReportPartnerLedger(models.AbstractModel):
    _inherit = "account.partner.ledger"
    
    @api.model
    def _get_options_domain(self, options):
        domain = super(ReportPartnerLedger, self)._get_options_domain(options)
        
        cids = request.httprequest.cookies.get('cids', str(request.env.user.company_id.id))
        company_ids = [int(cid) for cid in cids.split(',')]
        company = self.env['res.company'].browse(company_ids[0])
    
        if self._context.get('print_mode') and company.remove_exchange_journal:
            domain.append(('journal_id', '!=', company.currency_exchange_journal_id.id))
    
        return domain
    

    def _do_query_group_by_account(self, options, line_id):
        account_types = [a.get('id') for a in options.get('account_type') if a.get('selected', False)]
        if not account_types:
            account_types = [a.get('id') for a in options.get('account_type')]
        # Create the currency table.
        cids = request.httprequest.cookies.get('cids', str(request.env.user.company_id.id))
        company_ids = [int(cid) for cid in cids.split(',')]
        user_company = self.env['res.company'].browse(company_ids[0])
        companies = self.env['res.company'].search([])
        rates_table_entries = []
        for company in companies:
            if company.currency_id == user_company.currency_id:
                rate = 1.0
            else:
                rate = self.env['res.currency']._get_conversion_rate(
                    company.currency_id, user_company.currency_id, user_company, datetime.today())
            rates_table_entries.append((company.id, rate, user_company.currency_id.decimal_places))
        currency_table = ','.join('(%s, %s, %s)' % r for r in rates_table_entries)
        with_currency_table = 'WITH currency_table(company_id, rate, precision) AS (VALUES %s)' % currency_table

        # Sum query
        if options.get('selected_multi_currency'):
            selected_multi_currency = int(options.get('selected_multi_currency'))
                       
            if selected_multi_currency == company.second_currency_id.id:
                debit_field = 'second_debit_cash_basis' if options.get('cash_basis') else 'second_debit' 
                credit_field = 'second_credit_cash_basis' if options.get('cash_basis') else 'second_credit'
                balance_field = 'second_balance_cash_basis' if options.get('cash_basis') else 'second_balance'
            elif selected_multi_currency == company.third_currency_id.id:
                debit_field = 'third_debit_cash_basis' if options.get('cash_basis') else 'third_debit'
                credit_field = 'third_credit_cash_basis' if options.get('cash_basis') else 'third_credit'
                balance_field = 'third_balance_cash_basis' if options.get('cash_basis') else 'third_balance'
            else:
                debit_field = 'debit_cash_basis' if options.get('cash_basis') else 'debit'
                credit_field = 'credit_cash_basis' if options.get('cash_basis') else 'credit'
                balance_field = 'balance_cash_basis' if options.get('cash_basis') else 'balance'
        else:
            debit_field = 'debit_cash_basis' if options.get('cash_basis') else 'debit'
            credit_field = 'credit_cash_basis' if options.get('cash_basis') else 'credit'
            balance_field = 'balance_cash_basis' if options.get('cash_basis') else 'balance'
            
        tables, where_clause, params = self.env['account.move.line']._query_get(
            [('account_id.internal_type', 'in', account_types)])
        query = '''
            SELECT
                \"account_move_line\".partner_id,
                SUM(\"account_move_line\".''' + debit_field + ''' * currency_table.rate)     AS debit,
                SUM(\"account_move_line\".''' + credit_field + ''' * currency_table.rate)    AS credit,
                SUM(\"account_move_line\".''' + balance_field + ''' * currency_table.rate)   AS balance
            FROM %s
            LEFT JOIN currency_table                    ON currency_table.company_id = \"account_move_line\".company_id
            WHERE %s
            AND \"account_move_line\".partner_id IS NOT NULL
            GROUP BY \"account_move_line\".partner_id
        ''' % (tables, where_clause)
        if line_id:
            query = query.replace('WHERE', 'WHERE \"account_move_line\".partner_id = %s AND ')
            params = [str(line_id)] + params
        if options.get("unreconciled"):
            query = query.replace("WHERE", 'WHERE \"account_move_line\".full_reconcile_id IS NULL AND ')
            
        self._cr.execute(with_currency_table + query, params)
        query_res = self._cr.dictfetchall()
        return dict((res['partner_id'], res) for res in query_res)

    def _group_by_partner_id(self, options, line_id):
        partners = {}
        account_types = [a.get('id') for a in options.get('account_type') if a.get('selected', False)]
        if not account_types:
            account_types = [a.get('id') for a in options.get('account_type')]
        date_from = options['date']['date_from']
        results = self._do_query_group_by_account(options, line_id)
        initial_bal_results = self.with_context(
            date_from=False, date_to=fields.Date.from_string(date_from) + timedelta(days=-1)
        )._do_query_group_by_account(options, line_id)
        context = self.env.context
        base_domain = [('date', '<=', context['date_to']), ('company_id', 'in', context['company_ids']), ('account_id.internal_type', 'in', account_types)]
        base_domain.append(('date', '>=', date_from))
        if context['state'] == 'posted':
            base_domain.append(('move_id.state', '=', 'posted'))
        if options.get('unreconciled'):
            base_domain.append(('full_reconcile_id', '=', False))
        for partner_id, result in results.items():
            domain = list(base_domain)  # copying the base domain
            domain.append(('partner_id', '=', partner_id))
            partner = self.env['res.partner'].browse(partner_id)
            partners[partner] = result
            partners[partner]['initial_bal'] = initial_bal_results.get(partner.id, {'balance': 0, 'debit': 0, 'credit': 0})
            partners[partner]['balance'] += partners[partner]['initial_bal']['balance']
            partners[partner]['total_lines'] = 0
            if not context.get('print_mode'):
                partners[partner]['total_lines'] = self.env['account.move.line'].search_count(domain)
                offset = int(options.get('lines_offset', 0))
                limit = self.MAX_LINES
                partners[partner]['lines'] = self.env['account.move.line'].search(domain, order='date,id', limit=limit, offset=offset)
            else:
                partners[partner]['lines'] = self.env['account.move.line'].search(domain, order='date,id')

        # Add partners with an initial balance != 0 but without any AML in the selected period.
        
        cids = request.httprequest.cookies.get('cids', str(request.env.user.company_id.id))
        company_ids = [int(cid) for cid in cids.split(',')]
        company = self.env['res.company'].browse(company_ids[0])
        prec = company.currency_id.rounding
        missing_partner_ids = set(initial_bal_results.keys()) - set(results.keys())
        for partner_id in missing_partner_ids:
            if not float_is_zero(initial_bal_results[partner_id]['balance'], precision_rounding=prec):
                partner = self.env['res.partner'].browse(partner_id)
                partners[partner] = {'balance': 0, 'debit': 0, 'credit': 0}
                partners[partner]['initial_bal'] = initial_bal_results[partner_id]
                partners[partner]['balance'] += partners[partner]['initial_bal']['balance']
                partners[partner]['lines'] = self.env['account.move.line']
                partners[partner]['total_lines'] = 0

        return partners
    
    
    ####################################################
    # QUERIES
    ####################################################

    @api.model
    def _get_query_sums(self, options, expanded_partner=None):
        ''' Construct a query retrieving all the aggregated sums to build the report. It includes:
        - sums for all accounts.
        - sums for the initial balances.
        - sums for the unaffected earnings.
        - sums for the tax declaration.
        :param options:             The report options.
        :param expanded_partner:    An optional account.account record that must be specified when expanding a line
                                    with of without the load more.
        :return:                    (query, params)
        '''
        params = []
        queries = []

        if expanded_partner:
            domain = [('partner_id', '=', expanded_partner.id)]
        else:
            domain = []

        # Create the currency table.
        ct_query = self._get_query_currency_table(options)

        # Get sums for all partners.
        # period: [('date' <= options['date_to']), ('date' >= options['date_from'])]
        new_options = self._get_options_sum_balance(options)
        tables, where_clause, where_params = self._query_get(new_options, domain=domain)
        params += where_params
        queries.append('''
            SELECT
                account_move_line.partner_id        AS groupby,
                'sum'                               AS key,
                SUM(ROUND(account_move_line.debit * currency_table.rate, currency_table.precision))   AS debit,
                SUM(ROUND(account_move_line.credit * currency_table.rate, currency_table.precision))  AS credit,
                SUM(ROUND(account_move_line.balance * currency_table.rate, currency_table.precision)) AS balance
            FROM %s
            LEFT JOIN %s ON currency_table.company_id = account_move_line.company_id
            WHERE %s
            GROUP BY account_move_line.partner_id
        ''' % (tables, ct_query, where_clause))

        # Get sums for the initial balance.
        # period: [('date' <= options['date_from'] - 1)]
        new_options = self._get_options_initial_balance(options)
        tables, where_clause, where_params = self._query_get(new_options, domain=domain)
        params += where_params
        queries.append('''
            SELECT
                account_move_line.partner_id        AS groupby,
                'initial_balance'                   AS key,
                SUM(ROUND(account_move_line.debit * currency_table.rate, currency_table.precision))   AS debit,
                SUM(ROUND(account_move_line.credit * currency_table.rate, currency_table.precision))  AS credit,
                SUM(ROUND(account_move_line.balance * currency_table.rate, currency_table.precision)) AS balance
            FROM %s
            LEFT JOIN %s ON currency_table.company_id = account_move_line.company_id
            WHERE %s
            GROUP BY account_move_line.partner_id
        ''' % (tables, ct_query, where_clause))
        
        if options.get('selected_multi_currency'):
            selected_multi_currency = int(options.get('selected_multi_currency'))
            
            cids = request.httprequest.cookies.get('cids', str(request.env.user.company_id.id))
            company_ids = [int(cid) for cid in cids.split(',')]
            company = self.env['res.company'].browse(company_ids[0])
            
            updated_queries = []
            
            for query in queries:
                if selected_multi_currency == company.second_currency_id.id:
                    query = query.replace('account_move_line.debit', 'account_move_line.second_debit').replace('account_move_line.credit', 'account_move_line.second_credit').replace('account_move_line.balance', 'account_move_line.second_balance')
                elif selected_multi_currency == company.third_currency_id.id:
                    query = query.replace('account_move_line.debit', 'account_move_line.third_debit').replace('account_move_line.credit', 'account_move_line.third_credit').replace('account_move_line.balance', 'account_move_line.third_balance')
            
                updated_queries.append(query)
        
            queries = updated_queries
            
        return ' UNION ALL '.join(queries), params

    @api.model
    def _get_query_amls(self, options, expanded_partner=None, offset=None, limit=None):
        ''' Construct a query retrieving the account.move.lines when expanding a report line with or without the load
        more.
        :param options:             The report options.
        :param expanded_partner:    The res.partner record corresponding to the expanded line.
        :param offset:              The offset of the query (used by the load more).
        :param limit:               The limit of the query (used by the load more).
        :return:                    (query, params)
        '''
        unfold_all = options.get('unfold_all') or (self._context.get('print_mode') and not options['unfolded_lines'])

        # Get sums for the account move lines.
        # period: [('date' <= options['date_to']), ('date', '>=', options['date_from'])]
        if expanded_partner:
            domain = [('partner_id', '=', expanded_partner.id)]
        elif unfold_all:
            domain = []
        elif options['unfolded_lines']:
            domain = [('partner_id', 'in', [int(line[8:]) for line in options['unfolded_lines']])]

        new_options = self._get_options_sum_balance(options)
        tables, where_clause, where_params = self._query_get(new_options, domain=domain)
        ct_query = self._get_query_currency_table(options)

        query = '''
            SELECT
                account_move_line.id,
                account_move_line.date,
                account_move_line.date_maturity,
                account_move_line.name,
                account_move_line.ref,
                account_move_line.company_id,
                account_move_line.account_id,             
                account_move_line.payment_id,
                account_move_line.partner_id,
                account_move_line.currency_id,
                account_move_line.amount_currency,
                ROUND(account_move_line.debit * currency_table.rate, currency_table.precision)   AS debit,
                ROUND(account_move_line.credit * currency_table.rate, currency_table.precision)  AS credit,
                ROUND(account_move_line.balance * currency_table.rate, currency_table.precision) AS balance,
                account_move_line__move_id.name         AS move_name,
                company.currency_id                     AS company_currency_id,
                partner.name                            AS partner_name,
                account_move_line__move_id.type         AS move_type,
                account_move_line__move_id.invoice_date AS invoice_date,
                account.code                            AS account_code,
                account.name                            AS account_name,
                journal.code                            AS journal_code,
                journal.name                            AS journal_name,
                full_rec.name                           AS full_rec_name
            FROM account_move_line
            LEFT JOIN account_move account_move_line__move_id ON account_move_line__move_id.id = account_move_line.move_id
            LEFT JOIN %s ON currency_table.company_id = account_move_line.company_id
            LEFT JOIN res_company company               ON company.id = account_move_line.company_id
            LEFT JOIN res_partner partner               ON partner.id = account_move_line.partner_id
            LEFT JOIN account_account account           ON account.id = account_move_line.account_id
            LEFT JOIN account_journal journal           ON journal.id = account_move_line.journal_id
            LEFT JOIN account_full_reconcile full_rec   ON full_rec.id = account_move_line.full_reconcile_id
            WHERE %s
            ORDER BY account_move_line.id
        ''' % (ct_query, where_clause)

        if offset:
            query += ' OFFSET %s '
            where_params.append(offset)
        if limit:
            query += ' LIMIT %s '
            where_params.append(limit)
        
        if options.get('selected_multi_currency'):
            selected_multi_currency = int(options.get('selected_multi_currency'))
            
            cids = request.httprequest.cookies.get('cids', str(request.env.user.company_id.id))
            company_ids = [int(cid) for cid in cids.split(',')]
            company = self.env['res.company'].browse(company_ids[0])
            
            if selected_multi_currency == company.second_currency_id.id:
                query = query.replace('account_move_line.debit', 'account_move_line.second_debit').replace('account_move_line.credit', 'account_move_line.second_credit').replace('account_move_line.balance', 'account_move_line.second_balance')
            elif selected_multi_currency == company.third_currency_id.id:
                query = query.replace('account_move_line.debit', 'account_move_line.third_debit').replace('account_move_line.credit', 'account_move_line.third_credit').replace('account_move_line.balance', 'account_move_line.third_balance')
        cids = request.httprequest.cookies.get('cids', str(request.env.user.company_id.id))
        company_ids = [int(cid) for cid in cids.split(',')]
        company = self.env['res.company'].browse(company_ids[0])
    
        return query, where_params
    
    
    
    def _get_columns_name(self, options):
        result = super(ReportPartnerLedger,self)._get_columns_name(options)
        cids = request.httprequest.cookies.get('cids', str(request.env.user.company_id.id))
        company_ids = [int(cid) for cid in cids.split(',')]
        company = self.env['res.company'].browse(company_ids[0])
    
        if  company.add_invoice_customer:
            result.pop(2)
            result.insert(2,{'name': _('Customer Ref')})
            result.insert(4,{'name': _('Invoice Date'), 'class': 'date'})
        return result
        

    @api.model
    def _get_report_line_total(self, options, initial_balance, debit, credit, balance):
        res = super(ReportPartnerLedger,self)._get_report_line_total(options,initial_balance, debit, credit, balance)
        cids = request.httprequest.cookies.get('cids', str(request.env.user.company_id.id))
        company_ids = [int(cid) for cid in cids.split(',')]
        company = self.env['res.company'].browse(company_ids[0])
    
        if  company.add_invoice_customer:
            res['colspan'] = 7
        return res
        
    @api.model
    def _get_report_line_partner(self, options, partner, initial_balance, debit, credit, balance):
        res = super(ReportPartnerLedger,self)._get_report_line_partner(options, partner, initial_balance, debit, credit, balance)
        cids = request.httprequest.cookies.get('cids', str(request.env.user.company_id.id))
        company_ids = [int(cid) for cid in cids.split(',')]
        company = self.env['res.company'].browse(company_ids[0])
    
        if  company.add_invoice_customer:
            res['colspan'] = 7
        return res
      
    @api.model
    def _get_report_line_move_line(self, options, partner, aml, cumulated_init_balance, cumulated_balance):
        res = super(ReportPartnerLedger,self)._get_report_line_move_line(options, partner, aml, cumulated_init_balance, cumulated_balance)
        cids = request.httprequest.cookies.get('cids', str(request.env.user.company_id.id))
        company_ids = [int(cid) for cid in cids.split(',')]
        company = self.env['res.company'].browse(company_ids[0])
        if  company.add_invoice_customer:
            res['columns'].pop(1)
            res['columns'].insert(1,{'name': aml['ref']})
            res['columns'].insert(3,{'name': aml['invoice_date']})
        return res
    
    
    def get_report_filename(self, options):
        """The name that will be used for the file when downloading pdf,xlsx,..."""
        report_filename = "%s-%s" % (self._get_report_name().lower().replace(' ', '_'), fields.Date.to_string(fields.Date.today()))
        
        if options.get('partner_ids') and len(options.get('partner_ids')) == 1:
            partner_id = self.env['res.partner'].browse([int(partner) for partner in options['partner_ids']])
            report_filename = "%s-%s-%s" % (self._get_report_name().lower().replace(' ', '_'), partner_id.name,fields.Date.to_string(fields.Date.today()))
            
        return report_filename