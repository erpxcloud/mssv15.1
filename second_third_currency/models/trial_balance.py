# -*- coding: utf-8 -*-

from odoo import models, api, _, fields
from datetime import datetime, timedelta
from odoo.tools.misc import format_date
from odoo.exceptions import UserError
import logging
import warnings

_logger = logging.getLogger(__name__)

try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    # TODO saas-17: remove the try/except to directly import from misc
    import xlsxwriter
import io



class ReportAccountCoa(models.AbstractModel):
    _inherit = "account.coa.report"

    filter_currencys = True

    @api.model
    def _get_options(self, previous_options=None):
        res = super(ReportAccountCoa, self)._get_options(previous_options)
        if self.filter_currencys :
            company = self.env['res.company'].search([('id', '=', self.env.company.id)])
            second = self.env['res.currency'].search([('id', '=', company.second_currency.id)])
            third = self.env['res.currency'].search([('id', '=', company.third_currency.id)])
            currencies = self.env['res.currency'].search([('id','in', [second.id, third.id,self.env.company.currency_id])])
            _logger.debug("currencies")
            res['currenciess'] = [{'id': c.id, 'name': c.name, 'selected': False} for c in currencies]
            if 'curr' in self._context:
                for c in res['currenciess']:
                    if c['id'] == self._context.get('curr'):
                        c['selected'] = True
            else:
                for c in res['currenciess']:
                    if c['id'] == self.env.company.currency_id:
                        c['selected'] = True
            res['currencys'] = True
        return res
    
    @api.model
    def _get_lines(self, options, line_id=None):
        company = self.env['res.company'].search([('id', '=', self.env.company.id)])
        second = self.env['res.currency'].search([('id', '=', company.second_currency.id)])
        third = self.env['res.currency'].search([('id', '=', company.third_currency.id)])
        if self._context.get('curr') == second.id:
            cur = self.env['res.currency'].browse(self._context.get('curr'))
            new_options = options.copy()
            new_options['unfold_all'] = True
            options_list = self._get_options_periods_list(new_options)
            accounts_results, taxes_results = self.env['account.general.ledger']._do_query(options_list, fetch_lines=False)
            company_currency = self.env.company.currency_id
            lines = []
            totals = [0.0] * (2 * (len(options_list) + 2))

            # Add lines, one per account.account record.
            for account, periods_results in accounts_results:
                sums = []
                account_balance = 0.0
                for i, period_values in enumerate(reversed(periods_results)):
                    account_sum = period_values.get('sum', {})
                    account_un_earn = period_values.get('unaffected_earnings', {})
                    account_init_bal = period_values.get('initial_balance', {})

                    if i == 0:
                        # Append the initial balances.
                        initial_balance = account_init_bal.get('second_balance', 0.0) + account_un_earn.get('second_balance', 0.0)
                        sums += [
                            initial_balance > 0 and initial_balance or 0.0,
                            initial_balance < 0 and -initial_balance or 0.0,
                        ]
                        account_balance += initial_balance

                    # Append the debit/credit columns.
                    debit = account_sum.get('second_debit_id', 0.0) - account_init_bal.get('second_debit_id', 0.0)
                    credit = account_sum.get('second_credit_id', 0.0) - account_init_bal.get('second_credit_id', 0.0)
#                     debit = self.env.company.currency_id._compute(self.env.company.currency_id,cur,debit)
#                     credit = self.env.company.currency_id._compute(self.env.company.currency_id,cur,credit)
                    sums += [
                        debit,
                        credit,self.env.company
                    ]
                    account_balance += sums[-2] - sums[-1]

                # Append the totals.
                sums += [
                    account_balance > 0 and account_balance or 0.0,
                    account_balance < 0 and -account_balance or 0.0,
                ]

                # account.account report line.
                columns = []
                for i, value in enumerate(sums):
                    # Update totals.
                    #value = cur._compute(self.env.user.company_id.currency_id,cur,value)
                    totals[i] += value

                    # Create columns.
                    columns.append({'name': self.format_value(value, currency=cur, blank_if_zero=True), 'class': 'number', 'no_format_name': value})

                name = account.name_get()[0][1]

                lines.append({
                    'id': account.id,
                    'name': name,
                    'title_hover': name,
                    'columns': columns,
                    'unfoldable': False,
                    'caret_options': 'account.account',
                    'class': 'o_account_searchable_line o_account_coa_column_contrast',
                })

            # Total report line.
            lines.append({
                 'id': 'grouped_accounts_total',
                 'name': _('Total'),
                 'class': 'total o_account_coa_column_contrast',
                 'columns': [{'name': self.format_value(total, currency=cur), 'class': 'number'} for total in totals],
                 'level': 1,
            })
            return lines
        elif self._context.get('curr') == third.id:
            cur = self.env['res.currency'].browse(self._context.get('curr'))
            new_options = options.copy()
            new_options['unfold_all'] = True
            options_list = self._get_options_periods_list(new_options)
            accounts_results, taxes_results = self.env['account.general.ledger']._do_query(options_list, fetch_lines=False)
            company_currency = self.env.company.currency_id
            lines = []
            totals = [0.0] * (2 * (len(options_list) + 2))

            # Add lines, one per account.account record.
            for account, periods_results in accounts_results:
                sums = []
                account_balance = 0.0
                for i, period_values in enumerate(reversed(periods_results)):
                    account_sum = period_values.get('sum', {})
                    account_un_earn = period_values.get('unaffected_earnings', {})
                    account_init_bal = period_values.get('initial_balance', {})

                    if i == 0:
                        # Append the initial balances.
                        initial_balance = account_init_bal.get('third_balance', 0.0) + account_un_earn.get('third_balance', 0.0)
                        sums += [
                            initial_balance > 0 and initial_balance or 0.0,
                            initial_balance < 0 and -initial_balance or 0.0,
                        ]
                        account_balance += initial_balance

                    # Append the debit/credit columns.
                    debit = account_sum.get('third_debit_id', 0.0) - account_init_bal.get('third_debit_id', 0.0)
                    credit = account_sum.get('third_credit_id', 0.0) - account_init_bal.get('third_credit_id', 0.0)
#                     debit = self.env.user.company_id.currency_id._compute(self.env.user.company_id.currency_id,cur,debit)
#                     credit = self.env.user.company_id.currency_id._compute(self.env.user.company_id.currency_id,cur,credit)
                    sums += [
                        debit,
                        credit,
                    ]
                    account_balance += sums[-2] - sums[-1]

                # Append the totals.
                sums += [
                    account_balance > 0 and account_balance or 0.0,
                    account_balance < 0 and -account_balance or 0.0,
                ]

                # account.account report line.
                columns = []
                for i, value in enumerate(sums):
                    # Update totals.
                    #value = cur._compute(self.env.user.company_id.currency_id,cur,value)
                    totals[i] += value

                    # Create columns.
                    columns.append({'name': self.format_value(value, currency=cur, blank_if_zero=True), 'class': 'number', 'no_format_name': value})

                name = account.name_get()[0][1]

                lines.append({
                    'id': account.id,
                    'name': name,
                    'title_hover': name,
                    'columns': columns,
                    'unfoldable': False,
                    'caret_options': 'account.account',
                    'class': 'o_account_searchable_line o_account_coa_column_contrast',
                })

            # Total report line.
            lines.append({
                 'id': 'grouped_accounts_total',
                 'name': _('Total'),
                 'class': 'total o_account_coa_column_contrast',
                 'columns': [{'name': self.format_value(total, currency=cur), 'class': 'number'} for total in totals],
                 'level': 1,
            })
            return lines
        else:
            _logger.debug("MA FET BL IF")
            cur = self.env['res.currency'].browse(self._context.get('curr'))
            new_options = options.copy()
            new_options['unfold_all'] = True
            options_list = self._get_options_periods_list(new_options)
            accounts_results, taxes_results = self.env['account.general.ledger']._do_query(options_list, fetch_lines=False)
            company_currency = self.env.company.currency_id
            lines = []
            totals = [0.0] * (2 * (len(options_list) + 2))

            # Add lines, one per account.account record.
            for account, periods_results in accounts_results:
                sums = []
                account_balance = 0.0
                for i, period_values in enumerate(reversed(periods_results)):
                    account_sum = period_values.get('sum', {})
                    account_un_earn = period_values.get('unaffected_earnings', {})
                    account_init_bal = period_values.get('initial_balance', {})

                    if i == 0:
                        # Append the initial balances.
                        initial_balance = account_init_bal.get('balance', 0.0) + account_un_earn.get('balance', 0.0)
                        sums += [
                            initial_balance > 0 and initial_balance or 0.0,
                            initial_balance < 0 and -initial_balance or 0.0,
                        ]
                        account_balance += initial_balance

                    # Append the debit/credit columns.
                    debit = account_sum.get('debit', 0.0) - account_init_bal.get('debit', 0.0)
                    credit = account_sum.get('credit', 0.0) - account_init_bal.get('credit', 0.0)
#                     debit = self.env.user.company_id.currency_id._compute(self.env.user.company_id.currency_id,cur,debit)
#                     credit = self.env.user.company_id.currency_id._compute(self.env.user.company_id.currency_id,cur,credit)
                    sums += [
                        debit,
                        credit,
                    ]
                    account_balance += sums[-2] - sums[-1]

                # Append the totals.
                sums += [
                    account_balance > 0 and account_balance or 0.0,
                    account_balance < 0 and -account_balance or 0.0,
                ]

                # account.account report line.
                columns = []
                for i, value in enumerate(sums):
                    # Update totals.
                    #value = cur._compute(self.env.user.company_id.currency_id,cur,value)
                    totals[i] += value

                    # Create columns.
                    columns.append({'name': self.format_value(value, currency=cur, blank_if_zero=True), 'class': 'number', 'no_format_name': value})

                name = account.name_get()[0][1]

                lines.append({
                    'id': account.id,
                    'name': name,
                    'title_hover': name,
                    'columns': columns,
                    'unfoldable': False,
                    'caret_options': 'account.account',
                    'class': 'o_account_searchable_line o_account_coa_column_contrast',
                })

            # Total report line.
            lines.append({
                 'id': 'grouped_accounts_total',
                 'name': _('Total'),
                 'class': 'total o_account_coa_column_contrast',
                 'columns': [{'name': self.format_value(total, currency=cur), 'class': 'number'} for total in totals],
                 'level': 1,
            })
            return lines
        return super(ReportAccountCoa, self)._get_lines(options, line_id)

#     def get_pdf(self, options, minimal_layout=True):
#         for opt in options['currenciess']:
#             if opt['selected'] and self.env['res.currency'].browse(opt['id']) != self.env.user.company_id.currency_id:
#                 return super(report_account_coa, self.with_context(curr = opt['id'])).get_pdf(options,minimal_layout)
#         return super(report_account_coa, self).get_pdf(options,minimal_layout)
    
    def get_xlsx(self, options, response=None):
        for opt in options['currenciess']:
            if opt['selected'] and self.env['res.currency'].browse(opt['id']) != self.env.user.company_id.currency_id:
                return super(ReportAccountCoa, self.with_context(curr = opt['id'])).get_xlsx(options,response)
        return super(ReportAccountCoa, self).get_xlsx(options,response)



   
