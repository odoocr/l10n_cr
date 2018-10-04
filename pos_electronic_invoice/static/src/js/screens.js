odoo.define('pos_electronic_invoice.screens', function(require){
    'use strict'
    var models = require('point_of_sale.models');
    var screens = require('point_of_sale.screens');


    console.log("Pos js Loaded" , models)
    screens.PaymentScreenWidget.include({
        validate_order: function (force_validate) {
            var order = this.pos.get_order();
            if (!order.to_invoice) {
                order.set_simple_inv_number();
            }

            this._super(force_validate);
        }
    });

});