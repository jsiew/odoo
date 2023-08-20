# -*- coding: utf-8 -*-
from odoo import _, api, models
from odoo.exceptions import UserError
class StockMoveLine(models.Model):
    _inherit = "stock.move"
    
    @api.ondelete(at_uninstall=False)
    def _unlink_if_draft_or_cancel(self):
        if any(move.state not in ('draft', 'cancel', 'assigned') for move in self):
            raise UserError(_('You can only delete draft, assigned or cancelled moves.'))