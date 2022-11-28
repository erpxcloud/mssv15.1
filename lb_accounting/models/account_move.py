# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp

import logging
from odoo.exceptions import ValidationError, UserError

from datetime import date
from odoo.tools import float_is_zero, float_compare

log = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = "account.move"
 
    _order = 'name desc'
    
    def _post_validate_for_small_values(self):
        """
        Check if second/third debit/credit total is not equal then get max debit, max credit
        and update one random line second/third debit or credit based on the second/third currency balance
        """
        delta = 0.1
        for move in self:
            
            if move.line_ids and self.user_has_groups('base.group_multi_currency') and any([not line.manual_entry_computation for line in move.line_ids]):
                second_currency_balance = sum(line['second_debit'] - line['second_credit'] for line in move.line_ids)
                max_credit = max(move.line_ids.mapped('second_credit'), key=lambda x:float(x))
                max_debit = max(move.line_ids.mapped('second_debit'), key=lambda x:float(x))
                delta = (0.001*abs(max_debit))
                if (0.001*abs(max_credit))>delta:
                    delta = (0.001*abs(max_credit))
                        
                log.info("Total second currency balance: %s for move: %s", second_currency_balance, move.id)
    
                if ((not delta or abs(second_currency_balance) <= delta) and second_currency_balance != 0) or abs(second_currency_balance) < 0.1:
                    
                    if second_currency_balance > 0:
                        max_credit = max(move.line_ids.mapped('second_credit'), key=lambda x:float(x))
                        for det_line in move.line_ids:
                            if round(det_line.second_credit, det_line.move_id.company_id.second_currency_id.decimal_places) == round(max_credit, det_line.move_id.company_id.second_currency_id.decimal_places):
                                det_line.with_context(check_move_validity=False).write({'second_credit': max_credit + abs(second_currency_balance)})
                                break
                    else:
                        max_debit = max(move.line_ids.mapped('second_debit'), key=lambda x:float(x))
                        for det_line in move.line_ids:
                            if round(det_line.second_debit, det_line.move_id.company_id.second_currency_id.decimal_places) == round(max_debit, det_line.move_id.company_id.second_currency_id.decimal_places):
                                det_line.with_context(check_move_validity=False).write({'second_debit': max_debit + abs(second_currency_balance)})
                                break

    
                third_currency_balance = sum(line['third_debit'] - line['third_credit'] for line in move.line_ids)
                log.info("Total third currency balance: %s for move: %s", third_currency_balance, move.id)
                max_credit = max(move.line_ids.mapped('third_credit'), key=lambda x:float(x))
                max_debit = max(move.line_ids.mapped('third_debit'), key=lambda x:float(x))
                delta = (0.001*abs(max_debit))
                if (0.001*abs(max_credit))>delta:
                    delta = (0.001*abs(max_credit))
                    
                if ((not delta or abs(third_currency_balance) <= delta) and third_currency_balance != 0)  or abs(third_currency_balance) < 0.1:
                    if third_currency_balance > 0:
                        max_credit = max(move.line_ids.mapped('third_credit'), key=lambda x:float(x))
                        for det_line in move.line_ids:
                            if round(det_line.third_credit, det_line.move_id.company_id.third_currency_id.decimal_places) == round(max_credit, det_line.move_id.company_id.third_currency_id.decimal_places):
                                det_line.with_context(check_move_validity=False).write({'third_credit': max_credit + abs(third_currency_balance)})
                                break

                    else:
                        max_debit = max(move.line_ids.mapped('third_debit'), key=lambda x:float(x))
                        for det_line in move.line_ids:
                            if round(det_line.third_debit, det_line.move_id.company_id.third_currency_id.decimal_places) == round(max_debit, det_line.move_id.company_id.third_currency_id.decimal_places):
                                det_line.with_context(check_move_validity=False).write({'third_debit': max_debit + abs(third_currency_balance)})
                                break
                    
    
    def _post_validate(self):
        """
        Check if second/third debit/credit total is not equal then get max debit, max credit 
        and update one random line second/third debit or credit based on the second/third currency balance
        """
        for move in self:
            if move.line_ids and self.user_has_groups('base.group_multi_currency') and any([not line.manual_entry_computation for line in move.line_ids]):
                second_currency_balance = sum(line['second_debit'] - line['second_credit'] for line in move.line_ids)
                
                log.info("Total second currency balance: %s for move: %s", second_currency_balance, move.id)
                
                if second_currency_balance != 0:
                    
                    if second_currency_balance > 0:
                        max_credit = max(move.line_ids.mapped('second_credit'), key=lambda x:float(x))
                        move.line_ids.search([('move_id','=',move.id), ('second_credit','=',max_credit)], limit=1).with_context(check_move_validity=False).write({'second_credit': max_credit + second_currency_balance})
                    else:
                        max_debit = max(move.line_ids.mapped('second_debit'), key=lambda x:float(x))
                        move.line_ids.search([('move_id','=',move.id), ('second_debit','=',max_debit)], limit=1).with_context(check_move_validity=False).write({'second_debit': max_debit + abs(second_currency_balance)})
                        
                third_currency_balance = sum(line['third_debit'] - line['third_credit'] for line in move.line_ids)
                log.info("Total third currency balance: %s for move: %s", third_currency_balance, move.id)
                
                if third_currency_balance != 0:
                    
                    if third_currency_balance > 0:
                        max_credit = max(move.line_ids.mapped('third_credit'), key=lambda x:float(x))
                        move.line_ids.search([('move_id','=',move.id), ('third_credit','=',max_credit)], limit=1).with_context(check_move_validity=False).write({'third_credit': max_credit + third_currency_balance})
                    else:
                        max_debit = max(move.line_ids.mapped('third_debit'), key=lambda x:float(x))
                        move.line_ids.search([('move_id','=',move.id), ('third_debit','=',max_debit)], limit=1).with_context(check_move_validity=False).write({'third_debit': max_debit + abs(third_currency_balance)})
                                
    def _check_balanced(self):
        ''' Assert the move is fully balanced debit = credit.
        An error is raised if it's not the case.
        '''
        for inv in self:
            if self.user_has_groups('base.group_multi_currency'):
                inv._post_validate_for_small_values()
                inv._check_second_balanced()
                inv._check_third_balanced()
           
        super(AccountMove, self)._check_balanced()
    
    def _check_second_balanced(self):
        moves = self.filtered(lambda move: move.line_ids)
        if not moves:
            return
        
        # /!\ As this method is called in create / write, we can't make the assumption the computed stored fields
        # are already done. Then, this query MUST NOT depend of computed stored fields (e.g. balance).
        # It happens as the ORM makes the create with the 'no_recompute' statement.
        self.env['account.move.line'].flush(['second_debit', 'second_credit', 'move_id'])
        self.env['account.move'].flush(['journal_id'])
        self._cr.execute('''
            SELECT line.move_id, ROUND(SUM(second_debit - second_credit), currency.decimal_places)
            FROM account_move_line line
            JOIN account_move move ON move.id = line.move_id
            JOIN account_journal journal ON journal.id = move.journal_id
            JOIN res_company company ON company.id = journal.company_id
            JOIN res_currency currency ON currency.id = company.second_currency_id
            WHERE line.move_id IN %s
            GROUP BY line.move_id, currency.decimal_places
            HAVING ROUND(SUM(second_debit - second_credit), currency.decimal_places) != 0.0;
        ''', [tuple(self.ids)])
        
        query_res = self._cr.fetchall()
        if query_res:
            ids = [res[0] for res in query_res]
            sums = [res[1] for res in query_res]
            raise UserError(_("Cannot create unbalanced journal entry. Ids: %s\nDifferences second debit - credit: %s") % (ids, sums))
     
    def _check_third_balanced(self):
        moves = self.filtered(lambda move: move.line_ids)
        if not moves:
            return

        # /!\ As this method is called in create / write, we can't make the assumption the computed stored fields
        # are already done. Then, this query MUST NOT depend of computed stored fields (e.g. balance).
        # It happens as the ORM makes the create with the 'no_recompute' statement.
        self.env['account.move.line'].flush(['third_debit', 'third_credit', 'move_id'])
        self.env['account.move'].flush(['journal_id'])
        self._cr.execute('''
            SELECT line.move_id, ROUND(SUM(third_debit - third_credit), currency.decimal_places)
            FROM account_move_line line
            JOIN account_move move ON move.id = line.move_id
            JOIN account_journal journal ON journal.id = move.journal_id
            JOIN res_company company ON company.id = journal.company_id
            JOIN res_currency currency ON currency.id = company.third_currency_id
            WHERE line.move_id IN %s
            GROUP BY line.move_id, currency.decimal_places
            HAVING ROUND(SUM(third_debit - third_credit), currency.decimal_places) != 0.0;
        ''', [tuple(self.ids)])
        
        query_res = self._cr.fetchall()
        
        if query_res:
            ids = [res[0] for res in query_res]
            sums = [res[1] for res in query_res]
            raise UserError(_("Cannot create unbalanced journal entry. Ids: %s\nDifferences third debit - credit: %s") % (ids, sums))
       
    def button_cancel(self):
        if not self.user_has_groups('account.group_account_manager'):
            raise UserError(_('You are not allowed to cancel a posted entry of this journal.'))
         
        return super(AccountMove, self).button_cancel()

    def post(self):
        #Added In order to make sure that no reconciled found before posting
        #self.mapped('line_ids').remove_move_reconcile()
        
        super(AccountMove, self).post()
        
        for move in self:
            for move_line in move.line_ids:
                if self.user_has_groups('base.group_multi_currency'):
                    if move_line.manual_entry_computation or self._context.get('manual_entry_computation'):
                        log.info("Manual move line entry computation")
                    else:
                        log.info("Auto move line entry computation")
                        move_line.calculate_second_third_debit_credit()
            
            move._post_validate()
            move._check_balanced()
            
    @api.onchange('line_ids','invoice_line_ids','date')
    def on_change_line_ids(self):
        for move in self:
            for move_line in move.line_ids:
                if self.user_has_groups('base.group_multi_currency'):
                    if move_line.manual_entry_computation or self._context.get('manual_entry_computation'):
                        log.info("Manual move line entry computation")
                    else:
                        log.info("Auto move line entry computation")
                        move_line.with_context(calculate_second_third_amount = True).calculate_second_third_debit_credit() 
            move._post_validate_for_small_values()
        
    def button_draft(self):
        """
        In invoicing:
        * Reset values second debit/credit, third debit/credit on change of debit and credit amount
        """
        self._post_validate()
        
        res = super(AccountMove, self).button_draft()

        for line in self:
            if line.is_invoice(include_receipts=True):
                log.info("Journal is reset to draft, resetting second/third currency for invoice: %s", line)
                
                for l in line.mapped('line_ids'):
                    values = {
                        'second_credit': 0.0,
                        'second_debit': 0.0,
                        'third_credit': 0.0,
                        'third_debit': 0.0,
                    }
                    l.with_context(check_move_validity=False).write(values)
            
        return res
    
    @api.onchange('partner_id')
    def _onchange_partner_id_tax_line(self):
        for move in self:
            for line in move.line_ids:
                if line.tax_group_id and move.state != "posted" and line.tax_line_id.vat_tax:
                    if move.journal_id.type=='sale':
                        line.account_id= line.move_id.partner_id.with_context(force_company=line.move_id.company_id.id).vat_receivable.id
                    else:
                        line.account_id= line.move_id.partner_id.with_context(force_company=line.move_id.company_id.id).vat_payable.id
                        
    @api.model
    def _get_tax_grouping_key_from_tax_line(self, tax_line):
        ''' Create the dictionary based on a tax line that will be used as key to group taxes together.
        /!\ Must be consistent with '_get_tax_grouping_key_from_base_line'.
        :param tax_line:    An account.move.line being a tax line (with 'tax_repartition_line_id' set then).
        :return:            A dictionary containing all fields on which the tax will be grouped.
        '''
        base_line_dict = super(AccountMove, self)._get_tax_grouping_key_from_tax_line(tax_line)
        tax_line = self.env['account.tax.repartition.line'].browse(base_line_dict['tax_repartition_line_id'])
        is_tax_vat = self.env['account.tax'].search([('id','=',tax_line.tax_id.id)]).vat_tax
        if is_tax_vat:
            if self.type in ('in_invoice', 'in_refund'): 
                if self.partner_id.vat_payable:
                    account_id = self.partner_id.vat_payable.id
                    base_line_dict['account_id'] = account_id
                    log.info("Updating base line account to partner vat payable account: %s", account_id)

            # Customer Invoice or Customer Credit Note
            if self.type in ('out_invoice', 'out_refund'): 
                if self.partner_id.vat_receivable:
                    account_id = self.partner_id.vat_receivable.id
                    base_line_dict['account_id'] = account_id
                    log.info("Updating base line account to partner vat receivable account: %s", account_id)

        return base_line_dict
    
    @api.model
    def _get_tax_grouping_key_from_base_line(self, base_line, tax_vals):
        ''' Create the dictionary based on a base line that will be used as key to group taxes together.
        /!\ Must be consistent with '_get_tax_grouping_key_from_tax_line'.
        
        Check if the tax is vat then update the tax default account by the customer vat payable or receivable account
        
        :param base_line:   An account.move.line being a base line (that could contains something in 'tax_ids').
        :param tax_vals:    An element of compute_all(...)['taxes'].
        :return:            A dictionary containing all fields on which the tax will be grouped.
        '''
        base_line_dict = super(AccountMove, self)._get_tax_grouping_key_from_base_line(base_line, tax_vals)
        
        is_tax_vat = self.env['account.tax'].search([('id','=',tax_vals['id'])]).vat_tax
        
        if is_tax_vat:
            if self.type in ('in_invoice', 'in_refund'): 
                if self.partner_id.vat_payable:
                    account_id = self.partner_id.vat_payable.id
                    base_line_dict['account_id'] = account_id
                    log.info("Updating base line account to partner vat payable account: %s", account_id)
                     
            # Customer Invoice or Customer Credit Note
            if self.type in ('out_invoice', 'out_refund'): 
                if self.partner_id.vat_receivable:
                    account_id = self.partner_id.vat_receivable.id
                    base_line_dict['account_id'] = account_id
                    log.info("Updating base line account to partner vat receivable account: %s", account_id)
        
        return base_line_dict
     
    def _reverse_move_vals(self, default_values, cancel=True):
        ''' Reverse values passed as parameter being the copied values of the original journal entry.
        For example, debit / credit must be switched. The tax lines must be edited in case of refunds.

        :param default_values:  A copy_date of the original journal entry.
        :param cancel:          A flag indicating the reverse is made to cancel the original journal entry.
        :return:                The updated default_values.
        '''
        self.ensure_one()

        def compute_tax_repartition_lines_mapping(move_vals):
            ''' Computes and returns a mapping between the current repartition lines to the new expected one.
            :param move_vals:   The newly created invoice as a python dictionary to be passed to the 'create' method.
            :return:            A map invoice_repartition_line => refund_repartition_line.
            '''
            # invoice_repartition_line => refund_repartition_line
            mapping = {}

            # Do nothing if the move is not a credit note.
            if move_vals['type'] not in ('out_refund', 'in_refund'):
                return mapping

            for line_command in move_vals.get('line_ids', []):
                line_vals = line_command[2]  # (0, 0, {...})

                if line_vals.get('tax_ids') and line_vals['tax_ids'][0][2]:
                    # Base line.
                    tax_ids = line_vals['tax_ids'][0][2]
                elif line_vals.get('tax_line_id'):
                    # Tax line.
                    tax_ids = [line_vals['tax_line_id']]
                else:
                    continue

                for tax in self.env['account.tax'].browse(tax_ids).flatten_taxes_hierarchy():
                    for inv_rep_line, ref_rep_line in zip(tax.invoice_repartition_line_ids, tax.refund_repartition_line_ids):
                        mapping[inv_rep_line] = ref_rep_line
            return mapping

        move_vals = self.with_context(include_business_fields=True).copy_data(default=default_values)[0]

        tax_repartition_lines_mapping = compute_tax_repartition_lines_mapping(move_vals)

        for line_command in move_vals.get('line_ids', []):
            line_vals = line_command[2]  # (0, 0, {...})

            # ==== Inverse debit / credit / amount_currency ====
            amount_currency = -line_vals.get('amount_currency', 0.0)
            balance = line_vals['credit'] - line_vals['debit']
            second_balance = line_vals['second_credit'] - line_vals['second_debit']
            third_balance = line_vals['third_credit'] - line_vals['third_debit']

            line_vals.update({
                'amount_currency': amount_currency,
                'debit': balance > 0.0 and balance or 0.0,
                'credit': balance < 0.0 and -balance or 0.0,
                'second_debit': second_balance > 0.0 and second_balance or 0.0,
                'second_credit': second_balance < 0.0 and -second_balance or 0.0,
                'third_debit': third_balance > 0.0 and third_balance or 0.0,
                'third_credit': third_balance < 0.0 and -third_balance or 0.0,
            })

            if move_vals['type'] not in ('out_refund', 'in_refund'):
                continue

            # ==== Map tax repartition lines ====
            if line_vals.get('tax_ids') and line_vals['tax_ids'][0][2]:
                # Base line.
                taxes = self.env['account.tax'].browse(line_vals['tax_ids'][0][2]).flatten_taxes_hierarchy()
                invoice_repartition_lines = taxes\
                    .mapped('invoice_repartition_line_ids')\
                    .filtered(lambda line: line.repartition_type == 'base')
                refund_repartition_lines = invoice_repartition_lines\
                    .mapped(lambda line: tax_repartition_lines_mapping[line])

                line_vals['tag_ids'] = [(6, 0, refund_repartition_lines.mapped('tag_ids').ids)]
            elif line_vals.get('tax_repartition_line_id'):
                # Tax line.
                invoice_repartition_line = self.env['account.tax.repartition.line'].browse(line_vals['tax_repartition_line_id'])
                refund_repartition_line = tax_repartition_lines_mapping[invoice_repartition_line]

                # Find the right account.
                account_id = self.env['account.move.line']._get_default_tax_account(refund_repartition_line).id
                if not account_id:
                    if not invoice_repartition_line.account_id:
                        # Keep the current account as the current one comes from the base line.
                        account_id = line_vals['account_id']
                    else:
                        tax = invoice_repartition_line.invoice_tax_id
                        base_line = self.line_ids.filtered(lambda line: tax in line.tax_ids)[0]
                        account_id = base_line.account_id.id

                line_vals.update({
                    'tax_repartition_line_id': refund_repartition_line.id,
                    'account_id': account_id,
                    'tag_ids': [(6, 0, refund_repartition_line.tag_ids.ids)],
                })
        return move_vals
           
class AccountMoveLine(models.Model):
    _inherit = "account.move.line"
    
    @api.model
    def _auto_init(self):
        self._cr.execute("""
        ALTER TABLE account_move_line
        ADD COLUMN IF NOT EXISTS second_balance NUMERIC DEFAULT 0
        """)
        self._cr.execute("""
        ALTER TABLE account_move_line
        ADD COLUMN IF NOT EXISTS second_amount_residual NUMERIC DEFAULT 0
        """)
        self._cr.execute("""
        ALTER TABLE account_move_line
        ADD COLUMN IF NOT EXISTS second_amount_residual_currency NUMERIC DEFAULT 0
        """)
        self._cr.execute("""
        ALTER TABLE account_move_line
        ADD COLUMN IF NOT EXISTS company_second_currency_id INTEGER
        """)
        self._cr.execute("""
        ALTER TABLE account_move_line
        ADD COLUMN IF NOT EXISTS third_balance NUMERIC DEFAULT 0
        """)
        self._cr.execute("""
        ALTER TABLE account_move_line
        ADD COLUMN IF NOT EXISTS third_amount_residual NUMERIC DEFAULT 0
        """)
        self._cr.execute("""
        ALTER TABLE account_move_line
        ADD COLUMN IF NOT EXISTS third_amount_residual_currency NUMERIC DEFAULT 0
        """)
        self._cr.execute("""
        ALTER TABLE account_move_line
        ADD COLUMN IF NOT EXISTS company_third_currency_id INTEGER
        """)
        
        return super(AccountMoveLine, self)._auto_init()

    @api.model
    def default_get(self, default_fields):
        # OVERRIDE
        values = super(AccountMoveLine, self).default_get(default_fields)

        if 'account_id' in default_fields \
            and (self._context.get('journal_id') or self._context.get('default_journal_id')) \
            and not values.get('account_id') \
            and self._context.get('default_type') in self.move_id.get_inbound_types():
            # Fill missing 'account_id'.
            journal = self.env['account.journal'].browse(self._context.get('default_journal_id') or self._context['journal_id'])
            values['account_id'] = journal.default_credit_account_id.id
        elif 'account_id' in default_fields \
            and (self._context.get('journal_id') or self._context.get('default_journal_id')) \
            and not values.get('account_id') \
            and self._context.get('default_type') in self.move_id.get_outbound_types():
            # Fill missing 'account_id'.
            journal = self.env['account.journal'].browse(self._context.get('default_journal_id') or self._context['journal_id'])
            values['account_id'] = journal.default_debit_account_id.id
        elif self._context.get('line_ids') and any(field_name in default_fields for field_name in ('debit', 'credit', 'second_debit', 'second_credit', 
                                                                                                   'third_debit', 'third_credit', 'account_id', 'partner_id')):
            move = self.env['account.move'].new({'line_ids': self._context['line_ids']})

            # Suggest default value for debit / credit to balance the journal entry.
            balance = sum(line['debit'] - line['credit'] for line in move.line_ids)
            # if we are here, line_ids is in context, so journal_id should also be.
            journal = self.env['account.journal'].browse(self._context.get('default_journal_id') or self._context['journal_id'])
            currency = journal.exists() and journal.company_id.currency_id
            if currency:
                balance = currency.round(balance)
            if balance < 0.0:
                values.update({'debit': -balance})
            if balance > 0.0:
                values.update({'credit': balance})
            
            # Suggest default value for second debit / second credit to balance the journal entry.
            second_balance = sum(line['second_debit'] - line['second_credit'] for line in move.line_ids)
            if second_balance < 0.0:
                values.update({'second_debit': -second_balance})
            if second_balance > 0.0:
                values.update({'second_credit': second_balance})
                
            # Suggest default value for third debit / third credit to balance the journal entry.
            third_balance = sum(line['third_debit'] - line['third_credit'] for line in move.line_ids)
            if third_balance < 0.0:
                values.update({'third_debit': -third_balance})
            if third_balance > 0.0:
                values.update({'third_credit': third_balance})
                
            # Suggest default value for 'partner_id'.
            if 'partner_id' in default_fields and not values.get('partner_id'):
                partners = move.line_ids[-2:].mapped('partner_id')
                if len(partners) == 1:
                    values['partner_id'] = partners.id

            # Suggest default value for 'account_id'.
            if 'account_id' in default_fields and not values.get('account_id'):
                accounts = move.line_ids[-2:].mapped('account_id')
                if len(accounts) == 1:
                    values['account_id'] = accounts.id
            
        if values.get('display_type'):
           values.pop('account_id', None)
        
        return values
    
    _sql_constraints = [
        (
            'check_credit_debit',
            'CHECK(credit + debit>=0 AND credit * debit=0)',
            'Wrong credit or debit value in accounting entry !'
        ),
        (
            'check_second_credit_debit',
            'CHECK(second_credit + second_debit>=0 AND second_credit * second_debit=0)',
            'Wrong second credit or second debit value in accounting entry !'
        ),
        (
            'check_third_credit_debit',
            'CHECK(third_credit + third_debit>=0 AND third_credit * third_debit=0)',
            'Wrong third credit or debit value in accounting entry !'
        ),
        (
            'check_accountable_required_fields',
             "CHECK(COALESCE(display_type IN ('line_section', 'line_note'), 'f') OR account_id IS NOT NULL)",
             "Missing required account on accountable invoice line."
        ),
        (
            'check_non_accountable_fields_null',
             "CHECK(display_type NOT IN ('line_section', 'line_note') OR (amount_currency = 0 AND debit = 0 AND credit = 0 AND account_id IS NULL))",
             "Forbidden unit price, account and quantity on non-accountable invoice line"
        ),
    ]
    
    name = fields.Text(string="Label")
    company_second_currency_id = fields.Many2one('res.currency', related='company_id.second_currency_id', string="Second Company Currency", readonly=True,
        help='Utility field to express amount currency', store=True)
    
    company_third_currency_id = fields.Many2one('res.currency', related='company_id.third_currency_id', string="Third Company Currency", readonly=True,
        help='Utility field to express amount currency', store=True)
    
    second_debit = fields.Monetary(default=0.0, currency_field='company_second_currency_id', copy=True)
    second_credit = fields.Monetary(default=0.0, currency_field='company_second_currency_id', copy=True)
    third_debit = fields.Monetary(default=0.0, currency_field='company_third_currency_id', copy=True)
    third_credit = fields.Monetary(default=0.0, currency_field='company_third_currency_id', copy=True)
    
    second_balance = fields.Monetary(compute='_second_store_balance', store=True, currency_field='company_second_currency_id',
        help="Technical field holding the debit - credit in order to open meaningful graph views from reports")
    third_balance = fields.Monetary(compute='_third_store_balance', store=True, currency_field='company_third_currency_id',
        help="Technical field holding the debit - credit in order to open meaningful graph views from reports")
     
    second_amount_residual = fields.Monetary(compute='_second_amount_residual', string='Second Residual Amount', store=True, currency_field='company_second_currency_id',
        help="The residual amount on a journal item expressed in the company currency.")
    second_amount_residual_currency = fields.Monetary(compute='_second_amount_residual', string='Second Residual Amount in Currency', store=True,
        help="The residual amount on a journal item expressed in its currency (possibly not the company currency).")
     
    third_amount_residual = fields.Monetary(compute='_third_amount_residual', string='Third Residual Amount', store=True, currency_field='company_third_currency_id',
        help="The residual amount on a journal item expressed in the company currency.")
    third_amount_residual_currency = fields.Monetary(compute='_third_amount_residual', string='Third Residual Amount in Currency', store=True,
        help="The residual amount on a journal item expressed in its currency (possibly not the company currency).")
    
    #This field is added to differentiate between auto entry created or a manual one
    manual_entry_computation = fields.Boolean(default=False)
    
    @api.onchange('currency_id')
    def on_change_currency_id(self):
        if self.currency_id and self.currency_id == self.move_id.company_id.currency_id:
            raise UserError(_("Just Foreign Currencies are allowed"))
            
    @api.depends('second_debit', 'second_credit')
    def _second_store_balance(self):
        for line in self:
            line.second_balance = line.second_debit - line.second_credit
            
    @api.depends('third_debit', 'third_credit')
    def _third_store_balance(self):
        for line in self:
            line.third_balance = line.third_debit - line.third_credit
            
    @api.onchange('account_id')
    def _onchange_account_id(self):
        if self.user_has_groups('base.group_multi_currency'):
            self.manual_entry_computation = True
    
    @api.onchange('amount_currency', 'currency_id', 'account_id')
    def _onchange_amount_currency_value(self):
        '''Recompute the debit/credit based on amount_currency/currency_id and date.
        '''
        for line in self:
            if not line.move_id.is_invoice(include_receipts=True):
                company_currency_id = line.account_id.company_id.currency_id
                company_id = line.move_id.company_id
                amount = line.amount_currency
                if line.currency_id and company_currency_id and line.currency_id != company_currency_id:
                    amount = line.currency_id._convert(amount, company_currency_id, company_id, line.date or fields.Date.today())
                    line.debit = amount > 0 and amount or 0.0
                    line.credit = amount < 0 and -amount or 0.0
                elif line.currency_id and company_currency_id and line.currency_id == company_currency_id:
                    line.debit = amount > 0 and amount or 0.0
                    line.credit = amount < 0 and -amount or 0.0

    @api.onchange('amount_currency', 'currency_id', 'debit', 'credit')
    def _onchange_amount_currency_second_third(self):
        '''Recompute the debit/credit based on amount_currency/currency_id and date. for second and third currency
        '''
        for line in self:
            if not line.move_id.is_invoice(include_receipts=True):
                balance = sum(line1['debit'] - line1['credit'] for line1 in line.move_id.line_ids)
                second_balance = sum(line1['second_debit'] - line1['second_credit'] for line1 in line.move_id.line_ids)
                if balance or second_balance:
                    line.with_context(**{'calculate_second_third_amount': True, 'rate_date': line.move_id.date}).calculate_second_third_debit_credit()

                
    @api.depends('second_debit', 'second_credit', 'amount_currency', 'currency_id', 'matched_debit_ids', 'matched_credit_ids', 'matched_debit_ids.amount', 'matched_credit_ids.amount', 'move_id.state')
    def _second_amount_residual(self):
        """ Computes the residual amount of a move line from a reconcilable account in the company currency and the line's currency.
            This amount will be 0 for fully reconciled lines or lines from a non-reconcilable account, the original line amount
            for unreconciled lines, and something in-between for partially reconciled lines.
        """
        for line in self:
            
            if not line.company_id.second_currency_id.id:
                line.second_amount_residual = 0
                line.second_amount_residual_currency = 0
            else:
                if not line.account_id.reconcile and line.account_id.internal_type != 'liquidity':
                    line.second_amount_residual = 0
                    line.second_amount_residual_currency = 0
                    continue
                
                amount = abs(line.second_debit - line.second_credit)
                value = abs(line.amount_currency) or 0.0
                if line.currency_id:
                    amount_residual_currency = line.currency_id._convert(value, line.move_id.company_id.second_currency_id, line.move_id.company_id, line.move_id.date) 
                else:
                    amount_residual_currency = line.company_currency_id._convert(value, line.move_id.company_id.second_currency_id, line.move_id.company_id, line.move_id.date)
                sign = 1 if (line.second_debit - line.second_credit) > 0 else -1
                
                if not line.second_debit and not line.second_credit and line.amount_currency and line.currency_id:
                    sign = 1 if float_compare(line.amount_currency, 0, precision_rounding=line.currency_id.rounding) == 1 else -1
    
                for partial_line in (line.matched_debit_ids + line.matched_credit_ids):
                    sign_partial_line = sign if partial_line.credit_move_id == line else (-1 * sign)
                    date = partial_line.credit_move_id.date if partial_line.debit_move_id == line else partial_line.debit_move_id.date
                    rate = line.company_id.second_currency_id.with_context(date=date).rate
                    if line.currency_id and line.amount_currency:
                        if partial_line.currency_id and partial_line.currency_id == line.move_id.company_id.second_currency_id:
                            amount_residual_currency += sign_partial_line * partial_line.amount_currency
                            amount += sign_partial_line * partial_line.amount_currency
                        else:
                            amount_residual_currency += sign_partial_line * partial_line.amount * rate
                            amount += sign_partial_line * partial_line.amount * rate
    
                line.second_amount_residual = line.currency_id and line.currency_id.round(amount * sign) or 0.0
                line.second_amount_residual_currency = line.currency_id and line.currency_id.round(amount * sign) or 0.0
     
    @api.depends('third_debit', 'third_credit', 'amount_currency', 'currency_id', 'matched_debit_ids', 'matched_credit_ids', 'matched_debit_ids.amount', 'matched_credit_ids.amount', 'move_id.state')
    def _third_amount_residual(self):
        """ Computes the residual amount of a move line from a reconcilable account in the company currency and the line's currency.
            This amount will be 0 for fully reconciled lines or lines from a non-reconcilable account, the original line amount
            for unreconciled lines, and something in-between for partially reconciled lines.
        """
        for line in self:
            
            if not line.company_id.third_currency_id.id:
                line.third_amount_residual = 0
                line.third_amount_residual_currency = 0
            else:
                if not line.account_id.reconcile and line.account_id.internal_type != 'liquidity':
                    line.third_amount_residual = 0
                    line.third_amount_residual_currency = 0
                    continue
                
                amount = abs(line.third_debit - line.third_credit)
                value = abs(line.amount_currency) or 0.0
                if line.currency_id:
                    amount_residual_currency = line.currency_id._convert(value, line.move_id.company_id.third_currency_id, line.move_id.company_id, line.move_id.date) 
                else:
                    amount_residual_currency = line.company_currency_id._convert(value, line.move_id.company_id.third_currency_id, line.move_id.company_id, line.move_id.date) 
                sign = 1 if (line.third_debit - line.third_credit) > 0 else -1
                
                if not line.third_debit and not line.third_credit and line.amount_currency and line.currency_id:
                    sign = 1 if float_compare(line.amount_currency, 0, precision_rounding=line.currency_id.rounding) == 1 else -1
    
                for partial_line in (line.matched_debit_ids + line.matched_credit_ids):
                    sign_partial_line = sign if partial_line.credit_move_id == line else (-1 * sign)
                    
                    date = partial_line.credit_move_id.date if partial_line.debit_move_id == line else partial_line.debit_move_id.date
                    rate = line.company_id.third_currency_id.with_context(date=date).rate
                    if line.currency_id and line.amount_currency:
                        if partial_line.currency_id and partial_line.currency_id == line.move_id.company_id.third_currency_id:
                            amount_residual_currency += sign_partial_line * partial_line.amount_currency
                            amount += sign_partial_line * partial_line.amount_currency
                        else:
                            amount_residual_currency += sign_partial_line * partial_line.amount * rate
                            amount += sign_partial_line * partial_line.amount * rate
                    
                                                                                                      
                line.third_amount_residual = line.currency_id and line.currency_id.round(amount * sign) or 0.0
                line.third_amount_residual_currency = line.currency_id and line.currency_id.round(amount * sign) or 0.0
    
    def calculate_second_third_debit_credit(self):
        """
        Calculation of second and third debit/credit
        Get currency rate of second and third currency by date
        Convert to second and third currency the debit/credit in case second/third currency rate not equal to jv currency
        else the amount currency is used if jv currency equal to second currency or third currency
        
        Second/third credit/debit rounded with 6 digits
        """
        line = self
        date = line._context.get('rate_date') or fields.Date.today()
        
        company_id = line.move_id.company_id
        
        if (self._context.get('calculate_second_third_amount') or (not line.second_debit and not line.second_credit and not line.third_debit and not line.third_credit)):
            log.info("Calculating second, third, debit & credit for currency rate at date: %s", date)
            #ODOO-150: The below two lines are added on purpose, since there was an issue in getting selected company currency. 
            company_second_currency_rate_id = company_id.second_currency_id.with_context(dict(self._context or {}, date=self.move_id.invoice_date or fields.Date().today()))
            line_currency_rate_id = line.currency_id.with_context(date=self.move_id.date or fields.Date().today())
            company_third_currency_rate_id = company_id.third_currency_id.with_context(dict(self._context or {}, date=self.move_id.invoice_date or fields.Date().today()))
             
            second_debit, second_credit, third_debit, third_credit = 0, 0, 0, 0
            
            if company_second_currency_rate_id and company_second_currency_rate_id != line_currency_rate_id:
                second_debit = line.debit * company_second_currency_rate_id.rate
                second_credit = line.credit * company_second_currency_rate_id.rate
            elif company_second_currency_rate_id.id and company_second_currency_rate_id == line_currency_rate_id:
                second_debit = line.amount_currency > 0 and line.amount_currency or 0.0
                second_credit = line.amount_currency < 0 and -line.amount_currency or 0.0
            else:
                second_currency_balance = 0
                line_ids = self._context['line_ids'] if 'line_ids' in self._context else line.move_id.line_ids.ids
                for r_line in line.move_id.resolve_2many_commands(
                        'line_ids', line_ids, fields=['second_debit', 'second_credit']):
                    second_currency_balance += r_line.get('second_debit', 0) - r_line.get('second_credit', 0)
                 
                if second_currency_balance < 0:
                    second_debit = -second_currency_balance
                if second_currency_balance > 0:
                    second_credit = second_currency_balance
     
            if company_third_currency_rate_id and company_third_currency_rate_id != line_currency_rate_id:
                third_debit = line.debit * company_third_currency_rate_id.rate
                third_credit = line.credit * company_third_currency_rate_id.rate
            elif company_third_currency_rate_id.id and company_third_currency_rate_id == line_currency_rate_id:
                third_debit = line.amount_currency > 0 and line.amount_currency or 0.0
                third_credit = line.amount_currency < 0 and -line.amount_currency or 0.0
            else:
                third_currency_balance = 0
                line_ids = self._context['line_ids'] if 'line_ids' in self._context else line.move_id.line_ids.ids
                for r_line in line.move_id.resolve_2many_commands(
                        'line_ids', line_ids, fields=['third_debit', 'third_credit']):
                    third_currency_balance += r_line.get('third_debit', 0) - r_line.get('third_credit', 0)
                     
                if third_currency_balance < 0:
                    third_debit = -third_currency_balance
                if third_currency_balance > 0:
                    third_credit = third_currency_balance   
            
            line_second_debit = round(second_debit, company_id.second_currency_id.decimal_places)
            line_second_credit = round(second_credit, company_id.second_currency_id.decimal_places)
            line_third_debit = round(third_debit, company_id.third_currency_id.decimal_places)
            line_third_credit = round(third_credit, company_id.third_currency_id.decimal_places)

            
            line.with_context(check_move_validity=False).update({
                'second_debit': line_second_debit,
                'second_credit': line_second_credit,
                'third_debit': line_third_debit,
                'third_credit': line_third_credit,
            })
             
            log.info("Calculation result: Second D/C: %s/%s. Third D/C: %s/%s", line_second_debit, line_second_credit, line_third_debit, line_third_credit)
        
    ####################################################
    # Reconciliation methods
    ####################################################
    
    def check_full_reconcile(self):
        """
        This method check if a move is totally reconciled and if we need to create exchange rate entries for the move.
        In case exchange rate entries needs to be created, one will be created per currency present.
        In case of full reconciliation, all moves belonging to the reconciliation will belong to the same account_full_reconcile object.
        """
        if not self.user_has_groups('base.group_multi_currency'):
            super(AccountMoveLine, self).check_full_reconcile()
        else:
            self.check_full_reconcile_multi_currency()
             
    def check_full_reconcile_multi_currency(self):
        # Get first all aml involved
        todo = self.env['account.partial.reconcile'].search_read(['|', ('debit_move_id', 'in', self.ids), ('credit_move_id', 'in', self.ids)], ['debit_move_id', 'credit_move_id'])
        amls = set(self.ids)
        seen = set()
        while todo:
            aml_ids = [rec['debit_move_id'][0] for rec in todo if rec['debit_move_id']] + [rec['credit_move_id'][0] for rec in todo if rec['credit_move_id']]
            amls |= set(aml_ids)
            seen |= set([rec['id'] for rec in todo])
            todo = self.env['account.partial.reconcile'].search_read(['&', '|', ('credit_move_id', 'in', aml_ids), ('debit_move_id', 'in', aml_ids), '!', ('id', 'in', list(seen))], ['debit_move_id', 'credit_move_id'])

        partial_rec_ids = list(seen)
        if not amls:
            return
        else:
            amls = self.browse(list(amls))

        # If we have multiple currency, we can only base ourselves on debit-credit to see if it is fully reconciled
        currency = set([a.currency_id for a in amls if a.currency_id.id != False])
        multiple_currency = False
        if len(currency) != 1:
            currency = False
            multiple_currency = True
        else:
            currency = list(currency)[0]
        # Get the sum(debit, credit, amount_currency) of all amls involved
        total_debit = 0
        total_credit = 0
        total_amount_currency = 0
        total_second_debit = 0
        total_second_credit = 0
        total_third_debit = 0
        total_third_credit = 0
        maxdate = date.min
        to_balance = {}
        cash_basis_partial = self.env['account.partial.reconcile']
        
        for aml in amls:
            cash_basis_partial |= aml.move_id.tax_cash_basis_rec_id
            total_debit += aml.debit
            total_credit += aml.credit
            total_second_debit += aml.second_debit
            total_second_credit += aml.second_credit
            total_third_debit += aml.third_debit
            total_third_credit += aml.third_credit
            maxdate = max(aml.date, maxdate)
            total_amount_currency += aml.amount_currency
            # Convert in currency if we only have one currency and no amount_currency
            if not aml.amount_currency and currency:
                multiple_currency = True
                total_amount_currency += aml.company_id.currency_id._convert(aml.balance, currency, aml.company_id, aml.date)
            # If we still have residual value, it means that this move might need to be balanced using an exchange rate entry
            if aml.amount_residual != 0 or aml.amount_residual_currency != 0 or \
                aml.second_amount_residual != 0 or aml.second_amount_residual_currency != 0 or \
                aml.third_amount_residual != 0 or aml.third_amount_residual_currency != 0:
                
                aml_currency_id = aml.currency_id
                
                if not aml_currency_id:
                    log.info("Aml currency is empty => Using main currency instead while full reconciling")
                    aml_currency_id = aml.company_id.currency_id
                     
                if not to_balance.get(aml_currency_id):
                    to_balance[aml_currency_id] = [aml, 0, 0, 0]
                to_balance[aml_currency_id][0] += aml
                if aml_currency_id.id:
                    to_balance[aml_currency_id][1] += aml.amount_residual != 0 and aml.amount_residual or aml.amount_residual_currency
                    to_balance[aml_currency_id][2] += aml.second_amount_residual != 0 and aml.second_amount_residual or aml.second_amount_residual_currency
                    to_balance[aml_currency_id][3] += aml.third_amount_residual != 0 and aml.third_amount_residual or aml.third_amount_residual_currency
            
        # Check if reconciliation is total
        # To check if reconciliation is total we have 3 different use case:
        # 1) There are multiple currency different than company currency, in that case we check using debit-credit
        # 2) We only have one currency which is different than company currency, in that case we check using amount_currency
        # 3) We have only one currency and some entries that don't have a secundary currency, in that case we check debit-credit
        #   or amount_currency.
        # 4) Cash basis full reconciliation
        #     - either none of the moves are cash basis reconciled, and we proceed
        #     - or some moves are cash basis reconciled and we make sure they are all fully reconciled

        digits_rounding_precision = amls[0].company_id.currency_id.rounding
        digits_second_currency_rounding_precision = amls[0].company_id.second_currency_id.rounding
        digits_third_currency_rounding_precision = amls[0].company_id.third_currency_id.rounding
        log.info("AML to balance value: %s", to_balance)

        if (
            (
                not cash_basis_partial or (cash_basis_partial and all([p >= 1.0 for p in amls._get_matched_percentage().values()]))
            ) and
            (
                (currency and float_is_zero(total_amount_currency, precision_rounding=currency.rounding)) or
                (multiple_currency and float_compare(total_debit, total_credit, precision_rounding=digits_rounding_precision) == 0) or 
                (multiple_currency and amls[0].company_id.second_currency_id.id and float_compare(total_second_debit, total_second_credit, precision_rounding=digits_second_currency_rounding_precision) == 0) or 
                (multiple_currency and amls[0].company_id.third_currency_id.id and float_compare(total_third_debit, total_third_credit, precision_rounding=digits_third_currency_rounding_precision) == 0)
            )
        ):
            exchange_move_id = False
            log.info("Create a journal entry to book the difference due to foreign currency's exchange rate that fluctuates")

            missing_exchange_difference = False
            # Eventually create a journal entry to book the difference due to foreign currency's exchange rate that fluctuates
            if ( 
                to_balance and (any([not float_is_zero(residual, precision_rounding=digits_rounding_precision) for aml, residual, _, _ in to_balance.values()]) or 
                                (amls[0].company_id.second_currency_id.id and any([not float_is_zero(second_residual, precision_rounding=digits_second_currency_rounding_precision) for aml, _, second_residual, _ in to_balance.values()])) or 
                                (amls[0].company_id.third_currency_id.id and any([not float_is_zero(third_residual, precision_rounding=digits_third_currency_rounding_precision) for aml, _, _, third_residual in to_balance.values()])))
            ):
                if not self.env.context.get('no_exchange_difference'):
                    part_reconcile = self.env['account.partial.reconcile']
                    for aml_to_balance, total, second_total, third_total in to_balance.values():
                        total = round((total_debit - total_credit), 4)
                        second_total = round((total_second_debit - total_second_credit), 4)
                        third_total = round((total_third_debit - total_third_credit), 4)

                        if total or second_total or third_total:
                            exchange_move = self.env['account.move'].with_context(default_type='entry').create(
                            self.env['account.full.reconcile']._prepare_exchange_diff_move(move_date=maxdate, company=amls[0].company_id))
                            
                            log.info("Creating currency exchange rate for: %s. Total: %s, total second: %s, total third: %s", aml_to_balance, total, second_total, third_total)
                            rate_diff_amls, rate_diff_partial_rec = part_reconcile.create_exchange_rate_entry(aml_to_balance, exchange_move, total, second_total, third_total)
                            amls += rate_diff_amls
                            partial_rec_ids += rate_diff_partial_rec.ids
                            exchange_move.post()
                            exchange_move_id = exchange_move.id
                        else:
                            if not aml_to_balance.reconcile:
                                aml_to_balance.reconcile()
                        break
                else:
                    missing_exchange_difference = True
                    
            if not missing_exchange_difference:
                #mark the reference of the full reconciliation on the exchange rate entries and on the entries
                self.env['account.full.reconcile'].create({
                    'partial_reconcile_ids': [(6, 0, partial_rec_ids)],
                    'reconciled_line_ids': [(6, 0, amls.ids)],
                    'exchange_move_id': exchange_move_id,
                })
     
    def _reconcile_lines(self, debit_moves, credit_moves, field):
        """ This function loops on the 2 recordsets given as parameter as long as it
            can find a debit and a credit to reconcile together. It returns the recordset of the
            account move lines that were not reconciled during the process.
        """
        if not self.user_has_groups('base.group_multi_currency'):
            super(AccountMoveLine, self)._reconcile_lines(debit_moves, credit_moves, field)
        else:
            self._reconcile_lines_multi(debit_moves, credit_moves, field)
            
    def _reconcile_lines_multi(self, debit_moves, credit_moves, field):
        """ This function loops on the 2 recordsets given as parameter as long as it
            can find a debit and a credit to reconcile together. It returns the recordset of the
            account move lines that were not reconciled during the process.
        """
        (debit_moves + credit_moves).read([field])
        to_create = []
        cash_basis = debit_moves and debit_moves[0].account_id.internal_type in ('receivable', 'payable') or False
        cash_basis_percentage_before_rec = {}
        dc_vals ={}
        while (debit_moves and credit_moves):
            debit_move = debit_moves[0]
            credit_move = credit_moves[0]
            company_currency = debit_move.company_id.currency_id
            # We need those temporary value otherwise the computation might be wrong below
            temp_amount_residual = min(debit_move.amount_residual, -credit_move.amount_residual)
            temp_amount_residual_currency = min(debit_move.amount_residual_currency, -credit_move.amount_residual_currency)
            dc_vals[(debit_move.id, credit_move.id)] = (debit_move, credit_move, temp_amount_residual_currency)
            amount_reconcile = min(debit_move[field], -credit_move[field])
 
            #Remove from recordset the one(s) that will be totally reconciled
            # For optimization purpose, the creation of the partial_reconcile are done at the end,
            # therefore during the process of reconciling several move lines, there are actually no recompute performed by the orm
            # and thus the amount_residual are not recomputed, hence we have to do it manually.
            if amount_reconcile == debit_move[field]:
                debit_moves -= debit_move
            else:
                debit_moves[0].amount_residual -= temp_amount_residual
                debit_moves[0].amount_residual_currency -= temp_amount_residual_currency
 
            if amount_reconcile == -credit_move[field]:
                credit_moves -= credit_move
            else:
                credit_moves[0].amount_residual += temp_amount_residual
                credit_moves[0].amount_residual_currency += temp_amount_residual_currency
            
            #Check for the currency and amount_currency we can set
            currency = False
            amount_reconcile_currency = 0
            if field == 'amount_residual_currency':
                currency = credit_move.currency_id.id
                amount_reconcile_currency = temp_amount_residual_currency
                amount_reconcile = temp_amount_residual
 
            if cash_basis:
                tmp_set = debit_move | credit_move
                cash_basis_percentage_before_rec.update(tmp_set._get_matched_percentage())
             
            to_create.append({
                'debit_move_id': debit_move.id,
                'credit_move_id': credit_move.id,
                'amount': amount_reconcile,
                'amount_currency': amount_reconcile_currency,
                'currency_id': currency,
            })
 
        cash_basis_subjected = []
        part_rec = self.env['account.partial.reconcile']
        for partial_rec_dict in to_create:
            debit_move, credit_move, amount_residual_currency = dc_vals[partial_rec_dict['debit_move_id'], partial_rec_dict['credit_move_id']]
            # /!\ NOTE: Exchange rate differences shouldn't create cash basis entries
            # i. e: we don't really receive/give money in a customer/provider fashion
            # Since those are not subjected to cash basis computation we process them first
            if not amount_residual_currency and debit_move.currency_id and credit_move.currency_id:
                part_rec.create(partial_rec_dict)
            else:
                cash_basis_subjected.append(partial_rec_dict)
 
        for after_rec_dict in cash_basis_subjected:
            new_rec = part_rec.create(after_rec_dict)
            # if the pair belongs to move being reverted, do not create CABA entry
            if cash_basis and not (
                    new_rec.debit_move_id.move_id == new_rec.credit_move_id.move_id.reversed_entry_id
                    or
                    new_rec.credit_move_id.move_id == new_rec.debit_move_id.move_id.reversed_entry_id
            ):
                new_rec.create_tax_cash_basis_entry(cash_basis_percentage_before_rec)
        return debit_moves+credit_moves
                 
     
class AccountPartialReconcile(models.Model):
    _inherit = "account.partial.reconcile"
                 
    @api.model
    def create_exchange_rate_entry(self, aml_to_fix, move, total=None, second_total=None, third_total=None):
        """
        Automatically create a journal items to book the exchange rate
        differences that can occur in multi-currencies environment. That
        new journal item will be made into the given `move` in the company
        `currency_exchange_journal_id`, and one of its journal items is
        matched with the other lines to balance the full reconciliation.
    
        :param aml_to_fix: recordset of account.move.line (possible several
            but sharing the same currency)
        :param move: account.move
        :return: tuple.
            [0]: account.move.line created to balance the `aml_to_fix`
            [1]: recordset of account.partial.reconcile created between the
                tuple first element and the `aml_to_fix`
        """
        if not self.user_has_groups('base.group_multi_currency'):
            created_lines, partial_rec = super(AccountPartialReconcile, self).create_exchange_rate_entry(aml_to_fix, move)
        else:
            created_lines, partial_rec = self.create_exchange_rate_entry_multi_currency(aml_to_fix, move, total, second_total, third_total  )
              
        return created_lines, partial_rec
     
    def create_exchange_rate_entry_multi_currency(self, aml_to_fix, move, total=None, second_total=None, third_total=None):
        """
        Multi currency Automatically create a journal items to book the exchange rate
        differences that can occur in multi-currencies environment. That
        new journal item will be made into the given `move` in the company
        `currency_exchange_journal_id`, and one of its journal items is
        matched with the other lines to balance the full reconciliation.
    
        :param aml_to_fix: recordset of account.move.line (possible several
            but sharing the same currency)
        :param move: account.move
        :return: tuple.
            [0]: account.move.line created to balance the `aml_to_fix`
            [1]: recordset of account.partial.reconcile created between the
                tuple first element and the `aml_to_fix`
        """
        partial_rec = self.env['account.partial.reconcile']
        aml_model = self.env['account.move.line']

        created_lines = self.env['account.move.line']
        lines_to_create = []
        closing_lines_to_create = []
        for aml in aml_to_fix:
            line_vals = []
            #create the line that will compensate all the aml_to_fix
            debit = total < 0 and -total or 0.0
            credit = total > 0 and total or 0.0
                 
            second_debit = second_total < 0 and -second_total or 0.0
            second_credit = second_total > 0 and second_total or 0.0
                 
            third_debit = third_total < 0 and -third_total or 0.0
            third_credit = third_total > 0 and third_total or 0.0
              
            log.info("D: %s, C: %s, SD: %s, SC: %s, TD: %s, TC: %s", debit, credit, second_debit, second_credit, third_debit, third_credit)
                 
            amount_currency = aml.amount_residual_currency and -aml.amount_residual_currency or 0.0
            
            lines_to_create.append({
                'name': _('Currency exchange rate difference'),
                'debit': aml.amount_residual < 0 and -aml.amount_residual or 0.0,
                'credit': aml.amount_residual > 0 and aml.amount_residual or 0.0,
                'second_debit': aml.second_amount_residual < 0 and -aml.second_amount_residual or 0.0,
                'second_credit': aml.second_amount_residual > 0 and aml.second_amount_residual or 0.0,
                'third_debit': aml.third_amount_residual < 0 and -aml.third_amount_residual or 0.0,
                'third_credit': aml.third_amount_residual > 0 and aml.third_amount_residual or 0.0,
                'account_id': aml.account_id.id,
                'move_id': move.id,
                'currency_id': aml.currency_id.id,
                #'amount_currency': (aml.currency_id != aml.company_currency_id) and amount_currency or 0,
                'manual_entry_computation': True,
                'partner_id': aml.partner_id.id,
            })
            #create the counterpart on exchange gain/loss account
            exchange_journal = move.company_id.currency_exchange_journal_id
            if aml.amount_residual != 0:
                closing_lines_to_create.append({
                        'name': _('Currency exchange rate difference'),
                        'debit': aml.amount_residual > 0 and aml.amount_residual or 0.0,
                        'credit': aml.amount_residual < 0 and -aml.amount_residual or 0.0,
                        'account_id': total > 0 and exchange_journal.default_debit_account_id.id or exchange_journal.default_credit_account_id.id,
                        'move_id': move.id,
                        'second_debit': 0,
                        'second_credit': 0,
                        'third_debit': 0,
                        'third_credit': 0,
                        'currency_id': aml.currency_id.id,
                        #'amount_currency': (aml.currency_id != aml.company_currency_id) and amount_currency or 0,
                        'manual_entry_computation': True,
                        'partner_id': aml.partner_id.id,
                    })
                
            if aml.second_amount_residual != 0:
                closing_lines_to_create.append({
                        'name': _('Currency exchange rate difference'),
                        'second_debit': aml.second_amount_residual > 0 and aml.second_amount_residual or 0.0,
                        'second_credit': aml.second_amount_residual < 0 and -aml.second_amount_residual or 0.0,
                        'account_id': second_total > 0 and exchange_journal.default_debit_account_id.id or exchange_journal.default_credit_account_id.id,
                        'move_id': move.id,
                        'credit': 0,
                        'debit': 0,
                        'third_debit': 0,
                        'third_credit': 0,
                        'currency_id': aml.currency_id.id,
                        'manual_entry_computation': True,
                        #'amount_currency': amount_currency,
                        'partner_id': aml.partner_id.id,
                    })
                
            if aml.third_amount_residual != 0:
                closing_lines_to_create.append({
                        'name': _('Currency exchange rate difference'),
                        'credit': 0,
                        'debit': 0,
                        'second_debit': 0,
                        'second_credit': 0,
                        'third_debit': aml.third_amount_residual > 0 and aml.third_amount_residual or 0.0,
                        'third_credit': aml.third_amount_residual < 0 and -aml.third_amount_residual or 0.0,
                        'account_id': third_total > 0 and exchange_journal.default_debit_account_id.id or exchange_journal.default_credit_account_id.id,
                        'move_id': move.id,
                        'manual_entry_computation': True,
                        'currency_id': aml.currency_id.id,
                        #'amount_currency': amount_currency,
                        'partner_id': aml.partner_id.id,
                    })
                
        #reconcile all aml_to_fix
        final_aml_lines = []
        for temp_line in lines_to_create:
            found = False
            for exist_line in final_aml_lines:
                if exist_line['partner_id'] == temp_line['partner_id'] and exist_line['account_id'] == temp_line['account_id'] and exist_line['currency_id'] == temp_line['currency_id']:
                    found = True
                    exist_line['credit'] += temp_line['credit']
                    exist_line['debit'] += temp_line['debit']
                    exist_line['second_credit'] += temp_line['second_credit']
                    exist_line['second_debit'] += temp_line['second_debit']
                    exist_line['third_credit'] += temp_line['third_credit']
                    exist_line['third_debit'] += temp_line['third_debit']
            if not found:
                final_aml_lines.append(temp_line)

        for temp_line in closing_lines_to_create:
            found = False
            for exist_line in final_aml_lines:
                if exist_line['partner_id'] == temp_line['partner_id'] and exist_line['account_id'] == temp_line['account_id'] and exist_line['currency_id'] == temp_line['currency_id']:
                    found = True
                    exist_line['credit'] += temp_line['credit'] or 0
                    exist_line['debit'] += temp_line['debit'] or 0
                    exist_line['second_credit'] += temp_line['second_credit'] or 0
                    exist_line['second_debit'] += temp_line['second_debit'] or 0
                    exist_line['third_credit'] += temp_line['third_credit'] or 0
                    exist_line['third_debit'] += temp_line['third_debit'] or 0
            if not found:
                final_aml_lines.append(temp_line)
        created_aml_ids = []                    
        for temp_line in final_aml_lines:
            if temp_line['second_credit']>temp_line['second_debit']:
                temp_line['second_credit'] = temp_line['second_credit'] - temp_line['second_debit']
                temp_line['second_debit'] = 0
            else:
                temp_line['second_debit'] = temp_line['second_debit'] - temp_line['second_credit']
                temp_line['second_credit'] = 0

            if temp_line['third_credit']>temp_line['third_debit']:
                temp_line['third_credit'] = temp_line['third_credit'] - temp_line['third_debit']
                temp_line['third_debit'] = 0
            else:
                temp_line['third_debit'] = temp_line['third_debit'] - temp_line['third_credit']
                temp_line['third_credit'] = 0

            if temp_line['credit']>temp_line['debit']:
                temp_line['credit'] = temp_line['credit'] - temp_line['debit']
                temp_line['debit'] = 0
            else:
                temp_line['debit'] = temp_line['debit'] - temp_line['credit']
                temp_line['credit'] = 0
                    
            res = aml_model.with_context(manual_entry_computation=True, check_move_validity=False).create(temp_line)
            created_aml_ids.append(res.id)
            created_lines |= res
        for temp_line in lines_to_create:
            partial_rec |= self.create(
                self._prepare_exchange_diff_partial_reconcile(
                        aml=aml,
                        line_to_reconcile=aml_model.search([('account_id', '=',temp_line['account_id']),('id','in',created_aml_ids),('currency_id','=',temp_line['currency_id']),('partner_id','=',temp_line['partner_id'])],limit=1),
                        currency=aml.currency_id or False)
            )
            
            
        return created_lines, partial_rec