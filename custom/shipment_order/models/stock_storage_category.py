# -*- coding: utf-8 -*-
from odoo import _, api, fields, tools, models
class StorageCategory(models.Model):
    _inherit = "stock.storage.category"

    max_total_capacity = fields.Float('Maximum Total Capacity',help='Total maximum quantity of all products that can be stored. Leave blank for no limit.')