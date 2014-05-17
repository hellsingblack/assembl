define(['backbone', 'underscore', 'jquery', 'app'],
function(Backbone, _, $, Assembl){
    'use strict';

    var LateralMenu = Backbone.View.extend({
        initialize: function(obj){
            this.on('toggle', this.toggle, this);
        },

        /**
         * Flag whether it is open or not
         * @type {Boolean}
         */
        isOpen: false,

        /**
         * The template
         * @type {_.template}
         */
        template: Assembl.loadTemplate('lateralMenu'),

        /**
         * The page's wrapper
         * @type {jQuery}
         */
        wrapper: $('#wrapper'),

        /**
         * The render
         * @return {LateralMenu}
         */
        render: function(){
            Assembl.trigger('render');
            this.$el.html( this.template() );

            return this;
        },

        /**
         * Open a closed area
         * @param  {jQuery} area
         */
        openArea: function(area){
            var body = area.find('.accordion-body'),
                height = this.getBodyHeight(body);

            area.addClass('is-open');
            body.animate({height: height+'px'}, 'fast', Assembl.ease, function(){
                body.css('height', 'auto');
            });
        },

        /**
         * Closes an open area
         * @param  {jQuery} area
         */
        closeArea: function(area){
            var body = area.find('.accordion-body');
            body.height( body.height()+'px' );

            area.removeClass('is-open');
            body.animate({height:0}, 'fast', Assembl.ease);
        },

        /**
         * Returns the height of the given .accordion-body
         * @param  {jQuery} body
         * @return {Number}
         */
        getBodyHeight: function(body){
            body.css({
                position: 'absolute',
                height: 'auto',
                visibility: 'hidden'
            });

            var height = body.height();

            body.css({
                position: 'static',
                height: '0px',
                overflow: 'hidden',
                visibility: 'visible'
            });

            return height;
        },

        /**
         * The events
         * @type {Object}
         */
        events: {
            'click  #lateralmenu-button': 'toggle',
            'click .accordion-header': 'toggleArea'
        },

        // Events

        toggleArea: function(ev){
            var area = $(ev.currentTarget).parent();

            if( area.hasClass('is-open') ){
                this.closeArea( area );
            } else {
                this.openArea( area );
            }
        },

        /**
         * Open or close the lateralmenu
         * @event
         */
        toggle: function(){
            if (this.isOpen) this.close();
            else this.open();
        },

        /**
         * Open the lateralmenu
         */
        open: function(){
            var data = { translateX: Assembl.lateralMenuWidth + 'px' };

            this.$el.animate({translateX: 0}, Assembl.lateralMenuAnimationTime, Assembl.ease);
            this.wrapper.animate(data, Assembl.lateralMenuAnimationTime, Assembl.ease);
            this.isOpen = true;
            Assembl.trigger('lateralmenu.open');
        },

        /**
         * Close the lateralMenu
         */
        close: function(){
            var data = { translateX: '-' + Assembl.lateralMenuWidth + 'px' };
            this.$el.animate(data, Assembl.lateralMenuAnimationTime, Assembl.ease);
            this.wrapper.animate({translateX: 0}, Assembl.lateralMenuAnimationTime, Assembl.ease);
            this.isOpen = false;
            Assembl.trigger('lateralmenu.close');
        }

    });

    return LateralMenu;
});
