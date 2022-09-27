# Part of Odoo. See LICENSE file for full copyright and licensing details

from datetime import datetime
from odoo import Command
from odoo.addons.industry_fsm_sale.tests.common import TestFsmFlowCommon, TestFsmFlowSaleCommon
from odoo.exceptions import UserError
from odoo.tests import new_test_user, tagged


@tagged('-at_install', 'post_install')
class TestFsmFlowSale(TestFsmFlowSaleCommon):
    def test_fsm_flow(self):
        # material
        self.assertFalse(self.task.material_line_product_count, "No product should be linked to a new task")
        with self.assertRaises(UserError, msg='Should not be able to get to material without customer set'):
            self.task.action_fsm_view_material()
        self.task.write({'partner_id': self.partner_1.id})
        self.assertFalse(self.task.task_to_invoice, "Nothing should be invoiceable on task")
        self.task.with_user(self.project_user).action_fsm_view_material()
        self.service_product_ordered.with_user(self.project_user).with_context({'fsm_task_id': self.task.id}).fsm_add_quantity()
        self.assertEqual(self.task.material_line_product_count, 1, "1 product should be linked to the task")
        self.service_product_ordered.with_user(self.project_user).with_context({'fsm_task_id': self.task.id}).fsm_add_quantity()
        self.assertEqual(self.task.material_line_product_count, 2, "2 product should be linked to the task")
        self.service_product_delivered.with_user(self.project_user).with_context({'fsm_task_id': self.task.id}).fsm_add_quantity()
        self.assertEqual(self.task.material_line_product_count, 3, "3 products should be linked to the task")
        self.service_product_delivered.with_user(self.project_user).with_context({'fsm_task_id': self.task.id}).fsm_remove_quantity()

        self.assertEqual(self.task.material_line_product_count, 2, "2 product should be linked to the task")

        self.service_product_delivered.with_user(self.project_user).with_context({'fsm_task_id': self.task.id}).fsm_add_quantity()

        self.assertEqual(self.task.material_line_product_count, 3, "3 product should be linked to the task")

        # timesheet
        values = {
            'task_id': self.task.id,
            'project_id': self.task.project_id.id,
            'date': datetime.now(),
            'name': 'test timesheet',
            'user_id': self.env.uid,
            'unit_amount': 0.25,
        }
        self.env['account.analytic.line'].create(values)
        self.assertEqual(self.task.material_line_product_count, 3, "Timesheet should not appear in material")

        # validation and SO
        self.assertFalse(self.task.fsm_done, "Task should not be validated")
        self.assertEqual(self.task.sale_order_id.state, 'draft', "Sale order should not be confirmed")
        self.task.with_user(self.project_user).action_fsm_validate()
        self.assertTrue(self.task.fsm_done, "Task should be validated")
        self.assertEqual(self.task.sale_order_id.state, 'sale', "Sale order should be confirmed")

        # invoice
        self.assertTrue(self.task.task_to_invoice, "Task should be invoiceable")
        invoice_ctx = self.task.action_create_invoice()['context']
        invoice_wizard = self.env['sale.advance.payment.inv'].with_context(invoice_ctx).create({})
        invoice_wizard.create_invoices()
        self.assertFalse(self.task.task_to_invoice, "Task should not be invoiceable")

        # quotation
        self.assertEqual(self.task.quotation_count, 1, "1 quotation should be linked to the task")
        quotation = self.env['sale.order'].search([('state', '!=', 'cancel'), ('task_id', '=', self.task.id)])
        self.assertEqual(self.task.action_fsm_view_quotations()['res_id'], quotation.id, "Created quotation id should be in the action")


# TODO: [XBO] move this class in new file.
# This test class has to be tested at install since the flow is modified in industry_fsm_stock
# where the SO gets confirmed as soon as a product is added in an FSM task which causes the
# tests of this class to fail
class TestFsmSaleWithMaterial(TestFsmFlowCommon):

    # If the test has to be run at install, it cannot inherit indirectly from accounttestinvoicingcommon.
    # So we have to setup the test data again here.
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.account_revenue = cls.env['account.account'].create([{'code': '1014040', 'name': 'A', 'user_type_id': cls.env.ref('account.data_account_type_revenue').id}])
        cls.account_expense = cls.env['account.account'].create([{'code': '101600', 'name': 'C', 'user_type_id': cls.env.ref('account.data_account_type_expenses').id}])
        cls.tax_sale_a = cls.env['account.tax'].create({
            'name': "tax_sale_a",
            'amount_type': 'percent',
            'type_tax_use': 'sale',
            'amount': 10.0,
        })
        cls.tax_purchase_a = cls.env['account.tax'].create({
            'name': "tax_purchase_a",
            'amount_type': 'percent',
            'type_tax_use': 'purchase',
            'amount': 10.0,
        })
        cls.product_a = cls.env['product.product'].create({
            'name': 'product_a',
            'uom_id': cls.env.ref('uom.product_uom_unit').id,
            'lst_price': 1000.0,
            'standard_price': 800.0,
            'property_account_income_id': cls.account_revenue.id,
            'property_account_expense_id': cls.account_expense.id,
            'taxes_id': [(6, 0, cls.tax_sale_a.ids)],
            'supplier_taxes_id': [(6, 0, cls.tax_purchase_a.ids)],
        })

    def test_change_product_selection(self):
        self.task.write({'partner_id': self.partner_1.id})
        product = self.service_product_ordered.with_context({'fsm_task_id': self.task.id})
        product.set_fsm_quantity(5)

        so = self.task.sale_order_id
        sol01 = so.order_line[-1]
        sol01.sequence = 10
        self.assertEqual(sol01.product_uom_qty, 5)

        # Manually add a line for the same product
        sol02 = self.env['sale.order.line'].create({
            'order_id': so.id,
            'product_id': product.id,
            'product_uom_qty': 3,
            'sequence': 20,
            'product_uom': product.uom_id.id,
            'task_id': self.task.id
        })
        product.sudo()._compute_fsm_quantity()
        self.assertEqual(sol02.product_uom_qty, 3)
        self.assertEqual(product.fsm_quantity, 8)

        product.set_fsm_quantity(2)
        product.sudo()._compute_fsm_quantity()
        self.assertEqual(product.fsm_quantity, 2)
        self.assertEqual(sol01.product_uom_qty, 0)
        self.assertEqual(sol02.product_uom_qty, 2)

    def test_fsm_sale_pricelist(self):
        product = self.product_a.with_context({"fsm_task_id": self.task.id})
        self.task.write({'partner_id': self.partner_1.id})
        pricelist = self.env['product.pricelist'].create({
            'name': 'Sale pricelist',
            'discount_policy': 'with_discount',
            'item_ids': [(0, 0, {
                'compute_price': 'formula',
                'base': 'list_price',  # based on public price
                'price_discount': 10,
                'min_quantity': 2,
                'product_id': product.id,
                'applied_on': '0_product_variant',
            })]
        })
        self.task._fsm_ensure_sale_order()
        self.task.sale_order_id.pricelist_id = pricelist

        self.assertEqual(product.fsm_quantity, 0)
        product.fsm_add_quantity()
        self.assertEqual(product.fsm_quantity, 1)

        order_line = self.task.sale_order_id.order_line.filtered(lambda l: l.name == "product_a")
        self.assertEqual(order_line.product_uom_qty, 1)
        self.assertEqual(order_line.price_unit, product.list_price)

        product.fsm_add_quantity()
        self.assertEqual(product.fsm_quantity, 2)
        self.assertEqual(order_line.product_uom_qty, 2)
        self.assertEqual(order_line.price_unit, product.list_price*0.9)

    def test_fsm_sale_timesheet_discount(self):
        product = self.product_a.with_context({"fsm_task_id": self.task.id})
        product.type = 'service'
        product.service_type = 'timesheet'
        # create pricelist a with discount included in price and with fixed product price on timesheet service product
        pricelist_a = self.env['product.pricelist'].create({
            'name': 'Sale pricelist a',
            'discount_policy': 'with_discount',
            'item_ids': [(0, 0, {
                'compute_price': 'fixed',
                'base': 'list_price',  # based on public price
                'fixed_price': 10.0,
                'product_id': product.id,
                'applied_on': '1_product',
                'product_tmpl_id': product.product_tmpl_id.id,
            })]
        })
        # pricelist b to show discount, formula based on pricelist 1 and a discount for the same product.
        pricelist_b = self.env['product.pricelist'].create({
            'name': 'Sale pricelist b',
            'discount_policy': 'without_discount',
            'item_ids': [(0, 0, {
                'compute_price': 'formula',
                'base': 'pricelist',  # based on public price
                'base_pricelist_id':pricelist_a.id,
                'price_discount': 50.0,
                'product_id': product.id,
                'applied_on': '1_product',
                'product_tmpl_id': product.product_tmpl_id.id,
            })]
        })
        # Assign pricelist b to partner_1
        self.partner_1.property_product_pricelist = pricelist_b

        # create a test user to add timesheet
        self.user_employee_timesheet = new_test_user(self.env, login='marcel', groups='industry_fsm.group_fsm_user,product.group_discount_per_so_line')
        self.task.project_id.timesheet_product_id = product
        self.task.write({'partner_id': self.partner_1.id})
        self.assertEqual(len(self.task.sudo().timesheet_ids), 0, 'There is no timesheet associated to the task')
        self.env['account.analytic.line'].with_user(self.user_employee_timesheet).create({
            'name': '/',
            'project_id': self.fsm_project.id,
            'task_id': self.task.id,
            'unit_amount': 1.0
        })

        self.task.with_user(user=self.user_employee_timesheet.id).action_fsm_validate()
        self.assertTrue(self.task.fsm_done, "Task should be validated")
        self.assertEqual(self.task.sale_order_id.state, 'sale', "Sale order should be confirmed")
        order_line = self.task.sale_order_id.order_line.filtered(lambda l: l.product_id == product)
        self.assertEqual(order_line.price_unit, 10.0)
        self.assertEqual(order_line.price_subtotal, 5.0, "Discount was not applied")
        self.assertEqual(order_line.discount, 50.0, "Discount was not applied")

    def test_invoicing_flow(self):
        self.service_product_ordered.write({
            'detailed_type': 'service',
            'service_policy': 'ordered_timesheet',
        })
        self.service_product_delivered.write({
            'detailed_type': 'service',
            'service_policy': 'delivered_timesheet',
        })
        self.fsm_project.write({
            'timesheet_product_id': self.service_product_delivered.id,
        })
        self.task.write({
            'partner_id': self.partner_1,
        })
        self.assertFalse(self.task.sale_order_id)
        self.assertFalse(self.task.sale_line_id)
        self.assertFalse(self.task.task_to_invoice)
        self.service_product_ordered.with_user(self.project_user).with_context({'fsm_task_id': self.task.id}).set_fsm_quantity(1.0)
        self.assertEqual(self.task.sale_order_id.state, 'draft')
        self.assertEqual(len(self.task.sale_order_id.order_line), 1)

        first_order_line = self.task.sale_order_id.order_line
        self.assertEqual(first_order_line.product_uom_qty, 1.0)
        self.assertFalse(self.task.task_to_invoice)
        self.assertFalse(self.task.display_create_invoice_primary)
        self.assertFalse(self.task.sale_line_id)

        self.task.sale_order_id.write({
            'order_line': [
                Command.create({
                    'product_id': self.service_timesheet.id,
                    'product_uom_qty': 1.0,
                    'name': '/',
                }),
            ]
        })

        self.task.sale_order_id.action_confirm()
        self.assertEqual(len(self.task.sale_order_id.order_line), 2)
        service_timesheet_order_line = self.task.sale_order_id.order_line.filtered(lambda order_line: order_line.product_id == self.service_timesheet)
        self.task.write({
            'timesheet_ids': [
                Command.create({
                    'name': '/',
                    'unit_amount': 0.5,
                    'project_id': self.task.project_id.id,
                }),
                Command.create({
                    'name': '/',
                    'unit_amount': 0.5,
                    'project_id': self.task.project_id.id,
                }),
                Command.create({
                    'name': '/',
                    'unit_amount': 1.0,
                    'so_line': service_timesheet_order_line.id,
                    'is_so_line_edited': True,
                    'project_id': self.task.project_id.id,
                }),
            ]
        })

        self.task.action_fsm_validate()
        self.assertEqual(len(self.task.timesheet_ids.so_line), 2)
        self.assertEqual(self.task.sale_order_id.order_line.mapped('qty_delivered'), [1.0] * 3)
        self.assertEqual(self.task.sale_line_id.product_id, self.service_product_delivered)
        self.assertEqual(self.task.sale_order_id.state, 'sale')
        self.assertEqual(len(self.task.sale_order_id.order_line), 3)
        second_order_line = self.task.sale_line_id
        self.assertEqual(second_order_line.project_id, self.fsm_project)
        self.assertEqual(second_order_line.task_id, self.task)
        self.assertTrue(second_order_line.is_service)
        self.assertEqual(second_order_line.qty_delivered_method, 'timesheet')
        self.assertTrue(self.task.task_to_invoice)
        self.assertTrue(self.task.display_create_invoice_primary)
        self.task.sale_order_id._create_invoices()
        self.assertEqual(self.task.invoice_count, 1)
        self.assertFalse(self.task.display_create_invoice_primary)
        self.service_product_ordered.with_user(self.project_user).with_context({'fsm_task_id': self.task.id}).fsm_add_quantity()
        self.assertTrue(self.task.display_create_invoice_primary)
        self.task.sale_order_id._create_invoices()
        self.assertEqual(self.task.invoice_count, 2)
        self.assertFalse(self.task.display_create_invoice_primary)
