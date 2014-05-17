define(['models/base','app', 'models/synthesis'], function(Base, Assembl, SynthesisModel){

    /**
     * @class IdeaColleciton
     */
    var SynthesisCollection = Base.Collection.extend({
        /**
         * Url
         * @type {String}
         */
        url: Assembl.getApiUrl("explicit_subgraphs/synthesis"),

        /**
         * The model
         * @type {SynthesisModel}
         */
        model: SynthesisModel
    });

    Assembl.Collections.Synthesis = SynthesisCollection;

})