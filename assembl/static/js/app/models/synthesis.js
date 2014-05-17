define(['models/base', 'jquery', 'app', 'i18n'], function(Base, $, Assembl, i18n){
    'use strict';

    /**
     * @class SynthesisModel
     */
    var SynthesisModel = Base.Model.extend({

        /**
         * @init
         */
        initialize: function(){
            //What was this?  Benoitg - 2014-05-13
            //this.on('change', this.onAttrChange, this);
        },
        
        /**
         * The urlRoot endpoint
         * @type {String}
         */
        urlRoot: Assembl.getApiUrl('explicit_subgraphs/synthesis'),

        /**
         * Default values
         * @type {Object}
         */
        defaults: {
            subject: i18n.gettext('Add a title'),
            introduction: i18n.gettext('Add an introduction'),
            conclusion: i18n.gettext('Add a conclusion'),
            ideas: []
        }


    });

    Assembl.Models.Synthesis = SynthesisModel;

});
