from odoo import fields, models, api


#     add second and third amount in hr expense sheet
class AccountMove(models.Model):
    _inherit = 'hr.expense.sheet'

    second_amount = fields.Monetary(string='Second Amount', default=0.0, readonly=False, store=True,
                                    compute="exchange_second_amount")
    third_amount = fields.Monetary(string='Third Amount', default=0.0, readonly=False, store=True,
                                   compute="exchange_third_amount")
    second_currency = fields.Many2one('res.currency', related="company_id.second_currency")
    third_currency = fields.Many2one('res.currency', related="company_id.third_currency")

    @api.depends('total_amount', 'amount_residual')
    def exchange_second_amount(self):
        for rec in self:
            second = rec.env['res.currency'].search([('id', '=', rec.company_id.second_currency.id)])
            if rec.amount_residual:
                rec.second_amount = rec.currency_id.compute(rec.amount_residual, second)
            else:
                rec.second_amount = rec.currency_id.compute(rec.total_amount, second)

    @api.depends('total_amount', 'amount_residual')
    def exchange_third_amount(self):
        for rec in self:
            third = rec.env['res.currency'].search([('id', '=', rec.company_id.third_currency.id)])
            if rec.amount_residual:
                rec.third_amount = rec.currency_id.compute(rec.amount_residual, third)
            else:
                rec.third_amount = rec.currency_id.compute(rec.total_amount, third)
