# -*- coding: utf-8 -*-

from odoo import tools
from odoo import models, fields, api


class AccountInvoiceReport(models.Model):
    _inherit = "account.invoice.report"

    partner_official_name = fields.Char(string='Partner Official Name', readonly=True)
    
    @api.model
    def _select(self):
        return '''
            SELECT
                line.id,
                line.move_id,
                line.product_id,
                line.account_id,
                line.analytic_account_id,
                line.journal_id,
                line.company_id,
                line.company_currency_id                                    AS currency_id,
                line.partner_id AS commercial_partner_id,
                move.name,
                move.state,
                move.type,
                move.partner_id,
                move.invoice_user_id,
                move.fiscal_position_id,
                move.invoice_payment_state,
                move.invoice_date,
                move.invoice_date_due,
                move.invoice_payment_term_id,
                move.invoice_partner_bank_id,
                -line.balance * (move.amount_residual_signed / NULLIF(move.amount_total_signed, 0.0)) * (line.price_total / NULLIF(line.price_subtotal, 0.0))
                                                                            AS residual,
                -line.balance * (line.price_total / NULLIF(line.price_subtotal, 0.0))    AS amount_total,
                uom_template.id                                             AS product_uom_id,
                template.categ_id                                           AS product_categ_id,
                line.quantity / NULLIF(COALESCE(uom_line.factor, 1) / COALESCE(uom_template.factor, 1), 0.0) * (CASE WHEN move.type IN ('in_invoice','out_refund','in_receipt') THEN -1 ELSE 1 END)
                                                                            AS quantity,
                -line.balance                                               AS price_subtotal,
                -COALESCE(line.balance
                   / NULLIF(line.quantity, 0.0)
                   / NULLIF(COALESCE(uom_line.factor, 1), 0.0)
                   / NULLIF(COALESCE(uom_template.factor, 1), 0.0),
                   0.0)
                                                                            AS price_average,
                COALESCE(partner.official_name, partner.display_name)       AS partner_official_name,
                COALESCE(partner.country_id, commercial_partner.country_id) AS country_id,
                1                                                           AS nbr_lines
        '''
    
    @api.model
    def _group_by(self):
        return '''
            GROUP BY
                line.id,
                line.move_id,
                line.product_id,
                line.account_id,
                line.analytic_account_id,
                line.journal_id,
                line.company_id,
                line.currency_id,
                line.partner_id,
                move.name,
                move.state,
                move.type,
                move.amount_residual_signed,
                move.amount_total_signed,
                move.partner_id,
                move.invoice_user_id,
                move.fiscal_position_id,
                move.invoice_payment_state,
                move.invoice_date,
                move.invoice_date_due,
                move.invoice_payment_term_id,
                move.invoice_partner_bank_id,
                uom_template.id,
                uom_line.factor,
                template.categ_id,
                COALESCE(partner.country_id, commercial_partner.country_id),
                COALESCE(partner.official_name, partner.display_name)
        '''
         
    def init(self):
        return super(AccountInvoiceReport, self).init()