define(['marionette','jquery', 'underscore', 'ckeditor', 'moment', 'i18n', 'zeroclipboard', 'types', 'permissions'],
    function(Marionette, $, _, ckeditor, Moment, i18n, ZeroClipboard, Types, Permissions){

        Backbone.$.ajaxSetup({
            cache: false
        });

        var Assembl = {
            Models : {},
            Collections : {},
            Views : {},
            Factories : {}
        };

        Assembl.app = new Backbone.Marionette.Application();

        Assembl.app.addInitializer(function(){
            Assembl.app.addRegions({
                header: '',
                side: '',
                body: '',
                slider: ''
            });
        });

        Assembl.app.addInitializer(function(){});

        var
            CONTEXT_MENU_WIDTH = 150,
            DRAGBOX_MAX_LENGTH = 25,
            DISCUSSION_SLUG = $('#discussion-slug').val(),
            $d = $(document);

        Assembl.socket_url = $('#socket-url').val();

        /**
         * Ckeditor default configuration
         * @type {object}
         */
        Assembl.CKEDITOR_CONFIG = {
            toolbar: [  ['Bold', 'Italic', 'Outdent', 'Indent', 'NumberedList', 'BulletedList'] ],
            extraPlugins: 'sharedspace',
            removePlugins: 'floatingspace,resize',
            sharedSpaces: { top: 'ckeditor-toptoolbar', bottom: 'ckeditor-bottomtoolbar' }
        }

        Assembl.AVAILABLE_MESSAGE_VIEW_STYLES = {
            TITLE_ONLY: {
                id: "viewStyleTitleOnly",
                label: i18n.gettext('Message titles')
            },
            PREVIEW: {
                id: "viewStylePreview",
                label: i18n.gettext('Message previews')
            },
            FULL_BODY: {
                id: "viewStyleFullBody",
                label: i18n.gettext('Complete messages')
            }
        }

        /**
         * The a cache for posts linked by segments
         * FIXME:  Remove once lazy loading is implemented
         * @type {string}
         */
        Assembl.segmentPostCache = {};

        /**
         * Current user
         * @type {User}
         */
        Assembl.currentUser = null;

        /**
         * Csrf token
         * @type {String}
         */
        Assembl.csrfToken = null;

        /**
         * Default ease for all kids of animation
         * @type {String}
         */
        Assembl.ease = 'ease';

        /**
         * The date format
         * @type {String}
         */
        Assembl.dateFormat = 'DD/MM/YYYY';

        /**
         * The datetime format
         * @type {string}
         */
        Assembl.datetimeFormat = 'DD/MM/YYYY HH:mm:ss';

        /**
         * The time for all animations related to lateralMenu
         * @type {Number}
         */
        Assembl.lateralMenuAnimationTime = 600;

        /**
         * Current dragged segment
         * @type {Segment}
         */
        Assembl.draggedSegment = null;

        /**
         * Current dragged idea
         * @type {Idea}
         */
        Assembl.draggedIdea = null;

        /**
         * Current dragged annotation
         * @type {Annotation}
         */
        Assembl.draggedAnnotation = null;

        /**
         * The lateral menu width
         * @type {number}
         */
        Assembl.lateralMenuWidth = 453;

        /**
         * The selection tooltip.
         * @type {jQuery}
         */
        Assembl.selectionTooltip = null;

        /**
         * Reference to dragbox
         * @type {HTMLDivElement}
         */
        Assembl.dragbox = null;

        /**
         * Qty of opened panels
         * @type {Number}
         */
        Assembl.openedPanels = 0;

        /**
         * get a view style definition by id
         * @param {messageViewStyle.id}
         * @return {messageViewStyle or undefined}
         */
        Assembl.getMessageViewStyleDefById = function(messageViewStyleId){
            var retval = _.find(Assembl.AVAILABLE_MESSAGE_VIEW_STYLES, function(messageViewStyle){ return messageViewStyle.id == messageViewStyleId; });
            return retval;
        }

        /**
         * Formats the url to the current api url
         * @param  {string} url
         * @return {string} The url formatted
         */
        Assembl.getApiUrl = function(url){
            var discussionId = $('#discussion-id').val();

            if( url[0] !== '/' ){
                url = '/' + url;
            }

            return '/api/v1/discussion/' + discussionId + url;
        }

        /**
         * Show or hide the given panel
         * @param  {String} panelName
         */
        Assembl.togglePanel = function(panelName){
            var panel = Assembl[panelName];
            if( panel === undefined ){
                return false;
            }

            if( panel.$el.hasClass('is-visible') ){
                Assembl.closePanel(panel);
            } else {
                Assembl.openPanel(panel);
            }
        }

        /**
         * Open the given panel
         * @param {backbone.View} panel
         */
        Assembl.openPanel = function(panel){
            if( panel.$el.hasClass('is-visible') ){
                return false;
            }

            Assembl.openedPanels += 1;
            $d.attr('data-panel-qty', Assembl.openedPanels);
            $d.removeClass('is-fullscreen');
            panel.$el.addClass('is-visible');

            Assembl.addPanelToStorage(panel.el.id);

            if( panel.button ) {

                panel.button.addClass('active');
            }
            Assembl.trigger("panel:open", [panel]);
        }

        /**
         * Close the given panel
         * @param {backbone.View} panel
         */
        Assembl.closePanel = function(panel){
            if( ! panel.$el.hasClass('is-visible') ){
                return false;
            }

            Assembl.openedPanels -= 1;
            $d.attr('data-panel-qty', Assembl.openedPanels);
            if( Assembl.isInFullscreen() ){
                $d.addClass('is-fullscreen');
            }

            panel.$el.removeClass('is-visible');

            Assembl.removePanelFromStorage(panel.el.id);

            if( panel.button ) {
                panel.button.removeClass('active');
            }
            Assembl.trigger("panel:close", [panel]);
        }

        /**
         * @return {Object} The Object with all panels in the localStorage
         */
        Assembl.getPanelsFromStorage = function(){
            var panels = JSON.parse(localStorage.getItem('panels')) || {};
            return panels;
        }

        /**
         * Adds a panel in the localStoage
         * @param {string} panelId
         * @return {Object} The current object
         */
        Assembl.addPanelToStorage = function(panelId){
            var panels = Assembl.getPanelsFromStorage();
            panels[panelId] = 'open';
            localStorage.setItem('panels', JSON.stringify(panels));

            return panels;
        }

        /**
         * Remove a panel from the localStorage by its id
         * @param  {string} panelId
         * @return {Object} The remaining panels
         */
        Assembl.removePanelFromStorage = function(panelId){
            var panels = Assembl.getPanelsFromStorage();
            delete panels[panelId];
            localStorage.setItem('panels', JSON.stringify(panels));

            return panels;
        }

        /**
         * @return {Object} The Object with mesagelistconfig in the localStorage
         */
        Assembl.getMessageListConfigFromStorage = function(){
            var messageListConfig = JSON.parse(localStorage.getItem('messageListConfig')) || {};
            return messageListConfig;
        }

        /**
         * Adds a panel in the localStorage
         * @param {Object} The Object with mesagelistconfig in the localStorage
         * @return {Object} The Object with mesagelistconfig in the localStorage
         */
        Assembl.setMessageListConfigToStorage = function(messageListConfig){
            localStorage.setItem('messageListConfig', JSON.stringify(messageListConfig));
            return messageListConfig;
        }

        /**
         * Checks if there is a panel in fullscreen mode
         * ( i.e.: there is only one open )
         * @return {Boolean}
         */
        Assembl.isInFullscreen = function(){
            return Assembl.openedPanels === 1;
        }

        /**
         * @return {Segment}
         */
        Assembl.getDraggedSegment = function(){
            var segment = Assembl.draggedSegment;
            Assembl.draggedSegment = null;

            if( segment ){
                delete segment.attributes.highlights;
            }

            return segment;
        }

        /**
         * @return {Idea}
         */
        Assembl.getDraggedIdea = function(){
            if( Assembl.ideaList && Assembl.draggedIdea ){
                Assembl.ideaList.removeIdea(Assembl.draggedIdea);
            }

            var idea = Assembl.draggedIdea;
            Assembl.draggedIdea = null;

            return idea;
        }


        /**
         * @return {Annotation}
         */
        Assembl.getDraggedAnnotation = function(){
            var annotation = Assembl.draggedAnnotation;
            Assembl.draggedAnnotation = null;

            return annotation;
        },

        /**
         * fulfill app.currentUser
         */
            Assembl.loadCurrentUser = function(){
                if( Assembl.users ){

                    var current_user_id = $('#user-id').val();

                    Assembl.currentUser = Assembl.users.getByNumericId(current_user_id) || Assembl.users.getUnknownUser();
                    Assembl.currentUser.fetchPermissionsFromScripTag();
                    Assembl.loadCsrfToken(true);
                    Assembl.trigger('user:loaded', [app.getCurrentUser()]);
                }
            }

        /**
         * @return {User}
         */
        Assembl.getCurrentUser = function(){
            return Assembl.currentUser || Assembl.users.getUnknownUser();
        }

        /**
         * fallback: synchronously load app.csrfToken
         */
        Assembl.loadCsrfToken = function(async){
            $.ajax('/api/v1/token', {
                async: async,
                dataType: 'text',
                success: function(data) {
                    Assembl.csrfToken = data;
                }
            });
            return Assembl.csrfToken;
        }

        /**
         * @return {User}
         */
        Assembl.getCsrfToken = function(){
            return Assembl.csrfToken || Assembl.loadCsrfToken(false);
        }

        /**
         * Return the Post related to the given annotation
         * @param {Annotation} annotation
         * @return {Message}
         */
        Assembl.getPostFromAnnotation = function(annotation){
            var span = $(annotation.highlights[0]),
                messageId = span.closest('[id^="'+this.ANNOTATOR_MESSAGE_BODY_ID_PREFIX+'"]').attr('id');

            return Assembl.messageList.messages.get(messageId.substr(this.ANNOTATOR_MESSAGE_BODY_ID_PREFIX.length));
        }


        /**
         * Saves the current annotation if there is any
         */
        Assembl.saveCurrentAnnotation = function(){
            if( Assembl.currentUser.can(Permissions.EDIT_EXTRACT) &&
                Assembl.messageList.annotatorEditor ){
                Assembl.messageList.annotatorEditor.element.find('.annotator-save').click();
            }
        }

        /**
         * Creates the selection tooltip
         */
        Assembl.createSelectionTooltip = function(){
            Assembl.selectionTooltip = $('<div>', { 'class': 'textbubble' } );
            $d.append(Assembl.selectionTooltip.hide());
        }

        /**
         * Returns a template from an script tag
         * @param {string} id The id of the script tag
         * @return {function} The Underscore.js _.template return
         */
        Assembl.loadTemplate = function(id){
            return _.template( $('#tmpl-'+id).html() );
        }

        /**
         * Return the select text on the document
         * @return {Selection}
         */
        Assembl.getSelectedText = function(){
            if( document.getSelection ){
                return document.getSelection();
            } else if( window.getSelection ){
                return window.getSelection();
            } else {
                var selection = document.selection && document.selection.createRange();
                return selection.text ? selection.text : false;
            }
        }

        /**
         * Shows the dragbox when user starts dragging an element
         * @param  {Event} ev The event object
         * @param  {String} text The text to be shown in the .dragbox
         */
        Assembl.showDragbox = function(ev, text){
            if( ev.originalEvent ){
                ev = ev.originalEvent;
            }

            if( Assembl.dragbox === null ){
                Assembl.dragbox = document.createElement('div');
                Assembl.dragbox.className = 'dragbox';
                Assembl.dragbox.setAttribute('hidden', 'hidden');

                $d.append(Assembl.dragbox);
            }

            Assembl.dragbox.removeAttribute('hidden');

            text = text || i18n.gettext('Extract');

            if( text.length > DRAGBOX_MAX_LENGTH ){
                text = text.substring(0, DRAGBOX_MAX_LENGTH) + '...';
            }
            Assembl.dragbox.innerHTML = text;

            if( ev.dataTransfer ) {
                ev.dataTransfer.dropEffect = 'all';
                ev.dataTransfer.effectAllowed = 'copy';
                ev.dataTransfer.setData("text/plain", text);
                ev.dataTransfer.setDragImage(app.dragbox, 10, 10);
            }

            $(ev.currentTarget).one("dragend", function(){
                Assembl.dragbox.setAttribute('hidden', 'hidden');
            });
        }

        /**
         * Return the current time
         * @return {timestamp}
         */
        Assembl.getCurrentTime = function(){
            return (new Date()).getTime();
        }

        /**
         * Capitalize the first letter of the string
         * @param {string} str
         * @return {string}
         */
        Assembl.capitalize = function(str){
            return str.charAt(0).toUpperCase() + str.slice(1);
        }

        /**
         * Format string function
         * @param {string} string
         * @param {string} ...
         * @return {string}
         */
        Assembl.format = function(str){
            var args = [].slice.call(arguments, 1);

            return str.replace(/\{(\d+)\}/g, function(a,b){
                return typeof args[b] != 'undefined' ? args[b] : a;
            });
        }

        /**
         * Format date
         * @param {Date|timestamp} date
         * @param {string} [format=app.dateFormat] The format
         * @return {string}
         */
        Assembl.formatDate = function(date, format){
            format = format || Assembl.dateFormat;

            if( date === null ){
                return '';
            }

            date = new Moment(date);
            return date.format(format);
        }

        /**
         * Format date time
         * @param {Date|timestamp} date
         * @param {String} [format=app.datetimeFormat] The format
         * @return {string}
         */
        Assembl.formatDatetime = function(date, format){
            return Assembl.formatDate(date, format || Assembl.datetimeFormat);
        }

        /**
         * Shows the context menu given the options
         * @param {Number} x
         * @param {Number} y
         * @param {Object} scope The scope where the functions will be executed
         * @param {Object<string:function>} items The items on the context menu
         */
        Assembl.showContextMenu = function(x, y, scope, items){
            Assembl.hideContextMenu();

            var menu = $('<div>').addClass('contextmenu');

            // Adjusting position
            if( (x + CONTEXT_MENU_WIDTH) > (window.innerWidth - 50) ){
                x = window.innerWidth - CONTEXT_MENU_WIDTH - 10;
            }

            menu.css({'top': y, 'left': x});

            _.each(items, function(func, text){
                var item = $('<a>').addClass('contextmenu-item').text(text);
                item.on('click', func.bind(scope) );
                menu.append( item );
            });

            $d.append( menu );
            window.setTimeout(function(){
                $d.on("click", app.hideContextMenu);
            });

            // Adjusting menu position
            var menuY = menu.height() + y,
                maxY = window.innerHeight - 50;

            if( menuY >= maxY ){
                menu.css({'top': maxY - menu.height() });
            }
        }

        /**
         * Removes all .contextmenu on the page
         * @param {Event} [ev=null] If given, checks to see if it was clicked outside
         */
        Assembl.hideContextMenu = function(ev){
            if( ev && ev.target.classList.contains('contextmenu')){
                return;
            }

            $('.contextmenu').remove();
            $d.off('click', app.hideContextMenu);
        }

        /**
         * Set the given Idea as the current one to be edited
         * @param  {Idea} [idea]
         */
        Assembl.setCurrentIdea = function(idea){
            if (idea != this.getCurrentIdea()) {
                Assembl.trigger('idea:select', [idea]);
            }
        }

        /**
         * Get the current Idea
         * @return {Idea}
         */
        Assembl.getCurrentIdea = function(){
            return Assembl.ideaPanel.idea;
        }

        /**
         * Returns an array with all segments for the given idea
         * @param {Idea} idea
         * @return {Array<Segment>}
         */
        Assembl.getSegmentsByIdea = function(idea){
            var id = idea.getId();
            return Assembl.segmentList && Assembl.segmentList.segments ? Assembl.segmentList.segments.where({idIdea:id}) : [];
        }

        /**
         * Returns the order number for a new root idea
         * @return {Number}
         */
        Assembl.getOrderForNewRootIdea = function(){
            var lastIdea = Assembl.ideaList.ideas.last();
            return lastIdea ? lastIdea.get('order') + 1 : 0;
        }

        /**
         * Returns the collection from the giving object's @type .
         * @param {BaseModel} item
         * @param {String} [type=item['@type']] The model type
         * @return {BaseCollection}
         */
        Assembl.getCollectionByType = function(item, type){
            type = type || item['@type'];

            switch(type){
                case Types.EXTRACT:
                    return Assembl.segmentList.segments;

                case Types.IDEA:
                case Types.ROOT_IDEA:
                    return Assembl.ideaList.ideas;

                case Types.POST:
                case Types.ASSEMBL_POST:
                case Types.SYNTHESIS_POST:
                case Types.IMPORTED_POST:
                case Types.EMAIL:
                    return Assembl.messageList.messages;

                case Types.USER:
                    return Assembl.users;

                case Types.SYNTHESIS:
                    return Assembl.syntheses;
            }

            return null;
        }

        /**
         * Shows the related segment from the given annotation
         * @param  {annotation} annotation
         */
        Assembl.showSegmentByAnnotation = function(annotation){
            var segment = Assembl.segmentList.segments.getByAnnotation(annotation);

            if( !segment ){
                return;
            }

            if( segment.get('idIdea') ){
                // It is in the ideaList
                Assembl.ideaPanel.showSegment(segment);
            } else {
                // It is in the segmentList
                Assembl.segmentList.showSegment(segment);
            }
        }

        /**
         * Shows the segment source in the better way related to the source
         * e.g.: If it is an email, opens it, if it is a webpage, open in another window ...
         * @param {Segment} segment
         */
        Assembl.showTargetBySegment = function(segment){
            var target = segment.get('target');

            switch(target['@type']){
                case 'Webpage':
                    window.open(target.url, "_blank");
                    break;

                default:
                    // This will treat:
                    // ['Email', 'Post', 'AssemblPost', 'SynthesisPost', 'ImportedPost']

                    var selector = Assembl.format('[data-annotation-id="{0}"]', segment.id);
                    Assembl.messageList.showMessageById(segment.get('idPost'), function(){
                        $(selector).highlight();
                    });
                    break;
            }
        }

        /**
         * Updates the order in the idea list
         */
        Assembl.updateIdealistOrder = function(){
            var children = Assembl.ideaList.ideas.where({ parentId: null }),
                currentOrder = 1;

            _.each(children, function(child){
                child.set('order', currentOrder);
                child.save();
                currentOrder += 1;
            });
        }

        /**
         * @see http://blog.snowfinch.net/post/3254029029/uuid-v4-js
         * @return {String} an uuid
         */
        Assembl.createUUID = function(){
            var uuid = "", i = 0, random;

            for (; i < 32; i++) {
                random = Math.random() * 16 | 0;

                if (i == 8 || i == 12 || i == 16 || i == 20) {
                    uuid += "-";
                }

                uuid += (i == 12 ? 4 : (i == 16 ? (random & 3 | 8) : random)).toString(16);
            }

            return uuid;
        }

        /**
         * Given the string in the format "local:ModelName/{id}" returns the id
         * @param  {String} str
         * @return {String}
         */
        Assembl.extractId = function(str){
            return str.split('/')[1];
        }

        /**
         * @param  {Number} userID The user's ID
         * @param  {Number} [size=44] The avatar size
         * @return {String} The avatar's url formatted with the given size
         */
        Assembl.formatAvatarUrl = function(userID, size){
            size = size || 44;
            return Assembl.format("/user/id/{0}/avatar/{1}", userID, size);
        }

        /**
         * Returns a fancy date (ex: a few seconds ago)
         * @return {String}
         */
        Assembl.getDateFormated = function(date){
            var momentDate = moment(date);
            return momentDate ? momentDate.fromNow() : momentDate;
        }

        /**
         * @param  {String} html
         * @return {String} The new string without html tags
         */
        Assembl.stripHtml = function(html){
            return html ? $.trim( $('<div>'+html+'</div>').text() ) : html;
        }

        /**
         * Sets the given panel as fullscreen closing all other ones
         * @param {Panel} targetPanel
         */
        Assembl.setFullscreen = function(targetPanel){
            var panels = [
                Assembl.ideaList,
                Assembl.segmentList,
                Assembl.ideaPanel,
                Assembl.messageList,
                Assembl.synthesisPanel
            ];

            _.each(panels, function(panel){
                if( targetPanel !== panel ){
                    Assembl.closePanel(panel);
                    $d.addClass('is-fullscreen');
                }
            });

            Assembl.setCurrentIdea(null);
        }

        /**
         * @event
         */
        Assembl.onDropdownClick = function(ev){
            var dropdown = $(ev.target);

            if( !dropdown.hasClass("dropdown-label") ){
                return;
            }

            var parent = dropdown.parent();

            var onMouseLeave = function(ev){
                parent.removeClass('is-open');
            };

            if( parent.hasClass('is-open') ){
                onMouseLeave();
                return;
            }

            parent.addClass('is-open');
            $d.one('click', onMouseLeave);
        }

        /**
         * @event
         */
        Assembl.onAjaxError = function( ev, jqxhr, settings, exception ){
            var message = i18n.gettext('ajax error message:');
            message = "url: " + settings.url + "\n" + message + "\n" + exception;

            alert( message );
        }

        /**
         * Removes all tooltips from the screen
         */
        Assembl.cleanTooltips = function(){
            $('.tipsy').remove();
        }

        Assembl.setLocale = function(locale){
            document.cookie = "_LOCALE_="+locale+"; path=/";
            location.reload(true);
        }

        /**
         * @init
         */
        Assembl.initTooltips = function(){
            // reference: http://onehackoranother.com/projects/jquery/tipsy/

            $('[data-tooltip]').tipsy({
                delayIn: 400,
                live: true,
                gravity: function(){ return this.getAttribute('data-tooltip-position') || 's'; },
                title: function() { return this.getAttribute('data-tooltip'); },
                opacity: 0.95
            });
        }

        /**
         * @init
         */
        Assembl.initClipboard = function(){
            if( ! Assembl.clipboard ){
                ZeroClipboard.setDefaults( { moviePath: '/static/js/bower/zeroclipboard/ZeroClipboard.swf' } );
                Assembl.clipboard = new ZeroClipboard();
                Assembl.clipboard.on('complete', function(client, args){
                    // Nothing to do, nowhere to go uouuu ...
                });

                Assembl.clipboard.on('mouseover', function(client, args){
                    $(this).trigger('mouseover');
                });

                Assembl.clipboard.on('mouseout', function(client, args){
                    $(this).trigger('mouseout');
                });
            }

            $('[data-copy-text]').each(function(i, el){
                var text = el.getAttribute('data-copy-text');
                text = Assembl.format('{0}//{1}/{2}{3}', location.protocol, location.host, DISCUSSION_SLUG, text);
                el.removeAttribute('data-copy-text');

                el.setAttribute('data-clipboard-text', text);
                Assembl.clipboard.glue(el);
            });
        }

        /**
         * @init
         * inits ALL app components
         */
        Assembl.init = function(){
            Assembl.loadCurrentUser();

            $d.removeClass('preload');
            Assembl.createSelectionTooltip();
            Assembl.initTooltips();

            $d.on('click', '.dropdown-label', Assembl.onDropdownClick);
            $d.on('ajaxError', Assembl.onAjaxError);

            Assembl.on('render', function(){
                Assembl.cleanTooltips();
                window.setTimeout(Assembl.initTooltips, 500);
            });
        }

        return Assembl;

    });