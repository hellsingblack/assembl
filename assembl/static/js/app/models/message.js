define(['models/base', 'jquery', 'app', 'underscore'], function(Base, $, Assembl, _){
    'use strict';

    /**
     * @class MessageModel
     */
    var MessageModel = Base.Model.extend({
        /**
         * The url
         * @type {String}
         */
        urlRoot: Assembl.getApiUrl('posts'),

        /**
         * Default values
         * @type {Object}
         */
        defaults: {
            collapsed: false,
            checked: false,
            read: false,
            parentId: null,
            subject: null,
            body: null,
            idCreator: null,
            avatarUrl: null,
            date: null
        },

        /**
         * Return all children
         * @return {MessageModel[]}
         */
        getChildren: function(){
            return this.collection.where({ parentId: this.getId() });
        },

        /**
         * Return the parent idea
         * @return {MessageModel}
         */
        getParent: function(){
            return this.collection.findWhere({ '@id': this.get('parentId') });
        },

        /**
         * Return all segments related to this message
         * @return {Segment[]}
         */
        getSegments: function(){
            return Assembl.segmentList.segments.where({ idPost: this.getId() });
        },

        /**
         * Return all segments in the annotator format
         * @return {Object[]}
         */
        getAnnotations: function(){
            var segments = this.getSegments(),
                ret = [];

            _.each(segments, function(segment){
                segment.attributes.ranges = segment.attributes._ranges;
                ret.push( _.clone(segment.attributes) );
            });

            return ret;
        },


        /**
         * Returns the toppest parent
         * @return {MessageModel}
         */
        getRootParent: function(){
            if( this.get('parentId') === null ){
                return null;
            }

            var parent = this.getParent(),
                current = null;

            do {

                if( parent ){
                    current = parent;
                    parent = parent.get('parentId') !== null ? parent.getParent() : null;
                } else {
                    parent = null;
                }

            } while (parent !== null);

            return current;

        },

        /**
         * Returns the post's creator
         * @return {User}
         */
        getCreator: function(){
            var creatorId = this.get('idCreator');
            return Assembl.users.getById(creatorId);
        },

        /**
         * @event
         */
        onAttrChange: function(){
            this.save();
        },

        /**
         * Set the `read` property
         * @param {Boolean} value
         */
        setRead: function(value){
            var user = Assembl.getCurrentUser();

            if( user.isUnknownUser() ){
                // Unknown User can't mark as read
                return;
            }

            var isRead = this.get('read');
            if( value === isRead ){
                return; // Nothing to do
            }

            this.set('read', value, { silent: true });

            var that = this,
                url = Assembl.getApiUrl('post_read/') + this.getId(),
                ajax;

            ajax = $.ajax(url, {
                method: 'PUT',
                data: JSON.stringify({ 'read': value }),
                contentType: "application/json; charset=utf-8",
                dataType: "json",
                success: function(data){
                    that.trigger('change:read', [value]);
                    that.trigger('change', that);
                    Assembl.trigger('ideas:update', [data.ideas]);
                }
            });
        }
    });

    Assembl.Models.Message = MessageModel;

});
