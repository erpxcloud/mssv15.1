from odoo import _, api, fields, models
import logging

_logger = logging.getLogger(__name__)

class ResCompanyInherit(models.Model):
    _inherit = "res.company"

    second_currency = fields.Many2one('res.currency', string='Second Currency')
    third_currency = fields.Many2one('res.currency', string='Third Currency')


class AccountMoveLineInherit(models.Model):
    _inherit = "account.move.line"

    x_original_amount = fields.Monetary()
    second_debit_id = fields.Monetary(string='Second Debit', default=0.0, readonly=False, store=True,
                                      compute="exchange_second_debit")
    second_credit_id = fields.Monetary(string='Second Credit', default=0.0, readonly=False, store=True,
                                       compute="exchange_second_credit")
    second_balance = fields.Monetary(string='Second Balance', default=0.0, readonly=False, store=True,
                                     compute="get_second_balance")
    third_debit_id = fields.Monetary(string='Third Debit', default=0.0, readonly=False, store=True,
                                     compute="exchange_third_debit")
    third_credit_id = fields.Monetary(string='Third Credit', default=0.0, readonly=False, store=True,
                                      compute="exchange_third_credit")
    third_balance = fields.Monetary(string='Third Balance', default=0.0, readonly=False, store=True,
                                    compute="get_third_balance")
    second_currency = fields.Many2one('res.currency', related ="company_id.second_currency")
    third_currency = fields.Many2one('res.currency', related ="company_id.third_currency")


    @api.depends('debit')
    def exchange_third_debit(self):
        for rec in self:
            third = rec.env['res.currency'].search([('id', '=', rec.company_id.third_currency.id)])
            rec.third_debit_id = rec.company_currency_id.compute(rec.debit, third)

    @api.depends('credit')
    def exchange_third_credit(self):
        for rec in self:
            third = rec.env['res.currency'].search([('id', '=', rec.company_id.third_currency.id)])
            rec.third_credit_id = rec.company_currency_id.compute(rec.credit, third)

    @api.depends('debit')
    def exchange_second_debit(self):
        for rec in self:
            second = rec.env['res.currency'].search([('id', '=', rec.company_id.second_currency.id)])
            rec.second_debit_id = rec.company_currency_id.compute(rec.debit, second)

    @api.depends('credit')
    def exchange_second_credit(self):  
        for rec in self:
            second = rec.env['res.currency'].search([('id', '=', rec.company_id.second_currency.id)])
            rec.second_credit_id = rec.company_currency_id.compute(rec.credit, second)

    @api.depends('second_debit_id', 'second_credit_id')
    def get_second_balance(self):
        for rec in self:
            rec.second_balance = rec.second_debit_id - rec.second_credit_id

    @api.depends('third_debit_id', 'third_credit_id')
    def get_third_balance(self):
        for rec in self:
            rec.third_balance = rec.third_debit_id - rec.third_credit_id
            

class AccountMove(models.Model):
    _inherit = 'account.move'
    
    second_amount = fields.Monetary(string='Second Amount', default=0.0, readonly=False, store=True,
                                    compute="exchange_second_amount")
#     third_amount = fields.Monetary(string='Third Amount', default=0.0, readonly=False, store=True,
#                                    compute="exchange_third_amount")
    second_currency = fields.Many2one('res.currency', related ="company_id.second_currency")
    third_currency = fields.Many2one('res.currency', related ="company_id.third_currency")
    
    @api.depends('amount_total','amount_residual')
    def exchange_second_amount(self):
        for rec in self:
            second = rec.env['res.currency'].search([('id', '=', rec.company_id.second_currency.id)])
            if rec.amount_residual:
                rec.second_amount = rec.currency_id.compute(rec.amount_residual, second)
            else:
                rec.second_amount = rec.currency_id.compute(rec.amount_total, second)


#     @api.depends('amount_total', 'amount_residual')
#     def exchange_third_amount(self):
#         for rec in self:
#             third = rec.env['res.currency'].search([('id', '=', rec.company_id.third_currency.id)])
#             if rec.amount_residual:
#                 rec.third_amount = rec.currency_id.compute(rec.amount_residual, third)
#             else:
#                 rec.third_amount = rec.currency_id.compute(rec.amount_total, third)
    
    
    @api.onchange('invoice_line_ids')
    def get_debit_credit(self):
        second = self.env['res.currency'].search([('id', '=', self.company_id.second_currency.id)])
        third = self.env['res.currency'].search([('id', '=', self.company_id.third_currency.id)])
        for l in self.line_ids:
            l.update(
                {'second_debit_id': l.company_currency_id.compute(l.debit, second),
                 'second_credit_id': l.company_currency_id.compute(l.credit, second),
                 'third_debit_id': l.company_currency_id.compute(l.debit, third),
                 'third_credit_id': l.company_currency_id.compute(l.credit, third), 
                }
            )
            
class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    def _create_invoices(self, grouped=False, final=False, date=None):
        res = super(SaleOrder, self)._create_invoices()
        if self.invoice_ids:
            for l in self.invoice_ids:
                l.get_debit_credit()
        return res
    
class PurchaseOrder(models.Model):
    _inherit = "purchase.order"
    
    def action_create_invoice(self):
        res = super(PurchaseOrder, self).action_create_invoice()
        if self.invoice_ids:
            for l in self.invoice_ids:
                l.get_debit_credit()
        return res
    
class StockPicking(models.Model):
    _inherit = "stock.picking"
    
    def button_validate(self):
        res = super(StockPicking, self).button_validate()
        for valuation in self.move_lines.stock_valuation_layer_ids.account_move_id:
            valuation.get_debit_credit()
        return res
        
    

#     def _prepare_invoice_line(self, **optional_values):
#         res = super(SaleOrderLine, self)._prepare_invoice_line(**optional_values)
#         res.update({'second_debit_id': 15111110000, 'third_debit_id': 15111110000})
#         return res

# class AccountMove(models.Model):
#     _inherit = "account.move"

#     def _recompute_payment_terms_lines(self):
#         ''' Compute the dynamic payment term lines of the journal entry.'''
#         self.ensure_one()
#         self = self.with_company(self.company_id)
#         in_draft_mode = self != self._origin
#         today = fields.Date.context_today(self)
#         self = self.with_company(self.journal_id.company_id)
#         def _compute_diff_payment_terms_lines(self, existing_terms_lines, account, to_compute):
#                 ''' Process the result of the '_compute_payment_terms' method and creates/updates corresponding invoice lines.
#                 :param self:                    The current account.move record.
#                 :param existing_terms_lines:    The current payment terms lines.
#                 :param account:                 The account.account record returned by '_get_payment_terms_account'.
#                 :param to_compute:              The list returned by '_compute_payment_terms'.
#                 '''
#                 # As we try to update existing lines, sort them by due date.
#                 existing_terms_lines = existing_terms_lines.sorted(lambda line: line.date_maturity or today)
#                 existing_terms_lines_index = 0

#                 # Recompute amls: update existing line or create new one for each payment term.
#                 new_terms_lines = self.env['account.move.line']
#                 for date_maturity, balance, amount_currency in to_compute:
#                     currency = self.journal_id.company_id.currency_id
#                     if currency and currency.is_zero(balance) and len(to_compute) > 1:
#                         continue

#                     if existing_terms_lines_index < len(existing_terms_lines):
#                         # Update existing line.
#                         candidate = existing_terms_lines[existing_terms_lines_index]
#                         existing_terms_lines_index += 1
#                         c = balance > 0.0 and balance or 0.0
#                         d = balance < 0.0 and -balance or 0.0
#                         candidate.update({
#                             'date_maturity': date_maturity,
#                             'amount_currency': -amount_currency,
#                             'debit': balance < 0.0 and -balance or 0.0,
#                             'credit': balance > 0.0 and balance or 0.0,
#                             'credit_usd': self.env['res.currency'].search([('name', '=', 'LBP')]).compute(c, self.env['res.currency'].search([('name', '=', 'USD')])),
#                             'debit_usd': self.env['res.currency'].search([('name', '=', 'LBP')]).compute(d, self.env['res.currency'].search([('name', '=', 'USD')]))
#                         })
#                     else:
#                         # Create new line.
#                         create_method = in_draft_mode and self.env['account.move.line'].new or self.env['account.move.line'].create
#                         candidate = create_method({
#                             'name': self.payment_reference or '',
#                             'debit': balance < 0.0 and -balance or 0.0,
#                             'credit': balance > 0.0 and balance or 0.0,
#                             'quantity': 1.0,
#                             'amount_currency': -amount_currency,
#                             'date_maturity': date_maturity,
#                             'move_id': self.id,
#                             'currency_id': self.currency_id.id,
#                             'account_id': account.id,
#                             'partner_id': self.commercial_partner_id.id,
#                             'exclude_from_invoice_tab': True,
#                         })
#                     new_terms_lines += candidate
#                     if in_draft_mode:
#                         candidate.update(candidate._get_fields_onchange_balance(force_computation=True))
#                 return new_terms_lines

#             existing_terms_lines = self.line_ids.filtered(lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
#             others_lines = self.line_ids.filtered(lambda line: line.account_id.user_type_id.type not in ('receivable', 'payable'))
#             company_currency_id = (self.company_id or self.env.company).currency_id
#             total_balance = sum(others_lines.mapped(lambda l: company_currency_id.round(l.balance)))
#             total_amount_currency = sum(others_lines.mapped('amount_currency'))

#             if not others_lines:
#                 self.line_ids -= existing_terms_lines
#                 return

#             computation_date = _get_payment_terms_computation_date(self)
#             account = _get_payment_terms_account(self, existing_terms_lines)
#             to_compute = _compute_payment_terms(self, computation_date, total_balance, total_amount_currency)
#             new_terms_lines = _compute_diff_payment_terms_lines(self, existing_terms_lines, account, to_compute)

#             # Remove old terms lines that are no longer needed.
#             self.line_ids -= existing_terms_lines - new_terms_lines

#             if new_terms_lines:
#                 self.payment_reference = new_terms_lines[-1].name or ''
#                 self.invoice_date_due = new_terms_lines[-1].date_maturity
