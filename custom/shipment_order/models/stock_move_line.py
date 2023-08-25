# -*- coding: utf-8 -*-
from collections import defaultdict
from odoo import _, api, fields, tools, models
from odoo.tools import OrderedSet, groupby
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from odoo.exceptions import UserError, ValidationError

class StockMoveLine(models.Model):
    _inherit = "stock.move.line"
    _rec_name = "pallet_id"


    #transport order = one2one field
    transport_order_id = fields.Many2one('shipment_order.move', compute='compute_transport_order', inverse='transport_order_inverse', string ='Transport Order', store=True)
    transport_order_ids = fields.One2many('shipment_order.move', 'move_line_id', string ='Transport Orders')
    transport_order_state_1 = fields.Char( compute='compute_transport_order', string ='1st WCS State',compute_sudo=True)
    transport_order_wcs_id_1 = fields.Char( compute='compute_transport_order', string ='1st WCS ID',compute_sudo=True)
    transport_order_state_2 = fields.Char( compute='compute_transport_order', string ='2nd WCS State',compute_sudo=True)
    transport_order_wcs_id_2 = fields.Char( compute='compute_transport_order', string ='2nd WCS ID',compute_sudo=True)
    transport_order_overall_state = fields.Char(string='Transport Order State', related='transport_order_id.wcs_overall_state')
    transport_order_state_summary = fields.Html(string='Transport Order State Desc', related='transport_order_id.wcs_state_summary')
    transport_order_id_summary = fields.Html(string='Transport Order IDs', related='transport_order_id.wcs_id_summary')
    transport_order_description = fields.Html(string='Transport Order Description', related='transport_order_id.wcs_order_desc')

    transport_order_log_ids = fields.One2many('shipment_order.movelog', compute='compute_transport_order',compute_sudo=True)

    pallet_id = fields.Many2one('shipment_order.pallet', compute='compute_pallet', inverse='pallet_inverse', index = True, string ='Pallet Ref')
    pallet_ids = fields.One2many('shipment_order.pallet', 'move_line_id', string ='Pallets')

    pickup_location_tag_id = fields.Many2one('generic.tag',compute='_compute_field_names', string="Pickup Tag") 
    inbound_from = fields.Many2one('stock.location',domain="[('generic_tag_ids','in',[pickup_location_tag_id])]", string='Pickup Location')
    outbound_to = fields.Many2one('stock.location', string='Drop Off Location')
    
    customer = fields.Char(compute='_compute_field_names',string ='Cust.')
    container_number = fields.Char(compute='_compute_container', string ='Ctr No.', store=True)
    container_number_actual = fields.Char(compute='_compute_container', string ='Act. Ctr No.', store=True)
    ref_number = fields.Char(compute='_compute_field_names', string ='BL/Bking No.')
    pallet_name = fields.Char(compute='_compute_field_names', string ='Pallet')
    move_from = fields.Char(related='location_id.name', string ='From')
    move_to = fields.Char(related='location_dest_id.name', string ='To')
    product_name = fields.Char(related='product_id.name', string ='Type')
    picking_type_id_ref = fields.Integer(related='picking_type_id.id', string ='Picking Type ID')

    is_wcs_order = fields.Boolean('Is WCS Order',default=False)

    @api.depends('pallet_id')
    def _compute_field_names(self):
       for record in self:
            if record.pallet_ids:
                record.customer = record.pallet_id.container_id.picking_id.partner_id.name
                record.pallet_name = record.pallet_ids.name
                record.ref_number = record.pallet_id.container_id.picking_id.ref_number
            else: 
                record.customer = ''
                record.pallet_name = ''
                record.ref_number = ''
                
            tag = self.env['generic.tag'].search([('code', '=', 'pickup'),], limit=1)
            if len(tag) == 0:
                raise(ValidationError,'No pickup locations found')
            else: record.pickup_location_tag_id = tag

    @api.depends('pallet_id')
    def _compute_container(self):
        for record in self:
            if record.pallet_id:
                record.container_number = record.pallet_id.container_number
                record.container_number_actual = record.pallet_id.container_number_actual
            else: record.container_number = ''

    @api.depends('transport_order_ids')
    def compute_transport_order(self):
        for record in self:
            transport_order = self.env['shipment_order.move'].search([('move_line_id', '=', record.id),], limit=1)
            if transport_order.id:
                record.transport_order_id = transport_order.id
                record.transport_order_wcs_id_1 = transport_order.wcs_id_1
                record.transport_order_state_1 =transport_order.wcs_state_1
                record.transport_order_wcs_id_2 = transport_order.wcs_id_2
                record.transport_order_state_2 =transport_order.wcs_state_2
                record.transport_order_log_ids = transport_order.log_ids
            else: 
                record.transport_order_state_1 = False
                record.transport_order_state_2 = False
                record.transport_order_wcs_id_1 = False
                record.transport_order_wcs_id_2 = False
                record.transport_order_log_ids = False
    
    def _search_transport_order(self):
        transport_order = self.env['shipment_order.move'].search([('move_line_id', '=', self.id)], limit=1)
        if transport_order: return True
        else: return False


    def transport_order_inverse(self):
        if len(self.transport_order_ids) > 0:
            # delete previous reference
            transport_order = self.env['shipment_order.move'].browse(self.transport_order_ids[0].id)
            transport_order.move_line_id = False
        # set new reference
        self.transport_order_id.move_line_id = self
    
    @api.depends('pallet_ids')
    def compute_pallet(self):
        if len(self.pallet_ids) > 0:
            self.pallet_id = self.pallet_ids[0]
        else: self.pallet_id = False

    def pallet_inverse(self):
        if len(self.transport_order_ids) > 0:
            # delete previous reference
            pallet = self.env['shipment_order.pallet'].browse(self.pallet_ids[0].id)
            pallet.move_line_id = False
        # set new reference
        self.pallet_id.move_line_id = self

    def action_update_wcs_order(self):
        return{
            'name': "Update WCS Order",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'shipment_order.move.edit.wizard',
            'view_id': self.env.ref('shipment_order.shipment_order_move_edit_view').id,
            'target': 'new',
            'context': {'transport_order': self.transport_order_id.id, 'move_line': self.id} 
        }

    def write(self, vals):
        if 'location_dest_id' in vals:
            location_dest_id = self.env['stock.location'].browse(vals['location_dest_id'])
            if location_dest_id.id != self.location_dest_id.id:
                if 'product_id' in vals:
                    product_to_check = self.env['product.product'].browse(vals['product_id'])
                else: product_to_check = self.product_id

                qty_by_location = defaultdict(lambda: 0)
                move_line_data = self.env['stock.move.line']._read_group([
                    ('id', 'not in', self._context.get('exclude_sml_ids', [])),
                    ('product_id', '=', product_to_check.id),
                    ('location_dest_id', '=', location_dest_id.id),
                    ('state', 'not in', ['draft', 'done', 'cancel'])
                ], ['location_dest_id', 'product_id', 'reserved_qty:array_agg', 'qty_done:array_agg', 'product_uom_id:array_agg'], ['location_dest_id'])
                quant_data = self.env['stock.quant']._read_group([
                    ('product_id', '=', product_to_check.id),
                    ('location_id', '=', location_dest_id.id),
                ], ['location_id', 'product_id', 'quantity:sum'], ['location_id'])

                for values in move_line_data:
                    uoms = self.env['uom.uom'].browse(values['product_uom_id'])
                    qty_done = sum(max(ml_uom._compute_quantity(float(qty), product_to_check.uom_id), float(qty_reserved))
                                for qty_reserved, qty, ml_uom in zip(values['reserved_qty'], values['qty_done'], list(uoms)))
                    qty_by_location[values['location_dest_id'][0]] = qty_done
                for values in quant_data:
                    qty_by_location[values['location_id'][0]] += values['quantity']

                can_use = location_dest_id._check_can_be_used(product_to_check,self.qty_done,None,qty_by_location[location_dest_id.id])
                if not can_use:
                    raise UserError(_('Destination location is full'))
                
        res = super(StockMoveLine, self).write(vals)
        return res
    """ 
    def unlink(self):
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        for ml in self:
            # MMT reduce move reserved qty for WCS order
            if ml.is_wcs_order:
                if ml.move_id.product_uom_qty > 0:
                    ml.move_id.write({'product_uom_qty':  (ml.move_id.product_uom_qty - 1.0)}) 

            # Unlinking a move line should unreserve.
            if not float_is_zero(ml.reserved_qty, precision_digits=precision) and ml.move_id and not ml.move_id._should_bypass_reservation(ml.location_id):
                self.env['stock.quant']._update_reserved_quantity(ml.product_id, ml.location_id, -ml.reserved_qty, lot_id=ml.lot_id, package_id=ml.package_id, owner_id=ml.owner_id, strict=True)
        moves = self.mapped('move_id')
        res = super(StockMoveLine, self).unlink()
        if moves:
            # Add with_prefetch() to set the _prefecht_ids = _ids
            # because _prefecht_ids generator look lazily on the cache of move_id
            # which is clear by the unlink of move line
            moves.with_prefetch()._recompute_state()
        return res 
        """

    def _action_done(self):
        """ This method is called during a move's `action_done`. It'll actually move a quant from
        the source location to the destination location, and unreserve if needed in the source
        location.

        This method is intended to be called on all the move lines of a move. This method is not
        intended to be called when editing a `done` move (that's what the override of `write` here
        is done.
        """
        Quant = self.env['stock.quant']

        # First, we loop over all the move lines to do a preliminary check: `qty_done` should not
        # be negative and, according to the presence of a picking type or a linked inventory
        # adjustment, enforce some rules on the `lot_id` field. If `qty_done` is null, we unlink
        # the line. It is mandatory in order to free the reservation and correctly apply
        # `action_done` on the next move lines.
        ml_ids_tracked_without_lot = OrderedSet()
        ml_ids_to_delete = OrderedSet()
        ml_ids_to_create_lot = OrderedSet()
        for ml in self:
            # Check here if `ml.qty_done` respects the rounding of `ml.product_uom_id`.
            uom_qty = float_round(ml.qty_done, precision_rounding=ml.product_uom_id.rounding, rounding_method='HALF-UP')
            precision_digits = self.env['decimal.precision'].precision_get('Product Unit of Measure')
            qty_done = float_round(ml.qty_done, precision_digits=precision_digits, rounding_method='HALF-UP')
            if float_compare(uom_qty, qty_done, precision_digits=precision_digits) != 0:
                raise UserError(_('The quantity done for the product "%s" doesn\'t respect the rounding precision '
                                  'defined on the unit of measure "%s". Please change the quantity done or the '
                                  'rounding precision of your unit of measure.') % (ml.product_id.display_name, ml.product_uom_id.name))

            qty_done_float_compared = float_compare(ml.qty_done, 0, precision_rounding=ml.product_uom_id.rounding)
            if qty_done_float_compared > 0:
                if ml.product_id.tracking != 'none':
                    picking_type_id = ml.move_id.picking_type_id
                    if picking_type_id:
                        if picking_type_id.use_create_lots:
                            # If a picking type is linked, we may have to create a production lot on
                            # the fly before assigning it to the move line if the user checked both
                            # `use_create_lots` and `use_existing_lots`.
                            if ml.lot_name and not ml.lot_id:
                                lot = self.env['stock.lot'].search([
                                    ('company_id', '=', ml.company_id.id),
                                    ('product_id', '=', ml.product_id.id),
                                    ('name', '=', ml.lot_name),
                                ], limit=1)
                                if lot:
                                    ml.lot_id = lot.id
                                else:
                                    ml_ids_to_create_lot.add(ml.id)
                        elif not picking_type_id.use_create_lots and not picking_type_id.use_existing_lots:
                            # If the user disabled both `use_create_lots` and `use_existing_lots`
                            # checkboxes on the picking type, he's allowed to enter tracked
                            # products without a `lot_id`.
                            continue
                    elif ml.is_inventory:
                        # If an inventory adjustment is linked, the user is allowed to enter
                        # tracked products without a `lot_id`.
                        continue

                    if not ml.lot_id and ml.id not in ml_ids_to_create_lot:
                        ml_ids_tracked_without_lot.add(ml.id)
            elif qty_done_float_compared < 0:
                raise UserError(_('No negative quantities allowed'))
            elif not ml.is_inventory:
                ml_ids_to_delete.add(ml.id)

        if ml_ids_tracked_without_lot:
            mls_tracked_without_lot = self.env['stock.move.line'].browse(ml_ids_tracked_without_lot)
            raise UserError(_('You need to supply a Lot/Serial Number for product: \n - ') +
                              '\n - '.join(mls_tracked_without_lot.mapped('product_id.display_name')))
        ml_to_create_lot = self.env['stock.move.line'].browse(ml_ids_to_create_lot)
        ml_to_create_lot.with_context(bypass_reservation_update=True)._create_and_assign_production_lot()

        mls_to_delete = self.env['stock.move.line'].browse(ml_ids_to_delete)
        mls_to_delete.unlink()

        mls_todo = (self - mls_to_delete)
        mls_todo._check_company()

        # Now, we can actually move the quant.
        ml_ids_to_ignore = OrderedSet()
        for ml in mls_todo:
            if ml.product_id.type == 'product':
                rounding = ml.product_uom_id.rounding

                # if this move line is force assigned, unreserve elsewhere if needed
                if not ml.move_id._should_bypass_reservation(ml.location_id) and float_compare(ml.qty_done, ml.reserved_uom_qty, precision_rounding=rounding) > 0:
                    qty_done_product_uom = ml.product_uom_id._compute_quantity(ml.qty_done, ml.product_id.uom_id, rounding_method='HALF-UP')
                    extra_qty = qty_done_product_uom - ml.reserved_qty
                    ml._free_reservation(ml.product_id, ml.location_id, extra_qty, lot_id=ml.lot_id, package_id=ml.package_id, owner_id=ml.owner_id, ml_ids_to_ignore=ml_ids_to_ignore)
                # unreserve what's been reserved
                if not ml.move_id._should_bypass_reservation(ml.location_id) and ml.product_id.type == 'product' and ml.reserved_qty:
                    Quant._update_reserved_quantity(ml.product_id, ml.location_id, -ml.reserved_qty, lot_id=ml.lot_id, package_id=ml.package_id, owner_id=ml.owner_id, strict=True)

                # move what's been actually done
                # MMT: Only for non WCS orders and WCS orders with done qty 
                if (ml.is_wcs_order == False or (ml.is_wcs_order and ml.qty_done == 1 ))  and ml.state != 'confirmed':
                    quantity = ml.product_uom_id._compute_quantity(ml.qty_done, ml.move_id.product_id.uom_id, rounding_method='HALF-UP')
                    available_qty, in_date = Quant._update_available_quantity(ml.product_id, ml.location_id, -quantity, lot_id=ml.lot_id, package_id=ml.package_id, owner_id=ml.owner_id)
                    if available_qty < 0 and ml.lot_id:
                        # see if we can compensate the negative quants with some untracked quants
                        untracked_qty = Quant._get_available_quantity(ml.product_id, ml.location_id, lot_id=False, package_id=ml.package_id, owner_id=ml.owner_id, strict=True)
                        if untracked_qty:
                            taken_from_untracked_qty = min(untracked_qty, abs(quantity))
                            Quant._update_available_quantity(ml.product_id, ml.location_id, -taken_from_untracked_qty, lot_id=False, package_id=ml.package_id, owner_id=ml.owner_id)
                            Quant._update_available_quantity(ml.product_id, ml.location_id, taken_from_untracked_qty, lot_id=ml.lot_id, package_id=ml.package_id, owner_id=ml.owner_id)
                    Quant._update_available_quantity(ml.product_id, ml.location_dest_id, quantity, lot_id=ml.lot_id, package_id=ml.result_package_id, owner_id=ml.owner_id, in_date=in_date)
            ml_ids_to_ignore.add(ml.id)
        # Reset the reserved quantity as we just moved it to the destination location.
        mls_todo.with_context(bypass_reservation_update=True).write({
            'reserved_uom_qty': 0.00,
            'date': fields.Datetime.now(),
        })