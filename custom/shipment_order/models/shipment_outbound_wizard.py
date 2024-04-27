from odoo import models, fields, api, exceptions, _
from datetime import date, datetime
import xml.etree.ElementTree as ET
import requests, json
from odoo.exceptions import ValidationError
from json import JSONDecodeError


class ShipmentOutScan(models.TransientModel):
    _name = "shipment_order.scan.line.out"
    _description = "Shipment Outbound Scan Line"

    length = fields.Integer('Length')
    width = fields.Integer('Width')
    height = fields.Integer('Height')
    pallet_id = fields.Char('Pallet ID')

    is_wcs_order = fields.Boolean('Create WCS Order', default=True)

    shipment_out_id = fields.Many2one('shipment_order.scan.out',ondelete='cascade')
    
    pickup_location = fields.Many2one('stock.location', string='Pickup Location', required='True')
    pickup_is_bottom_rack = fields.Boolean('Is Bottom Rack')
    pickup_slot_tag_sequence = fields.Integer('Slot Tag Sequence')
    pickup_rack_tag_sequence = fields.Integer('Rack Tag Sequence')
    drop_off_location = fields.Many2one('stock.location', string='Drop Off Location')
    transport_order_sequence = fields.Integer(string='Transport Order Sequence', help='WCS Transport Order Processing Sequence')
    
    process_order = fields.Boolean('Process Order', default=True)

    
class ShipmentOutboundWizard(models.TransientModel):
    _name = "shipment_order.scan.out"
    _description = "Shipment Outbound Wizard"
    _inherit = ['multi.step.wizard.mixin']

    WIZARD_PICKING_IDS = []
    WIZARD_MOVE_LINE_IDS = []
    WIZARD_MOVE_LINES = []  
    WIZARD_WCS_ORDER_IDS = []
    WIZARD_CONTAINER_IDS = []

    
    customer = fields.Many2one('res.partner',string='Customer',domain="[('is_company', '=', True)]")
    shipment_month = fields.Selection([('1', 'January'), ('2', 'February'), ('3', 'March'), ('4', 'April'),
                            ('5', 'May'), ('6', 'June'), ('7', 'July'), ('8', 'August'), 
                            ('9', 'September'), ('10', 'October'), ('11', 'November'), ('12', 'December')], 
                            string='Shipment Month', default=str(date.today().month))
    
    shipment_week = fields.Selection([('0','0'),('1','1'),('2','2'),('3','3'),('4','4'),('5','5')], default = str(((date.today().day - 1 + (date.today().weekday() - date.today().day + 1) % 7)//7+1)-1))
    container_id = fields.Many2one('shipment_order.container',string='Container')


    ref_number = fields.Char(string="Booking/BL No.") 
    vessel_name = fields.Char(string="Vessel Name")
    voyage_number = fields.Char(string="Voyage No.")
    eta = fields.Date(string="ETA",default=date.today())
    
    container_number_actual = fields.Char(string='Actual Container', related='container_id.container_number_actual')
    pallet_ids = fields.One2many('shipment_order.scan.line.out', 'shipment_out_id', string="Pallets")
    wcs_order_ids = fields.One2many('shipment_order.move', compute='_compute_wcs_orders', inverse='_inverse_wcs_orders', string="WCS Orders")
    move_line_ids = fields.One2many('stock.move.line', compute='_compute_move_lines', inverse='_inverse_move_lines', string="Move Lines")
    recompute_wcs_order_ids = fields.Boolean('Recompute WCS Orders', default=True, store=False)
    is_wcs_order = fields.Boolean('Create WCS Order', default=True)

    company_id = fields.Many2one(
        'res.company', 'Company', required=True,
        default=lambda s: s.env.company.id, ondelete='cascade', index=True)
    
    def default_get(self, fields):
        self._populate_staging()
        result = super(ShipmentOutboundWizard, self).default_get(fields)  
        if 'state' in result:
            if result['state'] == "start":
                self.WIZARD_WCS_ORDER_IDS.clear()
                self.WIZARD_MOVE_LINE_IDS.clear()
                self.WIZARD_MOVE_LINES.clear()
        return result   


    @api.model
    def _selection_state(self):
        return [
            ('start', 'Search for Pallets'),
            ('final', 'WCS Transport Orders'),
        ]
    
    def state_exit_start(self):
        if(self.customer == False):
                raise exceptions.ValidationError("Please select a customer")
        if(self.shipment_month == False):
                raise exceptions.ValidationError("Please select a shipment month")
        if(self.shipment_week == False):
                raise exceptions.ValidationError("Please select a shipment week")
        if(self.container_id == False):
                raise exceptions.ValidationError("Please select a container")
        
        self.state = "final"
        self.name = "Retrieve Booking"
        self.action_process_pallets()
    
    def action_cancel(self):
        if self.is_first_open:
            self.WIZARD_WCS_ORDER_IDS.clear()
            self.WIZARD_MOVE_LINE_IDS.clear()
            self.WIZARD_MOVE_LINES.clear()
        return {'type': 'ir.actions.act_window_close'}
    
    def _inverse_move_lines(self):
        return
    
    def _inverse_wcs_orders(self):
        return
    
    
    @api.depends('pallet_ids')
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

    def _compute_wcs_orders(self):
        self.wcs_order_ids = self.env['shipment_order.move'].search([
                                ('id', 'in', self.WIZARD_WCS_ORDER_IDS),
                                ])
    
    def action_search_ref(self):
        container_obj = self.env['shipment_order.container']
        self.container_id = container_obj.search([
                                ('ref_number', '=ilike', self.ref_number)
                                ])
    @api.onchange('customer','shipment_month','shipment_week')
    def _onchange_fields(self):
        for rec in self:
            #Only validated incoming pickings should be included
            pickings = self.env['stock.picking'].search([
                                ('partner_id','=',rec.customer.id),
                                ('shipment_month','=',rec.shipment_month),
                                ('shipment_week','=',rec.shipment_week),
                                ('picking_type_id','=',1),
                                ('state', '=', 'done'),
                                ('scheduled_date','>=',datetime(datetime.today().year, 1, 1)),
                             ]) 
            containers = []
            if len(pickings) != 0:
                for picking in pickings:
                    for container in picking.container_ids:
                        containers.append(container.id)
            return {'domain': {'container_id': [('id', 'in', containers)]}}
            #return {'domain': {'container_id': [('ref_number', '=ilike', rec.ref_number)]}}
        
    """ @api.onchange('ref_number')
    def _onchange_ref_number(self):
        for rec in self:
            return {'domain': {'container_id': [('ref_number', '=ilike', rec.ref_number)]}} """
    
    @api.onchange('container_id')
    def _onchange_container_id(self):

        for rec in self:
            for existing_pallet in rec.pallet_ids:
                existing_pallet.unlink()
            pallet_obj = self.env['shipment_order.pallet']
            pallet_list = pallet_obj.search([
                                ('container_id', '=', rec.container_id.id)
                                ])
            location_drop_list = []
            out_of_space_pallets = 0
            total_pallets = 0
            rec.ref_number = rec.container_id.ref_number

            # CHECK FOR EXISTING PICKING
            picking_obj = self.env['stock.picking']
            existing_picking = picking_obj.search([
                                    ('ref_number', '=', rec.ref_number),
                                    ('picking_type_id', '=', 2)
                                    ], limit=1)
            if existing_picking.id:
                existing_pallets = []
                for moveline in existing_picking.move_line_ids:
                    if moveline.transport_order_overall_state != 'cancelled':
                        if moveline.pallet_ids:
                            existing_pallets.append(moveline.pallet_ids[0])
                pallet_list = list(filter(lambda x: x not in existing_pallets, pallet_list))
            
            pallets = []
            racks = []
            for pallet in pallet_list:
                pallets.append(pallet)
            pallets.sort(key=(lambda x: x.id),reverse=True)

            for pallet in pallets:
                lot_id = self.env['stock.lot'].search([
                                ('name', '=', pallet.name)
                                ],limit=1, order="id desc")
                if lot_id.id:
                    quant_id = self.env['stock.quant'].search([
                                ('lot_id', '=', lot_id.id),
                                ('quantity', '=', 1),
                                ('reserved_quantity', '=', 0),
                                ('location_id.usage', '!=', 'customer')
                                ],limit=1)
                    if quant_id.id:
                        total_pallets += 1
                        location_id = self.env['stock.location'].browse(quant_id.location_id)
                        
                        if location_id.id:
                            if location_id.id.rack_tag_id.sequence not in racks:
                                racks.append(location_id.id.rack_tag_id.sequence)
                            pallet_max_height = int(self.env['ir.config_parameter'].sudo().get_param('shipment_order.shipment_pallet_max_height'))
                            #if pallet height is more than max height, do not use AGV (is_wcs_order = False)
                            self.env['shipment_order.scan.line.out'].create({
                                                                        'pallet_id' : pallet.name,
                                                                        'length' : pallet.cargo_length,
                                                                        'width' : pallet.cargo_width,
                                                                        'height' : pallet.cargo_height,
                                                                        'pickup_location': location_id.id.id,
                                                                        'drop_off_location': None,
                                                                        'shipment_out_id': self.id,
                                                                        'pickup_is_bottom_rack': True if 'Bottom' in location_id.id.slot_tag_id.category_name else False,
                                                                        'pickup_slot_tag_sequence': location_id.id.slot_tag_id.sequence,
                                                                        'pickup_rack_tag_sequence': location_id.id.rack_tag_id.sequence,
                                                                        'is_wcs_order': False if pallet.cargo_height > pallet_max_height else self.is_wcs_order})

            #SORT FROM FURTHEST TO NEAREST RACK, BOTTOM TO TOP RACK, OUTERMOST TO INNERMOST SLOT           
            racks.sort(reverse=True)
            wcs_sequence = 1
            for rack in racks:
                rack_pallet_list = [x for x in self.pallet_ids if x.pickup_rack_tag_sequence == rack]
                bottom_pallet_list = [x for x in rack_pallet_list if x.pickup_is_bottom_rack]
                bottom_pallet_list.sort(key=lambda x: (x.pickup_slot_tag_sequence), reverse=True)
                top_pallet_list = [x for x in rack_pallet_list if not x.pickup_is_bottom_rack]
                top_pallet_list.sort(key=lambda x: (x.pickup_slot_tag_sequence), reverse=True)
                bottom_pallet_list.extend(top_pallet_list)
                index = 0
                while index < len(bottom_pallet_list):
                    wizard_pallet= bottom_pallet_list[index]
                    location_drop_id = self.env['shipment_order.staging.state'].search([
                                                                ('pallet_id', '=', None),
                                                                ('location_id', 'not in', location_drop_list),
                                                                ],limit=1,order='staging_sequence')
                    if location_drop_id.id:
                        location_drop_list.append(location_drop_id.location_id.id)
                        wizard_pallet.write({'drop_off_location': location_drop_id.location_id.id,
                                             'transport_order_sequence': wcs_sequence})
                        wcs_sequence += 1
                    else: 
                        wizard_pallet.write({'is_wcs_order': False})
                        out_of_space_pallets += 1
                    index+=1
            
            if out_of_space_pallets > 0:
                msg = "Booking No.: " + rec.ref_number + ", Container: " +rec.container_id.container_number + ". \r\n"
                msg += 'WCS transport orders not created for ' + str(out_of_space_pallets) + '/' + str(total_pallets) 
                self.env.user.notify_warning(message=msg,title="Staging Area Full", sticky=True)

                    
    def _populate_staging(self):
        # Get locations with staging tag
        staging_category = self.env['generic.tag.category'].search([('code', '=', 'stgout'),])
        staging_tags = self.env['generic.tag'].search([('category_id', '=', staging_category.id),])
        staging_locations = self.env['stock.location'].search([
                                    ('staging_out_tag_id', 'in', staging_tags.ids)
                                    ])
        for staging in staging_locations:
            # If staging state table does not contain this staging location, add it
            staging_state = self.env['shipment_order.staging.state'].search([('location_id', '=', staging.id),],limit=1)
            if not staging_state.id:
                staging_tag = staging.staging_out_tag_id
                if staging_tag.id:
                    self.env['shipment_order.staging.state'].create({
                                                            'location_id' : staging.id,
                                                            'staging_sequence' : staging_tag.sequence})  

    def _get_default_locations(self, partner):

        picking_type = self.env['stock.picking.type'].browse(2)
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
    
    def action_process_pallets(self):
        #CREATE/RETRIEVE PICKING
        picking_obj = self.env['stock.picking']
        
        incoming_picking = picking_obj.search([
                            ('ref_number', '=ilike', self.container_id.ref_number),
                            ('picking_type_id', '=', 1)
                            ], limit=1)
        if incoming_picking.id == False:
           raise exceptions.ValidationError("No inbound movement found for this booking number")
        
        existing_picking = picking_obj.search([
                                ('ref_number', '=ilike', incoming_picking.ref_number),
                                ('picking_type_id', '=', 2)
                                ], limit=1)
        default_locations = self._get_default_locations(incoming_picking.partner_id)
        picking_pickup_location = default_locations['location_id']
        picking_dropoff_location = default_locations['location_dest_id']
        if existing_picking.id == False:
            #CREATE OUTBOUND PICKING
            existing_picking = picking_obj.create({
                                'picking_type_id': 2,
                                'partner_id': incoming_picking.partner_id.id,
                                'location_id':picking_pickup_location,
                                'location_dest_id':picking_dropoff_location,
                                'ref_number': self.container_id.ref_number,
                                'vessel_name': incoming_picking.vessel_name,
                                'voyage_number': incoming_picking.voyage_number,
                                'eta': incoming_picking.eta,
                                'shipment_month': incoming_picking.shipment_month,
                                'shipment_week': incoming_picking.shipment_week,
                                })
        # UPDATE CONTAINER
        container_id = self.env['shipment_order.container'].search([
                                        ('container_number','=',self.container_id.container_number),
                                        ('picking_id','=',incoming_picking.id)],limit=1)
        if not container_id.id:
            raise exceptions.ValidationError("Inbound movement does not contain this container")
        if container_id.outgoing_picking_id.id == False:
            container_id.write({'outgoing_picking_id':existing_picking.id})
        
        # GET PALLETS TO PROCESS
        pallet_names = []
        pallet_list = []
        for pallet in self.pallet_ids:
            pallet_names.append(pallet.pallet_id)
        
        pallet_list = self.pallet_ids.sorted(key='transport_order_sequence')

        index = 0
        while index < len(pallet_list):
            wizard_pallet = pallet_list[index]
        #for wizard_pallet in self.pallet_ids:
            if wizard_pallet.process_order:
                outbound_pallet =  next((x for x in incoming_picking.pallet_ids if x.name == wizard_pallet.pallet_id), None)
                #wizard_pallet = next((x for x in self.pallet_ids if x.pallet_id == outbound_pallet.name), None)
                existing_move_line = False
                move_lines = self.env['stock.move.line'].search([
                                ('picking_id', '=', existing_picking.id)
                                ])
                move_line = False
                for ml in move_lines:
                    if ml.pallet_ids[0].id == outbound_pallet.id:
                        move_line = ml
                        break
                if not move_line:
                    move_line = self._create_move_line(outbound_pallet, existing_picking, wizard_pallet.is_wcs_order,incoming_picking,wizard_pallet.pickup_location,picking_dropoff_location)
                else: existing_move_line = True
                
                #delete existing transport orders
                if existing_move_line:
                    for to in move_line.transport_order_ids:
                        to.unlink()
                    move_line.write(
                        {'is_wcs_order': wizard_pallet.is_wcs_order}
                    )

                print("MOVE LINE: " + str(move_line.id))
                if wizard_pallet.is_wcs_order:
                    #BOTTOM RACK: PICK UP FROM RACK, DROP OFF AT STAGING
                    #TOP RACK: 1. PICK UP FROM RACK, DROP OFF AT ELEVATED TRAY CLOSED SIDE
                    #          2. PICK UP FROM ELEVATED TRAY OPEN SIDE, DROP OFF AT STAGING

                    if wizard_pallet.pickup_is_bottom_rack:
                        wcs_order = self.env['shipment_order.move'].create({'location_id': wizard_pallet.pickup_location.id,
                                                                'location_dest_id': wizard_pallet.drop_off_location.id,
                                                                'wcs_state_1': 'pending',
                                                                'wcs_pickup_1': wizard_pallet.pickup_location.name,
                                                                'wcs_dropoff_1': wizard_pallet.drop_off_location.name,
                                                                'wcs_timestamp': datetime.today(),
                                                                'pallet_id': outbound_pallet.id,
                                                                'picking_id': existing_picking.id,
                                                                'move_line_id': move_line.id,
                                                                'qr_code': outbound_pallet.qr_code_data})
                        self._send_wcs_order(wizard_pallet.pickup_location.name, wizard_pallet.drop_off_location.name,outbound_pallet.id, wcs_order, 1, False)
                    else:
                        #Get available elevated tray (closed side)
                        elevated_tray = self.env['shipment_order.elevated.tray'].search([],order='pallet_date, priority', limit=1)
                        if elevated_tray.id == False:
                            raise exceptions.ValidationError("No available elevated tray for pallet" + outbound_pallet.name)
                        
                        elevated_tray.write({'occupied_state': 'Reserved',
                                            'pallet_date': datetime.today()})
                        wcs_order = self.env['shipment_order.move'].create({'location_id': wizard_pallet.pickup_location.id,
                                                                'location_dest_id': wizard_pallet.drop_off_location.id,
                                                                'wcs_state_1': 'pending',
                                                                'wcs_pickup_1': wizard_pallet.pickup_location.name,
                                                                'wcs_dropoff_1': elevated_tray.closed_side_code,
                                                                'wcs_state_2': 'pending',
                                                                'wcs_pickup_2':elevated_tray.open_side_code,
                                                                'wcs_dropoff_2': wizard_pallet.drop_off_location.name,
                                                                'wcs_timestamp': datetime.today(),
                                                                'pallet_id': outbound_pallet.id,
                                                                'picking_id': existing_picking.id,
                                                                'move_line_id': move_line.id,
                                                                'qr_code': outbound_pallet.qr_code_data})
                        self._send_wcs_order(wizard_pallet.pickup_location.name, elevated_tray.closed_side_code,outbound_pallet.id, wcs_order, 1, True)
                        self._send_wcs_order(elevated_tray.open_side_code,  wizard_pallet.drop_off_location.name,outbound_pallet.id, wcs_order, 2, False)
                        
                    self.WIZARD_WCS_ORDER_IDS.append(wcs_order.id)
                    print("WCS ORDER: " + str(wcs_order))
                else:
                    move_line.write({'qty_done':1})
                    if move_line.state != 'done':
                        move_line._action_done()
                        move_line.write({'state':'confirmed'})
                    
                
                staging_state = self.env['shipment_order.staging.state'].search([('location_id', '=', wizard_pallet.drop_off_location.id),],limit=1)
                if staging_state.id:
                    staging_state.write({'pallet_id':outbound_pallet.id, 'pallet_date':date.today()})
                
                self.WIZARD_MOVE_LINE_IDS.append(move_line.id)
                self.WIZARD_MOVE_LINES.append(move_line)
            self.recompute_wcs_order_ids = not(self.recompute_wcs_order_ids)
            index += 1

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
                    wcs_order.write({state_field_name: 'error'})
                    remarks = 'Error creating transport order. ' + msg
                    wcs_message_type = 'system'
                
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

    @api.depends('recompute_wcs_order_ids')
    def _compute_wcs_orders(self):
        self.wcs_order_ids = self.env['shipment_order.move'].search([
                                ('id', 'in', self.WIZARD_WCS_ORDER_IDS),
                                ])
    @api.depends('pallet_ids')
    def _compute_move_lines(self):
        self.move_line_ids = self.env['stock.move.line'].search([
                                ('id', 'in', self.WIZARD_MOVE_LINE_IDS),
                                ])
    
    @api.depends('pallet_ids')
    def _compute_move_lines(self):
        self.num_pallets = len(self.pallet_ids)
                           
    def _create_move_line(self, pallet_id, picking_id, is_wcs_order, incoming_picking, pickup_location, picking_dropoff_location):
        
        incoming_product_move_line = next((x for x in incoming_picking.move_line_ids if x.lot_name == pallet_id.name), None)
        if incoming_product_move_line.id:
            product_obj = incoming_product_move_line.product_id
                
            print(",".join([str(pallet_id),str(product_obj.id),str(self.company_id.id)]))
            lot_id = self.env['stock.lot'].search([
                        ('name', '=', pallet_id.name),
                        ('product_id', '=', product_obj.id),
                        ('company_id', '=', self.company_id.id),
                        ], limit=1)
            
            print("lot: " + str(lot_id.id) + ", " + str(lot_id))
            move_line_obj = self.env['stock.move.line']
            
            outbound_pallet = next((x for x in self.pallet_ids if x.pallet_id == pallet_id.name), None)
            new_move_line = move_line_obj.create({'picking_id': picking_id.id,
                                'company_id': self.company_id.id,
                                'product_id': product_obj.id,
                                'product_uom_id': product_obj.uom_id.id,
                                'location_id': pickup_location.id,
                                'location_dest_id': picking_dropoff_location,
                                'lot_id': lot_id.id,
                                'lot_name':pallet_id.name,
                                'reference': picking_id.name,
                                'reserved_uom_qty': 0,
                                'qty_done': 0,
                                'is_wcs_order': is_wcs_order,
                                'pallet_id': pallet_id.id,
                                'inbound_from': outbound_pallet.pickup_location.id,
                                'outbound_to': outbound_pallet.drop_off_location.id})
            pallet_id.write({'outbound_move_line_id':new_move_line.id})
                    
            if picking_id.state == 'draft':
                picking_id.action_assign()
            
            if new_move_line.id:
                self.WIZARD_MOVE_LINE_IDS.append(new_move_line._origin.id)
                self.WIZARD_MOVE_LINES.append(new_move_line)

        
            return new_move_line
