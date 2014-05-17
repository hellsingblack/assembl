define(['backbone', 'underscore', 'jquery', 'app', 'collections/segment', 'i18n', 'permissions'],
function(Backbone, _, $, Assembl, Segment, i18n, Permissions){
    'use strict';

    var SegmentList = Backbone.View.extend({
        /**
         * @init
         */
        initialize: function(obj){
            var that = this;

            if( obj && obj.button ){
                this.button = $(obj.button).on('click', Assembl.togglePanel.bind(window, 'segmentList'));
            }

            this.segments.on('invalid', function(model, error){ alert(error); });
            Assembl.users.on('reset', this.render, Assembl.segmentList);
            
            this.segments.on('add remove change reset', this.render, this);

            this.segments.on('add', function(segment){
                that.showSegment(segment);
            });
        },

        /**
         * The template
         * @type {_.template}
         */
        template: Assembl.loadTemplate('segmentList'),

        /**
         * The collection
         * @type {SegmentCollection}
         */
        segments: new Assembl.Collections.Segment,

        /**
         * The panel element
         * @type {jQuery}
         */
        panel: null,

        /**
         * The render
         * @return {segmentList}
         */
        render: function(){
            if(Assembl.debugRender) {
                console.log("segmentList:render() is firing");
            }
            Assembl.trigger('render');

            var segments = this.segments.getClipboard(),
                currentUser = Assembl.getCurrentUser(),
                data = {segments:segments,
                        canEditExtracts:currentUser.can(Permissions.EDIT_EXTRACT),
                        canEditMyExtracts:currentUser.can(Permissions.EDIT_MY_EXTRACT)
                       },
                top = 0;
            if( this.panel ){
                top = this.panel.find('.panel-body')[0].scrollTop;
            }

            this.$el.html(this.template(data));

            this.panel = this.$('.panel');

            if( top > 0 ){
                this.panel.find('.panel-body')[0].scrollTop = top;
            }

            return this;
        },

        /**
         * Add a segment to the bucket
         * @param {Segment} segment
         */
        addSegment: function(segment){
            delete segment.attributes.highlights;

            segment.save('idIdea', null);
            this.segments.add(segment);
        },

        /**
         * Add annotation as segment. 
         * @param {annotation} annotation
         * @param {Number} [idIdea=null] 
         * @return {Segment}
         */
        addAnnotationAsSegment: function(annotation, idIdea){
            var post = Assembl.getPostFromAnnotation(annotation),
                idPost = post.getId();

            var segment = new Segment.Model({
                target: { "@id": idPost, "@type": "email" },
                text: annotation.text,
                quote: annotation.quote,
                idCreator: app.getCurrentUser().getId(),
                ranges: annotation.ranges,
                idPost: idPost,
                idIdea: idIdea
            });

            if( segment.isValid() ){
                delete segment.attributes.highlights;

                this.segments.add(segment);
                segment.save();
            } else {
                alert( segment.validationError );
            }

            return segment;
        },

        /**
         * Creates a segment with the given text and adds it to the segmentList
         * @param  {string} text
         * @param  {string} [post=null] The origin post
         * @return {Segment}
         */
        addTextAsSegment: function(text, post){
            var idPost = null;

            if( post ){
                idPost = post.getId();
            }

            var segment = new Segment.Model({
                target: { "@id": idPost, "@type": "email" },
                text: text,
                quote: text,
                idCreator: app.getCurrentUser().getId(),
                idPost: idPost
            });

            if( segment.isValid() ){
                this.addSegment(segment);
                segment.save();
            }
        },

        /**
         * Removes a segment by its cid
         * @param  {String} cid
         */
        removeSegmentByCid: function(cid){
            var model = this.segments.get(cid);

            if(model){
                model.destroy();
            }
        },

        /**
         * Remove the given segment
         * @param {Segment} segment
         */
        removeSegment: function(segment){
            this.segments.remove(segment);
        },


        /**
         * Shows the given segment with an small fx
         * @param {Segment} segment
         */
        showSegment: function(segment){
            Assembl.openPanel(Assembl.segmentList);

            var selector = Assembl.format('.box[data-segmentid={0}]', segment.cid),
                box = this.$(selector);

            if( box.length ){
                var panelBody = this.$('.panel-body');
                var panelOffset = panelBody.offset().top;
                var offset = box.offset().top;
                // Scrolling to the element
                var target = offset - panelOffset + panelBody.scrollTop();
                panelBody.animate({ scrollTop: target });
                box.highlight();
            }
        },
        
        /**
         * Closes the panel
         */
        closePanel: function(){
            console.log("closePanel");
            if( this.button ){
                this.button.trigger('click');
            }
        },

        /**
         * The events
         * @type {Object}
         */
        events: {
            'dragstart .postit': "onDragStart",
            'dragend .postit': "onDragEnd",
            'dragover .panel': 'onDragOver',
            'dragleave .panel': 'onDragLeave',
            'drop .panel': 'onDrop',

            'click .closebutton': "onCloseButtonClick",
            'click #segmentList-clear': "onClearButtonClick",
            'click #segmentList-closeButton': "closePanel",

            'click .segment-link': "onSegmentLinkClick"
        },

        /**
         * @event
         */
        onDragStart: function(ev){
            ev.currentTarget.style.opacity = 0.4;

            var cid = ev.currentTarget.getAttribute('data-segmentid'),
                segment = this.segments.get(cid);

            Assembl.showDragbox(ev, segment.getQuote());
            Assembl.draggedSegment = segment;
        },

        /**
         * @event
         */
        onDragEnd: function(ev){
            if( ev ){
                ev.preventDefault();
                ev.stopPropagation();
            }

            ev.currentTarget.style.opacity = '';
            Assembl.draggedSegment = null;
        },

        /**
         * @event
         */
        onDragOver: function(ev){
            ev.preventDefault();

            var isText = false;
            if( ev.dataTransfer && ev.dataTransfer.types && ev.dataTransfer.types.indexOf('text/plain') > -1 ){
                isText = app.draggedIdea ? false : true;
            }

            if( Assembl.draggedSegment !== null || isText ){
                this.panel.addClass("is-dragover");
            }

            if( Assembl.draggedAnnotation !== null ){
                this.panel.addClass("is-dragover");
            }
        },

        /**
         * @event
         */
        onDragLeave: function(){
            this.panel.removeClass('is-dragover');
        },

        /**
         * @event
         */
        onDrop: function(ev){
            if( ev ){
                ev.preventDefault();
                ev.stopPropagation();
            }

            this.panel.trigger('dragleave');

            var idea = Assembl.getDraggedIdea();
            if( idea ){
                return; // Do nothing
            }

            var segment = Assembl.getDraggedSegment();
            if( segment ){
                this.addSegment(segment);
                return;
            }

            var annotation = Assembl.getDraggedAnnotation();
            if( annotation ){
                app.saveCurrentAnnotation();
                return;
            }

            var text = ev.dataTransfer.getData("Text");
            if( text ){
                this.addTextAsSegment(text);
                return;
            }
        },

        /**
         * @event
         */
        onCloseButtonClick: function(ev){
            var cid = ev.currentTarget.getAttribute('data-segmentid');
            this.removeSegmentByCid(cid);
        },

        /**
         * @event
         */
        onClearButtonClick: function(ev){
            var ok = confirm( i18n.gettext('segmentList-clearConfirmationMessage') );
            if( ok ){
                var segments = this.segments.getClipboard();
                _.each(segments, function(segment){
                    segment.destroy();
                });
            }
        },

        /**
         * @event
         */
        onSegmentLinkClick: function(ev){
            var cid = ev.currentTarget.getAttribute('data-segmentid'),
                segment = this.segments.get(cid);

            Assembl.showTargetBySegment(segment);
        }

    });

    return SegmentList;
});
