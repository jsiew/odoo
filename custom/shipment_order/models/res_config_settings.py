from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    wms_interface_url = fields.Char('WMS Interface URL', config_parameter='shipment_order.wms_interface_url')
    wms_interface_api_key = fields.Char('WMS Interface API Key', config_parameter='shipment_order.wms_interface_api_key')
    wcs_system_name = fields.Char('WCS System Name', config_parameter='shipment_order.wcs_system_name')
    wcs_subsystem_id = fields.Integer('WCS Subsystem ID', config_parameter='shipment_order.wcs_subsystem_id')
    shipment_pallet_max_height = fields.Integer('Pallet Max Height', config_parameter='shipment_order.shipment_pallet_max_height')
    shipment_short_pallet_max_height = fields.Integer('Short Pallet Max Height', config_parameter='shipment_order.shipment_short_pallet_max_height')
    validate_elevated_tray_qr = fields.Boolean('Validate Elevated Tray Pallet QR', config_parameter='shipment_order.validate_elevated_tray_qr')
    validate_qr = fields.Boolean('Validate Pallet QR', config_parameter='shipment_order.validate_qr')
    short_dummy_pallet_height = fields.Integer('Short Dummy Pallet Height', config_parameter='shipment_order.short_dummy_pallet_height', help='Will be auto added to height of short pallets')
    tall_dummy_pallet_height = fields.Integer('Tall Dummy Pallet Height', config_parameter='shipment_order.tall_dummy_pallet_height', help='Will be auto added to height of tall pallets')
    module_shipment_order = fields.Boolean("General Settings")
