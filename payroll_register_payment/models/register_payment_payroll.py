from odoo import fields, models, api


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    payroll_slip_id = fields.Many2one('hr.payslip')


class RegisterPaymentPayslips(models.Model):
    _inherit = 'hr.payslip'

    payment_method_id = fields.Many2one('account.payment.method', string='Payment Type', required=True)

    def _compute_payment(self):
        payment_obj = self.env['account.payment']
        self.payment_id = payment_obj.search([('payroll_slip_id', '=', self.id)])

    def _compute_pay_amount(self):
        line_obj = self.env['hr.payslip.line']
        payoff = line_obj.search([('code', 'in', ('NET', 'LIQ')), ('slip_id', '=', self.id)])
        self.pay_amount = payoff.amount

    def register_payment(self):
        value_amount = self.pay_amount
        if self.state == 'done':
            payment_values = {
                'partner_type': 'supplier',
                'payment_type': 'outbound',
                'partner_id': self.employee_id.address_home_id.id,
                'journal_id': self.journal_id.id,
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
    pay_amount = fields.Float('Payed amount', compute='_compute_pay_amount')
    payment_id = fields.Many2one('account.payment', 'Payment', compute="_compute_payment")
