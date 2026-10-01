
  (function(){
    var DKEY="esr_pwa_dismiss", dp=null, bar=null;
    function isDismissed(){try{var v=localStorage.getItem(DKEY);if(!v)return false;return (Date.now()-parseInt(v,10))<1209600000;}catch(e){return false;}}
    function setDismissed(){try{localStorage.setItem(DKEY,String(Date.now()));}catch(e){}}
    function isStandalone(){return (window.matchMedia&&window.matchMedia("(display-mode: standalone)").matches)||window.navigator.standalone===true;}
    function isIOS(){var ua=navigator.userAgent||"";if(/CriOS|FxiOS|EdgiOS/i.test(ua))return false;if(/iPhone|iPad|iPod/i.test(ua))return true;return /Macintosh/i.test(ua)&&navigator.maxTouchPoints>1;}
    function remove(){if(bar){var b=bar;bar=null;b.classList.remove("pwa-show");setTimeout(function(){if(b&&b.parentNode)b.parentNode.removeChild(b);},400);}}
    function show(mode,force){
      if(bar||(!force&&isDismissed())||isStandalone())return;
      if(!document.body){document.addEventListener("DOMContentLoaded",function(){show(mode);});return;}
      bar=document.createElement("div");
      bar.id="pwa-bar";bar.setAttribute("role","dialog");bar.setAttribute("aria-label","Install Explore Suriname");
      var ic='<img class="pwa-ic" src="/icons/icon-192.png" width="42" height="42" alt="">';
      var tt,sb,btns;
      if(mode==="ios"){
        tt="Add Explore Suriname";
        sb="Tap the Share button, then Add to Home Screen.";
        btns='<button class="pwa-x" type="button" aria-label="Dismiss">&times;</button>';
      }else{
        tt="Install Explore Suriname";
        sb="Live SRD rates and offline access on your home screen.";
        btns='<button class="pwa-go" type="button">Install</button><button class="pwa-x" type="button" aria-label="Dismiss">&times;</button>';
      }
      bar.innerHTML=ic+'<div class="pwa-tx"><div class="pwa-tt">'+tt+'</div><div class="pwa-sb">'+sb+'</div></div>'+btns;
      document.body.appendChild(bar);
      requestAnimationFrame(function(){requestAnimationFrame(function(){if(bar)bar.classList.add("pwa-show");});});
      var go=bar.querySelector(".pwa-go");
      if(go){go.addEventListener("click",function(){
        if(!dp){remove();return;}
        dp.prompt();
        dp.userChoice.then(function(c){setDismissed();dp=null;hideNav();remove();}).catch(function(){remove();});
      });}
      bar.querySelector(".pwa-x").addEventListener("click",function(){setDismissed();remove();});
    }
    function navEl(){return document.getElementById("pwa-nav");}
    function revealNav(){var n=navEl();if(n&&!isStandalone())n.style.display="inline-flex";}
    function hideNav(){var n=navEl();if(n)n.style.display="none";}
    window.pwaInstall=function(){
      if(dp){dp.prompt();dp.userChoice.then(function(c){setDismissed();dp=null;hideNav();}).catch(function(){});return;}
      if(isIOS()){show("ios",true);}
    };
    window.addEventListener("beforeinstallprompt",function(e){e.preventDefault();dp=e;revealNav();show("android");});
    window.addEventListener("appinstalled",function(){setDismissed();hideNav();remove();});
    if(isIOS()){
      var iosInit=function(){revealNav();setTimeout(function(){show("ios");},1400);};
      if(document.readyState==="loading"){document.addEventListener("DOMContentLoaded",iosInit);}
      else{iosInit();}
    }
    document.addEventListener("DOMContentLoaded",function(){if(dp)revealNav();});
  })();
  