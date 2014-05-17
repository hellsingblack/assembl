define(['backbone', 'underscore', 'models/idea', 'views/idea', "views/ideaGraph", 'app', 'types', 'views/allMessagesInIdeaList', 'views/orphanMessagesInIdeaList', 'views/synthesisInIdeaList', 'permissions', 'utils/renderVisitor', 'utils/siblingChainVisitor'],
function(Backbone, _, Idea, IdeaView, ideaGraphLoader, Assembl, Types, AllMessagesInIdeaListView, OrphanMessagesInIdeaListView, SynthesisInIdeaListView, Permissions, renderVisitor, siblingChainVisitor){
    'use strict';

    var FEATURED = 'featured',
        IN_SYNTHESIS = 'inNextSynthesis';



    var IdeaList = Backbone.View.extend({

        /**
         * The filter applied to the idea list
         * @type {string}
         */
        filter: null,

        /**
         * The collapse/expand flag
         * @type {Boolean}
         */
        collapsed: false,

        /**
         * The tempate
         * @type {_.template}
         */
        template: Assembl.loadTemplate('ideaList'),

        /**
         * .panel-body
         */
        body: null,

        /**
         * Are we showing the graph or the list?
         * @type {Boolean}
         */
        show_graph: false,

        /**
         * @init
         */
        initialize: function(obj){
            this.ideas = new Idea.Collection();
            /*this.on("all", function(eventName) {
                console.log("ideaList event received: ", eventName);
              });
            this.ideas.on("all", function(eventName) {
                console.log("ideaList collection event received: ", eventName);
              });*/
            
            if( obj && obj.button ){
                this.button = $(obj.button);
                this.button.on('click', app.togglePanel.bind(window, 'ideaList'));
            }

            var events = ['reset', 'change:parentId', 'change:inNextSynthesis', 'remove', 'add'];
            this.ideas.on(events.join(' '), this.render, this);

            var that = this;
            Assembl.on('idea:delete', function(){
                if(Assembl.debugRender) {
                    console.log("ideaList: triggering render because app.on('idea:delete') was triggered");
                }
                that.render();
            });

            Assembl.on('ideas:update', function(ideas){
                if(Assembl.debugRender) {
                    console.log("ideaList: triggering render because app.on('idea:update') was triggered");
                }
                that.ideas.add(ideas, {merge: true, silent: true});
                that.render();
            });
            
            // Benoitg - 2014-05-05:  There is no need for this, if an idealink
            // is associated with the idea, the idea itself will receive a change event
            // on the socket
            //app.segmentList.segments.on('add change reset', this.render, this);

            Assembl.on("panel:open", function(){that.resizeGraphView();});
            Assembl.on("panel:close", function(){that.resizeGraphView();});
        },

        /**
         * The render
         */
        render: function(){
            if(Assembl.debugRender) {
                console.log("ideaList:render() is firing");
            }
            Assembl.trigger('render');

            this.body = this.$('.panel-body');
            var y = 0,
            rootIdea = this.ideas.getRootIdea(),
            rootIdeaDirectChildrenModels = [],
            filter = {};

            if( this.body.get(0) ){
                y = this.body.get(0).scrollTop;
            }

            if( this.filter === FEATURED ){
                filter.featured = true;
            } else if ( this.filter === IN_SYNTHESIS ){
                filter.inNextSynthesis = true;
            }

            var list = document.createDocumentFragment();

            if(Object.keys(filter).length > 0) {
                rootIdeaDirectChildrenModels = this.ideas.where(filter);
            }
            else {
                rootIdeaDirectChildrenModels = this.ideas.models;
            }

            rootIdeaDirectChildrenModels = rootIdeaDirectChildrenModels.filter(function(idea) {
                return (idea.get("parentId") == rootIdea.id) || (idea.get("parentId") == null && idea.id != rootIdea.id); 
                }
            );

            rootIdeaDirectChildrenModels = _.sortBy(rootIdeaDirectChildrenModels, function(idea){
                return idea.get('order');
            });

            // Synthesis posts pseudo-idea
            var synthesisView = new SynthesisInIdeaListView({model:rootIdea});
            list.appendChild(synthesisView.render().el);
            
            // All posts pseudo-idea
            var allMessagesInIdeaListView = new AllMessagesInIdeaListView({model:rootIdea});
            list.appendChild(allMessagesInIdeaListView.render().el);
            
            var view_data = {};
            var roots = [];
            function excludeRoot(idea) {return idea != rootIdea};
            rootIdea.visitDepthFirst(renderVisitor(view_data, roots, excludeRoot));
            rootIdea.visitDepthFirst(siblingChainVisitor(view_data));

            _.each(roots, function(idea){
                var ideaView =  new IdeaView({model:idea}, view_data);
                list.appendChild(ideaView.render().el);
            });

            // Orphan messages pseudo-idea
            var orphanView = new OrphanMessagesInIdeaListView({model: rootIdea});
            list.appendChild(orphanView.render().el);

            var data = {
                tocTotal: this.ideas.length -1,//We don't count the root idea
                featuredTotal: this.ideas.where({featured: true}).length,
                synthesisTotal: this.ideas.where({inNextSynthesis: true}).length,
                canAdd: Assembl.getCurrentUser().can(Permissions.ADD_IDEA)
            };

            data.title = data.tocTitle;
            data.collapsed = this.collapsed;

            data.filter = this.filter;

            this.$el.html( this.template(data) );
            this.$('.idealist').append( list );

            this.body = this.$('.panel-body');
            this.body.get(0).scrollTop = y;

            return this;
        },

        /**
         * Remove the given idea
         * @param  {Idea} idea
         */
        removeIdea: function(idea){
            var parent = idea.get('parent');

            if( parent ){
                parent.get('children').remove(idea);
            } else {
                this.ideas.remove(idea);
            }
        },

        /**
         * Collapse ALL ideas
         */
        collapseIdeas: function(){
            this.ideas.each(function(idea){
                idea.attributes.isOpen = false;
            });

            this.collapsed = true;
            this.render();
        },

        /**
         * Expand ALL ideas
         */
        expandIdeas: function(){
            this.ideas.each(function(idea){
                idea.attributes.isOpen = true;
            });

            this.collapsed = false;
            this.render();
        },

        /**
         * Filter the current idea list by featured
         */
        filterByFeatured: function(){
            this.filter = FEATURED;
            this.render();
        },

        /**
         * Filter the current idea list by inNextSynthesis
         */
        filterByInNextSynthesis: function(){
            this.filter = IN_SYNTHESIS;
            this.render();
        },

        /**
         * Clear the filter applied to the idea list
         */
        clearFilter: function(){
            this.filter = '';
            this.render();
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
         * Sets the panel as full screen
         */
        setFullscreen: function(){
            Assembl.setFullscreen(this);
        },

        toggleGraphView: function() {
            this.show_graph = !this.show_graph;
            if (this.show_graph) {
                this.$('#idealist-graph').show();
                this.$('#idealist-list').hide();
                this.loadGraphView();
            } else {
                this.$('#idealist-graph').hide();
                this.$('#idealist-list').show();
            }
        },

        /**
         * Load the graph view
         */
        loadGraphView: function() {
            if (this.show_graph) {
                var that = this;
                $.getJSON( Assembl.getApiUrl('generic')+"/Discussion/"+app.discussionID+"/idea_graph_jit", function(data){
                    that.graphData = data['graph'];
                    that.hypertree = ideaGraphLoader(that.graphData);
                    try {
                        that.hypertree.onClick(Assembl.getCurrentIdea().getId(), {
                            // onComplete: function() {
                            //     that.hypertree.controller.onComplete();
                            // },
                            duration: 0
                        });
                    } catch (Exception) {}
                });
            }
        },

        /**
         * Load the graph view
         */
        resizeGraphView: function() {
            if (this.show_graph && this.graphData !== undefined) {
                try {
                    this.hypertree = ideaGraphLoader(this.graphData);
                    this.hypertree.onClick(Assembl.getCurrentIdea().getId(), {
                        duration: 0
                    });
                } catch (Exception) {}
            }
        },


        /**
         * The events
         */
        'events': {
            'click .panel-body': 'onPanelBodyClick',
            'dragover .panel-bodyabove': 'onAboveDragOver',
            'dragover .panel-bodybelow': 'onBelowDragOver',

            'click #ideaList-addbutton': 'addChildToSelected',
            'click #ideaList-collapseButton': 'toggleIdeas',
            'click #ideaList-graphButton': 'toggleGraphView',
            'click #ideaList-closeButton': 'closePanel',
            'click #ideaList-fullscreenButton': 'setFullscreen',

            'click #ideaList-filterByFeatured': 'filterByFeatured',
            'click #ideaList-filterByInNextSynthesis': 'filterByInNextSynthesis',
            'click #ideaList-filterByToc': 'clearFilter'
        },

        /**
         * @event
         */
        onPanelBodyClick: function(ev){
            if( $(ev.target).hasClass('panel-body') ){
                Assembl.setCurrentIdea(null);
            }
        },

        /**
         * Add a new child to the current selected.
         * If no idea is selected, add it at the root level ( no parent )
         */
        addChildToSelected: function(){
            var currentIdea = Assembl.getCurrentIdea(),
                newIdea = new Idea.Model(),
                that = this;

            if( this.ideas.get(currentIdea) ){
                newIdea.set('order', currentIdea.getOrderForNewChild());
                currentIdea.addChild(newIdea);
            } else {
                newIdea.set('order', Assembl.getOrderForNewRootIdea());
                this.ideas.add(newIdea);
                newIdea.save();
            }

            Assembl.setCurrentIdea(newIdea);
        },

        /**
         * Collapse or expand the ideas
         */
        toggleIdeas: function(){
            if( this.collapsed ){
                this.expandIdeas();
            } else {
                this.collapseIdeas();
            }
        },

        /**
         * Closes the panel
         */
        closePanel: function(){
            if(this.button){
                this.button.trigger('click');
            }
        },

        /**
         * @event
         */
        onAboveDragOver: function(ev){
            var y = this.body.get(0).scrollTop;

            if( y === 0 ){
                return;
            }

            this.body.get(0).scrollTop -= 1;
        },

        /**
         * @event
         */
        onBelowDragOver: function(ev){
            this.body.get(0).scrollTop += 1;
        }

    });

    return IdeaList;
});
