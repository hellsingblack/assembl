define(['models/base', 'app', 'jquery', 'i18n', 'permissions'], function(Base, Assembl, $, i18n, Permissions){
    'use strict';

    var AVATAR_PLACEHOLDER = '//placehold.it/{0}';
    var UNKNOWN_USER_ID = 'system.Everyone';

    /**
     * @class UserModel
     */
    var UserModel = Base.Model.extend({

        /**
         * @type {String}
         */
        url: Assembl.getApiUrl('agents/'),

        /**
         * Defaults
         * @type {Object}
         */
        defaults: {
            id: null,
            name: '',
            avatarUrl: ''
        },

        /**
         * The list with all user's permissions
         * This is usefull only for the logged user.
         * @type {String[]}
         */
        permissions: [],

        /**
         * Load the permissions from script tag
         * and populates `this.permissions`
         *
         * @param {String} [id='permissions-json'] The script tag id
         */
        fetchPermissionsFromScripTag: function(id){
            id = id || 'permissions-json';

            var script = document.getElementById(id),
                json;

            if( !script ){
                throw new Error(app.format("Script tag #{0} doesn't exist", id));
            }

            try {
                json = JSON.parse(script.textContent);
                this.permissions = json;
            } catch(e){
                throw new Error("Invalid json");
            }

        },

        /**
         * return the avatar's url
         * @param  {Number} [size=44] The avatar size
         * @return {string}
         */
        getAvatarUrl: function(size){
            var id = this.getId();

            return id != UNKNOWN_USER_ID ? app.formatAvatarUrl(app.extractId(id), size) : app.format(AVATAR_PLACEHOLDER, size);
        },

        /**
         * @param  {String}  permission The permission name
         * @return {Boolean} True if the user has the given permission
         */
        hasPermission: function(permission){
            return $.inArray(permission, this.permissions) >= 0;
        },

        /**
         * @alias hasPermission
         */
        can: function(permission){
            return this.hasPermission(permission);
        },

        /**
         * @return {Boolean} true if the user is an unknown user
         */
        isUnknownUser: function(){
            return this.getId() == UNKNOWN_USER_ID;
        }

    });

    Assembl.Models.User = UserModel;

});
