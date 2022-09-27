odoo.define('pos_blackbox_be.CashMovePopup', function (require) {
    'use strict';

    const CashMovePopup = require('point_of_sale.CashMovePopup');
    const Registries = require('point_of_sale.Registries');

    const PosBlackboxBeCashMovePopup = (CashMovePopup) => class extends CashMovePopup {
        confirm() {
            let result = super.confirm();
            this.rpc({
                model: 'pos.session',
                method: 'increase_cash_box_opening_counter',
                args: [this.env.pos.pos_session.id]
            })
            return result;
        }
    };

    Registries.Component.extend(CashMovePopup, PosBlackboxBeCashMovePopup);

    return CashMovePopup;
});
