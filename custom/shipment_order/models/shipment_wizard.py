from odoo import models, fields, api, exceptions, _
from datetime import date, datetime
import xml.etree.ElementTree as ET
import requests, json
from odoo.exceptions import ValidationError
from json import JSONDecodeError
import operator
import logging

_logger = logging.getLogger(__name__)

class ShipmentMoveEditWizard(models.TransientModel):
    _name = "shipment_order.move.edit.wizard"
    _description = "Edit WCS Order State"

    move_line_id = fields.Many2one('stock.move.line', 'Move Line')
    transport_id = fields.Many2one('shipment_order.move', 'WCS Order')
    wcs_desc = fields.Html(string="WCS Order Description",related='transport_id.wcs_order_desc')
    wcs_id_1 = fields.Char(string='WCS Order ID',related='transport_id.wcs_id_1')
    wcs_id_2 = fields.Char(string='WCS Order ID',related='transport_id.wcs_id_2')
    curr_state_1 = fields.Char(string='WCS Order 1 State', related='transport_id.wcs_state_1')
    curr_state_2 = fields.Char(string='WCS Order 2 State', related='transport_id.wcs_state_2')
    new_state = fields.Selection('_get_valid_states', required=True)
    update_wcs = fields.Boolean('Update WCS Order', default=False)

    @api.model
    def create(self, vals_list):
        return super().create(vals_list)
    
    def _get_valid_states(self):
        states=[('cancelled', 'Cancelled'),('completed', 'Completed')]
        id = self.env.context.get('transport_order')
        if (id):
            if self.curr_state_1 in ('cancelled','completed') or self.curr_state_2 in ('cancelled','completed'):
                raise exceptions.ValidationError("WCS orders in completed/cancelled state cannot be edited")
            else:
                states=[('cancelled', 'Cancelled'),('completed', 'Completed')]
        else:
            states=[('cancelled', 'Cancelled'),('completed', 'Completed')]
        return states 
    
    @api.model
    def default_get(self, fields):
        result = super(ShipmentMoveEditWizard, self).default_get(fields)      
        id = self.env.context.get('transport_order')
        move_line_id = self.env.context.get('move_line')

        transport_order = self.env['shipment_order.move'].browse(id)
        move_line = self.env['stock.move.line'].browse(move_line_id)
        if transport_order.id:
            result.update({'transport_id': transport_order, 
                           'curr_state_1': transport_order.wcs_state_1, 
                           'curr_state_2': transport_order.wcs_state_2, 
                           'wcs_id_1': transport_order.wcs_id_1,
                           'wcs_id_2': transport_order.wcs_id_2})
        if move_line.id:
            result.update({'move_line_id': move_line})
        if move_line.id == False and transport_order.id == False: 
            raise exceptions.ValidationError("Invalid transport order id")
        return result
    
    def _complete_move_line(self, move_line):
        move_line.write({'qty_done': 1, 'reserved_uom_qty':0})
        move_line._action_done()
        move_line.write({'state': 'confirmed'})
    
    def _delete_move_line(self, move_line):
        move_line.write({'qty_done': 0, 'reserved_uom_qty':0, 'state': 'draft'})
        lot_id = move_line.lot_id
        #delete move line
        move_line.unlink()
        #delete quant
        quants = self.env['stock.quant'].search([
                                    ('lot_id','=', lot_id.id)
                                ])
        for quant in quants:
            quant.unlink()
        #delete lot
        lot_id.unlink()
    
    def _clear_staging(self, pallet_id):
        #clear staging state
        staging_id = self.env['shipment_order.staging.state'].search([
                                    ('pallet_id','=', pallet_id.id)
                                ])
        if staging_id.id:
            staging_id.write({'pallet_id':None, 'pallet_date':None})

    def action_update_order(self):
        record = self.transport_id
        
        if record.id:
            old_state_1 = record.wcs_state_1
            old_state_2 = record.wcs_state_2

            #completed state need not be sent to WCS, for updating in case WMS did not receive WCS notification
            if self.update_wcs and self.new_state == 'completed':
                self.update_wcs = False

            #check in case WCS updated the state before form was submitted
            if record.wcs_overall_state in ('cancelled','completed'):
                raise exceptions.ValidationError("WCS orders in completed/cancelled state cannot be edited")
            
            if self.update_wcs and self.new_state == 'cancelled':
                wms_interface_url = self.env['ir.config_parameter'].sudo().get_param('shipment_order.wms_interface_url')
                
                #cancel transport order 1
                if record.wcs_state_1 not in ('cancelled','completed'):

                    data = {
                        "wcs_id": record.wcs_id_1
                    }

                    try:
                        response = requests.post(wms_interface_url + '/DeleteTransportOrder', json=data)
                        if response.ok:
                            try:
                                response_json = response.json()
                            except JSONDecodeError:
                                raise ValidationError('Response could not be serialized: ' + response.text)
                            except Exception as err:
                                raise exceptions.UserError('Error sending request to WCS, please try again. '+ f"Unexpected {err=}, {type(err)=}")
                            result = bool(response_json['result'])
                            msg = response_json['msg']
                            statusCode = response_json['statusCode']
                            responseCode = response_json['code']
                            data = response_json['data']

                            if result:
                                remarks = 'Transport Order ' + record.wcs_id_1 + ' Manually Cancelled [Old State: '+ old_state_1 +']'
                                wcs_message_type = 'system'
                                record.write({'wcs_state_1': 'cancelled'})
                                msg = ''
                            else:
                                wcs_message_type = 'system'
                                raise exceptions.UserError('Error sending request to WCS, please try again. Status Code:' + statusCode + '. ' + msg)
                                
                            log_obj = self.env['shipment_order.movelog']
                            log_id = log_obj.create({'remarks': remarks,
                                                            'wcs_message': msg,
                                                            'wcs_message_type':wcs_message_type,
                                                            'wcs_message_code': statusCode,
                                                            'wcs_notification_code': responseCode,
                                                            'wcs_timestamp': datetime.today(),
                                                            'wcs_raw_data':data,
                                                            'transport_order' : None,
                                                            'transport_order_number': None,
                                                            'wcs_id': record.wcs_id_1})
                        else: raise exceptions.UserError('Error sending request to WCS, please try again. Status Code:' + str(response.status_code))
                    except Exception as err:
                        raise exceptions.UserError('Error sending request to WCS, please try again. '+ f"Unexpected {err=}, {type(err)=}")

                #cancel transport order 2
                if record.wcs_id_2 and record.wcs_state_2 not in ('cancelled','completed'):

                    data = {
                        "wcs_id": record.wcs_id_2,
                    }

                    try:
                        response = requests.post(wms_interface_url + '/DeleteTransportOrder', json=data)
                        if response.ok:
                            try:
                                response_json = response.json()
                            except JSONDecodeError:
                                raise ValidationError('Response could not be serialized: ' + response.text)
                            result = bool(response_json['result'])
                            msg = response_json['msg']
                            statusCode = response_json['statusCode']
                            responseCode = response_json['code']
                            data = response_json['data']

                            if result:
                                record.write({'wcs_state_2': 'cancelled'})
                                remarks = 'Transport Order ' + record.wcs_id_2 + ' Manually Cancelled [Old State: '+ old_state_2 +']'
                                wcs_message_type = 'system'
                                msg = ''
                            else:
                                wcs_message_type = 'system'
                                raise exceptions.UserError('Error sending request to WCS, please try again. Status Code:' + str(response.status_code))
                                
                            log_obj = self.env['shipment_order.movelog']
                            log_id = log_obj.create({'remarks': remarks,
                                                            'wcs_message': msg,
                                                            'wcs_message_type':wcs_message_type,
                                                            'wcs_message_code': statusCode,
                                                            'wcs_notification_code': responseCode,
                                                            'wcs_timestamp': datetime.today(),
                                                            'wcs_raw_data':data,
                                                            'transport_order' : None,
                                                            'transport_order_number': None,
                                                            'wcs_id': record.wcs_id_2})
                        else: raise exceptions.UserError('Error sending request to WCS, please try again. Status Code:' + str(response.status_code))
                    
                    except Exception as err:
                        raise exceptions.UserError('Error sending request to WCS, please try again. '+ f"Unexpected {err=}, {type(err)=}")
                
                
                #delete for incoming
                picking_type_code = record.move_line_id.picking_type_id.code
                if picking_type_code == 'incoming':
                    self._delete_move_line(record.move_line_id)
                else:
                    self._clear_staging(record.pallet_id)
                    
            else:
                record.write({'wcs_state_1': self.new_state})
                elevated_tray = self.env['shipment_order.elevated.tray'].search(['|',
                                    ('open_side_code','=',record.wcs_dropoff_1),
                                    ('closed_side_code','=',record.wcs_dropoff_1)
                                    ], limit=1)
                if elevated_tray.id != False:
                                elevated_tray.write({'occupied_state' : 'Empty'})
                
                if record.wcs_id_2:  
                    record.write({'wcs_state_2': self.new_state})
                    elevated_tray = self.env['shipment_order.elevated.tray'].search(['|',
                                    ('open_side_code','=',record.wcs_dropoff_2),
                                    ('closed_side_code','=',record.wcs_dropoff_2)
                                    ], limit=1)
                    if elevated_tray.id != False:
                                    elevated_tray.write({'occupied_state' : 'Empty'})
                
                
                
                log_obj = self.env['shipment_order.movelog']
                log_id = log_obj.create({'remarks': 'Transport Order manually changed from '+ old_state_1 +' to '+ self.new_state + '. (Not updated to WCS)' ,
                                                    'wcs_message': '',
                                                    'wcs_message_type':'system',
                                                    'wcs_message_code': '',
                                                    'wcs_notification_code': '',
                                                    'wcs_timestamp': datetime.today(),
                                                    'wcs_raw_data':'',
                                                    'transport_order' : record.id if self.new_state != 'cancelled' else None,
                                                    'transport_order_number': 1 if self.new_state != 'cancelled' else None,
                                                    'wcs_id': record.wcs_id_1})
                
                if self.new_state == 'cancelled':

                    picking_type_code = record.move_line_id.picking_type_id.code
                    if picking_type_code == 'incoming':
                        self._delete_move_line(record.move_line_id)
                    else:
                        self._clear_staging(record.pallet_id)
                            
                else: 
                    self._complete_move_line(record.move_line_id)

        else:
            if self.new_state == 'cancelled':
                picking_type_code = self.move_line_id.picking_type_id.code
                if picking_type_code == 'incoming':
                    self._delete_move_line(self.move_line_id)
                else:
                    self._clear_staging(self.transport_id.pallet_id)
            else:
                self._complete_move_line(self.move_line_id)

class ShipmentScan(models.TransientModel):
    _name = "shipment_order.scan.line"
    _description = "Shipment Scan Line"

    qr_code_data = fields.Char(string="Scan QR Code")
    shipment_type = fields.Char('Shipment Type')
    pickup_location_tag_id = fields.Many2one('generic.tag',compute='_compute_pickup_tag', string="Pickup Tag") 
    pickup_location = fields.Many2one('stock.location',domain="[('generic_tag_ids','in',[pickup_location_tag_id])]", string='Pickup Location', required='True')

    ref_number = fields.Char('Ref No.')
    container_number = fields.Char('Container No.')
    seal_number = fields.Char('Seal No.')
    container_size = fields.Selection(selection=[
        ('20', "20 Ft."),
        ('40', "40 Ft.")
    ], default='20')
    customer = fields.Many2one('res.partner', 'Customer')
    vessel_name = fields.Char(string="Vessel Name")
    voyage_number = fields.Char(string="Voyage No.")
    eta = fields.Date(string="ETA",default=date.today())
    shipment_month = fields.Selection([('1', 'January'), ('2', 'February'), ('3', 'March'), ('4', 'April'),
                            ('5', 'May'), ('6', 'June'), ('7', 'July'), ('8', 'August'), 
                            ('9', 'September'), ('10', 'October'), ('11', 'November'), ('12', 'December')], 
                            string='Shipment Month', default=str(date.today().month))
    shipment_week = fields.Selection([('0','0'),('1','1'),('2','2'),('3','3'),('4','4'),('5','5')], default = str(((date.today().day - 1 + (date.today().weekday() - date.today().day + 1) % 7)//7+1)-1)
                                     )
    pallet_id = fields.Char('Pallet ID')
    length = fields.Integer('Length')
    width = fields.Integer('Width')
    height = fields.Integer('Height')

    is_wcs_order = fields.Boolean('Create WCS Order', default=True)
    
    shipment_scan_id = fields.Many2one('shipment_order.scan',ondelete='cascade')

    @api.depends('pickup_location_tag_id')
    def _compute_pickup_tag(self):
        tag = self.env['generic.tag'].search([('code', '=', 'pickup'),], limit=1)
        if len(tag) == 0:
            raise(ValidationError,'No pickup locations found')
        else: 
            self.pickup_location_tag_id = tag
            return tag

class ShipmentWizard(models.TransientModel):
    _name = "shipment_order.scan"
    _description = "Shipment Wizard"
    _inherit = ['multi.step.wizard.mixin']

    
    WIZARD_PICKING_IDS = []
    WIZARD_MOVE_LINE_IDS = []
    WIZARD_MOVE_LINES = []  
    WIZARD_WCS_ORDER_IDS = []
    WIZARD_CONTAINER_IDS = []

    shipment_type = fields.Selection(selection=[
        ('I', "Incoming"),
        ('O', "Outgoing")
    ], default='I',readonly=True, required=True)
    customer = fields.Char(string="Customer")
    ref_number = fields.Char(string="Ref No.")
    container_number = fields.Char(string="Container No.")
    seal_number = fields.Char(string="Seal No.")
    container_size = fields.Selection(selection=[
        ('20', "20 Ft."),
        ('40', "40 Ft.")
    ], default='20')
    vessel_name = fields.Char(string="Vessel Name")
    voyage_number = fields.Char(string="Voyage No.")
    eta = fields.Date(string="ETA",default=date.today())
    shipment_month = fields.Selection([('1', 'January'), ('2', 'February'), ('3', 'March'), ('4', 'April'),
                            ('5', 'May'), ('6', 'June'), ('7', 'July'), ('8', 'August'), 
                            ('9', 'September'), ('10', 'October'), ('11', 'November'), ('12', 'December')], 
                            string='Shipment Month', default=str(date.today().month))
    shipment_week = fields.Selection([('0','0'),('1','1'),('2','2'),('3','3'),('4','4'),('5','5')], default = str(((date.today().day - 1 + (date.today().weekday() - date.today().day + 1) % 7)//7+1)-1))
    
    length = fields.Integer('Length')
    width = fields.Integer('Width')
    height = fields.Integer('Height')
    pallet_id = fields.Char('Pallet ID')

    qr_code_data = fields.Char(string="Scan QR Code")
    
    pallet_ids = fields.One2many('shipment_order.scan.line', 'shipment_scan_id', string="Pallets")
    move_line_ids = fields.One2many('stock.move.line', compute='_compute_move_lines', inverse='_inverse_move_lines', string="Move Lines")
    wcs_order_ids = fields.One2many('shipment_order.move', compute='_compute_wcs_orders', inverse='_inverse_wcs_orders', string="WCS Orders")

    pickup_location_tag_id = fields.Many2one('generic.tag',compute='_compute_pickup_tag', string="Pickup Tag") 
    pickup_location = fields.Many2one('stock.location',domain="[('generic_tag_ids','in',[pickup_location_tag_id])]", string='Pickup Location')
    
    is_wcs_order = fields.Boolean('Create WCS Order', default=True)
    company_id = fields.Many2one(
        'res.company', 'Company', required=True,
        default=lambda s: s.env.company.id, ondelete='cascade', index=True)
    
    num_pallets = fields.Integer("No. of Pallets Scanned", compute='_compute_scan_lines')
    recompute_wcs_order_ids = fields.Boolean('Recompute WCS Orders', default=True, store=False)

    @api.model
    def _selection_state(self):
        return [
            ('start', 'Scan Pallets'),
            ('review', 'Review Locations'),
            ('final', 'WCS Transport Orders'),
        ]
    
    def state_exit_start(self):
        self.state = "review"
        self.action_process_scanned_lines()
    
    def state_exit_review(self):
        self.state = "final"
        self.action_process_wcs_orders()

    """ def state_previous_review(self):
        self.state = "start"
        self.action_process_wcs_orders()
    
    def state_previous_final(self):
        self.state = "review" """
    
    def action_cancel(self):
        if self.is_first_open:
            self.WIZARD_WCS_ORDER_IDS.clear()
            self.WIZARD_MOVE_LINE_IDS.clear()
            self.WIZARD_MOVE_LINES.clear()
        
        #delete incomplete move lines
        if self.state != "final":
            for move_line in self.move_line_ids:
                move_line.write({'qty_done': 0, 'reserved_uom_qty':0, 'state': 'draft'})
                lot_id = move_line.lot_id
                #delete move line
                move_line.unlink()
                #delete quant
                quants = self.env['stock.quant'].search([
                                            ('lot_id','=', lot_id.id)
                                        ])
                for quant in quants:
                    quant.unlink()
                #delete lot
                lot_id.unlink()

        return {'type': 'ir.actions.act_window_close'}
    
    def action_close(self):
        if self.is_first_open:
            self.WIZARD_WCS_ORDER_IDS.clear()
            self.WIZARD_MOVE_LINE_IDS.clear()
            self.WIZARD_MOVE_LINES.clear()

        return {'type': 'ir.actions.act_window_close'}
        
    def _inverse_move_lines(self):
        return
    
    def _inverse_wcs_orders(self):
        return
    
    @api.depends('pickup_location_tag_id')
    def _compute_pickup_tag(self):
        tag = self.env['generic.tag'].search([('code', '=', 'pickup'),], limit=1)
        if len(tag) == 0:
            raise(ValidationError,'No pickup locations found')
        else: 
            self.pickup_location_tag_id = tag
            return tag
    
    @api.depends('recompute_wcs_order_ids')
    def _compute_wcs_orders(self):
        self.wcs_order_ids = self.env['shipment_order.move'].search([
                                ('id', 'in', self.WIZARD_WCS_ORDER_IDS),
                                ])
        
    def _compute_move_lines(self):
        if self.is_first_open == True:
            self.WIZARD_WCS_ORDER_IDS.clear()
            self.WIZARD_MOVE_LINE_IDS.clear()
            self.WIZARD_MOVE_LINES.clear()
            self.write({'is_first_open': False})
        self.move_line_ids = self.env['stock.move.line'].search([
                                ('id', 'in', self.WIZARD_MOVE_LINE_IDS),
                                ])
    
    @api.depends('pallet_ids')
    def _compute_scan_lines(self):
        self.num_pallets = len(self.pallet_ids)

    @api.model
    def default_get(self, fields):
        
        result = super(ShipmentWizard, self).default_get(fields)
        seq = self.env.context.get('barcode')
        if(seq == "WH-RECEIPTS"):       
            result.update({'shipment_type': 'I'})
        elif(seq == "WH-DELIVERY"):       
            result.update({'shipment_type': 'O'})
        tag = self._compute_pickup_tag()
        if tag: result.update({'pickup_location_tag_id': tag})
        result.update({'name': 'Scan Pallet'})
        return result
    
    @api.onchange('qr_code_data')
    def onchange_qr_code_data(self):
        pallet_max_height = int(self.env['ir.config_parameter'].sudo().get_param('shipment_order.shipment_pallet_max_height'))
        short_pallet_max_height = int(self.env['ir.config_parameter'].sudo().get_param('shipment_order.shipment_short_pallet_max_height'))
        short_dummy_pallet_height = int(self.env['ir.config_parameter'].sudo().get_param('shipment_order.short_dummy_pallet_height'))
        tall_dummy_pallet_height = int(self.env['ir.config_parameter'].sudo().get_param('shipment_order.tall_dummy_pallet_height'))

        if self.qr_code_data:
            if len(self.pallet_ids) == 2:
                raise exceptions.ValidationError("A maximum of 2 pallets can be scanned")
            if(self.pickup_location == False):
                raise exceptions.ValidationError("Please select a pickup location")
            try:
                root = ET.fromstring("<DATA>" + self.qr_code_data + "</DATA>")
            
                qr_pallet_id = root.findtext('ID')
                qr_bkg_id = root.findtext('BL')
                if root.findtext('BL') == None:
                    qr_bkg_id = root.findtext('BK')
                qr_customer = root.findtext('CUST')
                qr_container = root.findtext('DCTR')
                qr_seal = root.findtext('SEAL')
                qr_size = root.findtext('SZ')
                qr_vessel = root.findtext('VSL')
                qr_voyage = root.findtext('VOY')
                if root.findtext('ETA'):
                    qr_eta = datetime.strptime(root.findtext('ETA'), '%d/%m/%y') 

                monthDict = {'JAN':'1', 'FEB':'2', 'MAR': '3', 'APR':'4', 'MAY':'5', 'JUN':'6','JUL':'7','AUG':'8','SEP':'9','OCT':'10','NOV':'11','DEC':'12'}
                qr_shipment = root.findtext('WK').upper()
                shipment_arr = qr_shipment.split()
                qr_shipment_mth = monthDict[shipment_arr[0]]
                qr_shipment_wk = shipment_arr[2]
                qr_length = root.findtext('LH')
                qr_width = root.findtext('WH')
                qr_height = root.findtext('HT')
                qr_ref_id = qr_bkg_id + "_" + qr_container
            except:
                raise exceptions.ValidationError("Incorrect QR Code format")

            
            if int(qr_height) <= short_pallet_max_height:
                qr_height = int(qr_height) + short_dummy_pallet_height
            else: qr_height = int(qr_height) + tall_dummy_pallet_height

            #Check max height if sending to AGV
            if (int(qr_height) > pallet_max_height and self.is_wcs_order == True) == True:
                raise exceptions.ValidationError("Current pallet height (" + str(qr_height) + ") exceeds pallet max height: " + str(pallet_max_height) )
            

            existing_pallet = [x for x in self.pallet_ids if x["pallet_id"] == qr_pallet_id]
            if existing_pallet:
                raise exceptions.ValidationError("Pallet ID " + qr_pallet_id + " has already been added")
            else:
                # Pallet ID should not be repeated at all
                # Move with WCS order
                existing_pallet = self.env['shipment_order.pallet'].search([
                                ('name', '=', qr_pallet_id),
                                #('container_id.ref_number', '=', qr_ref_id),
                                ('company_id', '=', self.company_id.id),#'|',
                                #('move_line_id.transport_order_id.wcs_state_1', 'not in', ('cancelled','error',False)),
                                #('move_line_id.transport_order_id.wcs_state_2', 'not in', ('cancelled','error',False))
                                ], limit=1)
                if existing_pallet.id:
                    raise exceptions.ValidationError("Pallet ID " + qr_pallet_id + " has already been added in Bkg No.: " + existing_pallet.container_id.ref_number)
                
                # Move with no WCS order
                existing_pallet = self.env['shipment_order.pallet'].search([
                                ('name', '=', qr_pallet_id),
                                #('container_id.ref_number', '=', qr_ref_id),
                                ('company_id', '=', self.company_id.id),
                                ('move_line_id.transport_order_id.wcs_id_1', '=', None),
                                ], limit=1)
                if existing_pallet.id:
                    raise exceptions.ValidationError("Pallet ID " + qr_pallet_id + " has already been added in Bkg No.: " + existing_pallet.container_id.ref_number + "(No WCS order)")

            existing_partner = self.env['res.partner'].search([
                                ('name', '=', qr_customer),
                                ], limit=1)
            print(str(existing_partner.id))
            if existing_partner.id == False:
                raise exceptions.ValidationError("Customer " + qr_customer + " does not exist, please create the customer first")

            #Should not have same customer, week, month, container for 2 different booking numbers
            existing_picking = self.env['stock.picking'].search([
                                    ('ref_number', '!=', qr_ref_id),
                                    ('ref_number', '!=', qr_bkg_id),
                                    ('picking_type_id', '=', 1),
                                    ('shipment_month', '=', qr_shipment_mth),
                                    ('shipment_week', '=', qr_shipment_wk),
                                    ('partner_id', '=', existing_partner.id),
                                    ], limit=1)
            if existing_picking.id:
                raise exceptions.ValidationError("Booking " + existing_picking.ref_number + " already exists for " + qr_customer + ", " + shipment_arr[0] + " WK " + qr_shipment_wk + ", Container: " + qr_container)

            self.ref_number = qr_ref_id
            self.seal_number = qr_seal
            self.container_number = qr_container
            self.customer = qr_customer
            self.container_size = qr_size
            self.vessel_name = qr_vessel
            self.voyage_number = qr_voyage
            self.eta = qr_eta
            self.shipment_month = qr_shipment_mth
            self.shipment_week = qr_shipment_wk
            self.length = qr_length
            self.width = qr_width
            self.height = qr_height
            self.pallet_id = qr_pallet_id
            
            self.env['shipment_order.scan.line'].create({
                                                         'ref_number': qr_ref_id,
                                                         'container_number': qr_container,
                                                         'seal_number': qr_seal,
                                                         'container_size': qr_size,
                                                         'customer': existing_partner.id,
                                                         'vessel_name': qr_vessel,
                                                         'voyage_number': qr_voyage,
                                                         'eta': qr_eta,
                                                         'shipment_month': qr_shipment_mth,
                                                         'shipment_week': qr_shipment_wk,
                                                         'pallet_id' : qr_pallet_id,
                                                         'length' : qr_length,
                                                         'width' : qr_width,
                                                         'height' : qr_height,
                                                         'qr_code_data': self.qr_code_data,
                                                         'pickup_location': self.pickup_location.id,
                                                         'shipment_type' : self.shipment_type,
                                                         'is_wcs_order': self.is_wcs_order,
                                                         'shipment_scan_id': self.id})    
    
    def action_process_scanned_lines(self):
        pallet_list = []
        for pallet in self.pallet_ids:
            pallet_list.append(pallet)
        pallet_list.sort(key=lambda x: x.height)
        for pallet in pallet_list:
            #CREATE/RETRIEVE PICKING
            picking_obj = self.env['stock.picking']
            existing_picking = picking_obj.search([
                                    ('ref_number', '=', pallet.ref_number),
                                    ('picking_type_id', '=', 1)
                                    ], limit=1)
            if existing_picking.id == False:
                default_locations = self._get_default_locations(pallet.customer)
                existing_picking = picking_obj.create({
                                    'picking_type_id': 1 if self.shipment_type == 'I' else 2,
                                    'partner_id': pallet.customer.id,
                                    'location_id':default_locations['location_id'],
                                    'location_dest_id':default_locations['location_dest_id'],
                                    'ref_number': pallet.ref_number,
                                    'vessel_name': pallet.vessel_name,
                                    'voyage_number': pallet.voyage_number,
                                    'eta': pallet.eta,
                                    'shipment_month': pallet.shipment_month,
                                    'shipment_week': pallet.shipment_week,
                                    'scheduled_date': pallet.eta,
                                    'state': 'assigned'
                                    })
            self.WIZARD_PICKING_IDS.append(existing_picking.id)
            print("PICKING:" + str(existing_picking))

            #CREATE/RETRIEVE CONTAINER
            container_obj = self.env['shipment_order.container']
            existing_new_container = [x for x in existing_picking.container_ids if x["container_number"] == pallet.container_number]
            is_newly_created_container = False
            if not existing_new_container:
                existing_container = container_obj.search([
                                    ('container_number', '=', pallet.container_number),
                                    ('picking_id', '=', existing_picking.id),
                                    ], limit=1)
            else: existing_container = existing_new_container[0]
             
            if existing_container.id == False:
                is_newly_created_container = True
                existing_container = container_obj.create({'container_number':pallet.container_number,
                                                    'ref_number': pallet.ref_number,
                                                    'seal_number':pallet.seal_number,
                                                    'container_size': pallet.container_size,
                                                    'picking_id': existing_picking.id})
            else: 
                if len(existing_container.pallet_ids) == 0: is_newly_created_container = True
            
            print("CONTAINER:" + str(existing_container))

            #CREATE PALLET
            pallet_obj = self.env['shipment_order.pallet']
            existing_pallet = pallet_obj.search([
                                    ('container_number', '=', pallet.container_number),
                                    ('name', '=', pallet.pallet_id),
                                    ], limit=1)
            if existing_pallet.id:
                pallet_id = existing_pallet
                pallet_id.write({'qr_code_data':pallet.qr_code_data,
                                    'name': pallet.pallet_id,
                                    'cargo_length':pallet.length,
                                    'cargo_width': pallet.width,
                                    'cargo_height': pallet.height})
                print("Existing Pallet: " + str(pallet_id))
            else:
                pallet_id = pallet_obj.create({'qr_code_data':pallet.qr_code_data,
                                                'name': pallet.pallet_id,
                                                'cargo_length':pallet.length,
                                                'cargo_width': pallet.width,
                                                'cargo_height': pallet.height,
                                                'container_id' : existing_container.id})
            
                print("Pallet created: " + str(pallet_id))
            
            #CREATE MOVE LINE
            #return {'move_line': new_move_line, 'top_rack': True if 'TALL_PALLET' in product_obj.product_code else False}
            move_line = self._create_move_line(pallet_id, existing_picking, is_newly_created_container, existing_container, pallet.is_wcs_order, pallet.pickup_location)

            _logger.warning("[shipment_wizard.action_process_scanned_lines] MOVE LINE CREATED FOR PICKING " + str(existing_picking.name)  + ", ID: " + str(move_line.id) + ", DEST: " + move_line.location_dest_id.name)
            print("MOVE LINE: " + str(move_line.id))
        for move_line in self.move_line_ids:
            move_line.set_exclusions(self.move_line_ids.ids)

    def _change_move_line_product(self, move_line):
        move_line_rack = move_line.location_dest_id.rack_tag_id.code
        product_rack = move_line.product_id.product_tmpl_id.categ_id.name
        original_product = move_line.product_id.name
        if move_line_rack != product_rack:
            product_code = move_line_rack + '_' + ('TALL_PALLET' if 'TALL_PALLET' in move_line.product_id.code  else 'SHORT_PALLET')
            product_obj = self.env['product.product'].search([
                                ('default_code', '=', product_code),
                                ], limit=1)
            if not product_obj.id:
                raise exceptions.ValidationError("Cannot find product with code: " + product_code)
            move_line.write({'state': 'draft'})
            lot_pallet_name =  str(move_line.lot_id.name),
            lot_ref = move_line.lot_id.ref
            
            #delete quant
            quants = self.env['stock.quant'].search([
                                        ('lot_id','=', move_line.lot_id.id)
                                    ])
            for quant in quants:
                quant.unlink()
            move_line.lot_id.unlink()
            new_lot = self.env['stock.lot'].create({'name':lot_pallet_name[0],
                                        'company_id': self.company_id.id,
                                        'product_id': product_obj.id,
                                        'product_qty': 1,
                                        'ref':lot_ref})
            move_line.write({'product_id': product_obj.id, 'lot_id' : new_lot})
            move_line.write({'state': 'assigned'})
            
    def action_process_wcs_orders(self):

        #if destination location was manually changed, change product obj
        first_move_line = self.move_line_ids[0]
        first_move_line.set_exclusions(self.move_line_ids.ids)
        move_line_rack = first_move_line.location_dest_id.rack_tag_id.code
        product_rack = first_move_line.product_id.product_tmpl_id.categ_id.name
        if move_line_rack != product_rack:
            self._change_move_line_product(first_move_line)

            
        #only 1 pallet in bottom rack, send straight to rack
        dest_slot = first_move_line.location_dest_id.slot_tag_id
        top_slot_category = self.env['generic.tag.category'].search([
                    ('code','=', 'top_slot')
                ])
        if dest_slot.category_id.id in top_slot_category.ids:
            is_top_rack = 1
        else: is_top_rack = 0
        if len(self.move_line_ids) == 1 and is_top_rack == 0:
            move_line = self.move_line_ids[0]
            pallet = move_line.pallet_ids[0]
            pickup_location_name = move_line.inbound_from.name
            move_line.write({'reserved_uom_qty':1})
            
            if move_line.is_wcs_order:
                #check if pickup from elevated tray, change to elevated tray closed side code
                pickup_elevated_tray = self.env['shipment_order.elevated.tray'].search([('name','=','move_line.inbound_from.name')], limit=1)
                if pickup_elevated_tray.id:
                    pickup_location_name = pickup_elevated_tray.closed_side_code

                wcs_order = self.env['shipment_order.move'].create({'location_id': move_line.inbound_from.id,
                                                        'location_dest_id': move_line.location_dest_id.id,
                                                        'wcs_state_1': 'pending',
                                                        'wcs_pickup_1': pickup_location_name,
                                                        'wcs_dropoff_1':  move_line.location_dest_id.name,
                                                        'wcs_timestamp': datetime.today(),
                                                        'pallet_id': pallet.id,
                                                        'picking_id': move_line.picking_id.id,
                                                        'move_line_id': move_line.id,
                                                        'qr_code': pallet.qr_code_data})
                self._send_wcs_order(move_line.inbound_from.name, move_line.location_dest_id.name,move_line.pallet_ids.name,
                                    wcs_order,1,False)
                self.WIZARD_WCS_ORDER_IDS.append(wcs_order.id)
                print("WCS ORDER: " + str(wcs_order))
            else:
                move_line.write({'qty_done':1,'reserved_uom_qty':0})
                if move_line.state != 'done':
                    move_line._action_done()
                    move_line.write({'state':'confirmed'})

            _logger.warning("[shipment_wizard.action_process_wcs_orders] 761 MOVE LINE PROCESSED FOR PICKING " + str(move_line.picking_id.name)  + ", ID: " + str(move_line.id) + ", DEST: " + move_line.location_dest_id.name)
        
        else:
            transport_order_list = []
            move_line_list = []
            order_sequence = 1
            for move_line in self.move_line_ids:
                move_line.set_exclusions(self.move_line_ids.ids)
                move_line_list.append(move_line)
            #process in order of scanning
            move_line_list.sort(key=lambda x: (x['id']))

            for move_line in move_line_list:
                #if destination location was manually changed, change product obj
                move_line_rack = move_line.location_dest_id.rack_tag_id.code
                product_rack = move_line.product_id.product_tmpl_id.categ_id.name
                if move_line_rack != product_rack:
                    self._change_move_line_product(move_line)
                
                pallet = move_line.pallet_ids
                if move_line.is_wcs_order:

                    pickup_location_name = move_line.inbound_from.name
                    pickup_elevated_tray = self.env['shipment_order.elevated.tray'].search([('name','=',move_line.inbound_from.name)], limit=1)
                    dest_slot = move_line.location_dest_id.slot_tag_id
                    top_slot_category = self.env['generic.tag.category'].search([
                                ('code','=', 'top_slot')
                            ])
                    if dest_slot.category_id.id in top_slot_category.ids:
                        is_top_rack = 1
                    else: is_top_rack = 0
                    
                    #Send from elevated tray to rack
                    if pickup_elevated_tray.id:
                        if is_top_rack == 0:
                            #send from elevated tray open side to rack
                            pickup_location_name = pickup_elevated_tray.open_side_code
                        else: pickup_location_name = pickup_elevated_tray.closed_side_code

                        wcs_order = self.env['shipment_order.move'].create({'location_id': move_line.inbound_from.id,
                                                            'location_dest_id': move_line.location_dest_id.id,
                                                            'wcs_state_1': 'pending',
                                                            'wcs_pickup_1': pickup_location_name,
                                                            'wcs_dropoff_1': move_line.location_dest_id.name,
                                                            'wcs_timestamp': datetime.today(),
                                                            'pallet_id': pallet.id,
                                                            'picking_id': move_line.picking_id.id,
                                                            'move_line_id': move_line.id,
                                                            'qr_code': pallet.qr_code_data})
                        transport_order_list.append({
                                'pickup': pickup_location_name,
                                'dropoff':move_line.location_dest_id.name,
                                'pallet_name': pallet.name,
                                'wcs_order':wcs_order,
                                'sequence': 1,
                                'is_elevated_tray': False,
                                'is_top_rack': is_top_rack,
                                'order_sequence' : order_sequence
                            })
                        order_sequence += 1
                        
                        self.WIZARD_WCS_ORDER_IDS.append(wcs_order.id)
                        print("WCS ORDER: " + str(wcs_order))
                        
                    #Send from lift to rack
                    else:
                        #1. For all racks: send to elevated tray open side
                        #2. For bottom rack: send from elevated tray closed side to rack
                        #   For top rack: send from elevated tray open side to rack
                    
                        #Just get 1st tray based on earliest last updated date
                        elevated_tray = self.env['shipment_order.elevated.tray'].search([],order='pallet_date, priority', limit=1)
                        if elevated_tray.id == False:
                            raise exceptions.ValidationError("No available elevated tray for pallet " + pallet.name)
                        else:
                            wcs_order = self.env['shipment_order.move'].create({'location_id': move_line.inbound_from.id,
                                                            'location_dest_id': move_line.location_dest_id.id,
                                                            'wcs_state_1': 'pending',
                                                            'wcs_pickup_1': move_line.inbound_from.name,
                                                            'wcs_dropoff_1': elevated_tray.open_side_code,
                                                            'wcs_timestamp': datetime.today(),
                                                            'pallet_id': pallet.id,
                                                            'picking_id': move_line.picking_id.id,
                                                            'move_line_id': move_line.id,
                                                            'qr_code': pallet.qr_code_data})
                            elevated_tray.write({'occupied_state': 'Reserved',
                                                'pallet_date': datetime.today()})
                            #send to elevated tray open side
                            transport_order_list.append({
                                'pickup':move_line.inbound_from.name,
                                'dropoff':elevated_tray.open_side_code,
                                'pallet_name': pallet.name,
                                'wcs_order':wcs_order,
                                'sequence': 1,
                                'is_elevated_tray': True,
                                'is_top_rack': is_top_rack,
                                'order_sequence' : order_sequence
                            })
                            order_sequence += 1
                            
                            #send from elevated tray open/closed side to rack
                            wcs_order.write({'wcs_state_2': 'pending',
                                            'wcs_pickup_2': (elevated_tray.open_side_code if is_top_rack == 0 else elevated_tray.closed_side_code),
                                            'wcs_dropoff_2': move_line.location_dest_id.name})
                            
                            transport_order_list.append({
                                'pickup':(elevated_tray.open_side_code if is_top_rack == 0 else elevated_tray.closed_side_code),
                                'dropoff':move_line.location_dest_id.name,
                                'pallet_name': pallet.name,
                                'wcs_order':wcs_order,
                                'sequence': 2,
                                'is_elevated_tray': False,
                                'is_top_rack': is_top_rack,
                                'rack_sequence': move_line.location_dest_id.rack_tag_id.sequence,
                                'slot_sequence': move_line.location_dest_id.slot_tag_id.sequence,
                                'order_sequence' : order_sequence
                            })
                            order_sequence += 1
                        
                        self.WIZARD_WCS_ORDER_IDS.append(wcs_order.id)
                        print("WCS ORDER: " + str(wcs_order))
                else:
                    move_line.write({'qty_done':1,'reserved_uom_qty':0})
                    if move_line.state != 'done':
                        move_line._action_done()
                        move_line.write({'state':'confirmed'})
                
                _logger.warning("[shipment_wizard.action_process_wcs_orders] 888 MOVE LINE PROCESSED FOR PICKING " + str(move_line.picking_id.name)  + ", ID: " + str(move_line.id) + ", DEST: " + move_line.location_dest_id.name)
        
            
            #send orders with destination as elevated tray first to avoid holding up the lift
            elevated_tray_orders = [x for x in transport_order_list if x['is_elevated_tray'] == True]
            if elevated_tray_orders:
                elevated_tray_orders.sort(key=lambda x: (x['order_sequence']))

            non_elevated_tray_orders = [x for x in transport_order_list if x['is_elevated_tray'] == False]
            if non_elevated_tray_orders:
                #place top rack pallets first
                non_elevated_tray_orders = sorted(non_elevated_tray_orders, key = operator.itemgetter('is_top_rack'), reverse=True)
                non_elevated_tray_orders = sorted(non_elevated_tray_orders, key = operator.itemgetter('rack_sequence','slot_sequence'))

            for to in elevated_tray_orders:
                self._send_wcs_order(to['pickup'], to['dropoff'],to['pallet_name'], to['wcs_order'],to['sequence'],to['is_elevated_tray'])
            for to in non_elevated_tray_orders:
                self._send_wcs_order(to['pickup'], to['dropoff'],to['pallet_name'], to['wcs_order'],to['sequence'],to['is_elevated_tray'])

           
        self.recompute_wcs_order_ids = not(self.recompute_wcs_order_ids)
        for move_line in self.move_line_ids:
            move_line.write({'move_line_exclusions':''})

    def _send_wcs_order(self, pickup_name, delivery_name, payload, wcs_order, sequence_no, is_elevated_tray):
        wms_interface_url = self.env['ir.config_parameter'].sudo().get_param('shipment_order.wms_interface_url')
        wcs_system_name = self.env['ir.config_parameter'].sudo().get_param('shipment_order.wcs_system_name')
        wcs_subsystem_id = int(self.env['ir.config_parameter'].sudo().get_param('shipment_order.wcs_subsystem_id'))
        validate_elevated_tray_qr = bool(self.env['ir.config_parameter'].sudo().get_param('shipment_order.validate_elevated_tray_qr'))
        validate_qr = bool(self.env['ir.config_parameter'].sudo().get_param('shipment_order.validate_qr'))

        data = {
            "system": wcs_system_name,
            "subsystem_id": wcs_subsystem_id,
            "priority": 5,
            "pickup": pickup_name,
            "delivery": delivery_name,
            "scan": validate_elevated_tray_qr if is_elevated_tray else validate_qr, #indicate if WCS should scan the pallet qr code when picking up the pallet
            "payload": payload
        }
        try:
            response = requests.post(wms_interface_url + '/CreateTransportOrder', json=data)
            if response.ok:
                try:
                    response_json = response.json()
                except JSONDecodeError:
                    raise ValidationError('Response could not be serialized: ' + response.text)
                result = bool(response_json['result'])
                msg = response_json['msg']
                statusCode = response_json['statusCode']
                responseCode = response_json['code']
                data = response_json['data']

                
                if sequence_no == 1:
                    state_field_name = 'wcs_state_1'
                    id_field_name = 'wcs_id_1'
                else:
                    state_field_name = 'wcs_state_2'
                    id_field_name = 'wcs_id_2'
                if result:
                    wcs_order_id = int(msg)
                    wcs_order.write({id_field_name: wcs_order_id,
                                    state_field_name: 'created'})
                    remarks = 'Transport Order Created. ID: ' + msg
                    wcs_message_type = 'system'
                    msg = ''
                else:
                    #wcs_order.write({state_field_name: 'error'})
                    remarks = 'Error creating transport order. ' + msg
                    wcs_message_type = 'system'
                    raise exceptions.UserError(remarks)
                
                log_obj = self.env['shipment_order.movelog']
                log_id = log_obj.create({'remarks': remarks,
                                                'wcs_message': msg,
                                                'wcs_message_type':wcs_message_type,
                                                'wcs_message_code': statusCode,
                                                'wcs_notification_code': responseCode,
                                                'wcs_timestamp': datetime.today(),
                                                'wcs_raw_data':data,
                                                'transport_order' : wcs_order.id,
                                                'transport_order_number':sequence_no})
                self._compute_wcs_orders()
            else: raise exceptions.UserError('Error sending request to WCS, please try again. Status Code:' + str(response.status_code))
        except Exception as err:
            raise exceptions.UserError('Error sending request to WCS, please try again. '+ f"Unexpected {err=}, {type(err)=}")
        



    def _get_product(self, pallet_id, is_newly_created_container, container_id):
        max_height = int(self.env['ir.config_parameter'].sudo().get_param('shipment_order.shipment_short_pallet_max_height'))
        is_tall_pallet = False
        if(pallet_id.cargo_height > max_height):
            is_tall_pallet = True

        rack_tag_category = self.env['generic.tag.category'].search([
                                ('code', '=', 'rack'),
                                ], limit=1)
        
        if not rack_tag_category.id:
            raise exceptions.ValidationError("No location tag with category 'rack' has been created")
        
        stock_quant_list = self.env['stock.quant'].search([
                            ('quantity', '>', 0),
                            ])
        
        move_line_list = self.env['stock.move.line'].search([
                            ('reserved_qty', '>', 0),
                            ('state', 'in', ('assigned','draft')),
                            ])
        
        #container exists, use existing rack based on last added pallet
        if container_id.id and not is_newly_created_container:
            pallet_obj = self.env['shipment_order.pallet'].search([
                                ('container_id', '=', container_id.id),
                                ('id', '!=', pallet_id.id)
                                ], limit=1, order="id desc") 
            move_line_obj = self.env['stock.move.line'].browse(pallet_obj.move_line_id.id)

            #check if rack is full, no locations under this rack tag category with 0 stock
            location_dest = move_line_obj.location_dest_id
            rack_tag = location_dest.generic_tag_ids.filtered(lambda x: x.category_id.id == rack_tag_category.id)
            #total number of locations in this rack
            total_locations_count = rack_tag.objects_count
            #find all locations in this rack that are occupied
            locations_with_qty = []
            for quant in stock_quant_list:
                location_rack_tag = quant.location_id.generic_tag_ids.filtered(lambda x: x.id == rack_tag.id)
                if len(location_rack_tag) > 0:
                    if quant.location_id.id not in locations_with_qty:
                        locations_with_qty.append(quant.location_id.id)
            #add on locations for movements that are not yet completed
            for move_line in move_line_list:
                tags = move_line.location_dest_id.generic_tag_ids
                location_rack_tag = tags.filtered(lambda x: x.id == rack_tag.id)
                if len(location_rack_tag) > 0:
                    if move_line.location_dest_id.id not in locations_with_qty:
                        locations_with_qty.append(move_line.location_dest_id.id)
            
            if len(locations_with_qty) < total_locations_count:
                #there are still available locations in this rack
                product_code = move_line_obj.product_id.product_tmpl_id.categ_id.name + '_' + ('TALL_PALLET' if is_tall_pallet else 'SHORT_PALLET')
                product_obj = self.env['product.product'].search([
                                    ('default_code', '=', product_code),
                                    ], limit=1)
                if not product_obj.id:
                    raise exceptions.ValidationError("Cannot find product with code: " + product_code)
                return product_obj
        
        #find new lane for container
        #find locations with stock
        rack_tags_with_qty = []
        for quant in stock_quant_list:
            location_rack_tag = quant.location_id.generic_tag_ids.filtered(lambda x: x.category_id.id == rack_tag_category.id)
            if len(location_rack_tag) > 0:
                if location_rack_tag[0].id not in rack_tags_with_qty:
                    rack_tags_with_qty.append(location_rack_tag.id)

        #find all stock in pending move lines
        for move_line in move_line_list:
            tags = move_line.location_dest_id.generic_tag_ids
            location_rack_tag = tags.filtered(lambda x: x.category_id.id == rack_tag_category.id)
            if len(location_rack_tag) > 0:
                if location_rack_tag[0].id not in rack_tags_with_qty:
                    rack_tags_with_qty.append(location_rack_tag.id) #now we have a complete list of all racks that are occupied
        
        #Find locations tagged with category = 'rack' and not having any stock 
        next_available_rack_tag = self.env['generic.tag'].search([
                            ('category_id', '=', rack_tag_category.id),
                            ('id', 'not in', rack_tags_with_qty),
                            ], order="sequence", limit=1)
        
        if not next_available_rack_tag.id:
            raise exceptions.ValidationError("No available racks, all racks are occupied")
        product_code = next_available_rack_tag.code + '_' + ('TALL_PALLET' if is_tall_pallet else 'SHORT_PALLET')
        product_obj = self.env['product.product'].search([
                            ('default_code', '=', product_code),
                            ], limit=1)
        
        if not product_obj.id:
            raise exceptions.ValidationError("Cannot find product with code: " + product_code)
        return product_obj
            
    def _create_move_line(self, pallet_id, picking_id, is_newly_created_container, container_id, is_wcs_order, pickup_location):
        
        
        product_obj = self._get_product(pallet_id, is_newly_created_container, container_id)

        lot_obj = self.env['stock.lot']

        location = picking_id.location_dest_id._get_putaway_strategy(product_obj, quantity=1)
            
        print(",".join([str(pallet_id),str(product_obj.id),str(self.company_id.id)]))
        new_lot = self.env['stock.lot'].search([
                    ('name', '=', pallet_id.name),
                    ('product_id', '=', product_obj.id),
                    ('company_id', '=', self.company_id.id),
                    ], limit=1)
        
        print("new_lot: " + str(new_lot.id) + ", " + str(new_lot))
        if not new_lot.id :
            new_lot = lot_obj.create({'name':pallet_id.name,
                                        'company_id': self.company_id.id,
                                        'product_id': product_obj.id,
                                        'product_qty': 1,
                                        'ref':picking_id.ref_number})
        move_line_obj = self.env['stock.move.line']

        new_move_line = move_line_obj.create({'picking_id': picking_id.id,
                                    'company_id': self.company_id.id,
                                    'product_id': product_obj.id,
                                    'product_uom_id': product_obj.uom_id.id,
                                    'location_id': picking_id.location_id.id,
                                    'location_dest_id': location.id,
                                    'lot_id': new_lot.id,
                                    'lot_name':pallet_id.name,
                                    'reference': picking_id.name,
                                    'reserved_uom_qty': 1,
                                    'qty_done': 0,
                                    'is_wcs_order': is_wcs_order,
                                    'pallet_id': pallet_id.id,
                                    'inbound_from': pickup_location.id,
                                    'state': 'assigned'})
        pallet_id.write({'move_line_id':new_move_line.id})

        if new_move_line.id:
            new_move_line.move_id.write({'date':picking_id.eta})
            self.WIZARD_MOVE_LINE_IDS.append(new_move_line._origin.id)
            self.WIZARD_MOVE_LINES.append(new_move_line)
        
        
        if picking_id.state == 'draft':
            picking_id.write({'state':'assigned'})

        return new_move_line
                    

    def _get_default_locations(self, partner):

        picking_type_id = 1 
        picking_type = self.env['stock.picking.type'].browse(picking_type_id)
        if picking_type.default_location_src_id:
            location_id = picking_type.default_location_src_id.id
        elif partner:
            location_id = partner.property_stock_supplier.id
        else:
            _customerloc, location_id = self.env['stock.warehouse']._get_partner_locations()

        if picking_type.default_location_dest_id:
            location_dest_id = picking_type.default_location_dest_id.id
        elif partner:
            location_dest_id = partner.property_stock_customer.id
        else:
            location_dest_id, _supplierloc = self.env['stock.warehouse']._get_partner_locations()

        result = {'location_id': location_id, 'location_dest_id': location_dest_id}
        return result