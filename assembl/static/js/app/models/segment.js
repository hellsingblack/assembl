define(['app', 'models/base', 'underscore', 'models/user', 'models/message'],
function(Assembl, Base, _, User, Message){
    'use strict';

    /**
     * @class SegmentModel
     */
    var SegmentModel = Base.Model.extend({

        /**
         * @init
         */
        initialize: function(){
            if( this.attributes.created ){
                this.attributes.creationDate = this.attributes.created;
            }

            if( ! this.get('creationDate') ){
                this.set( 'creationDate', Assembl.getCurrentTime() );
            }

            var ranges = this.attributes.ranges,
                _serializedRange = [],
                _ranges = [];

            _.each(ranges, function(range, index){

                if( !(range instanceof Range.SerializedRange) ){
                    ranges[index] = new Range.SerializedRange(range);
                }

                _ranges[index] = ranges[index];

            });

            // We need to create a copy 'cause annotator destroy all ranges
            // once it creates the highlight
            this.attributes._ranges = _ranges;

            // cleaning
            delete this.attributes.highlights;
        },

        /**
         * @type {string}
         */
        urlBase: Assembl.getApiUrl("extracts"),

        /**
         * @type {Object}
         */
        defaults: {
            text: '',
            quote: '',
            idPost: null,
            idIdea: null,
            creationDate: null,
            idCreator: null,
            ranges: [],
            target: null
        },

        /**
         * Validation
         */
        validate: function(attrs, options){
            var currentUser = Assembl.getCurrentUser(),
                id = currentUser.getId();

            if( !id ){
                return i18n.gettext('You must be logged in to create segments');
            }
        },

        /**
         * @return {Idea} The Post the segments is associated to, if any
         * 
         * FIXME:  Once proper lazy loading is implemented, this must be changed
         * to use it.  As it is, it will leak memory
         * 
         */
        getAssociatedPost: function(){
            var post = null,
                idPost = this.attributes.idPost;

            if (idPost) {
                if(Assembl.segmentPostCache[idPost]) {
                    return Assembl.segmentPostCache[idPost];
                }
                post = Assembl.messageList.messages.get(idPost);
                if( !post ){
                    post = new Message.Model({'@id': idPost});
                    post.fetch({async:false});
                }
                Assembl.segmentPostCache[idPost] = post;
            }
            return post;
        },

        /**
         * Return the html markup to the icon
         * @return {string}
         */
        getTypeIcon: function(){
            var cls = 'icon-',
                target = this.get('target'),
                idPost = this.idPost;

            // todo(Marc-Antonie): review this `type` because `idPost`
            // is a string and doesn't have `@type` attribute

            if (target != null) {
                switch(target['@type']){
                    case 'Webpage':
                        cls += 'link';
                        break;

                    case 'Email':
                    case 'Post':
                    case 'AssemblPost':
                    case 'SynthesisPost':
                    case 'ImportedPost':
                    default:
                        cls += 'mail';
                }
            } else if (idPost != null) {
                cls += 'mail';
            }


            return Assembl.format("<i class='{0}'></i>", cls);
        },

        /**
         * Returns the segent's creator
         * @return {User}
         */
        getCreator: function(){
            var creatorId = this.get('idCreator');
            return Assembl.users.getById(creatorId);
        },

        /**
         * Alias for `.get('quote') || .get('text')`
         * @return {String}
         */
        getQuote: function(){
            return this.get('quote') || this.get('text');
        }
    });

    Assembl.Models.Segment = SegmentModel;

});
