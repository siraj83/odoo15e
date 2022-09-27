# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from dateutil import parser


class PosOrderLineProFormaBe(models.Model):
    _name = 'pos.order_line_pro_forma_be'  # needs to be a new class
    _inherit = 'pos.order.line'
    _description = 'Order line of a pro forma order'

    order_id = fields.Many2one('pos.order_pro_forma_be')

    @api.model
    def create(self, values):
        # the pos.order.line create method consider 'order_id' is a pos.order
        # override to bypass it and generate a name
        if values.get('order_id') and not values.get('name'):
            name = self.env['pos.order_pro_forma_be'].browse(values['order_id']).name
            values['name'] = "%s-%s" % (name, values.get('id'))
        return super(PosOrderLineProFormaBe, self).create(values)


class PosOrderProFormaBe(models.Model):
    _name = 'pos.order_pro_forma_be'
    _description = 'Model for pro forma order'

    def _default_session(self):
        so = self.env['pos.session']
        session_ids = so.search([('state', '=', 'opened'), ('user_id', '=', self.env.uid)])
        return session_ids and session_ids[0] or False

    def _default_pricelist(self):
        session_ids = self._default_session()
        if session_ids:
            session_record = self.env['pos.session'].browse(session_ids.id)
            return session_record.config_id.pricelist_id or False
        return False

    name = fields.Char('Order Ref', readonly=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env['res.users'].browse(self.env.uid).company_id.id, readonly=True)
    date_order = fields.Datetime('Order Date', readonly=True)
    create_date = fields.Datetime(string="Pro Forma Creation")
    user_id = fields.Many2one('res.users', 'Salesman', help="Person who uses the cash register. It can be a reliever, a student or an interim employee.", readonly=True)
    lines = fields.One2many('pos.order_line_pro_forma_be', 'order_id', 'Order Lines', readonly=True, copy=True)
    pos_reference = fields.Char('Receipt Ref', readonly=True)
    session_id = fields.Many2one('pos.session', 'Session', readonly=True)
    partner_id = fields.Many2one('res.partner', 'Customer', readonly=True)
    config_id = fields.Many2one('pos.config', related='session_id.config_id', readonly=True)
    pricelist_id = fields.Many2one('product.pricelist', 'Pricelist', default=_default_pricelist, readonly=True)
    fiscal_position_id = fields.Many2one('account.fiscal.position', 'Fiscal Position', readonly=True)
    table_id = fields.Many2one('restaurant.table', 'Table', readonly=True)
    currency_id = fields.Many2one(related='session_id.currency_id')
    employee_id = fields.Many2one('hr.employee')
    amount_total = fields.Float(readonly=True)

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

    plu_hash = fields.Char(help="Eight last characters of PLU hash", readonly=True)
    pos_version = fields.Char(help="Version of Odoo that created the order", readonly=True)
    pos_production_id = fields.Char(help="Unique ID of Odoo that created this order", readonly=True)
    terminal_id = fields.Char(help="Unique ID of the POS that created this order", readonly=True)

    def _set_log_description(self, order):
        lines = "Lignes de commande: "
        if order.lines:
            lines += "\n* " + "\n* ".join([
                "%s x %s: %s" % (l.qty, l.product_id.name, l.price_subtotal_incl)
                for l in order.lines
            ])
        description = """
        PRO FORMA SALES
        Date: {create_date}
        Réf: {pos_reference}
        Vendeur: {user_id}
        {lines}
        Total: {total}
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
            total=order.amount_total,
            pos_reference=order.pos_reference,
            hash=order.plu_hash,
            pos_version=order.pos_version,
            ticket_counters=order.blackbox_ticket_counters,
            fdm_id=order.blackbox_unique_fdm_production_number,
            pos_id=order.pos_production_id,
            fdmIdentifier=order.config_id.certifiedBlackboxIdentifier
        )
        return description

    def set_values(self, ui_order):
        return {
            'user_id': ui_order['user_id'] or False,
            'session_id': ui_order['pos_session_id'],
            'pos_reference': ui_order['name'],
            'lines': [self.env['pos.order_line_pro_forma_be']._order_line_fields(l) for l in ui_order['lines']] if ui_order['lines'] else False,
            'partner_id': ui_order['partner_id'] or False,
            'date_order': parser.parse(ui_order['creation_date']).strftime("%Y-%m-%d %H:%M:%S"),
            'amount_total': ui_order.get('amount_total'),
            'fiscal_position_id': ui_order['fiscal_position_id'],
            'blackbox_date': ui_order.get('blackbox_date'),
            'blackbox_time': ui_order.get('blackbox_time'),
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
            'table_id': ui_order.get('table_id'),
            'employee_id': ui_order.get('employee_id')
        }


    @api.model
    def create_from_ui(self, orders):
        for ui_order in orders:
            values = self.set_values(ui_order)
            # set name based on the sequence specified on the config
            session = self.env['pos.session'].browse(values['session_id'])
            values['name'] = session.config_id.sequence_id._next()

            order = self.create(values)
            description = self._set_log_description(order)
            self.env["pos_blackbox_be.log"].sudo().create(description, "create", self._name, order.pos_reference)
