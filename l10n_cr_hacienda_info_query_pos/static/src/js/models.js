odoo.define('l10n_cr_hacienda_info_query_pos_init.models',
function(require) {
    "use strict";

    const models = require("point_of_sale.models");

    models.load_fields('res.partner', ['county_id', 'district_id']);

    var existing_models = models.PosModel.prototype.models;
    var partner_index = _.findIndex(existing_models, function (model) {
        return model.model === "res.partner";
    });
    var partner_model = existing_models[partner_index];

    models.load_models([{
        model:  partner_model.model,
        fields: partner_model.fields,
        order:  partner_model.order,
        context: partner_model.context,
        loaded: partner_model.loaded,
    }]);

    models.load_fields('res.country.state', 'code');

    models.load_models([
        {
            model: 'res.country.county',
            fields: ['name','code','state_id'],
            loaded: function(self, counties){
                self.counties = counties;
            },
        },
        {
            model: 'res.country.district',
            fields: ['name','code','county_id'],
            loaded: function(self, districts){
                self.districts = districts;
            },
        }
    ],{'before': 'res.country.state'});

    return models;

});
