define(['models/base', 'app', 'jquery', 'i18n', 'models/user'], function(Base, Assembl, $, i18n, UserModel){

    var UNKNOWN_USER_ID = 'system.Everyone';

    /**
     * The unknown User
     * @type {UserModel}
     */
    var UNKNOWN_USER = new UserModel({
        id: UNKNOWN_USER_ID,
        name: i18n.gettext('Unknown user')
    });

    /**
     * @class UserCollection
     */
    var UserCollection = Base.Collection.extend({
        /**
         * @type {String}
         */
        url: Assembl.getApiUrl('agents/'),

        /**
         * The model
         * @type {UserModel}
         */
        model: UserModel,

        /**
         * Returns the user by his/her id, or return the unknown user
         * @param {Number} id
         * @type {User}
         */
        getById: function(id){
            var user = this.get(id);
            return user || this.getUnknownUser();
        },

        /**
         * Returns the unknown user
         * @return {User}
         */
        getUnknownUser: function(){
            return UNKNOWN_USER;
        }
    });

    Assembl.Collections.User = UserCollection;

})