from odoo import fields, models, api
import logging
import warnings

_logger = logging.getLogger(__name__)


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    payroll_slip_id = fields.Many2one('hr.payslip', string='Payslip Payment')


class AccountBatchPayment(models.Model):
    _inherit = 'account.batch.payment'

    payroll_batch_id = fields.Many2one('hr.payslip.run', string='Batch Payment')


class RegisterPaymentPayslips(models.Model):
    _inherit = 'hr.payslip'

    def _compute_payment(self):
        payment_obj = self.env['account.payment']
        self.payment_id = payment_obj.search([('payroll_slip_id', '=', self.id)])

    #     def _compute_pay_amount(self):
    #         for rec in self:
    #             for line in rec.line_ids:
    #                 payoff = line.search([('code', 'in', ('NET', 'LIQ')), ('slip_id', '=', self.id)], limit=1)
    #             rec.pay_amount = payoff.amount

    @api.depends('line_ids')
    @api.onchange('line_ids')
    def _compute_pay_amount(self):
        for slip in self:
            pay_amount_new = 0.0
            for line in slip.line_ids:
                if line.code == 'NET':
                    pay_amount_new += line.total
            slip.pay_amount = pay_amount_new

    def register_payment(self):
        value_amount = self.pay_amount
        if self.state == 'done' and value_amount != 0.00:
            payment_values = {
                'partner_type': 'supplier',
                'payment_type': 'outbound',
                'partner_id': self.employee_id.address_home_id.id,
                #                 'journal_id': self.journal_id.id,
                #                 'payment_method_id': self.payment_method_id.id,
                #                 'company_id': self.company_id.id,
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
    pay_amount = fields.Float('Payed amount', compute='_compute_pay_amount', currency_field='currency_id',
                              readonly=False)
    payment_id = fields.Many2one('account.payment', 'Payment', compute="_compute_payment")


class RegisterPaymentBatch(models.Model):
    _inherit = 'hr.payslip.run'

    def _compute_batch_payment(self):
        payment_batch_obj = self.env['account.batch.payment']
        self.batch_payment_id = payment_batch_obj.search([('payroll_batch_id', '=', self.id)])

    batch_payment_id = fields.Many2one('account.batch.payment', string='Batch Payment',
                                       compute="_compute_batch_payment")
    is_batch_paid = fields.Boolean(string='Paid Payslips')

    #     def batch_payslip_register_payment(self):
    #         _logger.info(f'\n\n\n  START \n\n\n.')
    #         for batch_id in self:
    #             for payslip in batch_id.slip_ids:
    #                 payslip.register_payment()
    #             batch_id.is_batch_paid = True

    def batch_register_payment(self):
        _logger.info(f'\n\n\n  START \n\n\n.')
        for batch_id in self:
            payments = []
            for payslip in batch_id.slip_ids:
                payment_payslip = payslip.register_payment()
                _logger.info(f'\n\n\n  Payment Payslip {payment_payslip} \n\n\n.')
                payment = batch_id.env['account.payment'].search([('payroll_slip_id', '=', payslip.id)], limit=1)
                _logger.info(f'\n\n\n  Payment  {payment} \n\n\n.')
                payments.append(payment)
            _logger.info(f'\n\n\n  Paymentssssssssssss {payments} \n\n\n.')
            batch_payment = batch_id.env['account.batch.payment'].create({
                        'journal_id': payment[0].journal_id.id,
                        'payment_method_id': payment[0].payment_method_id.id,
                        'date': batch_id.date_end,
                        'batch_type': 'outbound',
                        'payroll_batch_id': batch_id.id,
                    })
            _logger.info(f'\n\n\n  Batch Payment************ {batch_payment.id} \n\n\n.')
            for payment in payments:
                _logger.info(f'\n\n\n  Batch Payment************ {payment.id, payment.name, payment.ref, payment.partner_id.id, payment.date, payment. amount} \n\n\n.')
                batch_payment.payment_ids.create({
                    'name': payment.name,
                    'ref': payment.ref,
                    'partner_id': payment.partner_id.id,
                    'date': payment.date,
                    'amount_signed': - payment.amount,
                    'batch_payment_id': batch_payment.id
                 })
            batch_id.is_batch_paid = True


#                 batch_payment.validate_batch_button()


class HrContract(models.Model):
    _inherit = 'hr.contract'

    mobile = fields.Char(string='Mobile')


class HrEmployee(models.Model):
    _inherit = 'hr.employee'
    subjected_to_mof = fields.Boolean(string='Subjected to MOF')
