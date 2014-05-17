require.config({
  baseUrl:'/static/js/',
  waitSeconds:20,
  urlArgs:'bust=' + (new Date()).getTime(),
  paths:{
    'app': 'app/app',
    'models':'app/models',
    'views':'app/views',
    'collections':'app/collections',
    'router': 'app/router',
    'i18n': 'app/plugins/i18n',
    'socket': 'utils/socket',
    'types': 'utils/types',
    'permissions': 'utils/permissions',
    'jquery': 'bower_components/jquery/jquery.min',
    'tipsy': 'bower_components/tipsy/src/javascripts/jquery.tipsy',
    'backbone': 'bower_components/backbone/backbone',
    'underscore': 'bower_components/underscore/underscore-min',
    'marionette': 'bower_components/marionette/lib/backbone.marionette.min',
    'jasmine': 'bower_components/jasmine/lib/jasmine-core/jasmine',
    'jasmine-html': 'bower_components/jasmine/lib/jasmine-core/jasmine',
    'jasmine-jquery': 'bower_components/jasmine-jquery/lib/jasmine-jquery',
    'ckeditor': 'bower_components/ckeditor/ckeditor',
    'moment': 'bower_components/momentjs/min/moment.min',
    'zeroclipboard': 'bower_components/zeroclipboard/ZeroClipboard',
    'sockjs': 'bower_components/sockjs/sockjs.min',
    'cytoscape': 'bower_components/cytoscape/dist/cytoscape.min',
    'jit': 'bower_components/jit/Jit/jit',
    'sprintf': 'bower_components/sprintf/dist/sprintf.min',
    'annotator': 'bower_components/annotator/annotator-full.min',
    'jquery-highlight': 'app/plugins/jquery.highlight',
    'ckeditor-sharedspace': 'app/plugins/plugin'
  },
  shim:{
      'backbone': {
          deps: ['underscore', 'jquery'],
          exports: 'backbone'
      },
      'underscore': {
          exports: '_'
      },
      marionette: {
          deps: ['backbone', 'underscore'],
          exports: "marionette"
      },
      'jquery': {
          exports: 'jQuery'
      },
      'jquery-highlight': {
          exports: 'jQuery',
          deps: ['jquery']
      },
      'i18n': {
          exports: 'i18n'
      },
      'socket': {
          deps: ['sockjs']
      },
      'jasmine': {
          exports: 'jasmine'
      },
      'jasmine-html': {
          deps: ['jasmine', 'jasmine-jquery'],
          exports: 'jasmine'
      },
      'jasmine-jquery': {
          deps: ['jasmine'],
          exports: 'jasmine'
      },
      'ckeditor': {
          exports: 'CKEDITOR'
      },
      'ckeditor-sharedspace': {
          deps: ['ckeditor'],
          exports: 'CKEDITOR'
      },
      'tipsy': {
          deps: ['jquery']
      },
      'zeroclipboard' : {
          exports: 'ZeroClipboard'
      },
      'sockjs': {
          deps: ['jquery'],
          exports: 'SockJS'
      },
      'cytoscape': {
          deps: ['jquery'],
          exports: 'cytoscape'
      },
      'jit': {
          deps: [],
          exports: '$jit'
      },
      'annotator' : {
          deps: ['jquery'],
          exports: 'Annotator'
      },
      'sprintf' : {
          deps: [],
          exports: 'sprintf'
      }
  }

});

//Marionette application start

require(['app','i18n','jquery','views/lateralMenu','views/ideaList','views/ideaPanel','views/segmentList','views/messageList',
        'views/synthesisPanel','models/synthesis','models/user','models/segment','router','socket'],
    function(Assembl, i18n, $, LateralMenu, IdeaList, IdeaPanel, SegmentList, MessageList,
             SynthesisPanel, Synthesis, User, Segment, Router, Socket){
    'use strict';

    i18n(json);

    Assembl.app.start();

    Assembl.init();

    // The router
    Assembl.router = new Router();

    // The socket
    Assembl.socket = new Socket();
    Assembl.on('socket:open', function(){ $('#onlinedot').addClass('is-online').attr('title', 'online'); });
    Assembl.on('socket:close', function(){ $('#onlinedot').removeClass('is-online').attr('title', 'offline'); });

    // User
    Assembl.users = new User.Collection();
    Assembl.users.on('reset', app.loadCurrentUser);
    Assembl.users.fetchFromScriptTag('users-json');

    // Lateral menu
    // app.lateralMenu = new LateralMenu({el: '#lateralMenu'}).render();
    // $('#assembl-mainbutton').on('click', app.lateralMenu.trigger.bind(app.lateralMenu, 'toggle'));
    // app.getCurrentUser().on('change', app.lateralMenu.render, app.lateralMenu);

    // The order of these initialisations matter...
    // Segment List
    Assembl.segmentList = new SegmentList({el: '#segmentList', button: '#button-segmentList'});

    // Idea list
    Assembl.ideaList = new IdeaList({el: '#ideaList', button: '#button-ideaList'});

    // Idea panel
    Assembl.ideaPanel = new IdeaPanel({el: '#ideaPanel', button: '#button-ideaPanel'}).render();

    // Message
    Assembl.messageList = new MessageList({el: '#messageList', button: '#button-messages'}).render();
    Assembl.messageList.loadInitialData();

    // Synthesis
    Assembl.syntheses = new Synthesis.Collection();
    var nextSynthesisModel = new Synthesis.Model({'@id': 'next_synthesis'});
    nextSynthesisModel.fetch();
    Assembl.syntheses.add(nextSynthesisModel);
    Assembl.synthesisPanel = new SynthesisPanel({
        el: '#synthesisPanel',
        button: '#button-synthesis',
        model: nextSynthesisModel
    });


    // Fetching the ideas
    Assembl.segmentList.segments.fetchFromScriptTag('extracts-json');
    Assembl.ideaList.ideas.fetchFromScriptTag('ideas-json');

    // Let the game begins...
    Backbone.history.start({hashChange: false, root: "/" + Assembl.slug });


});