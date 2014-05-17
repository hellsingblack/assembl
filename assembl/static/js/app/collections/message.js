define(['app','models/base', 'underscore', 'models/message'], function(Assembl, Base, _, MessageModel){

    var MessageCollection = Base.Collection.extend({
        /**
         * The url
         * @type {String}
         */
        url: Assembl.getApiUrl("posts"),

        /**
         * The model
         * @type {MessageModel}
         */
        model: MessageModel,

        /**
         * Return all segments in all messages in the annotator format
         * @return {Object[]}
         */
        getAnnotations: function(){
            var ret = [];

            _.each(this.models, function(model){
                ret = _.union(ret, model.getAnnotations() );
            });

            return ret;
        }

    });

    Assembl.Collections.Message = MessageCollection;

});