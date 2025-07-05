odoo.define('l10n_cr_hacienda_info_query.ClientDetailsEdit',
function(require) {
    'use strict';

    const { getDataURLFromFile } = require('web.utils');
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    class ClientDetailsEdit extends PosComponent {
        constructor() {
            super(...arguments);
            this.intFields = ['country_id', 'state_id', 'property_product_pricelist'];
            this.changes = {};
        }
        mounted() {
            this.env.bus.on('save-customer', this, this.saveChanges);
        }
        willUnmount() {
            this.env.bus.off('save-customer', this);
        }
        get partnerImageUrl() {
            // We prioritize image_1920 in the `changes` field because we want
            // to show the uploaded image without fetching new data from the server.
            const partner = this.props.partner;
            if (this.changes.image_1920) {
                return this.changes.image_1920;
            } else if (partner.id) {
                return `/web/image?model=res.partner&id=${partner.id}&field=image_128&write_date=${partner.write_date}&unique=1`;
            } else {
                return false;
            }
        }
        /**
         * Save to field `changes` all input changes from the form fields.
         */
        captureChange(event) {
            this.changes[event.target.name] = event.target.value;
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

        obtener_nombre(event) {
            var vat = event.target.value
            var host = window.location.host
            var end_point = "http://" + host + "/cedula/" + vat
            var result = httpGet(end_point);
            this.changes[event.target.name] = event.target.value;

            this.changes['name'] = result['nombre'];
            this.changes['email'] = result['email'];

        }

        saveChanges() {
            let processedChanges = {};
            for (let [key, value] of Object.entries(this.changes)) {
                if (this.intFields.includes(key)) {
                    processedChanges[key] = parseInt(value) || false;
                } else {
                    processedChanges[key] = value;
                }
            }
            if ((!this.props.partner.name && !processedChanges.name) ||
                processedChanges.name === '' ){
                return this.showPopup('ErrorPopup', {
                  title: _('A Customer Name Is Required'),
                });
            }
            processedChanges.id = this.props.partner.id || false;
            this.trigger('save-changes', { processedChanges });
        }
        async uploadImage(event) {
            const file = event.target.files[0];
            if (!file.type.match(/image.*/)) {
                await this.showPopup('ErrorPopup', {
                    title: this.env._t('Unsupported File Format'),
                    body: this.env._t(
                        'Only web-compatible Image formats such as .png or .jpeg are supported.'
                    ),
                });
            } else {
                const imageUrl = await getDataURLFromFile(file);
                const loadedImage = await this._loadImage(imageUrl);
                if (loadedImage) {
                    const resizedImage = await this._resizeImage(loadedImage, 800, 600);
                    this.changes.image_1920 = resizedImage.toDataURL();
                    // Rerender to reflect the changes in the screen
                    this.render();
                }
            }
        }
        _resizeImage(img, maxwidth, maxheight) {
            var canvas = document.createElement('canvas');
            var ctx = canvas.getContext('2d');
            var ratio = 1;

            if (img.width > maxwidth) {
                ratio = maxwidth / img.width;
            }
            if (img.height * ratio > maxheight) {
                ratio = maxheight / img.height;
            }
            var width = Math.floor(img.width * ratio);
            var height = Math.floor(img.height * ratio);

            canvas.width = width;
            canvas.height = height;
            ctx.drawImage(img, 0, 0, width, height);
            return canvas;
        }
        /**
         * Loading image is converted to a Promise to allow await when
         * loading an image. It resolves to the loaded image if succesful,
         * else, resolves to false.
         *
         * [Source](https://stackoverflow.com/questions/45788934/how-to-turn-this-callback-into-a-promise-using-async-await)
         */
        _loadImage(url) {
            return new Promise((resolve) => {
                const img = new Image();
                img.addEventListener('load', () => resolve(img));
                img.addEventListener('error', () => {
                    this.showPopup('ErrorPopup', {
                        title: this.env._t('Loading Image Error'),
                        body: this.env._t(
                            'Encountered error when loading image. Please try again.'
                        ),
                    });
                    resolve(false);
                });
                img.src = url;
            });
        }
    }
    ClientDetailsEdit.template = 'ClientDetailsEdit';

    Registries.Component.add(ClientDetailsEdit);

    return ClientDetailsEdit;
});
