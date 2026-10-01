
  /* Horizontal chip strips and scroll rows, sitewide: make them usable with a
     mouse. Every .overflow-x-auto element that is not a table wrapper gets
     overlay arrow buttons at either edge while it overflows (hover-capable
     devices only), vertical-wheel sideways panning (page scroll resumes at
     the ends) and click-drag panning. Strips share one mechanism sitewide and
     drag (all strips share one mechanism; arrows hide whenever the strip has
     nothing to scroll). Content changes are observed so arrows appear when
     chips render or filter late. Touch and keyboard behaviour unchanged. */
  (function(){
    var FINE=window.matchMedia?matchMedia("(hover:hover) and (pointer:fine)"):{matches:false};
    function skip(el){return !!el.querySelector("table");}
    function mkArrow(dir){
      var b=document.createElement("button");
      b.type="button";b.className="esr-arrow esr-arrow-"+dir;
      b.setAttribute("aria-label",dir==="l"?"Scroll left":"Scroll right");
      b.innerHTML='<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="'+(dir==="l"?"M15 18l-6-6 6-6":"M9 18l6-6-6-6")+'"/></svg>';
      return b;
    }
    function arm(el){
      if(el.dataset.esrStrip||skip(el))return;
      el.dataset.esrStrip="1";
      el.classList.add("esr-grab");
      el.addEventListener("wheel",function(ev){
        if(ev.deltaX!==0||ev.shiftKey||ev.ctrlKey)return;
        if(el.scrollWidth<=el.clientWidth+2)return;
        var max=el.scrollWidth-el.clientWidth;
        if((ev.deltaY>0&&el.scrollLeft>=max-1)||(ev.deltaY<0&&el.scrollLeft<=0))return;
        el.scrollLeft+=ev.deltaY;ev.preventDefault();
      },{passive:false});
      var wrap=document.createElement("div");
      var cs=getComputedStyle(el);
      if(cs.position==="sticky"){
        wrap.style.position="sticky";wrap.style.top=cs.top;wrap.style.zIndex=cs.zIndex;
        el.style.position="static";
      }else{wrap.style.position="relative";}
      /* The wrapper must be allowed to shrink: as a flex item its default
         min-width:auto is the content width, which pushed the whole page
         sideways on mobile (category pages scrolled ~1300px wide). */
      wrap.style.minWidth="0";wrap.style.maxWidth="100%";
      var _pcs=el.parentNode?getComputedStyle(el.parentNode):null;
      if(_pcs&&(_pcs.display==="flex"||_pcs.display==="inline-flex")){wrap.style.flex="1 1 0%";}
      el.parentNode.insertBefore(wrap,el);
      wrap.appendChild(el);
      var L=mkArrow("l"),R=mkArrow("r");
      wrap.appendChild(L);wrap.appendChild(R);
      function upd(){
        var max=el.scrollWidth-el.clientWidth;
        var ok=FINE.matches&&max>4;
        L.style.display=(ok&&el.scrollLeft>4)?"":"none";
        R.style.display=(ok&&el.scrollLeft<max-4)?"":"none";
      }
      function go(s){el.scrollBy({left:s*Math.max(120,Math.round(el.clientWidth*0.7)),behavior:"smooth"});}
      L.addEventListener("click",function(){go(-1);});
      R.addEventListener("click",function(){go(1);});
      el.addEventListener("scroll",upd,{passive:true});
      window.addEventListener("resize",upd);
      if(window.MutationObserver){
        new MutationObserver(function(){upd();}).observe(el,
          {childList:true,subtree:true,attributes:true,attributeFilter:["style","class"]});
      }else{
        el.addEventListener("click",function(){setTimeout(upd,60);});
      }
      upd();
    }
    function init(){
      document.querySelectorAll(".overflow-x-auto").forEach(arm);
      var el=null,sx=0,sl=0,moved=false;
      document.addEventListener("pointerdown",function(ev){
        if(ev.pointerType!=="mouse"||ev.button!==0)return;
        if(ev.target.closest&&ev.target.closest(".esr-arrow"))return;
        var t=ev.target.closest&&ev.target.closest(".overflow-x-auto");
        if(!t||skip(t)||t.scrollWidth<=t.clientWidth+2)return;
        el=t;sx=ev.clientX;sl=t.scrollLeft;moved=false;
      });
      document.addEventListener("pointermove",function(ev){
        if(!el)return;
        var dx=ev.clientX-sx;
        if(!moved){if(Math.abs(dx)<5)return;moved=true;el.style.userSelect="none";}
        el.scrollLeft=sl-dx;ev.preventDefault();
      });
      function end(){
        if(!el)return;
        var was=el,m=moved;el=null;moved=false;was.style.userSelect="";
        if(m){var kill=function(e){e.stopPropagation();e.preventDefault();};
          was.addEventListener("click",kill,true);
          setTimeout(function(){was.removeEventListener("click",kill,true);},0);}
      }
      document.addEventListener("pointerup",end);
      document.addEventListener("pointercancel",end);
    }
    if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",init);else init();
  })();
  