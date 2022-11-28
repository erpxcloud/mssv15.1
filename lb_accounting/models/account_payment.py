# coding: utf-8
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
import datetime
import logging
import pprint
from locale import currency

log = logging.getLogger(__name__)

class AccountPayment(models.Model):
    _inherit = 'account.payment'
    
    def _prepare_payment_moves(self): 
        all_move_vals=super(AccountPayment,self)._prepare_payment_moves()
        for i in range(0, len(all_move_vals[0]['line_ids'])):
            all_move_vals[0]['line_ids'][i][2]['second_debit']= all_move_vals[0]['line_ids'][i][2]['debit'] * self.company_id.second_currency_id.rate
            all_move_vals[0]['line_ids'][i][2]['third_debit'] = all_move_vals[0]['line_ids'][i][2]['debit'] * self.company_id.third_currency_id.rate

            all_move_vals[0]['line_ids'][i][2]['second_credit'] = all_move_vals[0]['line_ids'][i][2]['credit'] * self.company_id.second_currency_id.rate
            all_move_vals[0]['line_ids'][i][2]['third_credit']=  all_move_vals[0]['line_ids'][i][2]['credit'] * self.company_id.third_currency_id.rate
        if(self.payment_type == 'transfer'):
            for i in range(0, len(all_move_vals[1]['line_ids'])):
                all_move_vals[1]['line_ids'][i][2]['second_debit']= all_move_vals[1]['line_ids'][i][2]['debit'] * self.company_id.second_currency_id.rate
                all_move_vals[1]['line_ids'][i][2]['third_debit'] = all_move_vals[1]['line_ids'][i][2]['debit'] * self.company_id.third_currency_id.rate

                all_move_vals[1]['line_ids'][i][2]['second_credit'] = all_move_vals[1]['line_ids'][i][2]['credit'] * self.company_id.second_currency_id.rate
                all_move_vals[1]['line_ids'][i][2]['third_credit']=  all_move_vals[1]['line_ids'][i][2]['credit'] * self.company_id.third_currency_id.rate
                
        return all_move_vals
    
    def post(self):
        res = None
        for line in self:
            res = super(AccountPayment, line.with_context(rate_date=line.payment_date)).post()
        return res