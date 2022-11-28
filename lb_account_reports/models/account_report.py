from datetime import datetime

import logging
import copy
import json
import io
import lxml.html
import datetime
import ast

from dateutil.relativedelta import relativedelta
from docutils.nodes import option

try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    # TODO saas-17: remove the try/except to directly import from misc
    import xlsxwriter

from odoo import models, fields, api, _, http
from odoo.http import request
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, pycompat, config, date_utils
from odoo.osv import expression
from babel.dates import get_quarter_names, parse_date
from odoo.tools.misc import formatLang, format_date
from odoo.addons.web.controllers.main import clean_action
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import UserError

log = logging.getLogger(__name__)

class AccountReport(models.AbstractModel):
    _inherit = "account.report"

    filter_multi_currency = True
    filter_hierarchy_parent = None
    filter_account = None
    
    
    @api.model
    def _init_filter_account(self, options, previous_options=None):
        if not self.filter_account:
            return

        options['accounts'] = True
        options['account_ids'] = previous_options and previous_options.get('account_ids') or []
        selected_account_ids = [int(account) for account in options['account_ids']]
        selected_accounts = selected_account_ids and self.env['account.account'].browse(selected_account_ids) or self.env['account.account']
        options['selected_account_ids'] = selected_accounts.mapped('name')
    
    @api.model
    def _get_options_account_domain(self, options):
        domain = []
        if options.get('account_ids'):
            account_ids = [int(account) for account in options['account_ids']]
            domain.append(('account_id', 'in', account_ids))
        return domain
    
    @api.model
    def _get_options_domain(self, options):
        domain = super(AccountReport, self)._get_options_domain(options)
        domain += self._get_options_account_domain(options)
        return domain
    
    def get_selected_company(self):
        cids = request.httprequest.cookies.get('cids', str(request.env.user.company_id.id))
        company_ids = [int(cid) for cid in cids.split(',')]
        user_company = self.env['res.company'].browse(company_ids[0])
            
        return user_company
    
    
    @api.model
    def _get_query_currency_table(self, options):
        ''' Construct the currency table as a mapping company -> rate to convert the amount to the user's company
        currency in a multi-company/multi-currency environment.
        The currency_table is a small postgresql table construct with VALUES.
        :param options: The report options.
        :return:        The query representing the currency table.
        '''
        temp = self.env.company
        cids = request.httprequest.cookies.get('cids', str(request.env.user.company_id.id))
        company_ids = [int(cid) for cid in cids.split(',')]
        user_company = self.env['res.company'].browse(company_ids[0])
            
        self.env.company = user_company
        res = super(AccountReport,self)._get_query_currency_table(options)
        self.env.company = temp
        return res

    def _format_aml_name(self, line_name, move_ref, move_name):
        names = []
        if move_name != '/':
            names.append(move_name)
        if move_ref and move_ref != '/':
            names.append(move_ref)
        if line_name and line_name != '/':
            names.append(line_name)
        name = '-'.join(names)
#         if len(name) > 35 and not self.env.context.get('no_format'):
#             name = name[:32] + "..."

        return name
    
    @api.model
    def _create_hierarchy(self, lines, options, display_parent_only=False, account_level=None):
        """This method is called when the option 'hiearchy' is enabled on a report.
        It receives the lines (as computed by _get_lines()) in argument, and will add
        a hiearchy in those lines by using the account.group of accounts. If not set,
        it will fallback on creating a hierarchy based on the account's code first 3
        digits.
        """
        is_number = ['number' in c.get('class', []) for c in self.get_header(options)[-1][1:]]
        # Avoid redundant browsing.
        accounts_cache = {}

        # Retrieve account either from cache, either by browsing.
        def get_account(id):
            if id not in accounts_cache:
                accounts_cache[id] = self.env['account.account'].browse(id)
            return accounts_cache[id]

        # Add the report line to the hierarchy recursively.
        def add_line_to_hierarchy(line, codes, level_dict, depth=None):
            # Recursively build a dict where:
            # 'children' contains only subcodes
            # 'lines' contains the lines at this level
            # This > lines [optional, i.e. not for topmost level]
            #      > children > [codes] "That" > lines
            #                                  > metadata
            #                                  > children
            #      > metadata(depth, parent ...)
            
            if display_parent_only:
                line['style'] = 'padding-left: 35px; display:none;'

            if not codes:
                return
            if not depth:
                depth = line.get('level', 1)
            level_dict.setdefault('depth', depth)
            level_dict.setdefault('parent_id', 'hierarchy_' + codes[0][1] if codes[0][0] != 'root' else codes[0][1])
            level_dict.setdefault('children', {})
            code = codes[1]
            codes = codes[1:]
            level_dict['children'].setdefault(code, {})

            if len(codes) > 1:
                add_line_to_hierarchy(line, codes, level_dict['children'][code], depth=depth + 1)
            else:
                level_dict['children'][code].setdefault('lines', [])
                level_dict['children'][code]['lines'].append(line)
                for l in level_dict['children'][code]['lines']:
                    l['parent_id'] = 'hierarchy_' + code[1]

        # Merge a list of columns together and take care about str values.
        def merge_columns(columns):
            return [('n/a' if any(i != '' for i in x) else '') if any(isinstance(i, str) for i in x) else sum(x) for x in zip(*columns)]

        # Get_lines for the newly computed hierarchy.
        def get_hierarchy_lines(values, depth=1):
            lines = []
            sum_sum_columns = []
            unfold_all = self.env.context.get('print_mode') and len(options.get('unfolded_lines')) == 0
            for base_line in values.get('lines', []):
                lines.append(base_line)
                sum_sum_columns.append([c.get('no_format_name', c['name']) for c in base_line['columns']])

            # For the last iteration, there might not be the children key (see add_line_to_hierarchy)
            for key in sorted(values.get('children', {}).keys()):
                account = key[1].split(" ")
                
                code = account[0] if len(account) > 0 and account[0].isnumeric() else ""
                start = 1 if len(account) > 0 and account[0].isnumeric() else 0
                name = " ".join(i for i in account[start:]) if len(account) > start else ""
                
                sum_columns, sub_lines = get_hierarchy_lines(values['children'][key], depth=values['depth'])
                id = 'hierarchy_' + key[1]
                header_line = {
                    'id': id,
                    'name': key[1] if len(key[1]) < 30 else key[1][:30] + '...',  # second member of the tuple
                    'account_name': name,
                    'account_code': code,
                    'title_hover': key[1],
                    'unfoldable': True,
                    'unfolded': id in options.get('unfolded_lines') or unfold_all,
                    'level': values['depth'],
                    'parent_id': values['parent_id'],
                    'columns': [{'name': self.format_value(c) if not isinstance(c, str) else c} for c in sum_columns],
                }
                if key[0] == self.LEAST_SORT_PRIO:
                    header_line['style'] = 'font-style:italic;'
                lines += [header_line] + sub_lines
                sum_sum_columns.append(sum_columns)
            
            max_depth = 0
            for line in lines:
                if(line.get('level') and line.get('level') > max_depth):
                    max_depth = line.get('level')
            if account_level:
                if int(account_level) not in [0, 1]:
                    lines = list(filter(lambda x: x.get('level') and x.get('level') <= int(account_level), lines))
                else:
                   lines = list(filter(lambda x: x.get('level') and x.get('level') <=  1, lines)) 
            elif display_parent_only :
                lines = list(filter(lambda x: x.get('level') and x.get('level') <=  max_depth, lines))

            return merge_columns(sum_sum_columns), lines

        def deep_merge_dict(source, destination):
            for key, value in source.items():
                if isinstance(value, dict):
                    # get node or create one
                    node = destination.setdefault(key, {})
                    deep_merge_dict(value, node)
                else:
                    destination[key] = value

            return destination

        # Hierarchy of codes.
        accounts_hierarchy = {}

        new_lines = []
        no_group_lines = []
        # If no account.group at all, we need to pass once again in the loop to dispatch
        # all the lines across their account prefix, hence the None
        for line in lines + [None]:
            # Only deal with lines grouped by accounts.
            # And discriminating sections defined by account.financial.html.report.line
            is_grouped_by_account = line and line.get('caret_options') == 'account.account'
            if not is_grouped_by_account or not line:

                # No group code found in any lines, compute it automatically.
                no_group_hierarchy = {}
                for no_group_line in no_group_lines:
                    codes = [('root', str(line.get('parent_id')) or 'root'), (self.LEAST_SORT_PRIO, _('(No Group)'))]
                    if not accounts_hierarchy:
                        account = get_account(no_group_line.get('account_id', no_group_line.get('id')))
                        codes = [('root', str(line.get('parent_id')) or 'root')] + self.get_account_codes(account)
                    add_line_to_hierarchy(no_group_line, codes, no_group_hierarchy, line.get('level', 1))
                no_group_lines = []

                deep_merge_dict(no_group_hierarchy, accounts_hierarchy)

                # Merge the newly created hierarchy with existing lines.
                if accounts_hierarchy:
                    new_lines += get_hierarchy_lines(accounts_hierarchy)[1]
                    accounts_hierarchy = {}

                if line:
                    new_lines.append(line)
                continue

            # Exclude lines having no group.
            account = get_account(line.get('account_id', line.get('id')))
            if not account.group_id:
                no_group_lines.append(line)
                continue

            codes = [('root', str(line.get('parent_id')) or 'root')] + self.get_account_codes(account)
            add_line_to_hierarchy(line, codes, accounts_hierarchy, line.get('level', 0) + 1)

        return new_lines
        
    def get_html(self, options, line_id=None, additional_context=None):
        '''
        return the html value of report, or html value of unfolded line
        * if line_id is set, the template used will be the line_template
        otherwise it uses the main_template. Reason is for efficiency, when unfolding a line in the report
        we don't want to reload all lines, just get the one we unfolded.
        '''
        # Check the security before updating the context to make sure the options are safe.
        self._check_report_security(options)

        # Prevent inconsistency between options and context.
        self = self.with_context(self._set_context(options))

        templates = self._get_templates()
        report_manager = self._get_report_manager(options)
        cids = request.httprequest.cookies.get('cids', str(request.env.user.company_id.id))
        company_ids = [int(cid) for cid in cids.split(',')]
        user_company = self.env['res.company'].browse(company_ids[0])
        report = {'name': self._get_report_name(),
                  'summary': report_manager.summary,
                  'company_name': user_company.name,
                  'company_id': user_company}
        lines = self._get_lines(options, line_id=line_id)

        if options.get('hierarchy_parent'):
            selected_account_level = None
            
            if options.get('selected_account_level'):
                selected_account_level = options.get('selected_account_level')
                
            lines = self._create_hierarchy(lines, options, display_parent_only=True, account_level=selected_account_level)
        elif options.get('hierarchy'):
            lines = self._create_hierarchy(lines, options)
        if options.get('selected_column'):
            lines = self._sort_lines(lines, options)

        footnotes_to_render = []
        if self.env.context.get('print_mode', False):
            # we are in print mode, so compute footnote number and include them in lines values, otherwise, let the js compute the number correctly as
            # we don't know all the visible lines.
            footnotes = dict([(str(f.line), f) for f in report_manager.footnotes_ids])
            number = 0
            for line in lines:
                f = footnotes.get(str(line.get('id')))
                if f:
                    number += 1
                    line['footnote'] = str(number)
                    footnotes_to_render.append({'id': f.id, 'number': number, 'text': f.text})

        rcontext = {'report': report,
                    'lines': {'columns_header': self.get_header(options), 'lines': lines},
                    'options': options,
                    'context': self.env.context,
                    'model': self,
                }
        if additional_context and type(additional_context) == dict:
            rcontext.update(additional_context)
        if self.env.context.get('analytic_account_ids'):
            rcontext['options']['analytic_account_ids'] = [
                {'id': acc.id, 'name': acc.name} for acc in self.env.context['analytic_account_ids']
            ]

        render_template = templates.get('main_template', 'account_reports.main_template')
        if line_id is not None:
            render_template = templates.get('line_template', 'account_reports.line_template')
        html = self.env['ir.ui.view'].render_template(
            render_template,
            values=dict(rcontext),
        )
        if self.env.context.get('print_mode', False):
            for k,v in self._replace_class().items():
                html = html.replace(k, v)
            # append footnote as well
            html = html.replace(b'<div class="js_account_report_footnotes"></div>', self.get_html_footnotes(footnotes_to_render))
        return html
    
    def _get_options(self, previous_options=None):
        # Create default options.
        options = {
            'unfolded_lines': previous_options and previous_options.get('unfolded_lines') or [],
            'filter_accounts_ledger': previous_options and previous_options.get('filter_accounts_ledger') or None
        }

        # Multi-company is there for security purpose and can't be disabled by a filter.
        self._init_filter_multi_company(options, previous_options=previous_options)

        # Call _init_filter_date/_init_filter_comparison because the second one must be called after the first one.
        if self.filter_date:
            self._init_filter_date(options, previous_options=previous_options)
        if self.filter_comparison:
            self._init_filter_comparison(options, previous_options=previous_options)
        if self.filter_multi_currency:
            self._init_multi_currency(options, previous_options=previous_options)
        
        if self.filter_hierarchy_parent != None:
            self._init_hierarchy_parent(options, previous_options=previous_options)
        
        if self.filter_analytic:
            options['analytic'] = self.filter_analytic   
        filter_list = [attr for attr in dir(self)
                       if (attr.startswith('filter_') or attr.startswith('order_')) and attr not in ('filter_date', 'filter_comparison') and len(attr) > 7 and not callable(getattr(self, attr))]
        
        for filter_key in filter_list:
            options_key = filter_key[7:]
            init_func = getattr(self, '_init_%s' % filter_key, None)
            if init_func:
                init_func(options, previous_options=previous_options)
            else:
                filter_opt = getattr(self, filter_key, None)
                if filter_opt is not None:
                    if previous_options and options_key in previous_options:
                        options[options_key] = previous_options[options_key]
                    else:
                        options[filter_key[7:]] = filter_opt
          
        if self.filter_multi_currency:
            options['multi_currency'] = self._get_multi_currency(options, selected_multi_currency=options.get('selected_multi_currency'))
        if request.session.get("search_values"):
            options['search_values'] = request.session.get('search_values')
        return options
    
    def _set_context(self, options):
        """This method will set information inside the context based on the options dict as some options need to be in context for the query_get method defined in account_move_line"""
        ctx = super(AccountReport, self)._set_context(options)
        if options.get('selected_multi_currency'):
            ctx['selected_multi_currency'] = options.get('selected_multi_currency')
        
        if options.get('selected_account_level'):
            ctx['selected_account_level'] = options.get('selected_account_level')
        if options.get('account_ids'):
            ctx['account_ids'] = self.env['account.account'].browse([int(account) for account in options['account_ids']])
        return ctx
    
    def get_report_informations(self, options):
        info = super(AccountReport, self).get_report_informations(options)
        options = self._get_options(options)
        if options.get('accounts'):
            options['selected_account_ids'] = [self.env['account.account'].browse(int(account)).name for account in options['account_ids']]
            info.update({'options': options})
          
        return info
    
    def _init_multi_currency(self, options, previous_options=None):
        if self.filter_multi_currency is None:
            return
        
        company_changed = False
        if (previous_options and previous_options.get('multi_company') != options.get('multi_company')):
           company_changed = True 
        # Handle previous_options.
        if previous_options and previous_options.get('selected_multi_currency') and not company_changed:
            selected_multi_currency = previous_options.get('selected_multi_currency')
        else:
            selected_multi_currency =  self.get_selected_company().currency_id.id
            
        options['selected_multi_currency'] = selected_multi_currency
       
    def _init_hierarchy_parent(self, options, previous_options=None):
        if self.filter_hierarchy_parent is None:
            return
        
        if previous_options and previous_options.get('selected_account_level'):
            selected_account_level = previous_options.get('selected_account_level')
        else:
            selected_account_level = False
            
        options['selected_account_level'] = selected_account_level
        
    def _get_multi_currency(self, options, selected_multi_currency):
        company_id = self.get_selected_company()
        
        filter_multi_currency = self.user_has_groups('base.group_multi_currency')
        if filter_multi_currency:
            if company_id:
                currency_selected = True if selected_multi_currency and selected_multi_currency == company_id.currency_id.id else False
                multi_currency_list = [{'id': company_id.currency_id.id, 'name': company_id.currency_id.name, 'selected': currency_selected}]
                if company_id.second_currency_id.id:
                    second_currency_selected = True if selected_multi_currency and selected_multi_currency == company_id.second_currency_id.id else False
                    multi_currency_list.append({'id': company_id.second_currency_id.id, 'name': company_id.second_currency_id.name, 'selected': second_currency_selected})
                if company_id.third_currency_id.id:
                    third_currency_selected = True if selected_multi_currency and selected_multi_currency == company_id.third_currency_id.id else False
                    multi_currency_list.append({'id': company_id.third_currency_id.id, 'name': company_id.third_currency_id.name, 'selected': third_currency_selected})
        else:
           multi_currency_list = [{'id': company_id.currency_id.id, 'name': company_id.currency_id.name, 'selected': True}]
           
        return multi_currency_list
    
    def _check_report_security(self, options):
        '''The security check must be done in this method. It ensures no-one can by-passing some access rules
        (e.g. falsifying the options).

        :param options:     The report options.
        '''
        super(AccountReport, self)._check_report_security(options)
        
        # Check the options has not been falsified in order to access not allowed companies.
        if options.get('multi_currency'):
            group_multi_currency = self.env.ref('base.group_multi_currency')
            if self.env.user.id not in group_multi_currency.users.ids:
                options.pop('multi_currency')
    
    def format_value(self, amount, currency=False, blank_if_zero=False):
       context = self.env.context
       if currency:
           currency_id = currency
       elif context.get('selected_multi_currency'):
           currency_id = self.env['res.currency'].browse(int(context.get('selected_multi_currency')) if context.get('selected_multi_currency') else company_id.currency_id.id)
       else:
           currency_id = self.get_selected_company().currency_id

       if context.get('no_format'):
           return amount
       
       if not amount:
            amount = 0
       if currency_id.is_zero(amount):
           if blank_if_zero:
                return ''
           # don't print -0.0 in reports
           amount = abs(amount)
       
       res = formatLang(self.env, amount, currency_obj=currency_id)
       
       return res

    def open_general_ledger(self, options, params=None):
        if not params:
            params = {}
        ctx = self.env.context.copy()
        ctx.pop('id', '')
        action = self.env.ref('account_reports.action_account_report_general_ledger').read()[0]
        account_id = self._get_caret_option_target_id(params.get('id'))
        options['unfolded_lines'] = ['account_%s' % account_id]
        options['unfold_all'] = False
        
        account_id = self.env['account.account'].browse(account_id)
        if account_id:
            account_name = "%s %s" % (account_id.code, account_id.name)
            options['filter_accounts_ledger'] = account_name
            
        ctx.update({'model': 'account.general.ledger' , 'filter_accounts_ledger_flag': True})
        action.update({'options': options, 'context': ctx, 'ignore_session': 'read'})
        return action
    
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

        #Set the first column width to 50
        sheet.set_column(0, 0, 50)

        super_columns = self._get_super_columns(options)
        y_offset = bool(super_columns.get('columns')) and 1 or 0

        sheet.write(y_offset, 0, '', title_style)

        # Todo in master: Try to put this logic elsewhere
        x = super_columns.get('x_offset', 0)
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
            if cell_type == 'date':
                sheet.write_datetime(y + y_offset, 0, cell_value, date_default_col1_style)
            else:
                sheet.write(y + y_offset, 0, cell_value, col1_style)

            #write all the remaining cells
            for x in range(1, len(lines[y]['columns']) + 1):
                cell_type, cell_value = self._get_cell_type_value(lines[y]['columns'][x - 1])
                if cell_type == 'date':
                    sheet.write_datetime(y + y_offset, x + lines[y].get('colspan', 1) - 1, cell_value, date_default_style)
                else:
                    sheet.write(y + y_offset, x + lines[y].get('colspan', 1) - 1, cell_value, style)

        workbook.close()
        output.seek(0)
        generated_file = output.read()
        output.close()

        return generated_file   