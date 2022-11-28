#-*- coding:utf-8 -*-

import base64

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_is_zero
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import UserError, ValidationError
import logging

log = logging.getLogger(__name__)

class HrContract(models.Model):
    _inherit = 'hr.contract'

    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Tags')


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'
    
    def action_payslip_done(self):
        """
            Generate the accounting entries related to the selected payslips
            A move is created for each journal and for each month.
        """
        
        if any(slip.state == 'cancel' for slip in self):
            raise ValidationError(_("You can't validate a cancelled payslip."))
        self.write({'state' : 'done'})
        self.mapped('payslip_run_id').action_close()
        if self.env.context.get('payslip_generate_pdf'):
            for payslip in self:
                if not payslip.struct_id or not payslip.struct_id.report_id:
                    report = self.env.ref('hr_payroll.action_report_payslip', False)
                else:
                    report = payslip.struct_id.report_id
                pdf_content, content_type = report.render_qweb_pdf(payslip.id)
                if payslip.struct_id.report_id.print_report_name:
                    pdf_name = safe_eval(payslip.struct_id.report_id.print_report_name, {'object': payslip})
                else:
                    pdf_name = _("Payslip")
                self.env['ir.attachment'].create({
                    'name': pdf_name,
                    'type': 'binary',
                    'datas': base64.encodestring(pdf_content),
                    'res_model': payslip._name,
                    'res_id': payslip.id
                })
                
        precision = self.env['decimal.precision'].precision_get('Payroll')

        # Add payslip without run
        payslips_to_post = self.filtered(lambda slip: not slip.payslip_run_id)

        # Adding pay slips from a batch and deleting pay slips with a batch that is not ready for validation.
        payslip_runs = (self - payslips_to_post).mapped('payslip_run_id')
        for run in payslip_runs:
            if run._are_payslips_ready():
                payslips_to_post |= run.slip_ids

        # A payslip need to have a done state and not an accounting move.
        payslips_to_post = payslips_to_post.filtered(lambda slip: slip.state == 'done' and not slip.move_id)

        # Check that a journal exists on all the structures
        if any(not payslip.struct_id for payslip in payslips_to_post):
            raise ValidationError(_('One of the contract for these payslips has no structure type.'))
        if any(not structure.journal_id for structure in payslips_to_post.mapped('struct_id')):
            raise ValidationError(_('One of the payroll structures has no account journal defined on it.'))

        # Map all payslips by structure journal and pay slips month.
        # {'journal_id': {'month': [slip_ids]}}
        slip_mapped_data = {slip.struct_id.journal_id.id: {fields.Date().end_of(slip.date_to, 'month'): self.env['hr.payslip']} for slip in payslips_to_post}
        for slip in payslips_to_post:
            slip_mapped_data[slip.struct_id.journal_id.id][fields.Date().end_of(slip.date_to, 'month')] |= slip
        
        for journal_id in slip_mapped_data: # For each journal_id.
            for slip_date in slip_mapped_data[journal_id]: # For each month.
                line_ids = []
                debit_sum = 0.0
                credit_sum = 0.0
                date = slip_date
                
                move_dict = {
                    'narration': '',
                    'ref': date.strftime('%B %Y'),
                    'journal_id': journal_id,
                    'date': date,
                }

                for slip in slip_mapped_data[journal_id][slip_date]:
                    company_id = slip.company_id or slip.struct_id.journal_id.company_id
                    currency = company_id.currency_id
                    payroll_currency = company_id.payroll_currency_id or currency
            
                    move_dict['narration'] += slip.number or '' + ' - ' + slip.employee_id.name or ''
                    move_dict['narration'] += '\n'
                    for line in slip.line_ids.filtered(lambda line: line.category_id):
                        amount = -line.total if slip.credit_note else line.total
                        if line.code == 'NET': # Check if the line is the 'Net Salary'.
                            for tmp_line in slip.line_ids.filtered(lambda line: line.category_id):
                                if tmp_line.salary_rule_id.not_computed_in_net: # Check if the rule must be computed in the 'Net Salary' or not.
                                    if amount > 0:
                                        amount -= abs(tmp_line.total)
                                    elif amount < 0:
                                        amount += abs(tmp_line.total)
                        if float_is_zero(amount, precision_digits=precision):
                            continue

                        partner_id = False
                        if (slip.employee_id.user_id.partner_id):
                            partner_id = slip.employee_id.user_id.partner_id.ids[0]
                        elif slip.employee_id.address_home_id:
                            partner_id = slip.employee_id.address_home_id.id
                            
                        amount_currency = amount
                        amount = payroll_currency._convert(amount_currency, currency, company_id, slip.date_from or fields.Date.today())
                        
                        employee = slip.employee_id
                        employee_account = employee.employee_account.search([('salary_rule','=',line.salary_rule_id.id), ('employee_id','=',employee.id)])
                        
                        if employee_account and employee_account.debit_account.id:
                            debit_account_id = employee_account.debit_account.id
                            debit_account = employee_account.debit_account
                        else:
                            debit_account_id = line.salary_rule_id.account_debit.id
                            debit_account = line.salary_rule_id.account_debit
                            
                        if employee_account and employee_account.credit_account.id:
                            credit_account_id = employee_account.credit_account.id
                            credit_account = employee_account.credit_account
                        else:
                            credit_account_id = line.salary_rule_id.account_credit.id
                            credit_account = line.salary_rule_id.account_credit
                            
                        analytic_tag_ids = [(4, analytic_tag.id, False) for analytic_tag in slip.contract_id.analytic_tag_ids]
                        
                        
                        if (not debit_account or not debit_account.internal_type in ('receivable', 'payable')) and (not credit_account or not credit_account.internal_type in ('receivable', 'payable')):
                            partner_id = False
                            
                        if debit_account_id: # If the rule has a debit account.
                            debit = amount if amount > 0.0 else 0.0
                            credit = -amount if amount < 0.0 else 0.0

                            existing_debit_lines = (
                                line_id for line_id in line_ids if
                                line_id['name'] == line.name
                                and (line_id['partner_id'] == line.partner_id  or not (debit_account.internal_type == 'payable' or debit_account.internal_type == 'receivable'))
                                and line_id['account_id'] == debit_account_id
                                and line_id['analytic_account_id'] == (line.salary_rule_id.analytic_account_id.id or slip.contract_id.analytic_account_id.id)
                                and ((line_id['debit'] > 0 and credit <= 0) or (line_id['credit'] > 0 and debit <= 0)))
                            debit_line = next(existing_debit_lines, False)
                            if not debit_line:
                                debit_line = {
                                    'name': line.name,
                                    'partner_id':partner_id,
                                    'account_id': debit_account_id,
                                    'journal_id': slip.struct_id.journal_id.id,
                                    'amount_currency': company_id.currency_id != payroll_currency and amount_currency or 0,
                                    'currency_id': company_id.currency_id != payroll_currency and payroll_currency.id or False,
                                    'date': date,
                                    'debit': debit,
                                    'credit': credit,
                                    'analytic_account_id': line.salary_rule_id.analytic_account_id.id or slip.contract_id.analytic_account_id.id,
                                    'analytic_tag_ids': analytic_tag_ids,
                                }
                                line_ids.append(debit_line)
                            else:
                                debit_line['debit'] += debit
                                debit_line['credit'] += credit
                                if company_id.currency_id != payroll_currency:
                                    debit_line['amount_currency'] += amount_currency
                        
                        if credit_account_id: # If the rule has a credit account.
                            debit = -amount if amount < 0.0 else 0.0
                            credit = amount if amount > 0.0 else 0.0
                            existing_credit_line = (
                                line_id for line_id in line_ids if
                                line_id['name'] == line.name
                                and line_id['account_id'] == credit_account_id
                                and (line_id['partner_id'] == line.partner_id or not (credit_account.internal_type == 'payable' or credit_account.internal_type == 'receivable'))
                                and line_id['analytic_account_id'] == (line.salary_rule_id.analytic_account_id.id or slip.contract_id.analytic_account_id.id)
                                and ((line_id['debit'] > 0 and credit <= 0) or (line_id['credit'] > 0 and debit <= 0))
                            )
                            credit_line = next(existing_credit_line, False)
                            
                            if not credit_line:
                                credit_line = {
                                    'name': line.name,
                                    'partner_id': partner_id,
                                    'account_id': credit_account_id,
                                    'journal_id': slip.struct_id.journal_id.id,
                                    'amount_currency': company_id.currency_id != payroll_currency and -amount_currency or 0,
                                    'currency_id': company_id.currency_id != payroll_currency and  payroll_currency.id or False,
                                    'date': date,
                                    'debit': debit,
                                    'credit': credit,
                                    'analytic_account_id': line.salary_rule_id.analytic_account_id.id or slip.contract_id.analytic_account_id.id,
                                    'analytic_tag_ids': analytic_tag_ids
                                }
                                line_ids.append(credit_line)
                            else:
                                credit_line['debit'] += debit
                                credit_line['credit'] += credit
                                if company_id.currency_id != payroll_currency:
                                    credit_line['amount_currency'] += -amount_currency

                for line_id in line_ids: # Get the debit and credit sum.
                    debit_sum += line_id['debit']
                    credit_sum += line_id['credit']

                # The code below is called if there is an error in the balance between credit and debit sum.
                if float_compare(credit_sum, debit_sum, precision_digits=precision) == -1:
                    acc_id = slip.journal_id.default_credit_account_id.id
                    if not acc_id:
                        raise UserError(_('The Expense Journal "%s" has not properly configured the Credit Account!') % (slip.journal_id.name))
                    existing_adjustment_line = (
                        line_id for line_id in line_ids if line_id['name'] == _('Adjustment Entry')
                    )
                    adjust_credit = next(existing_adjustment_line, False)

                    if not adjust_credit:
                        adjust_credit = {
                            'name': _('Adjustment Entry'),
                            'partner_id': False,
                            'account_id': acc_id,
                            'journal_id': slip.journal_id.id,
                            'date': date,
                            'debit': 0.0,
                            'credit': debit_sum - credit_sum,
                        }
                        line_ids.append(adjust_credit)
                    else:
                        adjust_credit['credit'] = debit_sum - credit_sum

                elif float_compare(debit_sum, credit_sum, precision_digits=precision) == -1:
                    acc_id = slip.journal_id.default_debit_account_id.id
                    if not acc_id:
                        raise UserError(_('The Expense Journal "%s" has not properly configured the Debit Account!') % (slip.journal_id.name))
                    existing_adjustment_line = (
                        line_id for line_id in line_ids if line_id['name'] == _('Adjustment Entry')
                    )
                    adjust_debit = next(existing_adjustment_line, False)

                    if not adjust_debit:
                        adjust_debit = {
                            'name': _('Adjustment Entry'),
                            'partner_id': False,
                            'account_id': acc_id,
                            'journal_id': slip.journal_id.id,
                            'date': date,
                            'debit': credit_sum - debit_sum,
                            'credit': 0.0,
                        }
                        line_ids.append(adjust_debit)
                    else:
                        adjust_debit['debit'] = credit_sum - debit_sum

                # Add accounting lines in the move
                
                move_dict['line_ids'] = [(0, 0, line_vals) for line_vals in line_ids]
                move = self.env['account.move'].create(move_dict)
                for slip in slip_mapped_data[journal_id][slip_date]:
                    slip.write({'move_id': move.id, 'date': date})
        return True