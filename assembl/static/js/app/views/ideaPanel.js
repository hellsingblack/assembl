define(['backbone', 'underscore', 'models/idea', 'models/message', 'app', 'i18n', 'types', 'views/editableField', 'views/ckeditorField', 'permissions', 'views/messageSend'],
function(Backbone, _, Idea, Message, Assembl, i18n, Types, EditableField, CKEditorField, Permissions, MessageSendView){
    'use strict';

    var LONG_TITLE_ID = 'ideaPanel-longtitle';

    /**
     * @class IdeaPanel
     */
    var IdeaPanel = Backbone.View.extend({

        /**
         * The tempate
         * @type {_.template}
         */
        template: Assembl.loadTemplate('ideaPanel'),

        /**
         * @type {Idea.Model}
         */
        idea: null,

        /**
         * @init
         */
        initialize: function(obj){
            obj = obj || {};

            if( obj.button ){
                this.button = $(obj.button).on('click', app.togglePanel.bind(window, 'ideaPanel'));
            }

            if( ! obj.idea ){
                this.idea = new Assembl.Models.Idea();
            }

            this.idea.on('change', this.render, this);

            // Benoitg - 2014-05-05:  There is no need for this, if an idealink
            // is associated with the idea, the idea will recieve a change event
            // on the socket
            //app.segmentList.segments.on('change reset', this.render, this);
            Assembl.users.on('reset', this.render, this);
            
            var that = this;
            Assembl.on('idea:select', function(idea){
                that.setCurrentIdea(idea);
                if(idea) {
                    $('#button-ideaPanel').show();
                }
                else {
                    $('#button-ideaPanel').hide();
                }
            });
        },

        /**
         * The render
         */
        render: function(){
            if(Assembl.debugRender) {
                console.log("ideaPanel:render() is firing");
            }
            Assembl.trigger('render');

            var segments = this.idea.getSegments(),
                currentUser = Assembl.getCurrentUser(),
                editing = currentUser.can(Permissions.EDIT_IDEA) && this.idea.get('ideaPanel-editing') || false;
            this.$el.html( this.template( {
                idea:this.idea,
                segments:segments,
                editing:editing,
                i18n:i18n,
                sprintf:sprintf,
                canDelete:currentUser.can(Permissions.EDIT_IDEA),
                canEditExtracts:currentUser.can(Permissions.EDIT_EXTRACT),
                canEditMyExtracts:currentUser.can(Permissions.EDIT_MY_EXTRACT),
                canAddExtracts:currentUser.can(Permissions.EDIT_EXTRACT) //TODO: This is a bit too coarse
            } ) );
            this.panel = this.$('.panel');

            var shortTitleField = new EditableField({
                'model': this.idea,
                'modelProp': 'shortTitle',
                'class': 'panel-editablearea text-bold',
                'data-tooltip': i18n.gettext('Short expression (only a few words) of the idea in the table of ideas.'),
                'placeholder': i18n.gettext('New idea')
            });
            shortTitleField.renderTo(this.$('#ideaPanel-shorttitle'));

            Assembl.initClipboard();

            this.longTitleField = new CKEditorField({
                'model': this.idea,
                'modelProp': 'longTitle',
                'placeholder': this.idea.getLongTitleDisplayText()
            });
            this.longTitleField.renderTo( this.$('#ideaPanel-longtitle') );
            
            this.definitionField = new CKEditorField({
                'model': this.idea,
                'modelProp': 'definition',
                'placeholder': this.idea.getDefinitionDisplayText()
            });
            this.definitionField.renderTo( this.$('#ideaPanel-definition') );
            this.commentView = new MessageSendView({
                'allow_setting_subject': false,
                'reply_idea': this.idea,
                'body_help_message': i18n.gettext('Comment on this idea here...'),
                'send_button_label': i18n.gettext('Send your comment'),
                'subject_label': null,
                'mandatory_body_missing_msg': i18n.gettext('You need to type a comment first...'),
                'mandatory_subject_missing_msg': null
            });
            this.$('#ideaPanel-comment').append( this.commentView.render().el );
            return this;
        },

        /**
         * Blocks the panel
         */
        blockPanel: function(){
            this.$('.panel').addClass('is-loading');
        },

        /**
         * Unblocks the panel
         */
        unblockPanel: function(){
            this.$('.panel').removeClass('is-loading');
        },

        /**
         * Add a segment
         * @param  {Segment} segment
         */
        addSegment: function(segment){
            delete segment.attributes.highlights;

            var id = this.idea.getId();
            segment.save('idIdea', id);
        },

        /**
         * Shows the given segment with an small fx
         * @param {Segment} segment
         */
        showSegment: function(segment){
            var selector = Assembl.format('.box[data-segmentid={0}]', segment.cid),
                idIdea = segment.get('idIdea'),
                idea = Assembl.ideaList.ideas.get(idIdea),
                box;

            if( !idea ){
                return;
            }

            this.setCurrentIdea(idea);
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
         * Set the given idea as the current one
         * @param  {Idea} [idea=null]
         */
        setCurrentIdea: function(idea){
            if( idea !== null ){
                if( this.idea ) {
                    if( this.idea.getId() === idea.getId() ){
                        return; // already the current one
                    } else {
                        this.idea.set('isSelected', false);
                        this.idea.off('change', this.render);
                    }
                }
                this.idea = idea;
                this.idea.set('isSelected', true);

                if( this.idea.get('@type') === Types.IDEA ){
                    Assembl.openPanel(app.ideaPanel);
                } else {
                    Assembl.closePanel(app.ideaPanel);
                }
            } else {
                if( this.idea ){
                    this.idea.set('isSelected', false);
                }

                this.idea = new Idea.Model();
                Assembl.closePanel(Assembl.ideaPanel);
            }

            this.idea.on('change', this.render, this);
            this.render();
        },

        /**
         * Delete the current idea
         */
        deleteCurrentIdea: function(){
            // to be deleted, an idea cannot have any children nor segments
            var children = this.idea.getChildren(),
                segments = this.idea.getSegments(),
                that = this;

            if( children.length > 0 ){
                return alert( i18n.gettext('ideaPanel-cantDeleteByChildren') );
            }

            // Nor has any segments
            if( segments.length > 0 ){
                return alert( i18n.gettext('ideaPanel-cantDeleteBySegments') );
            }

            // That's a bingo
            this.blockPanel();
            this.idea.destroy({ success: function(){
                that.unblockPanel();
                Assembl.closePanel( app.ideaPanel );
                Assembl.trigger('idea:delete');
            }});
        },

        /**
         * Events
         */
        events: {
            'dragstart .box': 'onDragStart',
            'dragend .box': "onDragEnd",
            'dragover .panel': 'onDragOver',
            'dragleave .panel': 'onDragLeave',
            'drop .panel': 'onDrop',

            'click .closebutton': 'onCloseButtonClick',
            'click #ideaPanel-clearbutton': 'onClearAllClick',
            'click #ideaPanel-closebutton': 'onTopCloseButtonClick',
            'click #ideaPanel-deleteButton': 'onDeleteButtonClick',

            'click .segment-link': "onSegmentLinkClick"
        },

        /**
         * @event
         */
        onDragStart: function(ev){
            //TODO: Deal with editing own extract (EDIT_MY_EXTRACT)
            if( Assembl.segmentList && Assembl.segmentList.segments && Assembl.getCurrentUser().can(Permissions.EDIT_EXTRACT)){
                ev.currentTarget.style.opacity = 0.4;

                var cid = ev.currentTarget.getAttribute('data-segmentid'),
                    segment = Assembl.segmentList.segments.getByCid(cid);
                console.log( cid );
                Assembl.showDragbox(ev, segment.getQuote());
                Assembl.draggedSegment = segment;
            }
        },

        /**
         * @event
         */
        onDragEnd: function(ev){
            ev.currentTarget.style.opacity = '';
            Assembl.draggedSegment = null;
        },

        /**
         * @event
         */
        onDragOver: function(ev){
            ev.preventDefault();
            if( Assembl.draggedSegment !== null ){
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

            var segment = Assembl.getDraggedSegment();
            if( segment ){
                this.addSegment(segment);
            }
        },

        /**
         * @event
         */
        onCloseButtonClick: function(ev){
            var cid = ev.currentTarget.getAttribute('data-segmentid');

            if( Assembl.segmentList && Assembl.segmentList.segments ){
                var segment = Assembl.segmentList.segments.get(cid);

                if( segment ){
                    segment.save('idIdea', null);
                }
            }
        },

        /**
         * @event
         */
        onClearAllClick: function(ev){
            var ok = confirm( i18n.gettext('ideaPanel-clearConfirmationMessage') );
            if( ok ){
                this.idea.get('segments').reset();
            }
        },

        /**
         * @event
         */
        onTopCloseButtonClick: function(){
            Assembl.setCurrentIdea(null);
        },

        /**
         * @event
         */
        onDeleteButtonClick: function(){
            var ok = confirm( i18n.gettext('ideaPanel-deleteIdeaConfirmMessage') );

            if(ok){
                this.deleteCurrentIdea();
            }
        },

        /**
         * @event
         */
        onSegmentLinkClick: function(ev){
            var cid = ev.currentTarget.getAttribute('data-segmentid'),
                segment = Assembl.segmentList.segments.get(cid);

            Assembl.showTargetBySegment(segment);
        }

    });

    return IdeaPanel;
});
