# -*- coding: utf-8 -*-
import time
from odoo import api, fields, models, _, http
from odoo.http import request
from odoo.exceptions import UserError
from odoo.tools import float_is_zero
from datetime import datetime
from dateutil.relativedelta import relativedelta

import logging
log = logging.getLogger(__name__)
            
class report_account_aged_receivable(models.AbstractModel):
    _inherit = "account.aged.receivable"
    
    filter_account = True

    def get_search_data(self, values):
        cids = request.httprequest.cookies.get('cids', str(request.env.user.company_id.id))
        company_ids = [int(cid) for cid in cids.split(',')]
        company = self.env['res.company'].browse(company_ids[0])
        
        accounts = []
        for value in values:
            accounts += self.env['account.account'].search([('display_name_computed', 'ilike', value), ('company_id', '=', company.id)]).ids
          
        request.session["account_ids"] = accounts
        request.session["search_values"] = values
            
    def clear_data(self):
        if request.session.get("account_ids"):
            del request.session["account_ids"]
            
        if request.session.get("search_values"):
            del request.session["search_values"]
            
class report_account_aged_payable(models.AbstractModel):
    _inherit = "account.aged.payable"
    
    filter_account = True
    
    def get_search_data(self, values):
        cids = request.httprequest.cookies.get('cids', str(request.env.user.company_id.id))
        company_ids = [int(cid) for cid in cids.split(',')]
        company = self.env['res.company'].browse(company_ids[0])
        
        accounts = []
        for value in values:
            accounts += self.env['account.account'].search([('display_name_computed', 'ilike', value), ('company_id', '=', company.id)]).ids
           
        request.session["account_ids"] = accounts
        request.session["search_values"] = values
            
    def clear_data(self):
        if request.session.get("account_ids"):
            del request.session["account_ids"]
            
        if request.session.get("search_values"):
            del request.session["search_values"]

class ReportAgedPartnerBalance(models.AbstractModel):
    _inherit = 'report.account.report_agedpartnerbalance'
    
        
    def _get_partner_move_lines(self, account_type, date_from, target_move, period_length):
        # This method can receive the context key 'include_nullified_amount' {Boolean}
        # Do an invoice and a payment and unreconcile. The amount will be nullified
        # By default, the partner wouldn't appear in this report.
        # The context key allow it to appear
        # In case of a period_length of 30 days as of 2019-02-08, we want the following periods:
        # Name       Stop         Start
        # 1 - 30   : 2019-02-07 - 2019-01-09
        # 31 - 60  : 2019-01-08 - 2018-12-10
        # 61 - 90  : 2018-12-09 - 2018-11-10
        # 91 - 120 : 2018-11-09 - 2018-10-11
        # +120     : 2018-10-10
        ctx = self._context
        periods = {}
        date_from = fields.Date.from_string(date_from)
        start = date_from
        for i in range(5)[::-1]:
            stop = start - relativedelta(days=period_length)
            period_name = str((5-(i+1)) * period_length + 1) + '-' + str((5-i) * period_length)
            period_stop = (start - relativedelta(days=1)).strftime('%Y-%m-%d')
            if i == 0:
                period_name = '+' + str(4 * period_length)
            periods[str(i)] = {
                'name': period_name,
                'stop': period_stop,
                'start': (i!=0 and stop.strftime('%Y-%m-%d') or False),
            }
            start = stop

        res = []
        total = []
        partner_clause = ''
        cr = self.env.cr

        cids = request.httprequest.cookies.get('cids', str(request.env.user.company_id.id))
        company_ids = [int(cid) for cid in cids.split(',')]
        user_company = self.env['res.company'].browse(company_ids[0])
        
        user_currency = user_company.currency_id
        
        context = self.env.context
        selected_multi_currency_id = context.get('selected_multi_currency')
        if selected_multi_currency_id:
            selected_multi_currency_id = int(selected_multi_currency_id)
            if user_company.second_currency_id.id == selected_multi_currency_id:
                user_currency = user_company.second_currency_id
            elif user_company.third_currency_id.id == selected_multi_currency_id:
                user_currency = user_company.third_currency_id
                
        company_ids = self._context.get('company_ids') or [user_company.id]
        move_state = ['draft', 'posted']
        if target_move == 'posted':
            move_state = ['posted']
        arg_list = (tuple(move_state), tuple(account_type))
        #build the reconciliation clause to see what partner needs to be printed
        reconciliation_clause = '(l.reconciled IS FALSE)'
        cr.execute('SELECT debit_move_id, credit_move_id FROM account_partial_reconcile where max_date > %s', (date_from,))
        reconciled_after_date = []
        for row in cr.fetchall():
            reconciled_after_date += [row[0], row[1]]
        if reconciled_after_date:
            reconciliation_clause = '(l.reconciled IS FALSE OR l.id IN %s)'
            arg_list += (tuple(reconciled_after_date),)
        if ctx.get('partner_ids'):
            partner_clause = 'AND (l.partner_id IN %s)'
            arg_list += (tuple(ctx['partner_ids'].ids),)
        if ctx.get('account_ids'):
            partner_clause += 'AND (l.account_id IN %s)'
            arg_list += (tuple(ctx['account_ids'].ids),)
        if request.session.get("account_ids") and len(request.session.get("account_ids")) > 0:
            account_ids_list = request.session.get("account_ids")
            partner_clause += 'AND (l.account_id IN %s)'
            arg_list += (tuple(account_ids_list),)
        if ctx.get('partner_categories'):
            partner_clause += 'AND (l.partner_id IN %s)'
            partner_ids = self.env['res.partner'].search([('category_id', 'in', ctx['partner_categories'].ids)]).ids
            arg_list += (tuple(partner_ids or [0]),)
        arg_list += (date_from, tuple(company_ids))

            
        query = '''
            SELECT DISTINCT l.partner_id, res_partner.name AS name, UPPER(res_partner.name) AS UPNAME, CASE WHEN prop.value_text IS NULL THEN 'normal' ELSE prop.value_text END AS trust
            FROM account_move_line AS l
              LEFT JOIN res_partner ON l.partner_id = res_partner.id
              LEFT JOIN ir_property prop ON (prop.res_id = 'res.partner,'||res_partner.id AND prop.name='trust' AND prop.company_id=%s),
              account_account, account_move am
              
            WHERE (l.account_id = account_account.id)
                AND (l.move_id = am.id)
                AND (am.state IN %s)
                AND (account_account.internal_type IN %s)
                AND ''' + reconciliation_clause + partner_clause + '''
                AND (l.date <= %s)
                AND l.company_id IN %s
            ORDER BY UPPER(res_partner.name)'''
        arg_list = (user_company.id,) + arg_list
        cr.execute(query, arg_list)

        partners = cr.dictfetchall()
        # put a total of 0
        for i in range(7):
            total.append(0)

        # Build a string like (1,2,3) for easy use in SQL query
        partner_ids = [partner['partner_id'] for partner in partners if partner['partner_id']]
        lines = dict((partner['partner_id'] or False, []) for partner in partners)
        if not partner_ids:
            return [], [], {}

        # Use one query per period and store results in history (a list variable)
        # Each history will contain: history[1] = {'<partner_id>': <partner_debit-credit>}
        history = []
        arg_list = ''
        arg2_list = ''
        
        for i in range(5):
            partner_clause = ''
            account_clause = ''
            args_list = (tuple(move_state), tuple(account_type), tuple(partner_ids))
            if ctx.get('account_ids'):
                partner_clause = 'AND (l.account_id IN %s)'
                args_list += (tuple(ctx['account_ids'].ids),)
            if request.session.get("account_ids") and len(request.session.get("account_ids")) > 0:
                account_ids_list = request.session.get("account_ids")
                account_clause = ' AND (l.account_id IN %s)'
                args_list += (tuple(account_ids_list),)
                
            dates_query = '(COALESCE(l.date_maturity,l.date)'
            
            if periods[str(i)]['start'] and periods[str(i)]['stop']:
                dates_query += ' BETWEEN %s AND %s)'
                args_list += (periods[str(i)]['start'], periods[str(i)]['stop'])
            elif periods[str(i)]['start']:
                dates_query += ' >= %s)'
                args_list += (periods[str(i)]['start'],)
            else:
                dates_query += ' <= %s)'
                args_list += (periods[str(i)]['stop'],)
            args_list += (date_from, tuple(company_ids))

            query = '''SELECT l.id
                    FROM account_move_line AS l, account_account, account_move am
                    WHERE (l.account_id = account_account.id) AND (l.move_id = am.id)
                        AND (am.state IN %s)
                        AND (account_account.internal_type IN %s)
                        AND ((l.partner_id IN %s) OR (l.partner_id IS NULL))
                        ''' + partner_clause + '''
                        ''' + account_clause + '''
                        AND ''' + dates_query + '''
                    AND (l.date <= %s)
                    AND l.company_id IN %s
                    ORDER BY COALESCE(l.date_maturity, l.date)'''
            cr.execute(query, args_list)
            partners_amount = {}
            aml_ids = cr.fetchall()
            aml_ids = aml_ids and [x[0] for x in aml_ids] or []
            for line in self.env['account.move.line'].browse(aml_ids).with_context(prefetch_fields=False):
                partner_id = line.partner_id.id or False
                if partner_id not in partners_amount:
                    partners_amount[partner_id] = 0.0
                line_amount = line.company_id.currency_id._convert(line.balance, user_currency, user_company, date_from, round=False)
                if user_currency.is_zero(line_amount):
                    continue
                for partial_line in line.matched_debit_ids:
                    if partial_line.max_date <= date_from:
                        line_amount += partial_line.company_id.currency_id._convert(partial_line.amount, user_currency, user_company, date_from, round=False)
                for partial_line in line.matched_credit_ids:
                    if partial_line.max_date <= date_from:
                        line_amount -= partial_line.company_id.currency_id._convert(partial_line.amount, user_currency, user_company, date_from, round=False)
                
                if not user_company.currency_id.is_zero(line_amount):
                    partners_amount[partner_id] += line_amount
                    lines.setdefault(partner_id, [])
                    lines[partner_id].append({
                        'line': line,
                        'amount': line_amount,
                        'period': i + 1,
                        })
            history.append(partners_amount)
      
        # This dictionary will store the not due amount of all partners
        undue_amounts = {}
        partner_clause = ''
        partner_clause += 'AND (l.account_id in %s)' if ctx.get('account_ids') else ' '
        partner_clause += ' AND (l.account_id in %s)' if request.session.get("account_ids") and len(request.session.get("account_ids")) > 0 else ' '
        query = '''SELECT l.id
                FROM account_move_line AS l, account_account, account_move am
                WHERE (l.account_id = account_account.id) AND (l.move_id = am.id)
                    AND (am.state IN %s)
                    AND (account_account.internal_type IN %s)
                    AND (COALESCE(l.date_maturity,l.date) >= %s)\
                    AND ((l.partner_id IN %s) OR (l.partner_id IS NULL))
                AND (l.date <= %s)
                AND l.company_id IN %s
                ''' + partner_clause + '''
                ORDER BY COALESCE(l.date_maturity, l.date)'''
        args_list = (tuple(move_state), tuple(account_type), date_from, tuple(partner_ids), date_from, tuple(company_ids))
        
        if ctx.get('account_ids'):
            args_list += (tuple(ctx['account_ids'].ids),)
        if request.session.get("account_ids") and len(request.session.get("account_ids")) > 0:
            args_list += (tuple(request.session.get("account_ids")),)
        
        cr.execute(query, args_list)
        aml_ids = cr.fetchall()
        aml_ids = aml_ids and [x[0] for x in aml_ids] or []
        for line in self.env['account.move.line'].browse(aml_ids):
            partner_id = line.partner_id.id or False
            if partner_id not in undue_amounts:
                undue_amounts[partner_id] = 0.0
            line_amount = line.company_id.currency_id._convert(line.balance, user_currency, user_company, date_from)
            if user_currency.is_zero(line_amount):
                continue
            for partial_line in line.matched_debit_ids:
                if partial_line.max_date <= date_from:
                    line_amount += partial_line.company_id.currency_id._convert(partial_line.amount, user_currency, user_company, date_from)
            for partial_line in line.matched_credit_ids:
                if partial_line.max_date <= date_from:
                    line_amount -= partial_line.company_id.currency_id._convert(partial_line.amount, user_currency, user_company, date_from)
            
            if not user_company.currency_id.is_zero(line_amount):
                undue_amounts[partner_id] += line_amount
                lines.setdefault(partner_id, [])
                lines[partner_id].append({
                    'line': line,
                    'amount': line_amount,
                    'period': 6,
                })

        for partner in partners:
            if partner['partner_id'] is None:
                partner['partner_id'] = False
            at_least_one_amount = False
            values = {}
            undue_amt = 0.0
            if partner['partner_id'] in undue_amounts:  # Making sure this partner actually was found by the query
                undue_amt = undue_amounts[partner['partner_id']]

            total[6] = total[6] + undue_amt
            values['direction'] = undue_amt
                
            if not float_is_zero(values['direction'], precision_rounding=user_company.currency_id.rounding):
                at_least_one_amount = True

            for i in range(5):
                during = False
                if partner['partner_id'] in history[i]:
                    during = [history[i][partner['partner_id']]]
                # Adding counter
                total[(i)] = total[(i)] + (during and during[0] or 0)
                values[str(i)] = during and during[0] or 0.0
                if not float_is_zero(values[str(i)], precision_rounding=user_company.currency_id.rounding):
                    at_least_one_amount = True
            values['total'] = sum([values['direction']] + [values[str(i)] for i in range(5)])
            # Add for total
            total[(i + 1)] += values['total']
            values['partner_id'] = partner['partner_id']
            if partner['partner_id']:
                values['name'] = len(partner['name']) >= 45 and partner['name'][0:40] + '...' or partner['name']
                values['trust'] = partner['trust']
            else:
                values['name'] = _('Unknown Partner')
                values['trust'] = False

            if at_least_one_amount or (self._context.get('include_nullified_amount') and lines[partner['partner_id']]):
                res.append(values)
        return res, total, lines