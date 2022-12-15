from odoo import models, fields, api, _
from datetime import datetime
import logging
from werkzeug.urls import url_encode

log = logging.getLogger(__name__)

class AccountPayment(models.Model):
    _inherit = 'account.payment'
    
    account_amount = fields.Float('Account Amount', help='Amount to be recorded in the SOA')
    account_currency_id = fields.Many2one('res.currency', 'Account Currency', help='Account Currency', default=lambda self: self.env.company.currency_id)
    company_currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    invoice_total_amount = fields.Monetary()
    payment_rate = fields.Float('Main Payment Rate')
    
    @api.onchange('account_currency_id', 'amount', 'currency_id', 'account_amount')
    def _compute_payment_rate(self):
        for record in self:
            if not record.payment_rate or record.account_currency_id != record.currency_id:
                if record.account_currency_id == record.company_currency_id:
                    record.payment_rate = record.account_amount / record.amount if record.amount else 1.0
                elif record.currency_id == record.company_currency_id:
                    record.payment_rate = record.amount / record.account_amount if record.account_amount else 1.0
                else:
                    record.payment_rate = record.account_currency_id.rate and (record.company_currency_id.rate / record.account_currency_id.rate) or record.company_currency_id.rate
            elif record.account_currency_id == record.currency_id and record.account_currency_id == record.company_currency_id:
                record.payment_rate = 1.0
                
    @api.onchange('account_amount', 'account_currency_id', 'currency_id')
    def azk_onchnage_account(self):
        """
        On change of account amount or account currency, calculate the rate of the chosen currency_id 
        """
        if self.account_currency_id and self.account_currency_id != self.currency_id:
            rate = self.currency_id.rate / self.account_currency_id.rate
            self.amount = rate * self.account_amount
        else: 
            if self.account_currency_id == self.currency_id:
                if self.account_amount:
                    self.amount = self.account_amount
                else:
                    self.account_amount = self.amount
            
        log.debug('Called on change for account_ammount, account_currency_id, and currency_id on %s', self)
    
    @api.model
    def default_get(self, default_fields):
        rec = super(AccountPayment, self).default_get(default_fields)
        active_ids = self._context.get('active_ids') or self._context.get('active_id')
        active_model = self._context.get('active_model')

        # Check for selected invoices ids
        if not active_ids or active_model != 'account.move':
            return rec

        invoices = self.env['account.move'].browse(active_ids).filtered(lambda move: move.is_invoice(include_receipts=True))
        res = super().default_get(default_fields)
        res.update({"account_currency_id":invoices[0].currency_id.id, 'invoice_total_amount': invoices[0].amount_residual})
        
        return res
    
    @api.onchange('journal_id', 'invoice_ids')
    def azk_onchange_invoice_ids(self):
        """
        On change of invoice_ids, set the currency and amount of invoice  
        """
        for record in self:
            for invoice_id in record.invoice_ids:
                record.account_currency_id = invoice_id.currency_id
                record.account_amount = invoice_id.amount_residual
            
        log.debug('Called on change for invoice_ids on %s', self)
        
    @api.onchange('account_amount', 'amount')
    def azk_onchange_account_amount(self):
        if self.account_currency_id == self.currency_id:
            self.amount = self.account_amount  
    
    @api.depends('amount')
    def _compute_payment_difference(self):
        res = super(AccountPayment, self)._compute_payment_difference()
        draft_payments = self.filtered(lambda p: p.invoice_ids and p.state == 'draft')
        if draft_payments:
            for wizard in self:
                wizard._compute_payment_rate()
                if wizard.account_currency_id != wizard.currency_id:
                    if wizard.currency_id == wizard.company_currency_id:
                        total = wizard.invoice_total_amount * wizard.payment_rate
                    else:
                        rate = self.amount / self.account_amount if self.account_amount else 1.0
                        total = wizard.invoice_total_amount * rate
                    wizard.payment_difference = total - wizard.amount
                
        return res
    
    def _prepare_payment_moves(self):
        res =  super(AccountPayment, self)._prepare_payment_moves()
        write_off_account = self.writeoff_account_id.id if self.writeoff_account_id else None
        main_balance = 0
        debit, credit = 0, 0
        seq = []
        for line in res:
            journal_lines = line.get('line_ids')
            for journal in journal_lines:
                amount = 0
                currency_id = None
                amount_currency = 0
                if journal[2]["account_id"] in [self.partner_id.property_account_receivable_id.id, self.partner_id.property_account_payable_id.id]:
                    currency_id = self.account_currency_id.id
                    if write_off_account:
                        amount = self.account_currency_id._convert(self.invoice_total_amount, self.company_currency_id, self.company_id if self.company_id else self.env.company, self.payment_date)
                        amount_currency = self.invoice_total_amount
                    else:
                        amount = self.account_currency_id._convert(self.account_amount, self.company_currency_id, self.company_id if self.company_id else self.env.company, self.payment_date)
                        amount_currency = self.account_amount
                elif journal[2]["account_id"] in [self.journal_id.default_credit_account_id.id, self.journal_id.default_debit_account_id.id]:
                    amount = self.currency_id._convert(self.amount, self.company_currency_id, self.company_id if self.company_id else self.env.company, self.payment_date)
                    amount_currency = self.amount
                    currency_id = self.currency_id.id
                elif write_off_account and write_off_account == journal[2]["account_id"]:
                    currency_id = self.currency_id.id
                    total_amount = self.account_currency_id._convert(self.invoice_total_amount, self.company_currency_id, self.company_id if self.company_id else self.env.company, self.payment_date)
                    paid_amount = self.currency_id._convert(self.amount, self.company_currency_id, self.company_id if self.company_id else self.env.company, self.payment_date)
                    amount = total_amount - paid_amount
                    amount_currency = self.company_currency_id._convert(amount, self.currency_id, self.company_id if self.company_id else self.env.company, self.payment_date)
                
                amount = abs(amount)
                currency_id = currency_id if currency_id != self.company_currency_id.id else None
                amount_currency = abs(amount_currency) if currency_id else None
                if journal[2]["debit"] > 0:
                    journal[2]["debit"] = amount
                    if currency_id == self.company_currency_id or not amount_currency:
                        journal[2]["amount_currency"] =  0
                    else:
                        journal[2]["amount_currency"] =  amount_currency
                    debit = debit + amount
                else:
                    journal[2]["credit"] = amount
                    if currency_id == self.company_currency_id or not amount_currency:
                        journal[2]["amount_currency"] =  0
                    else:
                        journal[2]["amount_currency"] =  - amount_currency
                    credit = credit + amount
                journal[2]["currency_id"] = currency_id == self.company_currency_id and False or currency_id
                
            if debit - credit != 0:
                dex_currency_id = self.currency_id.id if self.currency_id != self.company_currency_id else None
                dex_debit = credit - debit if debit < credit else 0
                dex_credit = debit - credit if credit < debit else 0
                conv_amount = self.company_currency_id._convert(dex_debit if dex_debit else dex_credit, self.currency_id, self.company_id if self.company_id else self.env.company, self.payment_date)
                dex_amount_currency = conv_amount if dex_debit else -conv_amount
                dex_journal = self.company_id.currency_exchange_journal_id
                dex_account = dex_journal.default_debit_account_id.id if dex_debit else dex_journal.default_credit_account_id.id
                journal_lines.append((0, 0, {'name': 'DEX',
                                             'is_dex_line' : True,
                                             'debit': dex_debit,
                                             'credit': dex_credit,
                                             'currency_id': self.account_currency_id !=self.company_currency_id and  self.account_currency_id.id or False,
                                             'date_maturity': self.payment_date,
                                             'partner_id': self.partner_id.commercial_partner_id.id,
                                             'account_id': dex_account,
                                             'payment_id': self.id,
                                             'amount_residual': dex_debit if dex_debit else dex_credit
                                             }))
                
            for line in res:
                for det_line in line.get('line_ids'):
                    det_line[2]['credit'] = round(det_line[2]['credit'], self.company_currency_id.decimal_places)
                    det_line[2]['debit'] = round(det_line[2]['debit'], self.company_currency_id.decimal_places)
            
            for line in res:
                main_balance = sum(journal[2]['debit'] - journal[2]['credit'] for journal in line.get('line_ids'))
                
            if abs(main_balance) <= 1 and main_balance !=0:
                for line in res:
                    seq = [float(journal[2]['credit']) for journal in line.get('line_ids')]
                max_credit = max(seq)
                for line in res:
                    for det_line in line.get('line_ids'):
                        if round(det_line[2]['credit'], self.company_currency_id.decimal_places) == round(max_credit, self.company_currency_id.decimal_places):
                            det_line[2]['credit'] = max_credit + main_balance
                            break
                
        return res
    
    
class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'
    
    is_dex_line = fields.Boolean()
    
    @api.model
    def update_dex_lines(self):
        company_ids = self.env["res.company"].search([])
        for company in company_ids:
            dex_journal = company.currency_exchange_journal_id
            account_ids = []
            if dex_journal.default_credit_account_id:
                account_ids.append(dex_journal.default_credit_account_id.id)
            if dex_journal.default_debit_account_id:
                account_ids.append(dex_journal.default_debit_account_id.id)
            
            for aml in self.env["account.move.line"].search([("company_id","=",company.id),("account_id","in",account_ids),("move_id.state","=","posted")]):
                aml.is_dex_line = True
                
class ExpenseSheet(models.TransientModel):
    _inherit = "account.payment.register.form"
    
    account_amount_currency_id = fields.Many2one('res.currency', string='Account Amount Currency', required=True, default=lambda self: self.env.company.currency_id)
    account_amount_values = fields.Float(string="Account Amount Value")
    
    def expense_post_payment(self):
            context = self._context.copy()
            context.update({"default_amount": self.amount})
            exp = self.env["hr.expense.sheet"].search([('id', '=', context["active_id"])])
            exp.update({"state": 'done'})
         

            return super(
                ExpenseSheet, self.with_context(context)
            ).expense_post_payment()
    
    
    


    def _get_payment_vals(self):
        """ Hook for extension """
        return {
            'partner_type': 'supplier',
            'payment_type': 'outbound',
            'partner_id': self.partner_id.id,
            'partner_bank_account_id': self.partner_bank_account_id.id,
            'journal_id': self.journal_id.id,
            'company_id': self.company_id.id,
            'payment_method_id': self.payment_method_id.id,
            'amount': self.amount,
            'account_currency_id': self.account_amount_currency_id.id,
            'account_amount': self.account_amount_values,
            'currency_id': self.currency_id.id,
            'payment_date': self.payment_date,
            'communication': self.communication
        }

    def expense_post_payment(self):
        self.ensure_one()
        company = self.company_id
        self = self.with_context(force_company=company.id, company_id=company.id)
        context = dict(self._context or {})
        active_ids = context.get('active_ids', [])
        expense_sheet = self.env['hr.expense.sheet'].browse(active_ids)
        expense_sheet.update({"state": 'done'})

        # Create payment and post it
        payment = self.env['account.payment'].create(self._get_payment_vals())

        body = (
                    _("A payment of %s %s with the reference <a href='/mail/view?%s'>%s</a> related to your expense %s has been made.") % (
            payment.amount, payment.currency_id.symbol, url_encode({'model': 'account.payment', 'res_id': payment.id}),
            payment.name, expense_sheet.name))
        expense_sheet.message_post(body=body)

        account_move_lines_to_reconcile = self._prepare_lines_to_reconcile(
            payment.move_line_ids + expense_sheet.account_move_id.line_ids)
        account_move_lines_to_reconcile.reconcile()
        payment.post()

        return {'type': 'ir.actions.act_window_close'}
    
    
class ExpensesSheet(models.Model):
    _inherit = 'hr.expense.sheet'
    
    
    account_amount_value = fields.Float(string='Account Amount Value', compute='_compute_account_amount', store=True, tracking=True)
    account_currency = fields.Many2one('res.currency', string='Account Amount Currency' , compute='_get_account_amount_currency',default=lambda self: self.env.company.currency_id)
    
    
    @api.depends('expense_line_ids.total_amount')
    def _compute_account_amount(self):
        for sheet in self:
            sheet.account_amount_value = sum(sheet.expense_line_ids.mapped('total_amount'))
            
    @api.depends('expense_line_ids.currency_id')
    def _get_account_amount_currency(self):
        for sheet in self:
            for line in sheet.expense_line_ids:
                sheet.account_currency = line.currency_id.id
