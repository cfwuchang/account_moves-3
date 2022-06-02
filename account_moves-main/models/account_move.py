
from odoo import api, fields, models, _
from odoo.exceptions import UserError

class AccountMove(models.Model):
    _inherit = 'account.move'
    
    purchase_vendor_bill_id_list = fields.Many2many('purchase.bill.union', store=False, readonly=True,
        states={'draft': [('readonly', False)]},
        string=u'多选票单',
        help="Auto-complete from a past bill / purchase order.")
    
    amount_total = fields.Monetary(string='Total', store=True, readonly=False,
        compute='_compute_amount',
        inverse='_inverse_amount_total')
    amount_residual = fields.Monetary(string='Amount Due', store=True,readonly=False,
        compute='_compute_amount')

    @api.onchange('partner_id')
    def _partner_id(self):
        att_model = self.env['purchase.bill.union']
        if self.partner_id:
            self.write({'invoice_line_ids':()})
            query = [('partner_id.name', '=', self.partner_id.name),('purchase_order_id','!=',False)] 
            self.purchase_vendor_bill_id_list=att_model.search(query)
            self._onchange_purchase_auto_complete()
    @api.onchange('_onchange_purchase_auto_complete_list', 'purchase_id')
    # @api.model
    def _onchange_purchase_auto_complete_list(self):
        ''' Load from either an old purchase order, either an old vendor bill.

        When setting a 'purchase.bill.union' in 'purchase_vendor_bill_id_list':
        * If it's a vendor bill, 'invoice_vendor_bill_id' is set and the loading is done by '_onchange_invoice_vendor_bill'.
        * If it's a purchase order, 'purchase_id' is set and this method will load lines.

        /!\ All this not-stored fields must be empty at the end of this function.
        '''
        self.write({'invoice_line_ids':()})
        for i in self.purchase_vendor_bill_id_list:
            if i.vendor_bill_id:
                self.invoice_vendor_bill_id = i.vendor_bill_id
                self._onchange_invoice_vendor_bill()
            elif i.purchase_order_id:
                self.purchase_id = i.purchase_order_id

            if not self.purchase_id:
                return

            # Copy data from PO
            invoice_vals = self.purchase_id.with_company(self.purchase_id.company_id)._prepare_invoice()
            invoice_vals['currency_id'] = self.line_ids and self.currency_id or invoice_vals.get('currency_id')
            del invoice_vals['ref']
            self.update(invoice_vals)

            # Copy purchase lines.
            po_lines = self.purchase_id.order_line - self.line_ids.mapped('purchase_line_id')
            new_lines = self.env['account.move.line']
            for line in po_lines.filtered(lambda l: not l.display_type):
                if line.qty_received != 0:
                    new_line = new_lines.new(line._prepare_account_move_line(self))
                    new_line.account_id = new_line._get_computed_account()
                    new_line._onchange_price_subtotal()
                    new_lines += new_line
            new_lines._onchange_mark_recompute_taxes()

            # Compute invoice_origin.
            origins = set(self.line_ids.mapped('purchase_line_id.order_id.name'))
            self.invoice_origin = ','.join(list(origins))

            # Compute ref.
            refs = self._get_invoice_reference()
            self.ref = ', '.join(refs)

            # Compute payment_reference.
            if len(refs) == 1:
                self.payment_reference = refs[0]

            self.purchase_id = False
            self._onchange_currency()
            self.partner_bank_id = self.bank_partner_id.bank_ids and self.bank_partner_id.bank_ids[0]
