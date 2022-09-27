# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.tools.translate import _

from itertools import groupby


class pos_session(models.Model):
    _inherit = 'pos.session'

    pro_forma_order_ids = fields.One2many('pos.order_pro_forma_be', 'session_id')

    total_sold = fields.Monetary(compute='_compute_total_sold')
    total_pro_forma = fields.Monetary(compute='_compute_total_pro_forma')
    total_base_of_measure_tax_a = fields.Monetary(compute='_compute_total_tax')
    total_base_of_measure_tax_b = fields.Monetary(compute='_compute_total_tax')
    total_base_of_measure_tax_c = fields.Monetary(compute='_compute_total_tax')
    total_base_of_measure_tax_d = fields.Monetary(compute='_compute_total_tax')
    total_tax_a = fields.Monetary(compute='_compute_total_tax')
    total_tax_b = fields.Monetary(compute='_compute_total_tax')
    total_tax_c = fields.Monetary(compute='_compute_total_tax')
    total_tax_d = fields.Monetary(compute='_compute_total_tax')
    cash_box_opening_number = fields.Integer(help='Count the number of cashbox opening during the session')
    users_clocked_ids = fields.Many2many(
        'res.users',
        'users_session_clocking_info',
        string='Users Clocked In',
        help='This is a technical field used for tracking the status of the session for each users.',
    )
    employees_clocked_ids = fields.Many2many(
        'hr.employee',
        'employees_session_clocking_info',
        string='Employees Clocked In',
        help='This is a technical field used for tracking the status of the session for each employees.',
    )

    @api.depends('order_ids')
    def _compute_total_tax(self):
        for rec in self:
            rec.total_base_of_measure_tax_a = 0
            rec.total_base_of_measure_tax_b = 0
            rec.total_base_of_measure_tax_c = 0
            rec.total_base_of_measure_tax_d = 0
            for order in rec.order_ids:
                rec.total_base_of_measure_tax_a += order.blackbox_tax_category_a
                rec.total_base_of_measure_tax_b += order.blackbox_tax_category_b
                rec.total_base_of_measure_tax_c += order.blackbox_tax_category_c
                rec.total_base_of_measure_tax_d += order.blackbox_tax_category_d
            # compute the tax totals
            currency = self.env['res.currency'].browse(rec.currency_id.id)
            rec.total_tax_a = currency.round(rec.total_base_of_measure_tax_a * 0.21)
            rec.total_tax_b = currency.round(rec.total_base_of_measure_tax_b * 0.12)
            rec.total_tax_c = currency.round(rec.total_base_of_measure_tax_c * 0.06)
            rec.total_tax_d = 0

    @api.depends('order_ids')
    def _compute_amount_of_vat_tickets(self):
        for rec in self:
            rec.amount_of_vat_tickets = len(rec.order_ids)

    @api.depends('order_ids')
    def _compute_corrections(self):
        for rec in self:
            rec.amount_of_corrections = 0
            rec.total_corrections = 0
            for order in rec.order_ids:
                for line in order.lines:
                    if line.price_subtotal_incl < 0:
                        rec.amount_of_corrections += 1
                        rec.total_corrections += line.price_subtotal_incl

    def get_user_session_work_status(self, user_id):
        if self.config_id.module_pos_hr and user_id in self.employees_clocked_ids.ids:
            return True
        elif not self.config_id.module_pos_hr and user_id in self.users_clocked_ids.ids:
            return True
        return False

    def increase_cash_box_opening_counter(self):
        self.cash_box_opening_number += 1

    def set_user_session_work_status(self, user_id, status):
        context = 'employees_clocked_ids' if self.config_id.module_pos_hr else 'users_clocked_ids'
        if status:
            self.write({context: [(4, user_id)]})
        else:
            self.write({context: [(3, user_id)]})
        return self[context].ids

    def action_pos_session_closing_control(self, balancing_account=False, amount_to_balance=0, bank_payment_method_diffs=None):
        # The government does not want PS orders that have not been
        # finalized into an NS before we close a session
        pro_forma_orders = self.env['pos.order_pro_forma_be'].search([('session_id', '=', self.id)])
        regular_orders = self.env['pos.order'].search([('session_id', '=', self.id)])

        # we can link pro forma orders to regular orders using their pos_reference
        pro_forma_orders = {order.pos_reference for order in pro_forma_orders}
        regular_orders = {order.pos_reference for order in regular_orders}
        non_finalized_orders = pro_forma_orders.difference(regular_orders)

        if non_finalized_orders:
            raise UserError(_("Your session still contains open orders (%s). Please close all of them first.") % ', '.join(non_finalized_orders))

        return super(pos_session, self).action_pos_session_closing_control(balancing_account, amount_to_balance, bank_payment_method_diffs)

    def get_user_report_data(self):
        def sorted_key_insz(order):
            order.ensure_one()
            if order.employee_id:
                insz = order.employee_id.insz_or_bis_number
            else:
                insz = order.user_id.insz_or_bis_number
            return [insz, order.date_order]

        def groupby_key_insz(order):
            if order.employee_id:
                insz = order.employee_id.insz_or_bis_number
            else:
                insz = order.user_id.insz_or_bis_number
            return [insz]

        data = {}
        currency = self.env['res.currency'].browse(self.currency_id.id)

        for k, g in groupby(sorted(self.order_ids, key=sorted_key_insz), key=groupby_key_insz):
            i = 0
            insz = k[0]
            data[insz] = []
            for order in g:
                if order.plu_hash == 'cf44878a':
                    data[insz].append({
                            'login': order.employee_id.name if order.employee_id else order.user_id.name,
                            'insz_or_bis_number': order.employee_id.insz_or_bis_number if order.employee_id else order.user_id.insz_or_bis_number,
                            'revenue': 0,
                            'revenue_per_category': {},
                            'first_ticket_time': order.blackbox_pos_receipt_time,
                            'last_ticket_time': False,
                            'fdmIdentifier': order.config_id.certifiedBlackboxIdentifier,
                            'cash_rounding_applied': 0
                        })

                data[insz][i]['revenue'] += order.amount_paid
                data[insz][i]['cash_rounding_applied'] += currency.round(order.amount_total - order.amount_paid)
                total_sold_per_category = {}
                for line in order.lines:
                    category_name = line.product_id.pos_categ_id.name or "None"
                    if category_name in total_sold_per_category:
                        total_sold_per_category[category_name] += line.price_subtotal_incl
                    else:
                        total_sold_per_category[category_name] = line.price_subtotal_incl

                data[insz][i]['revenue_per_category'] = list(total_sold_per_category.items())

                if order.plu_hash == '142164ed':
                    data[insz][i]['last_ticket_time'] = order.blackbox_pos_receipt_time
                    i = i + 1
        return data

    def action_report_journal_file(self):
        self.ensure_one()
        pos = self.config_id
        if not pos.iface_fiscal_data_module:
            raise UserError(_("PoS %s is not a certified PoS", pos.name))
        return {
            'type': 'ir.actions.act_url',
            'url': "/journal_file/" + str(pos.certifiedBlackboxIdentifier),
            'target': 'self',
        }

    def get_total_discount(self):
        amount = 0
        for line in self.env['pos.order.line'].search([('order_id', 'in', self.order_ids.ids), ('discount', '>', 0)]):
            normal_price = line.qty * line.price_unit
            normal_price = normal_price + (normal_price / 100 * line.tax_ids.amount)
            amount += normal_price - line.price_subtotal_incl

        return amount

    def get_total_correction(self):
        total_corrections = 0
        for order in self.order_ids:
            for line in order.lines:
                if line.price_subtotal_incl < 0:
                    total_corrections += line.price_subtotal_incl

        return total_corrections

    def get_total_proforma(self):
        amount_total = 0
        for pf in self.pro_forma_order_ids:
            amount_total += pf.amount_total

        return amount_total

    def get_invoice_total_list(self):
        invoice_list = []
        for order in self.order_ids.filtered(lambda o: o.is_invoiced):
            invoice = {
                'total': order.account_move.amount_total,
                'name': order.account_move.highest_name
            }
            invoice_list.append(invoice)

        return invoice_list

    def get_total_invoice(self):
        amount = 0
        for order in self.order_ids.filtered(lambda o: o.is_invoiced):
            amount += order.amount_paid

        return amount
