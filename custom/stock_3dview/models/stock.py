# Copyright 2020 Openindustry.it SAS
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import _, api, models


class StockLocation(models.Model):
    _inherit = "stock.location"

    def threedView(self):
        return {
            "name": _("Location 3D View"),
            "type": "ir.actions.act_window",
            "customdata_request_type": "tagged",
            "view_mode": "threed",
            "res_model": "stock.location",
            "domain": [("id", "child_of", self.id)],
            "context": dict(self.env.context, request_type="tagged"),
        }

    @api.model
    def get_3d_view_item_info(self, id):
        location = self.browse(id)
        stock_quants = []
        for stock_quant in self.env["stock.quant"].search(
            [("location_id", "=", location.id),("quantity","=",1)]
        ):
            booking_num = ""
            container_num = ""
            pallet = self.env['shipment_order.pallet'].search([
                        ("name", "=", stock_quant.lot_id.name)
                     ],limit=1)
            if pallet.id:
                container = self.env['shipment_order.container'].search([
                        ("id", "=", pallet.container_id.id)
                     ],limit=1)
                booking_num = container.ref_number
                container_num = container.container_number
                
            stock_quants.append(
                {
                    "product_name": stock_quant.product_id.name,
                    "product_qty": stock_quant.quantity,
                    "product_code": stock_quant.product_id.default_code,
                    "product_lot": stock_quant.lot_id.name,
                    "booking_num": booking_num,
                    "container_num": container_num,
                }
            )
        return {"barcode": location.name, "stock_quants": stock_quants}
