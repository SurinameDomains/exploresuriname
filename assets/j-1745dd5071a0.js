
  /* PWA install (29 Oct 2026): phones and tablets only, never on desktop.
     Android/Chromium: our bar + the browser's own install dialog (beforeinstallprompt).
     iPhone/iPad: Apple offers no install API, so the bar opens a 3-step guide matched to the
     browser (Safari 26+, older Safari, Chrome) with the button names in the phone's language. */
  (function(){
    var DKEY="esr_pwa_dismiss", dp=null, bar=null, sheet=null;
    var UA=navigator.userAgent||"";
    var PL=((document.documentElement.getAttribute("lang")||"en")+"").toLowerCase().slice(0,2);
    var T={
      en:{tA:"Install Explore Suriname",sA:"Live SRD rates and offline access on your home screen.",go:"Install",
          tI:"Put Explore Suriname on your Home Screen",sI:"Opens full screen like an app. Free, no App Store.",how:"Show me how",
          hd:"Add to your Home Screen in 3 taps",ok:"Got it",x:"Close",
          s26:["Tap {dots} next to the address bar, then tap {share}.","Scroll down and tap {add}.","Keep the web app switch on and tap {addbtn}."],
          sOld:["Tap the Share button {shareic} in the toolbar.","Scroll down and tap {add}.","Tap {addbtn}. The icon now sits on your Home Screen."],
          sCr:["Tap the Share button {shareic} next to the address bar.","Tap {add} (scroll down if needed).","Tap {addbtn}."]},
      nl:{tA:"Installeer Explore Suriname",sA:"Live SRD-koersen en offline toegang op je beginscherm.",go:"Installeren",
          tI:"Zet Explore Suriname op je beginscherm",sI:"Opent schermvullend als een app. Gratis, zonder App Store.",how:"Laat zien hoe",
          hd:"In 3 tikken op je beginscherm",ok:"Begrepen",x:"Sluiten",
          s26:["Tik op {dots} naast de adresbalk en daarna op {share}.","Scroll omlaag en tik op {add}.","Laat de webapp-schakelaar aan en tik op {addbtn}."],
          sOld:["Tik op de deelknop {shareic} in de werkbalk.","Scroll omlaag en tik op {add}.","Tik op {addbtn}. Het icoon staat nu op je beginscherm."],
          sCr:["Tik op de deelknop {shareic} naast de adresbalk.","Tik op {add} (scroll zo nodig omlaag).","Tik op {addbtn}."]},
      es:{tA:"Instala Explore Suriname",sA:"Tipos de cambio del SRD en vivo y acceso sin conexión en tu pantalla de inicio.",go:"Instalar",
          tI:"Pon Explore Suriname en tu pantalla de inicio",sI:"Se abre a pantalla completa como una app. Gratis, sin App Store.",how:"Muéstrame cómo",
          hd:"En tu pantalla de inicio en 3 toques",ok:"Entendido",x:"Cerrar",
          s26:["Toca {dots} junto a la barra de direcciones y luego {share}.","Desplázate hacia abajo y toca {add}.","Deja activado el interruptor de app web y toca {addbtn}."],
          sOld:["Toca el botón Compartir {shareic} en la barra de herramientas.","Desplázate hacia abajo y toca {add}.","Toca {addbtn}. El icono aparecerá en tu pantalla de inicio."],
          sCr:["Toca el botón Compartir {shareic} junto a la barra de direcciones.","Toca {add} (desplázate hacia abajo si hace falta).","Toca {addbtn}."]},
      fr:{tA:"Installer Explore Suriname",sA:"Taux du SRD en direct et accès hors ligne sur votre écran d’accueil.",go:"Installer",
          tI:"Ajoutez Explore Suriname à votre écran d’accueil",sI:"S’ouvre en plein écran comme une app. Gratuit, sans App Store.",how:"Comment faire",
          hd:"Sur votre écran d’accueil en 3 gestes",ok:"Compris",x:"Fermer",
          s26:["Touchez {dots} à côté de la barre d’adresse, puis {share}.","Faites défiler et touchez {add}.","Laissez l’option app web activée et touchez {addbtn}."],
          sOld:["Touchez le bouton Partager {shareic} dans la barre d’outils.","Faites défiler et touchez {add}.","Touchez {addbtn}. L’icône apparaît sur votre écran d’accueil."],
          sCr:["Touchez le bouton Partager {shareic} à côté de la barre d’adresse.","Touchez {add} (faites défiler si besoin).","Touchez {addbtn}."]},
      pt:{tA:"Instale o Explore Suriname",sA:"Câmbio do SRD ao vivo e acesso offline na sua tela de início.",go:"Instalar",
          tI:"Coloque o Explore Suriname na sua tela de início",sI:"Abre em tela cheia como um app. Grátis, sem App Store.",how:"Mostrar como",
          hd:"Na sua tela de início em 3 toques",ok:"Entendi",x:"Fechar",
          s26:["Toque em {dots} ao lado da barra de endereço e depois em {share}.","Role para baixo e toque em {add}.","Deixe a opção de app web ativada e toque em {addbtn}."],
          sOld:["Toque no botão Compartilhar {shareic} na barra de ferramentas.","Role para baixo e toque em {add}.","Toque em {addbtn}. O ícone aparece na sua tela de início."],
          sCr:["Toque no botão Compartilhar {shareic} ao lado da barra de endereço.","Toque em {add} (role para baixo se precisar).","Toque em {addbtn}."]},
      zh:{tA:"安装 Explore Suriname",sA:"在主屏幕上查看实时 SRD 汇率，离线也能用。",go:"安装",
          tI:"把 Explore Suriname 添加到主屏幕",sI:"像 App 一样全屏打开。免费，无需 App Store。",how:"查看步骤",
          hd:"三步添加到主屏幕",ok:"知道了",x:"关闭",
          s26:["轻点地址栏旁的 {dots}，再轻点{share}。","向下滚动，轻点{add}。","保持网页 App 开关打开，然后轻点{addbtn}。"],
          sOld:["轻点工具栏中的共享按钮 {shareic}。","向下滚动，轻点{add}。","轻点{addbtn}，图标就会出现在主屏幕上。"],
          sCr:["轻点地址栏旁的共享按钮 {shareic}。","轻点{add}（如有需要请向下滚动）。","轻点{addbtn}。"]}
    };
    var t=T[PL]||T.en;
    /* iOS button names follow the PHONE's language (navigator.language), not the page language */
    function sysLabels(){
      var l=((navigator.language||"en")+"").toLowerCase();
      if(l.indexOf("nl")===0)return {share:"Deel",add:"Zet op beginscherm",addbtn:"Voeg toe"};
      if(l.indexOf("es-es")===0)return {share:"Compartir",add:"Añadir a pantalla de inicio",addbtn:"Añadir"};
      if(l.indexOf("es")===0)return {share:"Compartir",add:"Agregar a pantalla de inicio",addbtn:"Agregar"};
      if(l.indexOf("fr")===0)return {share:"Partager",add:"Sur l’écran d’accueil",addbtn:"Ajouter"};
      if(l.indexOf("pt-pt")===0)return {share:"Partilhar",add:"Adicionar ao ecrã principal",addbtn:"Adicionar"};
      if(l.indexOf("pt")===0)return {share:"Compartilhar",add:"Adicionar à Tela de Início",addbtn:"Adicionar"};
      if(l.indexOf("zh-tw")===0||l.indexOf("zh-hk")===0||l.indexOf("zh-hant")===0)return {share:"分享",add:"加入主畫面",addbtn:"加入"};
      if(l.indexOf("zh")===0)return {share:"共享",add:"添加到主屏幕",addbtn:"添加"};
      return {share:"Share",add:"Add to Home Screen",addbtn:"Add"};
    }
    var IC_SHARE='<svg class="pwa-gl" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="#0a84ff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3v12M8 7l4-4 4 4"/><path d="M6 11H5v10h14V11h-1"/></svg>';
    var IC_ADD='<svg class="pwa-gl" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><rect x="4" y="4" width="16" height="16" rx="4"/><path d="M12 8v8M8 12h8"/></svg>';
    var IC_DOTS='<span class="pwa-dots" aria-label="•••">•••</span>';
    function isDismissed(){try{var v=localStorage.getItem(DKEY);if(!v)return false;return (Date.now()-parseInt(v,10))<1209600000;}catch(e){return false;}}
    function setDismissed(){try{localStorage.setItem(DKEY,String(Date.now()));}catch(e){}}
    function isStandalone(){return (window.matchMedia&&window.matchMedia("(display-mode: standalone)").matches)||window.navigator.standalone===true;}
    function isAppleTouch(){return /iPhone|iPad|iPod/i.test(UA)||(/Macintosh/i.test(UA)&&navigator.maxTouchPoints>1);}
    function isMobile(){
      if(isAppleTouch())return true;
      if(/Android|Mobile/i.test(UA))return true;
      try{if(navigator.userAgentData&&navigator.userAgentData.mobile===true)return true;}catch(e){}
      return false;
    }
    /* which iOS browser can add to the Home Screen: "s26" Safari 26+, "sOld" older Safari, "sCr" Chrome; "" = none
       (in-app browsers such as Facebook/Instagram/TikTok, Firefox, Edge: no guide) */
    function iosKind(){
      if(!isAppleTouch())return "";
      if(/CriOS/.test(UA))return "sCr";
      if(/FxiOS|EdgiOS|OPiOS|GSA|FBAN|FBAV|FB_IAB|Instagram|musical_ly|Bytedance|TikTok|Snapchat|Line|LinkedInApp|Twitter|WhatsApp/i.test(UA))return "";
      if(UA.indexOf("Safari/")<0)return "";
      var i=UA.indexOf("Version/"),v=i<0?0:parseInt(UA.substr(i+8),10)||0;
      return v>=26?"s26":"sOld";
    }
    var MOBILE=isMobile(), IOSK=iosKind();
    function track(n,p){
      p=p||{};p.pwa_platform=IOSK?("ios-"+IOSK):(/Android/i.test(UA)?"android":"other");
      var tries=0;
      (function send(){
        var d=window.dataLayer||[],ok=false;
        for(var i=0;i<d.length;i++){if(d[i]&&d[i][0]==="config"){ok=true;break;}}
        if(!ok&&tries++<20){setTimeout(send,1500);return;}
        if(!ok)return;
        try{window.gtag("event",n,p);}catch(e){}
      })();
    }
    function remove(){if(bar){var b=bar;bar=null;b.classList.remove("pwa-show");setTimeout(function(){if(b&&b.parentNode)b.parentNode.removeChild(b);},400);}}
    function closeSheet(){if(sheet){var s=sheet;sheet=null;s.classList.remove("pwa-show");setTimeout(function(){if(s&&s.parentNode)s.parentNode.removeChild(s);},350);}}
    function fill(s,lb){
      return s.replace("{dots}",IC_DOTS).replace("{shareic}",IC_SHARE)
              .replace("{share}","<b>"+lb.share+"</b>")
              .replace("{add}",IC_ADD+"<b>"+lb.add+"</b>")
              .replace("{addbtn}","<b>"+lb.addbtn+"</b>");
    }
    function openSheet(){
      if(sheet||!IOSK)return;
      remove();
      var lb=sysLabels(),st=t[IOSK]||t.sOld,li="";
      for(var i=0;i<st.length;i++){li+='<li><span class="pwa-n">'+(i+1)+'</span><span class="pwa-st">'+fill(st[i],lb)+'</span></li>';}
      sheet=document.createElement("div");
      sheet.id="pwa-sheet";sheet.setAttribute("role","dialog");sheet.setAttribute("aria-modal","true");sheet.setAttribute("aria-label",t.hd);
      sheet.innerHTML='<div class="pwa-bd"></div><div class="pwa-pn">'+
        '<button class="pwa-x" type="button" aria-label="'+t.x+'">&times;</button>'+
        '<div class="pwa-hd"><img class="pwa-ic" src="/icons/icon-192.png" width="48" height="48" alt=""><div class="pwa-tt">'+t.hd+'</div></div>'+
        '<ol class="pwa-ol">'+li+'</ol>'+
        '<button class="pwa-ok" type="button">'+t.ok+'</button></div>';
      document.body.appendChild(sheet);
      requestAnimationFrame(function(){requestAnimationFrame(function(){if(sheet)sheet.classList.add("pwa-show");});});
      var done=function(){setDismissed();closeSheet();};
      sheet.querySelector(".pwa-x").addEventListener("click",done);
      sheet.querySelector(".pwa-bd").addEventListener("click",done);
      sheet.querySelector(".pwa-ok").addEventListener("click",function(){track("pwa_ios_ok");done();});
      try{sheet.querySelector(".pwa-ok").focus({preventScroll:true});}catch(e){}
      track("pwa_ios_steps");
    }
    function show(mode,force){
      if(!MOBILE||bar||sheet||(!force&&isDismissed())||isStandalone())return;
      if(!document.body){document.addEventListener("DOMContentLoaded",function(){show(mode,force);});return;}
      bar=document.createElement("div");
      bar.id="pwa-bar";bar.setAttribute("role","dialog");bar.setAttribute("aria-label",mode==="ios"?t.tI:t.tA);
      var ic='<img class="pwa-ic" src="/icons/icon-192.png" width="42" height="42" alt="">';
      var tt=mode==="ios"?t.tI:t.tA, sb=mode==="ios"?t.sI:t.sA, go=mode==="ios"?t.how:t.go;
      bar.innerHTML=ic+'<div class="pwa-tx"><div class="pwa-tt">'+tt+'</div><div class="pwa-sb">'+sb+'</div></div>'+
        '<button class="pwa-go" type="button">'+go+'</button><button class="pwa-x" type="button" aria-label="'+t.x+'">&times;</button>';
      document.body.appendChild(bar);
      requestAnimationFrame(function(){requestAnimationFrame(function(){if(bar)bar.classList.add("pwa-show");});});
      track("pwa_prompt_shown");
      bar.querySelector(".pwa-go").addEventListener("click",function(){
        if(mode==="ios"){openSheet();return;}
        if(!dp){remove();return;}
        track("pwa_install_click");
        dp.prompt();
        dp.userChoice.then(function(c){track("pwa_install_choice",{pwa_outcome:(c&&c.outcome)||""});setDismissed();dp=null;hideNav();remove();}).catch(function(){remove();});
      });
      bar.querySelector(".pwa-x").addEventListener("click",function(){track("pwa_dismiss");setDismissed();remove();});
    }
    function navEl(){return document.getElementById("pwa-nav");}
    function revealNav(){var n=navEl();if(n&&MOBILE&&!isStandalone()){var s=n.querySelector("span");if(s)s.textContent=t.go;n.style.display="inline-flex";}}
    function hideNav(){var n=navEl();if(n)n.style.display="none";}
    window.pwaInstall=function(){
      if(dp){track("pwa_install_click",{pwa_from:"menu"});dp.prompt();dp.userChoice.then(function(c){track("pwa_install_choice",{pwa_outcome:(c&&c.outcome)||""});setDismissed();dp=null;hideNav();}).catch(function(){});return;}
      if(IOSK){openSheet();}
    };
    window.addEventListener("beforeinstallprompt",function(e){
      if(!MOBILE)return; /* desktop: leave Chrome/Edge's own address-bar install icon alone */
      e.preventDefault();dp=e;revealNav();show("android");
    });
    window.addEventListener("appinstalled",function(){track("pwa_installed");setDismissed();hideNav();remove();});
    if(isStandalone()){
      try{if(!sessionStorage.getItem("esr_pwa_launch")){sessionStorage.setItem("esr_pwa_launch","1");track("pwa_launch");}}catch(e){}
    }else if(IOSK){
      var iosInit=function(){revealNav();setTimeout(function(){show("ios");},1400);};
      if(document.readyState==="loading"){document.addEventListener("DOMContentLoaded",iosInit);}
      else{iosInit();}
    }
    document.addEventListener("DOMContentLoaded",function(){if(dp)revealNav();});
  })();
  