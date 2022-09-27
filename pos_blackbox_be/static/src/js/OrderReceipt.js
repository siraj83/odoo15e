odoo.define('pos_blackbox_be.OrderReceipt', function(require) {
    'use strict';

    const OrderReceipt = require('point_of_sale.OrderReceipt');
    const Registries = require('point_of_sale.Registries');

    const PosBlackBoxBeOrderReceipt = OrderReceipt =>
        class extends OrderReceipt {
            get receiptEnv () {
                let receipt_render_env = super.receiptEnv;
                if (this.env.pos.useBlackBoxBe()) {
                    let order = this.env.pos.get_order();
                    receipt_render_env.receipt.company.street = this.env.pos.company.street;

                    receipt_render_env.receipt.receipt_type = order.receipt_type;
                    receipt_render_env.receipt.blackboxSignature = order.blackbox_signature;
                    receipt_render_env.receipt.terminalId = order.blackbox_unit_id;
                    receipt_render_env.receipt.versionId = order.blackbox_pos_production_id;
                    receipt_render_env.receipt.pluHash = order.blackbox_plu_hash;
                    receipt_render_env.receipt.vscIdentificationNumber = order.blackbox_vsc_identification_number;
                    receipt_render_env.receipt.blackboxFdmNumber = order.blackbox_unique_fdm_production_number;
                    receipt_render_env.blackbox_ticket_counter = order.blackbox_ticket_counter;
                    receipt_render_env.blackbox_total_ticket_counter = order.blackbox_total_ticket_counter;
                    receipt_render_env.receipt.ticketCounter = order.blackbox_ticket_counters;
                    receipt_render_env.receipt.blackboxTime = order.blackbox_time;
                    receipt_render_env.receipt.blackboxDate = order.blackbox_date;
                    receipt_render_env.receipt.posIdentifier = order.pos.config.name;
                    receipt_render_env.receipt.fdmIdentifier = order.pos.config.certifiedBlackboxIdentifier;
                }
                return receipt_render_env;
            }
        };

    Registries.Component.extend(OrderReceipt, PosBlackBoxBeOrderReceipt);

    return OrderReceipt;
});
