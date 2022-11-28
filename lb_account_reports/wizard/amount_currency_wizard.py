# -*- coding: utf-8 -*-
import datetime 
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import pprint 

import logging
import json

from odoo.tools.misc import format_date
from datetime import datetime, timedelta
from odoo.addons.web.controllers.main import clean_action
from odoo.tools import float_is_zero

import xlsxwriter
import os
import base64
import  datetime

from odoo.tools.config import config

log = logging.getLogger(__name__)

class AmountCurrency(models.TransientModel):
    _name = 'amount.currency.wizard'
    _description = 'Amount Currency Wizard'
    
    account_id = fields.Many2many('account.account')
    partner_id = fields.Many2one('res.partner')
    analytic_account_ids = fields.Many2many('account.analytic.account')
    currency_ids = fields.Many2many('res.currency')
    from_date = fields.Date()
    to_date = fields.Date()
    
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company)
    
    @api.onchange('partner_id')
    def onchange_account_id(self):
        if self.partner_id:
            accounts = []
            if self.partner_id.property_account_receivable_id and self.partner_id.property_account_receivable_id.id:
                accounts.append(self.partner_id.property_account_receivable_id.id)
            if self.partner_id.property_account_payable_id and self.partner_id.property_account_payable_id.id:
                accounts.append(self.partner_id.property_account_payable_id.id)
                
            self.account_id = [(6, 0, accounts)]
            
    def _get_with_statement(self, user_types, domain=None):
        """ This function allow to define a WITH statement as prologue to the usual queries returned by query_get().
            It is useful if you need to shadow a table entirely and let the query_get work normally although you're
            fetching rows from your temporary table (built in the WITH statement) instead of the regular tables.

            @returns: the WITH statement to prepend to the sql query and the parameters used in that WITH statement
            @rtype: tuple(char, list)
        """
        sql = ''
        params = []

        #Cash basis option
        #-----------------
        #In cash basis, we need to show amount on income/expense accounts, but only when they're paid AND under the payment date in the reporting, so
        #we have to make a complex query to join aml from the invoice (for the account), aml from the payments (for the date) and partial reconciliation
        #(for the reconciled amount).
        if self.env.context.get('cash_basis'):
            if not user_types:
                return sql, params
            #we use query_get() to filter out unrelevant journal items to have a shadowed table as small as possible
            tables, where_clause, where_params = self.env['account.move.line']._query_get(domain=domain)
            sql = """WITH account_move_line AS (
              SELECT \"account_move_line\".id, \"account_move_line\".date, \"account_move_line\".name, \"account_move_line\".debit_cash_basis, \"account_move_line\".credit_cash_basis, \"account_move_line\".move_id, \"account_move_line\".account_id, \"account_move_line\".journal_id, \"account_move_line\".balance_cash_basis, \"account_move_line\".amount_residual, \"account_move_line\".partner_id, \"account_move_line\".reconciled, \"account_move_line\".company_id, \"account_move_line\".company_currency_id, \"account_move_line\".amount_currency, \"account_move_line\".balance, \"account_move_line\".user_type_id, \"account_move_line\".analytic_account_id
               FROM """ + tables + """
               WHERE (\"account_move_line\".journal_id IN (SELECT id FROM account_journal WHERE type in ('cash', 'bank'))
                 OR \"account_move_line\".move_id NOT IN (SELECT DISTINCT move_id FROM account_move_line WHERE user_type_id IN %s))
                 AND """ + where_clause + """
              UNION ALL
              (
               WITH payment_table AS (
                 SELECT aml.move_id, \"account_move_line\".date,
                        CASE WHEN (aml.balance = 0 OR sub_aml.total_per_account = 0)
                            THEN 0
                            ELSE part.amount / ABS(sub_aml.total_per_account)
                        END as matched_percentage
                   FROM account_partial_reconcile part
                   LEFT JOIN account_move_line aml ON aml.id = part.debit_move_id
                   LEFT JOIN (SELECT move_id, account_id, ABS(SUM(balance)) AS total_per_account
                                FROM account_move_line
                                GROUP BY move_id, account_id) sub_aml
                            ON (aml.account_id = sub_aml.account_id AND sub_aml.move_id=aml.move_id)
                   LEFT JOIN account_move am ON aml.move_id = am.id,""" + tables + """
                   WHERE part.credit_move_id = "account_move_line".id
                    AND "account_move_line".user_type_id IN %s
                    AND """ + where_clause + """
                 UNION ALL
                 SELECT aml.move_id, \"account_move_line\".date,
                        CASE WHEN (aml.balance = 0 OR sub_aml.total_per_account = 0)
                            THEN 0
                            ELSE part.amount / ABS(sub_aml.total_per_account)
                        END as matched_percentage
                   FROM account_partial_reconcile part
                   LEFT JOIN account_move_line aml ON aml.id = part.credit_move_id
                   LEFT JOIN (SELECT move_id, account_id, ABS(SUM(balance)) AS total_per_account
                                FROM account_move_line
                                GROUP BY move_id, account_id) sub_aml
                            ON (aml.account_id = sub_aml.account_id AND sub_aml.move_id=aml.move_id)
                   LEFT JOIN account_move am ON aml.move_id = am.id,""" + tables + """
                   WHERE part.debit_move_id = "account_move_line".id
                    AND "account_move_line".user_type_id IN %s
                    AND """ + where_clause + """
               )
               SELECT aml.id, ref.date, aml.name,
                 CASE WHEN aml.debit > 0 THEN ref.matched_percentage * aml.debit ELSE 0 END AS debit_cash_basis,
                 CASE WHEN aml.credit > 0 THEN ref.matched_percentage * aml.credit ELSE 0 END AS credit_cash_basis,
                 aml.move_id, aml.account_id, aml.journal_id,
                 ref.matched_percentage * aml.balance AS balance_cash_basis,
                 aml.amount_residual, aml.partner_id, aml.reconciled, aml.company_id, aml.company_currency_id, aml.amount_currency, aml.balance, aml.user_type_id, aml.analytic_account_id
                FROM account_move_line aml
                RIGHT JOIN payment_table ref ON aml.move_id = ref.move_id
                WHERE journal_id NOT IN (SELECT id FROM account_journal WHERE type in ('cash', 'bank'))
                  AND aml.move_id IN (SELECT DISTINCT move_id FROM account_move_line WHERE user_type_id IN %s)
              )
            ) """
            params = [tuple(user_types.ids)] + where_params + [tuple(user_types.ids)] + where_params + [tuple(user_types.ids)] + where_params + [tuple(user_types.ids)]
        return sql, params

    def _do_query_unaffected_earnings(self, options, line_id, company=None):
        ''' Compute the sum of ending balances for all accounts that are of a type that does not bring forward the balance in new fiscal years.
            This is needed to balance the trial balance and the general ledger reports (to have total credit = total debit)
        '''

        select = '''
        SELECT COALESCE(SUM("account_move_line".balance), 0),
               COALESCE(SUM("account_move_line".amount_currency), 0),
               COALESCE(SUM("account_move_line".debit), 0),
               COALESCE(SUM("account_move_line".credit), 0)'''
        if options.get('cash_basis'):
            select = select.replace('debit', 'debit_cash_basis').replace('credit', 'credit_cash_basis').replace('balance', 'balance_cash_basis')
        select += " FROM %s WHERE %s"
        user_types = self.env['account.account.type'].search([('type', 'in', ('receivable', 'payable'))])
        with_sql, with_params = self._get_with_statement(user_types)
        
        aml_domain = [('currency_id','in',self._context.get('currency_ids'))]
        
        if company:
            aml_domain += [('company_id', '=', company.id)]
            
        tables, where_clause, where_params = self.env['account.move.line']._query_get(domain=aml_domain)
        query = select % (tables, where_clause)
        self.env.cr.execute(with_sql + query, with_params + where_params)
        res = self.env.cr.fetchone()
        date = self._context.get('date_to') or fields.Date.today()
        
        selected_company_ids = self._context.get('allowed_company_ids', self.env.company.ids)
    
        if(selected_company_ids and selected_company_ids[0]):
            user_company = self.env['res.company'].browse(selected_company_ids[0])
        else:
            user_company = self.env.company
            
        currency_convert = lambda x: company and company.currency_id._convert(x, user_company.currency_id, user_company, date) or x
        return {'balance': currency_convert(res[0]), 'amount_currency': res[1], 'debit': currency_convert(res[2]), 'credit': currency_convert(res[3])}

    def _do_query(self, options, line_id, anayltic_line_id, group_by_account=True, limit=False):
        if(isinstance(line_id,int)):
            line_id = str(line_id)
        else:
            line_id =  ",".join([str(x) for x in line_id])
        
        if(isinstance(anayltic_line_id,int)):
            anayltic_line_id = str(anayltic_line_id)
        else:
            anayltic_line_id =  ",".join([str(x) for x in anayltic_line_id])
        
        if group_by_account:
            select = "SELECT \"account_move_line\".account_id"
            select += ',COALESCE(SUM(\"account_move_line\".debit-\"account_move_line\".credit), 0),SUM(\"account_move_line\".amount_currency),SUM(\"account_move_line\".debit),SUM(\"account_move_line\".credit)'
            if anayltic_line_id:
                select += " , \"account_move_line\".analytic_account_id"
            if options.get('cash_basis'):
                select = select.replace('debit', 'debit_cash_basis').replace('credit', 'credit_cash_basis').replace('balance', 'balance_cash_basis')
        else:
            if anayltic_line_id:
                select = "SELECT \"account_move_line\".id, \"account_move_line\".analytic_account_id"
            else:
                select = "SELECT \"account_move_line\".id"
        sql = "%s FROM %s WHERE %s%s"
        if group_by_account:
            if anayltic_line_id:
                sql +=  "GROUP BY \"account_move_line\".account_id, \"account_move_line\".analytic_account_id"
            else:
                sql +=  "GROUP BY \"account_move_line\".account_id"
        else:
            if anayltic_line_id:
                sql += " GROUP BY \"account_move_line\".id, \"account_move_line\".analytic_account_id"
            else:
                sql += " GROUP BY \"account_move_line\".id"
            sql += " ORDER BY MAX(\"account_move_line\".date),\"account_move_line\".id"
            if limit and isinstance(limit, int):
                sql += " LIMIT " + str(limit)
        user_types = self.env['account.account.type'].search([('type', 'in', ('receivable', 'payable'))])
        with_sql, with_params = self._get_with_statement(user_types)
        tables, where_clause, where_params = self.env['account.move.line']._query_get(domain=[('currency_id','in',self._context.get('currency_ids'))])
        line_clause = line_id and ' AND \"account_move_line\".account_id  in (' + str(line_id) + ')' or ''
        line_clause += self.partner_id and ' AND account_move_line.partner_id = ' +  str(self.partner_id.id) or ''
        line_clause += anayltic_line_id and ' AND \"account_move_line\".analytic_account_id  in (' + str(anayltic_line_id) + ')' or ''
        query = sql % (select, tables, where_clause, line_clause)
        self.env.cr.execute(with_sql + query, with_params + where_params)
        results = self.env.cr.fetchall()
        return results

    def _do_query_group_by_account(self, options, line_id, analytic_line_id):
        results = self._do_query(options, line_id, analytic_line_id, group_by_account=True, limit=False)
        
        
        selected_company_ids = self._context.get('allowed_company_ids', self.env.company.ids)
        
        if(selected_company_ids and selected_company_ids[0]):
            user_company = self.env['res.company'].browse(selected_company_ids[0])
        else:
            user_company = self.env.company
        
        used_currency = user_company.currency_id    
        company = self.env['res.company'].browse(self._context.get('company_id')) or user_company
        date = self._context.get('date_to') or fields.Date.today()
        def build_converter(currency):
            def convert(amount):
                return currency._convert(amount, used_currency, user_company, date, round=False)
            return convert

        compute_table = {
            a.id: build_converter(a.company_id.currency_id)
            for a in self.env['account.account'].browse([k[0] for k in results])
        }
        results = dict([(
            k[0], {
                'balance': compute_table[k[0]](k[1]) if k[0] in compute_table else k[1],
                'amount_currency': k[2],
                'debit': compute_table[k[0]](k[3]) if k[0] in compute_table else k[3],
                'credit': compute_table[k[0]](k[4]) if k[0] in compute_table else k[4],
            }
        ) for k in results])
        return results

    def _group_by_account_id(self, options, line_id, analytic_line_id):
        accounts = {}
        results = self._do_query_group_by_account(options, line_id, analytic_line_id)
        initial_bal_date_to = fields.Date.from_string(self.env.context['date_from_aml']) + timedelta(days=-1)
        initial_bal_results = self.with_context(date_to=initial_bal_date_to.strftime('%Y-%m-%d'))._do_query_group_by_account(options, line_id, analytic_line_id)

        context = self.env.context
        
        selected_company_ids = self._context.get('allowed_company_ids', self.env.company.ids)
    
        if(selected_company_ids and selected_company_ids[0]):
            user_company = self.env['res.company'].browse(selected_company_ids[0])
        else:
            user_company = self.env.company
            
        last_day_previous_fy = user_company.compute_fiscalyear_dates(fields.Date.from_string(self.env.context['date_from_aml']))['date_from'] + timedelta(days=-1)
        unaffected_earnings_per_company = {}
        
        company_ids = [user_company]
        for cid in company_ids:
            company = self.env['res.company'].search([('id','=',cid.id)])
            unaffected_earnings_per_company[company] = self.with_context(date_to=last_day_previous_fy.strftime('%Y-%m-%d'), date_from=False)._do_query_unaffected_earnings(options, line_id, company)

        unaff_earnings_treated_companies = set()
        unaffected_earnings_type = self.env.ref('account.data_unaffected_earnings')
        for account_id, result in results.items():
            account = self.env['account.account'].browse(account_id)
            accounts[account] = result
            accounts[account]['initial_bal'] = initial_bal_results.get(account.id, {'balance': 0, 'amount_currency': 0, 'debit': 0, 'credit': 0})
            if account.user_type_id == unaffected_earnings_type and account.company_id not in unaff_earnings_treated_companies:
                #add the benefit/loss of previous fiscal year to unaffected earnings accounts
                unaffected_earnings_results = unaffected_earnings_per_company[account.company_id]
                for field in ['balance', 'debit', 'credit']:
                    accounts[account]['initial_bal'][field] += unaffected_earnings_results[field]
                    accounts[account][field] += unaffected_earnings_results[field]
                unaff_earnings_treated_companies.add(account.company_id)
            #use query_get + with statement instead of a search in order to work in cash basis too
            aml_ctx = {}
            if context.get('date_from_aml'):
                aml_ctx = {
                    'strict_range': True,
                    'date_from': context['date_from_aml'],
                }
            aml_ids = self.with_context(**aml_ctx)._do_query(options, account_id, analytic_line_id, group_by_account=False)
            aml_ids = [x[0] for x in aml_ids]
            
            accounts[account]['total_lines'] = len(aml_ids)
            accounts[account]['lines'] = self.env['account.move.line'].search([('id','in',aml_ids), ('currency_id','in',self._context.get('currency_ids'))], order="date asc")

        return accounts
    
    def get_partner_account_jv(self):
        """
        Get Journal entries that are posted between date range from and date to
        Calculate initial balance and retrieve journal items grouped by currency
        """
        report_currency_list = []
        
        dt_from = self.from_date
        dt_to = self.to_date
        
        options = {}
    
        selected_currency_ids = self.currency_ids if len(self.currency_ids.ids) > 0 else self.env['res.currency'].search([('active','=',True)])
        log.info("Getting data for selected currencies: %s", selected_currency_ids.mapped('name'))
        
        selected_company_ids = self._context.get('allowed_company_ids', self.env.company.ids)
    
        if(selected_company_ids and selected_company_ids[0]):
            user_company = self.env['res.company'].browse(selected_company_ids[0])
        else:
            user_company = self.env.company
        
        for currency in selected_currency_ids:
            currency_id = currency.id
            currency_ids = [currency_id]
            if currency_id == user_company.currency_id.id:
                currency_ids = [currency_id, False]
            
            initial_balance_list = []
            total_balance_list = []
            account_move_lines_list = []
            account_move_lines_ids_list = []
            
            initial_balance = 0
            grouped_accounts = self.with_context(date_from_aml=dt_from, state="posted",
                date_from=dt_from and user_company.compute_fiscalyear_dates(fields.Date.from_string(dt_from))['date_from'] or None,
                date_to=dt_to, currency_ids=currency_ids, line_id=self.account_id.ids)._group_by_account_id(options, self.account_id.ids, self.analytic_account_ids.ids)
           
            sorted_accounts = sorted(grouped_accounts, key=lambda a: a.code)
            
            for account in sorted_accounts:
                if currency.id == user_company.currency_id.id:
                    initial_balance += grouped_accounts[account]['initial_bal']['balance'] or 0.0

                else:
                    initial_balance += grouped_accounts[account]['initial_bal']['amount_currency'] or 0.0
                
            balance = initial_balance
            total_balance = balance
            
            for account in sorted_accounts:
                for ml in grouped_accounts[account]['lines']:
                    amount_balance = ml.debit - ml.credit
                    
                    if not ml.currency_id or ml.currency_id.id == user_company.currency_id.id:
                        ml_debit = ml.debit
                        ml_credit = ml.credit
                    else:
                        ml_debit = (ml.amount_currency > 0 and ml.amount_currency or 0.0)
                        ml_credit = (ml.amount_currency < 0 and -ml.amount_currency or 0.0)
                    
                    
                    balance = balance + (ml_debit if ml_debit > 0 else -ml_credit)
                    
                    append_line = False
                    if not self._context.get("print_general_ledger") and not user_company.remove_exchange_journal:
                        append_line = True
                    
                    elif user_company.remove_exchange_journal and ml.move_id.journal_id.id != user_company.currency_exchange_journal_id.id:
                        append_line = True
                    
                    if append_line and not user_company.add_invoice_customer :
                           account_move_lines_list.append({
                            "date": ml.move_id.date,
                            "document": ml.move_id.name,
                            "description": ml.name,
                            "debit": ml_debit,
                            "credit": ml_credit,
                            "balance": balance
                        })
                    if append_line and  user_company.add_invoice_customer:
                           account_move_lines_list.append({
                              "date": ml.move_id.date,
                                "document": ml.move_id.name,
                                "description": ml.name,
                                "debit": ml_debit,
                                "credit": ml_credit,
                                "balance": balance,
                                "ref": ml.ref,
                                "invoice_date": ml.move_id.invoice_date
                            
                        })
                    
                        
                        
                    account_move_lines_ids_list.extend(grouped_accounts[account]['lines'].ids)
                    total_balance += (ml_debit - ml_credit)
                 
            
            initial_balance_list.append(initial_balance)
            total_balance_list.append(total_balance)
            
            if(sum(initial_balance_list) > 0 or len(account_move_lines_list) > 0 or sum(total_balance_list)):
                report_currency_list.append({
                    'initial_balance': sum(initial_balance_list),
                    'total_balance': sum(total_balance_list),
                    'account_move_lines_list': account_move_lines_list,
                    'account_move_lines_ids_list': account_move_lines_ids_list,
                    'currency_id': currency
                })
        
        return report_currency_list
    
    def _check_account_selected(self):
        if not self.account_id and not self.analytic_account_ids:
            raise UserError(_("You should either select account or analytic account"))
     
     
    def print_amount_currency_gl(self):
        """
        """
        self._check_account_selected()
        report = self.env.ref('lb_account_reports.report_amount_currency_gl')
        
        return report.report_action(self)
    
    def print_amount_currency(self):
        """
        """
        self._check_account_selected()
        report = self.env.ref('lb_account_reports.report_amount_currency')
        
        return report.report_action(self)
    
    def preview_amount_currency(self):
        """
        """
        self._check_account_selected()
        account_move_list_ids = []
        for account_move_id in self.get_partner_account_jv():
            account_move_list_ids.extend(account_move_id.get('account_move_lines_ids_list', []))
        
        action = self.env.ref('account.action_account_moves_all_a').read()[0]
        action['domain'] = [('id','in', account_move_list_ids)]
        
        return action
    
    def export_xlsx(self):
        """
        Returns a report to print amount currency
        """
        self._check_account_selected()
        log.debug('>> Calling the Amount Currency EXPORT Report')
        account_currencies = []
        
        report_currency_list = self.get_partner_account_jv()
       
        tmp_dir = os.path.join(config.get('data_dir'), 'tmp')
        if not os.path.exists(tmp_dir):
            os.makedirs(tmp_dir)
            
        ams_time = datetime.datetime.now()
        file_date = self.from_date.strftime('%m-%d-%Y-%H.%M.%S')
        filename = os.path.join(tmp_dir, 'Account Currency Report'+ '-' + file_date +'.xlsx')
        
        workbook = xlsxwriter.Workbook(filename)
        worksheet = workbook.add_worksheet()
        
        worksheet.set_default_row(20)
        
        i = 0
        
        header_format = workbook.add_format({'bold': True, 'font_size': 11})
        header_format.set_align('center')
        header_format.set_align('vcenter')
        header_format.set_border()
            
        header_without_border_format = workbook.add_format({'bold': True, 'font_size': 11})
        header_without_border_format.set_align('center')
        header_without_border_format.set_align('vcenter')
            
        info_header_columns = ['Partner:' if self.partner_id else '' , '', 'Account: ' if self.account_id else '', '', 'Analytic Account: ' if self.analytic_account_ids else '']
        info_header_val_columns = [self.partner_id.contact_address.replace(' \n', ', ') if self.partner_id else '', '', ", ".join([str(x.code + ' ' + x.name) for x in self.account_id]) if self.account_id else '', '', ", ".join([str(x.name) for x in self.analytic_account_ids]) if self.analytic_account_ids else '']
            
        info_columns_names = ['Date From: ', datetime.datetime.strftime(self.from_date, "%Y-%m-%d"), 'Date To: ', datetime.datetime.strftime(self.to_date, "%Y-%m-%d")]
            
        for idx, col_name in enumerate(info_header_columns):
            worksheet.set_column(idx, idx, 30)
            worksheet.write(i, idx, col_name, header_without_border_format)

        for idx, col_name in enumerate(info_header_val_columns):
            worksheet.set_column(idx, idx, 30)
            worksheet.write(i + 1, idx, col_name, header_without_border_format)        
        for idx, col_name in enumerate(info_columns_names):
            worksheet.set_column(idx+1, idx+1, 30)
            worksheet.write(i + 2, idx+1, col_name, header_without_border_format)
                
        for list in report_currency_list:
            account_currencies = list.get('account_move_lines_list')
            currency = list.get('currency_id').name if list.get('currency_id') else ''
            
            worksheet.set_column(2, 2, 30)
            worksheet.write(i + 4, 2, "Currency:", header_without_border_format)
            worksheet.set_column(3, 3, 30)
            worksheet.write(i + 4, 3, currency, header_without_border_format)
        
            columns_names = ['Date', 'Document', 'Description', 'Debit', 'Credit', 'Balance']
            second_columns_names = ['', '', 'Previous Balance', list.get('initial_balance') if list.get("initial_balance") > 0 else '', abs(list.get('initial_balance')) if not list.get("initial_balance") > 0 else 0.0, '']
            
            for idx, col_name in enumerate(columns_names):
                worksheet.set_column(idx, idx, 30)
                worksheet.write(i+5, idx, col_name, header_format)
                
            for idx, col_name in enumerate(second_columns_names):
                worksheet.set_column(idx, idx, 30)
                worksheet.write(i+6, idx, col_name, header_format)
            
            cell_format = workbook.add_format({'bold': True,'font_size': 11})
            cell_format.set_align('center')
            cell_format.set_align('vcenter')
            cell_format.set_border()
            worksheet.set_row(1, 80)
            num_format = workbook.add_format({'num_format': 'yyyy-mm-dd'})
            num_format.set_align('center')
            num_format.set_align('vcenter')
            num_format.set_border()
            
            records = []
            row_idx = i + 7
            
            for idx, key in enumerate(account_currencies):
                account_currency = account_currencies[idx]
                date = account_currency.get('date')
                document = account_currency.get('document')
                description = account_currency.get('description')
                debit = account_currency.get('debit')
                credit = account_currency.get('credit')
                balance = account_currency.get('balance')
                
                row = [date, 
                       document, description, debit, credit, balance]
                        
                records.append(row)
                
                for i in range(0, len(row)): 
                    if i == 0:
                        worksheet.write(row_idx, i, row[i], num_format)  
                    else:
                        worksheet.write(row_idx, i, row[i], cell_format) 
                row_idx = row_idx + 1
                
            i = i+2
            
        workbook.close()
        
        fp = open(filename, "rb")
        data = fp.read()
        data64 = base64.encodestring(data)
          
        fp.close()
        os.remove(filename)
        
        exported_file_name = 'amount-currency-%s.xlsx' % (file_date) 
        attach_doc = self.env['ir.attachment'].create({'name':exported_file_name , 'datas':data64, 'type':'binary'})
        
        return {
                   'type': 'ir.actions.act_url',
                   'url': '/web/content/%s?download=true' %(str(attach_doc.id)), 
                   'target': 'new'
               }