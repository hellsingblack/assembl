define(['app','models/base','models/ideas'], function(Assembl, Base, IdeaModel){

    /**
     * @class IdeaColleciton
     */
    var IdeaCollection = Base.Collection.extend({
        /**
         * Url
         * @type {String}
         */
        url: Assembl.getApiUrl("ideas"),

        /**
         * The model
         * @type {IdeaModel}
         */
        model: IdeaModel,

        /**
         * @return {Idea} The root idea
         */
        getRootIdea: function(){
            var retval = this.findWhere({ '@type': Types.ROOT_IDEA });
            if (!retval) {
                console.log("ERROR: getRootIdea() failed!");
                console.log(this);
            }
            return retval;
        }
    });

    Assembl.Collections.Idea = IdeaCollection;

});