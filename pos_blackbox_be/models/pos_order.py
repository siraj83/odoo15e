# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.tools.translate import _
from datetime import datetime


class PosOrder(models.Model):
    _inherit = 'pos.order'

    blackbox_date = fields.Char("Fiscal Data Module date", help="Date returned by the Fiscal Data Module.", readonly=True)
    blackbox_time = fields.Char("Fiscal Data Module time", help="Time returned by the Fiscal Data Module.", readonly=True)
    blackbox_pos_receipt_time = fields.Datetime("Receipt time", readonly=True)
    blackbox_ticket_counters = fields.Char("Fiscal Data Module ticket counters", help="Ticket counter returned by the Fiscal Data Module (format: counter / total event type)", readonly=True)
    blackbox_unique_fdm_production_number = fields.Char("Fiscal Data Module ID", help="Unique ID of the blackbox that handled this order", readonly=True)
    blackbox_vsc_identification_number = fields.Char("VAT Signing Card ID", help="Unique ID of the VAT signing card that handled this order", readonly=True)
    blackbox_signature = fields.Char("Electronic signature", help="Electronic signature returned by the Fiscal Data Module", readonly=True)
    blackbox_tax_category_a = fields.Float(readonly=True)
    blackbox_tax_category_b = fields.Float(readonly=True)
    blackbox_tax_category_c = fields.Float(readonly=True)
    blackbox_tax_category_d = fields.Float(readonly=True)
    receipt_type = fields.Char(readonly=True)

    plu_hash = fields.Char(help="Eight last characters of PLU hash")
    pos_version = fields.Char(help="Version of Odoo that created the order")
    pos_production_id = fields.Char(help="Unique ID of Odoo that created this order")
    terminal_id = fields.Char(help="Unique ID of the terminal that created this order")

    def _set_log_description(self, order):
        currency = self.env['res.currency'].browse(self.currency_id.id)
        lines = "Lignes de commande: "
        if order.lines:
            lines += "\n* " + "\n* ".join([
                "%s x %s: %s" % (l.qty, l.product_id.name, l.price_subtotal_incl) + (" (disc: %s" % l.discount + "%)" if l.discount else "")
                for l in order.lines
            ])
        description = """
        NORMAL SALES
        Date: {create_date}
        Réf: {pos_reference}
        Vendeur: {user_id}
        {lines}
        Total: {total}
        Arrondi: {rounding_applied}
        Compteur Ticket: {ticket_counters}
        Hash: {hash}
        POS Version: {pos_version}
        FDM ID: {fdm_id}
        POS ID: {pos_id}
        FDM Identifier: {fdmIdentifier}
        """.format(
            create_date=order.create_date,
            user_id=order.employee_id.name or order.user_id.name,
            lines=lines,
            total=order.amount_paid,
            pos_reference=order.pos_reference,
            hash=order.plu_hash,
            pos_version=order.pos_version,
            ticket_counters=order.blackbox_ticket_counters,
            fdm_id=order.blackbox_unique_fdm_production_number,
            pos_id=order.config_id.name,
            fdmIdentifier=order.config_id.certifiedBlackboxIdentifier,
            rounding_applied=currency.round(order.amount_total - order.amount_paid)
        )
        return description

    @api.ondelete(at_uninstall=False)
    def unlink_if_blackboxed(self):
        for order in self:
            if order.config_id.iface_fiscal_data_module:
                raise UserError(_('Deleting of registered orders is not allowed.'))

    def write(self, values):
        for order in self:
            if order.config_id.iface_fiscal_data_module and order.state != 'draft':
                white_listed_fields = ['state', 'account_move', 'picking_id',
                                       'invoice_id']

                for field in values:
                    if field not in white_listed_fields:
                        raise UserError(_("Modifying registered orders is not allowed."))

            if values.get('state') and values['state'] == 'paid':
                description = self._set_log_description(order)
                self.env["pos_blackbox_be.log"].sudo().create(description, "create", self._name, order.pos_reference)

        return super(PosOrder, self).write(values)

    @api.model
    def _order_fields(self, ui_order):
        fields = super(PosOrder, self)._order_fields(ui_order)

        date = ui_order.get('blackbox_date')
        time = ui_order.get('blackbox_time')

        fields.update({
            'blackbox_date': date,
            'blackbox_time': time,
            'blackbox_pos_receipt_time': datetime.strptime(date + ' ' + time, '%d-%m-%Y %H:%M:%S') if date else False,
            'blackbox_ticket_counters': ui_order.get('blackbox_ticket_counters'),
            'blackbox_unique_fdm_production_number': ui_order.get('blackbox_unique_fdm_production_number'),
            'blackbox_vsc_identification_number': ui_order.get('blackbox_vsc_identification_number'),
            'blackbox_signature': ui_order.get('blackbox_signature'),
            'blackbox_tax_category_a': ui_order.get('blackbox_tax_category_a'),
            'blackbox_tax_category_b': ui_order.get('blackbox_tax_category_b'),
            'blackbox_tax_category_c': ui_order.get('blackbox_tax_category_c'),
            'blackbox_tax_category_d': ui_order.get('blackbox_tax_category_d'),
            'plu_hash': ui_order.get('blackbox_plu_hash'),
            'pos_version': ui_order.get('blackbox_pos_version'),
            'pos_production_id': ui_order.get('blackbox_pos_production_id'),
            'terminal_id': ui_order.get('blackbox_terminal_id'),
        })

        return fields

    @api.model
    def create_from_ui(self, orders, draft=False):
        pro_forma_orders = [order['data'] for order in orders if order['data'].get('receipt_type') == "PS"]
        regular_orders = [order for order in orders if not order['data'].get('receipt_type') == "PS"]
        self.env['pos.order_pro_forma_be'].create_from_ui(pro_forma_orders)
        return super(PosOrder, self).create_from_ui(regular_orders, draft)


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    vat_letter = fields.Selection([('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D')])

    def write(self, values):
        if values.get('vat_letter'):
            raise UserError(_("Can't modify fields related to the Fiscal Data Module."))

        return super(PosOrderLine, self).write(values)
