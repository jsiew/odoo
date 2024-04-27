# -*- coding: utf-8 -*-
from odoo import fields,models,api,  _
from odoo.tools.float_utils import float_compare
class Location(models.Model):
    _name = "stock.location"
    _inherit = ["stock.location", "generic.tag.mixin",]
    _rec_names_search = ['complete_name', 'barcode']

    pallet_name = fields.Char('Pallet', compute="_compute_pallets",search = '_search_pallet')
    container_number = fields.Char('Container', compute="_compute_pallets",search = '_search_container')
    ref_number = fields.Char("B/L/Bkg No.", compute="_compute_pallets",search = '_search_ref')
    
    rack_tag_id = fields.Many2one('generic.tag',string = 'Rack Tag', compute="_compute_tags",store=True)
    slot_tag_id = fields.Many2one('generic.tag','Slot Tag', compute="_compute_tags",store=True)
    staging_out_tag_id = fields.Many2one('generic.tag','Staging Out Tag', compute="_compute_tags",store=True)
    

    def _search_pallet(self, operator, value):
        pallets = self.env["shipment_order.pallet"].search(
                            [("name", operator, value)])
        
        pallet_names = []
        for pallet in pallets:
            pallet_names.append(pallet.name)
        quant_ids = self.env["stock.quant"].search(
                            [("lot_id.name", "in", pallet_names),
                            ("quantity", ">", 0)]
                        )
        locations = []
        for quant in quant_ids:
            locations.append(quant.location_id.id)
        return [('id','in',locations)]
    
    def _search_container(self, operator, value):
        
        pallets = self.env["shipment_order.pallet"].search(
                            [("container_number", operator, value)])
        
        pallet_names = []
        for pallet in pallets:
            pallet_names.append(pallet.name)
        quant_ids = self.env["stock.quant"].search(
                            [("lot_id.name", "in", pallet_names),
                            ("quantity", ">", 0)]
                        )
        locations = []
        for quant in quant_ids:
            locations.append(quant.location_id.id)
        return [('id','in',locations)]
    
    def _search_ref(self, operator, value):
        
        pallets = self.env["shipment_order.pallet"].search(
                            [("container_id.picking_id.ref_number", operator, value)])
        
        pallet_names = []
        for pallet in pallets:
            pallet_names.append(pallet.name)
        quant_ids = self.env["stock.quant"].search(
                            [("lot_id.name", "in", pallet_names),
                            ("quantity", ">", 0)]
                        )
        locations = []
        for quant in quant_ids:
            locations.append(quant.location_id.id)
        return [('id','in',locations)]

    @api.depends('generic_tag_ids')
    def _compute_tags(self):
        for record in self:
            record.rack_tag_id = self._get_rack_tag(record)
            record.slot_tag_id = self._get_slot_tag(record)
            record.staging_out_tag_id = self._get_staging_tag(record)

    @api.depends('quant_ids')
    def _compute_pallets(self):
        for location in self:
            location.pallet_name = ''
            location.container_number = ''
            location.ref_number = ''
            quant_id = self.env["stock.quant"].search(
                            [("location_id", "=", location.id),
                            ("quantity", ">", 0)], limit = 1
                        )
            if quant_id.lot_id.id:
                    pallet_number = quant_id.lot_id.name
                    location.pallet_name = pallet_number
                    pallet_id = self.env["shipment_order.pallet"].search(
                            [("name", "=", pallet_number),], limit = 1)
                    if pallet_id.id:
                        location.container_number = pallet_id.container_number
                        if pallet_id.move_line_id.picking_id.ref_number:
                            location.ref_number = pallet_id.move_line_id.picking_id.ref_number
            child_locations = self.env['stock.location'].search([('id', 'child_of', location.id)])
            for record in child_locations:
                record.pallet_name = ''
                record.container_number = ''
                record.ref_number = ''
                quant_id = self.env["stock.quant"].search(
                            [("location_id", "=", record.id),
                            ("quantity", ">", 0)], limit = 1
                        )
                if quant_id.lot_id.id:
                        pallet_number = quant_id.lot_id.name
                        record.pallet_name = pallet_number
                        pallet_id = self.env["shipment_order.pallet"].search(
                                [("name", "=", pallet_number),], limit = 1)
                        if pallet_id.id:
                            record.container_number = pallet_id.container_number
                            if pallet_id.move_line_id.picking_id.ref_number:
                                record.ref_number = pallet_id.move_line_id.picking_id.ref_number
    
    def _get_rack_tag(self, location_id):
        rack_category = self.env['generic.tag.category'].search([
                                ('code','=', 'rack')
                            ], limit=1)
        for tag in location_id.generic_tag_ids:
            if tag.category_id.id == rack_category.id:
                return tag
        return None

    def _get_slot_tag(self, location_id):
        slot_category = self.env['generic.tag.category'].search(['|',
                                ('code','=', 'top_slot'),
                                ('code','=', 'bottom_slot')
                            ])
        for tag in location_id.generic_tag_ids:
            if tag.category_id.id in slot_category.ids:
                return tag
        return None
    
    def _get_staging_tag(self, location_id):
        slot_category = self.env['generic.tag.category'].search([
                                ('code','=', 'stgout')
                            ])
        for tag in location_id.generic_tag_ids:
            if tag.category_id.id in slot_category.ids:
                return tag
        return None

    def _check_can_be_used(self, product, quantity=0, package=None, location_qty=0, is_wcs_order=True):
        """Check if product/package can be stored in the location. Quantity
        should in the default uom of product, it's only used when no package is
        specified."""
        self.ensure_one()
        if self.storage_category_id:
            # check if enough space
            if package and package.package_type_id:
                # check weight
                package_smls = self.env['stock.move.line'].search([('result_package_id', '=', package.id)])
                if self.storage_category_id.max_weight < self.forecast_weight + sum(package_smls.mapped(lambda sml: sml.reserved_qty * sml.product_id.weight)):
                    return False
                # check if enough space
                package_capacity = self.storage_category_id.package_capacity_ids.filtered(lambda pc: pc.package_type_id == package.package_type_id)
                if package_capacity and location_qty >= package_capacity.quantity:
                    return False
            else:
                # check weight
                if self.storage_category_id.max_weight < self.forecast_weight + product.weight * quantity:
                    return False
                product_capacity = self.storage_category_id.product_capacity_ids.filtered(lambda pc: pc.product_id == product)
                # To handle new line without quantity in order to avoid suggesting a location already full
                #if product_capacity and location_qty >= product_capacity.quantity:
                #    return False
                if product_capacity and quantity + location_qty > product_capacity.quantity:
                    return False
                # MMT - Restrict to maximum capacity of storage category 
                if self.storage_category_id.max_total_capacity != None:
                    if self.storage_category_id.max_total_capacity != 0:
                        if product_capacity and quantity + location_qty > self.storage_category_id.max_total_capacity:
                            return False

                if is_wcs_order == True:     
                    # MMT - Drive in rack restrictions [ONLY WHEN USING AGV, DO NOT RESTRICT FOR MANUAL OPERATIONS]: 
                    # if the location is a bottom slot 
                    # - all the bottom slots in the same rack with sequence more than or equal to the current slot cannot be occupied

                    # if the location is a top slot
                    # - all the top slots in the same rack with sequence more than the current slot cannot be occupied
                    # - all the bottom slots in the same rack with sequence more than or equal the current slot cannot be occupied
                    
                    #If location has a rack and a slot, validate
                    rack_tag_id = self._get_rack_tag(self)
                    slot_tag_id = self._get_slot_tag(self)
                    if rack_tag_id and slot_tag_id:
                        is_top_shelf = False    
                        if self.check_tag_category("top_slot"): is_top_shelf = True
                        #check that slots with sequence greater than this slot are not occupied
                        same_level_tag_ids = []
                        #get tags with sequence more than current tag 
                        slot_tags = self.env['generic.tag'].search([
                                        ('category_id', '=', slot_tag_id.category_id.id),
                                        ('sequence', '>', slot_tag_id.sequence)
                                        ])
                        
                        for tag in slot_tags:
                            same_level_tag_ids.append(tag.id)

                        #get all locations in the same rack and level with sequence more than current tag 
                        same_rack_level_locations = self.env['stock.location'].search([
                                        ('slot_tag_id', 'in', same_level_tag_ids),
                                        ('rack_tag_id','=',rack_tag_id.id)
                                        ])

                        #check if there is quantity in any of these locations
                        quants = self.env['stock.quant'].search([
                                        ('location_id', 'in', same_rack_level_locations.ids), '|',
                                            ('quantity', '>', 0),
                                            ('reserved_quantity', '>', 0),
                                        ])
                        #pending move line
                        mls = self.env['stock.move.line'].search(['|',
                                ('location_dest_id', 'in', same_rack_level_locations.ids),
                                ('location_dest_id', '=', self.id),
                                ('state', 'in', ('draft', 'waiting', 'confirmed', 'assigned', 'partially_available')),
                                ('reserved_qty', '>', 0),
                        ])
                        ml_list = []
                        for ml in mls:
                            if str(ml.id) not in ml.move_line_exclusions:
                                ml_list.append(ml)
                        if len(quants) > 0 or len(ml_list)>0: return False

                        #for top shelf, all the bottom slots in the same rack with sequence more than or equal the current slot cannot be occupied
                        if is_top_shelf:
                            tag_category = self.env['generic.tag.category'].search([
                                                ('code', '=', 'bottom_slot'),
                                                ],limit=1)
                            bottom_shelf_tags = self.env['generic.tag'].search([
                                            ('category_id', '=', tag_category.id),
                                            ('sequence', '>=', slot_tag_id.sequence)
                                            ])
                            bottom_rack_locations = self.env['stock.location'].search([
                                        ('slot_tag_id', 'in', bottom_shelf_tags.ids),
                                        ('rack_tag_id','=',rack_tag_id.id)
                                        ])
                            
                            #stock in location
                            quants = self.env['stock.quant'].search([
                                        ('location_id', 'in', bottom_rack_locations.ids), 
                                        ('quantity', '>', 0),
                                    ])
                            #pending move line
                            mls = self.env['stock.move.line'].search([
                                    ('location_dest_id', 'in', bottom_rack_locations.ids),
                                    ('state', 'in', ('draft', 'waiting', 'confirmed', 'assigned', 'partially_available')),
                                    ('reserved_qty', '>', 0),
                            ])
                            ml_list = []
                            for ml in mls:
                                if str(ml.id) not in ml.move_line_exclusions:
                                    ml_list.append(ml)
                            if len(quants) > 0 or len(ml_list)>0: return False
                    
                
            positive_quant = self.quant_ids.filtered(lambda q: float_compare(q.quantity, 0, precision_rounding=q.product_id.uom_id.rounding) > 0)
            # check if only allow new product when empty
            if self.storage_category_id.allow_new_product == "empty" and positive_quant:
                return False
            # check if only allow same product
            if self.storage_category_id.allow_new_product == "same" and positive_quant and positive_quant.product_id != product:
                return False
        return True