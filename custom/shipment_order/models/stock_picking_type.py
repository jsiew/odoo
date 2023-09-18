# -*- coding: utf-8 -*-
from odoo import models, fields
class StockPickingType(models.Model):
    _inherit = "stock.picking.type"
    
    def action_open_shipment_wizard(self):
        return{
            'name': "Scan Pallet",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'shipment_order.scan',
            'view_id': self.env.ref('shipment_order.shipment_wizard_view').id,
            'target': 'new',
            'context': {'barcode': self.barcode, 'new_record': True} 
        }
    
    def action_open_shipment_outbound_wizard(self):
        return{
            'name': "Retrieve Booking",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'shipment_order.scan.out',
            'view_id': self.env.ref('shipment_order.shipment_outbound_wizard_view').id,
            'target': 'new',
            'context': {'new_record': True} 
        }