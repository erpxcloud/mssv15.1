from odoo import fields, models, api
import logging
import warnings

_logger = logging.getLogger(__name__)


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    payroll_slip_id = fields.Many2one('hr.payslip')
    visible_payroll_slip_id = fields.Boolean(string='Visibility', compute='compute_visibility', store='True')

    def compute_visibility(self):
        for payment in self:
            self.visible_payroll_slip_id = False
            if self.payroll_slip_id:
                self.visible_payroll_slip_id = True


class RegisterPaymentPayslips(models.Model):
    _inherit = 'hr.payslip'

    def _compute_payment(self):
        payment_obj = self.env['account.payment']
        self.payment_id = payment_obj.search([('payroll_slip_id', '=', self.id)])

#     def _compute_pay_amount(self):
#         for rec in self:
#             for line in rec.line_ids:
#                 payoff = line.search([('code', 'in', ('NET', 'LIQ')), ('slip_id', '=', self.id)])
#             rec.pay_amount = payoff.amount

    @api.depends('line_ids')
    @api.onchange('line_ids')
    def _compute_pay_amount(self):
        for slip in self:
            pay_amount_new = 0.0
            for line in slip.line_ids:
                if line.code == 'NET':
                    pay_amount_new+=line.total
            slip.pay_amount = pay_amount_new
    
    def register_payment(self):
        value_amount = self.pay_amount
        if self.state == 'done':
            payment_values = {
                'partner_type': 'supplier',
                'payment_type': 'outbound',
                'partner_id': self.employee_id.address_home_id.id,
                #                 'journal_id': self.journal_id.id,
                #                 'payment_method_id': self.payment_method_id.id,
                'company_id': self.company_id.id,
                'amount': value_amount,
                'currency_id': self.currency_id.id,
                'date': self.date_to,
                'ref': self.number + ' - ' + self.name,
                'payroll_slip_id': self.id,

            }
        payment = self.env['account.payment'].create(payment_values)
        payment.action_post()

    def _compute_paid_state(self):
        self.is_paid = False
        if self.payment_id:
            self.is_paid = True

    is_paid = fields.Boolean('Paid Payment ', states={'draft': [('readonly', False)]}, compute="_compute_paid_state")
    currency_id = fields.Many2one('res.currency', string='Currency', required=True,
                                  default=lambda self: self.env.user.company_id.currency_id)
    pay_amount = fields.Float('Payed amount', compute='_compute_pay_amount', currency_field='currency_id')
    payment_id = fields.Many2one('account.payment', 'Payment', compute="_compute_payment")


class RegisterPaymentBatch(models.Model):
    _inherit = 'hr.payslip.run'

    batch_payment_id = fields.Many2one('account.batch.payment', string='Batch Payment')
    is_batch_paid = fields.Boolean(string='Paid Payslips')

    def batch_register_payment(self):
        _logger.info(f'\n\n\n  START \n\n\n.')
        for batch_id in self:
            for payslip in batch_id.slip_ids:
                payment_payslip = payslip.register_payment()
            batch_id.is_batch_paid = True


class HrContract(models.Model):
    _inherit = 'hr.contract'

    mobile = fields.Char(string='Mobile')


class HrEmployee(models.Model):
    _inherit = 'hr.employee'
    subjected_to_mof = fields.Boolean(string='Subjected to MOF')
