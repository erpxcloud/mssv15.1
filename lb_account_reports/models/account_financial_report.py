# -*- coding: utf-8 -*-
from odoo import models, fields, api, _, http
from odoo.http import request
from odoo.tools.misc import formatLang
from odoo.tools.safe_eval import safe_eval

import io
try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    # TODO saas-17: remove the try/except to directly import from misc
    import xlsxwriter
import logging

log = logging.getLogger(__name__)

class ReportAccountFinancialReport(models.Model):
    _inherit = "account.financial.html.report"
    
     
    def get_selected_company(self):
        cids = request.httprequest.cookies.get('cids', str(request.env.user.company_id.id))
        company_ids = [int(cid) for cid in cids.split(',')]
        user_company = self.env['res.company'].browse(company_ids[0])
            
        return user_company
    def _get_currency_table(self):
        user_company = self.get_selected_company()
      
        used_currency = user_company.currency_id.with_context(company_id=user_company.id)
        
        selected_multi_currency_id = self._context.get('selected_multi_currency')
        if selected_multi_currency_id:
            selected_multi_currency_id = int(selected_multi_currency_id)
            if user_company.second_currency_id.id == selected_multi_currency_id:
                user_currency = user_company.second_currency_id
            elif user_company.third_currency_id.id == selected_multi_currency_id:
                user_currency = user_company.third_currency_id
        
        currency_table = {}
        for company in self.env['res.company'].search([]):
            if company.currency_id != used_currency:
                currency_table[company.currency_id.id] = used_currency.rate / company.currency_id.rate
                
        return currency_table
    
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
            sheet.set_column(0, 0, 30)
            sheet.set_column(1, 1, 40)
            sheet.set_column(2, 2, 30)

        super_columns = self._get_super_columns(options)
        y_offset = bool(super_columns.get('columns')) and 1 or 0

        sheet.write(y_offset, 0, '', title_style)
        x = super_columns.get('x_offset', 0)
        
        if company_id.split_account_in_excel:
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
            cell_type, cell_value = self._get_cell_type_value(lines[y])
            
            if company_id.split_account_in_excel:
                if lines[y].get('financial_group_line_id', None):
                    try:
                        account_id = self.env["account.account"].browse(int(lines[y].get('id', None).split("_")[-1]))
                        account_name = account_id.name
                        account_code = account_id.code
                    except:
                        account_name = cell_value
                        account_code = cell_value
                    sheet.write(y + y_offset, 0, account_code, col1_style)
                    sheet.write(y + y_offset, 1, account_name, col1_style)
                else:
                    sheet.merge_range(y + y_offset, 0, y + y_offset, 1, cell_value, col1_style)
                offset = 2
            else:
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


class AccountFinancialReportLine(models.Model):
    _inherit = "account.financial.html.report.line"
    
     
    def get_selected_company(self):
        cids = request.httprequest.cookies.get('cids', str(request.env.user.company_id.id))
        company_ids = [int(cid) for cid in cids.split(',')]
        user_company = self.env['res.company'].browse(company_ids[0])
            
        return user_company
    def _query_get_select_sum(self, currency_table):
        """ Little function to help building the SELECT statement when computing the report lines.

            @param currency_table: dictionary containing the foreign currencies (key) and their factor (value)
                compared to the current user's company currency
            @returns: the string and parameters to use for the SELECT
        """
        user_company = self.get_selected_company()
        
        decimal_places = user_company.currency_id.decimal_places
        extra_params = []
        select = '''
            COALESCE(SUM(\"account_move_line\".balance), 0) AS balance,
            COALESCE(SUM(\"account_move_line\".amount_residual), 0) AS amount_residual,
            COALESCE(SUM(\"account_move_line\".debit), 0) AS debit,
            COALESCE(SUM(\"account_move_line\".credit), 0) AS credit
        '''
        if currency_table:
            select = 'COALESCE(SUM(CASE '
            for currency_id, rate in currency_table.items():
                extra_params += [currency_id, rate, decimal_places]
                select += 'WHEN \"account_move_line\".company_currency_id = %s THEN ROUND(\"account_move_line\".balance * %s, %s) '
            select += 'ELSE \"account_move_line\".balance END), 0) AS balance, COALESCE(SUM(CASE '
            for currency_id, rate in currency_table.items():
                extra_params += [currency_id, rate, decimal_places]
                select += 'WHEN \"account_move_line\".company_currency_id = %s THEN ROUND(\"account_move_line\".amount_residual * %s, %s) '
            select += 'ELSE \"account_move_line\".amount_residual END), 0) AS amount_residual, COALESCE(SUM(CASE '
            for currency_id, rate in currency_table.items():
                extra_params += [currency_id, rate, decimal_places]
                select += 'WHEN \"account_move_line\".company_currency_id = %s THEN ROUND(\"account_move_line\".debit * %s, %s) '
            select += 'ELSE \"account_move_line\".debit END), 0) AS debit, COALESCE(SUM(CASE '
            for currency_id, rate in currency_table.items():
                extra_params += [currency_id, rate, decimal_places]
                select += 'WHEN \"account_move_line\".company_currency_id = %s THEN ROUND(\"account_move_line\".credit * %s, %s) '
            select += 'ELSE \"account_move_line\".credit END), 0) AS credit'
        
        user_company = self.get_selected_company()
    
        selected_multi_currency_id = self._context.get('selected_multi_currency')
        if selected_multi_currency_id:
            selected_multi_currency_id = int(selected_multi_currency_id)
            if user_company.second_currency_id.id == selected_multi_currency_id:
                select = select.replace("\"account_move_line\".debit", "\"account_move_line\".second_debit").replace("\"account_move_line\".credit", "\"account_move_line\".second_credit").replace("\"account_move_line\".balance", "\"account_move_line\".second_balance")
            elif user_company.third_currency_id.id == selected_multi_currency_id:
                select = select.replace("\"account_move_line\".debit", "\"account_move_line\".third_debit").replace("\"account_move_line\".credit", "\"account_move_line\".third_credit").replace("\"account_move_line\".balance", "\"account_move_line\".third_balance")
        
        return select, extra_params
    
    def _compute_line(self, currency_table, financial_report, group_by=None, domain=[]):
        """ Computes the sum that appeas on report lines when they aren't unfolded. It is using _query_get() function
            of account.move.line which is based on the context, and an additional domain (the field domain on the report
            line) to build the query that will be used.
  
            @param currency_table: dictionary containing the foreign currencies (key) and their factor (value)
                compared to the current user's company currency
            @param financial_report: browse_record of the financial report we are willing to compute the lines for
            @param group_by: used in case of conditionnal sums on the report line
            @param domain: domain on the report line to consider in the query_get() call
  
            @returns : a dictionnary that has for each aml in the domain a dictionnary of the values of the fields
        """
        results = super(AccountFinancialReportLine, self)._compute_line(currency_table, financial_report, group_by, domain)
        results['currency_id'] = self._get_currency().id
          
        return results
    
    def _query_get_select_sum(self, currency_table):
        select, extra_params = super(AccountFinancialReportLine, self)._query_get_select_sum(currency_table)
        
        user_company = self.get_selected_company()
     
        selected_multi_currency_id = self._context.get('selected_multi_currency')
        if selected_multi_currency_id:
            selected_multi_currency_id = int(selected_multi_currency_id)
            if user_company.second_currency_id.id == selected_multi_currency_id:
                select = select.replace("\"account_move_line\".debit", "\"account_move_line\".second_debit").replace("\"account_move_line\".credit", "\"account_move_line\".second_credit").replace("\"account_move_line\".balance", "\"account_move_line\".second_balance")
            elif user_company.third_currency_id.id == selected_multi_currency_id:
                select = select.replace("\"account_move_line\".debit", "\"account_move_line\".third_debit").replace("\"account_move_line\".credit", "\"account_move_line\".third_credit").replace("\"account_move_line\".balance", "\"account_move_line\".third_balance")
                
        return select, extra_params
  
    def _format(self, value):
        if self.env.context.get('no_format'):
            return value
        value['no_format_name'] = value['name']
        if self.figure_type == 'float':
            currency_id = self._get_currency()
            if currency_id.is_zero(value['name']):
                # don't print -0.0 in reports
                value['name'] = abs(value['name'])
                value['class'] = 'number text-muted'
            value['name'] = formatLang(self.env, value['name'], currency_obj=currency_id)
            return value
        if self.figure_type == 'percents':
            value['name'] = str(round(value['name'] * 100, 1)) + '%'
            return value
        value['name'] = round(value['name'], 1)
        return value
     
    def _get_currency(self):
        user_company = self.get_selected_company()
            
        currency_id = user_company.currency_id
        selected_multi_currency_id = self._context.get('selected_multi_currency')
        if selected_multi_currency_id:
            selected_multi_currency_id = int(selected_multi_currency_id)
            if user_company.second_currency_id.id == selected_multi_currency_id:
                currency_id = user_company.second_currency_id
            elif user_company.third_currency_id.id == selected_multi_currency_id:
                currency_id = user_company.third_currency_id
         
        return currency_id
    
    def _get_balance(self, linesDict, currency_table, financial_report, field_names=None):
        results = []

        if not field_names:
            field_names = ['debit', 'credit', 'balance']
        
        user_company = self.get_selected_company()
        
        for rec in self:
            res = dict((fn, 0.0) for fn in field_names)
            c = FormulaContext(self.env['account.financial.html.report.line'],
                    linesDict, currency_table, financial_report, rec)
            if rec.formulas:
                for f in rec.formulas.split(';'):
                    [field, formula] = f.split('=')
                    field = field.strip()
                    if field in field_names:
                        try:
                            #This condition is set in order to convert the residual amount to the selected currency from report
                            if "sum.amount_residual" in formula:
                                balance = safe_eval(formula, c, nocopy=True)
                                user_currency = self._get_currency()
                                balance = user_company.currency_id._convert(balance, user_currency, user_company, fields.Date.today())
                                res[field] = balance
                            else:
                                res[field] = safe_eval(formula, c, nocopy=True)
                        except ValueError as err:
                            if 'division by zero' in err.args[0]:
                                res[field] = 0
                            else:
                                raise err
            results.append(res)
        return results
    
    def _eval_formula(self, financial_report, debit_credit, currency_table, linesDict_per_group, groups=False):
        groups = groups or {'fields': [], 'ids': [()]}
        debit_credit = debit_credit and financial_report.debit_credit
        formulas = self._split_formulas()
        currency = self._get_currency()

        line_res_per_group = []

        if not groups['ids']:
            return [{'line': {'balance': 0.0}}]

        # this computes the results of the line itself
        for group_index, group in enumerate(groups['ids']):
            self_for_group = self.with_context(group_domain=self._get_group_domain(group, groups))
            linesDict = linesDict_per_group[group_index]
            line = False

            if self.code and self.code in linesDict:
                line = linesDict[self.code]
            elif formulas and formulas['balance'].strip() == 'count_rows' and self.groupby:
                line_res_per_group.append({'line': {'balance': self_for_group._get_rows_count()}})
            elif formulas and formulas['balance'].strip() == 'from_context':
                line_res_per_group.append({'line': {'balance': self_for_group._get_value_from_context()}})
            else:
                line = FormulaLine(self_for_group, currency_table, financial_report, linesDict=linesDict)

            if line:
                res = {}
                res['balance'] = line.balance
                res['balance'] = currency.round(line.balance)
                if debit_credit:
                    res['credit'] = currency.round(line.credit)
                    res['debit'] = currency.round(line.debit)
                line_res_per_group.append(res)

        # don't need any groupby lines for count_rows and from_context formulas
        if all('line' in val for val in line_res_per_group):
            return line_res_per_group

        columns = []
        # this computes children lines in case the groupby field is set
        if self.domain and self.groupby and self.show_domain != 'never':
            if self.groupby not in self.env['account.move.line']:
                raise ValueError(_('Groupby should be a field from account.move.line'))

            groupby = [self.groupby or 'id']
            if groups:
                groupby = groups['fields'] + groupby
            groupby = ', '.join(['"account_move_line".%s' % field for field in groupby])

            aml_obj = self.env['account.move.line']
            tables, where_clause, where_params = aml_obj._query_get(domain=self._get_aml_domain())
            if financial_report.tax_report:
                where_clause += ''' AND "account_move_line".tax_exigible = 't' '''

            select, params = self._query_get_select_sum(currency_table)
            sql = "SELECT " + groupby + ", " + select + " FROM " + tables + " WHERE " + where_clause + " GROUP BY " + groupby + " ORDER BY " + groupby

            params += where_params
            self.env.cr.execute(sql, params)
            results = self.env.cr.fetchall()
            for group_index, group in enumerate(groups['ids']):
                linesDict = linesDict_per_group[group_index]
                results_for_group = [result for result in results if group == result[:len(group)]]
                if results_for_group:
                    results_for_group = [r[len(group):] for r in results_for_group]
                    user_company = self.get_selected_company()
                    #Converted residual amount to match the selected currency
                    results_for_group = dict([(k[0], {'balance': k[1], 
                                                      'amount_residual': user_company.currency_id._convert(k[2], currency, user_company, fields.Date.today()), 
                                                      'debit': k[3], 
                                                      'credit':  k[4]}) for k in results_for_group])
                    
                    c = FormulaContext(self.env['account.financial.html.report.line'].with_context(group_domain=self._get_group_domain(group, groups)),
                                       linesDict, currency_table, financial_report, only_sum=True)
                    if formulas:
                        for key in results_for_group:
                            c['sum'] = FormulaLine(results_for_group[key], currency_table, financial_report, type='not_computed')
                            c['sum_if_pos'] = FormulaLine(results_for_group[key]['balance'] >= 0.0 and results_for_group[key] or {'balance': 0.0},
                                                          currency_table, financial_report, type='not_computed')
                            c['sum_if_neg'] = FormulaLine(results_for_group[key]['balance'] <= 0.0 and results_for_group[key] or {'balance': 0.0},
                                                          currency_table, financial_report, type='not_computed')
                            for col, formula in formulas.items():
                                if col in results_for_group[key]:
                                    results_for_group[key][col] = safe_eval(formula, c, nocopy=True)
                    to_del = []
                    for key in results_for_group:
                        if currency.is_zero(results_for_group[key]['balance']):
                            to_del.append(key)
                    for key in to_del:
                        del results_for_group[key]
                    results_for_group.update({'line': line_res_per_group[group_index]})
                    columns.append(results_for_group)
                else:
                    res_vals = {'balance': 0.0}
                    if debit_credit:
                        res_vals.update({'debit': 0.0, 'credit': 0.0})
                    columns.append({'line': res_vals})

        return columns or [{'line': res} for res in line_res_per_group]
    
class FormulaLine(object):
    def __init__(self, obj, currency_table, financial_report, type='balance', linesDict=None):
        if linesDict is None:
            linesDict = {}
        fields = dict((fn, 0.0) for fn in ['debit', 'credit', 'balance'])
        if type == 'balance':
            fields = obj._get_balance(linesDict, currency_table, financial_report)[0]
            linesDict[obj.code] = self
        elif type in ['sum', 'sum_if_pos', 'sum_if_neg']:
            if type == 'sum_if_neg':
                obj = obj.with_context(sum_if_neg=True)
            if type == 'sum_if_pos':
                obj = obj.with_context(sum_if_pos=True)
            if obj._name == 'account.financial.html.report.line':
                fields = obj._get_sum(currency_table, financial_report)
                self.amount_residual = fields['amount_residual']
            elif obj._name == 'account.move.line':
                self.amount_residual = 0.0
                field_names = ['debit', 'credit', 'balance', 'amount_residual']
                res = obj.env['account.financial.html.report.line']._compute_line(currency_table, financial_report)
                for field in field_names:
                    fields[field] = res[field]
                self.amount_residual = fields['amount_residual']
        elif type == 'not_computed':
            for field in fields:
                fields[field] = obj.get(field, 0)
            self.amount_residual = obj.get('amount_residual', 0)
        elif type == 'null':
            self.amount_residual = 0.0
        self.balance = fields['balance']
        self.credit = fields['credit']
        self.debit = fields['debit']


class FormulaContext(dict):
    def __init__(self, reportLineObj, linesDict, currency_table, financial_report, curObj=None, only_sum=False, *data):
        self.reportLineObj = reportLineObj
        self.curObj = curObj
        self.linesDict = linesDict
        self.currency_table = currency_table
        self.only_sum = only_sum
        self.financial_report = financial_report
        return super(FormulaContext, self).__init__(data)

    def __getitem__(self, item):
        formula_items = ['sum', 'sum_if_pos', 'sum_if_neg']
        if item in set(__builtins__.keys()) - set(formula_items):
            return super(FormulaContext, self).__getitem__(item)

        if self.only_sum and item not in formula_items:
            return FormulaLine(self.curObj, self.currency_table, self.financial_report, type='null')
        if self.get(item):
            return super(FormulaContext, self).__getitem__(item)
        if self.linesDict.get(item):
            return self.linesDict[item]
        if item == 'sum':
            res = FormulaLine(self.curObj, self.currency_table, self.financial_report, type='sum')
            self['sum'] = res
            return res
        if item == 'sum_if_pos':
            res = FormulaLine(self.curObj, self.currency_table, self.financial_report, type='sum_if_pos')
            self['sum_if_pos'] = res
            return res
        if item == 'sum_if_neg':
            res = FormulaLine(self.curObj, self.currency_table, self.financial_report, type='sum_if_neg')
            self['sum_if_neg'] = res
            return res
        if item == 'NDays':
            d1 = fields.Date.from_string(self.curObj.env.context['date_from'])
            d2 = fields.Date.from_string(self.curObj.env.context['date_to'])
            res = (d2 - d1).days
            self['NDays'] = res
            return res
        if item == 'count_rows':
            return self.curObj._get_rows_count()
        if item == 'from_context':
            return self.curObj._get_value_from_context()
        line_id = self.reportLineObj.search([('code', '=', item)], limit=1)
        if line_id:
            date_from, date_to, strict_range = line_id._compute_date_range()
            res = FormulaLine(line_id.with_context(strict_range=strict_range, date_from=date_from, date_to=date_to), self.currency_table, self.financial_report, linesDict=self.linesDict)
            self.linesDict[item] = res
            return res
        return super(FormulaContext, self).__getitem__(item)
    