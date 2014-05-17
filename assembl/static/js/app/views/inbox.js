define(['backbone', 'models/inbox', 'views/email', 'app'],
function(Backbone, InboxModel, EmailView, Assembl){
    'use strict';

    var InboxView = Backbone.View.extend({
        el: '#inbox',
        model: new InboxModel(),
        template: Assembl.loadTemplate('inbox'),

        initialize: function(obj){
            this.collection = obj.collection;
            this.collection.on('reset', this.render, this);
        },

        render: function(){
            Assembl.trigger('render');

            var emailList = document.createDocumentFragment();

            this.collection.each(function(email){
                var emailView = new EmailView({model:email});
                emailList.appendChild(emailView.render().el);
            });

            this.$el.html(this.template());
            this.$('#inbox-emaillist').append( emailList );
            return this;
        }
    });


    return InboxView;
});
