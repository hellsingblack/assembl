define(['backbone', 'underscore', 'jquery', 'models/idea', 'models/segment', 'app', 'permissions', 'views/ckeditorField', 'views/messageSend'],
function(Backbone, _, $, Idea, Segment, Assembl, Permissions, CKEditorField, MessageSendView){
    'use strict';

    var IdeaInSynthesisView = Backbone.View.extend({
        /**
         * Tag name
         * @type {String}
         */
        tagName: 'div',

        /**
         * The template
         * @type {[type]}
         */
        template: Assembl.loadTemplate('ideaInSynthesis'),

        /**
         * @init
         */
        initialize: function(obj){
            this.model.on('change:shortTitle change:longTitle change:segments', this.render, this);
            this.editing = false;
        },

        /**
         * The render
         * @return {IdeaInSynthesisView}
         */
        render: function(){
            Assembl.trigger('render');

            var
                data = this.model.toJSON(),
                authors = [],
                segments = Assembl.getSegmentsByIdea(this.model);

            this.$el.addClass('synthesis-idea');

            segments.forEach(function(segment) {
                var post = segment.getAssociatedPost();
                if(post) {
                    var creator = post.getCreator();
                    if(creator) {
                        authors.push(creator);
                    }
                }
            });

            data.id = this.model.getId();
            data.editing = this.editing;
            data.longTitle = this.model.getLongTitleDisplayText();
            data.authors = _.uniq(authors);
            data.subject = data.longTitle;

            this.$el.html(this.template(data));
            if(this.editing) {
                this.renderCKEditor();
            }
            this.renderReplyView();
            return this;
        },
        
        /**
         * renders the ckEditor if there is one editable field
         */
        renderCKEditor: function(){
            var that = this,
                area = this.$('.synthesis-expression-editor');

            this.ckeditor = new CKEditorField({
                'model': this.model,
                'modelProp': 'longTitle',
                'placeholder': this.model.getLongTitleDisplayText()
            });

            this.ckeditor.on('save cancel', function(){
                that.editing=false;
                that.render();
            });

            
            this.ckeditor.renderTo( area );
            this.ckeditor.changeToEditMode();
        },
        /**
         * renders the reply interface
         */
        renderReplyView: function(){
            this.replyView = new MessageSendView({
                'allow_setting_subject': false,
                //TODO:  Benoitg:  Once we fix backend support for publishing, this needs to point to the synthesis message
                //'reply_message': this.model.publised_by...,
                'reply_idea': this.model,
                'body_help_message': i18n.gettext('Type your response here...'),
                'cancel_button_label': null,
                'send_button_label': i18n.gettext('Send your reply'),
                'subject_label': null,
                'default_subject': 'Re: ' + Assembl.stripHtml(this.model.getLongTitleDisplayText()).substring(0,50),
                'mandatory_body_missing_msg': i18n.gettext('You did not type a response yet...'),
                'mandatory_subject_missing_msg': null
            });
            this.$('.synthesisIdea-replybox').append(this.replyView.render().el);
        },
        
        /**
         * The events
         * @type {Object}
         */
        events: {
            'click .synthesis-expression': 'onEditableAreaClick',
            'click .synthesisIdea-replybox-openbtn': 'focusReplyBox',
            'click .messageSend-cancelbtn': 'closeReplyBox'
        },
        
        /**
         *  Focus on the reply box, and open it if closed
         **/
        focusReplyBox: function(){
            this.openReplyBox();

            var that = this;
            window.setTimeout(function(){
                that.$('.messageSend-body').focus();
            }, 100);
        },
        /**
         *  Opens the reply box the reply button
         */
        openReplyBox: function(){
            this.$('.synthesisIdea-replybox').show();
        },

        /**
         *  Closes the reply box
         */
        closeReplyBox: function(){
            this.$('.synthesisIdea-replybox').hide();
        },
        /**
         * @event
         */
        onEditableAreaClick: function(ev){
            console.log("onEditableAreaClick");
            if(Assembl.getCurrentUser().can(Permissions.EDIT_IDEA)) {
                this.editing = true;
                this.render();
            }
        }
    });

    return IdeaInSynthesisView;
});
