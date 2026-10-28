"use strict";

(function (){
    if (document.readyState != 'loading'){
        enableSmartSearchEntitySuggestions();
    } else {
        window.addEventListener('load', enableSmartSearchEntitySuggestions);
    }

    function enableSmartSearchEntitySuggestions() {
        //key press codes used in interactions
        var UP_ARROW = 38,
            DOWN_ARROW = 40,
            CARRIAGE_RETURN = 13,
            TAB = 9,
            ESCAPE = 27;

        //site-wide main and mobile search boxes
        var globalSearchBox = document.getElementById('global-search-box');
        var globalSearchBoxMobile = document.getElementById('global-search-box-mobile');
        var companyPersonLookup = document.getElementById('edgar-company-person');
        if(!globalSearchBoxMobile) globalSearchBoxMobile = document.getElementById('mobile-search-box');
        if(!globalSearchBoxMobile) globalSearchBoxMobile = document.getElementById('search-box');
        var activeHintsKeys,
            activeInputBoxID,
            autoselectFirstHint = false,
            waitingForHintsOnKeySubmit = false;
        var hintsContainer = document.createElement('div');
        hintsContainer.className = "smart-search-container";
        hintsContainer.innerHTML = '<div class="smart-search-entity-hints">' +
            '<div class="smart-search-section smart-search-section__edgar">' +
            '<div class="smart-search-heading smart-search-heading__edgar_filings"><span class="smart-search-EDGAR">EDGAR</span><span class="smart-search-resources">| Filings</span></div>' +
            '<table class="smart-search-entity-hints" width="450"></table>' +
            '<a class="smart-search-edgar-full-text" href="#">Search for &quot;<span class="smart-search-search-text"></span>&quot; in EDGAR filings</a>' +
            '</div>' +
            '<div class="smart-search-section smart-search-section__webpages_documents">' +
            '<div class="smart-search-heading smart-search-heading__webpages_documents"><span class="smart-search-SEC-gov">SEC.gov</span><span class="smart-search-resources">| Webpages &amp; Documents</span></div>' +
            '<div class="smart-search-sec-gov-website">Search for &quot;<span class="smart-search-search-text"></span>&quot; on SEC.gov</div>' +
            '</div>' +
            '</div>';
        hintsContainer.querySelector('div.smart-search-sec-gov-website').addEventListener('click', function searchSecGov(){
            var searchContainer = hintsContainer.parentElement;
            searchContainer.querySelector('input').form.submit();
        });
        function searchBoxFocus(event){
            var label = this.parentElement.querySelector('label');
            if(label && label.style) {
                label.style.display = 'none'
            }
        }

        function searchBoxKeyDown(event) { //capture tab on keydown as focus is lost before keyup can fire
            var keyCode = event.keyCode || event.which;
            if(event.shiftKey && keyCode==TAB) { 
                //shift was down when tab was pressed
                event.stopPropagation();
                event.preventDefault();
                hideCompanyHints();
                const allTabbable = getKeyboardFocusableElements(document);
                const prevTabbable = allTabbable[allTabbable.indexOf(document.activeElement) - 1];
                if (prevTabbable) {
                    prevTabbable.focus();
                }
            }
            else if(keyCode==TAB){
                event.stopPropagation();
                event.preventDefault();
                hideCompanyHints();
                var thisForm = this.closest('form');
                const allTabbable = getKeyboardFocusableElements(thisForm);
                const nextTabbable = allTabbable[allTabbable.indexOf(document.activeElement) + 1];
                if (nextTabbable) {
                    nextTabbable.focus();
                }
            }
            else if(keyCode == CARRIAGE_RETURN) {
                if(activeHintsKeys == event.target.value){
                    var selectedHint = hintsContainer.querySelector('.smart-search-selected-hint');
                    if(selectedHint){
                        event.stopPropagation();
                        event.preventDefault();
                        selectedHint.click(this);
                    }
                } else {
                    if(autoselectFirstHint){
                        event.stopPropagation();
                        event.preventDefault();
                        waitingForHintsOnKeySubmit = true;
                        window.setTimeout(function(){  //give time for hints to return to address speed-typing
                            if(waitingForHintsOnKeySubmit) event.target.form.submit();
                        }, 700);
                    }
                }
            }
        }

        /**
        * Gets keyboard-focusable elements within a specified element
        * @param {HTMLElement} [element=document] element
        * @returns {Array}
        */
        function getKeyboardFocusableElements (element = document) {
            return [
            ...element.querySelectorAll(
                'a[href], button, input:not([type="hidden"]), textarea, select, details,[tabindex]:not([tabindex="-1"])'
            )
            ].filter(
            el => !el.hasAttribute('disabled') && !el.getAttribute('aria-hidden') && !el.closest('[hidden]') && !el.closest('[style*="display: none"]')
            )
        }

        function searchBoxKeyUp(event){
            var keyCode = event.keyCode || event.which;
            if(keyCode==ESCAPE){  //return or ESC
                hideCompanyHints();
            } else {
                if(keyCode!=TAB && keyCode!=CARRIAGE_RETURN && keyCode!=UP_ARROW && keyCode != DOWN_ARROW){
                    getCompanyHints(this, this.value)
                }
            }
            var hintCount = hintsContainer.querySelectorAll('table.smart-search-entity-hints tr.smart-search-hint').length;
            if(hintCount && (keyCode == UP_ARROW || keyCode == DOWN_ARROW)){  //up arrow or down arrow
                var oldSelected = hintsContainer.querySelector('.smart-search-selected-hint'),
                    oldSelectedIndex;
                if (oldSelected) {
                    oldSelected.className = oldSelected.className.replace('smart-search-selected-hint','').trim(); //remove the smart-search-selected-hint class
                    if(!isNaN(oldSelected.rowIndex)){
                        oldSelectedIndex = oldSelected.rowIndex;
                    } else {
                        var className = oldSelected.className;
                        if(className.indexOf('smart-search-edgar-full-text') !== -1) oldSelectedIndex = hintCount;
                        if(className.indexOf('smart-search-sec-gov-website') !== -1) oldSelectedIndex = hintCount + 1;
                    }
                }
                var newSelectedIndex = Math.min(Math.max((oldSelected ? oldSelectedIndex : -1) + (keyCode==UP_ARROW?-1:1) ,0), hintCount+1); //hintCount-1+2 = includes the two permanent hints after the table2222
                if(newSelectedIndex < hintCount) hintsContainer.querySelectorAll('table.smart-search-entity-hints tr.smart-search-hint').item(newSelectedIndex).className ='smart-search-hint smart-search-selected-hint';
                if(newSelectedIndex == hintCount) hintsContainer.querySelector('.smart-search-edgar-full-text').className ='smart-search-edgar-full-text smart-search-selected-hint';
                if(newSelectedIndex == hintCount + 1) hintsContainer.querySelector('.smart-search-sec-gov-website').className ='smart-search-sec-gov-website smart-search-selected-hint';
            }
        }
        function searchBoxBlur(){if(!window.smartSearchStay) setTimeout(hideCompanyHints, 200)}

        var id;
        if(globalSearchBox) {
            globalSearchBox.className = '';
            id = globalSearchBox.id;
            globalSearchBox = document.getElementById(id);
            globalSearchBox.addEventListener('keydown', searchBoxKeyDown);
            globalSearchBox.addEventListener('keyup', searchBoxKeyUp);
            globalSearchBox.addEventListener('blur', searchBoxBlur);
            globalSearchBox.addEventListener('focus', searchBoxFocus);
            var searchContainer = globalSearchBox.parentElement;
        }
        if(globalSearchBoxMobile) {
            id = globalSearchBoxMobile.id;
            globalSearchBoxMobile = document.getElementById(id);
            globalSearchBoxMobile.addEventListener('keydown', searchBoxKeyDown);
            globalSearchBoxMobile.addEventListener('keyup', searchBoxKeyUp);
            globalSearchBoxMobile.addEventListener('blur', searchBoxBlur);
            globalSearchBoxMobile.addEventListener('focus', searchBoxFocus);
        }
      if(companyPersonLookup) {
        id = companyPersonLookup.id;
        autoselectFirstHint = true;
        companyPersonLookup = document.getElementById(id);
        companyPersonLookup.addEventListener('keydown', searchBoxKeyDown);
        companyPersonLookup.addEventListener('keyup', searchBoxKeyUp);
        companyPersonLookup.addEventListener('blur', searchBoxBlur);
        companyPersonLookup.addEventListener('focus', searchBoxFocus);
      }

        function getCompanyHints(control, keysTyped){
            if(keysTyped && keysTyped.trim()){
                var overlay = control.parentNode.querySelector('label.overlabel');
                if(overlay && overlay.style) overlay.style.display = 'none';  //hide the overlay
                var hintsURL = 'https://efts.sec.gov/LATEST/search-index';
                // var hintsURL = 'https://sec.lndo.site/modules/custom/sec_edgar/templates/examples/dropdown_button.json'; // dev
                var start = new Date();
                var request = new XMLHttpRequest();
                request.open('GET', hintsURL + "?keysTyped=" + keysTyped, true);
                // request.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded; charset=UTF-8');
                request.onload = function() {
                    if (this.status >= 200 && this.status < 400 && keysTyped==control.value) {
                        if(activeInputBoxID != control.id){
                            searchContainer = control.parentElement;
                            var bbInput = control.getBoundingClientRect(),
                                bbForm = searchContainer.getBoundingClientRect();
                            var rightOffset = bbForm.right - bbInput.right;
                            searchContainer.appendChild(hintsContainer);
                            var bbHints = hintsContainer.getBoundingClientRect();
                            var hintsDivStyle = hintsContainer.querySelector('.smart-search-entity-hints').style;
                            if(bbInput.left < window.innerWidth - bbInput.right){
                                hintsDivStyle.left = '0px';
                                hintsDivStyle.right = 'auto';
                                hintsDivStyle.top = (bbInput.top + control.offsetHeight - bbHints.top) + 'px';
                            } else {
                                hintsDivStyle.left = 'auto';
                                hintsDivStyle.right = rightOffset+'px';
                                hintsDivStyle.top = control.offsetHeight + 'px';
                            }
                            activeInputBoxID = control.id;
                        }
                        autoselectFirstHint = false;
                        if (companyPersonLookup && control.id === companyPersonLookup.id) {
                          autoselectFirstHint = true;
                        }
                        activeHintsKeys = keysTyped;
                        var data = JSON.parse(this.response);
                        console.log('round-trip execution time to '+hintsURL+ ' for "' + keysTyped + '" = '+((new Date()).getTime()-start.getTime())+' ms');
                        var hints = data.hits.hits;
                        var hintDivs = [];
                        var rgxKeysTyped = new RegExp('('+keysTyped.trim()+')','gi');
                        if(hints.length){
                            for(var h=0;h<hints.length;h++){
                                var CIK = hints[h]._id,
                                    entityName = hints[h]._source.entity,
                                    href = '/edgar/browse/?CIK='+CIK + (hints[h]._source.tickers?'&owner=exclude':'');
                                hintDivs.push('<tr class="smart-search-hint' +(autoselectFirstHint && h==0 ? ' smart-search-selected-hint' : '')
                                    + '" data="'+ entityName + ' (CIK '+formatCIK(CIK)+')"><td class="smart-search-hint-entity">'
                                    + '<a href="'+href+'">'+(entityName||'').replace(rgxKeysTyped, '<b>$1</b>')+'</a>'
                                    + '</td><td class="smart-search-hint-cik"><a href="'+href+'">' + ((' CIK&nbsp;'+ formatCIK(CIK))||'')+'</a></td></tr>');
                            }
                            var hintsTable = hintsContainer.querySelector('table.smart-search-entity-hints');
                            hintsTable.innerHTML = hintDivs.join('');
                            for( var r=0; r< hintsTable.rows.length; r++){
                                hintsTable.rows[r].addEventListener('click', hintClick)
                            }
                            var spans = hintsContainer.querySelectorAll('div.smart-search-entity-hints span.smart-search-search-text');
                            for(var i=0; i<spans.length; i++){
                                spans[i].innerHTML=keysTyped;
                            }
                            hintsContainer.querySelector('.smart-search-edgar-full-text').setAttribute('href','/edgar/search/#/q='+encodeURIComponent(keysTyped.trim())+ '&dateRange=all&startdt=1995-06-01&enddt=2020-04-21');
                            hintsContainer.querySelector('div.smart-search-entity-hints').style.display = 'block';
                            if(waitingForHintsOnKeySubmit){
                                var selectedHint = hintsContainer.querySelector('.smart-search-selected-hint');
                                if(selectedHint){
                                    waitingForHintsOnKeySubmit = false;
                                    selectedHint.click(this);
                                }
                            }
                        } else {
                            hideCompanyHints();
                        }
                    } else {
                        console.log('error fetching from '+hintsURL+'; status '+this.status);
                    }
                };
                request.onerror = function() {
                    console.log('error connecting to '+hintsURL);
                };
                request.send();
            } else {
                hideCompanyHints();
            }
            function formatCIK(unpaddedCIK){ //accept int or string and return string with padded zero
                var paddedCik = unpaddedCIK.toString();
                while(paddedCik.length<10) paddedCik = '0' + paddedCik;
                return paddedCik;
            }
            function hintClick(evt){
                this.querySelector('a').click();
            }
        }

        function hideCompanyHints(){
            var hintContainer = hintsContainer.querySelector('div.smart-search-entity-hints');
            hintContainer.style.display = 'none';
            hintContainer.querySelector('table.smart-search-entity-hints').innerHTML = '';  //remove the hint rows
        }
    }
})();
