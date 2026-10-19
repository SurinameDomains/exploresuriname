/* Keeps Explore's copy of the CBvS rates current: cbvs.sr only answers visitors in Suriname, so a browser
     here nudges the esr-cbvs relay at most every 15 minutes. Sends nothing about the visitor; the relay ignores
     other countries (see ExploreSR/cbvs-worker/). */
  (function(){try{var k="esr_cbvs_warm",t=Date.now(),l=+localStorage.getItem(k)||0;if(t-l<9e5)return;localStorage.setItem(k,t)}catch(e){}setTimeout(function(){try{fetch("https://esr-cbvs.surinamedomains.workers.dev/warm",{mode:"no-cors",credentials:"omit",keepalive:true}).catch(function(){})}catch(e){}},3000)})();