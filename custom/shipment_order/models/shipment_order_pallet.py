# -*- coding: utf-8 -*-
from odoo import api, models, fields, _
from datetime import date, datetime
from odoo.exceptions import UserError
import json

class ShipmentPallet(models.Model):
    _name = "shipment_order.pallet"
    _description = "Shipment Pallets"

    qr_code_data = fields.Char('QR Code', required=True)
    name = fields.Char('Pallet ID', index='trigram')
    cargo_length = fields.Integer('Cargo Length')
    cargo_width = fields.Integer('Cargo Width')
    cargo_height = fields.Integer('Cargo Height')
    company_id = fields.Many2one(
        'res.company', 'Company', required=True,
        default=lambda s: s.env.company.id, index=True,ondelete='cascade')

    container_id = fields.Many2one('shipment_order.container', 'Container',  index=True, ondelete='cascade', check_company=True)
    container_number = fields.Char(related='container_id.container_number', string ='Dummy Container No.')
    container_number_actual = fields.Char(related='container_id.container_number_actual',string ='Actual Container No.')

    move_line_id = fields.Many2one('stock.move.line', string='Stock Move Line', ondelete='cascade')
    outbound_move_line_id = fields.Many2one('stock.move.line', string='Outbound Stock Move Line', ondelete='cascade')

    transport_order_ids = fields.One2many('shipment_order.move', 'pallet_id', 'Transport Orders')

    def unlink(self):
        if self.move_line_id.is_wcs_order:
            if self.move_line_id.transport_order_id:
                if self.move_line_id.transport_order_id.wcs_state == 'completed':
                    raise UserError(_('This pallet has already been moved to the destination location and cannot be deleted'))
                if self.move_line_id.transport_order_id.wcs_state not in ('cancelled', 'cancelling'):
                    raise UserError(_('This pallet is linked to an active WCS transport order. Please cancel the order in WCS before deleting'))
        return super(ShipmentPallet, self).unlink()


class ShipmentPalletContainer(models.Model):
    _name = "shipment_order.container"
    _description = "Shipment Container"
    _rec_name = 'container_number'
    
    container_number = fields.Char('Container No.', index=True)
    container_number_actual = fields.Char('Actual Container No.', index=True)
    ref_number = fields.Char('Bkg/BL No.', index=True)
    seal_number = fields.Char(string="Seal No.")
    container_size = fields.Selection(selection=[
        ('20', "20 Ft."),
        ('40', "40 Ft.")
    ], default='20', required=True)
    
    pallet_ids = fields.One2many('shipment_order.pallet', 'container_id', 'Pallets')
    picking_id = fields.Many2one('stock.picking', 'Transfer Doc.', index=True, ondelete='cascade', check_company=True)
    outgoing_picking_id = fields.Many2one('stock.picking', 'Out Transfer Doc.', index=True, ondelete='cascade', check_company=True)
    company_id = fields.Many2one(
        'res.company', 'Company', required=True,
        default=lambda s: s.env.company.id, index=True,ondelete='cascade')
    
    def unlink(self):
        if self.outgoing_picking_id:
            raise UserError(_('Container is linked to an incoming movement and cannot be deleted'))
        for pallet in self.pallet_ids:
            if pallet.move_line_id.is_wcs_order:
                if pallet.move_line_id.transport_order_id:
                    if pallet.move_line_id.transport_order_id.wcs_state == 'completed':
                        raise UserError(_('Pallet ' + pallet.name + ' in this container has already been moved to the destination location and cannot be deleted'))
                    if pallet.move_line_id.transport_order_id.wcs_state not in ('cancelled', 'cancelling'):
                        raise UserError(_('Pallet ' + pallet.name + '  in this container is linked to an active WCS transport order. Please cancel the order in WCS before deleting'))
        return super(ShipmentPalletContainer, self).unlink()
    

class ShipmentPalletTransportOrder(models.Model):
    _name = "shipment_order.move"
    _description = "WCS Transport Orders"
    
    name = fields.Char('Name', compute="_get_name")
    location_id = location_id = fields.Many2one(
        'stock.location', 'Source Location',
        index=True, required=True,
        check_company=True)
    location_dest_id = fields.Many2one(
        'stock.location', 'Destination Location',
        index=True, required=True,
        check_company=True)
    qr_code = fields.Char('QR Code Data')
    
    #WCS states: created, queued, assigned, pickup, pickup_in_progress, delivery, delivery_in_progress, completed, cancelled, error
    wcs_state_1 = fields.Char('1st Transport Order State')
    wcs_state_2 = fields.Char('2nd Transport Order State')
    wcs_state_summary = fields.Html('WCS State', compute="_get_wcs_summary")
    wcs_overall_state = fields.Char('WCS Overall State', compute="_get_wcs_overall_state")
    wcs_id_1 = fields.Char('1st WCS Transport Order ID')
    wcs_id_2 = fields.Char('2nd WCS Transport Order ID')
    wcs_id_summary = fields.Html('WCS IDs', compute="_get_wcs_summary")
    
    wcs_pickup_1 = fields.Char('1st Pickup')
    wcs_pickup_2 = fields.Char('2nd Pickup')
    wcs_dropoff_1 = fields.Char('1st Dropoff')
    wcs_dropoff_2 = fields.Char('2nd Dropoff')
    wcs_order_desc = fields.Html('WCS Transport Orders', compute="_get_wcs_summary")
    wcs_timestamp = fields.Datetime('WCS Timestamp')

    log_ids = fields.One2many('shipment_order.movelog', 'transport_order', 'Log')

    pallet_id = fields.Many2one('shipment_order.pallet', 'Pallet', index=True, check_company=True, ondelete='cascade')
    picking_id = fields.Many2one('stock.picking', 'Transfer Doc.', index=True, readonly=True, ondelete='cascade')
    move_line_id = fields.Many2one('stock.move.line', string='Stock Move Line')
    ref_number = fields.Char(string="B/L/Bkg No.", related="picking_id.ref_number")
    
    company_id = fields.Many2one(
        'res.company', 'Company', required=True,
        default=lambda s: s.env.company.id, index=True, ondelete='cascade')
    
    all_wcs_log_ids = fields.One2many('shipment_order.movelog',compute="_get_wcs_logs")

    def _get_name(self):
        for record in self:
            if record.wcs_id_1:
                record.name = 'WCS Order(s): ' + str(record.wcs_id_1)
            else: record.name = ""
            if record.wcs_id_2:
                record.name += ' & ' + str(record.wcs_id_2)
    
    @api.depends('log_ids')
    def _get_wcs_logs(self):
        for record in self:
            record.all_wcs_log_ids = self.env['shipment_order.movelog'].search([],order='wcs_timestamp desc')

    
    #@api.depends('wcs_id_1','wcs_state_1', 'wcs_pickup_1', 'wcs_dropoff_1', 'wcs_state_2', 'wcs_id_2','wcs_pickup_2',
    #             'wcs_dropoff_2')
    def _get_wcs_overall_state(self):
        for record in self:
            if record.wcs_state_1 == 'created' and (record.wcs_state_2 == 'created' or record.wcs_state_2 == False):
                record.wcs_overall_state = 'created'
            elif  record.wcs_state_1 == 'completed' and (record.wcs_state_2 == 'completed' or record.wcs_state_2 == False): 
                record.wcs_overall_state = 'completed'
            elif  record.wcs_state_1 == 'cancelled' or record.wcs_state_2 == 'cancelled': 
                record.wcs_overall_state = 'cancelled'
            elif  record.wcs_state_1 == 'cancelling' or record.wcs_state_2 == 'cancelling': 
                record.wcs_overall_state = 'cancelling'
            elif  record.wcs_state_1 == 'error' or record.wcs_state_2 == 'error': 
                record.wcs_overall_state = 'error'
            else: record.wcs_overall_state = 'in progress'

    def _get_wcs_summary(self):
        for record in self:
            record.wcs_state_summary = 'TO 1 [ID: ' + record.wcs_id_1 + ']: ' + record.wcs_state_1
            record.wcs_id_summary = 'TO 1 ID:' + record.wcs_id_1
            record.wcs_order_desc = 'TO 1 [ID:' + record.wcs_id_1 + ']: Move from ' + record.wcs_pickup_1 + ' to ' + record.wcs_dropoff_1
            if record.wcs_state_2:
                if record.wcs_state_2 != '':
                    record.wcs_state_summary += ' TO 2 [ID: ' + record.wcs_id_2 + ']: ' + record.wcs_state_2
                    record.wcs_id_summary += ' TO 2 ID: ' + record.wcs_id_2
                    record.wcs_order_desc += ' TO 2 [ID: ' + record.wcs_id_2 + ']: Move from ' + record.wcs_pickup_2 + ' to ' + record.wcs_dropoff_2
            #WCS states: created, queued, assigned, pickup, pickup_in_progress, delivery, delivery_in_progress, completed, cancelled, error
    
            

class ShipmentPalletTransportOrderLog(models.Model):
    _name = "shipment_order.movelog"
    _description = "WCS Transport Order Log"

    name = fields.Char('Name', compute = '_get_name')
    transport_order = fields.Many2one('shipment_order.move', 'Transport Order', index=True,ondelete='cascade')
    transport_order_number = fields.Integer("1st/2nd Transport Order")
    remarks = fields.Text('Remarks')
    wcs_id = fields.Char('Transport Order ID')
    wcs_message = fields.Char('WCS Message')
    wcs_message_type = fields.Char('Message Type')
    wcs_message_code = fields.Char('WCS Status Code')
    wcs_notification_code = fields.Char('WCS Notification Code')
    wcs_timestamp = fields.Datetime('WCS Timestamp')
    wcs_raw_data = fields.Text('Raw Data')
    wcs_raw_data_html = fields.Html('Data', compute="_compute_data_html")

    ref_number =fields.Char('BL/Bkg No.',related="transport_order.picking_id.ref_number")
    pallet_id =fields.Char('Pallet ID',related="transport_order.pallet_id.name")
    container_number =fields.Char('Container',related="transport_order.move_line_id.container_number")

    def _get_name(self):
        for record in self:
            if record.transport_order.wcs_id_1 == self.wcs_id and record.transport_order.wcs_id_1 != False:
                record.name = 'Log for WCS Order: ' + record.transport_order.wcs_id_1
            elif record.transport_order.wcs_id_2 == self.wcs_id and record.transport_order.wcs_id_2 != False: 
                record.name = 'Log for WCS Order: ' + record.transport_order.wcs_id_2
            else: record.name = ""
    def _compute_data_html(self):
        raw_data = self.wcs_raw_data.replace('\\r\\n', '<br />').replace('\r\n', '<br />')
        html_data = json.dumps(raw_data, indent=4).replace("  ","&nbsp;&nbsp;&nbsp;").replace('\\"','"')
        self.wcs_raw_data_html = html_data

class ShipmentPalletStagingState(models.Model):
    _name = "shipment_order.staging.state"
    _description = "WCS Staging Location State"

    location_id = fields.Many2one('stock.location', 'Location', index=True,ondelete='cascade')
    pallet_id = fields.Many2one('shipment_order.pallet', 'Pallet', index=True,ondelete='cascade')
    pallet_name =fields.Char('Pallet ID',related="pallet_id.name")
    staging_sequence = fields.Integer('Sequence', compute='_get_staging_sequence', store=True)
    pallet_date = fields.Datetime('Date')

    def _get_staging_sequence(self):
        staging_category = self.env['generic.tag.category'].search([
                                ('code','=', 'stgout')
                            ], limit=1)
        for record in self:
            for tag in record.location_id.generic_tag_ids:
                if tag.category_id.id == staging_category.id:
                    record.staging_sequence = tag.sequence
                    break

class ShipmentPalletElevatedTray(models.Model):
    _name = "shipment_order.elevated.tray"
    _description = "Elevated Tray"

    name = fields.Char('Name')
    open_side_code = fields.Char('Open Side Code')
    closed_side_code = fields.Char('Closed Side Code')
    pallet_id = fields.Many2one('shipment_order.pallet', 'Pallet', index=True,ondelete='cascade')
    pallet_date = fields.Datetime('Date', default=datetime.today())
    occupied_state = fields.Char('Current Status', default='Empty') #Empty/Reserved/Occupied
    priority = fields.Integer('Priority')

    _sql_constraints = [
                        ('elevated_tray_name_unique', 'unique(name)', 'Elevated tray name should be unique.'),
                        ('elevated_tray_open_side_code_unique', 'unique(open_side_code)', 'Elevated tray open side code should be unique.'),
                        ('elevated_tray_closed_side_code_unique', 'unique(closed_side_code)', 'Elevated tray closed side code should be unique.'),
                    ]




