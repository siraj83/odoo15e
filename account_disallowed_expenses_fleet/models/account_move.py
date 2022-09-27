# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.model
    def _get_tax_grouping_key_from_tax_line(self, tax_line):
        # EXTENDS account
        res = super()._get_tax_grouping_key_from_tax_line(tax_line)
        res['vehicle_id'] = tax_line.vehicle_id.id
        return res

    @api.model
    def _get_tax_grouping_key_from_base_line(self, base_line, tax_vals):
        # EXTENDS account
        res = super()._get_tax_grouping_key_from_base_line(base_line, tax_vals)
        res['vehicle_id'] = base_line.vehicle_id.id
        return res


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.onchange('vehicle_id')
    def _onchange_mark_recompute_taxes_fleet(self):
        ''' Make sure changing 'vehicle_id' on invoice lines triggers the recomputation of taxes. '''
        self._onchange_mark_recompute_taxes()

    @api.depends('account_id.disallowed_expenses_category_id')
    def _compute_need_vehicle(self):
        for record in self:
            record.need_vehicle = record.account_id.disallowed_expenses_category_id.sudo().car_category and record.move_id.move_type == 'in_invoice'
