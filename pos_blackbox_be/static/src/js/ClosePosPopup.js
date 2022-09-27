odoo.define('pos_blackbox_be.ClosePosPopup', function (require) {
    'use strict';

    const ClosePosPopup = require('point_of_sale.ClosePosPopup');
    const Registries = require('point_of_sale.Registries');

    const PosBlackboxBeClosePopup = (ClosePosPopup) =>
        class extends ClosePosPopup {
            async canCloseSession() {
                if(this.env.pos.useBlackBoxBe()) {
                    let status = await this.get_user_session_status(this.env.pos.pos_session.id, this.env.pos.pos_session.user_id[0]);
                    if(status) {
                        await this.showPopup('ErrorPopup', {
                            title: this.env._t("POS error"),
                            body: this.env._t("You need to clock out before closing the POS."),
                        });
                        return;
                    }
                }
                return super.canCloseSession();
            }

            async get_user_session_status(session, user) {
                return await this.rpc({
                    model: 'pos.session',
                    method: 'get_user_session_work_status',
                    args: [session, user],
                });
            }
        };

    Registries.Component.extend(ClosePosPopup, PosBlackboxBeClosePopup);

    return ClosePosPopup;
});
