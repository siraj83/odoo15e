# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class XmlPolizasExportWizard(models.TransientModel):
    _inherit = 'l10n_mx_xml_polizas.xml_polizas_wizard'

    def _get_move_export_data(self, accounts_results):
        # Retrieve extra data for CompNal node

        mx_move_vals = {}
        AccountMove = self.env['account.move']
        for results in accounts_results:
            lines_data = results[1][0].get('lines', [])
            for line_data in lines_data:
                # move line data is already grouped by account, we store the retrieved move info
                # to reduce db queries
                move_id = line_data['move_id']
                mx_data = mx_move_vals.get(move_id)
                if not mx_data:
                    uuid = AccountMove.browse(move_id).l10n_mx_edi_cfdi_uuid
                    if line_data['country_code'] != 'MX':
                        partner_rfc = 'XEXX010101000'
                    elif line_data['partner_vat']:
                        partner_rfc = line_data['partner_vat'].strip()
                    elif line_data['country_code'] in (False, 'MX'):
                        partner_rfc = 'XAXX010101000'
                    else:
                        partner_rfc = 'XEXX010101000'

                    mx_data = {
                        'partner_rfc': partner_rfc,
                        'l10n_mx_edi_cfdi_uuid': uuid,
                    }
                    mx_move_vals[move_id] = mx_data
                if mx_data.get('l10n_mx_edi_cfdi_uuid'):
                    currency_name = line_data.pop('currency_name', False)
                    currency_conversion_rate = mx_data.get('currency_conversion_rate')
                    foreign_currency = line_data['currency_id'] and line_data['currency_id'] != line_data['company_currency_id']
                    amount_total = line_data['amount_currency'] if foreign_currency else line_data['balance']
                    if foreign_currency and not currency_conversion_rate:
                        # calculate conversion rate just once per move so we don't see
                        # rounding differences between lines
                        amount_total_signed = line_data['balance']
                        if amount_total:
                            currency_conversion_rate = abs(amount_total_signed) / abs(amount_total)
                        else:
                            currency_conversion_rate = 1
                        currency_conversion_rate = '%.*f' % (5, currency_conversion_rate)
                        mx_data['currency_name'] = currency_name
                        mx_data['currency_conversion_rate'] = currency_conversion_rate
                    line_data.update({
                        'amount_total': amount_total,
                        **mx_data
                    })
        return super()._get_move_export_data(accounts_results)

    def _get_move_line_export_data(self, line):
        data = super()._get_move_line_export_data(line)
        uuid = line.get('l10n_mx_edi_cfdi_uuid')
        if uuid:
            data.update({
                'uuid': uuid,
                'currency_name': line.get('currency_name'),
                'currency_conversion_rate': line.get('currency_conversion_rate'),
                'customer_vat': line['partner_rfc'],
                'amount_total': '%.2f' % line['amount_total'],
            })
        return data
