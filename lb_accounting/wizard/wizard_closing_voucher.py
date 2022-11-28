# -*- coding: utf-8 -*-
import datetime 
from odoo import models, fields, api
from odoo.exceptions import ValidationError

import logging
import pprint
from vobject.base import readOne
from xml.dom.minidom import ReadOnlySequentialNamedNodeMap

log = logging.getLogger(__name__)


class ClosingVoucher(models.TransientModel):
    _name = 'voucher.closing.wizard'
    _description = 'Closing Voucher Wizard'

    
    def _get_default_journal(self):
        return self.env['account.journal'].search([('type', '=', 'general')], limit=1).id
    
    
    def _get_groups_domain(self):
        company_id = self.env.company
        group_ids = self.env['account.account'].search([('company_id', '=', company_id.id)]).mapped('group_id').ids
        return [('id', 'in', group_ids)]
    
    reason = fields.Char(string='Justification', required=True)
    closing_by = fields.Selection([('group', "Account Groups"), ('account', 'Accounts')],  string='Closing By',
                                  help='Choose the closing criteria for creating the journal entry.', default="group")
    to_date = fields.Date(required=True,string='End Date',
                          help="Choose the end date of the period for which you want to automatically create the closing entry.")
    group_ids = fields.Many2many('account.group',string='Account Groups',
                                 help="""Choose the groups whose accounts will be used to automatically create the closing entry. 
The returned accounts are filtered by the ones used on the current company chat of account
                                 """,
                                domain= _get_groups_domain)
    account_ids = fields.Many2many('account.account', string='Accounts',
                                 help="Choose the accounts that will be used to automatically create the closing entry.")
    journal_id = fields.Many2one('account.journal', string='Journal',  required=True,  default=_get_default_journal, domain=[('type', '=', 'general')],
                                 help="Choose the journal that will be used to automatically create the closing entry")
    date = fields.Date(required=True, default=fields.Date.context_today, string = 'Date', help="Choose the date of the journal entry.")
    debit_account_id = fields.Many2one('account.account', string='Debit account',  required=True, domain=[('deprecated', '=', False)])
    credit_account_id = fields.Many2one('account.account', string='Credit account', required=True, domain=[('deprecated', '=', False)])
    reconcile = fields.Boolean(string='Allow Reconciliation',  help="Check this box if you want to match the journal items of invoices and payments.", default=False, readonly=True)
    
    @api.onchange('journal_id')
    def _onchange_journal_id(self):
        """On change of the journal change the credit and debit accounts"""

        self.debit_account_id  = self.journal_id.default_debit_account_id
        self.credit_account_id  = self.journal_id.default_credit_account_id
    
    
        
    
    def _get_accounts_journal_items(self):
        """ get the ending balance and journal items for each account during the selected period based on the selected criteria """
        
        company_id = self.env.company
        account_lines = []
      
        if self.closing_by == 'group':
            group_ids = []
            for group in self.group_ids:
                group_ids.append(group.id)
            
            account_ids = self.env['account.account'].search([('group_id', 'in', group_ids), ('company_id', '=', company_id.id)])  
        else:
            account_ids = self.account_ids 
            
        date_to = self.to_date.strftime('%m/%d/%Y')
        company_id = self.env.company
        
        if len(account_ids.ids)>1:
            sql = ("select sum(balance)  main_balance,sum(second_balance)  second_balance,sum(third_balance)  third_balance,\
            account_id,analytic_account_id from account_move_line aml,account_move am where aml.date<='%s'\
             and am.state='posted' and aml.move_id = am.id and account_id in %s and am.company_id = %s group by account_id,analytic_account_id having (sum(balance) != 0 \
             or sum(second_balance)  != 0 or sum(third_balance)!= 0 );"%(date_to,tuple(account_ids.ids),company_id.id))
        else:
            sql = ("select sum(balance)  main_balance,sum(second_balance)  second_balance,sum(third_balance)  third_balance,\
            account_id,analytic_account_id from account_move_line aml,account_move am where aml.date<='%s'\
             and am.state='posted' and aml.move_id = am.id and account_id = %s and am.company_id = %s group by account_id,analytic_account_id having (sum(balance) != 0 \
             or sum(second_balance)  != 0 or sum(third_balance)!= 0 );"%(date_to,account_ids.ids[0],company_id.id))
            
        self.env.cr.execute(sql)
        res = self.env.cr.fetchall()
        line_ids, total_balance, second_balance, third_balance, reconcile = [], 0, 0, 0, []
        if res:
            for line_res in res:
                line_id = self._get_moves_journal_item(line_res[0],line_res[1],line_res[2],line_res[3],line_res[4])
                line_ids.append(line_id)
                total_balance += (-1) * line_res[0]
                second_balance += (-1) * line_res[1]
                third_balance += (-1) * line_res[2]
                
        accounts_line_ids = {"line_ids": line_ids, 'total_balance': total_balance, 'second_balance': second_balance, 'third_balance': third_balance, 'reconcile':  reconcile}
         
        log.info('_get_accounts_journal_items: get the ending balance and journal items for accounts the %s for the company %s until %s, %s', account_ids, company_id,  self.to_date.strftime('%Y-%m-%d'),  pprint.pformat(accounts_line_ids) )
         
        return accounts_line_ids
    
    def _get_moves_journal_item(self, balance, second_balance, third_balance, account_id, analytic_account_id):
        "Create the journal item info"
        
        #if balance is debit => create the journal item as credit 
        if balance >= 0: 
            debit, credit, =  0.0, abs(balance)
        else:
            debit, credit =  abs(balance), 0.0
             
        if second_balance >= 0: 
            second_debit, second_credit =  0.0, abs(second_balance)
        else:
            second_debit, second_credit =  abs(second_balance), 0.0
          
        if third_balance >= 0: 
            third_debit, third_credit  =  0.0, abs(third_balance)
        else:
            third_debit, third_credit =  abs(third_balance), 0.0
                
        vals = {
            'name': self.reason,
            'debit': debit,
            'credit': credit,
            'second_debit': second_debit,
            'second_credit': second_credit,
            'third_debit': third_debit,
            'analytic_account_id':analytic_account_id,
            'third_credit': third_credit,
            'account_id': account_id,
            'tax_line_id': False,
        }   
        
        # check if the account is assigned with any partner
        partner_id  = self.env['res.partner'].search(['|', ('property_account_receivable_id', '=', account_id ), ('property_account_payable_id', '=', account_id )], limit=1)

        if partner_id:
            vals['partner_id'] = partner_id.id
            
        log.info('_get_moves_journal_item: prepare the journal item info %s', pprint.pformat(vals) )
        
        return (0, 0, vals)
    
    
    def _get_total_balance_journal_item(self, total_balance, second_balance, third_balance):
        "Create the total balace journal item info"
        
        #if total_balance is debit => create the journal item as debit 
        total_balance = (-1) * total_balance
        second_balance = (-1) * second_balance
        third_balance = (-1) * third_balance
        
        if total_balance >= 0: 
            vals = {
                'name': self.reason,
                'debit': abs(total_balance),
                'credit': 0.0,
                'second_debit': second_balance>0 and second_balance or 0.0,
                'second_credit': second_balance<0 and -second_balance or 0.0,
                'third_debit': third_balance>0 and third_balance or 0.0,
                'third_credit': third_balance<0 and -third_balance or 0.0,
                'account_id': self.debit_account_id.id,
                'tax_line_id': False,
            }
        #if total_balance is credit => create the journal item as credit 
        else:
            vals = {
                'name': self.reason,
                'debit': 0.0,
                'credit': abs(total_balance),
                'second_debit': second_balance>0 and second_balance or 0.0,
                'second_credit': second_balance<0 and -second_balance or 0.0,
                'third_debit': third_balance>0 and third_balance or 0.0,
                'third_credit': third_balance<0 and -third_balance or 0.0,
                'account_id': self.credit_account_id.id,
                'tax_line_id': False,
            }
            
        log.info('_get_total_balance_journal_item: the total balance journal item details %s', pprint.pformat(vals) )
        
        return (0, 0, vals)
    
    
    def _create_move(self):
        "Create the automatic journal entry"
        line_ids = []
        accounts_line_ids = self._get_accounts_journal_items()
        
        # prepare the total balance journal item details 
        if accounts_line_ids['total_balance'] != 0 or accounts_line_ids['second_balance'] != 0 or accounts_line_ids['third_balance'] != 0:
            total_balance_line_id = self._get_total_balance_journal_item(accounts_line_ids['total_balance'], accounts_line_ids['second_balance'], accounts_line_ids['third_balance'])
            line_ids.append( total_balance_line_id )
        
        line_ids += accounts_line_ids['line_ids']
            
        #create the move without posting
        vals = {
            'journal_id': self.journal_id.id,
            'date': self.date,
            'ref': self.reason,
            'state': 'draft',
            'line_ids': line_ids
        }
        
        log.debug('_create_move: creating the unposted journal entry with journal %s date %s and line_ids %s', self.journal_id, self.date, line_ids)
       
        move = self.env['account.move'].with_context({'manual_entry_computation': True}).create(vals)
   
        return move.id
       
    
    def create_move_action(self):
        return self.create_move()

    def create_move(self):
        "Generate an action showing the created move"
        
        # get if id of the created journal entry based on the selected type
        move_id = self._create_move() 
        
        # return an action showing the created move
        action = self.env.ref(self.env.context.get('action', 'account.action_move_line_form'))
        result = action.read()[0]
        result['views'] = [(False, 'form')]
        result['res_id'] = move_id
        
        return result