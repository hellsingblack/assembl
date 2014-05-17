define(['app', 'models/base', 'underscore', 'models/segment'], function(Assembl, Base, _, SegmentModel){

    /**
     * @class SegmentColleciton
     */
    var SegmentCollection = Base.Collection.extend({

        /**
         * @type {String}
         */
        url: Assembl.getApiUrl("extracts"),

        /**
         * @type {IdeaModel}
         */
        model: SegmentModel,

        /**
         * Return the segments to compose the clipboard
         * @return {Array<Segment>}
         */
        getClipboard: function(){
            var currentUser = Assembl.getCurrentUser(),
                segments;

            return this.filter(function(item){
                if( item.get('idIdea') !== null ){
                    return false;
                }

                return item.getCreator().getId() == currentUser.getId();
            });
        },

        /**
         * Returns the segment related to the annotation
         * @param  {annotation} annotation
         * @return {Segment}
         */
        getByAnnotation: function(annotation){
            return this.get(annotation['@id']);
        }
    });

    Assembl.Collections.Segment = SegmentCollection;

});