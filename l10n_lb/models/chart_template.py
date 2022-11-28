# -*- coding: utf-8 -*-

from odoo.exceptions import AccessError
from odoo import api, fields, models, _
from odoo import SUPERUSER_ID
from odoo.exceptions import UserError
from odoo.tools import pycompat
from odoo.http import request

import logging

log = logging.getLogger(__name__)

class AccountChartTemplateInherit(models.Model):
    _inherit = "account.chart.template"

    vat_closing_account_id = fields.Many2one('account.account.template', string='VAT CLosing Account')
    year_closing_account_id = fields.Many2one('account.account.template', string='Year CLosing Account')
    
    payable_group = fields.Many2one('account.group', string="Payable Group")
    payable_vat_group = fields.Many2one('account.group', string="Payable VAT Group")
    
    receivable_group = fields.Many2one('account.group', string="Receivable Group")
    receivable_vat_group = fields.Many2one('account.group', string="Receivable VAT Group")
    
    temporary_receivable_account = fields.Many2one('account.account.template', string='Temporary Receivable Account')
    temporary_payable_account = fields.Many2one('account.account.template', string='Temporary Payable Account')
    

    def generate_properties(self, acc_template_ref, company):
        """
        This method used for creating properties.

        :param acc_template_ref: Mapping between ids of account templates and real accounts created from them
        :param company_id: company to generate properties for.
        :returns: True
        """
        
        res = super(AccountChartTemplateInherit, self).generate_properties(acc_template_ref, company)
        
        temporary_properties = [
            'temporary_receivable_account',
            'temporary_payable_account',
        ]
        for temporary_property in temporary_properties:
            account = getattr(self, temporary_property)
            value = account and acc_template_ref[account.id] or False
            if value:
                company.write({temporary_property: value})
        
        return True
    
    def _prepare_all_journals(self, acc_template_ref, company, journals_dict=None):
        def _get_default_account(journal_vals, type='debit'):
            # Get the default accounts
            default_account = False
            if journal['type'] == 'sale':
                default_account = acc_template_ref.get(self.property_account_income_categ_id.id)
            elif journal['type'] == 'purchase':
                default_account = acc_template_ref.get(self.property_account_expense_categ_id.id)
            elif journal['type'] == 'general' and journal['code'] == _('EXCH'):
                if type=='credit':
                    default_account = acc_template_ref.get(self.income_currency_exchange_account_id.id)
                else:
                    default_account = acc_template_ref.get(self.expense_currency_exchange_account_id.id)
            elif journal['type'] == 'general' and journal['code'] == _('VAT'):
                default_account = acc_template_ref.get(self.vat_closing_account_id.id)
            elif journal['type'] == 'general' and journal['code'] == _('EOY'):
                default_account = acc_template_ref.get(self.year_closing_account_id.id)  
                
            return default_account

        journals = [{'name': _('Sales'), 'type': 'sale', 'code': _('INV'), 'favorite': True, 'color': 11, 'sequence': 5},
                    {'name': _('Bills'), 'type': 'purchase', 'code': _('BILL'), 'favorite': True, 'color': 11, 'sequence': 6},
                    {'name': _('Miscellaneous Operations'), 'type': 'general', 'code': _('MISC'), 'favorite': True, 'sequence': 7},
                    {'name': _('Exchange Difference'), 'type': 'general', 'code': _('EXCH'), 'favorite': True, 'sequence': 9},
                    {'name': _('Cash Basis Tax Journal'), 'type': 'general', 'code': _('CABA'), 'favorite': True, 'sequence': 10},
                    {'name': _('VAT Closing'), 'type': 'general', 'code': _('VAT'), 'favorite': True, 'sequence': 11},
                    {'name': _('Year Closing'), 'type': 'general', 'code': _('EOY'), 'favorite': True, 'sequence': 12}]
        if journals_dict != None:
            journals.extend(journals_dict)

        self.ensure_one()
        journal_data = []
        for journal in journals:
            vals = {
                'type': journal['type'],
                'name': journal['name'],
                'code': journal['code'],
                'company_id': company.id,
                'default_credit_account_id': _get_default_account(journal, 'credit'),
                'default_debit_account_id': _get_default_account(journal, 'debit'),
                'show_on_dashboard': journal['favorite'],
                'color': journal.get('color', False),
                'sequence': journal['sequence']
            }
            journal_data.append(vals)
        return journal_data
    
    
    def load_for_current_company(self, sale_tax_rate, purchase_tax_rate):
        res = super(AccountChartTemplateInherit, self).load_for_current_company(sale_tax_rate, purchase_tax_rate)
      
        # create the default contact group
        if request and request.session.uid:
            current_user = self.env['res.users'].browse(request.uid)
            company = current_user.company_id
        else:
            company = self.env.company
            
        vals = {
            'name': 'Default',
            'sequential': True,
            'receivable_code': 'C',
            'receivable_group': self.receivable_group.id,
            'receivable_vat_group':  self.receivable_vat_group.id,
            'payable_code': 'S',
            'payable_group': self.payable_group.id,
            'payable_vat_group':  self.payable_vat_group.id,
            'company_id': company.id
        }
        self.env['lb_accounting.contact_group'].create(vals)
        
        return res

class AccountTaxTemplateInherit(models.Model):
    _inherit = 'account.tax.template'

    vat_tax = fields.Boolean(string="Is VAT Tax")
    
    def _get_tax_vals(self, company, tax_template_to_tax):
        # Compute children tax ids
        children_ids = []
        for child_tax in self.children_tax_ids:
            if tax_template_to_tax.get(child_tax.id):
                children_ids.append(tax_template_to_tax[child_tax.id])
        self.ensure_one()
        val = {
            'name': self.name,
            'type_tax_use': self.type_tax_use,
            'amount_type': self.amount_type,
            'active': self.active,
            'company_id': company.id,
            'sequence': self.sequence,
            'amount': self.amount,
            'description': self.description,
            'price_include': self.price_include,
            'include_base_amount': self.include_base_amount,
            'analytic': self.analytic,
            'children_tax_ids': [(6, 0, children_ids)],
            'tax_exigibility': self.tax_exigibility,
            'vat_tax': self.vat_tax,
        }

        if self.tax_group_id:
            val['tax_group_id'] = self.tax_group_id.id
        return val

