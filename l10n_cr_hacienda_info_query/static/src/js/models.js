odoo.define('l10n_cr_hacienda_info_query_init.models',
function(require) {
    "use strict";
    
    var core = require('web.core');
    var models = require('point_of_sale.models');
    var OrderlineSuper = models.Orderline;
    var field_utils = require('web.field_utils');
    var QWeb = core.qweb;
    var _t = core._t;
    var utils = require('web.utils');
    var round_pr = utils.round_precision;
    var _super_orderline = models.Orderline.prototype;
    
    models.load_fields('res.partner', 'county_id', 'district_id');
    
    models.load_fields('res.country.state', 'code');
    
    models.load_models([{
            model: 'res.country.county',
            fields: ['name','code','state_id'],
            loaded: function(self,county){
                self.county = county;
            },
        },{
            model: 'res.country.district',
            fields: ['name','code','county_id'],
            loaded: function(self,district){
                self.district = district;
            },
        }
    
    ],{'before': 'res.country.state'});
 
    
    });
