from odoo import api, fields, models, _

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    x_remark =fields.Char(string=u"备注",readonly=False,)

    x_price = fields.Float(string=u'含税单价',compute='_get_x_price',readonly=False,)

    x_date = fields.Date(string=u"到货时间",compute='_get_x_date',readonly=False,)

    def _get_x_price(self):
        for obj in self:
            obj.x_price=obj.purchase_line_id.x_price
    
    def _get_x_date(self):
        for obj in self:
            for j in obj.purchase_line_id.move_ids:
                if j.product_id.id==obj.product_id.id:
                    obj.x_date=j.date