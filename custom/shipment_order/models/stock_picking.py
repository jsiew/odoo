# -*- coding: utf-8 -*-
from odoo import models, fields, api,_
from datetime import date
from odoo.exceptions import UserError, ValidationError

class StockPicking(models.Model):
    _inherit = "stock.picking"
    move_line_ids_without_package = fields.One2many('stock.move.line', 'picking_id', 'Pallets', domain=['|',('package_level_id', '=', False), ('picking_type_entire_packs', '=', False)])
 
    shipment_type = fields.Selection([('I', 'Import'), ('E','Export')], default = 'I', states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    ref_number = fields.Char(string="B/L/Bkg No.",required=False, index="trigram", states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    
    vessel_name = fields.Char(string="Vessel Name", states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    voyage_number = fields.Char(string="Voyage No.", states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    eta = fields.Date(string="ETA",default=date.today(), required=True, states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    shipment_month = fields.Selection([('1', 'January'), ('2', 'February'), ('3', 'March'), ('4', 'April'),
                            ('5', 'May'), ('6', 'June'), ('7', 'July'), ('8', 'August'), 
                            ('9', 'September'), ('10', 'October'), ('11', 'November'), ('12', 'December')], 
                            string='Shipment Month', default=str(date.today().month), states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    shipment_week = fields.Selection([('0','0'),('1','1'),('2','2'),('3','3'),('4','4'),('5','5')], default = str((date.today().day - 1 + (date.today().weekday() - date.today().day + 1) % 7)//7+1)
                                     , states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    pallet_ids = fields.One2many('shipment_order.pallet', string="Pallets", compute='_compute_pallet_ids')
    container_ids = fields.One2many('shipment_order.container', 'picking_id', string="Containers")
    outgoing_container_ids = fields.One2many('shipment_order.container', 'outgoing_picking_id', string="Containers")

    num_containers = fields.Integer('No. of Containers', compute='_compute_qty')
    num_pallets = fields.Integer('No. of Pallets', compute='_compute_qty')
    containers = fields.One2many('shipment_order.container',string="Container(s)", compute='_compute_qty')
    
    qr_code_data = fields.Char(string="Scan QR Code", store=False)
    #States: 
    # pending - not ready for wcs, 
    # ready - ready for wcs to pick, 
    # in progress - movement in progress, 
    # error - wcs error encountered, 
    # done - completed
    wcs_status = fields.Char(default='pending', string ="WCS Status",  states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    wcs_order_ids = fields.One2many('shipment_order.move', 'picking_id', string ='Transport Orders')

    @api.depends('pallet_ids','container_ids')
    def _compute_qty(self):
        for record in self:
            record.num_containers = len(record.container_ids)
            if record.num_containers == 0: 
                record.num_containers = len(record.outgoing_container_ids)
                record.containers = record.outgoing_container_ids
            else: record.containers = record.container_ids
            record.num_pallets = len(record.pallet_ids)

    def button_validate(self):
        for move_line in self.move_line_ids:
            if move_line.is_wcs_order:
                if move_line.transport_order_overall_state not in ('error','completed','cancelled','cancelling'):
                    raise UserError(_('All WCS transport orders must be in completed or cancelled state'))
        res = super(StockPicking, self).button_validate()
        return res

    def action_assign(self):
        res = super(StockPicking, self).action_assign()
        return res
    
    def unlink(self):
        self.move_ids._action_cancel()
        self.with_context(prefetch_fields=False).move_ids.unlink()  # Checks if moves are not done
        if self.picking_type_id.id == 1:
            for container in self.container_ids:
                container.unlink()
        return super(StockPicking, self).unlink()
        
    
    def _compute_pallet_ids(self):
        for record in self:
            pallet_list = []
            if record.picking_type_code == 'incoming':
                for container in record.container_ids:
                    for pallet in container.pallet_ids:
                        pallet_list.append(pallet.id)
            if record.picking_type_code == 'outgoing':
                for container in record.outgoing_container_ids:
                    for pallet in container.pallet_ids:
                        pallet_list.append(pallet.id)
        
            if len(pallet_list) == 0:
                record.pallet_ids = None
            else:  record.pallet_ids = pallet_list
            
            print("pallet: " + str(pallet_list))

    def _action_done(self):
        """Call `_action_done` on the `stock.move` of the `stock.picking` in `self`.
        This method makes sure every `stock.move.line` is linked to a `stock.move` by either
        linking them to an existing one or a newly created one.

        If the context key `cancel_backorder` is present, backorders won't be created.

        :return: True
        :rtype: bool
        """
        self._check_company()

        todo_moves = self.move_ids.filtered(lambda self: self.state in ['draft', 'waiting', 'partially_available', 'assigned', 'confirmed'])
        for picking in self:
            if picking.owner_id:
                picking.move_ids.write({'restrict_partner_id': picking.owner_id.id})
                picking.move_line_ids.write({'owner_id': picking.owner_id.id})
        todo_moves._action_done(cancel_backorder=self.env.context.get('cancel_backorder'))
        self.write({'date_done': fields.Datetime.now(), 'priority': '0'})

        # if incoming/internal moves make other confirmed/partially_available moves available, assign them
        done_incoming_moves = self.filtered(lambda p: p.picking_type_id.code in ('incoming', 'internal')).move_ids.filtered(lambda m: m.state == 'done')
        done_incoming_moves._trigger_assign()

        self._send_confirmation_email()

        # MMT Update Staging Area to free up space
        if self.picking_type_code == 'outgoing':
            for pallet in self.pallet_ids:
                staging_id = self.env['shipment_order.staging.state'].search([
                                                    ('pallet_id','=', pallet.id)
                                                ])
                if staging_id.id:
                    staging_id.write({'pallet_id':None, 'pallet_date':None})
        return True                                       