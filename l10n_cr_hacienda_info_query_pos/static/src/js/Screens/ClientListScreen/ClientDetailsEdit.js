odoo.define('l10n_cr_hacienda_info_query_pos.ClientDetailsEdit', function(require) {
    'use strict';

    const {_t} = require("web.core");
    const ClientDetailsEdit = require("point_of_sale.ClientDetailsEdit");
    const Registries = require("point_of_sale.Registries");

    const PosClientDetailsEdit = (ClientDetailsEdit) =>
        class extends ClientDetailsEdit {
            constructor() {
                super(...arguments);
            }
            onchange_county(event){
                /*
                 * Evento para cuando cambia el canton
                 *
                 * Aquí debo cargar los distritos correspondientes
                 * Aquí debo cargar los distritos correspondientes
                 */
                var district = this.env.pos.district;
                var canton = document.getElementsByName("county_id")[0];
                var str_html = "";
                for(var i = 0; i < district.length; i++){
                    if(district[i].county_id[0] == canton.options[canton.selectedIndex].value){
                        str_html += "<option value='" + district[i]['id'] + "'>" + district[i]['name'] +"</option>";
                    }
                }
                var select = document.getElementsByName("district_id")[0];
    
                select.innerHTML = str_html;
    
                this.changes[event.target.name] = event.target.value;
            }
    
    
            onchange_state(event){
                /*
                 * Evento para cuando cambia el canton
                 *
                 * Aquí debo cargar los distritos correspondientes
                 * Aquí debo cargar los distritos correspondientes
                 */
                var district_id = document.getElementsByName("district_id")[0];
                 // Reseteamos los otros combobox para que no se genere confusión
                district_id.innerHTML = str_html;
    
    
                var county = this.env.pos.county;
    
                var provincia = document.getElementsByName("state_id")[0];
                var str_html = "";
                for(var i = 0; i < county.length; i++){
                    if(county[i].state_id[0] == provincia.options[provincia.selectedIndex].value){
                        str_html += "<option value='" + county[i]['id'] + "'>" + county[i]['name'] +"</option>";
                    }
                }
                var select = document.getElementsByName("county_id")[0];
    
                select.innerHTML = str_html;
    
                this.changes[event.target.name] = event.target.value;
            }
    
            onchange_country(event){
                /*
                 * Evento para cuando cambia el canton
                 *
                 * Aquí debo cargar los distritos correspondientes
                 * Aquí debo cargar los distritos correspondientes
                 */
                var state_id = document.getElementsByName("state_id")[0];
                var district_id = document.getElementsByName("district_id")[0];
                var county_id = document.getElementsByName("county_id")[0];
                // Reseteamos los otros combobox para que no se genere confusión
                state_id.innerHTML = "";
                district_id.innerHTML = "";
                county_id.innerHTML = "";
    
                var states = this.env.pos.states;
    
                var pais = document.getElementsByName("country_id")[0];
                var str_html = "";
                for(var i = 0; i < states.length; i++){
                    if (pais.options[pais.selectedIndex].value == 50){
                        if((states[i].country_id[0] == pais.options[pais.selectedIndex].value) && !isNaN(states[i]['code'])){
                            str_html += "<option value='" + states[i]['id'] + "'>" + states[i]['name'] +"</option>";
                        }
                    }
                    else {
                        if((states[i].country_id[0] == pais.options[pais.selectedIndex].value)){
                            str_html += "<option value='" + states[i]['id'] + "'>" + states[i]['name'] +"</option>";
                        }
                    }
                }
                var select = document.getElementsByName("state_id")[0];
    
                select.innerHTML = str_html;
    
                this.changes[event.target.name] = event.target.value;
            }
    
            obtener_nombre(event){
                var vat = event.target.value
                var host = window.location.host
                var end_point = "http://" + host + "/cedula/" + vat
                var result = httpGet(end_point);
                this.changes[event.target.name] = event.target.value;
    
                this.changes['name'] = result['nombre'];
                this.changes['email'] = result['email'];
    
            }
            saveChanges() {
                const processedChanges = {};
                for (const [key, value] of Object.entries(this.changes)) {
                    if (this.intFields.includes(key)) {
                        processedChanges[key] = parseInt(value) || false;
                    } else {
                        processedChanges[key] = value;
                    }
                }
                this.props.partner.country_id = processedChanges.country_id
                
                super.saveChanges();
            }
            captureChange(event) {
                super.captureChange(event);
                this.props.partner.country_id = event.currentTarget.country_id;
            }
        };

    Registries.Component.extend(ClientDetailsEdit, PosClientDetailsEdit);

    return ClientDetailsEdit;
});
