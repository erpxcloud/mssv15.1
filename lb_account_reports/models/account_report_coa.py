# -*- coding: utf-8 -*-
from odoo import models, api, _, fields, http
from odoo.http import request
from datetime import datetime

from odoo.tools import pycompat


import io
try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    import xlsxwriter

import logging
log = logging.getLogger(__name__)

class report_account_coa(models.AbstractModel):
    _inherit = "account.coa.report"
           
    filter_hierarchy_parent = False
    
    def get_search_data(self, values):
        cids = request.httprequest.cookies.get('cids', str(request.env.user.company_id.id))
        company_ids = [int(cid) for cid in cids.split(',')]
        company = self.env['res.company'].browse(company_ids[0])
        
        accounts = []
        for value in values:
            accounts += self.env['account.account'].search([('display_name_computed', '=ilike', value + "%"), ('company_id', '=', company.id)]).ids
        
        request.session["account_ids"] = accounts
        request.session["search_values"] = values
        
    def clear_data(self):
        if request.session.get("account_ids"):
            del request.session["account_ids"]
            
        if request.session.get("search_values"):
            del request.session["search_values"]
            
    def _get_templates(self):
        templates = super(report_account_coa, self)._get_templates()
        templates['main_table_header_template'] = 'lb_account_reports.template_coa_table_header'
        return templates
    
    def _get_super_columns(self, options):
        date_cols = options.get('date') and [options['date']] or []
        date_cols += (options.get('comparison') or {}).get('periods', [])

        columns = [{'string': _('Initial Balance')}]
        columns += reversed(date_cols)
        columns += [{'string': _('Total')}]
        columns += [{'string': _('Total Balance')}]

        return {'columns': columns, 'x_offset': 1, 'merge': 2}
    
    def _get_columns_name(self, options):
        columns = super(report_account_coa, self)._get_columns_name(options)
        #Column for total balance 
        columns += [
            {'name': '', 'class': 'number', 'style': 'padding-left: 35px'},
        ]
        return columns
        
    @api.model
    def _get_lines(self, options, line_id=None):
        # Create new options with 'unfold_all' to compute the initial balances.
        # Then, the '_do_query' will compute all sums/unaffected earnings/initial balances for all comparisons.
        new_options = options.copy()
        new_options['unfold_all'] = True
        options_list = self._get_options_periods_list(new_options)
        accounts_results, taxes_results = self.env['account.general.ledger']._do_query(options_list, fetch_lines=False)
        lines = []
        totals = [0.0] * (2 * (len(options_list) + 2))
        
        totals.append(0.0) #Used for total balance
        
        # Add lines, one per account.account record.
        for account, periods_results in accounts_results:
            sums = []
            account_balance = 0.0
            initial_balance = 0.0
            
            display_name = account.code + " " + account.name
            if options.get('filter_accounts_list'):
                if not any([display_name_part.lower().startswith(tuple(options.get('filter_accounts_list'))) for display_name_part in display_name.split(' ')]):
                    continue
                
            if options.get('filter_accounts'):
                if not (options['filter_accounts'].lower() in display_name.lower()):
                        continue
            non_zero = False
            for i, period_values in enumerate(reversed(periods_results)):
                account_sum = period_values.get('sum', {})
                account_un_earn = period_values.get('unaffected_earnings', {})
                account_init_bal = period_values.get('initial_balance', {})
                
                #skip accounts with all periods = 0 and no initial balance
                non_zero = False
                if (account_sum.get('debit', 0.0) - account_init_bal.get('debit', 0.0)) or (account_sum.get('credit', 0.0) - account_init_bal.get('credit', 0.0)) or\
                        not self.env.company.currency_id.is_zero(account_init_bal.get('balance', 0) + account_un_earn.get('balance', 0)):
                        non_zero = True
                if not non_zero:
                    continue
                if i == 0:
                    # Append the initial balances.
                    initial_balance = account_init_bal.get('balance', 0.0) + account_un_earn.get('balance', 0.0)
                    sums += [
                        initial_balance > 0 and initial_balance or 0.0,
                        initial_balance < 0 and -initial_balance or 0.0,
                    ]
                    account_balance += initial_balance

                # Append the debit/credit columns.
                sums += [
                    account_sum.get('debit', 0.0) - account_init_bal.get('debit', 0.0),
                    account_sum.get('credit', 0.0) - account_init_bal.get('credit', 0.0),
                ]
                account_balance += sums[-2] - sums[-1]
            if not non_zero:
                continue
                    
            # Append the totals.
            sums += [
                account_balance > 0 and account_balance or 0.0,
                account_balance < 0 and -account_balance or 0.0,
            ]

            # account.account report line.
            columns = []
            for i, value in enumerate(sums):
                # Update totals.
                totals[i] += value

                # Create columns.
                columns.append({'name': self.format_value(value, blank_if_zero=False), 'class': 'number', 'no_format_name': value})
               
            total_debit = account_balance > 0 and account_balance or 0.0
            total_credit = account_balance < 0 and -account_balance or 0.0
            
            total_amount = total_debit - total_credit 
            columns += [
               {'name': self.format_value(total_amount) , 'no_format_name': (total_amount > 0 or total_amount < 0 ) and total_amount or 0, 'style': 'padding-left: 35px'},
            ]
            
            totals[-1] += total_amount
            
            name = account.name_get()[0][1]
#             if len(name) > 40 and not self._context.get('print_mode'):
#                 name = name[:40]+'...'

            lines.append({
                'id': account.id,
                'name': name,
                'account_name' : account.name,
                'account_code' : account.code,
                'title_hover': name,
                'columns': columns,
                'unfoldable': False,
                'caret_options': 'account.account',
            })

        # Total report line.
        lines.append({
             'id': 'grouped_accounts_total',
             'name': _('Total'),
             'class': 'total',
             'columns': [{'name': self.format_value(total), 'class': 'number'} for total in totals],
             'level': 1,
        })

        return lines
    
    def get_xlsx(self, options, response=None):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet(self._get_report_name()[:31])

        date_default_col1_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666', 'indent': 2, 'num_format': 'yyyy-mm-dd'})
        date_default_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666', 'num_format': 'yyyy-mm-dd'})
        default_col1_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666', 'indent': 2})
        default_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666'})
        title_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'bottom': 2})
        super_col_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'align': 'center'})
        level_0_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 13, 'bottom': 6, 'font_color': '#666666'})
        level_1_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 13, 'bottom': 1, 'font_color': '#666666'})
        level_2_col1_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 12, 'font_color': '#666666', 'indent': 1})
        level_2_col1_total_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 12, 'font_color': '#666666'})
        level_2_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 12, 'font_color': '#666666'})
        level_3_col1_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666', 'indent': 2})
        level_3_col1_total_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 12, 'font_color': '#666666', 'indent': 1})
        level_3_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666'})
        
        selected_company_ids = self._context.get('allowed_company_ids', self.env.company.ids)
        if selected_company_ids and selected_company_ids[0] :
            company_id = self.env['res.company'].browse(selected_company_ids[0])
        else:
            company_id = self.env.company
        
        #Set the first column width to 50
        sheet.set_column(0, 0, 50)
        
        if company_id.split_account_in_excel:
            # first column for the code and the second for the name of the account
            sheet.set_column(0, 0, 20)
            sheet.set_column(1, 1, 40)

        super_columns = self._get_super_columns(options)
        y_offset = bool(super_columns.get('columns')) and 1 or 0

        sheet.write(y_offset, 0, '', title_style)
        x = super_columns.get('x_offset', 0)
        
        if company_id.split_account_in_excel:
            # extra column for the name code of the account
            sheet.write(y_offset, 1, '', title_style)
            x = 2
        # Todo in master: Try to put this logic elsewhere
        for super_col in super_columns.get('columns', []):
            cell_content = super_col.get('string', '').replace('<br/>', ' ').replace('&nbsp;', ' ')
            x_merge = super_columns.get('merge')
            if x_merge and x_merge > 1:
                sheet.merge_range(0, x, 0, x + (x_merge - 1), cell_content, super_col_style)
                x += x_merge
            else:
                sheet.write(0, x, cell_content, super_col_style)
                x += 1
        for row in self.get_header(options):
            x = 0
            if company_id.split_account_in_excel:
                x = 1
            for column in row:
                colspan = column.get('colspan', 1)
                header_label = column.get('name', '').replace('<br/>', ' ').replace('&nbsp;', ' ')
                if colspan == 1:
                    sheet.write(y_offset, x, header_label, title_style)
                else:
                    sheet.merge_range(y_offset, x, y_offset, x + colspan - 1, header_label, title_style)
                x += colspan
            y_offset += 1
        ctx = self._set_context(options)
        ctx.update({'no_format':True, 'print_mode':True, 'prefetch_fields': False})
        # deactivating the prefetching saves ~35% on get_lines running time
        lines = self.with_context(ctx)._get_lines(options)
        
        if options.get('hierarchy_parent'):
            selected_account_level = None
            
            if options.get('selected_account_level'):
                selected_account_level = options.get('selected_account_level')
                
            lines = self._create_hierarchy(lines, options, display_parent_only=True, account_level=selected_account_level)

        if options.get('hierarchy'):
            lines = self._create_hierarchy(lines, options)
        if options.get('selected_column'):
            lines = self._sort_lines(lines, options)
        if options.get('hierarchy_parent'):
            lines = list(filter(lambda x: x.get('level') in [1, 2, 3], lines))

        #write all data rows
        for y in range(0, len(lines)):
            level = lines[y].get('level')
            if lines[y].get('caret_options'):
                style = level_3_style
                col1_style = level_3_col1_style
            elif level == 0:
                y_offset += 1
                style = level_0_style
                col1_style = style
            elif level == 1:
                style = level_1_style
                col1_style = style
            elif level == 2:
                style = level_2_style
                col1_style = 'total' in lines[y].get('class', '').split(' ') and level_2_col1_total_style or level_2_col1_style
            elif level == 3:
                style = level_3_style
                col1_style = 'total' in lines[y].get('class', '').split(' ') and level_3_col1_total_style or level_3_col1_style
            else:
                style = default_style
                col1_style = default_col1_style
            
            #write the first column, with a specific style to manage the indentation
            if company_id.split_account_in_excel:
                # write the first 2 column, with account code and name
                code_value = lines[y].get('account_code', '')
                sheet.write(y + y_offset, 0, code_value, col1_style)
                
                account_name = lines[y].get('account_name', '')
                sheet.write(y + y_offset, 1, account_name, col1_style)
                offset = 2
            else:
                cell_type, cell_value = self._get_cell_type_value(lines[y])
                sheet.write(y + y_offset, 0, cell_value, col1_style)
                offset = 1 

            #write all the remaining cells
            for x in range(offset, len(lines[y]['columns']) + offset):
                cell_type, cell_value = self._get_cell_type_value(lines[y]['columns'][x - offset])
                if cell_type == 'date':
                    sheet.write_datetime(y + y_offset, x + lines[y].get('colspan', 1) - 1, cell_value, date_default_style)
                else:
                    sheet.write(y + y_offset, x + lines[y].get('colspan', 1) - 1, cell_value, style)

        workbook.close()
        output.seek(0)
        generated_file = output.read()
        output.close()

        return generated_file