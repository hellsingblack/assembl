define(['backbone', 'underscore', 'jquery', 'models/idea', 'app', 'views/idea'],
function(Backbone, _, $, Idea, Assembl, IdeaView){
    'use strict';
    
    var AllMessagesInIdeaListView = IdeaView.extend({
        /**
         * The template
         * @type {[type]}
         */
        template: Assembl.loadTemplate('allMessagesInIdeaList'),

        /**
         * The render
         */
        render: function(){
            Assembl.trigger('render');

            var data = this.model.toJSON();

            this.$el.addClass('idealist-item');
            if(this.model.get('num_posts') == 0) {
                this.$el.addClass('hidden');
            }
            else {
                this.$el.removeClass('hidden');
            }
            
            this.$el.html(this.template(data));
            return this;
        },

        /**
         * @events
         */
        events: {
            'click .idealist-title': 'onTitleClick'
        },

        /**
         * @event
         */
        onTitleClick: function(){
            if( Assembl.messageList ){
                Assembl.messageList.showAllMessages();
            }
            Assembl.setCurrentIdea(null);
        }
    });


    return AllMessagesInIdeaListView;
});
