from odoo import models, fields, api
from odoo.tools.misc import format_date
import logging

log = logging.getLogger(__name__)


class ReportPartnerLedgerInherited(models.AbstractModel):
    _inherit = "account.partner.ledger"
    
    @api.model
    def _get_report_line_move_line(self, options, partner, aml, cumulated_init_balance, cumulated_balance):
        
        if aml.get('account_id'):
            non_auth = self.env['account.nonauthorized.user'].search([('account_id', '=', aml.get('account_id')), ('user_id', '=', self.env.user.id)])
            if non_auth:
                aml['account_code'] = "*****"
                aml['account_name'] = "*****"
                
        if aml['payment_id']:
            caret_type = 'account.payment'
        elif aml['move_type'] in ('in_refund', 'in_invoice', 'in_receipt'):
            caret_type = 'account.invoice.in'
        elif aml['move_type'] in ('out_refund', 'out_invoice', 'out_receipt'):
            caret_type = 'account.invoice.out'
        else:
            caret_type = 'account.move'

        date_maturity = aml['date_maturity'] and format_date(self.env, fields.Date.from_string(aml['date_maturity']))
        
        columns = [
            {'name': aml['journal_code']},
            {'name': aml['account_code']},
            {'name': self._format_aml_name(aml['name'], aml['ref'], aml['move_name'])},
            {'name': date_maturity or '', 'class': 'date'},
            {'name': aml['full_rec_name'] or ''},
            {'name': self.format_value(cumulated_init_balance), 'class': 'number'},
            {'name': self.format_value(aml['debit'], blank_if_zero=True), 'class': 'number'},
            {'name': self.format_value(aml['credit'], blank_if_zero=True), 'class': 'number'},
        ]
        
        if self.user_has_groups('base.group_multi_currency'):
            if aml['currency_id']:
                currency = self.env['res.currency'].browse(aml['currency_id'])
                formatted_amount = self.format_value(aml['amount_currency'], currency=currency, blank_if_zero=True)
                columns.append({'name': formatted_amount, 'class': 'number'})
            else:
                columns.append({'name': ''})
        
        columns.append({'name': self.format_value(cumulated_balance), 'class': 'number'})
        
        res =  {
            "id": aml["id"],
            "name": format_date(self.env, aml["date"]),
            "class": "date",
            "columns": columns,
            "caret_options": caret_type,
            "level": 4,
        }
        if partner:
            res["parent_id"] =  "partner_%s" % partner.id
        return res
