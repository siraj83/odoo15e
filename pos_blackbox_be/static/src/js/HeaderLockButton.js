odoo.define('pos_blackbox_be.HeaderLockButton', function (require) {
    'use strict';

    const HeaderLockButton = require('point_of_sale.HeaderLockButton');
    const Registries = require('point_of_sale.Registries');

    const PosBlackboxBeHeaderLockButton = (HeaderLockButton) => class extends HeaderLockButton {
        async showLoginScreen() {
             if(this.env.pos.useBlackBoxBe() && this.env.pos.check_if_user_clocked()) {
                await this.showPopup('ErrorPopup', {
                        title: this.env._t("Fiscal Data Module Restriction"),
                        body: this.env._t("You must clock out in order to change the current employee."),
                    });
                return;
             }
             super.showLoginScreen();
        }
    };

    Registries.Component.extend(HeaderLockButton, PosBlackboxBeHeaderLockButton);

    return HeaderLockButton;
});
