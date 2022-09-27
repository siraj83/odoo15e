# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from .test_common import TestSignCommon
from odoo.addons.sign.controllers.main import Sign
from odoo.addons.website.tools import MockRequest
from odoo.tests import tagged

@tagged('post_install', '-at_install')
class TestSignController(TestSignCommon):
    def setUp(self):
        super().setUp()
        self.SignController = Sign()

    # test float auto_field display
    def test_sign_controller_float(self):
        sign_request = self.single_role_sign_request
        text_type = self.env['sign.item.type'].search([('name', '=', 'Text')])
        # the partner_latitude expects 7 zeros of decimal precision
        text_type.auto_field = 'partner_latitude'
        token_a = self.env["sign.request.item"].search([('sign_request_id', '=', sign_request.id)]).access_token
        with MockRequest(sign_request.env):
            values = self.SignController.get_document_qweb_context(sign_request.id, token=token_a)
            sign_type = list(filter(lambda sign_type: sign_type["name"] == "Text", values["sign_item_types"]))[0]
            latitude = sign_type["auto_field"]
            self.assertEqual(latitude, "0.0000000")

    # test monetary auto_field display
    def test_sign_controller_monetary(self):
        sign_request = self.single_role_sign_request
        text_type = self.env['sign.item.type'].search([('name', '=', 'Text')])
        # no monetary field is set on res.partner with only the sign module
        # credit is added in the account module and the test should not be
        # run if this module is not installed
        if 'credit' not in self.partner_id:
            return
        # we set the text type defaut value with the partner.credit
        text_type.auto_field = 'credit'
        monetary_field = self.partner_id._fields['credit']
        monetary_field.currency_field = 'currency_id'
        # we set the partner currency as the euro and change its precison to 5 decimals
        euro_currency = self.env['res.currency'].search([('name', '=', 'EUR')], limit=1)
        self.partner_id.currency_id = euro_currency
        euro_currency.rounding = 0.00001
        token_a = self.env["sign.request.item"].search([('sign_request_id', '=', sign_request.id)]).access_token
        with MockRequest(sign_request.env):
            values = self.SignController.get_document_qweb_context(sign_request.id, token=token_a)
            sign_type = list(filter(lambda sign_type: sign_type["name"] == "Text", values["sign_item_types"]))[0]
            credit = sign_type["auto_field"]
            self.assertEqual(credit, "0.00000")

    # test auto_field display with wrong partner field
    def test_sign_controller_dummy_fields(self):
        sign_request = self.single_role_sign_request
        text_type = self.env['sign.item.type'].search([('name', '=', 'Text')])
        # we set a dummy field
        text_type.auto_field = 'this_is_not_a_partner_field'
        token_a = self.env["sign.request.item"].search([('sign_request_id', '=', sign_request.id)]).access_token
        with MockRequest(sign_request.env):
            values = self.SignController.get_document_qweb_context(sign_request.id, token=token_a)
            sign_type = list(filter(lambda sign_type: sign_type["name"] == "Text", values["sign_item_types"]))[0]
            dummy_value = sign_type["auto_field"]
            self.assertEqual(dummy_value, "")
