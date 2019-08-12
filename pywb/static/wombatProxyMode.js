/*
Copyright(c) 2013-2018 Rhizome and Contributors. Released under the GNU General Public License.

This file is part of pywb, https://github.com/webrecorder/pywb

pywb is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

pywb is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with pywb.  If not, see <http://www.gnu.org/licenses/>.
 */
(function(){function autobind(clazz){for(var prop,propValue,proto=clazz.__proto__||clazz.constructor.prototype||clazz.prototype,clazzProps=Object.getOwnPropertyNames(proto),len=clazzProps.length,i=0;i<len;i++)prop=clazzProps[i],propValue=clazz[prop],prop!=="constructor"&&typeof propValue==="function"&&(clazz[prop]=propValue.bind(clazz))}function AutoFetcherProxyMode(wombat,config){return this instanceof AutoFetcherProxyMode?void(this.wombat=wombat,this.msgQ=[],this.mutationObz=null,this.styleTag=null,this.elemSelector="img[srcset], img[data-srcset], img[data-src], video[srcset], video[data-srcset], video[data-src], audio[srcset], audio[data-srcset], audio[data-src], picture > source[srcset], picture > source[data-srcset], picture > source[data-src], video > source[srcset], video > source[data-srcset], video > source[data-src], audio > source[srcset], audio > source[data-srcset], audio > source[data-src]",autobind(this),this._init(config,true)):new AutoFetcherProxyMode(wombat,config)}function WombatLite($wbwindow,wbinfo){return this instanceof WombatLite?void(this.wb_info=wbinfo,this.$wbwindow=$wbwindow,this.wb_info.top_host=this.wb_info.top_host||"*",this.wb_info.wombat_opts=this.wb_info.wombat_opts||{},this.WBAutoFetchWorker=null,this.historyCB=null):new WombatLite($wbwindow,wbinfo)}AutoFetcherProxyMode.prototype._init=function(config,first){var afwpm=this,wombat=this.wombat;if(document.readyState==="complete")return this.styleTag=document.createElement("style"),this.styleTag.id="$wrStyleParser$",document.head.appendChild(this.styleTag),void(config.isTop?fetch(config.workerURL).then(function(res){res.text().then(function(text){var blob=new Blob([text],{type:"text/javascript"});afwpm.worker=new wombat.$wbwindow.Worker(URL.createObjectURL(blob),{type:"classic",credentials:"include"}),afwpm.startChecking()}).catch(error=>{console.error("Could not create the backing worker for AutoFetchWorkerProxyMode"),console.error(error)})}):(this.worker={postMessage:function(msg){msg.wb_type||(msg={wb_type:"aaworker",msg:msg}),wombat.$wbwindow.top.postMessage(msg,"*")},terminate:function(){}},this.startChecking()));if(first)var i=setInterval(function(){document.readyState==="complete"&&(afwpm._init(config),clearInterval(i))},1e3)},AutoFetcherProxyMode.prototype.startChecking=function(){for(;this.worker&&this.msgQ.length;)this.postMessage(this.msgQ.shift());this.extractFromLocalDoc(),this.mutationObz=new MutationObserver(this.mutationCB),this.mutationObz.observe(document.documentElement,{characterData:false,characterDataOldValue:false,attributes:true,attributeOldValue:true,subtree:true,childList:true,attributeFilter:["src","srcset"]})},AutoFetcherProxyMode.prototype.terminate=function(){this.worker&&this.worker.terminate()},AutoFetcherProxyMode.prototype.justFetch=function(urls){this.postMessage({type:"fetch-all",values:urls})},AutoFetcherProxyMode.prototype.fetchAsPage=function(url,title){if(url){var headers={"X-Wombat-History-Page":url};if(title){var encodedTitle=encodeURIComponent(title.trim());title&&(headers["X-Wombat-History-Title"]=encodedTitle)}var fetchData={url:url,options:{headers:headers}};this.justFetch([fetchData])}},AutoFetcherProxyMode.prototype.postMessage=function(msg){this.worker?this.worker.postMessage(msg):this.msgQ.push(msg)},AutoFetcherProxyMode.prototype.handleMutatedStyleElem=function(elem,accum,text){var checkNode,baseURI=document.baseURI;if(text){if(!elem.parentNode||elem.parentNode.localName!=="style")return;checkNode=elem.parentNode}else checkNode=elem;try{var extractedMedia=this.extractMediaRules(checkNode.sheet,baseURI);if(extractedMedia.length)return void(accum.media=accum.media.concat(extractedMedia))}catch(e){}!text&&checkNode.href&&accum.deferred.push(this.fetchCSSAndExtract(checkNode.href))},AutoFetcherProxyMode.prototype.handleMutatedElem=function(elem,accum){var baseURI=document.baseURI;if(elem.nodeType===Node.TEXT_NODE)return this.handleMutatedStyleElem(elem,accum,true);switch(elem.localName){case"img":case"video":case"audio":case"source":return this.handleDomElement(elem,baseURI,accum);case"style":return this.handleMutatedStyleElem(elem,accum);case"link":if(elem.rel==="stylesheet"||elem.rel==="preload"&&elem.as==="style")return this.handleMutatedStyleElem(elem,accum);}return this.extractSrcSrcsetFrom(elem,baseURI,accum)},AutoFetcherProxyMode.prototype.mutationCB=function(mutationList,observer){for(var accum={type:"values",srcset:[],src:[],media:[],deferred:[]},i=0;i<mutationList.length;i++){var mutation=mutationList[i],mutationTarget=mutation.target;if(this.handleMutatedElem(mutationTarget,accum),mutation.type==="childList"&&mutation.addedNodes.length)for(var addedLen=mutation.addedNodes.length,j=0;j<addedLen;j++)this.handleMutatedElem(mutation.addedNodes[j],accum)}if(accum.deferred.length){var deferred=accum.deferred;accum.deferred=null,Promise.all(deferred).then(this.handleDeferredSheetResults)}(accum.srcset.length||accum.src.length||accum.media.length)&&this.postMessage(accum)},AutoFetcherProxyMode.prototype.shouldSkipSheet=function(sheet){return!(sheet.id!=="$wrStyleParser$")||!!(sheet.href&&sheet.href.indexOf(this.wombat.wb_info.proxy_magic)!==-1)},AutoFetcherProxyMode.prototype.validateSrcV=function(srcV){return srcV&&srcV.indexOf("data:")!==0&&srcV.indexOf("blob:")!==0?srcV:null},AutoFetcherProxyMode.prototype.fetchCSSAndExtract=function(cssURL){var url=location.protocol+"//"+this.wombat.wb_info.proxy_magic+"/proxy-fetch/"+cssURL,afwpm=this;return fetch(url).then(function(res){return res.text().then(function(text){return afwpm.styleTag.textContent=text,afwpm.extractMediaRules(afwpm.styleTag.sheet,cssURL)})}).catch(function(error){return[]})},AutoFetcherProxyMode.prototype.extractMediaRules=function(sheet,baseURI){var results=[];if(!sheet)return results;var rules;try{rules=sheet.cssRules||sheet.rules}catch(e){return results}if(!rules||rules.length===0)return results;for(var rule,len=rules.length,resolve=sheet.href||baseURI,i=0;i<len;++i)rule=rules[i],rule.type===CSSRule.MEDIA_RULE&&results.push({cssText:rule.cssText,resolve:resolve});return results},AutoFetcherProxyMode.prototype.rwMod=function(elem){switch(elem.tagName){case"SOURCE":return elem.parentElement&&elem.parentElement.tagName==="PICTURE"?"im_":"oe_";case"IMG":return"im_";}return"oe_"},AutoFetcherProxyMode.prototype.handleDomElement=function(elem,baseURI,acum){var srcv=this.validateSrcV(elem.src),resolve=srcv||baseURI,mod=this.rwMod(elem);elem.srcset&&(acum.srcset==null&&(acum={srcset:[]}),acum.srcset.push({srcset:elem.srcset,resolve:resolve,mod:mod})),elem.dataset&&elem.dataset.srcset&&(acum.srcset==null&&(acum={srcset:[]}),acum.srcset.push({srcset:elem.dataset.srcset,resolve:resolve,mod:mod})),elem.dataset&&elem.dataset.src&&(acum.src==null&&(acum.src=[]),acum.src.push({src:elem.dataset.src,resolve:resolve,mod:mod})),elem.tagName==="SOURCE"&&srcv&&(acum.src==null&&(acum.src=[]),acum.src.push({src:srcv,resolve:baseURI,mod:mod}))},AutoFetcherProxyMode.prototype.extractSrcSrcsetFrom=function(fromElem,baseURI,acum){if(fromElem.querySelectorAll){for(var elems=fromElem.querySelectorAll(this.elemSelector),len=elems.length,msg=acum==null?{type:"values",srcset:[],src:[]}:acum,i=0;i<len;i++)this.handleDomElement(elems[i],baseURI,msg);acum==null&&(msg.srcset.length||msg.src.length)&&this.postMessage(msg)}},AutoFetcherProxyMode.prototype.handleDeferredSheetResults=function(results){if(results.length!==0){for(var len=results.length,media=[],i=0;i<len;++i)media=media.concat(results[i]);media.length&&this.postMessage({type:"values",media:media})}},AutoFetcherProxyMode.prototype.checkStyleSheets=function(doc){for(var sheet,media=[],deferredMediaExtraction=[],styleSheets=(doc||document).styleSheets,sheetLen=styleSheets.length,i=0;i<sheetLen;i++)if(sheet=styleSheets[i],!this.shouldSkipSheet(sheet))try{if(sheet.cssRules||sheet.rules){var extracted=this.extractMediaRules(sheet,doc.baseURI);extracted.length&&(media=media.concat(extracted))}else sheet.href!=null&&deferredMediaExtraction.push(this.fetchCSSAndExtract(sheet.href))}catch(error){sheet.href!=null&&deferredMediaExtraction.push(this.fetchCSSAndExtract(sheet.href))}media.length&&this.postMessage({type:"values",media:media}),deferredMediaExtraction.length&&Promise.all(deferredMediaExtraction).then(this.handleDeferredSheetResults)},AutoFetcherProxyMode.prototype.extractFromLocalDoc=function(){this.extractSrcSrcsetFrom(this.wombat.$wbwindow.document,this.wombat.$wbwindow.document.baseURI),this.checkStyleSheets(this.wombat.$wbwindow.document)},WombatLite.prototype.initSeededRandom=function(seed){this.$wbwindow.Math.seed=parseInt(seed);var wombat=this;this.$wbwindow.Math.random=function random(){return wombat.$wbwindow.Math.seed=(wombat.$wbwindow.Math.seed*9301+49297)%233280,wombat.$wbwindow.Math.seed/233280}},WombatLite.prototype.initCryptoRandom=function(){if(this.$wbwindow.crypto&&this.$wbwindow.Crypto){var wombat=this,new_getrandom=function getRandomValues(array){for(var i=0;i<array.length;i++)array[i]=parseInt(wombat.$wbwindow.Math.random()*4294967296);return array};this.$wbwindow.Crypto.prototype.getRandomValues=new_getrandom,this.$wbwindow.crypto.getRandomValues=new_getrandom}},WombatLite.prototype.initFixedRatio=function(){try{this.$wbwindow.devicePixelRatio=1}catch(e){}if(Object.defineProperty)try{Object.defineProperty(this.$wbwindow,"devicePixelRatio",{value:1,writable:false})}catch(e){}},WombatLite.prototype.initDateOverride=function(timestamp){if(!this.$wbwindow.__wb_Date_now){var newTimestamp=parseInt(timestamp)*1e3,timezone=0,start_now=this.$wbwindow.Date.now(),timediff=start_now-(newTimestamp-timezone),orig_date=this.$wbwindow.Date,orig_utc=this.$wbwindow.Date.UTC,orig_parse=this.$wbwindow.Date.parse,orig_now=this.$wbwindow.Date.now;this.$wbwindow.__wb_Date_now=orig_now,this.$wbwindow.Date=function(Date_){return function Date(A,B,C,D,E,F,G){return A===undefined?new Date_(orig_now()-timediff):B===undefined?new Date_(A):C===undefined?new Date_(A,B):D===undefined?new Date_(A,B,C):E===undefined?new Date_(A,B,C,D):F===undefined?new Date_(A,B,C,D,E):G===undefined?new Date_(A,B,C,D,E,F):new Date_(A,B,C,D,E,F,G)}}(this.$wbwindow.Date),this.$wbwindow.Date.prototype=orig_date.prototype,this.$wbwindow.Date.now=function now(){return orig_now()-timediff},this.$wbwindow.Date.UTC=orig_utc,this.$wbwindow.Date.parse=orig_parse,this.$wbwindow.Date.__WB_timediff=timediff,Object.defineProperty(this.$wbwindow.Date.prototype,"constructor",{value:this.$wbwindow.Date})}},WombatLite.prototype.initDisableNotifications=function(){window.Notification&&(window.Notification.requestPermission=function requestPermission(callback){return callback&&callback("denied"),Promise.resolve("denied")});var applyOverride=function(on){on&&(on.getCurrentPosition&&(on.getCurrentPosition=function getCurrentPosition(success,error,options){error&&error({code:2,message:"not available"})}),on.watchPosition&&(on.watchPosition=function watchPosition(success,error,options){error&&error({code:2,message:"not available"})}))};window.geolocation&&applyOverride(window.geolocation),window.navigator.geolocation&&applyOverride(window.navigator.geolocation)},WombatLite.prototype.initAutoFetchWorker=function(){if(this.$wbwindow.Worker){var config={isTop:this.$wbwindow.self===this.$wbwindow.top,workerURL:(this.wb_info.auto_fetch_worker_prefix||this.wb_info.static_prefix)+"autoFetchWorker.js"};if(this.$wbwindow.$WBAutoFetchWorker$==null?(this.WBAutoFetchWorker=new AutoFetcherProxyMode(this,config),Object.defineProperty(this.$wbwindow,"$WBAutoFetchWorker$",{enumerable:false,value:this.WBAutoFetchWorker})):this.WBAutoFetchWorker=this.$wbwindow.$WBAutoFetchWorker$,config.isTop){var wombatLite=this;this.$wbwindow.addEventListener("message",function(event){event.data&&event.data.wb_type==="aaworker"&&wombatLite.WBAutoFetchWorker.postMessage(event.data.msg)},false)}}},WombatLite.prototype.initHistoryOverrides=function(){if(this.$wbwindow.self===this.$wbwindow.top){this.overrideHistoryFunc("pushState"),this.overrideHistoryFunc("replaceState");var wombatLite=this;this.$wbwindow.addEventListener("popstate",function(event){wombatLite.historyCB&&wombatLite.historyCB(wombatLite.$wbwindow.location.href,wombatLite.$wbwindow.document.title,"popstate",event.state)})}},WombatLite.prototype.overrideHistoryFunc=function(funcName){if(!this.$wbwindow.history)return undefined;var orig_func=this.$wbwindow.history[funcName];if(!orig_func)return undefined;this.$wbwindow.history["_orig_"+funcName]=orig_func;var wombat=this,rewrittenFunc=function histNewFunc(stateObj,title,url){if(orig_func.call(this,stateObj,title,url),!!url){var origTitle=wombat.$wbwindow.document.title;wombat.WBAutoFetchWorker&&wombat.$wbwindow.setTimeout(function(){title||wombat.$wbwindow.document.title===origTitle||(title=wombat.$wbwindow.document.title),wombat.WBAutoFetchWorker.fetchAsPage(wombat.$wbwindow.location.href,title),wombat.historyCB&&wombat.historyCB(wombat.$wbwindow.location.href,title,funcName,stateObj)},100)}};return this.$wbwindow.history[funcName]=rewrittenFunc,this.$wbwindow.History&&this.$wbwindow.History.prototype&&(this.$wbwindow.History.prototype[funcName]=rewrittenFunc),rewrittenFunc},WombatLite.prototype.wombatInit=function(){this.wb_info.enable_auto_fetch&&this.wb_info.is_live&&this.initAutoFetchWorker(),this.initHistoryOverrides(),this.initSeededRandom(this.wb_info.wombat_sec),this.initCryptoRandom(),this.initFixedRatio(),this.initDateOverride(this.wb_info.wombat_sec),this.initDisableNotifications();var wombatLite=this;return{actual:false,setHistoryCB:function(cb){wombatLite.historyCB=cb}}},window._WBWombat=WombatLite,window._WBWombatInit=function(wbinfo){if(!this._wb_wombat||!this._wb_wombat.actual){var wombat=new WombatLite(this,wbinfo);wombat.actual=true,this._wb_wombat=wombat.wombatInit(),this._wb_wombat.actual=true}else this._wb_wombat||console.warn("_wb_wombat missing!")}})();
