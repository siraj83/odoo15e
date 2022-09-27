# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.tools.translate import _


class AccountTax(models.Model):
    _inherit = 'account.tax'

    identification_letter = fields.Selection([('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D')], compute='_compute_identification_letter')

    @api.depends('amount_type', 'amount')
    def _compute_identification_letter(self):
        for rec in self:
            if rec.type_tax_use == "sale" and (rec.amount_type == "percent" or rec.amount_type == "group"):
                if rec.amount == 21:
                    rec.identification_letter = "A"
                elif rec.amount == 12:
                    rec.identification_letter = "B"
                elif rec.amount == 6:
                    rec.identification_letter = "C"
                elif rec.amount == 0:
                    rec.identification_letter = "D"
                else:
                    rec.identification_letter = False
            else:
                rec.identification_letter = False


class pos_make_payment(models.TransientModel):
    _inherit = 'pos.make.payment'

    def check(self):
        order = self.env['pos.order'].browse(self.env.context.get('active_id'))

        if order.config_id.iface_fiscal_data_module:
            raise UserError(_("Adding additional payments to registered orders is not allowed."))

        return super(pos_make_payment, self).check()


class pos_blackbox_be_log(models.Model):
    _name = 'pos_blackbox_be.log'
    _description = 'Track every changes made while using the Blackbox'
    _order = 'id desc'

    user = fields.Many2one('res.users', readonly=True)
    action = fields.Selection([('create', 'create'), ('modify', 'modify'), ('delete', 'delete')], readonly=True)
    date = fields.Datetime(default=fields.Datetime.now, readonly=True)
    model_name = fields.Char(readonly=True)
    record_name = fields.Char(readonly=True)
    description = fields.Char(readonly=True)

    def create(self, values, action, model_name, record_name):
        if not self.env.context.get('install_mode'):
            log_values = {
                'user': self.env.uid,
                'action': action,
                'model_name': model_name,
                'record_name': record_name,
                'description': str(values)
            }

            return super(pos_blackbox_be_log, self).create(log_values)

        return None

    def write(self, values):
        raise UserError(_("Can't modify the log book."))

    @api.ondelete(at_uninstall=True)
    def unlink_if_modified(self):
        raise UserError(_("Can't modify the log book."))


class product_template(models.Model):
    _inherit = 'product.template'

    @api.model
    def create(self, values):
        self.env['pos_blackbox_be.log'].sudo().create(values, "create", self._name, values.get('name'))

        return super(product_template, self).create(values)

    @api.ondelete(at_uninstall=False)
    def unlink_if_workin_workout_deleted(self):
        work_in = self.env.ref("pos_blackbox_be.product_product_work_in", False).product_tmpl_id.id
        work_out = self.env.ref("pos_blackbox_be.product_product_work_in", False).product_tmpl_id.id

        for product in self.ids:
            if product == work_in or product == work_out:
                raise UserError(_('Deleting this product is not allowed.'))

        for product in self:
            self.env['pos_blackbox_be.log'].sudo().create({}, "delete", product._name, product.name)


class module(models.Model):
    _inherit = 'ir.module.module'

    def module_uninstall(self):
        for module_to_remove in self:
            if module_to_remove.name == "pos_blackbox_be":
                raise UserError(_("This module is not allowed to be removed."))

        return super(module, self).module_uninstall()


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def set_tax_on_work_in_out(self):
        existing_companies = self.env['res.company'].sudo().search([])
        for company in existing_companies:
            if company.chart_template_id == self.env.ref('l10n_be.l10nbe_chart_template'):
                work_in = self.env.ref('pos_blackbox_be.product_product_work_in')
                work_out = self.env.ref('pos_blackbox_be.product_product_work_out')
                taxes = self.env['account.tax'].sudo().with_context(active_test=False).search([('amount', '=', 0.0), ('type_tax_use', '=', 'sale'), ('name', '=', '0%'), ('company_id', '=', company.id)])
                if not taxes.active:
                    taxes.active = True
                work_in.with_company(company.id).write({'taxes_id': [(4, taxes.id)]})
                work_out.with_company(company.id).write({'taxes_id': [(4, taxes.id)]})


class AccountChartTemplate(models.Model):
    _inherit = "account.chart.template"

    def _load(self, sale_tax_rate, purchase_tax_rate, company):
        super(AccountChartTemplate, self)._load(sale_tax_rate, purchase_tax_rate, company)
        if self == self.env.ref('l10n_be.l10nbe_chart_template'):
            work_in = self.env.ref('pos_blackbox_be.product_product_work_in')
            work_out = self.env.ref('pos_blackbox_be.product_product_work_out')
            taxes = self.env['account.tax'].sudo().with_context(active_test=False).search([('amount', '=', 0.0), ('type_tax_use', '=', 'sale'), ('name', '=', '0%'), ('company_id', '=', company.id)])
            if not taxes.active:
                taxes.active = True
            work_in.with_context(install_mode=True).with_company(company.id).write({'taxes_id': [(4, taxes.id)]})
            work_out.with_context(install_mode=True).with_company(company.id).write({'taxes_id': [(4, taxes.id)]})


class PosDailyReport(models.TransientModel):
    _name = 'pos.daily.reports.wizard.be'
    _description = 'Point of Sale Daily Belgium Report'

    pos_session_id = fields.Many2one('pos.session')

    def generate_report(self):
        data = {'date_start': False, 'date_stop': False, 'config_ids': self.pos_session_id.config_id.ids,
                'session_ids': self.pos_session_id.ids}
        return self.env.ref('pos_blackbox_be.pos_daily_report_be').report_action([], data=data)


class ReportSaleDetails(models.AbstractModel):
    _inherit = 'report.point_of_sale.report_saledetails'

    @api.model
    def get_sale_details(self, date_start=False, date_stop=False, config_ids=False, session_ids=False):
        data = super(ReportSaleDetails, self).get_sale_details(date_start, date_stop, config_ids, session_ids)
        if session_ids:
            session = self.env['pos.session'].search([('id', 'in', session_ids)])
            if session.config_id.iface_fiscal_data_module:
                report_update = {
                    'isBelgium': session.config_id.iface_fiscal_data_module.id,
                    'cashier_name': session.user_id.name,
                    'insz_or_bis_number': session.user_id.insz_or_bis_number,
                    'state': session.state,
                    'NS_number': len(self.env['pos.order'].search([('session_id', "=", session.id)])),
                    'PF_number': len(self.env['pos.order_pro_forma_be'].search([('session_id', "=", session.id)])),
                    'PF_amount': session.get_total_proforma(),
                    'Discount_number': len(session.order_ids.filtered(lambda o: o.lines.filtered(lambda l: l.discount > 0))),
                    'Discount_amount': session.get_total_discount(),
                    'Correction_number': len(session.order_ids.filtered(lambda o: o.lines.filtered(lambda l: l.qty < 0))),
                    'Correction_amount': session.get_total_correction(),
                    'CashBoxStartAmount': session.cash_register_balance_start,
                    'CashBoxEndAmount': session.cash_register_balance_end_real,
                    'cashRegisterID': session.config_id.name,
                    'startAt': session.start_at,
                    'stopAt': session.stop_at,
                    'sequence': self.env['ir.sequence'].next_by_code(
                        'report.point_of_sale.report_saledetails.sequenceZ') if session.state == 'closed'
                    else self.env['ir.sequence'].next_by_code('report.point_of_sale.report_saledetails.sequenceX'),
                    'CompanyVAT': session.company_id.vat,
                    'fdmID': session.config_id.certifiedBlackboxIdentifier,
                    'invoiceList': session.get_invoice_total_list(),
                    'invoiceTotal': session.get_total_invoice(),
                    'CashBoxOpening': session.cash_box_opening_number
                }

                taxes = [
                    {
                        'identification_letter': 'A',
                        'name': '21%',
                        'base_amount': 0,
                        'tax_amount': 0,
                    },
                    {
                        'identification_letter': 'B',
                        'name': '12%',
                        'base_amount': 0,
                        'tax_amount': 0,
                    },
                    {
                        'identification_letter': 'C',
                        'name': '6%',
                        'base_amount': 0,
                        'tax_amount': 0,
                    },
                    {
                        'identification_letter': 'D',
                        'name': '0%',
                        'base_amount': 0,
                        'tax_amount': 0,
                    },
                ]

                for tax in data['taxes']:
                    amount = self.env['account.tax'].search([('name', '=', tax['name'])]).amount
                    if amount == 21:
                        taxes[0]['base_amount'] += tax['base_amount']
                        taxes[0]['tax_amount'] += tax['tax_amount']
                    elif amount == 12:
                        taxes[1]['base_amount'] += tax['base_amount']
                        taxes[1]['tax_amount'] += tax['tax_amount']
                    elif amount == 6:
                        taxes[2]['base_amount'] += tax['base_amount']
                        taxes[2]['tax_amount'] += tax['tax_amount']
                    else:
                        taxes[3]['base_amount'] += tax['base_amount']
                        taxes[3]['tax_amount'] += tax['tax_amount']

                data['taxes'] = taxes

                data.update(report_update)
        return data

    @api.model
    def _get_report_values(self, docids, data=None):
        data = dict(data or {})
        configs = self.env['pos.config'].browse(data['config_ids'])
        if 'session_ids' in data:
            data.update(self.get_sale_details(data['date_start'], data['date_stop'], configs.ids, data['session_ids']))
        else:
            data.update(self.get_sale_details(data['date_start'], data['date_stop'], configs.ids))
        return data
