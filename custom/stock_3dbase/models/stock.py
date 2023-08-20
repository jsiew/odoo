# © 2020 OpenIndustry.it
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_colors = {
    0: "#FFFFFF",  # white
    1: "#F06050",  # red
    2: "#F4A460",  # orange
    3: "#F7CD1F",  # yellow
    4: "#6CC1ED",  # light blue
    5: "#814968",  # dark purple
    6: "#EB7E7F",  # salmon pink
    7: "#2C8397",  # medium blue
    8: "#475577",  # dark blue
    9: "#D6145F",  # fushia
    10: "#30C381",  # green
    11: "#9365B8",  # purple
}


class StockLocationTag(models.Model):
    _description = "Location Tags"
    _name = "stock.location.tag"
    _order = "name"

    name = fields.Char(
        string="Tag Name",
        required=True,
        translate=True,
    )
    color = fields.Integer(
        string="Color Index",
        default=0,
    )
    color_hex = fields.Char(
        string="Color",
        compute="_compute_color_hex",
    )
    opacity = fields.Integer(
        string="Opacity",
        default=500,
    )

    @api.depends("color")
    def _compute_color_hex(self):
        for tag in self:
            tag.color_hex = _colors[tag.color]


class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    spacex = fields.Integer(
        string="Depth (X)",
        default=0,
    )
    spacey = fields.Integer(
        string="Width (Y)",
        default=0,
    )
    spacez = fields.Integer(
        string="Height (Z)",
        default=0,
    )
    planimetry_image = fields.Binary(
        string="Planimetry Image",
        help="Warehouse planimetry image",
    )

    count_sl = fields.Integer(
        string="Count Stock Locations",
        compute="_compute_count_sl",
    )

    def _compute_count_sl(self):
        for wh in self:
            wh.count_sl = self.env["stock.location"].search_count(
                [
                    ("warehouse_id", "=", wh.id),
                    ("usage", "=", "internal"),
                ]
            )

    @api.constrains("view_location_id")
    def _check_view_location_id(self):
        for wh in self:
            duplicate = self.search(
                [
                    ("id", "!=", wh.id),
                    ("view_location_id", "=", wh.view_location_id.id),
                ],
                limit=1,
            )
            if duplicate:
                raise ValidationError(
                    _("Location %s is used for warehouse '%s'")
                    % (wh.view_location_id.name, duplicate.name)
                )

    def action_open_stock_locations(self):
        action = self.env.ref("stock_3dbase.act_warehouse_stock_locations").read()[0]
        action["domain"] = [("warehouse_id", "=", self.id)]
        action["context"] = {"search_default_in_location": 1}
        return action


class StockLocationShape(models.Model):
    _name = "stock.location.shape"
    _description = "Location Shape"
    _order = "name"

    name = fields.Char(
        string="Shape",
    )
    shape_file = fields.Binary(
        string="Shape File",
        attachment=True,
    )


class StockLocation(models.Model):
    _inherit = "stock.location"

    barcode = fields.Char(
        string="Barcode",
    )
    posx = fields.Integer(
        string="Pos (X)",
        default=0,
    )
    posy = fields.Integer(
        string="Pos (Y)",
        default=0,
    )
    posz = fields.Integer(
        string="Pos (Z)",
        default=0,
    )
    sizex = fields.Integer(
        string="Size (X)",
        default=0,
    )
    sizey = fields.Integer(
        string="Size (Y)",
        default=0,
    )
    sizez = fields.Integer(
        string="Size (Z)",
        default=0,
    )
    tag_ids = fields.Many2many(
        comodel_name="stock.location.tag",
        column1="location_id",
        column2="tag_id",
        string="View Tags",
    )
    rotx = fields.Integer(
        string="Rotation (X)",
        default=0,
    )
    roty = fields.Integer(
        string="Rotation (Y)",
        default=0,
    )
    rotz = fields.Integer(
        string="Rotation (Z)",
        default=0,
    )
    scale_factor = fields.Float(
        string="Scale Factor",
        default=1.0,
    )
    shape_id = fields.Many2one(
        string="Location Shape",
        comodel_name="stock.location.shape",
    )
    gltf_3d_model = fields.Binary(
        string="3D model",
        attachment=True,
        help="Load a model in GLTF 2.0 format",
    )
    color = fields.Char(
        string="Color",
        compute="_compute_3d_attributes",
    )
    opacity = fields.Integer(
        string="Opacity",
        default=500,
        compute="_compute_3d_attributes",
    )
    shape_file = fields.Binary(
        string="Shape File",
        compute="_compute_3d_attributes",
    )

    @api.depends("tag_ids", "shape_id")
    def _compute_3d_attributes(self):
        for location in self:
            if self.env.context.get("force_color", False):
                location.color = self.env.context.get("force_color")
            else:
                quants = self.env["stock.quant"].search(
                    [("location_id", "=", location.id),
                    ("quantity", ">", 0)], limit = 1
                )
                if location.tag_ids:
                    color = _colors[location.tag_ids[0].color]
                elif quants.id: color = "#05471C"
                else: color = "#8F8F8F"
                location.color = color
                """ location.color = (
                    _colors[location.tag_ids[0].color]
                    if location.tag_ids
                    else "#8F8F8F"
                ) """
            if self.env.context.get("force_opacity", False):
                location.opacity = int(self.env.context.get("force_opacity"))
            else:
                location.opacity = (
                    location.tag_ids[0].opacity if location.tag_ids else 500
                )
            location.shape_file = (
                location.shape_id.shape_file if location.shape_id else False
            )
