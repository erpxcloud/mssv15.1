# -*- coding: utf-8 -*-
import datetime 
from odoo import models, fields, api
from odoo.exceptions import ValidationError
import pprint 

from odoo.tools import float_is_zero

import logging

log = logging.getLogger(__name__)


class DiffExchangeVoucher(models.TransientModel):
    _name = 'voucher.diff.exchange.wizard'
    _description = 'Difference Of Exchange Voucher Wizard'

    def _get_groups_domain(self):
        company_id = self.env.company
        group_ids = self.env['account.account'].search([('company_id', '=', company_id.id)]).mapped('group_id').ids
        
        return [('id', 'in', group_ids)]
    
    def _get_default_groups(self):
        company_id = self.env.company
        return self.env['account.account'].search([('company_id', '=', company_id.id), '|', ('group_id.code_prefix', '=like', '4%'), ('group_id.code_prefix', '=like', '5%')]).mapped('group_id').ids#self.env['account.group'].search(['|', ('code_prefix', '=like', '4%'), ('code_prefix', '=like', '5%')]).mapped('id')#self.env['account.group'].search([('code_prefix', 'in', ['4','5'])]).ids

    reason = fields.Char(string='Justification', required=True)
    up_to_date = fields.Date(required=True,
                             default=fields.Date.context_today, 
                             string='Up To Date',
                             help="Choose up to date of the period for which you want to automatically create the exchange difference entry.")
    group_ids = fields.Many2many('account.group', 
                                 string='Account Groups',
                                 help="Choose the groups whose accounts will be used to automatically create the exchange difference entry.",
                                 domain=_get_groups_domain,
                                 required=True,
                                 default=_get_default_groups)
    date = fields.Date(required=True, 
                       string='Journal Entry Date',
                       help="Choose the date of the journal entry.")
    journal_id = fields.Many2one("account.journal", required=True)
    debit_account_id = fields.Many2one('account.account', 
                                       string='Debit account',  
                                       required=True, 
                                       domain=[('deprecated', '=', False)])
    credit_account_id = fields.Many2one('account.account', 
                                        string='Credit account', 
                                        required=True, 
                                        domain=[('deprecated', '=', False)])
     
    currency_id = fields.Many2one('res.currency', required=True)
    
    @api.onchange('up_to_date')
    def onchange_up_to_date(self):
        if self.up_to_date:
            self.date = self.up_to_date
            
    @api.onchange('journal_id')
    def onchange_journal_id(self):
        if self.journal_id:
            self.debit_account_id = self.journal_id.default_debit_account_id
            self.credit_account_id = self.journal_id.default_credit_account_id
              
    def _create_move(self, currency_rate=0,wiz_currency_id=False):
        """Create the automatic journal entry, Filter journal entries with date up to DEX upto date, by the selected currency and the selected groups of account.
        Journal entries are grouped by account, and by account with partner both of it are treated the same where the DEX amount is calculated as follow
        
        Main currency amount = Total amount currency / currency_rate - initial main currency amount
        Second currency amount = Total amount currency * second_currency_rate - initial second currency amount
        Third currency amount = Total amount currency * third_currency_rate - initial third currency amount
        
        After getting DEX amounts for all currencies, close the JV by calculating total amount of each currency knowing that its different than 0, and related to credit or debit
        account of the selected journal
        """
        
        currency_id = self.currency_id.id
        company_id = self.journal_id.company_id
        account_move = False
        
        currency_ids = [currency_id]
        if currency_id == company_id.currency_id.id:
            currency_ids = [currency_id, False]
            
        qset_list = [('move_id.state','=','posted'), ('move_id.date','<=',self.up_to_date), ('currency_id','in',currency_ids), ('account_id.group_id','in',self.group_ids.ids)]
        
        account_move_lines = self.env['account.move.line'].search(qset_list)
        
        if currency_rate == 0:
                currency_rate = self.env['res.currency.rate'].search([('company_id','=',company_id.id), ('name','<=',self.up_to_date),
                                                                      ('currency_id','=',currency_id)], 
                                                                    limit=1, order="name desc").rate
                
        log.info("Retrieved %s journal items grouped by currency: %s", len(account_move_lines), self.currency_id)
        
        if account_move_lines:
            log.info("Creating Draft Journal Entry on journal: %s, date: %s, reason: %s", self.journal_id, self.date, self.reason)
            move_vals = {
                'date': self.date,
                'ref': "%s with rate %s for %s at %s" %(self.reason,round(1/currency_rate,3),self.currency_id.name,self.up_to_date),
                'journal_id': self.journal_id.id,
                'state': 'draft',
            }
            
            account_group_dict = {}
            account_group_partner_dict = {}
            
            for account_move_line in account_move_lines:
                total_amount_currency = account_move_line.amount_currency if account_move_line.currency_id and account_move_line.currency_id != company_id.currency_id else (account_move_line.debit - account_move_line.credit)
                total_main_currency = (account_move_line.debit - account_move_line.credit)
                total_second_currency = (account_move_line.second_debit - account_move_line.second_credit)
                total_third_currency = (account_move_line.third_debit - account_move_line.third_credit)
                    
                if account_move_line.account_id and account_move_line.partner_id:
                    group_key = "%s-%s" % (account_move_line.partner_id.id, account_move_line.account_id)
                    if group_key not in account_group_partner_dict:      
                        
                        account_group_partner_dict[group_key] = {account_move_line.partner_id:  {
                                                                                    'total_amount_currency': total_amount_currency,
                                                                                    'total_main_currency': total_main_currency,
                                                                                    'total_second_currency': total_second_currency,
                                                                                    'total_third_currency': total_third_currency,
                            'account_id': account_move_line.account_id
                                                                                }
                                                                            }
                    else:
                        account_group_partner_dict[group_key][account_move_line.partner_id]['total_amount_currency'] +=  total_amount_currency
                        account_group_partner_dict[group_key][account_move_line.partner_id]['total_main_currency'] += total_main_currency
                        account_group_partner_dict[group_key][account_move_line.partner_id]['total_second_currency'] += total_second_currency
                        account_group_partner_dict[group_key][account_move_line.partner_id]['total_third_currency'] += total_third_currency
                        
                    
                elif account_move_line.account_id:
                    if account_move_line.account_id not in account_group_dict:
                        account_group_dict[account_move_line.account_id] = {
                            'total_amount_currency': total_amount_currency,
                            'total_main_currency': total_main_currency,
                            'total_second_currency': total_second_currency,
                            'total_third_currency': total_third_currency
                        }
                    else:
                        account_group_dict[account_move_line.account_id]['total_amount_currency'] += total_amount_currency 
                        account_group_dict[account_move_line.account_id]['total_main_currency'] += total_main_currency
                        account_group_dict[account_move_line.account_id]['total_second_currency'] += total_second_currency
                        account_group_dict[account_move_line.account_id]['total_third_currency'] += total_third_currency  
                
            if currency_rate == 0:
                currency_rate = self.env['res.currency.rate'].search([('company_id','=',company_id.id), ('name','<=',self.up_to_date),
                                                                      ('currency_id','=',currency_id)], 
                                                                    limit=1, order="name desc").rate #Currency selected 
            second_currency_rate = self.env['res.currency.rate'].search([('company_id','=',company_id.id), ('name','<=',self.up_to_date),
                                                                   ('currency_id','=',company_id.second_currency_id.id)], 
                                                                    limit=1, order="name desc").rate #Company second currency rate
            third_currency_rate = self.env['res.currency.rate'].search([('company_id','=',company_id.id), ('name','<=',self.up_to_date),
                                                                   ('currency_id','=',company_id.third_currency_id.id)], 
                                                                    limit=1, order="name desc").rate #Company third currency rate
            
            if wiz_currency_id and wiz_currency_id.id == company_id.second_currency_id.id:
                second_currency_rate = currency_rate
            if wiz_currency_id and wiz_currency_id.id == company_id.third_currency_id.id:
                third_currency_rate = currency_rate
                
            digits_rounding_precision = company_id.currency_id.rounding and company_id.currency_id.rounding or 1
            digits_second_currency_rounding_precision = company_id.second_currency_id.rounding and company_id.second_currency_id.rounding or 1
            digits_third_currency_rounding_precision = company_id.third_currency_id.rounding and company_id.third_currency_id.rounding or 1
            
            aml_list = []
            
            total_debit_credit = 0
            total_second_debit_credit = 0
            total_third_debit_credit = 0

            for account_id, result in account_group_dict.items():
                diff_amount_currency = 0
                total_amount_currency_main = result['total_amount_currency'] / currency_rate
                diff_main_currency = (total_amount_currency_main) - result['total_main_currency']
                diff_second_currency = (total_amount_currency_main * second_currency_rate) - result['total_second_currency']
                diff_third_currency = company_id.third_currency_id and (total_amount_currency_main * third_currency_rate) - result['total_third_currency'] or 0

                if not float_is_zero(diff_main_currency, precision_rounding=digits_rounding_precision) \
                    or  not float_is_zero(diff_second_currency, precision_rounding=digits_second_currency_rounding_precision) \
                    or  not float_is_zero(diff_third_currency, precision_rounding=digits_third_currency_rounding_precision):

                    line_val = {
                        'name':  "%s with rate %s for %s at %s" %(self.reason,round(1/currency_rate,3),self.currency_id.name,self.up_to_date),
                        'account_id': account_id.id,
                        'amount_currency': diff_amount_currency,
                        'currency_id': currency_id,
                        'debit': company_id.currency_id.round(diff_main_currency) if diff_main_currency > 0 else 0,
                        'credit': - company_id.currency_id.round(diff_main_currency) if diff_main_currency < 0 else 0,
                        'second_debit': company_id.second_currency_id.round(diff_second_currency) if diff_second_currency > 0 else 0,
                        'second_credit': - company_id.second_currency_id.round(diff_second_currency) if diff_second_currency < 0 else 0,
                        'third_debit': company_id.third_currency_id.round(diff_third_currency) if (company_id.third_currency_id and diff_third_currency > 0) else 0,
                        'third_credit': - company_id.third_currency_id.round(diff_third_currency) if (company_id.third_currency_id and diff_third_currency < 0) else 0,
                        'manual_entry_computation': True
                    }

                    total_debit_credit += company_id.currency_id.round(line_val['debit'] - line_val['credit'])
                    total_second_debit_credit += company_id.second_currency_id.round(line_val['second_debit'] - line_val['second_credit'])
                    if company_id.third_currency_id:
                        total_third_debit_credit += company_id.third_currency_id.round(line_val['third_debit'] - line_val['third_credit'])

                    aml_list.append((0, 0, line_val))

             
            for account_id, result in account_group_partner_dict.items():
                result_value = list(result.values())[0]
                diff_amount_currency = 0

                total_amount_currency_main = result_value['total_amount_currency'] / currency_rate
                diff_main_currency = (total_amount_currency_main) - result_value['total_main_currency']
                diff_second_currency = (total_amount_currency_main * second_currency_rate) - result_value['total_second_currency']
                diff_third_currency = 0
                if company_id.third_currency_id:
                    diff_third_currency = (total_amount_currency_main * third_currency_rate) - result_value['total_third_currency']


                if not float_is_zero(diff_main_currency, precision_rounding=digits_rounding_precision) \
                    or  not float_is_zero(diff_second_currency, precision_rounding=digits_second_currency_rounding_precision) \
                    or  not float_is_zero(diff_third_currency, precision_rounding=digits_third_currency_rounding_precision):

                    line_val = {
                        'name':  "%s with rate %s for %s at %s" %(self.reason,round(1/currency_rate,3),self.currency_id.name,self.up_to_date),
                        'account_id': result_value['account_id'].id,
                        'amount_currency': diff_amount_currency,
                        'partner_id': list(result.keys())[0].id,
                        'currency_id': currency_id,
                        'debit': company_id.currency_id.round(diff_main_currency) if diff_main_currency > 0 else 0,
                        'credit': - company_id.currency_id.round(diff_main_currency) if diff_main_currency < 0 else 0,
                        'second_debit': company_id.second_currency_id.round(diff_second_currency) if diff_second_currency > 0 else 0,
                        'second_credit': - company_id.second_currency_id.round(diff_second_currency) if diff_second_currency < 0 else 0,
                        'third_debit': company_id.third_currency_id.round(diff_third_currency) if (company_id.third_currency_id and diff_third_currency > 0) else 0,
                        'third_credit': - company_id.third_currency_id.round(diff_third_currency) if (company_id.third_currency_id and diff_third_currency < 0) else 0,
                        'manual_entry_computation': True
                    }

                    total_debit_credit += company_id.currency_id.round(line_val['debit'] - line_val['credit'])
                    total_second_debit_credit += company_id.second_currency_id.round(line_val['second_debit'] - line_val['second_credit'])
                    if company_id.third_currency_id:
                        total_third_debit_credit += company_id.third_currency_id.round(line_val['third_debit'] - line_val['third_credit'])

                    aml_list.append((0, 0, line_val))
            
            #If main currency
            if total_debit_credit != 0:
                aml_list.append((0, 0, {
                    'name':  "%s with rate %s for %s at %s" %(self.reason,round(1/currency_rate,3),self.currency_id.name,self.up_to_date),
                    'currency_id': currency_id,
                    'account_id': self.credit_account_id.id if total_debit_credit > 0 else self.debit_account_id.id,
                    'credit': total_debit_credit if total_debit_credit > 0 else 0,
                    'debit': -total_debit_credit if total_debit_credit < 0 else 0,
                    'manual_entry_computation': True
                }))
            
            #If second currency
            if total_second_debit_credit != 0:
                aml_list.append((0, 0, {
                    'name':  "%s with rate %s for %s at %s" %(self.reason,round(1/currency_rate,3),self.currency_id.name,self.up_to_date),
                    'currency_id': currency_id,
                    'account_id': self.credit_account_id.id if total_second_debit_credit > 0 else self.debit_account_id.id,
                    'second_credit': total_second_debit_credit if total_second_debit_credit > 0 else 0,
                    'second_debit': -total_second_debit_credit if total_second_debit_credit < 0 else 0,
                    'manual_entry_computation': True
                }))
            
            #If third currency
            if company_id.third_currency_id and total_third_debit_credit != 0:
                aml_list.append((0, 0, {
                    'name':  "%s with rate %s for %s at %s" %(self.reason,round(1/currency_rate,3),self.currency_id.name,self.up_to_date),
                    'currency_id': currency_id,
                    'account_id': self.credit_account_id.id if total_third_debit_credit > 0 else self.debit_account_id.id,
                    'third_credit': total_third_debit_credit if total_third_debit_credit > 0 else 0,
                    'third_debit': -total_third_debit_credit if total_third_debit_credit < 0 else 0,
                    'manual_entry_computation': True
                }))

            
            
            if aml_list:
                log.info("Creating Diff exchange for: %s account without partners and %s accounts with partners", len(account_group_dict), len(account_group_partner_dict)) 
                
                move_vals['line_ids'] = aml_list
                account_move = self.env['account.move'].create(move_vals)

        return account_move
        
    def create_move(self):
        "Generate an action showing the created move"
        # get if id of the created journal entry based on the selected type
        move_id = self._create_move() 
        
        result = False
        if move_id:
            # return an action showing the created move
            action = self.env.ref(self.env.context.get('action', 'account.action_move_line_form'))
            result = action.read()[0]
            result['views'] = [(False, 'form')]
            result['res_id'] = move_id.id
             
        return result
