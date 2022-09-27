odoo.define('pos_blackbox_be.PaymentScreen', function(require) {
    "use strict";

    const PaymentScreen = require('point_of_sale.PaymentScreen');
    const Registries = require('point_of_sale.Registries');
    const { Gui } = require('point_of_sale.Gui');
    var core    = require('web.core');
    var _t      = core._t;

    const PosBlackboxBePaymentScreen = PaymentScreen => class extends PaymentScreen {
        //@Override
        async validateOrder(isForceValidate) {
            if(this.env.pos.useBlackBoxBe() && !this.env.pos.check_if_user_clocked()) {
                await Gui.showPopup('ErrorPopup',{
                    'title': _t("POS error"),
                    'body':  _t("User must be clocked in."),
                });
                return;
            }
            await super.validateOrder(...arguments);
        }
        openCashbox() {
            this.rpc({
                model: 'pos.session',
                method: 'increase_cash_box_opening_counter',
                args: [this.env.pos.pos_session.id]
            })
            super.openCashbox(...arguments);
        }
    };

    Registries.Component.extend(PaymentScreen, PosBlackboxBePaymentScreen);

    return PosBlackboxBePaymentScreen;
});
