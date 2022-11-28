# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _, http
from odoo.http import request
from odoo.tools.misc import formatLang, format_date
from odoo.osv import expression
import logging

log = logging.getLogger(__name__)

class account_bank_reconciliation_report(models.AbstractModel):
    _inherit = 'account.bank.reconciliation.report'

    def get_currency_rate(self, options):
        cids = request.httprequest.cookies.get('cids', str(request.env.user.company_id.id))
        company_ids = [int(cid) for cid in cids.split(',')]
        company = self.env['res.company'].browse(company_ids[0])
        
        currency_rate = self.env['res.currency.rate'].sudo().search([('company_id','=',company.id),
                                                                                  ('currency_id','=',company.currency_id.id)], 
                                                                                   limit=1, order="name desc")
            
        if options.get('selected_multi_currency'):
            selected_multi_currency = int(options.get('selected_multi_currency'))
            
            if selected_multi_currency == company.second_currency_id.id:
                currency_rate = self.env['res.currency.rate'].sudo().search([('company_id','=',company.id),
                                                                                       ('currency_id','=',company.second_currency_id.id)], 
                                                                                        limit=1, order="name desc")
            elif selected_multi_currency == company.third_currency_id.id:
                currency_rate = self.env['res.currency.rate'].sudo().search([('company_id','=',company.id), 
                                                                                  ('currency_id','=',company.third_currency_id.id)], 
                                                                                   limit=1, order="name desc")
                
        return currency_rate
    
    @api.model
    def _get_bank_rec_report_data(self, options, journal):
        # General data + setup
        rslt = {}

        accounts = journal.default_debit_account_id + journal.default_credit_account_id
        company = journal.company_id
        amount_field = 'amount_currency' if journal.currency_id else 'balance'
        states = ['posted']
        states += options.get('all_entries') and ['draft'] or []

        # Get total already accounted.
        self._cr.execute('''
            SELECT SUM(aml.''' + amount_field + ''')
            FROM account_move_line aml
            LEFT JOIN account_move am ON aml.move_id = am.id
            WHERE aml.date <= %s AND aml.company_id = %s AND aml.account_id IN %s
            AND am.state in %s
        ''', [self.env.context['date_to'], journal.company_id.id, tuple(accounts.ids), tuple(states)])
        rslt['total_already_accounted'] = self._cr.fetchone()[0] or 0.0

        # Payments not reconciled with a bank statement line
        self._cr.execute('''
            SELECT
                aml.id,
                aml.name,
                aml.ref,
                aml.date,
                aml.''' + amount_field + '''                    AS balance
            FROM account_move_line aml
            LEFT JOIN res_company company                       ON company.id = aml.company_id
            LEFT JOIN account_account account                   ON account.id = aml.account_id
            LEFT JOIN account_account_type account_type         ON account_type.id = account.user_type_id
            LEFT JOIN account_bank_statement_line st_line       ON st_line.id = aml.statement_line_id
            LEFT JOIN account_payment payment                   ON payment.id = aml.payment_id
            LEFT JOIN account_journal journal                   ON journal.id = aml.journal_id
            WHERE aml.date <= %s
            AND aml.company_id = %s
            AND CASE WHEN journal.type NOT IN ('cash', 'bank')
                     THEN payment.journal_id
                     ELSE aml.journal_id
                 END = %s
            AND account_type.type = 'liquidity'
            AND full_reconcile_id IS NULL
            AND (aml.statement_line_id IS NULL OR st_line.date > %s)
            AND (company.account_bank_reconciliation_start IS NULL OR aml.date >= company.account_bank_reconciliation_start)
            ORDER BY aml.date DESC, aml.id DESC
        ''', [self._context['date_to'], journal.company_id.id, journal.id, self._context['date_to']])
        rslt['not_reconciled_payments'] = self._cr.dictfetchall()

        # Bank statement lines not reconciled with a payment
        rslt['not_reconciled_st_positive'] = self.env['account.bank.statement.line'].search([
            ('statement_id.journal_id', '=', journal.id),
            ('date', '<=', self._context['date_to']),
            ('journal_entry_ids', '=', False),
            ('amount', '>', 0),
            ('company_id', '=', company.id)
        ])

        rslt['not_reconciled_st_negative'] = self.env['account.bank.statement.line'].search([
            ('statement_id.journal_id', '=', journal.id),
            ('date', '<=', self._context['date_to']),
            ('journal_entry_ids', '=', False),
            ('amount', '<', 0),
            ('company_id', '=', company.id)
        ])

        # Final
        last_statement = self.env['account.bank.statement'].search([
            ('journal_id', '=', journal.id),
            ('date', '<=', self._context['date_to']),
            ('company_id', '=', company.id)
        ], order="date desc, id desc", limit=1)
        rslt['last_st_balance'] = last_statement.balance_end * self.get_currency_rate(options).rate
        rslt['last_st_end_date'] = last_statement.date

        return rslt
    
    @api.model
    def _get_bank_rec_report_data(self, options, line_id=None):
        # General data + setup
        rslt = {}

        journal_id = self._context.get('active_id') or options.get('active_id')
        journal = self.env['account.journal'].browse(journal_id)
        selected_companies = self.env['res.company'].browse(self.env.context['company_ids'])

        rslt['use_foreign_currency'] = \
                journal.currency_id != journal.company_id.currency_id \
                if journal.currency_id else False
        rslt['account_ids'] = list(set([journal.default_debit_account_id.id, journal.default_credit_account_id.id]) - {False})
        rslt['line_currency'] = journal.currency_id if rslt['use_foreign_currency'] else False
        self = self.with_context(line_currency=rslt['line_currency'])
        lines_already_accounted = self.env['account.move.line'].search([('account_id', 'in', rslt['account_ids']),
                                                                        ('date', '<=', self.env.context['date_to']),
                                                                        ('company_id', 'in', self.env.context['company_ids'])])
        rslt['odoo_balance'] = sum([line.amount_currency if rslt['use_foreign_currency'] else line.balance for line in lines_already_accounted])

        # Payments not reconciled with a bank statement line
        aml_domain = ['|', '&', ('move_id.journal_id.type', 'in', ('cash', 'bank')), ('move_id.journal_id', '=', journal_id),
                           '&', ('move_id.journal_id.type', 'not in', ('cash', 'bank')), ('payment_id.journal_id', '=', journal_id),
                     '|', ('statement_line_id', '=', False),
                     ('statement_line_id.date', '>', self.env.context['date_to']),
                     ('user_type_id.type', '=', 'liquidity'),
                     ('full_reconcile_id', '=', False),
                     ('date', '<=', self.env.context['date_to']),
        ]
        companies_unreconciled_selection_domain = []
        for company in selected_companies:
            company_domain = [('company_id', '=', company.id)]
            if company.account_bank_reconciliation_start:
                company_domain = expression.AND([company_domain, [('date', '>=', company.account_bank_reconciliation_start)]])
            companies_unreconciled_selection_domain = expression.OR([companies_unreconciled_selection_domain, company_domain])
        aml_domain += companies_unreconciled_selection_domain

        move_lines = self.env['account.move.line'].search(aml_domain)

        if move_lines:
            rslt['not_reconciled_pmts'] = move_lines

        # Bank statement lines not reconciled with a payment
        rslt['not_reconciled_st_positive'] = self.env['account.bank.statement.line'].search([('statement_id.journal_id', '=', journal_id),
                                                                             ('date', '<=', self.env.context['date_to']),
                                                                             ('journal_entry_ids', '=', False),
                                                                             ('amount', '>', 0),
                                                                             ('company_id', 'in', self.env.context['company_ids'])])

        rslt['not_reconciled_st_negative'] = self.env['account.bank.statement.line'].search([('statement_id.journal_id', '=', journal_id),
                                                                             ('date', '<=', self.env.context['date_to']),
                                                                             ('journal_entry_ids', '=', False),
                                                                             ('amount', '<', 0),
                                                                             ('company_id', 'in', self.env.context['company_ids'])])

        # Final
        last_statement = self.env['account.bank.statement'].search(
                [
                    ('journal_id', '=', journal_id),
                    ('date', '<=', self.env.context['date_to']),
                    ('company_id', 'in', self.env.context['company_ids'])
                ], order="date desc, id desc", limit=1)
        
        rslt['last_st_balance'] = last_statement.balance_end * self.get_currency_rate(options).rate
        rslt['last_st_end_date'] = last_statement.date
        
        rslt['odoo_balance'] = rslt['odoo_balance'] * self.get_currency_rate(options).rate

        return rslt

    @api.model
    def _get_lines(self, options, line_id=None):
        # Fetch data
        report_data = self._get_bank_rec_report_data(options, line_id)
        self = self.with_context(line_currency=report_data['line_currency'])

        # Compute totals
        unrec_tot = sum([-(self._get_amount(aml, report_data)) for aml in report_data.get('not_reconciled_pmts', [])]) * self.get_currency_rate(options).rate
        outstanding_plus_tot = sum([st_line.amount for st_line in report_data.get('not_reconciled_st_positive', [])]) * self.get_currency_rate(options).rate
        outstanding_minus_tot = sum([st_line.amount for st_line in report_data.get('not_reconciled_st_negative', [])]) * self.get_currency_rate(options).rate
        
        computed_stmt_balance = report_data['odoo_balance'] + outstanding_plus_tot + outstanding_minus_tot + unrec_tot
        difference = computed_stmt_balance - report_data['last_st_balance']
        # Build report
        lines = []
        
        cids = request.httprequest.cookies.get('cids', str(request.env.user.company_id.id))
        company_ids = [int(cid) for cid in cids.split(',')]
        user_company = self.env['res.company'].browse(company_ids[0])
                
        lines.append(self._add_title_line(
            options,
            _("Virtual GL Balance"),
            amount=None if user_company.totals_below_sections else computed_stmt_balance,
            level=0))

        gl_title = _("Current balance of account %s")
        if len(report_data['account_ids']) > 1:
            gl_title = _("Current balance of accounts %s")

        accounts = self.env['account.account'].browse(report_data['account_ids'])
        accounts_string = ', '.join(accounts.mapped('code'))
        lines.append(self._add_title_line(options, gl_title % accounts_string, level=1, amount=report_data['odoo_balance'], date=options['date']['date']))

        lines.append(self._add_title_line(options, _("Operations to Process"), level=1))

        if report_data.get('not_reconciled_st_positive') or report_data.get('not_reconciled_st_negative'):
            lines.append(self._add_title_line(options, _("Unreconciled Bank Statement Lines"), level=2))
            for line in report_data.get('not_reconciled_st_positive', []):
                line_amount = line.amount * self.get_currency_rate(options).rate
                        
                lines.append(self._add_bank_statement_line(line, line_amount))

            for line in report_data.get('not_reconciled_st_negative', []):
                line_amount = line.amount * self.get_currency_rate(options).rate
                        
                lines.append(self._add_bank_statement_line(line, line_amount))

        if report_data.get('not_reconciled_pmts'):
            lines.append(self._add_title_line(options, _("Validated Payments not Linked with a Bank Statement Line"), level=2))
            for line in report_data['not_reconciled_pmts']:
                self.line_number += 1
                line_description = line_title = line.ref
                if line_description and len(line_description) > 70 and not self.env.context.get('print_mode'):
                    line_description = line.ref[:65] + '...'
                    
                line_amount = self._get_amount(line, report_data) * self.get_currency_rate(options).rate
                
                lines.append({
                    'id': str(line.id),
                    'name': line.name,
                    'columns': [
                        {'name': format_date(self.env, line.date)},
                        {'name': line_description, 'title': line_title, 'style': 'display:block;'},
                        {'name': self.format_value(-line_amount, report_data['line_currency'])},
                    ],
                    'class': 'o_account_reports_level3',
                    'caret_options': 'account.payment',
                })

        if user_company.totals_below_sections:
            lines.append(self._add_total_line(computed_stmt_balance))

        lines.append(self._add_title_line(options, _("Last Bank Statement Ending Balance"), level=0, amount=report_data['last_st_balance'], date=report_data['last_st_end_date']))
        last_line = self._add_title_line(options, _("Unexplained Difference"), level=0, amount=difference)
        last_line['title_hover'] = _("""Difference between Virtual GL Balance and Last Bank Statement Ending Balance.\n
If non-zero, it could be due to
  1) some bank statements being not yet encoded into Odoo
  2) payments double-encoded""")
        #NOTE: anyone trying to explain the 'unexplained difference' should check
        # * the list of 'validated payments not linked with a statement line': maybe an operation was recorded
        #   as a new payment when processing a statement, instead of choosing the blue line corresponding to
        #   an already existing payment
        # * the starting and ending balance of the bank statements, to make sure there is no gap between them.
        # * there's no 'draft' move linked with a bank statement
        line_currency = self.env.context.get('line_currency', False)
        if self.env.context.get('no_format'):
            last_line['columns'][-1]['title'] = self.format_value(computed_stmt_balance, line_currency) - self.format_value(report_data['last_st_balance'], line_currency)
        else:
            last_line['columns'][-1]['title'] = self.format_value(computed_stmt_balance, line_currency) + " - " + self.format_value(report_data['last_st_balance'], line_currency)
        lines.append(last_line)

        return lines