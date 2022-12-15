# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, fields, _, http
from odoo.tools.misc import format_date

from dateutil.relativedelta import relativedelta
from itertools import chain
import logging
import warnings
import time
from odoo.http import request
from odoo.exceptions import UserError
from odoo.tools import float_is_zero
from datetime import datetime

_logger = logging.getLogger(__name__)


class ReportAccountAgedPartner(models.AbstractModel):
    _inherit = "account.aged.partner"

    filter_date = {'mode': 'single', 'filter': 'today'}
    filter_unfold_all = False
    filter_partner = True
    order_selected_column = {'default': 0}

    partner_id = fields.Many2one('res.partner')
    partner_name = fields.Char(group_operator='max')
    partner_trust = fields.Char(group_operator='max')
    payment_id = fields.Many2one('account.payment')
    report_date = fields.Date(group_operator='max', string='Due Date')
    expected_pay_date = fields.Date(string='Expected Date')
    move_type = fields.Char()
    move_name = fields.Char(group_operator='max')
    move_ref = fields.Char()
    account_name = fields.Char(group_operator='max')
    account_code = fields.Char(group_operator='max')
    report_currency_id = fields.Many2one('res.currency')
    period0 = fields.Monetary(string='As of: ')
    period1 = fields.Monetary(string='1 - 30')
    period2 = fields.Monetary(string='31 - 60')
    period3 = fields.Monetary(string='61 - 90')
    period4 = fields.Monetary(string='91 - 120')
    period6 = fields.Monetary(string='121 - 240')
    period7 = fields.Monetary(string='241 - 360')
    period5 = fields.Monetary(string='Older')
    amount_currency = fields.Monetary(currency_field='currency_id')

    @api.model
    def _get_query_period_table(self, options):
        ''' Compute the periods to handle in the report.
        E.g. Suppose date = '2019-01-09', the computed periods will be:

        Name                | Start         | Stop
        --------------------------------------------
        As of 2019-01-09    | 2019-01-09    |
        1 - 30              | 2018-12-10    | 2019-01-08
        31 - 60             | 2018-11-10    | 2018-12-09
        61 - 90             | 2018-10-11    | 2018-11-09
        91 - 120            | 2018-09-11    | 2018-10-10
        Older               |               | 2018-09-10

        Then, return the values as an sql floating table to use it directly in queries.

        :return: A floating sql query representing the report's periods.
        '''

        def minus_days(date_obj, days):
            return fields.Date.to_string(date_obj - relativedelta(days=days))

        date_str = options['date']['date_to']
        date = fields.Date.from_string(date_str)
        period_values = [
            (False, date_str),
            (minus_days(date, 1), minus_days(date, 30)),
            (minus_days(date, 31), minus_days(date, 60)),
            (minus_days(date, 61), minus_days(date, 90)),
            (minus_days(date, 91), minus_days(date, 120)),
            (minus_days(date, 121), minus_days(date, 240)),
            (minus_days(date, 241), minus_days(date, 360)),
            (minus_days(date, 361), False),
        ]

        period_table = ('(VALUES %s) AS period_table(date_start, date_stop, period_index)' %
                        ','.join("(%s, %s, %s)" for i, period in enumerate(period_values)))
        params = list(chain.from_iterable(
            (period[0] or None, period[1] or None, i)
            for i, period in enumerate(period_values)
        ))
        return self.env.cr.mogrify(period_table, params).decode(self.env.cr.connection.encoding)

    ####################################################
    # COLUMNS/LINES
    ####################################################
    @api.model
    def _get_column_details(self, options):
        columns = [
            self._header_column(),
            self._field_column('report_date'),

            self._field_column('account_name', name=_("Account"), ellipsis=True),
            self._field_column('expected_pay_date'),
            self._field_column('period0', name=_("As of: %s", format_date(self.env, options['date']['date_to']))),
            self._field_column('period1', sortable=True),
            self._field_column('period2', sortable=True),
            self._field_column('period3', sortable=True),
            self._field_column('period4', sortable=True),
            self._field_column('period6', sortable=True),
            self._field_column('period7', sortable=True),
            self._field_column('period5', sortable=True),
            self._custom_column(  # Avoid doing twice the sub-select in the view
                name=_('Total'),
                classes=['number'],
                formatter=self.format_value,
                getter=(
                    lambda v: v['period0'] + v['period1'] + v['period2'] + v['period3'] + v['period4'] + v['period6'] +
                              v['period7'] + v['period5']),
                sortable=True,
            ),
        ]

        if self.user_has_groups('base.group_multi_currency'):
            columns[2:2] = [
                self._field_column('amount_currency'),
                self._field_column('currency_id'),
            ]
        return columns

    def _get_hierarchy_details(self, options):
        return [
            self._hierarchy_level('partner_id', foldable=True, namespan=len(self._get_column_details(options)) - 7),
            self._hierarchy_level('id'),
        ]

    def _show_line(self, report_dict, value_dict, current, options):
        # Don't display an aml report line (except the header) with all zero amounts.
        all_zero = all(
            self.env.company.currency_id.is_zero(value_dict[f])
            for f in ['period0', 'period1', 'period2', 'period3', 'period4', 'period6', 'period7', 'period5']
        ) and not value_dict.get('__count')
        return super()._show_line(report_dict, value_dict, current, options) and not all_zero

    def _format_partner_id_line(self, res, value_dict, options):
        res['name'] = value_dict['partner_name'][:128] if value_dict['partner_name'] else _('Unknown Partner')
        res['trust'] = value_dict['partner_trust']

    def _format_id_line(self, res, value_dict, options):
        res['name'] = value_dict['move_name']
        res['title_hover'] = value_dict['move_ref']
        res['caret_options'] = 'account.payment' if value_dict.get('payment_id') else 'account.move'
        for col in res['columns']:
            if col.get('no_format') == 0:
                col['name'] = ''
        res['columns'][-1]['name'] = ''

    def _format_total_line(self, res, value_dict, options):
        res['name'] = _('Total')
        res['colspan'] = len(self._get_column_details(options)) - 7
        res['columns'] = res['columns'][res['colspan'] - 1:]

