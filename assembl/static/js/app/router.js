define(['backbone', 'jquery', 'app'], function(Backbone, $, Assembl){
    'use strict';

    var Router = Backbone.Router.extend({

        /**
         * Router strings
         * @type {Object}
         */
        routes: {
            "/": "home",
            "idea/:id" : "idea",
            "idea/:slug/:id" : "ideaSlug",
            "message/:id": "message",
            "message/:slug/:id" : "messageSlug"
        },

        /**
         * Router for Idea
         * @param  {Number} id
         */
        idea: function(id){
            Assembl.openPanel( Assembl.ideaList );
            var idea = Assembl.ideaList.ideas.get(id);
            if( idea ){
                Assembl.setCurrentIdea(idea);
            }
        },

        /**
         * Alias for `idea`
         */
        ideaSlug: function(slug, id){
            return this.idea(slug +'/'+ id);
        },

        /**
         * Router for Message
         * @param  {Number} id
         */
        message: function(id){
            Assembl.openPanel( Assembl.messageList );
            Assembl.messageList.messages.once('reset', function(){
                Assembl.messageList.showMessageById(id);
            });
        },

        /**
         * Alias for `message`
         */
        messageSlug: function(slug, id){
            return this.message(slug +'/'+ id);
        },

        /**
         * Default home page
         */
        home: function(){
            var panels = Assembl.getPanelsFromStorage();
            _.each(panels, function(value, name){
                var panel = Assembl[name];
                if( panel && name !== 'ideaPanel' ){
                    Assembl.openPanel(panel);
                }
            });
            if(Assembl.openedPanels < 1) {
                /* If no panel would be opened on load, open the table of ideas
                 * and the Message panel so the user isn't presented with a 
                 * blank screen
                 */
                Assembl.openPanel(Assembl.ideaList);
                Assembl.openPanel(Assembl.messageList);
            }
        }

    });


    return Router;
});
