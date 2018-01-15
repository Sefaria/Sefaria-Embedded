var state = {
    languageCode : null
};


var init = function(){
    setInitialState();
    bindLanguageSwitcher();
};

var setInitialState = function(){
    state.languageCode = document.getElementsByTagName('head')[0]
        .getAttribute("data-languageCode");
};

var bindLanguageSwitcher = function(){
    document.getElementsByClassName('languageToggle')[0]
        .addEventListener("click", toggleLanguage);
};

var toggleLanguage = function(){
    //Toggle the view
    if(state.languageCode === "he"){
        Array.prototype.forEach.call(document.getElementsByClassName('en'), function(el) {
            el.removeAttribute("hidden");
        });

        Array.prototype.forEach.call(document.getElementsByClassName('he'), function(el) {
            el.setAttribute("hidden", null);
        });
    }

    if(state.languageCode === "en"){
        Array.prototype.forEach.call(document.getElementsByClassName('en'), function(el) {
            el.setAttribute("hidden", null);
        });

        Array.prototype.forEach.call(document.getElementsByClassName('he'), function(el) {
            el.removeAttribute("hidden");
        });
    }
    
    //Toggle the state
    if(state.languageCode === "he"){
        state.languageCode = "en";
    }
    
    else if(state.languageCode === "en"){
        state.languageCode = "he";
    }
}

window.onload = init();