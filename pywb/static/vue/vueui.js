(function () { /* SSR Support: Store raw CSS globally */ if (typeof globalThis !== 'undefined') { globalThis.__VITE_CSS_RAW__ = (globalThis.__VITE_CSS_RAW__ || '') + "\n.timeline {\n position: relative;\n display: flex;\n width: auto;\n height: 60px;\n margin: 5px;\n justify-content: left;\n}\n.timeline .id {\n display: inline-block;\n font-size: 30px;\n}\n.timeline .arrow {\n display: inline-block;\n width: 20px;\n font-size: 20px; /* font-size = width of arrow, as it UTF char */\n line-height: 60px;\n vertical-align: top;\n cursor: pointer;\n}\n.timeline .arrow.previous {\n}\n.timeline .arrow.next {\n}\n.timeline .arrow.disabled, .timeline .arrow.disabled:hover {\n /*color: lightgray;*/\n background-color: transparent;\n /*cursor: not-allowed;*/\n visibility: hidden;\n}\n.timeline .arrow:hover {\n background-color: antiquewhite;\n color: firebrick;\n}\n.timeline .scroll {\n position: relative;\n display: inline-block;\n width: 100%; /* */\n height: 100%;\n\n /* maker scrollable horizontally */\n overflow-x: scroll;\n overflow-y: hidden;\n white-space: nowrap;\n scroll-behavior: smooth;\n\n text-align: center;\n\n transition: background-color 500ms ease-in;\n}\n /* hide scroll bar */\n.timeline .scroll::-webkit-scrollbar {\n display: none;\n}\n /* highlight the scroll period: usually triggered from root app */\n.timeline .scroll.highlight {\n background-color: #fff7ce;\n}\n.timeline .scroll .periods {\n display: flex;\n justify-content: space-between;\n height: 100%;\n width: 100%;\n min-width: 600px;\n}\n.timeline .period {\n flex-grow: 1;\n position: relative;\n display: inline-block;\n height: 100%;\n /* line-height: 80px; /* use to center middle vertically */\n white-space: normal;\n vertical-align: top;\n text-align: center;\n background-color: transparent;\n\n transition: background-color 500ms ease-in-out;\n}\n /* 1st period period child el */\n.timeline .period:nth-child(1) {\n /*border-left: 1px solid white; !* has left border; all other periods have right border *!*/\n}\n.timeline .period:hover {\n background-color: #eeeeee;\n}\n.timeline .period.contains-current-snapshot, .timeline .period.contains-current-snapshot:hover {\n background-color: #f7def4;\n}\n\n /* empty period */\n.timeline .period.empty {\n color: #aaa;\n /*background-color: transparent;*/\n}\n /* highlighted period */\n.timeline .period.highlight {\n background-color: cyan;\n}\n.timeline .period .inner {\n display: block;\n position: absolute;\n bottom: 0;\n left: 0;\n width: 100%;\n height: 20px;\n background-color: white;\n border-top: 1px solid gray;\n white-space: nowrap;\n cursor: zoom-in;\n}\n.timeline .period .inner.has-single-snapshot {\n cursor: pointer;\n}\n.timeline .period.last-level .inner, .timeline .period.empty .inner {\n cursor: default;\n}\n.timeline .period .label {\n width: 100%;\n font-weight: bold;\n font-size: 14px;\n transition: background-color 500ms ease-in;\n}\n.timeline .period:hover .label {\n position: absolute;\n z-index: 20;\n background-color: lightgrey;\n}\n.timeline .period .histo {\n display: flex;\n position: absolute;\n top: 1px;\n left: 0;\n width: 100%;\n height: 39px;\n align-items: flex-end;\n justify-content: space-between;\n text-align: left;\n}\n.timeline .period .histo .line {\n position: relative;\n flex-grow: 1;\n display: inline-block;\n background-color: #a6cdf5;\n margin: 0;\n padding: 0;\n cursor: zoom-in;\n}\n.timeline .period .histo .line.has-single-snapshot {\n cursor: pointer;\n}\n\n /* Last level period histogram spaces things evenly */\n.timeline .period.last-level .histo {\n justify-content: space-around;\n}\n\n /* Last level period histogram lines do not grow, but are fixed width/margin */\n.timeline .period.last-level .histo .line {\n flex-grow: unset;\n width: 5px;\n margin-left: 2px;\n}\n\n /* update line color on hover*/\n.timeline .period .histo .line:hover {\n background-color: #f5a6eb;\n}\n.timeline .period .histo .line.contains-current-snapshot {\n background-color: red;\n}\n\n /* Period that contains ONE snapshot only will show snapshot info*/\n.timeline .period-tooltip {\n position: fixed;\n z-index: 100;\n /*left or right set programmatically*/\n display: block;\n background-color: white;\n border: 1px solid gray;\n padding: 2px;\n white-space: nowrap; /*no wrapping allowed*/\n}\n /*show on hover*/\n.timeline .period-tooltip.show {\n display: block;\n}\n\n\n.breadcrumbs {\n text-align: center;\n}\n.breadcrumbs .item {\n position: relative;\n display: inline;\n margin: 0 2px 0 0;\n font-size: inherit;\n}\n.breadcrumbs .count {\n /*vertical-align: middle;*/\n font-size: inherit;\n}\n.breadcrumbs .item .goto {\n display: inline-block;\n margin: 1px;\n padding: 1px;\n cursor: zoom-out;\n border-radius: 5px;\n background-color: #eeeeee;\n}\n.breadcrumbs .item .goto:hover {\n background-color: #a6cdf5;\n}\n.breadcrumbs .item .goto img {\n height: 15px;\n}\n.breadcrumbs .item.snapshot {\n display: block;\n}\n\n\n.calendar-month {\n position: relative;\n display: inline-block;\n padding: 5px;\n margin: 0;\n height: 260px;\n width: 220px;\n text-align: center;\n vertical-align: top;\n box-sizing: content-box;\n border-radius: 10px;\n}\n.calendar-month:hover {\n background-color: #F5F5F5;\n}\n.calendar-month.current {\n background-color: #fff7ce;\n}\n.calendar-month.contains-current-snapshot {\n border: solid 1px red;\n}\n.calendar-month > h3 {\n margin: 0;\n font-size: 16px;\n}\n.calendar-month > .empty {\n position: absolute;\n top: 45%;\n width: 100%;\n color: #454545;\n}\n.calendar-month .day {\n position: relative;\n display: inline-block;\n margin: 0;\n text-align: center;\n}\n.calendar-month .day.empty {\n color: #454545;\n}\n.calendar-month .day .count {\n display: none;\n position: absolute;\n bottom: 80%;\n left: 80%;\n line-height: 1; /* reset to normal */\n padding: 3px;\n border-radius: 10px;\n border-bottom-left-radius: 0;\n border: 1px solid gray;\n background-color: white;\n z-index: 30;\n white-space: nowrap;\n}\n.calendar-month .day:hover .count {\n display: block;\n}\n.calendar-month .day .size {\n position: absolute;\n box-sizing: border-box;\n background-color: rgba(166, 205, 245, .85);\n z-index: 10;\n}\n.calendar-month .day.contains-current-snapshot .size {\n background-color: rgba(255, 100, 100, .85);\n}\n.calendar-month .day .day-id {\n position: absolute;\n top: 0;\n left: 0;\n z-index: 11;\n\n display: inline-block;\n width: 100%;\n text-align: center;\n\n color: black;\n}\n.calendar-month .day .day-id.empty {\n color: #454545 !important;\n}\n.calendar-month .day:hover .size {\n border: 1px solid black;\n}\n.calendar-month .day:hover {\n cursor: zoom-in;\n}\n.calendar-month .day.empty:hover {\n cursor: not-allowed;\n}\n\n.timeline-linear[data-v-cd9252e7] {\n width: auto;\n padding: 5px;\n background-color: white;\n border: 1px solid gray;\n border-radius: 5px;\n z-index: 1100;\n}\n.timeline-linear .list[data-v-cd9252e7] {\n max-height: 80vh;\n min-height: 50px;\n overflow-x: hidden;\n overflow-y: auto;\n}\n.timeline-linear .title[data-v-cd9252e7] {\n border-bottom: 1px solid black;\n font-weight: bold;\n font-family: Arial, sans-serif;\n}\n.timeline-linear .link[data-v-cd9252e7] {\n text-decoration: underline;\n color: darkblue;\n}\n.timeline-linear .link[data-v-cd9252e7]:hover {\n color: lightseagreen;\n cursor: pointer;\n}\n.timeline-linear .current[data-v-cd9252e7] {\n background-color: deeppink;\n color: white;\n border-radius: 5px;\n}\n\n.pywb-tooltip[data-v-f5173de9] {\n position: fixed;\n top: 0;\n left: 0;\n z-index: 100;\n background-color: white;\n border: 1px solid grey;\n border-radius: 5px;\n}\n\n.full-view[data-v-f7e8c6b3] {\n display: flex;\n flex: 1;\n flex-wrap: wrap;\n z-index: 10;\n overflow-y: auto;\n width: 100%;\n background-color: white;\n padding-bottom: 1em;\n justify-content: center;\n}\n.full-view .months[data-v-f7e8c6b3] {\n display: flex;\n justify-content: center;\n flex-wrap: wrap;\n align-items: flex-start;\n}\n.full-view h2[data-v-f7e8c6b3] {\n margin: 10px 0;\n font-size: 20px;\n text-align: center;\n}\n.year-arrow[data-v-f7e8c6b3]:hover {\n cursor: pointer;\n}\n\nbody {\n padding-top: 89px !important;\n}\n.app {\n font-family: Calibri, Arial, sans-serif;\n /*border-bottom: 1px solid lightcoral;*/\n width: 100%;\n}\n.app.expanded {\n /*height: 130px;*/\n max-height: calc(100vh - 90px);\n display: flex;\n flex-direction: column;\n}\n.full-view {\n /*position: fixed;*/\n /*top: 150px;*/\n left: 0;\n}\n.navbar {\n background-color: var(--navbar-background);\n color: var(--navbar-color);\n}\n.top-navbar {\n z-index: 90;\n padding: 2px 16px 0 16px;\n}\n.top-navbar span.navbar-toggler-icon {\n margin: .25rem !important;\n}\n#logo-img {\n max-height: 40px;\n}\n.title-nav {\n margin-top: 50px;\n z-index: 80;\n}\n#secondNavbar {\n height: 24px !important;\n}\n#navbarCollapse {\n justify-content: right;\n}\n#navbarCollapse ul#toggles {\n display: flex;\n align-content: center;\n}\n#navbarCollapse:not(.show) ul#toggles li:not(:first-child) {\n margin-left: .25rem;\n}\n#navbarCollapse.show {\n padding-bottom: 1em;\n}\n#navbarCollapse.show ul#toggles li {\n margin-top: 5px;\n}\n#navbarCollapse.show ul#toggles li {\n margin-left: 0px;\n}\n.iframe iframe {\n width: 100%;\n height: 80vh;\n}\n#searchdiv {\n height: 31px;\n}\n#theurl {\n width: 250px;\n}\n@media (min-width: 576px) {\n#theurl {\n width: 350px;\n}\n}\n@media (min-width: 768px) {\n#theurl {\n width: 500px;\n}\n}\n@media (min-width: 992px) {\n#theurl {\n width: 600px;\n}\n}\n@media (min-width: 1200px) {\n#theurl {\n width: 900px;\n}\n}\n#toggles {\n align-items: center;\n}\n.breadcrumb-row {\n display: flex;\n align-items: center;\n justify-content: center;\n}\ndiv.timeline-wrap div.card {\n margin-top: 55px;\n}\n#calendar-card {\n overflow-y: auto;\n max-height: 100%;\n}\ndiv.timeline-wrap div.card-body {\n display: flex;\n align-items: center;\n justify-content: center;\n}\ndiv.timeline-wrap div.card-body div.row {\n width: 100%;\n align-items: center;\n justify-content: center;\n}\n#calendar-card-body {\n padding: 0;\n}\n.strong {\n font-weight: bold;\n}\n.hidden {\n color: var(--navbar-background);\n}\n/*$vite$:1*/"; } /* DOM Injection Support */ if (typeof document !== 'undefined' && typeof globalThis !== 'undefined') { var executeInject = function (options) { var target = (options && options.target) || document.head; if (!target) return; executeInject.cache = executeInject.cache || []; for (var i = 0; i < executeInject.cache.length; i++) { if (executeInject.cache[i].target === target) { var els = executeInject.cache[i].elements; for (var j = 0; j < els.length; j++) target.appendChild(els[j]); return; } } var newElements = []; var observer = new MutationObserver(function () { }); var obsTarget = target.nodeType === 11 ? target : (document.documentElement || document); observer.observe(obsTarget, { childList: true, subtree: true }); try { (function (document_head) { (function(){try{if(typeof document<`u`){var e=document.createElement(`style`);e.appendChild(document.createTextNode(`.timeline { position: relative; display: flex; width: auto; height: 60px; margin: 5px; justify-content: left;}.timeline .id { display: inline-block; font-size: 30px;}.timeline .arrow { display: inline-block; width: 20px; font-size: 20px; /* font-size = width of arrow, as it UTF char */ line-height: 60px; vertical-align: top; cursor: pointer;}.timeline .arrow.previous {}.timeline .arrow.next {}.timeline .arrow.disabled, .timeline .arrow.disabled:hover { /*color: lightgray;*/ background-color: transparent; /*cursor: not-allowed;*/ visibility: hidden;}.timeline .arrow:hover { background-color: antiquewhite; color: firebrick;}.timeline .scroll { position: relative; display: inline-block; width: 100%; /* */ height: 100%; /* maker scrollable horizontally */ overflow-x: scroll; overflow-y: hidden; white-space: nowrap; scroll-behavior: smooth; text-align: center; transition: background-color 500ms ease-in;} /* hide scroll bar */.timeline .scroll::-webkit-scrollbar { display: none;} /* highlight the scroll period: usually triggered from root app */.timeline .scroll.highlight { background-color: #fff7ce;}.timeline .scroll .periods { display: flex; justify-content: space-between; height: 100%; width: 100%; min-width: 600px;}.timeline .period { flex-grow: 1; position: relative; display: inline-block; height: 100%; /* line-height: 80px; /* use to center middle vertically */ white-space: normal; vertical-align: top; text-align: center; background-color: transparent; transition: background-color 500ms ease-in-out;} /* 1st period period child el */.timeline .period:nth-child(1) { /*border-left: 1px solid white; !* has left border; all other periods have right border *!*/}.timeline .period:hover { background-color: #eeeeee;}.timeline .period.contains-current-snapshot, .timeline .period.contains-current-snapshot:hover { background-color: #f7def4;} /* empty period */.timeline .period.empty { color: #aaa; /*background-color: transparent;*/} /* highlighted period */.timeline .period.highlight { background-color: cyan;}.timeline .period .inner { display: block; position: absolute; bottom: 0; left: 0; width: 100%; height: 20px; background-color: white; border-top: 1px solid gray; white-space: nowrap; cursor: zoom-in;}.timeline .period .inner.has-single-snapshot { cursor: pointer;}.timeline .period.last-level .inner, .timeline .period.empty .inner { cursor: default;}.timeline .period .label { width: 100%; font-weight: bold; font-size: 14px; transition: background-color 500ms ease-in;}.timeline .period:hover .label { position: absolute; z-index: 20; background-color: lightgrey;}.timeline .period .histo { display: flex; position: absolute; top: 1px; left: 0; width: 100%; height: 39px; align-items: flex-end; justify-content: space-between; text-align: left;}.timeline .period .histo .line { position: relative; flex-grow: 1; display: inline-block; background-color: #a6cdf5; margin: 0; padding: 0; cursor: zoom-in;}.timeline .period .histo .line.has-single-snapshot { cursor: pointer;} /* Last level period histogram spaces things evenly */.timeline .period.last-level .histo { justify-content: space-around;} /* Last level period histogram lines do not grow, but are fixed width/margin */.timeline .period.last-level .histo .line { flex-grow: unset; width: 5px; margin-left: 2px;} /* update line color on hover*/.timeline .period .histo .line:hover { background-color: #f5a6eb;}.timeline .period .histo .line.contains-current-snapshot { background-color: red;} /* Period that contains ONE snapshot only will show snapshot info*/.timeline .period-tooltip { position: fixed; z-index: 100; /*left or right set programmatically*/ display: block; background-color: white; border: 1px solid gray; padding: 2px; white-space: nowrap; /*no wrapping allowed*/} /*show on hover*/.timeline .period-tooltip.show { display: block;}.breadcrumbs { text-align: center;}.breadcrumbs .item { position: relative; display: inline; margin: 0 2px 0 0; font-size: inherit;}.breadcrumbs .count { /*vertical-align: middle;*/ font-size: inherit;}.breadcrumbs .item .goto { display: inline-block; margin: 1px; padding: 1px; cursor: zoom-out; border-radius: 5px; background-color: #eeeeee;}.breadcrumbs .item .goto:hover { background-color: #a6cdf5;}.breadcrumbs .item .goto img { height: 15px;}.breadcrumbs .item.snapshot { display: block;}.calendar-month { position: relative; display: inline-block; padding: 5px; margin: 0; height: 260px; width: 220px; text-align: center; vertical-align: top; box-sizing: content-box; border-radius: 10px;}.calendar-month:hover { background-color: #F5F5F5;}.calendar-month.current { background-color: #fff7ce;}.calendar-month.contains-current-snapshot { border: solid 1px red;}.calendar-month > h3 { margin: 0; font-size: 16px;}.calendar-month > .empty { position: absolute; top: 45%; width: 100%; color: #454545;}.calendar-month .day { position: relative; display: inline-block; margin: 0; text-align: center;}.calendar-month .day.empty { color: #454545;}.calendar-month .day .count { display: none; position: absolute; bottom: 80%; left: 80%; line-height: 1; /* reset to normal */ padding: 3px; border-radius: 10px; border-bottom-left-radius: 0; border: 1px solid gray; background-color: white; z-index: 30; white-space: nowrap;}.calendar-month .day:hover .count { display: block;}.calendar-month .day .size { position: absolute; box-sizing: border-box; background-color: rgba(166, 205, 245, .85); z-index: 10;}.calendar-month .day.contains-current-snapshot .size { background-color: rgba(255, 100, 100, .85);}.calendar-month .day .day-id { position: absolute; top: 0; left: 0; z-index: 11; display: inline-block; width: 100%; text-align: center; color: black;}.calendar-month .day .day-id.empty { color: #454545 !important;}.calendar-month .day:hover .size { border: 1px solid black;}.calendar-month .day:hover { cursor: zoom-in;}.calendar-month .day.empty:hover { cursor: not-allowed;}.timeline-linear[data-v-cd9252e7] { width: auto; padding: 5px; background-color: white; border: 1px solid gray; border-radius: 5px; z-index: 1100;}.timeline-linear .list[data-v-cd9252e7] { max-height: 80vh; min-height: 50px; overflow-x: hidden; overflow-y: auto;}.timeline-linear .title[data-v-cd9252e7] { border-bottom: 1px solid black; font-weight: bold; font-family: Arial, sans-serif;}.timeline-linear .link[data-v-cd9252e7] { text-decoration: underline; color: darkblue;}.timeline-linear .link[data-v-cd9252e7]:hover { color: lightseagreen; cursor: pointer;}.timeline-linear .current[data-v-cd9252e7] { background-color: deeppink; color: white; border-radius: 5px;}.pywb-tooltip[data-v-f5173de9] { position: fixed; top: 0; left: 0; z-index: 100; background-color: white; border: 1px solid grey; border-radius: 5px;}.full-view[data-v-f7e8c6b3] { display: flex; flex: 1; flex-wrap: wrap; z-index: 10; overflow-y: auto; width: 100%; background-color: white; padding-bottom: 1em; justify-content: center;}.full-view .months[data-v-f7e8c6b3] { display: flex; justify-content: center; flex-wrap: wrap; align-items: flex-start;}.full-view h2[data-v-f7e8c6b3] { margin: 10px 0; font-size: 20px; text-align: center;}.year-arrow[data-v-f7e8c6b3]:hover { cursor: pointer;}body { padding-top: 89px !important;}.app { font-family: Calibri, Arial, sans-serif; /*border-bottom: 1px solid lightcoral;*/ width: 100%;}.app.expanded { /*height: 130px;*/ max-height: calc(100vh - 90px); display: flex; flex-direction: column;}.full-view { /*position: fixed;*/ /*top: 150px;*/ left: 0;}.navbar { background-color: var(--navbar-background); color: var(--navbar-color);}.top-navbar { z-index: 90; padding: 2px 16px 0 16px;}.top-navbar span.navbar-toggler-icon { margin: .25rem !important;}#logo-img { max-height: 40px;}.title-nav { margin-top: 50px; z-index: 80;}#secondNavbar { height: 24px !important;}#navbarCollapse { justify-content: right;}#navbarCollapse ul#toggles { display: flex; align-content: center;}#navbarCollapse:not(.show) ul#toggles li:not(:first-child) { margin-left: .25rem;}#navbarCollapse.show { padding-bottom: 1em;}#navbarCollapse.show ul#toggles li { margin-top: 5px;}#navbarCollapse.show ul#toggles li { margin-left: 0px;}.iframe iframe { width: 100%; height: 80vh;}#searchdiv { height: 31px;}#theurl { width: 250px;}@media (min-width: 576px) {#theurl { width: 350px;}}@media (min-width: 768px) {#theurl { width: 500px;}}@media (min-width: 992px) {#theurl { width: 600px;}}@media (min-width: 1200px) {#theurl { width: 900px;}}#toggles { align-items: center;}.breadcrumb-row { display: flex; align-items: center; justify-content: center;}div.timeline-wrap div.card { margin-top: 55px;}#calendar-card { overflow-y: auto; max-height: 100%;}div.timeline-wrap div.card-body { display: flex; align-items: center; justify-content: center;}div.timeline-wrap div.card-body div.row { width: 100%; align-items: center; justify-content: center;}#calendar-card-body { padding: 0;}.strong { font-weight: bold;}.hidden { color: var(--navbar-background);}/*$vite$:1*/`)),document_head.appendChild(e)}}catch(e){console.error(`vite-plugin-css-injected-by-js`,e)}})(); })(target); } finally { var records = observer.takeRecords(); globalThis.__VITE_CSS_ELS__ = globalThis.__VITE_CSS_ELS__ || []; for (var i = 0; i < records.length; i++) { for (var j = 0; j < records[i].addedNodes.length; j++) { var node = records[i].addedNodes[j]; newElements.push(node); globalThis.__VITE_CSS_ELS__.push({ target: target, el: node }); } } observer.disconnect(); } executeInject.cache.push({ target: target, elements: newElements }); }; globalThis.__VITE_CSS_QUEUE__ = globalThis.__VITE_CSS_QUEUE__ || []; globalThis.__VITE_CSS_QUEUE__.push(executeInject); } })();
var VueUI = (function(exports) {
	Object.defineProperty(exports, Symbol.toStringTag, { value: "Module" });
	//#region src/i18n.js
	var PywbI18N = class PywbI18N {
		static #locale = "";
		static getLocale() {
			return PywbI18N.#locale;
		}
		static firstDayOfWeek = 1;
		static init = (locale, config) => {
			if (PywbI18N.instance) throw new Error("cannot instantiate PywbI18N twice");
			PywbI18N.#locale = locale;
			PywbI18N.instance = new PywbI18N(config);
			let intlLocale = new Intl.Locale(PywbI18N.getLocale());
			if ("weekInfo" in intlLocale) PywbI18N.firstDayOfWeek = intlLocale.weekInfo.firstDay % 7;
		};
		static monthIdPrefix = {
			1: "jan",
			2: "feb",
			3: "mar",
			4: "apr",
			5: "may",
			6: "jun",
			7: "jul",
			8: "aug",
			9: "sep",
			10: "oct",
			11: "nov",
			12: "dec"
		};
		static instance = null;
		constructor(config) {
			this.config = { ...config };
		}
		getMonth(id, type = "long") {
			return decodeURIComponent(this.config[PywbI18N.monthIdPrefix[id] + "_" + type]);
		}
		getWeekDay(id, type = "long") {
			return decodeURIComponent(this.config[id + "_" + type]);
		}
		getWeekDays(type = "long") {
			let weekDays = [
				"sun",
				"mon",
				"tue",
				"wed",
				"thu",
				"fri",
				"sat"
			];
			return weekDays.concat(weekDays).slice(PywbI18N.firstDayOfWeek, PywbI18N.firstDayOfWeek + 7).map((d) => this.getWeekDay(d, type));
		}
		getText(id, embeddedVariableStrings = null) {
			const translated = decodeURIComponent(this.config[id] || id);
			if (embeddedVariableStrings && id.indexOf("{") >= 0 && id.indexOf("}") >= 0) return translated.replace(/{(\w+)}/g, (match, stringId) => embeddedVariableStrings[stringId]);
			return translated;
		}
		_(id, embeddedVariableStrings = null) {
			return this.getText(id, embeddedVariableStrings);
		}
	};
	//#endregion
	//#region src/model.js
	var PywbPeriodIdDelimiter = "-";
	function PywbData(rawSnaps) {
		const allTimePeriod = new PywbPeriod({
			type: PywbPeriod.Type.all,
			id: "all"
		});
		const snapshots = [];
		let lastSingle = null;
		let lastYear, lastMonth, lastDay, lastHour;
		rawSnaps.forEach((rawSnap, i) => {
			const snap = new PywbSnapshot(rawSnap, i);
			let year, month, day, hour, single;
			if (!(year = allTimePeriod.getChildById(snap.year))) {
				if (lastYear) lastYear.checkIfSingleSnapshotOnly();
				lastYear = year = new PywbPeriod({
					type: PywbPeriod.Type.year,
					id: snap.year
				});
				allTimePeriod.addChild(year);
			}
			if (!(month = year.getChildById(snap.month))) {
				if (lastMonth) lastMonth.checkIfSingleSnapshotOnly();
				lastMonth = month = new PywbPeriod({
					type: PywbPeriod.Type.month,
					id: snap.month
				});
				year.addChild(month);
			}
			if (!(day = month.getChildById(snap.day))) {
				if (lastDay) lastDay.checkIfSingleSnapshotOnly();
				lastDay = day = new PywbPeriod({
					type: PywbPeriod.Type.day,
					id: snap.day
				});
				month.addChild(day);
			}
			const hourValue = Math.ceil((snap.hour + 1e-4) / 3);
			if (!(hour = day.getChildById(hourValue))) {
				if (lastHour) lastHour.checkIfSingleSnapshotOnly();
				lastHour = hour = new PywbPeriod({
					type: PywbPeriod.Type.hour,
					id: hourValue
				});
				day.addChild(hour);
			}
			if (!(single = hour.getChildById(snap.id))) {
				single = new PywbPeriod({
					type: PywbPeriod.Type.snapshot,
					id: snap.id
				});
				hour.addChild(single);
			}
			if (!lastSingle || lastSingle.id !== single.id) {
				single.setSnapshot(snap);
				if (lastSingle) {
					lastSingle.setNextSnapshotPeriod(single);
					single.setPreviousSnapshotPeriod(lastSingle);
				}
				lastSingle = single;
				snapshots.push(snap);
			}
			if (i === rawSnaps.length - 1) {
				year.checkIfSingleSnapshotOnly();
				month.checkIfSingleSnapshotOnly();
				day.checkIfSingleSnapshotOnly();
				hour.checkIfSingleSnapshotOnly();
			}
		});
		this.timeline = allTimePeriod;
		this.snapshots = snapshots;
		this.getSnapshot = function(index) {
			if (index < 0 || index >= this.snapshots.length) return null;
			return this.snapshots[index];
		};
		this.getPreviousSnapshot = function(snapshot) {
			const index = snapshot.index;
			return this.getSnapshot(index - 1);
		};
		this.getNextSnapshot = function(snapshot) {
			const index = snapshot.index;
			return this.getSnapshot(index + 1);
		};
	}
	var PywbSnapshot = class {
		constructor(init, index) {
			this.index = index;
			this.year = parseInt(init.timestamp.substr(0, 4));
			this.month = parseInt(init.timestamp.substr(4, 2));
			this.day = parseInt(init.timestamp.substr(6, 2));
			this.hour = parseInt(init.timestamp.substr(8, 2));
			this.minute = parseInt(init.timestamp.substr(10, 2));
			this.second = parseInt(init.timestamp.substr(12, 2));
			this.id = parseInt(init.timestamp);
			this.urlkey = init.urlkey;
			this.url = init.url;
			this.mime = init.mime;
			this.status = init.status;
			this.digest = init.digest;
			this.redirect = init.redirect;
			this.robotflags = init.robotflags;
			this.length = init.length;
			this.offset = init.offset;
			this.filename = init.filename;
			this.load_url = init.load_url;
			this["source-col"] = init["source-col"];
			this.access = init.access;
		}
		getTimeDateFormatted() {
			return new Date(this.year, this.month - 1, this.day, this.hour, this.minute, this.second).toLocaleString(PywbI18N.getLocale()).toLowerCase();
		}
		getDateFormatted() {
			return new Date(this.year, this.month - 1, this.day).toLocaleDateString(PywbI18N.getLocale()).toLowerCase();
		}
		getTimeFormatted() {
			return new Date(2e3, 0, 1, this.hour, this.minute, this.second).toLocaleTimeString(PywbI18N.getLocale()).toLowerCase();
		}
		getParentIds() {
			return [
				this.year,
				this.month,
				this.day,
				Math.ceil((this.hour + 1e-4) / 3)
			];
		}
		getFullId() {
			return [
				this.year,
				this.month,
				this.day,
				Math.ceil((this.hour + 1e-4) / 3),
				this.id
			].join(PywbPeriodIdDelimiter);
		}
	};
	function PywbPeriod(init) {
		this.type = init.type;
		this.id = init.id;
		this.fullId = Math.floor(1e6 + Math.random() * 9 * 1e3 * 1e3).toString(16);
		this.childrenIds = {};
		this.children = [];
		this.maxGrandchildSnapshotCount = 0;
		this.snapshotCount = 0;
	}
	PywbPeriod.Type = {
		all: 0,
		year: 1,
		month: 2,
		day: 3,
		hour: 4,
		snapshot: 5
	};
	PywbPeriod.TypeLabel = [
		"timeline",
		"year",
		"month",
		"day",
		"hour",
		"snapshot"
	];
	PywbPeriod.prototype.getTypeLabel = function() {
		return PywbPeriod.TypeLabel[this.type];
	};
	PywbPeriod.GetTypeLabel = function(type) {
		return PywbPeriod.TypeLabel[type] ? PywbPeriod.TypeLabel[type] : "";
	};
	PywbPeriod.prototype.getChildById = function(id) {
		return this.children[this.childrenIds[id]];
	};
	PywbPeriod.prototype.getPreviousSnapshotPeriod = () => {};
	PywbPeriod.prototype.setPreviousSnapshotPeriod = function(period) {
		this.getPreviousSnapshotPeriod = () => period;
	};
	PywbPeriod.prototype.getNextSnapshotPeriod = () => {};
	PywbPeriod.prototype.setNextSnapshotPeriod = function(period) {
		this.getNextSnapshotPeriod = () => period;
	};
	PywbPeriod.prototype.getFirstSnapshotPeriod = function() {
		return this.getFirstLastSnapshotPeriod_("first");
	};
	PywbPeriod.prototype.getLastSnapshotPeriod = function() {
		return this.getFirstLastSnapshotPeriod_("last");
	};
	PywbPeriod.prototype.getFirstLastSnapshotPeriod_ = function(direction) {
		let period = this;
		let iFailSafe = 100;
		while (period.snapshotCount && period.type !== PywbPeriod.Type.snapshot) {
			let i = 0;
			for (i = 0; i < period.children.length; i++) {
				const ii = direction === "first" ? i : period.children.length - 1 - i;
				if (period.children[ii].snapshotCount) {
					period = period.children[ii];
					break;
				}
			}
			if (iFailSafe-- < 0) break;
		}
		if (period.type === PywbPeriod.Type.snapshot && period.snapshot) return period;
		return null;
	};
	PywbPeriod.prototype.getPrevious = function() {
		const firstSnapshotPeriod = this.getFirstSnapshotPeriod();
		if (!firstSnapshotPeriod) return null;
		const previousSnapshotPeriod = firstSnapshotPeriod.getPreviousSnapshotPeriod();
		if (!previousSnapshotPeriod) return null;
		if (this.type === PywbPeriod.Type.snapshot) return previousSnapshotPeriod;
		let parent = previousSnapshotPeriod.parent;
		while (parent) {
			if (parent.type === this.type) break;
			parent = parent.parent;
		}
		return parent;
	};
	PywbPeriod.prototype.getNext = function() {
		const lastSnapshotPeriod = this.getLastSnapshotPeriod();
		if (!lastSnapshotPeriod) return null;
		const nextSnapshotPeriod = lastSnapshotPeriod.getNextSnapshotPeriod();
		if (!nextSnapshotPeriod) return null;
		if (this.type === PywbPeriod.Type.snapshot) return nextSnapshotPeriod;
		let parent = nextSnapshotPeriod.parent;
		while (parent) {
			if (parent.type === this.type) break;
			parent = parent.parent;
		}
		return parent;
	};
	PywbPeriod.prototype.parent = null;
	PywbPeriod.prototype.addChild = function(period) {
		if (this.getChildById(period.id)) return false;
		period.parent = this;
		this.childrenIds[period.id] = this.children.length;
		this.children.push(period);
		period.initFullId();
		return true;
	};
	PywbPeriod.prototype.getChildrenRange = function() {
		switch (this.type) {
			case PywbPeriod.Type.all: return [this.children[0].id, this.children[this.children.length - 1].id];
			case PywbPeriod.Type.year: return [1, 12];
			case PywbPeriod.Type.month: {
				const y = this.parent.id;
				const m = this.id;
				return [1, new Date(new Date(y, m, 1).getTime() - 1e3).getDate()];
			}
			case PywbPeriod.Type.day: return [1, 8];
		}
		return null;
	};
	PywbPeriod.prototype.fillEmptyGrandChildPeriods = function() {
		if (this.hasFilledEmptyGrandchildPeriods) return;
		this.children.forEach((c) => {
			c.fillEmptyChildPeriods();
		});
		this.hasFilledEmptyGrandchildPeriods = true;
	};
	PywbPeriod.prototype.fillEmptyChildPeriods = function(isFillEmptyGrandChildrenPeriods = false) {
		if (this.type > PywbPeriod.Type.day) return;
		const idRange = this.getChildrenRange();
		if (!idRange) return;
		let i = 0;
		for (let newId = idRange[0]; newId <= idRange[1]; newId++) if (i < this.children.length) {
			if (this.children[i].id !== newId) {
				const empty = new PywbPeriod({
					type: this.type + 1,
					id: newId
				});
				if (newId < this.children[i].id) this.children.splice(i, 0, empty);
				else this.children.splice(i + 1, 0, empty);
				empty.parent = this;
				empty.initFullId();
			}
			i++;
		} else {
			const empty = new PywbPeriod({
				type: this.type + 1,
				id: newId
			});
			this.addChild(empty);
		}
		for (let i = 0; i < this.children.length; i++) this.childrenIds[this.children[i].id] = i;
		if (isFillEmptyGrandChildrenPeriods) this.fillEmptyGrandChildPeriods();
		return idRange;
	};
	PywbPeriod.prototype.getParents = function(skipAllTime = false) {
		let parents = [];
		let parent = this.parent;
		while (parent) {
			parents.push(parent);
			parent = parent.parent;
		}
		parents = parents.reverse();
		if (skipAllTime) parents.shift();
		return parents;
	};
	PywbPeriod.prototype.contains = function(periodOrSnapshot) {
		if (this.type === 0) return true;
		if (periodOrSnapshot instanceof PywbPeriod) return periodOrSnapshot.getParents(true).slice(0, this.type).map((p) => p.id).join(PywbPeriodIdDelimiter) === this.fullId;
		if (periodOrSnapshot instanceof PywbSnapshot) {
			if (this.type === PywbPeriod.Type.snapshot) return periodOrSnapshot.getFullId() === this.fullId;
			else return periodOrSnapshot.getParentIds(true).slice(0, this.type).join(PywbPeriodIdDelimiter) === this.fullId;
		}
		return false;
	};
	PywbPeriod.prototype.snapshot = null;
	PywbPeriod.prototype.snapshotPeriod = null;
	PywbPeriod.prototype.checkIfSingleSnapshotOnly = function() {
		if (this.snapshotCount === 1) {
			let snapshotPeriod = this;
			let failSafe = PywbPeriod.Type.snapshot;
			while (!snapshotPeriod.snapshot) {
				if (--failSafe <= 0) break;
				snapshotPeriod = snapshotPeriod.children[0];
			}
			this.snapshot = snapshotPeriod.snapshot;
			this.snapshotPeriod = snapshotPeriod;
		}
	};
	PywbPeriod.prototype.setSnapshot = function(snap) {
		this.snapshot = snap;
		this.snapshotCount++;
		let parent = this.parent;
		let child = this;
		while (parent) {
			parent.snapshotCount++;
			let grandParent = parent.parent;
			if (grandParent) grandParent.maxGrandchildSnapshotCount = Math.max(grandParent.maxGrandchildSnapshotCount, child.snapshotCount);
			child = parent;
			parent = parent.parent;
		}
	};
	PywbPeriod.prototype.getSnapshotPeriodsFlat = function(flatArray = false) {
		if (!flatArray) flatArray = [];
		if (!this.snapshotCount) return flatArray;
		if (this.snapshotCount === 1) {
			flatArray.push(this.snapshotPeriod || this);
			return flatArray;
		}
		this.children.forEach((child) => {
			child.getSnapshotPeriodsFlat(flatArray);
		});
		return flatArray;
	};
	PywbPeriod.prototype.initFullId = function() {
		const ids = this.getParents(true).map((p) => p.id);
		ids.push(this.id);
		this.fullId = ids.join(PywbPeriodIdDelimiter);
	};
	PywbPeriod.prototype.findByFullId = function(fullId) {
		let parent = this;
		if (this.type !== PywbPeriod.Type.all) parent = this.getParents()[0];
		const ids = fullId.split(PywbPeriodIdDelimiter);
		let found = false;
		for (let i = 0; i < ids.length; i++) {
			parent = parent.getChildById(ids[i]);
			if (parent) {
				if (i === ids.length - 1) found = parent;
			} else break;
		}
		return found;
	};
	PywbPeriod.prototype.getFullReadableId = function() {
		switch (this.type) {
			case PywbPeriod.Type.all: return "";
			case PywbPeriod.Type.year: return this.id;
			case PywbPeriod.Type.month: return this.getReadableId() + " " + this.parent.id;
			case PywbPeriod.Type.day: return new Date(this.parent.parent.id, this.parent.id, this.getReadableId()).toLocaleDateString(PywbI18N.getLocale());
			case PywbPeriod.Type.hour:
				const hourRange = this.getReadableId({ hourRange: true });
				return this.parent.getFullReadableId() + " " + PywbI18N.instance._("from {hour1} to {hour2}", {
					hour1: hourRange[0],
					hour2: hourRange[1]
				});
			case PywbPeriod.Type.snapshot: return this.snapshot.getTimeDateFormatted();
		}
	};
	PywbPeriod.prototype.getReadableId = function(opts = { hourRange: null }) {
		switch (this.type) {
			case PywbPeriod.Type.all: return PywbI18N.instance._("All-time");
			case PywbPeriod.Type.year: return this.id;
			case PywbPeriod.Type.month: return PywbI18N.instance.getMonth(this.id, "short");
			case PywbPeriod.Type.day: return this.id + "";
			case PywbPeriod.Type.hour:
				const hours = [
					0,
					3,
					6,
					9,
					12,
					15,
					18,
					21
				].map((hour) => new Date(2e3, 0, 1, hour, 0, 0).toLocaleTimeString(PywbI18N.getLocale()).replace(/^(\d{1,2}:\d\d):\d\d/, (m, m1) => m1).toLowerCase());
				if (opts.hourRange) return [hours[this.id - 1], hours[this.id % hours.length]];
				return hours[this.id - 1];
			case PywbPeriod.Type.snapshot: return this.snapshot.getTimeFormatted();
		}
	};
	PywbPeriod.prototype.getYear = function() {
		this.get(PywbPeriod.Type.year);
	};
	PywbPeriod.prototype.getMonth = function() {
		this.get(PywbPeriod.Type.month);
	};
	PywbPeriod.prototype.getDay = function() {
		this.get(PywbPeriod.Type.day);
	};
	PywbPeriod.prototype.getHour = function() {
		this.get(PywbPeriod.Type.hour);
	};
	PywbPeriod.prototype.get = function(type) {
		if (this.type === type) return this;
		else if (this.type > type) return this.getParents()[type];
	};
	//#endregion
	//#region node_modules/@vue/shared/dist/shared.esm-bundler.js
	function makeMap(str) {
		const map = Object.create(null);
		for (const key of str.split(",")) map[key] = 1;
		return (val) => val in map;
	}
	var EMPTY_OBJ = {};
	var EMPTY_ARR = [];
	var NOOP = () => {};
	var NO = () => false;
	var isOn = (key) => key.charCodeAt(0) === 111 && key.charCodeAt(1) === 110 && (key.charCodeAt(2) > 122 || key.charCodeAt(2) < 97);
	var isModelListener = (key) => key.startsWith("onUpdate:");
	var extend = Object.assign;
	var remove = (arr, el) => {
		const i = arr.indexOf(el);
		if (i > -1) arr.splice(i, 1);
	};
	var hasOwnProperty$1 = Object.prototype.hasOwnProperty;
	var hasOwn = (val, key) => hasOwnProperty$1.call(val, key);
	var isArray = Array.isArray;
	var isMap = (val) => toTypeString(val) === "[object Map]";
	var isSet = (val) => toTypeString(val) === "[object Set]";
	var isDate = (val) => toTypeString(val) === "[object Date]";
	var isFunction = (val) => typeof val === "function";
	var isString = (val) => typeof val === "string";
	var isSymbol = (val) => typeof val === "symbol";
	var isObject = (val) => val !== null && typeof val === "object";
	var isPromise = (val) => {
		return (isObject(val) || isFunction(val)) && isFunction(val.then) && isFunction(val.catch);
	};
	var objectToString = Object.prototype.toString;
	var toTypeString = (value) => objectToString.call(value);
	var toRawType = (value) => {
		return toTypeString(value).slice(8, -1);
	};
	var isPlainObject = (val) => toTypeString(val) === "[object Object]";
	var isIntegerKey = (key) => isString(key) && key !== "NaN" && key[0] !== "-" && "" + parseInt(key, 10) === key;
	var isReservedProp = makeMap(",key,ref,ref_for,ref_key,onVnodeBeforeMount,onVnodeMounted,onVnodeBeforeUpdate,onVnodeUpdated,onVnodeBeforeUnmount,onVnodeUnmounted");
	var cacheStringFunction = (fn) => {
		const cache = Object.create(null);
		return ((str) => {
			return cache[str] || (cache[str] = fn(str));
		});
	};
	var camelizeRE = /-\w/g;
	var camelize = cacheStringFunction((str) => {
		return str.replace(camelizeRE, (c) => c.slice(1).toUpperCase());
	});
	var hyphenateRE = /\B([A-Z])/g;
	var hyphenate = cacheStringFunction((str) => str.replace(hyphenateRE, "-$1").toLowerCase());
	var capitalize = cacheStringFunction((str) => {
		return str.charAt(0).toUpperCase() + str.slice(1);
	});
	var toHandlerKey = cacheStringFunction((str) => {
		return str ? `on${capitalize(str)}` : ``;
	});
	var hasChanged = (value, oldValue) => !Object.is(value, oldValue);
	var invokeArrayFns = (fns, ...arg) => {
		for (let i = 0; i < fns.length; i++) fns[i](...arg);
	};
	var def = (obj, key, value, writable = false) => {
		Object.defineProperty(obj, key, {
			configurable: true,
			enumerable: false,
			writable,
			value
		});
	};
	var looseToNumber = (val) => {
		const n = parseFloat(val);
		return isNaN(n) ? val : n;
	};
	var _globalThis;
	var getGlobalThis = () => {
		return _globalThis || (_globalThis = typeof globalThis !== "undefined" ? globalThis : typeof self !== "undefined" ? self : typeof window !== "undefined" ? window : typeof global !== "undefined" ? global : {});
	};
	function normalizeStyle(value) {
		if (isArray(value)) {
			const res = {};
			for (let i = 0; i < value.length; i++) {
				const item = value[i];
				const normalized = isString(item) ? parseStringStyle(item) : normalizeStyle(item);
				if (normalized) for (const key in normalized) res[key] = normalized[key];
			}
			return res;
		} else if (isString(value) || isObject(value)) return value;
	}
	var listDelimiterRE = /;(?![^(]*\))/g;
	var propertyDelimiterRE = /:([^]+)/;
	var styleCommentRE = /"(?:[^"\\]|\\[^])*"|'(?:[^'\\]|\\[^])*'|\\[^]|\/\*[^]*?\*\//g;
	function parseStringStyle(cssText) {
		const ret = {};
		cssText.replace(styleCommentRE, (match) => match.startsWith("/*") ? "" : match).split(listDelimiterRE).forEach((item) => {
			if (item) {
				const tmp = item.split(propertyDelimiterRE);
				tmp.length > 1 && (ret[tmp[0].trim()] = tmp[1].trim());
			}
		});
		return ret;
	}
	function normalizeClass(value) {
		let res = "";
		if (isString(value)) res = value;
		else if (isArray(value)) for (let i = 0; i < value.length; i++) {
			const normalized = normalizeClass(value[i]);
			if (normalized) res += normalized + " ";
		}
		else if (isObject(value)) {
			for (const name in value) if (value[name]) res += name + " ";
		}
		return res.trim();
	}
	var specialBooleanAttrs = `itemscope,allowfullscreen,formnovalidate,ismap,nomodule,novalidate,readonly`;
	var isSpecialBooleanAttr = makeMap(specialBooleanAttrs);
	var isBooleanAttr = makeMap(specialBooleanAttrs + `,async,autofocus,autoplay,controls,default,defer,disabled,inert,loop,open,required,reversed,scoped,seamless,checked,muted,multiple,selected`);
	function includeBooleanAttr(value) {
		return !!value || value === "";
	}
	function looseCompareArrays(a, b, seen) {
		if (a.length !== b.length) return false;
		let equal = true;
		for (let i = 0; equal && i < a.length; i++) equal = looseEqual(a[i], b[i], seen);
		return equal;
	}
	function looseCompareCollections(a, b, seen) {
		if (a.size !== b.size) return false;
		const candidates = Array.from(b);
		const matched = new Uint8Array(candidates.length);
		for (const item of a) {
			let index = -1;
			for (let i = 0; i < candidates.length; i++) if (!matched[i] && looseEqual(item, candidates[i], seen)) {
				index = i;
				break;
			}
			if (index < 0) return false;
			matched[index] = 1;
		}
		return true;
	}
	function looseCompareObjects(a, b, seen) {
		let aValidType = isMap(a);
		let bValidType = isMap(b);
		if (aValidType || bValidType) return aValidType && bValidType ? looseCompareCollections(a, b, seen) : false;
		aValidType = isSet(a);
		bValidType = isSet(b);
		if (aValidType || bValidType) return aValidType && bValidType ? looseCompareCollections(a, b, seen) : false;
		if (Object.keys(a).length !== Object.keys(b).length) return false;
		for (const key in a) {
			const aHasKey = a.hasOwnProperty(key);
			const bHasKey = b.hasOwnProperty(key);
			if (aHasKey && !bHasKey || !aHasKey && bHasKey || !looseEqual(a[key], b[key], seen)) return false;
		}
		return String(a) === String(b);
	}
	function looseCompareNested(a, b, seen, compare) {
		if (!seen) seen = [new Map(), new Map()];
		const [seenA, seenB] = seen;
		if (seenA.has(a) || seenB.has(b)) return seenA.get(a) === b && seenB.get(b) === a;
		seenA.set(a, b);
		seenB.set(b, a);
		const equal = compare(a, b, seen);
		seenA.delete(a);
		seenB.delete(b);
		return equal;
	}
	function looseEqual(a, b, seen) {
		if (a === b) return true;
		let aValidType = isDate(a);
		let bValidType = isDate(b);
		if (aValidType || bValidType) return aValidType && bValidType ? a.getTime() === b.getTime() : false;
		aValidType = isSymbol(a);
		bValidType = isSymbol(b);
		if (aValidType || bValidType) return a === b;
		aValidType = isArray(a);
		bValidType = isArray(b);
		if (aValidType || bValidType) return aValidType && bValidType ? looseCompareNested(a, b, seen, looseCompareArrays) : false;
		aValidType = isObject(a);
		bValidType = isObject(b);
		if (aValidType || bValidType) {
			if (!aValidType || !bValidType) return false;
			return looseCompareNested(a, b, seen, looseCompareObjects);
		}
		return String(a) === String(b);
	}
	var isRef$1 = (val) => {
		return !!(val && val["__v_isRef"] === true);
	};
	var toDisplayString = (val) => {
		return isString(val) ? val : val == null ? "" : isArray(val) || isObject(val) && (val.toString === objectToString || !isFunction(val.toString)) ? isRef$1(val) ? toDisplayString(val.value) : JSON.stringify(val, replacer, 2) : String(val);
	};
	var replacer = (_key, val) => {
		if (isRef$1(val)) return replacer(_key, val.value);
		else if (isMap(val)) return { [`Map(${val.size})`]: [...val.entries()].reduce((entries, [key, val2], i) => {
			entries[stringifySymbol(key, i) + " =>"] = val2;
			return entries;
		}, {}) };
		else if (isSet(val)) return { [`Set(${val.size})`]: [...val.values()].map((v) => stringifySymbol(v)) };
		else if (isSymbol(val)) return stringifySymbol(val);
		else if (isObject(val) && !isArray(val) && !isPlainObject(val)) return String(val);
		return val;
	};
	var stringifySymbol = (v, i = "") => {
		var _a;
		return isSymbol(v) ? `Symbol(${(_a = v.description) != null ? _a : i})` : v;
	};
	//#endregion
	//#region node_modules/@vue/reactivity/dist/reactivity.esm-bundler.js
	var activeEffectScope;
	var EffectScope = class {
		constructor(detached = false) {
			this.detached = detached;
			this._active = true;
			this._on = 0;
			this.effects = [];
			this.cleanups = [];
			this._isPaused = false;
			this._warnOnRun = true;
			this.__v_skip = true;
			if (!detached && activeEffectScope) {
				if (activeEffectScope.active) {
					this.parent = activeEffectScope;
					this.index = (activeEffectScope.scopes || (activeEffectScope.scopes = [])).push(this) - 1;
				} else {
					this._active = false;
					this._warnOnRun = false;
				}
			}
		}
		get active() {
			return this._active;
		}
		pause() {
			if (this._active) {
				this._isPaused = true;
				let i, l;
				if (this.scopes) {
					const scopes = this.scopes.slice();
					for (i = 0, l = scopes.length; i < l; i++) scopes[i].pause();
				}
				for (i = 0, l = this.effects.length; i < l; i++) this.effects[i].pause();
			}
		}
		resume() {
			if (this._active) {
				if (this._isPaused) {
					this._isPaused = false;
					let i, l;
					if (this.scopes) {
						const scopes = this.scopes.slice();
						for (i = 0, l = scopes.length; i < l; i++) scopes[i].resume();
					}
					const effects = this.effects.slice();
					for (i = 0, l = effects.length; i < l; i++) effects[i].resume();
				}
			}
		}
		run(fn) {
			if (this._active) {
				const currentEffectScope = activeEffectScope;
				try {
					activeEffectScope = this;
					return fn();
				} finally {
					activeEffectScope = currentEffectScope;
				}
			}
		}
		on() {
			if (++this._on === 1) {
				this.prevScope = activeEffectScope;
				activeEffectScope = this;
			}
		}
		off() {
			if (this._on > 0 && --this._on === 0) {
				if (activeEffectScope === this) activeEffectScope = this.prevScope;
				else {
					let current = activeEffectScope;
					while (current) {
						if (current.prevScope === this) {
							current.prevScope = this.prevScope;
							break;
						}
						current = current.prevScope;
					}
				}
				this.prevScope = void 0;
			}
		}
		stop(fromParent) {
			if (this._active) {
				this._active = false;
				let i, l;
				for (i = 0, l = this.effects.length; i < l; i++) this.effects[i].stop();
				this.effects.length = 0;
				for (i = 0, l = this.cleanups.length; i < l; i++) this.cleanups[i]();
				this.cleanups.length = 0;
				if (this.scopes) {
					const scopes = this.scopes.slice();
					for (i = 0, l = scopes.length; i < l; i++) scopes[i].stop(true);
					this.scopes.length = 0;
				}
				if (!this.detached && this.parent && !fromParent) {
					const last = this.parent.scopes.pop();
					if (last && last !== this) {
						this.parent.scopes[this.index] = last;
						last.index = this.index;
					}
				}
				this.parent = void 0;
			}
		}
	};
	function getCurrentScope() {
		return activeEffectScope;
	}
	var activeSub;
	var pausedQueueEffects = new WeakSet();
	var ReactiveEffect = class {
		constructor(fn) {
			this.fn = fn;
			this.deps = void 0;
			this.depsTail = void 0;
			this.flags = 5;
			this.next = void 0;
			this.cleanup = void 0;
			this.scheduler = void 0;
			if (activeEffectScope) {
				if (activeEffectScope.active) activeEffectScope.effects.push(this);
				else this.flags &= -2;
			}
		}
		pause() {
			this.flags |= 64;
		}
		resume() {
			if (this.flags & 64) {
				this.flags &= -65;
				if (pausedQueueEffects.has(this)) {
					pausedQueueEffects.delete(this);
					this.trigger();
				}
			}
		}
		notify() {
			if (this.flags & 2 && !(this.flags & 32)) return;
			if (!(this.flags & 8)) batch(this);
		}
		run() {
			if (!(this.flags & 1)) return this.fn();
			this.flags |= 2;
			cleanupEffect(this);
			prepareDeps(this);
			const prevEffect = activeSub;
			const prevShouldTrack = shouldTrack;
			activeSub = this;
			shouldTrack = true;
			try {
				return this.fn();
			} finally {
				cleanupDeps(this);
				activeSub = prevEffect;
				shouldTrack = prevShouldTrack;
				this.flags &= -3;
			}
		}
		stop() {
			if (this.flags & 1) {
				for (let link = this.deps; link; link = link.nextDep) removeSub(link);
				this.deps = this.depsTail = void 0;
				cleanupEffect(this);
				this.onStop && this.onStop();
				this.flags &= -2;
			}
		}
		trigger() {
			if (this.flags & 64) pausedQueueEffects.add(this);
			else if (this.scheduler) this.scheduler();
			else this.runIfDirty();
		}
		runIfDirty() {
			if (isDirty(this)) this.run();
		}
		get dirty() {
			return isDirty(this);
		}
	};
	var batchDepth = 0;
	var batchedSub;
	var batchedComputed;
	function batch(sub, isComputed = false) {
		sub.flags |= 8;
		if (isComputed) {
			sub.next = batchedComputed;
			batchedComputed = sub;
			return;
		}
		sub.next = batchedSub;
		batchedSub = sub;
	}
	function startBatch() {
		batchDepth++;
	}
	function endBatch() {
		if (--batchDepth > 0) return;
		if (batchedComputed) {
			let e = batchedComputed;
			batchedComputed = void 0;
			while (e) {
				const next = e.next;
				e.next = void 0;
				e.flags &= -9;
				e = next;
			}
		}
		let error;
		while (batchedSub) {
			let e = batchedSub;
			batchedSub = void 0;
			while (e) {
				const next = e.next;
				e.next = void 0;
				e.flags &= -9;
				if (e.flags & 1) try {
					e.trigger();
				} catch (err) {
					if (!error) error = err;
				}
				e = next;
			}
		}
		if (error) throw error;
	}
	function prepareDeps(sub) {
		for (let link = sub.deps; link; link = link.nextDep) {
			link.version = -1;
			link.prevActiveLink = link.dep.activeLink;
			link.dep.activeLink = link;
		}
	}
	function cleanupDeps(sub) {
		let head;
		let tail = sub.depsTail;
		let link = tail;
		while (link) {
			const prev = link.prevDep;
			if (link.version === -1) {
				if (link === tail) tail = prev;
				removeSub(link);
				removeDep(link);
			} else head = link;
			link.dep.activeLink = link.prevActiveLink;
			link.prevActiveLink = void 0;
			link = prev;
		}
		sub.deps = head;
		sub.depsTail = tail;
	}
	function isDirty(sub) {
		for (let link = sub.deps; link; link = link.nextDep) if (link.dep.version !== link.version || link.dep.computed && (refreshComputed(link.dep.computed) || link.dep.version !== link.version)) return true;
		if (sub._dirty) return true;
		return false;
	}
	function refreshComputed(computed) {
		if (computed.flags & 4 && !(computed.flags & 16)) return;
		computed.flags &= -17;
		if (computed.globalVersion === globalVersion) return;
		computed.globalVersion = globalVersion;
		if (!computed.isSSR && computed.flags & 128 && (!computed.deps && !computed._dirty || !isDirty(computed))) return;
		computed.flags |= 2;
		const dep = computed.dep;
		const prevSub = activeSub;
		const prevShouldTrack = shouldTrack;
		activeSub = computed;
		shouldTrack = true;
		try {
			prepareDeps(computed);
			const value = computed.fn(computed._value);
			if (dep.version === 0 || hasChanged(value, computed._value)) {
				computed.flags |= 128;
				computed._value = value;
				dep.version++;
			}
		} catch (err) {
			dep.version++;
			throw err;
		} finally {
			activeSub = prevSub;
			shouldTrack = prevShouldTrack;
			cleanupDeps(computed);
			computed.flags &= -3;
		}
	}
	function removeSub(link, soft = false) {
		const { dep, prevSub, nextSub } = link;
		if (prevSub) {
			prevSub.nextSub = nextSub;
			link.prevSub = void 0;
		}
		if (nextSub) {
			nextSub.prevSub = prevSub;
			link.nextSub = void 0;
		}
		if (dep.subs === link) {
			dep.subs = prevSub;
			if (!prevSub && dep.computed) {
				dep.computed.flags &= -5;
				for (let l = dep.computed.deps; l; l = l.nextDep) removeSub(l, true);
			}
		}
		if (!soft && !--dep.sc && dep.map) dep.map.delete(dep.key);
	}
	function removeDep(link) {
		const { prevDep, nextDep } = link;
		if (prevDep) {
			prevDep.nextDep = nextDep;
			link.prevDep = void 0;
		}
		if (nextDep) {
			nextDep.prevDep = prevDep;
			link.nextDep = void 0;
		}
	}
	var shouldTrack = true;
	var trackStack = [];
	function pauseTracking() {
		trackStack.push(shouldTrack);
		shouldTrack = false;
	}
	function resetTracking() {
		const last = trackStack.pop();
		shouldTrack = last === void 0 ? true : last;
	}
	function cleanupEffect(e) {
		const { cleanup } = e;
		e.cleanup = void 0;
		if (cleanup) {
			const prevSub = activeSub;
			activeSub = void 0;
			try {
				cleanup();
			} finally {
				activeSub = prevSub;
			}
		}
	}
	var globalVersion = 0;
	var Link = class {
		constructor(sub, dep) {
			this.sub = sub;
			this.dep = dep;
			this.version = dep.version;
			this.nextDep = this.prevDep = this.nextSub = this.prevSub = this.prevActiveLink = void 0;
		}
	};
	var Dep = class {
		constructor(computed) {
			this.computed = computed;
			this.version = 0;
			this.activeLink = void 0;
			this.subs = void 0;
			this.map = void 0;
			this.key = void 0;
			this.sc = 0;
			this.__v_skip = true;
		}
		track(debugInfo) {
			if (!activeSub || !shouldTrack || activeSub === this.computed) return;
			let link = this.activeLink;
			if (link === void 0 || link.sub !== activeSub) {
				link = this.activeLink = new Link(activeSub, this);
				if (!activeSub.deps) activeSub.deps = activeSub.depsTail = link;
				else {
					link.prevDep = activeSub.depsTail;
					activeSub.depsTail.nextDep = link;
					activeSub.depsTail = link;
				}
				addSub(link);
			} else if (link.version === -1) {
				link.version = this.version;
				if (link.nextDep) {
					const next = link.nextDep;
					next.prevDep = link.prevDep;
					if (link.prevDep) link.prevDep.nextDep = next;
					link.prevDep = activeSub.depsTail;
					link.nextDep = void 0;
					activeSub.depsTail.nextDep = link;
					activeSub.depsTail = link;
					if (activeSub.deps === link) activeSub.deps = next;
				}
			}
			return link;
		}
		trigger(debugInfo) {
			this.version++;
			globalVersion++;
			this.notify(debugInfo);
		}
		notify(debugInfo) {
			startBatch();
			try {
				for (let link = this.subs; link; link = link.prevSub) if (link.sub.notify()) link.sub.dep.notify();
			} finally {
				endBatch();
			}
		}
	};
	function addSub(link) {
		link.dep.sc++;
		if (link.sub.flags & 4) {
			const computed = link.dep.computed;
			if (computed && !link.dep.subs) {
				computed.flags |= 20;
				for (let l = computed.deps; l; l = l.nextDep) addSub(l);
			}
			const currentTail = link.dep.subs;
			if (currentTail !== link) {
				link.prevSub = currentTail;
				if (currentTail) currentTail.nextSub = link;
			}
			link.dep.subs = link;
		}
	}
	var targetMap = new WeakMap();
	var ITERATE_KEY = Symbol("");
	var MAP_KEY_ITERATE_KEY = Symbol("");
	var ARRAY_ITERATE_KEY = Symbol("");
	function track(target, type, key) {
		if (shouldTrack && activeSub) {
			let depsMap = targetMap.get(target);
			if (!depsMap) targetMap.set(target, depsMap = new Map());
			let dep = depsMap.get(key);
			if (!dep) {
				depsMap.set(key, dep = new Dep());
				dep.map = depsMap;
				dep.key = key;
			}
			dep.track();
		}
	}
	function trigger(target, type, key, newValue, oldValue, oldTarget) {
		const depsMap = targetMap.get(target);
		if (!depsMap) {
			globalVersion++;
			return;
		}
		const run = (dep) => {
			if (dep) dep.trigger();
		};
		startBatch();
		if (type === "clear") depsMap.forEach(run);
		else {
			const targetIsArray = isArray(target);
			const isArrayIndex = targetIsArray && isIntegerKey(key);
			if (targetIsArray && key === "length") {
				const newLength = Number(newValue);
				depsMap.forEach((dep, key2) => {
					if (key2 === "length" || key2 === ARRAY_ITERATE_KEY || !isSymbol(key2) && key2 >= newLength) run(dep);
				});
			} else {
				if (key !== void 0 || depsMap.has(void 0)) run(depsMap.get(key));
				if (isArrayIndex) run(depsMap.get(ARRAY_ITERATE_KEY));
				switch (type) {
					case "add":
						if (!targetIsArray) {
							run(depsMap.get(ITERATE_KEY));
							if (isMap(target)) run(depsMap.get(MAP_KEY_ITERATE_KEY));
						} else if (isArrayIndex) run(depsMap.get("length"));
						break;
					case "delete":
						if (!targetIsArray) {
							run(depsMap.get(ITERATE_KEY));
							if (isMap(target)) run(depsMap.get(MAP_KEY_ITERATE_KEY));
						}
						break;
					case "set": if (isMap(target)) run(depsMap.get(ITERATE_KEY));
				}
			}
		}
		endBatch();
	}
	function reactiveReadArray(array) {
		const raw = toRaw(array);
		if (raw === array) return raw;
		track(raw, "iterate", ARRAY_ITERATE_KEY);
		if (isShallow(array)) return raw;
		if (!isReadonly(array)) return raw.map(toReactive);
		return isReactive(array) ? raw.map((item) => toReadonly(toReactive(item))) : raw.map(toReadonly);
	}
	function shallowReadArray(arr) {
		track(arr = toRaw(arr), "iterate", ARRAY_ITERATE_KEY);
		return arr;
	}
	function toWrapped(target, item) {
		if (isReadonly(target)) return isReactive(target) ? toReadonly(toReactive(item)) : toReadonly(item);
		return toReactive(item);
	}
	var arrayInstrumentations = {
		__proto__: null,
		[Symbol.iterator]() {
			return iterator(this, Symbol.iterator, (item) => toWrapped(this, item));
		},
		concat(...args) {
			return reactiveReadArray(this).concat(...args.map((x) => isArray(x) ? reactiveReadArray(x) : x));
		},
		entries() {
			return iterator(this, "entries", (value) => {
				value[1] = toWrapped(this, value[1]);
				return value;
			});
		},
		every(fn, thisArg) {
			return apply(this, "every", fn, thisArg, void 0, arguments);
		},
		filter(fn, thisArg) {
			return apply(this, "filter", fn, thisArg, (v) => v.map((item) => toWrapped(this, item)), arguments);
		},
		find(fn, thisArg) {
			return apply(this, "find", fn, thisArg, (item) => toWrapped(this, item), arguments);
		},
		findIndex(fn, thisArg) {
			return apply(this, "findIndex", fn, thisArg, void 0, arguments);
		},
		findLast(fn, thisArg) {
			return apply(this, "findLast", fn, thisArg, (item) => toWrapped(this, item), arguments);
		},
		findLastIndex(fn, thisArg) {
			return apply(this, "findLastIndex", fn, thisArg, void 0, arguments);
		},
		forEach(fn, thisArg) {
			return apply(this, "forEach", fn, thisArg, void 0, arguments);
		},
		includes(...args) {
			return searchProxy(this, "includes", args);
		},
		indexOf(...args) {
			return searchProxy(this, "indexOf", args);
		},
		join(separator) {
			return reactiveReadArray(this).join(separator);
		},
		lastIndexOf(...args) {
			return searchProxy(this, "lastIndexOf", args);
		},
		map(fn, thisArg) {
			return apply(this, "map", fn, thisArg, void 0, arguments);
		},
		pop() {
			return noTracking(this, "pop");
		},
		push(...args) {
			return noTracking(this, "push", args);
		},
		reduce(fn, ...args) {
			return reduce(this, "reduce", fn, args);
		},
		reduceRight(fn, ...args) {
			return reduce(this, "reduceRight", fn, args);
		},
		shift() {
			return noTracking(this, "shift");
		},
		some(fn, thisArg) {
			return apply(this, "some", fn, thisArg, void 0, arguments);
		},
		splice(...args) {
			return noTracking(this, "splice", args);
		},
		toReversed() {
			return reactiveReadArray(this).toReversed();
		},
		toSorted(comparer) {
			return reactiveReadArray(this).toSorted(comparer);
		},
		toSpliced(...args) {
			return reactiveReadArray(this).toSpliced(...args);
		},
		unshift(...args) {
			return noTracking(this, "unshift", args);
		},
		values() {
			return iterator(this, "values", (item) => toWrapped(this, item));
		}
	};
	function iterator(self, method, wrapValue) {
		const arr = shallowReadArray(self);
		const iter = arr[method]();
		if (arr !== self && !isShallow(self)) {
			iter._next = iter.next;
			iter.next = () => {
				const result = iter._next();
				if (!result.done) result.value = wrapValue(result.value);
				return result;
			};
		}
		return iter;
	}
	var arrayProto = Array.prototype;
	function apply(self, method, fn, thisArg, wrappedRetFn, args) {
		const arr = shallowReadArray(self);
		const needsWrap = arr !== self && !isShallow(self);
		const methodFn = arr[method];
		if (methodFn !== arrayProto[method]) {
			const result2 = methodFn.apply(self, args);
			return needsWrap ? toReactive(result2) : result2;
		}
		let wrappedFn = fn;
		if (arr !== self) {
			if (needsWrap) wrappedFn = function(item, index) {
				return fn.call(this, toWrapped(self, item), index, self);
			};
			else if (fn.length > 2) wrappedFn = function(item, index) {
				return fn.call(this, item, index, self);
			};
		}
		const result = methodFn.call(arr, wrappedFn, thisArg);
		return needsWrap && wrappedRetFn ? wrappedRetFn(result) : result;
	}
	function reduce(self, method, fn, args) {
		const arr = shallowReadArray(self);
		const needsWrap = arr !== self && !isShallow(self);
		let wrappedFn = fn;
		let wrapInitialAccumulator = false;
		if (arr !== self) {
			if (needsWrap) {
				wrapInitialAccumulator = args.length === 0;
				wrappedFn = function(acc, item, index) {
					if (wrapInitialAccumulator) {
						wrapInitialAccumulator = false;
						acc = toWrapped(self, acc);
					}
					return fn.call(this, acc, toWrapped(self, item), index, self);
				};
			} else if (fn.length > 3) wrappedFn = function(acc, item, index) {
				return fn.call(this, acc, item, index, self);
			};
		}
		const result = arr[method](wrappedFn, ...args);
		return wrapInitialAccumulator ? toWrapped(self, result) : result;
	}
	function searchProxy(self, method, args) {
		const arr = toRaw(self);
		track(arr, "iterate", ARRAY_ITERATE_KEY);
		const res = arr[method](...args);
		if ((res === -1 || res === false) && isProxy(args[0])) {
			args[0] = toRaw(args[0]);
			return arr[method](...args);
		}
		return res;
	}
	function noTracking(self, method, args = []) {
		pauseTracking();
		startBatch();
		const res = toRaw(self)[method].apply(self, args);
		endBatch();
		resetTracking();
		return res;
	}
	var isNonTrackableKeys = makeMap(`__proto__,__v_isRef,__isVue`);
	var builtInSymbols = new Set(Object.getOwnPropertyNames(Symbol).filter((key) => key !== "arguments" && key !== "caller").map((key) => Symbol[key]).filter(isSymbol));
	function hasOwnProperty(key) {
		if (!isSymbol(key)) key = String(key);
		const obj = toRaw(this);
		track(obj, "has", key);
		return obj.hasOwnProperty(key);
	}
	var BaseReactiveHandler = class {
		constructor(_isReadonly = false, _isShallow = false) {
			this._isReadonly = _isReadonly;
			this._isShallow = _isShallow;
		}
		get(target, key, receiver) {
			if (key === "__v_skip") return target["__v_skip"];
			const isReadonly2 = this._isReadonly, isShallow2 = this._isShallow;
			if (key === "__v_isReactive") return !isReadonly2;
			else if (key === "__v_isReadonly") return isReadonly2;
			else if (key === "__v_isShallow") return isShallow2;
			else if (key === "__v_raw") {
				if (receiver === (isReadonly2 ? isShallow2 ? shallowReadonlyMap : readonlyMap : isShallow2 ? shallowReactiveMap : reactiveMap).get(target) || Object.getPrototypeOf(target) === Object.getPrototypeOf(receiver)) return target;
				return;
			}
			const targetIsArray = isArray(target);
			if (!isReadonly2) {
				let fn;
				if (targetIsArray && (fn = arrayInstrumentations[key])) return fn;
				if (key === "hasOwnProperty") return hasOwnProperty;
			}
			const res = Reflect.get(target, key, isRef(target) ? target : receiver);
			if (isSymbol(key) ? builtInSymbols.has(key) : isNonTrackableKeys(key)) return res;
			if (!isReadonly2) track(target, "get", key);
			if (isShallow2) return res;
			if (isRef(res)) {
				const value = targetIsArray && isIntegerKey(key) ? res : res.value;
				return isReadonly2 && isObject(value) ? readonly(value) : value;
			}
			if (isObject(res)) return isReadonly2 ? readonly(res) : reactive(res);
			return res;
		}
	};
	var MutableReactiveHandler = class extends BaseReactiveHandler {
		constructor(isShallow2 = false) {
			super(false, isShallow2);
		}
		set(target, key, value, receiver) {
			let oldValue = target[key];
			const isArrayWithIntegerKey = isArray(target) && isIntegerKey(key);
			if (!this._isShallow) {
				const isOldValueReadonly = isReadonly(oldValue);
				if (!isShallow(value) && !isReadonly(value)) {
					oldValue = toRaw(oldValue);
					value = toRaw(value);
				}
				if (!isArrayWithIntegerKey && isRef(oldValue) && !isRef(value)) {
					if (isOldValueReadonly) return true;
					else {
						oldValue.value = value;
						return true;
					}
				}
			}
			const hadKey = isArrayWithIntegerKey ? Number(key) < target.length : hasOwn(target, key);
			const result = Reflect.set(target, key, value, isRef(target) ? target : receiver);
			if (target === toRaw(receiver) && result) {
				if (!hadKey) trigger(target, "add", key, value);
				else if (hasChanged(value, oldValue)) trigger(target, "set", key, value, oldValue);
			}
			return result;
		}
		deleteProperty(target, key) {
			const hadKey = hasOwn(target, key);
			const oldValue = target[key];
			const result = Reflect.deleteProperty(target, key);
			if (result && hadKey) trigger(target, "delete", key, void 0, oldValue);
			return result;
		}
		has(target, key) {
			const result = Reflect.has(target, key);
			if (!isSymbol(key) || !builtInSymbols.has(key)) track(target, "has", key);
			return result;
		}
		ownKeys(target) {
			track(target, "iterate", isArray(target) ? "length" : ITERATE_KEY);
			return Reflect.ownKeys(target);
		}
	};
	var ReadonlyReactiveHandler = class extends BaseReactiveHandler {
		constructor(isShallow2 = false) {
			super(true, isShallow2);
		}
		set(target, key) {
			return true;
		}
		deleteProperty(target, key) {
			return true;
		}
	};
	var mutableHandlers = new MutableReactiveHandler();
	var readonlyHandlers = new ReadonlyReactiveHandler();
	var shallowReactiveHandlers = new MutableReactiveHandler(true);
	var toShallow = (value) => value;
	var getProto = (v) => Reflect.getPrototypeOf(v);
	function createIterableMethod(method, isReadonly2, isShallow2) {
		return function(...args) {
			const target = this["__v_raw"];
			const rawTarget = toRaw(target);
			const targetIsMap = isMap(rawTarget);
			const isPair = method === "entries" || method === Symbol.iterator && targetIsMap;
			const isKeyOnly = method === "keys" && targetIsMap;
			const innerIterator = target[method](...args);
			const wrap = isShallow2 ? toShallow : isReadonly2 ? toReadonly : toReactive;
			!isReadonly2 && track(rawTarget, "iterate", isKeyOnly ? MAP_KEY_ITERATE_KEY : ITERATE_KEY);
			return extend(Object.create(innerIterator), { next() {
				const { value, done } = innerIterator.next();
				return done ? {
					value,
					done
				} : {
					value: isPair ? [wrap(value[0]), wrap(value[1])] : wrap(value),
					done
				};
			} });
		};
	}
	function createReadonlyMethod(type) {
		return function(...args) {
			return type === "delete" ? false : type === "clear" ? void 0 : this;
		};
	}
	function createInstrumentations(readonly, shallow) {
		const instrumentations = {
			get(key) {
				const target = this["__v_raw"];
				const rawTarget = toRaw(target);
				const rawKey = toRaw(key);
				if (!readonly) {
					if (hasChanged(key, rawKey)) track(rawTarget, "get", key);
					track(rawTarget, "get", rawKey);
				}
				const { has } = getProto(rawTarget);
				const wrap = shallow ? toShallow : readonly ? toReadonly : toReactive;
				if (has.call(rawTarget, key)) return wrap(target.get(key));
				else if (has.call(rawTarget, rawKey)) return wrap(target.get(rawKey));
				else if (target !== rawTarget) target.get(key);
			},
			get size() {
				const target = this["__v_raw"];
				!readonly && track(toRaw(target), "iterate", ITERATE_KEY);
				return target.size;
			},
			has(key) {
				const target = this["__v_raw"];
				const rawTarget = toRaw(target);
				const rawKey = toRaw(key);
				if (!readonly) {
					if (hasChanged(key, rawKey)) track(rawTarget, "has", key);
					track(rawTarget, "has", rawKey);
				}
				return key === rawKey ? target.has(key) : target.has(key) || target.has(rawKey);
			},
			forEach(callback, thisArg) {
				const observed = this;
				const target = observed["__v_raw"];
				const rawTarget = toRaw(target);
				const wrap = shallow ? toShallow : readonly ? toReadonly : toReactive;
				!readonly && track(rawTarget, "iterate", ITERATE_KEY);
				return target.forEach((value, key) => {
					return callback.call(thisArg, wrap(value), wrap(key), observed);
				});
			}
		};
		extend(instrumentations, readonly ? {
			add: createReadonlyMethod("add"),
			set: createReadonlyMethod("set"),
			delete: createReadonlyMethod("delete"),
			clear: createReadonlyMethod("clear")
		} : {
			add(value) {
				const target = toRaw(this);
				const proto = getProto(target);
				const rawValue = toRaw(value);
				const valueToAdd = !shallow && !isShallow(value) && !isReadonly(value) ? rawValue : value;
				if (!(proto.has.call(target, valueToAdd) || hasChanged(value, valueToAdd) && proto.has.call(target, value) || hasChanged(rawValue, valueToAdd) && proto.has.call(target, rawValue))) {
					target.add(valueToAdd);
					trigger(target, "add", valueToAdd, valueToAdd);
				}
				return this;
			},
			set(key, value) {
				if (!shallow && !isShallow(value) && !isReadonly(value)) value = toRaw(value);
				const target = toRaw(this);
				const { has, get } = getProto(target);
				let hadKey = has.call(target, key);
				if (!hadKey) {
					key = toRaw(key);
					hadKey = has.call(target, key);
				}
				const oldValue = get.call(target, key);
				target.set(key, value);
				if (!hadKey) trigger(target, "add", key, value);
				else if (hasChanged(value, oldValue)) trigger(target, "set", key, value, oldValue);
				return this;
			},
			delete(key) {
				const target = toRaw(this);
				const { has, get } = getProto(target);
				let hadKey = has.call(target, key);
				if (!hadKey) {
					key = toRaw(key);
					hadKey = has.call(target, key);
				}
				const oldValue = get ? get.call(target, key) : void 0;
				const result = target.delete(key);
				if (hadKey) trigger(target, "delete", key, void 0, oldValue);
				return result;
			},
			clear() {
				const target = toRaw(this);
				const hadItems = target.size !== 0;
				const oldTarget = void 0;
				const result = target.clear();
				if (hadItems) trigger(target, "clear", void 0, void 0, oldTarget);
				return result;
			}
		});
		[
			"keys",
			"values",
			"entries",
			Symbol.iterator
		].forEach((method) => {
			instrumentations[method] = createIterableMethod(method, readonly, shallow);
		});
		return instrumentations;
	}
	function createInstrumentationGetter(isReadonly2, shallow) {
		const instrumentations = createInstrumentations(isReadonly2, shallow);
		return (target, key, receiver) => {
			if (key === "__v_isReactive") return !isReadonly2;
			else if (key === "__v_isReadonly") return isReadonly2;
			else if (key === "__v_raw") return target;
			return Reflect.get(hasOwn(instrumentations, key) && key in target ? instrumentations : target, key, receiver);
		};
	}
	var mutableCollectionHandlers = { get: createInstrumentationGetter(false, false) };
	var shallowCollectionHandlers = { get: createInstrumentationGetter(false, true) };
	var readonlyCollectionHandlers = { get: createInstrumentationGetter(true, false) };
	var reactiveMap = new WeakMap();
	var shallowReactiveMap = new WeakMap();
	var readonlyMap = new WeakMap();
	var shallowReadonlyMap = new WeakMap();
	function targetTypeMap(rawType) {
		switch (rawType) {
			case "Object":
			case "Array": return 1;
			case "Map":
			case "Set":
			case "WeakMap":
			case "WeakSet": return 2;
			default: return 0;
		}
	}
	function reactive(target) {
		if (isReadonly(target)) return target;
		return createReactiveObject(target, false, mutableHandlers, mutableCollectionHandlers, reactiveMap);
	}
	function shallowReactive(target) {
		return createReactiveObject(target, false, shallowReactiveHandlers, shallowCollectionHandlers, shallowReactiveMap);
	}
	function readonly(target) {
		return createReactiveObject(target, true, readonlyHandlers, readonlyCollectionHandlers, readonlyMap);
	}
	function createReactiveObject(target, isReadonly2, baseHandlers, collectionHandlers, proxyMap) {
		if (!isObject(target)) return target;
		if (target["__v_raw"] && !(isReadonly2 && target["__v_isReactive"])) return target;
		if (target["__v_skip"] || !Object.isExtensible(target)) return target;
		const existingProxy = proxyMap.get(target);
		if (existingProxy) return existingProxy;
		const targetType = targetTypeMap(toRawType(target));
		if (targetType === 0) return target;
		const proxy = new Proxy(target, targetType === 2 ? collectionHandlers : baseHandlers);
		proxyMap.set(target, proxy);
		return proxy;
	}
	function isReactive(value) {
		if (isReadonly(value)) return isReactive(value["__v_raw"]);
		return !!(value && value["__v_isReactive"]);
	}
	function isReadonly(value) {
		return !!(value && value["__v_isReadonly"]);
	}
	function isShallow(value) {
		return !!(value && value["__v_isShallow"]);
	}
	function isProxy(value) {
		return value ? !!value["__v_raw"] : false;
	}
	function toRaw(observed) {
		const raw = observed && observed["__v_raw"];
		return raw ? toRaw(raw) : observed;
	}
	function markRaw(value) {
		if (!hasOwn(value, "__v_skip") && Object.isExtensible(value)) def(value, "__v_skip", true);
		return value;
	}
	var toReactive = (value) => isObject(value) ? reactive(value) : value;
	var toReadonly = (value) => isObject(value) ? readonly(value) : value;
	function isRef(r) {
		return r ? r["__v_isRef"] === true : false;
	}
	function unref(ref2) {
		return isRef(ref2) ? ref2.value : ref2;
	}
	var shallowUnwrapHandlers = {
		get: (target, key, receiver) => key === "__v_raw" ? target : unref(Reflect.get(target, key, receiver)),
		set: (target, key, value, receiver) => {
			const oldValue = target[key];
			if (isRef(oldValue) && !isRef(value)) {
				oldValue.value = value;
				return true;
			} else return Reflect.set(target, key, value, receiver);
		}
	};
	function proxyRefs(objectWithRefs) {
		return isReactive(objectWithRefs) ? objectWithRefs : new Proxy(objectWithRefs, shallowUnwrapHandlers);
	}
	var ComputedRefImpl = class {
		constructor(fn, setter, isSSR) {
			this.fn = fn;
			this.setter = setter;
			this._value = void 0;
			this.dep = new Dep(this);
			this.__v_isRef = true;
			this.deps = void 0;
			this.depsTail = void 0;
			this.flags = 16;
			this.globalVersion = globalVersion - 1;
			this.next = void 0;
			this.effect = this;
			this["__v_isReadonly"] = !setter;
			this.isSSR = isSSR;
		}
		notify() {
			this.flags |= 16;
			if (!(this.flags & 8) && activeSub !== this) {
				batch(this, true);
				return true;
			}
		}
		get value() {
			const link = this.dep.track();
			refreshComputed(this);
			if (link) link.version = this.dep.version;
			return this._value;
		}
		set value(newValue) {
			if (this.setter) this.setter(newValue);
		}
	};
	function computed$1(getterOrOptions, debugOptions, isSSR = false) {
		let getter;
		let setter;
		if (isFunction(getterOrOptions)) getter = getterOrOptions;
		else {
			getter = getterOrOptions.get;
			setter = getterOrOptions.set;
		}
		return new ComputedRefImpl(getter, setter, isSSR);
	}
	var INITIAL_WATCHER_VALUE = {};
	var cleanupMap = new WeakMap();
	var activeWatcher = void 0;
	function onWatcherCleanup(cleanupFn, failSilently = false, owner = activeWatcher) {
		if (owner) {
			let cleanups = cleanupMap.get(owner);
			if (!cleanups) cleanupMap.set(owner, cleanups = []);
			cleanups.push(cleanupFn);
		}
	}
	function watch$1(source, cb, options = EMPTY_OBJ) {
		const { immediate, deep, once, scheduler, augmentJob, call } = options;
		const reactiveGetter = (source2) => {
			if (deep) return source2;
			if (isShallow(source2) || deep === false || deep === 0) return traverse(source2, 1);
			return traverse(source2);
		};
		let effect;
		let getter;
		let cleanup;
		let boundCleanup;
		let forceTrigger = false;
		let isMultiSource = false;
		if (isRef(source)) {
			getter = () => source.value;
			forceTrigger = isShallow(source);
		} else if (isReactive(source)) {
			getter = () => reactiveGetter(source);
			forceTrigger = true;
		} else if (isArray(source)) {
			isMultiSource = true;
			forceTrigger = source.some((s) => isReactive(s) || isShallow(s));
			getter = () => source.map((s) => {
				if (isRef(s)) return s.value;
				else if (isReactive(s)) return reactiveGetter(s);
				else if (isFunction(s)) return call ? call(s, 2) : s();
			});
		} else if (isFunction(source)) {
			if (cb) getter = call ? () => call(source, 2) : source;
			else getter = () => {
				if (cleanup) {
					pauseTracking();
					try {
						cleanup();
					} finally {
						resetTracking();
					}
				}
				const currentEffect = activeWatcher;
				activeWatcher = effect;
				try {
					return call ? call(source, 3, [boundCleanup]) : source(boundCleanup);
				} finally {
					activeWatcher = currentEffect;
				}
			};
		} else getter = NOOP;
		if (cb && deep) {
			const baseGetter = getter;
			const depth = deep === true ? Infinity : deep;
			getter = () => traverse(baseGetter(), depth);
		}
		const scope = getCurrentScope();
		const watchHandle = () => {
			effect.stop();
			if (scope && scope.active) remove(scope.effects, effect);
		};
		if (once && cb) {
			const _cb = cb;
			cb = (...args) => {
				const res = _cb(...args);
				watchHandle();
				return res;
			};
		}
		let oldValue = isMultiSource ? new Array(source.length).fill(INITIAL_WATCHER_VALUE) : INITIAL_WATCHER_VALUE;
		const job = (immediateFirstRun) => {
			if (!(effect.flags & 1) || !effect.dirty && !immediateFirstRun) return;
			if (cb) {
				const newValue = effect.run();
				if (immediateFirstRun || deep || forceTrigger || (isMultiSource ? newValue.some((v, i) => hasChanged(v, oldValue[i])) : hasChanged(newValue, oldValue))) {
					if (cleanup) cleanup();
					const currentWatcher = activeWatcher;
					activeWatcher = effect;
					try {
						const args = [
							newValue,
							oldValue === INITIAL_WATCHER_VALUE ? void 0 : isMultiSource && oldValue[0] === INITIAL_WATCHER_VALUE ? [] : oldValue,
							boundCleanup
						];
						oldValue = newValue;
						call ? call(cb, 3, args) : cb(...args);
					} finally {
						activeWatcher = currentWatcher;
					}
				}
			} else effect.run();
		};
		if (augmentJob) augmentJob(job);
		effect = new ReactiveEffect(getter);
		effect.scheduler = scheduler ? () => scheduler(job, false) : job;
		boundCleanup = (fn) => onWatcherCleanup(fn, false, effect);
		cleanup = effect.onStop = () => {
			const cleanups = cleanupMap.get(effect);
			if (cleanups) {
				if (call) call(cleanups, 4);
				else for (const cleanup2 of cleanups) cleanup2();
				cleanupMap.delete(effect);
			}
		};
		if (cb) {
			if (immediate) job(true);
			else oldValue = effect.run();
		} else if (scheduler) scheduler(job.bind(null, true), true);
		else effect.run();
		watchHandle.pause = effect.pause.bind(effect);
		watchHandle.resume = effect.resume.bind(effect);
		watchHandle.stop = watchHandle;
		return watchHandle;
	}
	function traverse(value, depth = Infinity, seen) {
		if (depth <= 0 || !isObject(value) || value["__v_skip"]) return value;
		seen = seen || new Map();
		if ((seen.get(value) || 0) >= depth) return value;
		seen.set(value, depth);
		depth--;
		if (isRef(value)) traverse(value.value, depth, seen);
		else if (isArray(value)) for (let i = 0; i < value.length; i++) traverse(value[i], depth, seen);
		else if (isSet(value) || isMap(value)) value.forEach((v) => {
			traverse(v, depth, seen);
		});
		else if (isPlainObject(value)) {
			for (const key in value) traverse(value[key], depth, seen);
			for (const key of Object.getOwnPropertySymbols(value)) if (Object.prototype.propertyIsEnumerable.call(value, key)) traverse(value[key], depth, seen);
		}
		return value;
	}
	//#endregion
	//#region node_modules/@vue/runtime-core/dist/runtime-core.esm-bundler.js
	function callWithErrorHandling(fn, instance, type, args) {
		try {
			return args ? fn(...args) : fn();
		} catch (err) {
			handleError(err, instance, type);
		}
	}
	function callWithAsyncErrorHandling(fn, instance, type, args) {
		if (isFunction(fn)) {
			const res = callWithErrorHandling(fn, instance, type, args);
			if (res && isPromise(res)) res.catch((err) => {
				handleError(err, instance, type);
			});
			return res;
		}
		if (isArray(fn)) {
			const values = [];
			for (let i = 0; i < fn.length; i++) values.push(callWithAsyncErrorHandling(fn[i], instance, type, args));
			return values;
		}
	}
	function handleError(err, instance, type, throwInDev = true) {
		const contextVNode = instance ? instance.vnode : null;
		const { errorHandler, throwUnhandledErrorInProduction } = instance && instance.appContext.config || EMPTY_OBJ;
		if (instance) {
			let cur = instance.parent;
			const exposedInstance = instance.proxy;
			const errorInfo = `https://vuejs.org/error-reference/#runtime-${type}`;
			while (cur) {
				const errorCapturedHooks = cur.ec;
				if (errorCapturedHooks) {
					for (let i = 0; i < errorCapturedHooks.length; i++) if (errorCapturedHooks[i](err, exposedInstance, errorInfo) === false) return;
				}
				cur = cur.parent;
			}
			if (errorHandler) {
				pauseTracking();
				callWithErrorHandling(errorHandler, null, 10, [
					err,
					exposedInstance,
					errorInfo
				]);
				resetTracking();
				return;
			}
		}
		logError(err, type, contextVNode, throwInDev, throwUnhandledErrorInProduction);
	}
	function logError(err, type, contextVNode, throwInDev = true, throwInProd = false) {
		if (throwInProd) throw err;
		else console.error(err);
	}
	var queue = [];
	var flushIndex = -1;
	var pendingPostFlushCbs = [];
	var activePostFlushCbs = null;
	var postFlushIndex = 0;
	var resolvedPromise = Promise.resolve();
	var currentFlushPromise = null;
	function nextTick(fn) {
		const p = currentFlushPromise || resolvedPromise;
		return fn ? p.then(this ? fn.bind(this) : fn) : p;
	}
	function findInsertionIndex(id) {
		let start = flushIndex + 1;
		let end = queue.length;
		while (start < end) {
			const middle = start + end >>> 1;
			const middleJob = queue[middle];
			const middleJobId = getId(middleJob);
			if (middleJobId < id || middleJobId === id && middleJob.flags & 2) start = middle + 1;
			else end = middle;
		}
		return start;
	}
	function queueJob(job) {
		if (!(job.flags & 1)) {
			const jobId = getId(job);
			const lastJob = queue[queue.length - 1];
			if (!lastJob || !(job.flags & 2) && jobId >= getId(lastJob)) queue.push(job);
			else queue.splice(findInsertionIndex(jobId), 0, job);
			job.flags |= 1;
			queueFlush();
		}
	}
	function queueFlush() {
		if (!currentFlushPromise) currentFlushPromise = resolvedPromise.then(flushJobs);
	}
	function queuePostFlushCb(cb) {
		if (!isArray(cb)) {
			if (activePostFlushCbs && cb.id === -1) activePostFlushCbs.splice(postFlushIndex + 1, 0, cb);
			else if (!(cb.flags & 1)) {
				pendingPostFlushCbs.push(cb);
				cb.flags |= 1;
			}
		} else for (let i = 0; i < cb.length; i++) pendingPostFlushCbs.push(cb[i]);
		queueFlush();
	}
	function flushPreFlushCbs(instance, seen, i = flushIndex + 1) {
		for (; i < queue.length; i++) {
			const cb = queue[i];
			if (cb && cb.flags & 2) {
				if (instance && cb.id !== instance.uid) continue;
				queue.splice(i, 1);
				i--;
				if (cb.flags & 4) cb.flags &= -2;
				cb();
				if (!(cb.flags & 4)) cb.flags &= -2;
			}
		}
	}
	function flushPostFlushCbs(seen) {
		if (pendingPostFlushCbs.length) {
			const deduped = [...new Set(pendingPostFlushCbs)].sort((a, b) => getId(a) - getId(b));
			pendingPostFlushCbs.length = 0;
			if (activePostFlushCbs) {
				for (let i = 0; i < deduped.length; i++) activePostFlushCbs.push(deduped[i]);
				return;
			}
			activePostFlushCbs = deduped;
			for (postFlushIndex = 0; postFlushIndex < activePostFlushCbs.length; postFlushIndex++) {
				const cb = activePostFlushCbs[postFlushIndex];
				if (cb.flags & 4) cb.flags &= -2;
				if (!(cb.flags & 8)) cb();
				cb.flags &= -2;
			}
			activePostFlushCbs = null;
			postFlushIndex = 0;
		}
	}
	var getId = (job) => job.id == null ? job.flags & 2 ? -1 : Infinity : job.id;
	function flushJobs(seen) {
		try {
			for (flushIndex = 0; flushIndex < queue.length; flushIndex++) {
				const job = queue[flushIndex];
				if (job && !(job.flags & 8)) {
					if (job.flags & 4) job.flags &= -2;
					callWithErrorHandling(job, job.i, job.i ? 15 : 14);
					if (!(job.flags & 4)) job.flags &= -2;
				}
			}
		} finally {
			for (; flushIndex < queue.length; flushIndex++) {
				const job = queue[flushIndex];
				if (job) job.flags &= -2;
			}
			flushIndex = -1;
			queue.length = 0;
			flushPostFlushCbs(seen);
			currentFlushPromise = null;
			if (queue.length || pendingPostFlushCbs.length) flushJobs(seen);
		}
	}
	var currentRenderingInstance = null;
	var currentScopeId = null;
	function setCurrentRenderingInstance(instance) {
		const prev = currentRenderingInstance;
		currentRenderingInstance = instance;
		currentScopeId = instance && instance.type.__scopeId || null;
		return prev;
	}
	function withCtx(fn, ctx = currentRenderingInstance, isNonScopedSlot) {
		if (!ctx) return fn;
		if (fn._n) return fn;
		const renderFnWithContext = (...args) => {
			if (renderFnWithContext._d) setBlockTracking(-1);
			const prevInstance = setCurrentRenderingInstance(ctx);
			const prevStackSize = blockStack.length;
			let res;
			try {
				res = fn(...args);
			} finally {
				for (let i = blockStack.length; i > prevStackSize; i--) closeBlock();
				setCurrentRenderingInstance(prevInstance);
				if (renderFnWithContext._d) setBlockTracking(1);
			}
			return res;
		};
		renderFnWithContext._n = true;
		renderFnWithContext._c = true;
		renderFnWithContext._d = true;
		return renderFnWithContext;
	}
	function withDirectives(vnode, directives) {
		if (currentRenderingInstance === null) return vnode;
		const instance = getComponentPublicInstance(currentRenderingInstance);
		const bindings = vnode.dirs || (vnode.dirs = []);
		for (let i = 0; i < directives.length; i++) {
			let [dir, value, arg, modifiers = EMPTY_OBJ] = directives[i];
			if (dir) {
				if (isFunction(dir)) dir = {
					mounted: dir,
					updated: dir
				};
				if (dir.deep) traverse(value);
				bindings.push({
					dir,
					instance,
					value,
					oldValue: void 0,
					arg,
					modifiers
				});
			}
		}
		return vnode;
	}
	function invokeDirectiveHook(vnode, prevVNode, instance, name) {
		const bindings = vnode.dirs;
		const oldBindings = prevVNode && prevVNode.dirs;
		for (let i = 0; i < bindings.length; i++) {
			const binding = bindings[i];
			if (oldBindings) binding.oldValue = oldBindings[i].value;
			let hook = binding.dir[name];
			if (hook) {
				pauseTracking();
				callWithAsyncErrorHandling(hook, instance, 8, [
					vnode.el,
					binding,
					vnode,
					prevVNode
				]);
				resetTracking();
			}
		}
	}
	function provide(key, value) {
		if (currentInstance) {
			let provides = currentInstance.provides;
			const parentProvides = currentInstance.parent && currentInstance.parent.provides;
			if (parentProvides === provides) provides = currentInstance.provides = Object.create(parentProvides);
			provides[key] = value;
		}
	}
	function inject(key, defaultValue, treatDefaultAsFactory = false) {
		const instance = getCurrentInstance();
		if (instance || currentApp) {
			let provides = currentApp ? currentApp._context.provides : instance ? instance.parent == null || instance.ce ? instance.vnode.appContext && instance.vnode.appContext.provides : instance.parent.provides : void 0;
			if (provides && key in provides) return provides[key];
			else if (arguments.length > 1) return treatDefaultAsFactory && isFunction(defaultValue) ? defaultValue.call(instance && instance.proxy) : defaultValue;
		}
	}
	var ssrContextKey = Symbol.for("v-scx");
	var useSSRContext = () => {
		{
			const ctx = inject(ssrContextKey);
			if (!ctx) {}
			return ctx;
		}
	};
	function watch(source, cb, options) {
		return doWatch(source, cb, options);
	}
	function doWatch(source, cb, options = EMPTY_OBJ) {
		const { immediate, deep, flush, once } = options;
		const baseWatchOptions = extend({}, options);
		const runsImmediately = cb && immediate || !cb && flush !== "post";
		let ssrCleanup;
		if (isInSSRComponentSetup) {
			if (flush === "sync") {
				const ctx = useSSRContext();
				ssrCleanup = ctx.__watcherHandles || (ctx.__watcherHandles = []);
			} else if (!runsImmediately) {
				const watchStopHandle = () => {};
				watchStopHandle.stop = NOOP;
				watchStopHandle.resume = NOOP;
				watchStopHandle.pause = NOOP;
				return watchStopHandle;
			}
		}
		const instance = currentInstance;
		baseWatchOptions.call = (fn, type, args) => callWithAsyncErrorHandling(fn, instance, type, args);
		let isPre = false;
		if (flush === "post") baseWatchOptions.scheduler = (job) => {
			queuePostRenderEffect(job, instance && instance.suspense);
		};
		else if (flush !== "sync") {
			isPre = true;
			baseWatchOptions.scheduler = (job, isFirstRun) => {
				if (isFirstRun) job();
				else queueJob(job);
			};
		}
		baseWatchOptions.augmentJob = (job) => {
			if (cb) job.flags |= 4;
			if (isPre) {
				job.flags |= 2;
				if (instance) {
					job.id = instance.uid;
					job.i = instance;
				}
			}
		};
		const watchHandle = watch$1(source, cb, baseWatchOptions);
		if (isInSSRComponentSetup) {
			if (ssrCleanup) ssrCleanup.push(watchHandle);
			else if (runsImmediately) watchHandle();
		}
		return watchHandle;
	}
	function instanceWatch(source, value, options) {
		const publicThis = this.proxy;
		const getter = isString(source) ? source.includes(".") ? createPathGetter(publicThis, source) : () => publicThis[source] : source.bind(publicThis, publicThis);
		let cb;
		if (isFunction(value)) cb = value;
		else {
			cb = value.handler;
			options = value;
		}
		const reset = setCurrentInstance(this);
		const res = doWatch(getter, cb.bind(publicThis), options);
		reset();
		return res;
	}
	function createPathGetter(ctx, path) {
		const segments = path.split(".");
		return () => {
			let cur = ctx;
			for (let i = 0; i < segments.length && cur; i++) cur = cur[segments[i]];
			return cur;
		};
	}
	var TeleportEndKey = Symbol("_vte");
	var isTeleport = (type) => type.__isTeleport;
	var leaveCbKey = Symbol("_leaveCb");
	function findNonCommentChild(children) {
		let child = children[0];
		if (children.length > 1) {
			for (const c of children) if (c.type !== Comment) {
				child = c;
				break;
			}
		}
		return child;
	}
	function getInnerChild$1(vnode) {
		if (!isKeepAlive(vnode)) {
			if (isTeleport(vnode.type) && vnode.children) return findNonCommentChild(vnode.children);
			return vnode;
		}
		if (vnode.component) return vnode.component.subTree;
		const { shapeFlag, children } = vnode;
		if (children) {
			if (shapeFlag & 16) return children[0];
			if (shapeFlag & 32 && isFunction(children.default)) return children.default();
		}
	}
	function setTransitionHooks(vnode, hooks) {
		if (vnode.shapeFlag & 6 && vnode.component) {
			vnode.transition = hooks;
			const subTree = vnode.component.subTree;
			setTransitionHooks(isTeleport(subTree.type) ? getInnerChild$1(subTree) || subTree : subTree, hooks);
		} else if (vnode.shapeFlag & 128) {
			vnode.ssContent.transition = hooks.clone(vnode.ssContent);
			vnode.ssFallback.transition = hooks.clone(vnode.ssFallback);
		} else vnode.transition = hooks;
	}
	function markAsyncBoundary(instance) {
		instance.ids = [
			instance.ids[0] + instance.ids[2]++ + "-",
			0,
			0
		];
	}
	function isTemplateRefKey(refs, key) {
		let desc;
		return !!((desc = Object.getOwnPropertyDescriptor(refs, key)) && !desc.configurable);
	}
	var pendingSetRefMap = new WeakMap();
	function setRef(rawRef, oldRawRef, parentSuspense, vnode, isUnmount = false) {
		if (isArray(rawRef)) {
			rawRef.forEach((r, i) => setRef(r, oldRawRef && (isArray(oldRawRef) ? oldRawRef[i] : oldRawRef), parentSuspense, vnode, isUnmount));
			return;
		}
		if (isAsyncWrapper(vnode) && !isUnmount) {
			if (vnode.shapeFlag & 512 && vnode.type.__asyncResolved && vnode.component.subTree.component) setRef(rawRef, oldRawRef, parentSuspense, vnode.component.subTree);
			return;
		}
		const refValue = vnode.shapeFlag & 4 ? getComponentPublicInstance(vnode.component) : vnode.el;
		const value = isUnmount ? null : refValue;
		const { i: owner, r: ref } = rawRef;
		const oldRef = oldRawRef && oldRawRef.r;
		const refs = owner.refs === EMPTY_OBJ ? owner.refs = {} : owner.refs;
		const setupState = owner.setupState;
		const rawSetupState = toRaw(setupState);
		const canSetSetupRef = setupState === EMPTY_OBJ ? NO : (key) => {
			if (isTemplateRefKey(refs, key)) return false;
			return hasOwn(rawSetupState, key);
		};
		const canSetRef = (ref2, key) => {
			if (key && isTemplateRefKey(refs, key)) return false;
			return true;
		};
		if (oldRef != null && oldRef !== ref) {
			invalidatePendingSetRef(oldRawRef);
			if (isString(oldRef)) {
				refs[oldRef] = null;
				if (canSetSetupRef(oldRef)) setupState[oldRef] = null;
			} else if (isRef(oldRef)) {
				const oldRawRefAtom = oldRawRef;
				if (canSetRef(oldRef, oldRawRefAtom.k)) oldRef.value = null;
				if (oldRawRefAtom.k) refs[oldRawRefAtom.k] = null;
			}
		}
		if (isFunction(ref)) callWithErrorHandling(ref, owner, 12, [value, refs]);
		else {
			const _isString = isString(ref);
			const _isRef = isRef(ref);
			if (_isString || _isRef) {
				const doSet = () => {
					if (rawRef.f) {
						const existing = _isString ? canSetSetupRef(ref) ? setupState[ref] : refs[ref] : canSetRef(ref) || !rawRef.k ? ref.value : refs[rawRef.k];
						if (isUnmount) isArray(existing) && remove(existing, refValue);
						else if (!isArray(existing)) {
							if (_isString) {
								refs[ref] = [refValue];
								if (canSetSetupRef(ref)) setupState[ref] = refs[ref];
							} else {
								const newVal = [refValue];
								if (canSetRef(ref, rawRef.k)) ref.value = newVal;
								if (rawRef.k) refs[rawRef.k] = newVal;
							}
						} else if (!existing.includes(refValue)) existing.push(refValue);
					} else if (_isString) {
						refs[ref] = value;
						if (canSetSetupRef(ref)) setupState[ref] = value;
					} else if (_isRef) {
						if (canSetRef(ref, rawRef.k)) ref.value = value;
						if (rawRef.k) refs[rawRef.k] = value;
					}
				};
				if (value) {
					const job = () => {
						doSet();
						pendingSetRefMap.delete(rawRef);
					};
					job.id = -1;
					pendingSetRefMap.set(rawRef, job);
					queuePostRenderEffect(job, parentSuspense);
				} else {
					invalidatePendingSetRef(rawRef);
					doSet();
				}
			}
		}
	}
	function invalidatePendingSetRef(rawRef) {
		const pendingSetRef = pendingSetRefMap.get(rawRef);
		if (pendingSetRef) {
			pendingSetRef.flags |= 8;
			pendingSetRefMap.delete(rawRef);
		}
	}
	var requestIdleCallback = getGlobalThis().requestIdleCallback || ((cb) => setTimeout(cb, 1));
	var cancelIdleCallback = getGlobalThis().cancelIdleCallback || ((id) => clearTimeout(id));
	var isAsyncWrapper = (i) => !!i.type.__asyncLoader;
	var isKeepAlive = (vnode) => vnode.type.__isKeepAlive;
	function onActivated(hook, target) {
		registerKeepAliveHook(hook, "a", target);
	}
	function onDeactivated(hook, target) {
		registerKeepAliveHook(hook, "da", target);
	}
	function registerKeepAliveHook(hook, type, target = currentInstance) {
		const wrappedHook = hook.__wdc || (hook.__wdc = () => {
			let current = target;
			while (current) {
				if (current.isDeactivated) return;
				current = current.parent;
			}
			return hook();
		});
		injectHook(type, wrappedHook, target);
		if (target) {
			let current = target.parent;
			while (current && current.parent) {
				if (isKeepAlive(current.parent.vnode)) injectToKeepAliveRoot(wrappedHook, type, target, current);
				current = current.parent;
			}
		}
	}
	function injectToKeepAliveRoot(hook, type, target, keepAliveRoot) {
		const injected = injectHook(type, hook, keepAliveRoot, true);
		onUnmounted(() => {
			remove(keepAliveRoot[type], injected);
		}, target);
	}
	function injectHook(type, hook, target = currentInstance, prepend = false) {
		if (target) {
			const hooks = target[type] || (target[type] = []);
			const wrappedHook = hook.__weh || (hook.__weh = (...args) => {
				pauseTracking();
				const reset = setCurrentInstance(target);
				const res = callWithAsyncErrorHandling(hook, target, type, args);
				reset();
				resetTracking();
				return res;
			});
			if (prepend) hooks.unshift(wrappedHook);
			else hooks.push(wrappedHook);
			return wrappedHook;
		}
	}
	var createHook = (lifecycle) => (hook, target = currentInstance) => {
		if (!isInSSRComponentSetup || lifecycle === "sp") injectHook(lifecycle, (...args) => hook(...args), target);
	};
	var onBeforeMount = createHook("bm");
	var onMounted = createHook("m");
	var onBeforeUpdate = createHook("bu");
	var onUpdated = createHook("u");
	var onBeforeUnmount = createHook("bum");
	var onUnmounted = createHook("um");
	var onServerPrefetch = createHook("sp");
	var onRenderTriggered = createHook("rtg");
	var onRenderTracked = createHook("rtc");
	function onErrorCaptured(hook, target = currentInstance) {
		injectHook("ec", hook, target);
	}
	var COMPONENTS = "components";
	function resolveComponent(name, maybeSelfReference) {
		return resolveAsset(COMPONENTS, name, true, maybeSelfReference) || name;
	}
	var NULL_DYNAMIC_COMPONENT = Symbol.for("v-ndc");
	function resolveAsset(type, name, warnMissing = true, maybeSelfReference = false) {
		const instance = currentRenderingInstance || currentInstance;
		if (instance) {
			const Component = instance.type;
			if (type === COMPONENTS) {
				const selfName = getComponentName(Component, false);
				if (selfName && (selfName === name || selfName === camelize(name) || selfName === capitalize(camelize(name)))) return Component;
			}
			const res = resolve(instance[type] || Component[type], name) || resolve(instance.appContext[type], name);
			if (!res && maybeSelfReference) return Component;
			return res;
		}
	}
	function resolve(registry, name) {
		return registry && (registry[name] || registry[camelize(name)] || registry[capitalize(camelize(name))]);
	}
	function renderList(source, renderItem, cache, index) {
		let ret;
		const cached = cache && cache[index];
		const sourceIsArray = isArray(source);
		if (sourceIsArray || isString(source)) {
			const sourceIsReactiveArray = sourceIsArray && isReactive(source);
			let needsWrap = false;
			let isReadonlySource = false;
			if (sourceIsReactiveArray) {
				needsWrap = !isShallow(source);
				isReadonlySource = isReadonly(source);
				source = shallowReadArray(source);
			}
			ret = new Array(source.length);
			for (let i = 0, l = source.length; i < l; i++) ret[i] = renderItem(needsWrap ? isReadonlySource ? toReadonly(toReactive(source[i])) : toReactive(source[i]) : source[i], i, void 0, cached && cached[i]);
		} else if (typeof source === "number") {
			ret = new Array(source);
			for (let i = 0; i < source; i++) ret[i] = renderItem(i + 1, i, void 0, cached && cached[i]);
		} else if (isObject(source)) {
			if (source[Symbol.iterator]) ret = Array.from(source, (item, i) => renderItem(item, i, void 0, cached && cached[i]));
			else {
				const keys = Object.keys(source);
				ret = new Array(keys.length);
				for (let i = 0, l = keys.length; i < l; i++) {
					const key = keys[i];
					ret[i] = renderItem(source[key], key, i, cached && cached[i]);
				}
			}
		} else ret = [];
		if (cache) cache[index] = ret;
		return ret;
	}
	function renderSlot(slots, name, props, fallback, noSlotted, branchKey) {
		if (props == null) props = {};
		if (currentRenderingInstance.ce || currentRenderingInstance.parent && isAsyncWrapper(currentRenderingInstance.parent) && currentRenderingInstance.parent.ce) {
			const slotProps = branchKey != null && props.key == null ? extend({}, props, { key: branchKey }) : props;
			const hasProps = Object.keys(slotProps).length > 0;
			if (name !== "default") slotProps.name = name;
			return openBlock(), createBlock(Fragment, null, [createVNode("slot", slotProps, fallback && fallback())], hasProps ? -2 : 64);
		}
		let slot = slots[name];
		if (slot && slot._c) slot._d = false;
		const prevStackSize = blockStack.length;
		openBlock();
		let rendered;
		try {
			const validSlotContent = slot && ensureValidVNode(slot(props));
			const slotKey = props.key || branchKey || validSlotContent && validSlotContent.key;
			rendered = createBlock(Fragment, { key: (slotKey && !isSymbol(slotKey) ? slotKey : `_${name}`) + (!validSlotContent && fallback ? "_fb" : "") }, validSlotContent || (fallback ? fallback() : []), validSlotContent && slots._ === 1 ? 64 : -2);
		} catch (err) {
			for (let i = blockStack.length; i > prevStackSize; i--) closeBlock();
			throw err;
		} finally {
			if (slot && slot._c) slot._d = true;
		}
		if (!noSlotted && rendered.scopeId) rendered.slotScopeIds = [rendered.scopeId + "-s"];
		return rendered;
	}
	function ensureValidVNode(vnodes) {
		return vnodes.some((child) => {
			if (!isVNode(child)) return true;
			if (child.type === Comment) return false;
			if (child.type === Fragment && !ensureValidVNode(child.children)) return false;
			return true;
		}) ? vnodes : null;
	}
	var getPublicInstance = (i) => {
		if (!i) return null;
		if (isStatefulComponent(i)) return getComponentPublicInstance(i);
		return getPublicInstance(i.parent);
	};
	var publicPropertiesMap = extend(Object.create(null), {
		$: (i) => i,
		$el: (i) => i.vnode.el,
		$data: (i) => i.data,
		$props: (i) => i.props,
		$attrs: (i) => i.attrs,
		$slots: (i) => i.slots,
		$refs: (i) => i.refs,
		$parent: (i) => getPublicInstance(i.parent),
		$root: (i) => getPublicInstance(i.root),
		$host: (i) => i.ce,
		$emit: (i) => i.emit,
		$options: (i) => resolveMergedOptions(i),
		$forceUpdate: (i) => i.f || (i.f = () => {
			queueJob(i.update);
		}),
		$nextTick: (i) => i.n || (i.n = nextTick.bind(i.proxy)),
		$watch: (i) => instanceWatch.bind(i)
	});
	var hasSetupBinding = (state, key) => state !== EMPTY_OBJ && !state.__isScriptSetup && hasOwn(state, key);
	var PublicInstanceProxyHandlers = {
		get({ _: instance }, key) {
			if (key === "__v_skip") return true;
			const { ctx, setupState, data, props, accessCache, type, appContext } = instance;
			if (key[0] !== "$") {
				const n = accessCache[key];
				if (n !== void 0) switch (n) {
					case 1: return setupState[key];
					case 2: return data[key];
					case 4: return ctx[key];
					case 3: return props[key];
				}
				else if (hasSetupBinding(setupState, key)) {
					accessCache[key] = 1;
					return setupState[key];
				} else if (data !== EMPTY_OBJ && hasOwn(data, key)) {
					accessCache[key] = 2;
					return data[key];
				} else if (hasOwn(props, key)) {
					accessCache[key] = 3;
					return props[key];
				} else if (ctx !== EMPTY_OBJ && hasOwn(ctx, key)) {
					accessCache[key] = 4;
					return ctx[key];
				} else if (shouldCacheAccess) accessCache[key] = 0;
			}
			const publicGetter = publicPropertiesMap[key];
			let cssModule, globalProperties;
			if (publicGetter) {
				if (key === "$attrs") track(instance.attrs, "get", "");
				return publicGetter(instance);
			} else if ((cssModule = type.__cssModules) && (cssModule = cssModule[key])) return cssModule;
			else if (ctx !== EMPTY_OBJ && hasOwn(ctx, key)) {
				accessCache[key] = 4;
				return ctx[key];
			} else if (globalProperties = appContext.config.globalProperties, hasOwn(globalProperties, key)) return globalProperties[key];
		},
		set({ _: instance }, key, value) {
			const { data, setupState, ctx } = instance;
			if (hasSetupBinding(setupState, key)) {
				setupState[key] = value;
				return true;
			} else if (data !== EMPTY_OBJ && hasOwn(data, key)) {
				data[key] = value;
				return true;
			} else if (hasOwn(instance.props, key)) return false;
			if (key[0] === "$" && key.slice(1) in instance) return false;
			else ctx[key] = value;
			return true;
		},
		has({ _: { data, setupState, accessCache, ctx, appContext, props, type } }, key) {
			let cssModules;
			return !!(accessCache[key] || data !== EMPTY_OBJ && key[0] !== "$" && hasOwn(data, key) || hasSetupBinding(setupState, key) || hasOwn(props, key) || hasOwn(ctx, key) || hasOwn(publicPropertiesMap, key) || hasOwn(appContext.config.globalProperties, key) || (cssModules = type.__cssModules) && cssModules[key]);
		},
		defineProperty(target, key, descriptor) {
			if (descriptor.get != null) target._.accessCache[key] = 0;
			else if (hasOwn(descriptor, "value")) this.set(target, key, descriptor.value, null);
			return Reflect.defineProperty(target, key, descriptor);
		}
	};
	function normalizePropsOrEmits(props) {
		return isArray(props) ? props.reduce((normalized, p) => (normalized[p] = null, normalized), {}) : props;
	}
	var shouldCacheAccess = true;
	function applyOptions(instance) {
		const options = resolveMergedOptions(instance);
		const publicThis = instance.proxy;
		const ctx = instance.ctx;
		shouldCacheAccess = false;
		if (options.beforeCreate) callHook(options.beforeCreate, instance, "bc");
		const { data: dataOptions, computed: computedOptions, methods, watch: watchOptions, provide: provideOptions, inject: injectOptions, created, beforeMount, mounted, beforeUpdate, updated, activated, deactivated, beforeDestroy, beforeUnmount, destroyed, unmounted, render, renderTracked, renderTriggered, errorCaptured, serverPrefetch, expose, inheritAttrs, components, directives, filters } = options;
		const checkDuplicateProperties = null;
		if (injectOptions) resolveInjections(injectOptions, ctx, checkDuplicateProperties);
		if (methods) for (const key in methods) {
			const methodHandler = methods[key];
			if (isFunction(methodHandler)) ctx[key] = methodHandler.bind(publicThis);
		}
		if (dataOptions) {
			const data = dataOptions.call(publicThis, publicThis);
			if (!isObject(data)) {} else instance.data = reactive(data);
		}
		shouldCacheAccess = true;
		if (computedOptions) for (const key in computedOptions) {
			const opt = computedOptions[key];
			const get = isFunction(opt) ? opt.bind(publicThis, publicThis) : isFunction(opt.get) ? opt.get.bind(publicThis, publicThis) : NOOP;
			const set = !isFunction(opt) && isFunction(opt.set) ? opt.set.bind(publicThis) : NOOP;
			const c = computed({
				get,
				set
			});
			Object.defineProperty(ctx, key, {
				enumerable: true,
				configurable: true,
				get: () => c.value,
				set: (v) => c.value = v
			});
		}
		if (watchOptions) for (const key in watchOptions) createWatcher(watchOptions[key], ctx, publicThis, key);
		if (provideOptions) {
			const provides = isFunction(provideOptions) ? provideOptions.call(publicThis) : provideOptions;
			Reflect.ownKeys(provides).forEach((key) => {
				provide(key, provides[key]);
			});
		}
		if (created) callHook(created, instance, "c");
		function registerLifecycleHook(register, hook) {
			if (isArray(hook)) hook.forEach((_hook) => register(_hook.bind(publicThis)));
			else if (hook) register(hook.bind(publicThis));
		}
		registerLifecycleHook(onBeforeMount, beforeMount);
		registerLifecycleHook(onMounted, mounted);
		registerLifecycleHook(onBeforeUpdate, beforeUpdate);
		registerLifecycleHook(onUpdated, updated);
		registerLifecycleHook(onActivated, activated);
		registerLifecycleHook(onDeactivated, deactivated);
		registerLifecycleHook(onErrorCaptured, errorCaptured);
		registerLifecycleHook(onRenderTracked, renderTracked);
		registerLifecycleHook(onRenderTriggered, renderTriggered);
		registerLifecycleHook(onBeforeUnmount, beforeUnmount);
		registerLifecycleHook(onUnmounted, unmounted);
		registerLifecycleHook(onServerPrefetch, serverPrefetch);
		if (isArray(expose)) {
			if (expose.length) {
				const exposed = instance.exposed || (instance.exposed = {});
				expose.forEach((key) => {
					Object.defineProperty(exposed, key, {
						get: () => publicThis[key],
						set: (val) => publicThis[key] = val,
						enumerable: true
					});
				});
			} else if (!instance.exposed) instance.exposed = {};
		}
		if (render && instance.render === NOOP) instance.render = render;
		if (inheritAttrs != null) instance.inheritAttrs = inheritAttrs;
		if (components) instance.components = components;
		if (directives) instance.directives = directives;
		if (serverPrefetch) markAsyncBoundary(instance);
	}
	function resolveInjections(injectOptions, ctx, checkDuplicateProperties = NOOP) {
		if (isArray(injectOptions)) injectOptions = normalizeInject(injectOptions);
		for (const key in injectOptions) {
			const opt = injectOptions[key];
			let injected;
			if (isObject(opt)) {
				if ("default" in opt) injected = inject(opt.from || key, opt.default, true);
				else injected = inject(opt.from || key);
			} else injected = inject(opt);
			if (isRef(injected)) Object.defineProperty(ctx, key, {
				enumerable: true,
				configurable: true,
				get: () => injected.value,
				set: (v) => injected.value = v
			});
			else ctx[key] = injected;
		}
	}
	function callHook(hook, instance, type) {
		callWithAsyncErrorHandling(isArray(hook) ? hook.map((h) => h.bind(instance.proxy)) : hook.bind(instance.proxy), instance, type);
	}
	function createWatcher(raw, ctx, publicThis, key) {
		let getter = key.includes(".") ? createPathGetter(publicThis, key) : () => publicThis[key];
		if (isString(raw)) {
			const handler = ctx[raw];
			if (isFunction(handler)) watch(getter, handler);
		} else if (isFunction(raw)) watch(getter, raw.bind(publicThis));
		else if (isObject(raw)) {
			if (isArray(raw)) raw.forEach((r) => createWatcher(r, ctx, publicThis, key));
			else {
				const handler = isFunction(raw.handler) ? raw.handler.bind(publicThis) : ctx[raw.handler];
				if (isFunction(handler)) watch(getter, handler, raw);
			}
		}
	}
	function resolveMergedOptions(instance) {
		const base = instance.type;
		const { mixins, extends: extendsOptions } = base;
		const { mixins: globalMixins, optionsCache: cache, config: { optionMergeStrategies } } = instance.appContext;
		const cached = cache.get(base);
		let resolved;
		if (cached) resolved = cached;
		else if (!globalMixins.length && !mixins && !extendsOptions) resolved = base;
		else {
			resolved = {};
			if (globalMixins.length) globalMixins.forEach((m) => mergeOptions(resolved, m, optionMergeStrategies, true));
			mergeOptions(resolved, base, optionMergeStrategies);
		}
		if (isObject(base)) cache.set(base, resolved);
		return resolved;
	}
	function mergeOptions(to, from, strats, asMixin = false) {
		const { mixins, extends: extendsOptions } = from;
		if (extendsOptions) mergeOptions(to, extendsOptions, strats, true);
		if (mixins) mixins.forEach((m) => mergeOptions(to, m, strats, true));
		for (const key in from) if (asMixin && key === "expose") {} else {
			const strat = internalOptionMergeStrats[key] || strats && strats[key];
			to[key] = strat ? strat(to[key], from[key]) : from[key];
		}
		return to;
	}
	var internalOptionMergeStrats = {
		data: mergeDataFn,
		props: mergeEmitsOrPropsOptions,
		emits: mergeEmitsOrPropsOptions,
		methods: mergeObjectOptions,
		computed: mergeObjectOptions,
		beforeCreate: mergeAsArray,
		created: mergeAsArray,
		beforeMount: mergeAsArray,
		mounted: mergeAsArray,
		beforeUpdate: mergeAsArray,
		updated: mergeAsArray,
		beforeDestroy: mergeAsArray,
		beforeUnmount: mergeAsArray,
		destroyed: mergeAsArray,
		unmounted: mergeAsArray,
		activated: mergeAsArray,
		deactivated: mergeAsArray,
		errorCaptured: mergeAsArray,
		serverPrefetch: mergeAsArray,
		components: mergeObjectOptions,
		directives: mergeObjectOptions,
		watch: mergeWatchOptions,
		provide: mergeDataFn,
		inject: mergeInject
	};
	function mergeDataFn(to, from) {
		if (!from) return to;
		if (!to) return from;
		return function mergedDataFn() {
			return extend(isFunction(to) ? to.call(this, this) : to, isFunction(from) ? from.call(this, this) : from);
		};
	}
	function mergeInject(to, from) {
		return mergeObjectOptions(normalizeInject(to), normalizeInject(from));
	}
	function normalizeInject(raw) {
		if (isArray(raw)) {
			const res = {};
			for (let i = 0; i < raw.length; i++) res[raw[i]] = raw[i];
			return res;
		}
		return raw;
	}
	function mergeAsArray(to, from) {
		return to ? [...new Set([].concat(to, from))] : from;
	}
	function mergeObjectOptions(to, from) {
		return to ? extend(Object.create(null), to, from) : from;
	}
	function mergeEmitsOrPropsOptions(to, from) {
		if (to) {
			if (isArray(to) && isArray(from)) return [...new Set([...to, ...from])];
			return extend(Object.create(null), normalizePropsOrEmits(to), normalizePropsOrEmits(from != null ? from : {}));
		} else return from;
	}
	function mergeWatchOptions(to, from) {
		if (!to) return from;
		if (!from) return to;
		const merged = extend(Object.create(null), to);
		for (const key in from) merged[key] = mergeAsArray(to[key], from[key]);
		return merged;
	}
	function createAppContext() {
		return {
			app: null,
			config: {
				isNativeTag: NO,
				performance: false,
				globalProperties: {},
				optionMergeStrategies: {},
				errorHandler: void 0,
				warnHandler: void 0,
				compilerOptions: {}
			},
			mixins: [],
			components: {},
			directives: {},
			provides: Object.create(null),
			optionsCache: new WeakMap(),
			propsCache: new WeakMap(),
			emitsCache: new WeakMap()
		};
	}
	var uid$1 = 0;
	function createAppAPI(render, hydrate) {
		return function createApp(rootComponent, rootProps = null) {
			if (!isFunction(rootComponent)) rootComponent = extend({}, rootComponent);
			if (rootProps != null && !isObject(rootProps)) rootProps = null;
			const context = createAppContext();
			const installedPlugins = new WeakSet();
			const pluginCleanupFns = [];
			let isMounted = false;
			const app = context.app = {
				_uid: uid$1++,
				_component: rootComponent,
				_props: rootProps,
				_container: null,
				_context: context,
				_instance: null,
				version,
				get config() {
					return context.config;
				},
				set config(v) {},
				use(plugin, ...options) {
					if (installedPlugins.has(plugin)) {} else if (plugin && isFunction(plugin.install)) {
						installedPlugins.add(plugin);
						plugin.install(app, ...options);
					} else if (isFunction(plugin)) {
						installedPlugins.add(plugin);
						plugin(app, ...options);
					}
					return app;
				},
				mixin(mixin) {
					if (!context.mixins.includes(mixin)) context.mixins.push(mixin);
					return app;
				},
				component(name, component) {
					if (!component) return context.components[name];
					context.components[name] = component;
					return app;
				},
				directive(name, directive) {
					if (!directive) return context.directives[name];
					context.directives[name] = directive;
					return app;
				},
				mount(rootContainer, isHydrate, namespace) {
					if (!isMounted) {
						const vnode = app._ceVNode || createVNode(rootComponent, rootProps);
						vnode.appContext = context;
						if (namespace === true) namespace = "svg";
						else if (namespace === false) namespace = void 0;
						if (isHydrate && hydrate) hydrate(vnode, rootContainer);
						else render(vnode, rootContainer, namespace);
						isMounted = true;
						app._container = rootContainer;
						rootContainer.__vue_app__ = app;
						return getComponentPublicInstance(vnode.component);
					}
				},
				onUnmount(cleanupFn) {
					pluginCleanupFns.push(cleanupFn);
				},
				unmount() {
					if (isMounted) {
						callWithAsyncErrorHandling(pluginCleanupFns, app._instance, 16);
						render(null, app._container);
						delete app._container.__vue_app__;
					}
				},
				provide(key, value) {
					context.provides[key] = value;
					return app;
				},
				runWithContext(fn) {
					const lastApp = currentApp;
					currentApp = app;
					try {
						return fn();
					} finally {
						currentApp = lastApp;
					}
				}
			};
			return app;
		};
	}
	var currentApp = null;
	var getModelModifiers = (props, modelName) => {
		return modelName === "modelValue" || modelName === "model-value" ? props.modelModifiers : props[`${modelName}Modifiers`] || props[`${camelize(modelName)}Modifiers`] || props[`${hyphenate(modelName)}Modifiers`];
	};
	function emit(instance, event, ...rawArgs) {
		if (instance.isUnmounted) return;
		const props = instance.vnode.props || EMPTY_OBJ;
		let args = rawArgs;
		const isModelListener = event.startsWith("update:");
		const modifiers = isModelListener && getModelModifiers(props, event.slice(7));
		if (modifiers) {
			if (modifiers.trim) args = rawArgs.map((a) => isString(a) ? a.trim() : a);
			if (modifiers.number) args = args.map(looseToNumber);
		}
		let handlerName;
		let handler = props[handlerName = toHandlerKey(event)] || props[handlerName = toHandlerKey(camelize(event))];
		if (!handler && isModelListener) handler = props[handlerName = toHandlerKey(hyphenate(event))];
		if (handler) callWithAsyncErrorHandling(handler, instance, 6, args);
		const onceHandler = props[handlerName + `Once`];
		if (onceHandler) {
			if (!instance.emitted) instance.emitted = {};
			else if (instance.emitted[handlerName]) return;
			instance.emitted[handlerName] = true;
			callWithAsyncErrorHandling(onceHandler, instance, 6, args);
		}
	}
	var mixinEmitsCache = new WeakMap();
	function normalizeEmitsOptions(comp, appContext, asMixin = false) {
		const cache = asMixin ? mixinEmitsCache : appContext.emitsCache;
		const cached = cache.get(comp);
		if (cached !== void 0) return cached;
		const raw = comp.emits;
		let normalized = {};
		let hasExtends = false;
		if (!isFunction(comp)) {
			const extendEmits = (raw2) => {
				const normalizedFromExtend = normalizeEmitsOptions(raw2, appContext, true);
				if (normalizedFromExtend) {
					hasExtends = true;
					extend(normalized, normalizedFromExtend);
				}
			};
			if (!asMixin && appContext.mixins.length) appContext.mixins.forEach(extendEmits);
			if (comp.extends) extendEmits(comp.extends);
			if (comp.mixins) comp.mixins.forEach(extendEmits);
		}
		if (!raw && !hasExtends) {
			if (isObject(comp)) cache.set(comp, null);
			return null;
		}
		if (isArray(raw)) raw.forEach((key) => normalized[key] = null);
		else extend(normalized, raw);
		if (isObject(comp)) cache.set(comp, normalized);
		return normalized;
	}
	function isEmitListener(options, key) {
		if (!options || !isOn(key)) return false;
		key = key.slice(2);
		key = key === "Once" ? key : key.replace(/Once$/, "");
		return hasOwn(options, key[0].toLowerCase() + key.slice(1)) || hasOwn(options, hyphenate(key)) || hasOwn(options, key);
	}
	function renderComponentRoot(instance) {
		const { type: Component, vnode, proxy, withProxy, propsOptions: [propsOptions], slots, attrs, emit, render, renderCache, props, data, setupState, ctx, inheritAttrs } = instance;
		const prev = setCurrentRenderingInstance(instance);
		let result;
		let fallthroughAttrs;
		try {
			if (vnode.shapeFlag & 4) {
				const proxyToUse = withProxy || proxy;
				const thisProxy = proxyToUse;
				result = normalizeVNode(render.call(thisProxy, proxyToUse, renderCache, props, setupState, data, ctx));
				fallthroughAttrs = attrs;
			} else {
				const render2 = Component;
				result = normalizeVNode(render2.length > 1 ? render2(props, {
					attrs,
					slots,
					emit
				}) : render2(props, null));
				fallthroughAttrs = Component.props ? attrs : getFunctionalFallthrough(attrs);
			}
		} catch (err) {
			blockStack.length = 0;
			handleError(err, instance, 1);
			result = createVNode(Comment);
		}
		let root = result;
		if (fallthroughAttrs && inheritAttrs !== false) {
			const keys = Object.keys(fallthroughAttrs);
			const { shapeFlag } = root;
			if (keys.length) {
				if (shapeFlag & 7) {
					if (propsOptions && keys.some(isModelListener)) fallthroughAttrs = filterModelListeners(fallthroughAttrs, propsOptions);
					root = cloneVNode(root, fallthroughAttrs, false, true);
				}
			}
		}
		if (vnode.dirs) {
			root = cloneVNode(root, null, false, true);
			root.dirs = root.dirs ? root.dirs.concat(vnode.dirs) : vnode.dirs;
		}
		if (vnode.transition) setTransitionHooks(isTeleport(root.type) ? getInnerChild$1(root) || root : root, vnode.transition);
		result = root;
		setCurrentRenderingInstance(prev);
		return result;
	}
	var getFunctionalFallthrough = (attrs) => {
		let res;
		for (const key in attrs) if (key === "class" || key === "style" || isOn(key)) (res || (res = {}))[key] = attrs[key];
		return res;
	};
	var filterModelListeners = (attrs, props) => {
		const res = {};
		for (const key in attrs) if (!isModelListener(key) || !(key.slice(9) in props)) res[key] = attrs[key];
		return res;
	};
	function shouldUpdateComponent(prevVNode, nextVNode, optimized) {
		const { props: prevProps, children: prevChildren, component } = prevVNode;
		const { props: nextProps, children: nextChildren, patchFlag } = nextVNode;
		const emits = component.emitsOptions;
		if (nextVNode.dirs || nextVNode.transition) return true;
		if (optimized && patchFlag >= 0) {
			if (patchFlag & 1024) return true;
			if (patchFlag & 16) {
				if (!prevProps) return !!nextProps;
				return hasPropsChanged(prevProps, nextProps, emits);
			} else if (patchFlag & 8) {
				const dynamicProps = nextVNode.dynamicProps;
				for (let i = 0; i < dynamicProps.length; i++) {
					const key = dynamicProps[i];
					if (hasPropValueChanged(nextProps, prevProps, key) && !isEmitListener(emits, key)) return true;
				}
			}
		} else {
			if (prevChildren || nextChildren) {
				if (!nextChildren || !nextChildren.$stable) return true;
			}
			if (prevProps === nextProps) return false;
			if (!prevProps) return !!nextProps;
			if (!nextProps) return true;
			return hasPropsChanged(prevProps, nextProps, emits);
		}
		return false;
	}
	function hasPropsChanged(prevProps, nextProps, emitsOptions) {
		const nextKeys = Object.keys(nextProps);
		if (nextKeys.length !== Object.keys(prevProps).length) return true;
		for (let i = 0; i < nextKeys.length; i++) {
			const key = nextKeys[i];
			if (hasPropValueChanged(nextProps, prevProps, key) && !isEmitListener(emitsOptions, key)) return true;
		}
		return false;
	}
	function hasPropValueChanged(nextProps, prevProps, key) {
		const nextProp = nextProps[key];
		const prevProp = prevProps[key];
		if (key === "style" && isObject(nextProp) && isObject(prevProp)) return !looseEqual(nextProp, prevProp);
		return nextProp !== prevProp;
	}
	function updateHOCHostEl({ vnode, parent, suspense }, el) {
		while (parent) {
			const root = parent.subTree;
			if (root.suspense && root.suspense.activeBranch === vnode) {
				root.suspense.vnode.el = root.el = el;
				vnode = root;
			}
			if (root === vnode) {
				(vnode = parent.vnode).el = el;
				parent = parent.parent;
			} else break;
		}
		if (suspense && suspense.activeBranch === vnode) suspense.vnode.el = el;
	}
	var internalObjectProto = {};
	var createInternalObject = () => Object.create(internalObjectProto);
	var isInternalObject = (obj) => Object.getPrototypeOf(obj) === internalObjectProto;
	function initProps(instance, rawProps, isStateful, isSSR = false) {
		const props = {};
		const attrs = createInternalObject();
		instance.propsDefaults = Object.create(null);
		setFullProps(instance, rawProps, props, attrs);
		for (const key in instance.propsOptions[0]) if (!(key in props)) props[key] = void 0;
		if (isStateful) instance.props = isSSR ? props : shallowReactive(props);
		else if (!instance.type.props) instance.props = attrs;
		else instance.props = props;
		instance.attrs = attrs;
	}
	function updateProps(instance, rawProps, rawPrevProps, optimized) {
		const { props, attrs, vnode: { patchFlag } } = instance;
		const rawCurrentProps = toRaw(props);
		const [options] = instance.propsOptions;
		let hasAttrsChanged = false;
		if ((optimized || patchFlag > 0) && !(patchFlag & 16)) {
			if (patchFlag & 8) {
				const propsToUpdate = instance.vnode.dynamicProps;
				for (let i = 0; i < propsToUpdate.length; i++) {
					let key = propsToUpdate[i];
					if (isEmitListener(instance.emitsOptions, key)) continue;
					const value = rawProps[key];
					if (options) {
						if (hasOwn(attrs, key)) {
							if (value !== attrs[key]) {
								attrs[key] = value;
								hasAttrsChanged = true;
							}
						} else {
							const camelizedKey = camelize(key);
							props[camelizedKey] = resolvePropValue(options, rawCurrentProps, camelizedKey, value, instance, false);
						}
					} else if (value !== attrs[key]) {
						attrs[key] = value;
						hasAttrsChanged = true;
					}
				}
			}
		} else {
			if (setFullProps(instance, rawProps, props, attrs)) hasAttrsChanged = true;
			let kebabKey;
			for (const key in rawCurrentProps) if (!rawProps || !hasOwn(rawProps, key) && ((kebabKey = hyphenate(key)) === key || !hasOwn(rawProps, kebabKey))) {
				if (options) {
					if (rawPrevProps && (rawPrevProps[key] !== void 0 || rawPrevProps[kebabKey] !== void 0)) props[key] = resolvePropValue(options, rawCurrentProps, key, void 0, instance, true);
				} else delete props[key];
			}
			if (attrs !== rawCurrentProps) {
				for (const key in attrs) if (!rawProps || !hasOwn(rawProps, key) && true) {
					delete attrs[key];
					hasAttrsChanged = true;
				}
			}
		}
		if (hasAttrsChanged) trigger(instance.attrs, "set", "");
	}
	function setFullProps(instance, rawProps, props, attrs) {
		const [options, needCastKeys] = instance.propsOptions;
		let hasAttrsChanged = false;
		let rawCastValues;
		if (rawProps) for (let key in rawProps) {
			if (isReservedProp(key)) continue;
			const value = rawProps[key];
			let camelKey;
			if (options && hasOwn(options, camelKey = camelize(key))) {
				if (!needCastKeys || !needCastKeys.includes(camelKey)) props[camelKey] = value;
				else (rawCastValues || (rawCastValues = {}))[camelKey] = value;
			} else if (!isEmitListener(instance.emitsOptions, key)) {
				if (!(key in attrs) || value !== attrs[key]) {
					attrs[key] = value;
					hasAttrsChanged = true;
				}
			}
		}
		if (needCastKeys) {
			const rawCurrentProps = toRaw(props);
			const castValues = rawCastValues || EMPTY_OBJ;
			for (let i = 0; i < needCastKeys.length; i++) {
				const key = needCastKeys[i];
				props[key] = resolvePropValue(options, rawCurrentProps, key, castValues[key], instance, !hasOwn(castValues, key));
			}
		}
		return hasAttrsChanged;
	}
	function resolvePropValue(options, props, key, value, instance, isAbsent) {
		const opt = options[key];
		if (opt != null) {
			const hasDefault = hasOwn(opt, "default");
			if (hasDefault && value === void 0) {
				const defaultValue = opt.default;
				if (opt.type !== Function && !opt.skipFactory && isFunction(defaultValue)) {
					const { propsDefaults } = instance;
					if (key in propsDefaults) value = propsDefaults[key];
					else {
						const reset = setCurrentInstance(instance);
						value = propsDefaults[key] = defaultValue.call(null, props);
						reset();
					}
				} else value = defaultValue;
				if (instance.ce) instance.ce._setProp(key, value);
			}
			if (opt[0]) {
				if (isAbsent && !hasDefault) value = false;
				else if (opt[1] && (value === "" || value === hyphenate(key))) value = true;
			}
		}
		return value;
	}
	var mixinPropsCache = new WeakMap();
	function normalizePropsOptions(comp, appContext, asMixin = false) {
		const cache = asMixin ? mixinPropsCache : appContext.propsCache;
		const cached = cache.get(comp);
		if (cached) return cached;
		const raw = comp.props;
		const normalized = {};
		const needCastKeys = [];
		let hasExtends = false;
		if (!isFunction(comp)) {
			const extendProps = (raw2) => {
				hasExtends = true;
				const [props, keys] = normalizePropsOptions(raw2, appContext, true);
				extend(normalized, props);
				if (keys) needCastKeys.push(...keys);
			};
			if (!asMixin && appContext.mixins.length) appContext.mixins.forEach(extendProps);
			if (comp.extends) extendProps(comp.extends);
			if (comp.mixins) comp.mixins.forEach(extendProps);
		}
		if (!raw && !hasExtends) {
			if (isObject(comp)) cache.set(comp, EMPTY_ARR);
			return EMPTY_ARR;
		}
		if (isArray(raw)) for (let i = 0; i < raw.length; i++) {
			const normalizedKey = camelize(raw[i]);
			if (validatePropName(normalizedKey)) normalized[normalizedKey] = EMPTY_OBJ;
		}
		else if (raw) for (const key in raw) {
			const normalizedKey = camelize(key);
			if (validatePropName(normalizedKey)) {
				const opt = raw[key];
				const prop = normalized[normalizedKey] = isArray(opt) || isFunction(opt) ? { type: opt } : extend({}, opt);
				const propType = prop.type;
				let shouldCast = false;
				let shouldCastTrue = true;
				if (isArray(propType)) for (let index = 0; index < propType.length; ++index) {
					const type = propType[index];
					const typeName = isFunction(type) && type.name;
					if (typeName === "Boolean") {
						shouldCast = true;
						break;
					} else if (typeName === "String") shouldCastTrue = false;
				}
				else shouldCast = isFunction(propType) && propType.name === "Boolean";
				prop[0] = shouldCast;
				prop[1] = shouldCastTrue;
				if (shouldCast || hasOwn(prop, "default")) needCastKeys.push(normalizedKey);
			}
		}
		const res = [normalized, needCastKeys];
		if (isObject(comp)) cache.set(comp, res);
		return res;
	}
	function validatePropName(key) {
		if (key[0] !== "$" && !isReservedProp(key)) return true;
		return false;
	}
	var isInternalKey = (key) => key === "_" || key === "_ctx" || key === "$stable";
	var normalizeSlotValue = (value) => isArray(value) ? value.map(normalizeVNode) : [normalizeVNode(value)];
	var normalizeSlot = (key, rawSlot, ctx) => {
		if (rawSlot._n) return rawSlot;
		const normalized = withCtx((...args) => {
			return normalizeSlotValue(rawSlot(...args));
		}, ctx);
		normalized._c = false;
		return normalized;
	};
	var normalizeObjectSlots = (rawSlots, slots, instance) => {
		const ctx = rawSlots._ctx;
		for (const key in rawSlots) {
			if (isInternalKey(key)) continue;
			const value = rawSlots[key];
			if (isFunction(value)) slots[key] = normalizeSlot(key, value, ctx);
			else if (value != null) {
				const normalized = normalizeSlotValue(value);
				slots[key] = () => normalized;
			}
		}
	};
	var normalizeVNodeSlots = (instance, children) => {
		const normalized = normalizeSlotValue(children);
		instance.slots.default = () => normalized;
	};
	var assignSlots = (slots, children, optimized) => {
		for (const key in children) if (optimized || !isInternalKey(key)) slots[key] = children[key];
	};
	var initSlots = (instance, children, optimized) => {
		const slots = instance.slots = createInternalObject();
		if (instance.vnode.shapeFlag & 32) {
			const type = children._;
			if (type) {
				assignSlots(slots, children, optimized);
				if (optimized) def(slots, "_", type, true);
			} else normalizeObjectSlots(children, slots);
		} else if (children) normalizeVNodeSlots(instance, children);
	};
	var updateSlots = (instance, children, optimized) => {
		const { vnode, slots } = instance;
		let needDeletionCheck = true;
		let deletionComparisonTarget = EMPTY_OBJ;
		if (vnode.shapeFlag & 32) {
			const type = children._;
			if (type) {
				if (optimized && type === 1) needDeletionCheck = false;
				else assignSlots(slots, children, optimized);
			} else {
				needDeletionCheck = !children.$stable;
				normalizeObjectSlots(children, slots);
			}
			deletionComparisonTarget = children;
		} else if (children) {
			normalizeVNodeSlots(instance, children);
			deletionComparisonTarget = { default: 1 };
		}
		if (needDeletionCheck) {
			for (const key in slots) if (!isInternalKey(key) && deletionComparisonTarget[key] == null) delete slots[key];
		}
	};
	var queuePostRenderEffect = queueEffectWithSuspense;
	function createRenderer(options) {
		return baseCreateRenderer(options);
	}
	function baseCreateRenderer(options, createHydrationFns) {
		const target = getGlobalThis();
		target.__VUE__ = true;
		const { insert: hostInsert, remove: hostRemove, patchProp: hostPatchProp, createElement: hostCreateElement, createText: hostCreateText, createComment: hostCreateComment, setText: hostSetText, setElementText: hostSetElementText, parentNode: hostParentNode, nextSibling: hostNextSibling, setScopeId: hostSetScopeId = NOOP, insertStaticContent: hostInsertStaticContent } = options;
		const patch = (n1, n2, container, anchor = null, parentComponent = null, parentSuspense = null, namespace = void 0, slotScopeIds = null, optimized = !!n2.dynamicChildren) => {
			if (n1 === n2) return;
			if (n1 && !isSameVNodeType(n1, n2)) {
				anchor = getNextHostNode(n1);
				unmount(n1, parentComponent, parentSuspense, true);
				n1 = null;
			}
			if (n2.patchFlag === -2) {
				optimized = false;
				n2.dynamicChildren = null;
			}
			if (n2.dynamicChildren && n1 && n1.dynamicChildren && n1.dynamicChildren.hasOnce) {
				if (n2.dynamicChildren === EMPTY_ARR) n2.dynamicChildren = [];
				n2.dynamicChildren.hasOnce = true;
			}
			const { type, ref, shapeFlag } = n2;
			switch (type) {
				case Text:
					processText(n1, n2, container, anchor);
					break;
				case Comment:
					processCommentNode(n1, n2, container, anchor);
					break;
				case Static:
					if (n1 == null) mountStaticNode(n2, container, anchor, namespace);
					break;
				case Fragment:
					processFragment(n1, n2, container, anchor, parentComponent, parentSuspense, namespace, slotScopeIds, optimized);
					break;
				default: if (shapeFlag & 1) processElement(n1, n2, container, anchor, parentComponent, parentSuspense, namespace, slotScopeIds, optimized);
				else if (shapeFlag & 6) processComponent(n1, n2, container, anchor, parentComponent, parentSuspense, namespace, slotScopeIds, optimized);
				else if (shapeFlag & 64) type.process(n1, n2, container, anchor, parentComponent, parentSuspense, namespace, slotScopeIds, optimized, internals);
				else if (shapeFlag & 128) type.process(n1, n2, container, anchor, parentComponent, parentSuspense, namespace, slotScopeIds, optimized, internals);
			}
			if (ref != null && parentComponent) setRef(ref, n1 && n1.ref, parentSuspense, n2 || n1, !n2);
			else if (ref == null && n1 && n1.ref != null) setRef(n1.ref, null, parentSuspense, n1, true);
		};
		const processText = (n1, n2, container, anchor) => {
			if (n1 == null) hostInsert(n2.el = hostCreateText(n2.children), container, anchor);
			else {
				const el = n2.el = n1.el;
				if (n2.children !== n1.children) hostSetText(el, n2.children);
			}
		};
		const processCommentNode = (n1, n2, container, anchor) => {
			if (n1 == null) hostInsert(n2.el = hostCreateComment(n2.children || ""), container, anchor);
			else n2.el = n1.el;
		};
		const mountStaticNode = (n2, container, anchor, namespace) => {
			[n2.el, n2.anchor] = hostInsertStaticContent(n2.children, container, anchor, namespace, n2.el, n2.anchor);
		};
		const moveStaticNode = ({ el, anchor }, container, nextSibling) => {
			let next;
			while (el && el !== anchor) {
				next = hostNextSibling(el);
				hostInsert(el, container, nextSibling);
				el = next;
			}
			hostInsert(anchor, container, nextSibling);
		};
		const removeStaticNode = ({ el, anchor }) => {
			let next;
			while (el && el !== anchor) {
				next = hostNextSibling(el);
				hostRemove(el);
				el = next;
			}
			hostRemove(anchor);
		};
		const processElement = (n1, n2, container, anchor, parentComponent, parentSuspense, namespace, slotScopeIds, optimized) => {
			if (n2.type === "svg") namespace = "svg";
			else if (n2.type === "math") namespace = "mathml";
			if (n1 == null) mountElement(n2, container, anchor, parentComponent, parentSuspense, namespace, slotScopeIds, optimized);
			else {
				const customElement = n1.el && n1.el._isVueCE ? n1.el : null;
				try {
					if (customElement) customElement._beginPatch();
					patchElement(n1, n2, parentComponent, parentSuspense, namespace, slotScopeIds, optimized);
				} finally {
					if (customElement) customElement._endPatch();
				}
			}
		};
		const mountElement = (vnode, container, anchor, parentComponent, parentSuspense, namespace, slotScopeIds, optimized) => {
			let el;
			let vnodeHook;
			const { props, shapeFlag, transition, dirs } = vnode;
			el = vnode.el = hostCreateElement(vnode.type, namespace, props && props.is, props);
			if (shapeFlag & 8) hostSetElementText(el, vnode.children);
			else if (shapeFlag & 16) mountChildren(vnode.children, el, null, parentComponent, parentSuspense, resolveChildrenNamespace(vnode, namespace), slotScopeIds, optimized);
			if (dirs) invokeDirectiveHook(vnode, null, parentComponent, "created");
			setScopeId(el, vnode, vnode.scopeId, slotScopeIds, parentComponent);
			if (props) {
				for (const key in props) if (key !== "value" && !isReservedProp(key)) hostPatchProp(el, key, null, props[key], namespace, parentComponent);
				if ("value" in props) hostPatchProp(el, "value", null, props.value, namespace);
				if (vnodeHook = props.onVnodeBeforeMount) invokeVNodeHook(vnodeHook, parentComponent, vnode);
			}
			if (dirs) invokeDirectiveHook(vnode, null, parentComponent, "beforeMount");
			const needCallTransitionHooks = needTransition(parentSuspense, transition);
			if (needCallTransitionHooks) transition.beforeEnter(el);
			hostInsert(el, container, anchor);
			if ((vnodeHook = props && props.onVnodeMounted) || needCallTransitionHooks || dirs) queuePostRenderEffect(() => {
				try {
					vnodeHook && invokeVNodeHook(vnodeHook, parentComponent, vnode);
					needCallTransitionHooks && transition.enter(el);
					dirs && invokeDirectiveHook(vnode, null, parentComponent, "mounted");
				} finally {}
			}, parentSuspense);
		};
		const setScopeId = (el, vnode, scopeId, slotScopeIds, parentComponent) => {
			if (scopeId) hostSetScopeId(el, scopeId);
			if (slotScopeIds) for (let i = 0; i < slotScopeIds.length; i++) hostSetScopeId(el, slotScopeIds[i]);
			if (parentComponent) {
				let subTree = parentComponent.subTree;
				if (vnode === subTree || isSuspense(subTree.type) && (subTree.ssContent === vnode || subTree.ssFallback === vnode)) {
					const parentVNode = parentComponent.vnode;
					setScopeId(el, parentVNode, parentVNode.scopeId, parentVNode.slotScopeIds, parentComponent.parent);
				}
			}
		};
		const mountChildren = (children, container, anchor, parentComponent, parentSuspense, namespace, slotScopeIds, optimized, start = 0) => {
			for (let i = start; i < children.length; i++) {
				const child = children[i] = optimized ? cloneIfMounted(children[i]) : normalizeVNode(children[i]);
				patch(null, child, container, anchor, parentComponent, parentSuspense, namespace, slotScopeIds, optimized);
			}
		};
		const patchElement = (n1, n2, parentComponent, parentSuspense, namespace, slotScopeIds, optimized) => {
			const el = n2.el = n1.el;
			let { patchFlag, dynamicChildren, dirs } = n2;
			patchFlag |= n1.patchFlag & 16;
			const oldProps = n1.props || EMPTY_OBJ;
			const newProps = n2.props || EMPTY_OBJ;
			let vnodeHook;
			parentComponent && toggleRecurse(parentComponent, false);
			if (vnodeHook = newProps.onVnodeBeforeUpdate) invokeVNodeHook(vnodeHook, parentComponent, n2, n1);
			if (dirs) invokeDirectiveHook(n2, n1, parentComponent, "beforeUpdate");
			parentComponent && toggleRecurse(parentComponent, true);
			if (dynamicChildren && (!n1.dynamicChildren || n1.dynamicChildren.length !== dynamicChildren.length)) {
				patchFlag = 0;
				optimized = false;
				dynamicChildren = null;
			}
			if (oldProps.innerHTML && newProps.innerHTML == null || oldProps.textContent && newProps.textContent == null) hostSetElementText(el, "");
			if (dynamicChildren) patchBlockChildren(n1.dynamicChildren, dynamicChildren, el, parentComponent, parentSuspense, resolveChildrenNamespace(n2, namespace), slotScopeIds);
			else if (!optimized) patchChildren(n1, n2, el, null, parentComponent, parentSuspense, resolveChildrenNamespace(n2, namespace), slotScopeIds, false);
			if (patchFlag > 0) {
				if (patchFlag & 16) patchProps(el, oldProps, newProps, parentComponent, namespace);
				else {
					if (patchFlag & 2) {
						if (oldProps.class !== newProps.class) hostPatchProp(el, "class", null, newProps.class, namespace);
					}
					if (patchFlag & 4) hostPatchProp(el, "style", oldProps.style, newProps.style, namespace);
					if (patchFlag & 8) {
						const propsToUpdate = n2.dynamicProps;
						for (let i = 0; i < propsToUpdate.length; i++) {
							const key = propsToUpdate[i];
							const prev = oldProps[key];
							const next = newProps[key];
							if (next !== prev || key === "value") hostPatchProp(el, key, prev, next, namespace, parentComponent);
						}
					}
				}
				if (patchFlag & 1) {
					if (n1.children !== n2.children) hostSetElementText(el, n2.children);
				}
			} else if (!optimized && dynamicChildren == null) patchProps(el, oldProps, newProps, parentComponent, namespace);
			if ((vnodeHook = newProps.onVnodeUpdated) || dirs) queuePostRenderEffect(() => {
				vnodeHook && invokeVNodeHook(vnodeHook, parentComponent, n2, n1);
				dirs && invokeDirectiveHook(n2, n1, parentComponent, "updated");
			}, parentSuspense);
		};
		const patchBlockChildren = (oldChildren, newChildren, fallbackContainer, parentComponent, parentSuspense, namespace, slotScopeIds) => {
			for (let i = 0; i < newChildren.length; i++) {
				const oldVNode = oldChildren[i];
				const newVNode = newChildren[i];
				const container = oldVNode.el && (oldVNode.type === Fragment || !isSameVNodeType(oldVNode, newVNode) || oldVNode.shapeFlag & 198) ? hostParentNode(oldVNode.el) : fallbackContainer;
				patch(oldVNode, newVNode, container, null, parentComponent, parentSuspense, namespace, slotScopeIds, true);
			}
		};
		const patchProps = (el, oldProps, newProps, parentComponent, namespace) => {
			if (oldProps !== newProps) {
				if (oldProps !== EMPTY_OBJ) {
					for (const key in oldProps) if (!isReservedProp(key) && !(key in newProps)) hostPatchProp(el, key, oldProps[key], null, namespace, parentComponent);
				}
				for (const key in newProps) {
					if (isReservedProp(key)) continue;
					const next = newProps[key];
					const prev = oldProps[key];
					if (next !== prev && key !== "value") hostPatchProp(el, key, prev, next, namespace, parentComponent);
				}
				if ("value" in newProps) hostPatchProp(el, "value", oldProps.value, newProps.value, namespace);
			}
		};
		const processFragment = (n1, n2, container, anchor, parentComponent, parentSuspense, namespace, slotScopeIds, optimized) => {
			const fragmentStartAnchor = n2.el = n1 ? n1.el : hostCreateText("");
			const fragmentEndAnchor = n2.anchor = n1 ? n1.anchor : hostCreateText("");
			let { patchFlag, dynamicChildren, slotScopeIds: fragmentSlotScopeIds } = n2;
			if (fragmentSlotScopeIds) slotScopeIds = slotScopeIds ? slotScopeIds.concat(fragmentSlotScopeIds) : fragmentSlotScopeIds;
			if (n1 == null) {
				hostInsert(fragmentStartAnchor, container, anchor);
				hostInsert(fragmentEndAnchor, container, anchor);
				mountChildren(n2.children || [], container, fragmentEndAnchor, parentComponent, parentSuspense, namespace, slotScopeIds, optimized);
			} else if (patchFlag > 0 && patchFlag & 64 && dynamicChildren && n1.dynamicChildren && n1.dynamicChildren.length === dynamicChildren.length) {
				patchBlockChildren(n1.dynamicChildren, dynamicChildren, container, parentComponent, parentSuspense, namespace, slotScopeIds);
				if (n2.key != null || parentComponent && n2 === parentComponent.subTree) traverseStaticChildren(n1, n2, true);
			} else patchChildren(n1, n2, container, fragmentEndAnchor, parentComponent, parentSuspense, namespace, slotScopeIds, optimized);
		};
		const processComponent = (n1, n2, container, anchor, parentComponent, parentSuspense, namespace, slotScopeIds, optimized) => {
			n2.slotScopeIds = slotScopeIds;
			if (n1 == null) {
				if (n2.shapeFlag & 512) parentComponent.ctx.activate(n2, container, anchor, namespace, optimized);
				else mountComponent(n2, container, anchor, parentComponent, parentSuspense, namespace, optimized);
			} else updateComponent(n1, n2, optimized);
		};
		const mountComponent = (initialVNode, container, anchor, parentComponent, parentSuspense, namespace, optimized) => {
			const instance = initialVNode.component = createComponentInstance(initialVNode, parentComponent, parentSuspense);
			if (isKeepAlive(initialVNode)) instance.ctx.renderer = internals;
			setupComponent(instance, false, optimized);
			if (instance.asyncDep) {
				parentSuspense && parentSuspense.registerDep(instance, setupRenderEffect, optimized);
				if (!initialVNode.el) {
					const placeholder = instance.subTree = createVNode(Comment);
					processCommentNode(null, placeholder, container, anchor);
					initialVNode.placeholder = placeholder.el;
				}
			} else setupRenderEffect(instance, initialVNode, container, anchor, parentSuspense, namespace, optimized);
		};
		const updateComponent = (n1, n2, optimized) => {
			const instance = n2.component = n1.component;
			if (shouldUpdateComponent(n1, n2, optimized)) {
				if (instance.asyncDep && !instance.asyncResolved) {
					n2.el = n1.el;
					updateComponentPreRender(instance, n2, optimized);
					return;
				} else {
					instance.next = n2;
					instance.update();
				}
			} else {
				n2.el = n1.el;
				instance.vnode = n2;
			}
		};
		const setupRenderEffect = (instance, initialVNode, container, anchor, parentSuspense, namespace, optimized) => {
			const componentUpdateFn = () => {
				if (!instance.isMounted) {
					let vnodeHook;
					const { el, props } = initialVNode;
					const { bm, m, parent, root, type } = instance;
					const isAsyncWrapperVNode = isAsyncWrapper(initialVNode);
					toggleRecurse(instance, false);
					if (bm) invokeArrayFns(bm);
					if (!isAsyncWrapperVNode && (vnodeHook = props && props.onVnodeBeforeMount)) invokeVNodeHook(vnodeHook, parent, initialVNode);
					toggleRecurse(instance, true);
					if (el && hydrateNode) {
						const hydrateSubTree = () => {
							instance.subTree = renderComponentRoot(instance);
							hydrateNode(el, instance.subTree, instance, parentSuspense, null);
						};
						if (isAsyncWrapperVNode && type.__asyncHydrate) type.__asyncHydrate(el, instance, hydrateSubTree);
						else hydrateSubTree();
					} else {
						if (root.ce && root.ce._hasShadowRoot()) root.ce._injectChildStyle(type, instance.parent ? instance.parent.type : void 0);
						const subTree = instance.subTree = renderComponentRoot(instance);
						patch(null, subTree, container, anchor, instance, parentSuspense, namespace);
						initialVNode.el = subTree.el;
					}
					if (m) queuePostRenderEffect(m, parentSuspense);
					if (!isAsyncWrapperVNode && (vnodeHook = props && props.onVnodeMounted)) {
						const scopedInitialVNode = initialVNode;
						queuePostRenderEffect(() => invokeVNodeHook(vnodeHook, parent, scopedInitialVNode), parentSuspense);
					}
					if (initialVNode.shapeFlag & 256 || parent && isAsyncWrapper(parent.vnode) && parent.vnode.shapeFlag & 256) instance.a && queuePostRenderEffect(instance.a, parentSuspense);
					instance.isMounted = true;
					initialVNode = container = anchor = null;
				} else {
					let { next, bu, u, parent, vnode } = instance;
					{
						const nonHydratedAsyncRoot = locateNonHydratedAsyncRoot(instance);
						if (nonHydratedAsyncRoot) {
							if (next) {
								next.el = vnode.el;
								updateComponentPreRender(instance, next, optimized);
							}
							nonHydratedAsyncRoot.asyncDep.then(() => {
								queuePostRenderEffect(() => {
									if (!instance.isUnmounted) update();
								}, parentSuspense);
							});
							return;
						}
					}
					let originNext = next;
					let vnodeHook;
					toggleRecurse(instance, false);
					if (next) {
						next.el = vnode.el;
						updateComponentPreRender(instance, next, optimized);
					} else next = vnode;
					if (bu) invokeArrayFns(bu);
					if (vnodeHook = next.props && next.props.onVnodeBeforeUpdate) invokeVNodeHook(vnodeHook, parent, next, vnode);
					toggleRecurse(instance, true);
					const nextTree = renderComponentRoot(instance);
					const prevTree = instance.subTree;
					instance.subTree = nextTree;
					patch(prevTree, nextTree, hostParentNode(prevTree.el), getNextHostNode(prevTree), instance, parentSuspense, namespace);
					next.el = nextTree.el;
					if (originNext === null) updateHOCHostEl(instance, nextTree.el);
					if (u) queuePostRenderEffect(u, parentSuspense);
					if (vnodeHook = next.props && next.props.onVnodeUpdated) queuePostRenderEffect(() => invokeVNodeHook(vnodeHook, parent, next, vnode), parentSuspense);
				}
			};
			instance.scope.on();
			const effect = instance.effect = new ReactiveEffect(componentUpdateFn);
			instance.scope.off();
			const update = instance.update = effect.run.bind(effect);
			const job = instance.job = effect.runIfDirty.bind(effect);
			job.i = instance;
			job.id = instance.uid;
			effect.scheduler = () => queueJob(job);
			toggleRecurse(instance, true);
			update();
		};
		const updateComponentPreRender = (instance, nextVNode, optimized) => {
			nextVNode.component = instance;
			const prevProps = instance.vnode.props;
			instance.vnode = nextVNode;
			instance.next = null;
			updateProps(instance, nextVNode.props, prevProps, optimized);
			updateSlots(instance, nextVNode.children, optimized);
			pauseTracking();
			flushPreFlushCbs(instance);
			resetTracking();
		};
		const patchChildren = (n1, n2, container, anchor, parentComponent, parentSuspense, namespace, slotScopeIds, optimized = false) => {
			const c1 = n1 && n1.children;
			const prevShapeFlag = n1 ? n1.shapeFlag : 0;
			const c2 = n2.children;
			const { patchFlag, shapeFlag } = n2;
			if (patchFlag > 0) {
				if (patchFlag & 128) {
					patchKeyedChildren(c1, c2, container, anchor, parentComponent, parentSuspense, namespace, slotScopeIds, optimized);
					return;
				} else if (patchFlag & 256) {
					patchUnkeyedChildren(c1, c2, container, anchor, parentComponent, parentSuspense, namespace, slotScopeIds, optimized);
					return;
				}
			}
			if (shapeFlag & 8) {
				if (prevShapeFlag & 16) unmountChildren(c1, parentComponent, parentSuspense);
				if (c2 !== c1) hostSetElementText(container, c2);
			} else if (prevShapeFlag & 16) {
				if (shapeFlag & 16) patchKeyedChildren(c1, c2, container, anchor, parentComponent, parentSuspense, namespace, slotScopeIds, optimized);
				else unmountChildren(c1, parentComponent, parentSuspense, true);
			} else {
				if (prevShapeFlag & 8) hostSetElementText(container, "");
				if (shapeFlag & 16) mountChildren(c2, container, anchor, parentComponent, parentSuspense, namespace, slotScopeIds, optimized);
			}
		};
		const patchUnkeyedChildren = (c1, c2, container, anchor, parentComponent, parentSuspense, namespace, slotScopeIds, optimized) => {
			c1 = c1 || EMPTY_ARR;
			c2 = c2 || EMPTY_ARR;
			const oldLength = c1.length;
			const newLength = c2.length;
			const commonLength = Math.min(oldLength, newLength);
			let i = 0;
			for (; i < commonLength; i++) {
				const nextChild = c2[i] = optimized ? cloneIfMounted(c2[i]) : normalizeVNode(c2[i]);
				patch(c1[i], nextChild, container, null, parentComponent, parentSuspense, namespace, slotScopeIds, optimized);
			}
			if (oldLength > newLength) unmountChildren(c1, parentComponent, parentSuspense, true, false, commonLength);
			else mountChildren(c2, container, anchor, parentComponent, parentSuspense, namespace, slotScopeIds, optimized, commonLength);
		};
		const patchKeyedChildren = (c1, c2, container, parentAnchor, parentComponent, parentSuspense, namespace, slotScopeIds, optimized) => {
			let i = 0;
			const l2 = c2.length;
			let e1 = c1.length - 1;
			let e2 = l2 - 1;
			while (i <= e1 && i <= e2) {
				const n1 = c1[i];
				const n2 = c2[i] = optimized ? cloneIfMounted(c2[i]) : normalizeVNode(c2[i]);
				if (isSameVNodeType(n1, n2)) patch(n1, n2, container, null, parentComponent, parentSuspense, namespace, slotScopeIds, optimized);
				else break;
				i++;
			}
			while (i <= e1 && i <= e2) {
				const n1 = c1[e1];
				const n2 = c2[e2] = optimized ? cloneIfMounted(c2[e2]) : normalizeVNode(c2[e2]);
				if (isSameVNodeType(n1, n2)) patch(n1, n2, container, null, parentComponent, parentSuspense, namespace, slotScopeIds, optimized);
				else break;
				e1--;
				e2--;
			}
			if (i > e1) {
				if (i <= e2) {
					const nextPos = e2 + 1;
					const anchor = nextPos < l2 ? c2[nextPos].el : parentAnchor;
					while (i <= e2) {
						patch(null, c2[i] = optimized ? cloneIfMounted(c2[i]) : normalizeVNode(c2[i]), container, anchor, parentComponent, parentSuspense, namespace, slotScopeIds, optimized);
						i++;
					}
				}
			} else if (i > e2) while (i <= e1) {
				unmount(c1[i], parentComponent, parentSuspense, true);
				i++;
			}
			else {
				const s1 = i;
				const s2 = i;
				const keyToNewIndexMap = new Map();
				for (i = s2; i <= e2; i++) {
					const nextChild = c2[i] = optimized ? cloneIfMounted(c2[i]) : normalizeVNode(c2[i]);
					if (nextChild.key != null) keyToNewIndexMap.set(nextChild.key, i);
				}
				let j;
				let patched = 0;
				const toBePatched = e2 - s2 + 1;
				let moved = false;
				let maxNewIndexSoFar = 0;
				const newIndexToOldIndexMap = new Array(toBePatched);
				for (i = 0; i < toBePatched; i++) newIndexToOldIndexMap[i] = 0;
				for (i = s1; i <= e1; i++) {
					const prevChild = c1[i];
					if (patched >= toBePatched) {
						unmount(prevChild, parentComponent, parentSuspense, true);
						continue;
					}
					let newIndex;
					if (prevChild.key != null) newIndex = keyToNewIndexMap.get(prevChild.key);
					else for (j = s2; j <= e2; j++) if (newIndexToOldIndexMap[j - s2] === 0 && isSameVNodeType(prevChild, c2[j])) {
						newIndex = j;
						break;
					}
					if (newIndex === void 0) unmount(prevChild, parentComponent, parentSuspense, true);
					else {
						newIndexToOldIndexMap[newIndex - s2] = i + 1;
						if (newIndex >= maxNewIndexSoFar) maxNewIndexSoFar = newIndex;
						else moved = true;
						patch(prevChild, c2[newIndex], container, null, parentComponent, parentSuspense, namespace, slotScopeIds, optimized);
						patched++;
					}
				}
				const increasingNewIndexSequence = moved ? getSequence(newIndexToOldIndexMap) : EMPTY_ARR;
				j = increasingNewIndexSequence.length - 1;
				for (i = toBePatched - 1; i >= 0; i--) {
					const nextIndex = s2 + i;
					const nextChild = c2[nextIndex];
					const anchorVNode = c2[nextIndex + 1];
					const anchor = nextIndex + 1 < l2 ? anchorVNode.el || resolveAsyncComponentPlaceholder(anchorVNode) : parentAnchor;
					if (newIndexToOldIndexMap[i] === 0) patch(null, nextChild, container, anchor, parentComponent, parentSuspense, namespace, slotScopeIds, optimized);
					else if (moved) {
						if (j < 0 || i !== increasingNewIndexSequence[j]) move(nextChild, container, anchor, 2);
						else j--;
					}
				}
			}
		};
		const move = (vnode, container, anchor, moveType, parentSuspense = null) => {
			const { el, type, transition, children, shapeFlag } = vnode;
			if (shapeFlag & 6) {
				move(vnode.component.subTree, container, anchor, moveType);
				return;
			}
			if (shapeFlag & 128) {
				vnode.suspense.move(container, anchor, moveType);
				return;
			}
			if (shapeFlag & 64) {
				type.move(vnode, container, anchor, internals);
				return;
			}
			if (type === Fragment) {
				hostInsert(el, container, anchor);
				for (let i = 0; i < children.length; i++) move(children[i], container, anchor, moveType);
				hostInsert(vnode.anchor, container, anchor);
				return;
			}
			if (type === Static) {
				moveStaticNode(vnode, container, anchor);
				return;
			}
			if (moveType !== 2 && shapeFlag & 1 && transition) {
				if (moveType === 0) {
					if (transition.persisted && !el[leaveCbKey]) hostInsert(el, container, anchor);
					else {
						transition.beforeEnter(el);
						hostInsert(el, container, anchor);
						queuePostRenderEffect(() => transition.enter(el), parentSuspense);
					}
				} else {
					const { leave, delayLeave, afterLeave } = transition;
					const remove2 = () => {
						if (vnode.ctx.isUnmounted) hostRemove(el);
						else hostInsert(el, container, anchor);
					};
					const performLeave = () => {
						const wasLeaving = el._isLeaving || !!el[leaveCbKey];
						if (el._isLeaving) el[leaveCbKey](true);
						if (transition.persisted && !wasLeaving) remove2();
						else leave(el, () => {
							remove2();
							afterLeave && afterLeave();
						});
					};
					if (delayLeave) delayLeave(el, remove2, performLeave);
					else performLeave();
				}
			} else hostInsert(el, container, anchor);
		};
		const unmount = (vnode, parentComponent, parentSuspense, doRemove = false, optimized = false) => {
			const { type, props, ref, children, dynamicChildren, shapeFlag, patchFlag, dirs, cacheIndex, memo } = vnode;
			if (patchFlag === -2 || dynamicChildren && dynamicChildren.hasOnce) optimized = false;
			if (ref != null) {
				pauseTracking();
				setRef(ref, null, parentSuspense, vnode, true);
				resetTracking();
			}
			if (cacheIndex != null && (!vnode.ctx || vnode.ctx === parentComponent)) parentComponent.renderCache[cacheIndex] = void 0;
			if (shapeFlag & 256) {
				parentComponent.ctx.deactivate(vnode);
				return;
			}
			const shouldInvokeDirs = shapeFlag & 1 && dirs;
			const shouldInvokeVnodeHook = !isAsyncWrapper(vnode);
			let vnodeHook;
			if (shouldInvokeVnodeHook && (vnodeHook = props && props.onVnodeBeforeUnmount)) invokeVNodeHook(vnodeHook, parentComponent, vnode);
			if (shapeFlag & 6) unmountComponent(vnode.component, parentSuspense, doRemove);
			else {
				if (shapeFlag & 128) {
					vnode.suspense.unmount(parentSuspense, doRemove);
					return;
				}
				if (shouldInvokeDirs) invokeDirectiveHook(vnode, null, parentComponent, "beforeUnmount");
				if (shapeFlag & 64) vnode.type.remove(vnode, parentComponent, parentSuspense, internals, doRemove);
				else if (dynamicChildren && !dynamicChildren.hasOnce && (type !== Fragment || patchFlag > 0 && patchFlag & 64)) unmountChildren(dynamicChildren, parentComponent, parentSuspense, false, true);
				else if (type === Fragment && patchFlag & 384 || !optimized && shapeFlag & 16) unmountChildren(children, parentComponent, parentSuspense);
				if (doRemove) remove(vnode);
			}
			const shouldInvalidateMemo = memo != null && cacheIndex == null;
			if (shouldInvokeVnodeHook && (vnodeHook = props && props.onVnodeUnmounted) || shouldInvokeDirs || shouldInvalidateMemo) queuePostRenderEffect(() => {
				vnodeHook && invokeVNodeHook(vnodeHook, parentComponent, vnode);
				shouldInvokeDirs && invokeDirectiveHook(vnode, null, parentComponent, "unmounted");
				if (shouldInvalidateMemo) vnode.el = null;
			}, parentSuspense);
		};
		const remove = (vnode) => {
			const { type, el, anchor, transition } = vnode;
			if (type === Fragment) {
				removeFragment(el, anchor);
				return;
			}
			if (type === Static) {
				removeStaticNode(vnode);
				if (transition && !transition.persisted && transition.afterLeave) transition.afterLeave();
				return;
			}
			const performRemove = () => {
				hostRemove(el);
				if (transition && !transition.persisted && transition.afterLeave) transition.afterLeave();
			};
			if (vnode.shapeFlag & 1 && transition && !transition.persisted) {
				const { leave, delayLeave } = transition;
				const performLeave = () => leave(el, performRemove);
				if (delayLeave) delayLeave(vnode.el, performRemove, performLeave);
				else performLeave();
			} else performRemove();
		};
		const removeFragment = (cur, end) => {
			let next;
			while (cur !== end) {
				next = hostNextSibling(cur);
				hostRemove(cur);
				cur = next;
			}
			hostRemove(end);
		};
		const unmountComponent = (instance, parentSuspense, doRemove) => {
			const { bum, scope, job, subTree, um, m, a } = instance;
			invalidateMount(m);
			invalidateMount(a);
			if (bum) invokeArrayFns(bum);
			scope.stop();
			if (job) {
				job.flags |= 8;
				unmount(subTree, instance, parentSuspense, doRemove);
			} else if (instance.vnode.el && subTree) {
				subTree.transition = instance.vnode.transition;
				unmount(subTree, instance, parentSuspense, doRemove);
			}
			if (um) queuePostRenderEffect(um, parentSuspense);
			queuePostRenderEffect(() => {
				instance.isUnmounted = true;
			}, parentSuspense);
		};
		const unmountChildren = (children, parentComponent, parentSuspense, doRemove = false, optimized = false, start = 0) => {
			for (let i = start; i < children.length; i++) unmount(children[i], parentComponent, parentSuspense, doRemove, optimized);
		};
		const getNextHostNode = (vnode) => {
			if (vnode.shapeFlag & 6) return getNextHostNode(vnode.component.subTree);
			if (vnode.shapeFlag & 128) return vnode.suspense.next();
			const el = hostNextSibling(vnode.anchor || vnode.el);
			const teleportEnd = el && el[TeleportEndKey];
			return teleportEnd ? hostNextSibling(teleportEnd) : el;
		};
		let isFlushing = false;
		const render = (vnode, container, namespace) => {
			let instance;
			if (vnode == null) {
				if (container._vnode) {
					unmount(container._vnode, null, null, true);
					instance = container._vnode.component;
				}
			} else patch(container._vnode || null, vnode, container, null, null, null, namespace);
			container._vnode = vnode;
			if (!isFlushing) {
				isFlushing = true;
				flushPreFlushCbs(instance);
				flushPostFlushCbs();
				isFlushing = false;
			}
		};
		const internals = {
			p: patch,
			um: unmount,
			m: move,
			r: remove,
			mt: mountComponent,
			mc: mountChildren,
			pc: patchChildren,
			pbc: patchBlockChildren,
			n: getNextHostNode,
			o: options
		};
		let hydrate;
		let hydrateNode;
		if (createHydrationFns) [hydrate, hydrateNode] = createHydrationFns(internals);
		return {
			render,
			hydrate,
			createApp: createAppAPI(render, hydrate)
		};
	}
	function resolveChildrenNamespace({ type, props }, currentNamespace) {
		return currentNamespace === "svg" && type === "foreignObject" || currentNamespace === "mathml" && type === "annotation-xml" && props && props.encoding && props.encoding.includes("html") ? void 0 : currentNamespace;
	}
	function toggleRecurse({ effect, job }, allowed) {
		if (allowed) {
			effect.flags |= 32;
			job.flags |= 4;
		} else {
			effect.flags &= -33;
			job.flags &= -5;
		}
	}
	function needTransition(parentSuspense, transition) {
		return (!parentSuspense || parentSuspense && !parentSuspense.pendingBranch) && transition && !transition.persisted;
	}
	function traverseStaticChildren(n1, n2, shallow = false) {
		const ch1 = n1.children;
		const ch2 = n2.children;
		if (isArray(ch1) && isArray(ch2)) for (let i = 0; i < ch1.length; i++) {
			const c1 = ch1[i];
			let c2 = ch2[i];
			if (c2.shapeFlag & 1 && !c2.dynamicChildren) {
				if (c2.patchFlag <= 0 || c2.patchFlag === 32) {
					c2 = ch2[i] = cloneIfMounted(ch2[i]);
					c2.el = c1.el;
				}
				if (!shallow && c2.patchFlag !== -2) traverseStaticChildren(c1, c2);
			}
			if (c2.type === Text) {
				if (c2.patchFlag === -1) c2 = ch2[i] = cloneIfMounted(c2);
				c2.el = c1.el;
			}
			if (c2.type === Comment && !c2.el) c2.el = c1.el;
		}
	}
	function getSequence(arr) {
		const p = arr.slice();
		const result = [0];
		let i, j, u, v, c;
		const len = arr.length;
		for (i = 0; i < len; i++) {
			const arrI = arr[i];
			if (arrI !== 0) {
				j = result[result.length - 1];
				if (arr[j] < arrI) {
					p[i] = j;
					result.push(i);
					continue;
				}
				u = 0;
				v = result.length - 1;
				while (u < v) {
					c = u + v >> 1;
					if (arr[result[c]] < arrI) u = c + 1;
					else v = c;
				}
				if (arrI < arr[result[u]]) {
					if (u > 0) p[i] = result[u - 1];
					result[u] = i;
				}
			}
		}
		u = result.length;
		v = result[u - 1];
		while (u-- > 0) {
			result[u] = v;
			v = p[v];
		}
		return result;
	}
	function locateNonHydratedAsyncRoot(instance) {
		const subComponent = instance.subTree.component;
		if (subComponent) {
			if (subComponent.asyncDep && !subComponent.asyncResolved) return subComponent;
			else return locateNonHydratedAsyncRoot(subComponent);
		}
	}
	function invalidateMount(hooks) {
		if (hooks) for (let i = 0; i < hooks.length; i++) hooks[i].flags |= 8;
	}
	function resolveAsyncComponentPlaceholder(anchorVnode) {
		if (anchorVnode.placeholder) return anchorVnode.placeholder;
		const instance = anchorVnode.component;
		if (instance) return resolveAsyncComponentPlaceholder(instance.subTree);
		return null;
	}
	var isSuspense = (type) => type.__isSuspense;
	function queueEffectWithSuspense(fn, suspense) {
		if (suspense && suspense.pendingBranch) {
			if (isArray(fn)) suspense.effects.push(...fn);
			else suspense.effects.push(fn);
		} else queuePostFlushCb(fn);
	}
	var Fragment = Symbol.for("v-fgt");
	var Text = Symbol.for("v-txt");
	var Comment = Symbol.for("v-cmt");
	var Static = Symbol.for("v-stc");
	var blockStack = [];
	var currentBlock = null;
	function openBlock(disableTracking = false) {
		blockStack.push(currentBlock = disableTracking ? null : []);
	}
	function closeBlock() {
		blockStack.pop();
		currentBlock = blockStack[blockStack.length - 1] || null;
	}
	var isBlockTreeEnabled = 1;
	function setBlockTracking(value, inVOnce = false) {
		isBlockTreeEnabled += value;
		if (value < 0 && currentBlock && inVOnce) currentBlock.hasOnce = true;
	}
	function setupBlock(vnode) {
		vnode.dynamicChildren = isBlockTreeEnabled > 0 ? currentBlock || EMPTY_ARR : null;
		closeBlock();
		if (isBlockTreeEnabled > 0 && currentBlock) currentBlock.push(vnode);
		return vnode;
	}
	function createElementBlock(type, props, children, patchFlag, dynamicProps, shapeFlag) {
		return setupBlock(createBaseVNode(type, props, children, patchFlag, dynamicProps, shapeFlag, true));
	}
	function createBlock(type, props, children, patchFlag, dynamicProps) {
		return setupBlock(createVNode(type, props, children, patchFlag, dynamicProps, true));
	}
	function isVNode(value) {
		return value ? value.__v_isVNode === true : false;
	}
	function isSameVNodeType(n1, n2) {
		return n1.type === n2.type && n1.key === n2.key;
	}
	var normalizeKey = ({ key }) => key != null ? key : null;
	var normalizeRef = ({ ref, ref_key, ref_for }) => {
		if (typeof ref === "number") ref = "" + ref;
		return ref != null ? isString(ref) || isRef(ref) || isFunction(ref) ? {
			i: currentRenderingInstance,
			r: ref,
			k: ref_key,
			f: !!ref_for
		} : ref : null;
	};
	function createBaseVNode(type, props = null, children = null, patchFlag = 0, dynamicProps = null, shapeFlag = type === Fragment ? 0 : 1, isBlockNode = false, needFullChildrenNormalization = false) {
		const vnode = {
			__v_isVNode: true,
			__v_skip: true,
			type,
			props,
			key: props && normalizeKey(props),
			ref: props && normalizeRef(props),
			scopeId: currentScopeId,
			slotScopeIds: null,
			children,
			component: null,
			suspense: null,
			ssContent: null,
			ssFallback: null,
			dirs: null,
			transition: null,
			el: null,
			anchor: null,
			target: null,
			targetStart: null,
			targetAnchor: null,
			staticCount: 0,
			shapeFlag,
			patchFlag,
			dynamicProps,
			dynamicChildren: null,
			appContext: null,
			ctx: currentRenderingInstance
		};
		if (needFullChildrenNormalization) {
			normalizeChildren(vnode, children);
			if (shapeFlag & 128) type.normalize(vnode);
		} else if (children) vnode.shapeFlag |= isString(children) ? 8 : 16;
		if (isBlockTreeEnabled > 0 && !isBlockNode && currentBlock && (vnode.patchFlag > 0 || shapeFlag & 6) && vnode.patchFlag !== 32) currentBlock.push(vnode);
		return vnode;
	}
	var createVNode = _createVNode;
	function _createVNode(type, props = null, children = null, patchFlag = 0, dynamicProps = null, isBlockNode = false) {
		if (!type || type === NULL_DYNAMIC_COMPONENT) type = Comment;
		if (isVNode(type)) {
			const cloned = cloneVNode(type, props, true);
			if (children) normalizeChildren(cloned, children);
			if (isBlockTreeEnabled > 0 && !isBlockNode && currentBlock) {
				if (cloned.shapeFlag & 6) currentBlock[currentBlock.indexOf(type)] = cloned;
				else currentBlock.push(cloned);
			}
			cloned.patchFlag = -2;
			return cloned;
		}
		if (isClassComponent(type)) type = type.__vccOpts;
		if (props) {
			props = guardReactiveProps(props);
			let { class: klass, style } = props;
			if (klass && !isString(klass)) props.class = normalizeClass(klass);
			if (isObject(style)) {
				if (isProxy(style) && !isArray(style)) style = extend({}, style);
				props.style = normalizeStyle(style);
			}
		}
		const shapeFlag = isString(type) ? 1 : isSuspense(type) ? 128 : isTeleport(type) ? 64 : isObject(type) ? 4 : isFunction(type) ? 2 : 0;
		return createBaseVNode(type, props, children, patchFlag, dynamicProps, shapeFlag, isBlockNode, true);
	}
	function guardReactiveProps(props) {
		if (!props) return null;
		return isProxy(props) || isInternalObject(props) ? extend({}, props) : props;
	}
	function cloneVNode(vnode, extraProps, mergeRef = false, cloneTransition = false) {
		const { props, ref, patchFlag, children, transition } = vnode;
		const mergedProps = extraProps ? mergeProps(props || {}, extraProps) : props;
		const cloned = {
			__v_isVNode: true,
			__v_skip: true,
			type: vnode.type,
			props: mergedProps,
			key: mergedProps && normalizeKey(mergedProps),
			ref: extraProps && extraProps.ref ? mergeRef && ref ? isArray(ref) ? ref.concat(normalizeRef(extraProps)) : [ref, normalizeRef(extraProps)] : normalizeRef(extraProps) : ref,
			scopeId: vnode.scopeId,
			slotScopeIds: vnode.slotScopeIds,
			children,
			target: vnode.target,
			targetStart: vnode.targetStart,
			targetAnchor: vnode.targetAnchor,
			staticCount: vnode.staticCount,
			shapeFlag: vnode.shapeFlag,
			patchFlag: extraProps && vnode.type !== Fragment ? patchFlag === -1 ? 16 : patchFlag | 16 : patchFlag,
			dynamicProps: vnode.dynamicProps,
			dynamicChildren: vnode.dynamicChildren,
			appContext: vnode.appContext,
			dirs: vnode.dirs,
			transition,
			component: vnode.component,
			suspense: vnode.suspense,
			ssContent: vnode.ssContent && cloneVNode(vnode.ssContent),
			ssFallback: vnode.ssFallback && cloneVNode(vnode.ssFallback),
			placeholder: vnode.placeholder,
			el: vnode.el,
			anchor: vnode.anchor,
			ctx: vnode.ctx,
			ce: vnode.ce,
			cacheIndex: vnode.cacheIndex
		};
		if (transition && cloneTransition) setTransitionHooks(cloned, transition.clone(cloned));
		return cloned;
	}
	function createTextVNode(text = " ", flag = 0) {
		return createVNode(Text, null, text, flag);
	}
	function createCommentVNode(text = "", asBlock = false) {
		return asBlock ? (openBlock(), createBlock(Comment, null, text)) : createVNode(Comment, null, text);
	}
	function normalizeVNode(child) {
		if (child == null || typeof child === "boolean") return createVNode(Comment);
		else if (isArray(child)) return createVNode(Fragment, null, child.slice());
		else if (isVNode(child)) return cloneIfMounted(child);
		else return createVNode(Text, null, String(child));
	}
	function cloneIfMounted(child) {
		return child.el === null && child.patchFlag !== -1 || child.memo ? child : cloneVNode(child);
	}
	function normalizeChildren(vnode, children) {
		let type = 0;
		const { shapeFlag } = vnode;
		if (children == null) children = null;
		else if (isArray(children)) type = 16;
		else if (typeof children === "object") {
			if (shapeFlag & 65) {
				const slot = children.default;
				if (slot) {
					slot._c && (slot._d = false);
					normalizeChildren(vnode, slot());
					slot._c && (slot._d = true);
				}
				return;
			} else {
				type = 32;
				const slotFlag = children._;
				if (!slotFlag && !isInternalObject(children)) children._ctx = currentRenderingInstance;
				else if (slotFlag === 3 && currentRenderingInstance) {
					if (currentRenderingInstance.slots._ === 1) children._ = 1;
					else {
						children._ = 2;
						vnode.patchFlag |= 1024;
					}
				}
			}
		} else if (isFunction(children)) {
			if (shapeFlag & 65) {
				normalizeChildren(vnode, { default: children });
				return;
			}
			children = {
				default: children,
				_ctx: currentRenderingInstance
			};
			type = 32;
		} else {
			children = String(children);
			if (shapeFlag & 64) {
				type = 16;
				children = [createTextVNode(children)];
			} else type = 8;
		}
		vnode.children = children;
		vnode.shapeFlag |= type;
	}
	function mergeProps(...args) {
		const ret = {};
		for (let i = 0; i < args.length; i++) {
			const toMerge = args[i];
			for (const key in toMerge) if (key === "class") {
				if (ret.class !== toMerge.class) ret.class = normalizeClass([ret.class, toMerge.class]);
			} else if (key === "style") ret.style = normalizeStyle([ret.style, toMerge.style]);
			else if (isOn(key)) {
				const existing = ret[key];
				const incoming = toMerge[key];
				if (incoming && existing !== incoming && !(isArray(existing) && existing.includes(incoming))) ret[key] = existing ? [].concat(existing, incoming) : incoming;
				else if (incoming == null && existing == null && !isModelListener(key)) ret[key] = incoming;
			} else if (key !== "") ret[key] = toMerge[key];
		}
		return ret;
	}
	function invokeVNodeHook(hook, instance, vnode, prevVNode = null) {
		callWithAsyncErrorHandling(hook, instance, 7, [vnode, prevVNode]);
	}
	var emptyAppContext = createAppContext();
	var uid = 0;
	function createComponentInstance(vnode, parent, suspense) {
		const type = vnode.type;
		const appContext = (parent ? parent.appContext : vnode.appContext) || emptyAppContext;
		const instance = {
			uid: uid++,
			vnode,
			type,
			parent,
			appContext,
			root: null,
			next: null,
			subTree: null,
			effect: null,
			update: null,
			job: null,
			scope: new EffectScope(true),
			render: null,
			proxy: null,
			exposed: null,
			exposeProxy: null,
			withProxy: null,
			provides: parent ? parent.provides : Object.create(appContext.provides),
			ids: parent ? parent.ids : [
				"",
				0,
				0
			],
			accessCache: null,
			renderCache: [],
			components: null,
			directives: null,
			propsOptions: normalizePropsOptions(type, appContext),
			emitsOptions: normalizeEmitsOptions(type, appContext),
			emit: null,
			emitted: null,
			propsDefaults: EMPTY_OBJ,
			inheritAttrs: type.inheritAttrs,
			ctx: EMPTY_OBJ,
			data: EMPTY_OBJ,
			props: EMPTY_OBJ,
			attrs: EMPTY_OBJ,
			slots: EMPTY_OBJ,
			refs: EMPTY_OBJ,
			setupState: EMPTY_OBJ,
			setupContext: null,
			suspense,
			suspenseId: suspense ? suspense.pendingId : 0,
			asyncDep: null,
			asyncResolved: false,
			isMounted: false,
			isUnmounted: false,
			isDeactivated: false,
			bc: null,
			c: null,
			bm: null,
			m: null,
			bu: null,
			u: null,
			um: null,
			bum: null,
			da: null,
			a: null,
			rtg: null,
			rtc: null,
			ec: null,
			sp: null
		};
		instance.ctx = { _: instance };
		instance.root = parent ? parent.root : instance;
		instance.emit = emit.bind(null, instance);
		if (vnode.ce) vnode.ce(instance);
		return instance;
	}
	var currentInstance = null;
	var getCurrentInstance = () => currentInstance || currentRenderingInstance;
	var internalSetCurrentInstance;
	var setInSSRSetupState;
	{
		const g = getGlobalThis();
		const registerGlobalSetter = (key, setter) => {
			let setters;
			if (!(setters = g[key])) setters = g[key] = [];
			setters.push(setter);
			return (v) => {
				if (setters.length > 1) setters.forEach((set) => set(v));
				else setters[0](v);
			};
		};
		internalSetCurrentInstance = registerGlobalSetter(`__VUE_INSTANCE_SETTERS__`, (v) => currentInstance = v);
		setInSSRSetupState = registerGlobalSetter(`__VUE_SSR_SETTERS__`, (v) => isInSSRComponentSetup = v);
	}
	var setCurrentInstance = (instance) => {
		const prev = currentInstance;
		internalSetCurrentInstance(instance);
		instance.scope.on();
		return () => {
			instance.scope.off();
			internalSetCurrentInstance(prev);
		};
	};
	var unsetCurrentInstance = () => {
		currentInstance && currentInstance.scope.off();
		internalSetCurrentInstance(null);
	};
	function isStatefulComponent(instance) {
		return instance.vnode.shapeFlag & 4;
	}
	var isInSSRComponentSetup = false;
	function setupComponent(instance, isSSR = false, optimized = false) {
		isSSR && setInSSRSetupState(isSSR);
		const { props, children } = instance.vnode;
		const isStateful = isStatefulComponent(instance);
		initProps(instance, props, isStateful, isSSR);
		initSlots(instance, children, optimized || isSSR);
		const setupResult = isStateful ? setupStatefulComponent(instance, isSSR) : void 0;
		isSSR && setInSSRSetupState(false);
		return setupResult;
	}
	function setupStatefulComponent(instance, isSSR) {
		const Component = instance.type;
		instance.accessCache = Object.create(null);
		instance.proxy = new Proxy(instance.ctx, PublicInstanceProxyHandlers);
		const { setup } = Component;
		if (setup) {
			pauseTracking();
			const setupContext = instance.setupContext = setup.length > 1 ? createSetupContext(instance) : null;
			const reset = setCurrentInstance(instance);
			const setupResult = callWithErrorHandling(setup, instance, 0, [instance.props, setupContext]);
			const isAsyncSetup = isPromise(setupResult);
			resetTracking();
			reset();
			if ((isAsyncSetup || instance.sp) && !isAsyncWrapper(instance)) markAsyncBoundary(instance);
			if (isAsyncSetup) {
				setupResult.then(unsetCurrentInstance, unsetCurrentInstance);
				if (isSSR) return setupResult.then((resolvedResult) => {
					setInSSRSetupState(true);
					try {
						handleSetupResult(instance, resolvedResult, isSSR);
					} finally {
						setInSSRSetupState(false);
					}
				}).catch((e) => {
					handleError(e, instance, 0);
				});
				else instance.asyncDep = setupResult;
			} else handleSetupResult(instance, setupResult, isSSR);
		} else finishComponentSetup(instance, isSSR);
	}
	function handleSetupResult(instance, setupResult, isSSR) {
		if (isFunction(setupResult)) {
			if (instance.type.__ssrInlineRender) instance.ssrRender = setupResult;
			else instance.render = setupResult;
		} else if (isObject(setupResult)) instance.setupState = proxyRefs(setupResult);
		finishComponentSetup(instance, isSSR);
	}
	var compile;
	var installWithProxy;
	function finishComponentSetup(instance, isSSR, skipOptions) {
		const Component = instance.type;
		if (!instance.render) {
			if (!isSSR && compile && !Component.render) {
				const template = Component.template || resolveMergedOptions(instance).template;
				if (template) {
					const { isCustomElement, compilerOptions } = instance.appContext.config;
					const { delimiters, compilerOptions: componentCompilerOptions } = Component;
					const finalCompilerOptions = extend(extend({
						isCustomElement,
						delimiters
					}, compilerOptions), componentCompilerOptions);
					Component.render = compile(template, finalCompilerOptions);
				}
			}
			instance.render = Component.render || NOOP;
			if (installWithProxy) installWithProxy(instance);
		}
		{
			const reset = setCurrentInstance(instance);
			pauseTracking();
			try {
				applyOptions(instance);
			} finally {
				resetTracking();
				reset();
			}
		}
	}
	var attrsProxyHandlers = { get(target, key) {
		track(target, "get", "");
		return target[key];
	} };
	function createSetupContext(instance) {
		const expose = (exposed) => {
			instance.exposed = exposed || {};
		};
		return {
			attrs: new Proxy(instance.attrs, attrsProxyHandlers),
			slots: instance.slots,
			emit: instance.emit,
			expose
		};
	}
	function getComponentPublicInstance(instance) {
		if (instance.exposed) return instance.exposeProxy || (instance.exposeProxy = new Proxy(proxyRefs(markRaw(instance.exposed)), {
			get(target, key) {
				if (key in target) return target[key];
				else if (key in publicPropertiesMap) return publicPropertiesMap[key](instance);
			},
			has(target, key) {
				return key in target || key in publicPropertiesMap;
			}
		}));
		else return instance.proxy;
	}
	function getComponentName(Component, includeInferred = true) {
		return isFunction(Component) ? Component.displayName || Component.name : Component.name || includeInferred && Component.__name;
	}
	function isClassComponent(value) {
		return isFunction(value) && "__vccOpts" in value;
	}
	var computed = (getterOrOptions, debugOptions) => {
		return computed$1(getterOrOptions, debugOptions, isInSSRComponentSetup);
	};
	var version = "3.5.43";
	//#endregion
	//#region node_modules/@vue/runtime-dom/dist/runtime-dom.esm-bundler.js
	var policy = void 0;
	var tt = typeof window !== "undefined" && window.trustedTypes;
	if (tt) try {
		policy = tt.createPolicy("vue", { createHTML: (val) => val });
	} catch (e) {}
	var unsafeToTrustedHTML = policy ? (val) => policy.createHTML(val) : (val) => val;
	var svgNS = "http://www.w3.org/2000/svg";
	var mathmlNS = "http://www.w3.org/1998/Math/MathML";
	var doc = typeof document !== "undefined" ? document : null;
	var templateContainer = doc && doc.createElement("template");
	var nodeOps = {
		insert: (child, parent, anchor) => {
			parent.insertBefore(child, anchor || null);
		},
		remove: (child) => {
			const parent = child.parentNode;
			if (parent) parent.removeChild(child);
		},
		createElement: (tag, namespace, is, props) => {
			const el = namespace === "svg" ? doc.createElementNS(svgNS, tag) : namespace === "mathml" ? doc.createElementNS(mathmlNS, tag) : is ? doc.createElement(tag, { is }) : doc.createElement(tag);
			if (tag === "select" && props && props.multiple != null) el.setAttribute("multiple", props.multiple);
			return el;
		},
		createText: (text) => doc.createTextNode(text),
		createComment: (text) => doc.createComment(text),
		setText: (node, text) => {
			node.nodeValue = text;
		},
		setElementText: (el, text) => {
			el.textContent = text;
		},
		parentNode: (node) => node.parentNode,
		nextSibling: (node) => node.nextSibling,
		querySelector: (selector) => doc.querySelector(selector),
		setScopeId(el, id) {
			el.setAttribute(id, "");
		},
		insertStaticContent(content, parent, anchor, namespace, start, end) {
			const before = anchor ? anchor.previousSibling : parent.lastChild;
			if (start && (start === end || start.nextSibling)) while (true) {
				parent.insertBefore(start.cloneNode(true), anchor);
				if (start === end || !(start = start.nextSibling)) break;
			}
			else {
				templateContainer.innerHTML = unsafeToTrustedHTML(namespace === "svg" ? `<svg>${content}</svg>` : namespace === "mathml" ? `<math>${content}</math>` : content);
				const template = templateContainer.content;
				if (namespace === "svg" || namespace === "mathml") {
					const wrapper = template.firstChild;
					while (wrapper.firstChild) template.appendChild(wrapper.firstChild);
					template.removeChild(wrapper);
				}
				parent.insertBefore(template, anchor);
			}
			return [before ? before.nextSibling : parent.firstChild, anchor ? anchor.previousSibling : parent.lastChild];
		}
	};
	var vtcKey = Symbol("_vtc");
	function patchClass(el, value, isSVG) {
		const transitionClasses = el[vtcKey];
		if (transitionClasses) value = (value ? [value, ...transitionClasses] : [...transitionClasses]).join(" ");
		if (value == null) el.removeAttribute("class");
		else if (isSVG) el.setAttribute("class", value);
		else el.className = value;
	}
	var vShowOriginalDisplay = Symbol("_vod");
	var vShowHidden = Symbol("_vsh");
	var vShow = {
		name: "show",
		beforeMount(el, { value }, { transition }) {
			el[vShowOriginalDisplay] = el.style.display === "none" ? "" : el.style.display;
			if (transition && value) transition.beforeEnter(el);
			else setDisplay(el, value);
		},
		mounted(el, { value }, { transition }) {
			if (transition && value) transition.enter(el);
		},
		updated(el, { value, oldValue }, { transition }) {
			if (!value === !oldValue) return;
			if (transition) {
				if (value) {
					transition.beforeEnter(el);
					setDisplay(el, true);
					transition.enter(el);
				} else transition.leave(el, () => {
					setDisplay(el, false);
				});
			} else setDisplay(el, value);
		},
		beforeUnmount(el, { value }) {
			setDisplay(el, value);
		}
	};
	function setDisplay(el, value) {
		el.style.display = value ? el[vShowOriginalDisplay] : "none";
		el[vShowHidden] = !value;
	}
	var CSS_VAR_TEXT = Symbol("");
	var displayRE = /(?:^|;)\s*display\s*:/;
	function patchStyle(el, prev, next) {
		const style = el.style;
		const isCssString = isString(next);
		let hasControlledDisplay = false;
		if (next && !isCssString) {
			if (prev) {
				if (!isString(prev)) {
					for (const key in prev) if (next[key] == null) setStyle(style, key, "");
				} else for (const prevStyle of prev.split(";")) {
					const key = prevStyle.slice(0, prevStyle.indexOf(":")).trim();
					if (next[key] == null) setStyle(style, key, "");
				}
			}
			for (const key in next) {
				if (key === "display") hasControlledDisplay = true;
				const value = next[key];
				if (value != null) {
					if (!shouldPreserveTextareaResizeStyle(el, key, !isString(prev) && prev ? prev[key] : void 0, value)) setStyle(style, key, value);
				} else setStyle(style, key, "");
			}
		} else if (isCssString) {
			if (prev !== next) {
				const cssVarText = style[CSS_VAR_TEXT];
				if (cssVarText) next += ";" + cssVarText;
				style.cssText = next;
				hasControlledDisplay = displayRE.test(next);
			}
		} else if (prev) el.removeAttribute("style");
		if (vShowOriginalDisplay in el) {
			el[vShowOriginalDisplay] = hasControlledDisplay ? style.display : "";
			if (el[vShowHidden]) style.display = "none";
		}
	}
	var importantRE = /\s*!important$/;
	function setStyle(style, name, val) {
		if (isArray(val)) val.forEach((v) => setStyle(style, name, v));
		else {
			if (val == null) val = "";
			if (name.startsWith("--")) {
				if (importantRE.test(val)) style.setProperty(name, val.replace(importantRE, ""), "important");
				else style.setProperty(name, val);
			} else {
				const prefixed = autoPrefix(style, name);
				if (importantRE.test(val)) style.setProperty(hyphenate(prefixed), val.replace(importantRE, ""), "important");
				else style[prefixed] = val;
			}
		}
	}
	var prefixes = [
		"Webkit",
		"Moz",
		"ms"
	];
	var prefixCache = {};
	function autoPrefix(style, rawName) {
		const cached = prefixCache[rawName];
		if (cached) return cached;
		let name = camelize(rawName);
		if (name !== "filter" && name in style) return prefixCache[rawName] = name;
		name = capitalize(name);
		for (let i = 0; i < prefixes.length; i++) {
			const prefixed = prefixes[i] + name;
			if (prefixed in style) return prefixCache[rawName] = prefixed;
		}
		return rawName;
	}
	function shouldPreserveTextareaResizeStyle(el, key, prev, next) {
		return el.tagName === "TEXTAREA" && (key === "width" || key === "height") && isString(next) && prev === next;
	}
	var xlinkNS = "http://www.w3.org/1999/xlink";
	function patchAttr(el, key, value, isSVG, instance, isBoolean = isSpecialBooleanAttr(key)) {
		if (isSVG && key.startsWith("xlink:")) {
			if (value == null) el.removeAttributeNS(xlinkNS, key.slice(6, key.length));
			else el.setAttributeNS(xlinkNS, key, value);
		} else if (value == null || isBoolean && !includeBooleanAttr(value)) el.removeAttribute(key);
		else el.setAttribute(key, isBoolean ? "" : isSymbol(value) ? String(value) : value);
	}
	function patchDOMProp(el, key, value, parentComponent, attrName) {
		if (key === "innerHTML" || key === "textContent") {
			if (value != null) el[key] = key === "innerHTML" ? unsafeToTrustedHTML(value) : value;
			return;
		}
		const tag = el.tagName;
		if (key === "value" && tag !== "PROGRESS" && !tag.includes("-")) {
			const oldValue = tag === "OPTION" ? el.getAttribute("value") || "" : el.value;
			const newValue = value == null ? el.type === "checkbox" ? "on" : "" : String(value);
			if (oldValue !== newValue || !("_value" in el)) el.value = newValue;
			if (value == null) el.removeAttribute(key);
			el._value = value;
			return;
		}
		let needRemove = false;
		if (value === "" || value == null) {
			const type = typeof el[key];
			if (type === "boolean") value = includeBooleanAttr(value);
			else if (value == null && type === "string") {
				value = "";
				needRemove = true;
			} else if (type === "number") {
				value = 0;
				needRemove = true;
			}
		}
		try {
			el[key] = value;
		} catch (e) {}
		needRemove && el.removeAttribute(attrName || key);
	}
	function addEventListener$1(el, event, handler, options) {
		el.addEventListener(event, handler, options);
	}
	function removeEventListener(el, event, handler, options) {
		el.removeEventListener(event, handler, options);
	}
	var veiKey = Symbol("_vei");
	function patchEvent(el, rawName, prevValue, nextValue, instance = null) {
		const invokers = el[veiKey] || (el[veiKey] = {});
		const existingInvoker = invokers[rawName];
		if (nextValue && existingInvoker) existingInvoker.value = nextValue;
		else {
			const [name, options] = parseName(rawName);
			if (nextValue) addEventListener$1(el, name, invokers[rawName] = createInvoker(nextValue, instance), options);
			else if (existingInvoker) {
				removeEventListener(el, name, existingInvoker, options);
				invokers[rawName] = void 0;
			}
		}
	}
	var optionsModifierRE = /(Once|Passive|Capture)$/;
	var optionsModifierEventRE = /^on:?(?:Once|Passive|Capture)$/;
	function parseName(name) {
		let options;
		let m;
		while ((m = name.match(optionsModifierRE)) && !optionsModifierEventRE.test(name)) {
			if (!options) options = {};
			name = name.slice(0, name.length - m[1].length);
			options[m[1].toLowerCase()] = true;
		}
		return [name[2] === ":" ? name.slice(3) : hyphenate(name.slice(2)), options];
	}
	var cachedNow = 0;
	var p = Promise.resolve();
	var getNow = () => cachedNow || (p.then(() => cachedNow = 0), cachedNow = Date.now());
	function createInvoker(initialValue, instance) {
		const invoker = (e) => {
			if (!e._vts) e._vts = Date.now();
			else if (e._vts <= invoker.attached) return;
			const value = invoker.value;
			if (isArray(value)) {
				const originalStop = e.stopImmediatePropagation;
				e.stopImmediatePropagation = () => {
					originalStop.call(e);
					e._stopped = true;
				};
				const handlers = value.slice();
				const args = [e];
				for (let i = 0; i < handlers.length; i++) {
					if (e._stopped) break;
					const handler = handlers[i];
					if (handler) callWithAsyncErrorHandling(handler, instance, 5, args);
				}
			} else callWithAsyncErrorHandling(value, instance, 5, [e]);
		};
		invoker.value = initialValue;
		invoker.attached = getNow();
		return invoker;
	}
	var isNativeOn = (key) => key.charCodeAt(0) === 111 && key.charCodeAt(1) === 110 && key.charCodeAt(2) > 96 && key.charCodeAt(2) < 123;
	var patchProp = (el, key, prevValue, nextValue, namespace, parentComponent) => {
		const isSVG = namespace === "svg";
		if (key === "class") patchClass(el, nextValue, isSVG);
		else if (key === "style") patchStyle(el, prevValue, nextValue);
		else if (isOn(key)) {
			if (!isModelListener(key)) patchEvent(el, key, prevValue, nextValue, parentComponent);
		} else if (key[0] === "." ? (key = key.slice(1), true) : key[0] === "^" ? (key = key.slice(1), false) : shouldSetAsProp(el, key, nextValue, isSVG)) {
			patchDOMProp(el, key, nextValue);
			if (!el.tagName.includes("-") && (key === "value" || key === "checked" || key === "selected")) patchAttr(el, key, nextValue, isSVG, parentComponent, key !== "value");
		} else if (el._isVueCE && (shouldSetAsPropForVueCE(el, key) || el._def.__asyncLoader && (/[A-Z]/.test(key) || !isString(nextValue)))) patchDOMProp(el, camelize(key), nextValue, parentComponent, key);
		else {
			if (key === "true-value") el._trueValue = nextValue;
			else if (key === "false-value") el._falseValue = nextValue;
			patchAttr(el, key, nextValue, isSVG);
		}
	};
	function shouldSetAsProp(el, key, value, isSVG) {
		if (isSVG) {
			if (key === "innerHTML" || key === "textContent") return true;
			if (key in el && isNativeOn(key) && isFunction(value)) return true;
			return false;
		}
		if (key === "spellcheck" || key === "draggable" || key === "translate" || key === "autocorrect") return false;
		if (key === "sandbox" && el.tagName === "IFRAME") return false;
		if (key === "form") return false;
		if (key === "list" && el.tagName === "INPUT") return false;
		if (key === "type" && el.tagName === "TEXTAREA") return false;
		if (key === "width" || key === "height") {
			const tag = el.tagName;
			if (tag === "IMG" || tag === "VIDEO" || tag === "CANVAS" || tag === "SOURCE") return false;
		}
		if (isNativeOn(key) && isString(value)) return false;
		return key in el;
	}
	function shouldSetAsPropForVueCE(el, key) {
		const props = el._def.props;
		if (!props) return false;
		const camelKey = camelize(key);
		return Array.isArray(props) ? props.some((prop) => camelize(prop) === camelKey) : Object.keys(props).some((prop) => camelize(prop) === camelKey);
	}
	var systemModifiers = [
		"ctrl",
		"shift",
		"alt",
		"meta"
	];
	var modifierGuards = {
		stop: (e) => e.stopPropagation(),
		prevent: (e) => e.preventDefault(),
		self: (e) => e.target !== e.currentTarget,
		ctrl: (e) => !e.ctrlKey,
		shift: (e) => !e.shiftKey,
		alt: (e) => !e.altKey,
		meta: (e) => !e.metaKey,
		left: (e) => "button" in e && e.button !== 0,
		middle: (e) => "button" in e && e.button !== 1,
		right: (e) => "button" in e && e.button !== 2,
		exact: (e, modifiers) => systemModifiers.some((m) => e[`${m}Key`] && !modifiers.includes(m))
	};
	var withModifiers = (fn, modifiers) => {
		if (!fn) return fn;
		const cache = fn._withMods || (fn._withMods = {});
		const cacheKey = modifiers.join(".");
		return cache[cacheKey] || (cache[cacheKey] = ((event, ...args) => {
			for (let i = 0; i < modifiers.length; i++) {
				const guard = modifierGuards[modifiers[i]];
				if (guard && guard(event, modifiers)) return;
			}
			return fn(event, ...args);
		}));
	};
	var keyNames = {
		esc: "escape",
		space: " ",
		up: "arrow-up",
		left: "arrow-left",
		right: "arrow-right",
		down: "arrow-down",
		delete: "backspace"
	};
	var withKeys = (fn, modifiers) => {
		const cache = fn._withKeys || (fn._withKeys = {});
		const cacheKey = modifiers.join(".");
		return cache[cacheKey] || (cache[cacheKey] = ((event) => {
			if (!("key" in event)) return;
			const eventKey = hyphenate(event.key);
			if (modifiers.some((k) => k === eventKey || keyNames[k] === eventKey)) return fn(event);
		}));
	};
	var rendererOptions = extend({ patchProp }, nodeOps);
	var renderer;
	function ensureRenderer() {
		return renderer || (renderer = createRenderer(rendererOptions));
	}
	var createApp = ((...args) => {
		const app = ensureRenderer().createApp(...args);
		const { mount } = app;
		app.mount = (containerOrSelector) => {
			const container = normalizeContainer(containerOrSelector);
			if (!container) return;
			const component = app._component;
			if (!isFunction(component) && !component.render && !component.template) component.template = container.innerHTML;
			if (container.nodeType === 1) container.textContent = "";
			const proxy = mount(container, false, resolveRootNamespace(container));
			if (container instanceof Element) {
				container.removeAttribute("v-cloak");
				container.setAttribute("data-v-app", "");
			}
			return proxy;
		};
		return app;
	});
	function resolveRootNamespace(container) {
		if (container instanceof SVGElement) return "svg";
		if (typeof MathMLElement === "function" && container instanceof MathMLElement) return "mathml";
	}
	function normalizeContainer(container) {
		if (isString(container)) return document.querySelector(container);
		return container;
	}
	//#endregion
	//#region \0plugin-vue:export-helper
	var _plugin_vue_export_helper_default = (sfc, props) => {
		const target = sfc.__vccOpts || sfc;
		for (const [key, val] of props) target[key] = val;
		return target;
	};
	//#endregion
	//#region src/components/Timeline.vue
	var _sfc_main$6 = {
		props: {
			period: { required: true },
			currentSnapshot: {
				required: false,
				default: null
			},
			highlight: {
				required: false,
				default: false
			},
			stayWithinPeriod: {
				required: false,
				default: false
			},
			maxZoomLevel: {
				required: false,
				default: PywbPeriod.Type.snapshot
			}
		},
		emits: ["goto-period"],
		data: function() {
			return {
				highlightPeriod: null,
				previousPeriod: null,
				nextPeriod: null,
				isScrollZero: true,
				isScrollMax: true,
				tooltipPeriod: null,
				tooltipPeriodPos: {
					x: 0,
					y: 0
				}
			};
		},
		created: function() {
			this.addEmptySubPeriods();
		},
		mounted: function() {
			this.$refs.periods._computedStyle = window.getComputedStyle(this.$refs.periods);
			this.$refs.periodScroll._computedStyle = window.getComputedStyle(this.$refs.periodScroll);
			this.$watch("period", this.onPeriodChanged);
			this.$refs.periodScroll.addEventListener("scroll", this.updateScrollArrows);
			window.addEventListener("resize", this.updateScrollArrows);
			this.updateScrollArrows();
		},
		computed: {
			canZoom() {
				return this.period.type < this.maxZoomLevel;
			},
			isTooltipPeriodDayOrHour() {
				return this.tooltipPeriod.type >= PywbPeriod.Type.day;
			},
			iContainCurrentSnapshot() {
				return this.currentSnapshot && this.period.contains(this.currentSnapshot);
			}
		},
		updated() {},
		methods: {
			containsCurrentSnapshot(period) {
				return this.iContainCurrentSnapshot && period.contains(this.currentSnapshot);
			},
			addEmptySubPeriods() {
				this.period.fillEmptyChildPeriods(true);
			},
			updateScrollArrows() {
				this.period.scroll = this.$refs.periodScroll.scrollLeft;
				const maxScroll = parseInt(this.$refs.periods._computedStyle.width) - parseInt(this.$refs.periodScroll._computedStyle.width);
				this.isScrollZero = !this.period.scroll;
				this.isScrollMax = Math.abs(maxScroll - this.period.scroll) < 5;
			},
			restoreScroll() {
				this.$refs.periodScroll.scrollLeft = this.period.scroll;
			},
			scrollNext: function() {
				if (this.isScrollMax) {
					if (this.nextPeriod) this.$emit("goto-period", this.nextPeriod, true);
				} else this.$refs.periodScroll.scrollLeft += 30;
			},
			scrollPrev: function() {
				if (this.isScrollZero) {
					if (this.previousPeriod) this.$emit("goto-period", this.previousPeriod, true);
				} else this.$refs.periodScroll.scrollLeft -= 30;
			},
			getTimeFormatted: function(date) {
				return (date.hour < 13 ? date.hour : date.hour % 12) + ":" + ((date.minute < 10 ? "0" : "") + date.minute) + " " + (date.hour < 12 ? "am" : "pm");
			},
			getHistoLineHeight: function(value) {
				const percent = Math.ceil(value / this.period.maxGrandchildSnapshotCount * 100);
				return (percent ? 5 + Math.ceil(percent * .95) : 0) + "%";
			},
			changePeriod(period, $event) {
				if (period.snapshotCount) {
					let periodToChangeTo = null;
					if (period.snapshot) {
						if (period.type === PywbPeriod.Type.snapshot) periodToChangeTo = period;
						else if (period.snapshotPeriod) periodToChangeTo = period.snapshotPeriod;
					} else if (this.canZoom) periodToChangeTo = period;
					if (periodToChangeTo) this.$emit("goto-period", periodToChangeTo);
				}
				$event.stopPropagation();
				return false;
			},
			onPeriodChanged(newPeriod, oldPeriod) {
				this.addEmptySubPeriods();
				const previousPeriod = this.period.getPrevious();
				const nextPeriod = this.period.getNext();
				if (!this.stayWithinPeriod || this.stayWithinPeriod.contains(previousPeriod)) this.previousPeriod = previousPeriod;
				if (!this.stayWithinPeriod || this.stayWithinPeriod.contains(nextPeriod)) this.nextPeriod = nextPeriod;
				if (oldPeriod && oldPeriod.type - newPeriod.type > 0) {
					let highlightPeriod = oldPeriod;
					for (let i = oldPeriod.type - newPeriod.type; i > 1; i--) highlightPeriod = highlightPeriod.parent;
					this.highlightPeriod = highlightPeriod;
					setTimeout((function() {
						this.highlightPeriod = null;
					}).bind(this), 2e3);
				}
				setTimeout((function() {
					this.restoreScroll();
					this.updateScrollArrows();
				}).bind(this), 1);
			},
			setTooltipPeriod(period, event) {
				if (!period || !period.snapshotCount) {
					this.tooltipPeriod = null;
					return;
				}
				this.tooltipPeriod = period;
				this.$nextTick(function() {
					const tooltipContentsEl = document.querySelector(".period-tooltip div");
					if (!tooltipContentsEl) return;
					const periodTooltipStyle = window.getComputedStyle(tooltipContentsEl);
					const tooltipWidth = parseInt(periodTooltipStyle.width);
					const tooltipHeight = parseInt(periodTooltipStyle.height);
					const spacing = 10;
					if (window.innerWidth < event.x + 20 + tooltipWidth) this.tooltipPeriodPos.x = event.x - (tooltipWidth + spacing);
					else this.tooltipPeriodPos.x = event.x + spacing;
					this.tooltipPeriodPos.y = event.y - (spacing + tooltipHeight);
				});
				event.stopPropagation();
				return false;
			}
		}
	};
	var _hoisted_1$6 = { class: "timeline" };
	var _hoisted_2$5 = { key: 0 };
	var _hoisted_3$5 = { key: 1 };
	var _hoisted_4$4 = { key: 2 };
	var _hoisted_5$3 = {
		class: "periods",
		ref: "periods"
	};
	var _hoisted_6$2 = { class: "histo" };
	var _hoisted_7$2 = [
		"onClick",
		"onKeyup",
		"onMouseover",
		"tabindex"
	];
	var _hoisted_8$1 = ["onClick", "onMouseover"];
	var _hoisted_9$1 = { class: "label" };
	function _sfc_render$6(_ctx, _cache, $props, $setup, $data, $options) {
		return openBlock(), createElementBlock("div", _hoisted_1$6, [
			withDirectives(createBaseVNode("div", {
				class: "period-tooltip",
				style: normalizeStyle({
					left: _ctx.tooltipPeriodPos.x + "px",
					top: _ctx.tooltipPeriodPos.y + "px"
				})
			}, [_ctx.tooltipPeriod ? (openBlock(), createElementBlock(Fragment, { key: 0 }, [_ctx.tooltipPeriod.snapshot ? (openBlock(), createElementBlock("div", _hoisted_2$5, toDisplayString(_ctx.$_("View capture on {date}", { date: _ctx.tooltipPeriod.snapshot.getTimeDateFormatted() })), 1)) : _ctx.tooltipPeriod.snapshotPeriod ? (openBlock(), createElementBlock("div", _hoisted_3$5, toDisplayString(_ctx.$_("View capture on {date}", { date: _ctx.tooltipPeriod.snapshotPeriod.snapshot.getTimeDateFormatted() })), 1)) : _ctx.tooltipPeriod.snapshotCount ? (openBlock(), createElementBlock("div", _hoisted_4$4, toDisplayString(_ctx.$_($options.isTooltipPeriodDayOrHour ? "{capture_text} on {date}" : "{capture_text} in {month}", {
				capture_text: _ctx.$_(_ctx.tooltipPeriod.snapshotCount !== 1 ? "{count} captures" : "{count} capture", { count: _ctx.tooltipPeriod.snapshotCount }),
				[$options.isTooltipPeriodDayOrHour ? "date" : "month"]: _ctx.tooltipPeriod.getFullReadableId()
			})), 1)) : createCommentVNode("", true)], 64)) : createCommentVNode("", true)], 4), [[vShow, _ctx.tooltipPeriod]]),
			_cache[10] || (_cache[10] = createTextVNode()),
			createBaseVNode("div", {
				innerHTML: "\u25C0",
				class: normalizeClass(["arrow previous", { disabled: _ctx.isScrollZero && !_ctx.previousPeriod }]),
				onClick: _cache[0] || (_cache[0] = (...args) => $options.scrollPrev && $options.scrollPrev(...args)),
				onKeyup: _cache[1] || (_cache[1] = withKeys((...args) => $options.scrollPrev && $options.scrollPrev(...args), ["enter"])),
				onDblclick: _cache[2] || (_cache[2] = withModifiers(() => {}, ["stop", "prevent"])),
				tabindex: "0"
			}, null, 34),
			_cache[11] || (_cache[11] = createTextVNode()),
			createBaseVNode("div", {
				class: normalizeClass(["scroll", { highlight: $props.highlight }]),
				ref: "periodScroll"
			}, [createBaseVNode("div", _hoisted_5$3, [(openBlock(true), createElementBlock(Fragment, null, renderList($props.period.children, (subPeriod) => {
				return openBlock(), createElementBlock("div", {
					key: subPeriod.fullId,
					class: normalizeClass(["period", {
						empty: !subPeriod.snapshotCount,
						highlight: _ctx.highlightPeriod === subPeriod,
						"last-level": !$options.canZoom,
						"contains-current-snapshot": $options.containsCurrentSnapshot(subPeriod)
					}])
				}, [
					createBaseVNode("div", _hoisted_6$2, [(openBlock(true), createElementBlock(Fragment, null, renderList(subPeriod.children, (histoPeriod) => {
						return openBlock(), createElementBlock("div", {
							class: normalizeClass(["line", {
								"has-single-snapshot": histoPeriod.snapshotCount === 1,
								"contains-current-snapshot": $options.containsCurrentSnapshot(histoPeriod)
							}]),
							key: histoPeriod.fullId,
							style: normalizeStyle({ height: $options.getHistoLineHeight(histoPeriod.snapshotCount) }),
							onClick: ($event) => $options.changePeriod(histoPeriod, $event),
							onKeyup: withKeys(($event) => $options.changePeriod(histoPeriod, $event), ["enter"]),
							onMouseover: ($event) => $options.setTooltipPeriod(histoPeriod, $event),
							onMouseout: _cache[3] || (_cache[3] = ($event) => $options.setTooltipPeriod(null, $event)),
							tabindex: histoPeriod.snapshotCount > 0 ? 0 : -1
						}, null, 46, _hoisted_7$2);
					}), 128))]),
					_cache[9] || (_cache[9] = createTextVNode()),
					createBaseVNode("div", {
						class: normalizeClass(["inner", { "has-single-snapshot": subPeriod.snapshotCount === 1 }]),
						onClick: ($event) => $options.changePeriod(subPeriod, $event),
						onKeyup: _cache[4] || (_cache[4] = withKeys(($event) => $options.changePeriod(_ctx.histoPeriod, $event), ["enter"])),
						onMouseover: ($event) => $options.setTooltipPeriod(subPeriod, $event),
						onMouseout: _cache[5] || (_cache[5] = ($event) => $options.setTooltipPeriod(null, $event))
					}, [createBaseVNode("div", _hoisted_9$1, toDisplayString(subPeriod.getReadableId()), 1)], 42, _hoisted_8$1)
				], 2);
			}), 128))], 512)], 2),
			_cache[12] || (_cache[12] = createTextVNode()),
			createBaseVNode("div", {
				innerHTML: "\u25B6",
				class: normalizeClass(["arrow next", { disabled: _ctx.isScrollMax && !_ctx.nextPeriod }]),
				onClick: _cache[6] || (_cache[6] = (...args) => $options.scrollNext && $options.scrollNext(...args)),
				onKeyup: _cache[7] || (_cache[7] = withKeys((...args) => $options.scrollNext && $options.scrollNext(...args), ["enter"])),
				onDblclick: _cache[8] || (_cache[8] = withModifiers(() => {}, ["stop", "prevent"])),
				tabindex: "0"
			}, null, 34)
		]);
	}
	var Timeline_default = _plugin_vue_export_helper_default(_sfc_main$6, [["render", _sfc_render$6]]);
	//#endregion
	//#region src/components/TimelineBreadcrumbs.vue
	var _sfc_main$5 = {
		props: { period: { required: true } },
		emits: ["goto-period"],
		computed: { parents: function() {
			return this.period.getParents();
		} },
		methods: {
			getPeriodZoomOutText(period) {
				return PywbI18N.instance._("Zoom out to {id} ({count} captures)", {
					id: period.getReadableId(true),
					count: period.snapshotCount
				});
			},
			changePeriod(period) {
				if (period.snapshotCount) this.$emit("goto-period", period);
			}
		}
	};
	var _hoisted_1$5 = { class: "breadcrumbs" };
	var _hoisted_2$4 = { class: "item" };
	var _hoisted_3$4 = ["title"];
	var _hoisted_4$3 = [
		"onClick",
		"onKeyup",
		"title"
	];
	var _hoisted_5$2 = { class: "item" };
	var _hoisted_6$1 = { class: "current" };
	var _hoisted_7$1 = { class: "count" };
	function _sfc_render$5(_ctx, _cache, $props, $setup, $data, $options) {
		return openBlock(), createElementBlock("div", _hoisted_1$5, [
			$options.parents.length ? (openBlock(), createElementBlock(Fragment, { key: 0 }, [
				createBaseVNode("span", _hoisted_2$4, [createBaseVNode("span", {
					class: "goto",
					onClick: _cache[0] || (_cache[0] = ($event) => $options.changePeriod($options.parents[0])),
					onKeyup: _cache[1] || (_cache[1] = withKeys(($event) => $options.changePeriod($options.parents[0]), ["enter"])),
					title: $options.getPeriodZoomOutText($options.parents[0]),
					tabindex: "1"
				}, [_cache[2] || (_cache[2] = createBaseVNode("i", { class: "fa fa-search-minus" }, null, -1)), createTextVNode(" " + toDisplayString($options.parents[0].getReadableId(true)), 1)], 40, _hoisted_3$4)]),
				_cache[3] || (_cache[3] = createTextVNode("\n            >\n            ", -1)),
				(openBlock(true), createElementBlock(Fragment, null, renderList($options.parents.slice(1), (parent) => {
					return openBlock(), createElementBlock("span", {
						key: parent.id,
						class: "item"
					}, [createBaseVNode("span", {
						class: "goto",
						onClick: ($event) => $options.changePeriod(parent),
						onKeyup: withKeys(($event) => $options.changePeriod(parent), ["enter"]),
						title: $options.getPeriodZoomOutText(parent),
						tabindex: "1"
					}, toDisplayString(parent.getReadableId(true)), 41, _hoisted_4$3)]);
				}), 128))
			], 64)) : createCommentVNode("", true),
			_cache[5] || (_cache[5] = createTextVNode()),
			createBaseVNode("span", _hoisted_5$2, [
				createBaseVNode("span", _hoisted_6$1, toDisplayString($props.period.getReadableId(true)), 1),
				_cache[4] || (_cache[4] = createTextVNode()),
				createBaseVNode("span", _hoisted_7$1, "(" + toDisplayString(_ctx.$_($props.period.snapshotCount !== 1 ? "{count} captures" : "{count} capture", { count: $props.period.snapshotCount })) + ")", 1)
			])
		]);
	}
	var TimelineBreadcrumbs_default = _plugin_vue_export_helper_default(_sfc_main$5, [["render", _sfc_render$5]]);
	//#endregion
	//#region src/components/CalendarMonth.vue
	var _sfc_main$4 = {
		props: [
			"month",
			"year",
			"isCurrent",
			"yearContainsCurrentSnapshot",
			"currentSnapshot"
		],
		emits: ["show-day-timeline"],
		data: function() {
			return {
				maxInDay: 0,
				daySize: 30
			};
		},
		computed: {
			dayInitials() {
				return PywbI18N.instance.getWeekDays().map((d) => d.substr(0, 1));
			},
			dayStyle() {
				const s = this.daySize;
				return `height: ${s}px; width: ${s}px; line-height: ${s}px`;
			},
			days() {
				if (!this.month) return [];
				const days = [];
				const [firstDay, lastDay] = this.month.getChildrenRange();
				const daysBeforeFirst = (7 + new Date(this.year.id, this.month.id - 1, firstDay).getDay() - PywbI18N.firstDayOfWeek) % 7;
				const daysAfterLastDay = (6 - new Date(this.year.id, this.month.id - 1, lastDay).getDay() + PywbI18N.firstDayOfWeek) % 7;
				for (let i = 0; i < daysBeforeFirst; i++) days.push(null);
				const hasChildren = !!this.month.children.length;
				for (let i = 0; i < lastDay; i++) days.push(hasChildren ? this.month.children[i] : null);
				for (let i = 0; i < daysAfterLastDay; i++) days.push(null);
				return days;
			},
			containsCurrentSnapshot() {
				return this.currentSnapshot && this.month.contains(this.currentSnapshot);
			}
		},
		methods: {
			getLongMonthName(id) {
				return PywbI18N.instance.getMonth(id);
			},
			gotoDay(day, event) {
				if (!day || !day.snapshotCount) return;
				this.$emit("show-day-timeline", day, event);
			},
			getDayCountCircleStyle(snapshotCount) {
				const size = Math.ceil(snapshotCount / this.year.maxGrandchildSnapshotCount * this.daySize);
				const scaledSize = size ? this.daySize * .3 + Math.ceil(size * .7) : 0;
				const margin = (this.daySize - scaledSize) / 2;
				return `width: ${scaledSize}px; height: ${scaledSize}px; top: ${margin}px; left: ${margin}px; border-radius: ${scaledSize / 2}px;`;
			},
			dayContainsCurrentSnapshot(day) {
				return !!day && day.snapshotCount > 0 && this.containsCurrentSnapshot && day.contains(this.currentSnapshot);
			}
		}
	};
	var _hoisted_1$4 = { key: 0 };
	var _hoisted_2$3 = { key: 0 };
	var _hoisted_3$3 = ["onClick", "onKeyup"];
	var _hoisted_4$2 = {
		key: 1,
		class: "count"
	};
	function _sfc_render$4(_ctx, _cache, $props, $setup, $data, $options) {
		return openBlock(), createElementBlock("div", { class: normalizeClass(["calendar-month", {
			current: $props.isCurrent,
			"contains-current-snapshot": $options.containsCurrentSnapshot
		}]) }, [
			createBaseVNode("h3", null, [createTextVNode(toDisplayString($options.getLongMonthName($props.month.id)) + " ", 1), $props.month.snapshotCount ? (openBlock(), createElementBlock("span", _hoisted_1$4, "(" + toDisplayString($props.month.snapshotCount) + ")", 1)) : createCommentVNode("", true)]),
			_cache[0] || (_cache[0] = createTextVNode()),
			(openBlock(true), createElementBlock(Fragment, null, renderList($options.dayInitials, (dayInitial) => {
				return openBlock(), createElementBlock("span", {
					class: "day",
					style: normalizeStyle($options.dayStyle)
				}, toDisplayString(dayInitial), 5);
			}), 256)),
			_cache[1] || (_cache[1] = createBaseVNode("br", null, null, -1)),
			_cache[2] || (_cache[2] = createTextVNode()),
			(openBlock(true), createElementBlock(Fragment, null, renderList($options.days, (day, i) => {
				return openBlock(), createElementBlock("span", null, [i && i % 7 === 0 ? (openBlock(), createElementBlock("br", _hoisted_2$3)) : createCommentVNode("", true), createBaseVNode("span", {
					class: normalizeClass(["day", {
						empty: !day || !day.snapshotCount,
						"contains-current-snapshot": $options.dayContainsCurrentSnapshot(day)
					}]),
					style: normalizeStyle($options.dayStyle),
					onClick: ($event) => $options.gotoDay(day, $event),
					onKeyup: withKeys(($event) => $options.gotoDay(day, $event), ["enter"])
				}, [day ? (openBlock(), createElementBlock(Fragment, { key: 0 }, [
					day.snapshotCount ? (openBlock(), createElementBlock("span", {
						key: 0,
						class: "size",
						style: normalizeStyle($options.getDayCountCircleStyle(day.snapshotCount)),
						tabindex: "0"
					}, null, 4)) : createCommentVNode("", true),
					createBaseVNode("span", { class: normalizeClass(["day-id", { empty: !day.snapshotCount }]) }, toDisplayString(day.id), 3),
					day.snapshotCount ? (openBlock(), createElementBlock("span", _hoisted_4$2, toDisplayString(_ctx.$_(day.snapshotCount !== 1 ? "{count} captures" : "{count} capture", { count: day.snapshotCount })), 1)) : createCommentVNode("", true)
				], 64)) : createCommentVNode("", true)], 46, _hoisted_3$3)]);
			}), 256))
		], 2);
	}
	var CalendarMonth_default = _plugin_vue_export_helper_default(_sfc_main$4, [["render", _sfc_render$4]]);
	//#endregion
	//#region src/components/TimelineLinear.vue
	var _sfc_main$3 = {
		name: "TimelineLinear",
		props: ["period", "currentSnapshot"],
		emits: ["goto-period"],
		computed: {
			snapshotPeriods() {
				return this.period.getSnapshotPeriodsFlat();
			},
			containsCurrentSnapshot() {
				return this.currentSnapshot && this.period.contains(this.currentSnapshot);
			},
			displayDate() {
				let dateStringNoSlashes = this.period.fullId.replace(/-/g, "/");
				return new Date(dateStringNoSlashes).toLocaleDateString(PywbI18N.getLocale());
			}
		},
		methods: {
			isCurrentSnapshot(period) {
				if (!!this.currentSnapshot && !!period.snapshot) return this.currentSnapshot && this.currentSnapshot.id === period.snapshot.id;
				return false;
			},
			changePeriod(period) {
				this.$emit("goto-period", period);
			}
		}
	};
	var _hoisted_1$3 = { class: "timeline-linear" };
	var _hoisted_2$2 = { class: "title" };
	var _hoisted_3$2 = { class: "list" };
	var _hoisted_4$1 = ["onClick", "onKeyup"];
	var _hoisted_5$1 = {
		key: 0,
		class: "current"
	};
	function _sfc_render$3(_ctx, _cache, $props, $setup, $data, $options) {
		return openBlock(), createElementBlock("div", _hoisted_1$3, [
			createBaseVNode("div", _hoisted_2$2, [
				createBaseVNode("div", null, toDisplayString($options.displayDate), 1),
				_cache[0] || (_cache[0] = createTextVNode()),
				createBaseVNode("div", null, toDisplayString(_ctx.$_($props.period.snapshotCount !== 1 ? "{count} captures" : "{count} capture", { count: $props.period.snapshotCount })), 1)
			]),
			_cache[2] || (_cache[2] = createTextVNode()),
			createBaseVNode("div", _hoisted_3$2, [(openBlock(true), createElementBlock(Fragment, null, renderList($options.snapshotPeriods, (snapshotPeriod) => {
				return openBlock(), createElementBlock("div", null, [
					createBaseVNode("span", {
						onClick: ($event) => $options.changePeriod(snapshotPeriod),
						onKeyup: withKeys(($event) => $options.changePeriod(snapshotPeriod), ["enter"]),
						class: "link",
						tabindex: "1"
					}, toDisplayString(snapshotPeriod.snapshot.getTimeFormatted()), 41, _hoisted_4$1),
					_cache[1] || (_cache[1] = createTextVNode()),
					$options.isCurrentSnapshot($props.period) ? (openBlock(), createElementBlock("span", _hoisted_5$1, toDisplayString(_ctx.$_("current")), 1)) : createCommentVNode("", true)
				]);
			}), 256))])
		]);
	}
	var TimelineLinear_default = _plugin_vue_export_helper_default(_sfc_main$3, [["render", _sfc_render$3], ["__scopeId", "data-v-cd9252e7"]]);
	//#endregion
	//#region src/components/Tooltip.vue
	var _sfc_main$2 = {
		name: "Tooltip",
		props: ["position"],
		mounted() {
			this.$watch("position", this.updatePosition);
			this.updatePosition();
		},
		methods: { updatePosition() {
			this.$el.style.top = 0;
			this.$el.style.left = 0;
			this.$el.style.maxHeight = "auto";
			const style = window.getComputedStyle(this.$el);
			const width = parseInt(style.width);
			const height = parseInt(style.height);
			const spacing = 10;
			const [initX, initY] = this.position.split(",").map((s) => parseInt(s));
			if (window.innerWidth < initX + 20 + width) this.$el.style.left = initX - (width + spacing) + "px";
			else this.$el.style.left = initX + spacing + "px";
			if (window.innerHeight < initY + 20 + height && initY - 20 - height < 0) {
				if (initY > window.innerHeight / 2) this.$el.style.top = window.innerHeight - (height + 20) + "px";
				else this.$el.style.top = "20px";
			} else if (window.innerHeight < initY + 20 + height) this.$el.style.top = initY - (spacing + height) + "px";
			else this.$el.style.top = initY + "px";
		} }
	};
	var _hoisted_1$2 = { class: "pywb-tooltip" };
	function _sfc_render$2(_ctx, _cache, $props, $setup, $data, $options) {
		return openBlock(), createElementBlock("div", _hoisted_1$2, [renderSlot(_ctx.$slots, "default", {}, void 0, true)]);
	}
	var Tooltip_default = _plugin_vue_export_helper_default(_sfc_main$2, [["render", _sfc_render$2], ["__scopeId", "data-v-f5173de9"]]);
	//#endregion
	//#region src/components/CalendarYear.vue
	var _sfc_main$1 = {
		components: {
			CalendarMonth: CalendarMonth_default,
			TimelineLinear: TimelineLinear_default,
			Tooltip: Tooltip_default
		},
		emits: ["goto-period"],
		props: ["period", "currentSnapshot"],
		data: function() {
			return {
				firstZoomLevel: PywbPeriod.Type.day,
				currentTimelinePeriod: null,
				currentTimelinePos: "0,0"
			};
		},
		mounted() {
			document.querySelector("body").addEventListener("click", this.resetCurrentTimeline);
		},
		computed: {
			year() {
				let year = null;
				if (this.period.type === PywbPeriod.Type.all) {
					if (!this.currentSnapshot) year = this.period.children[this.period.children.length - 1];
					else year = this.period.findByFullId(String(this.currentSnapshot.year));
				} else if (this.period.type === PywbPeriod.Type.year) year = this.period;
				else year = this.period.getParents().filter((p) => p.type === PywbPeriod.Type.year)[0];
				if (year) year.fillEmptyChildPeriods(true);
				return year;
			},
			currentYearIndex() {
				if (this.year.parent) return this.year.parent.children.findIndex((year) => year.fullId === this.year.fullId);
			},
			previousYear() {
				return this.year.getPrevious();
			},
			nextYear() {
				return this.year.getNext();
			},
			currentMonth() {
				let month = null;
				if (this.period.type === PywbPeriod.Type.month) month = this.period;
				else month = this.period.getParents().filter((p) => p.type === PywbPeriod.Type.month)[0];
				return month;
			},
			containsCurrentSnapshot() {
				return this.currentSnapshot && this.year.contains(this.currentSnapshot);
			}
		},
		methods: {
			gotoPreviousYear() {
				this.gotoPeriod(this.previousYear, true);
			},
			gotoNextYear() {
				this.gotoPeriod(this.nextYear, true);
			},
			resetCurrentTimeline(event) {
				if (event && this.$refs.timelineLinearTooltip) {
					let el = event.target;
					let clickWithinTooltip = false;
					while (el.parentElement) {
						if (el === this.$refs.timelineLinearTooltip.$el) {
							clickWithinTooltip = true;
							break;
						}
						el = el.parentElement;
					}
					if (!clickWithinTooltip) this.currentTimelinePeriod = null;
				}
			},
			setCurrentTimeline(day, event) {
				this.currentTimelinePeriod = day;
				if (!day) return;
				if (event.code === "Enter") {
					let middleXPos = window.innerWidth / 2 - 60;
					this.currentTimelinePos = `${middleXPos},200`;
				} else this.currentTimelinePos = `${event.x},${event.y}`;
				event.stopPropagation();
				event.preventDefault();
			},
			gotoPeriod(period, changeYearOnly = false) {
				if (period.snapshot || period.snapshotPeriod || changeYearOnly) this.$emit("goto-period", period);
				else this.currentTimelinePeriod = period;
			}
		}
	};
	var _hoisted_1$1 = { class: "full-view border-top-0 border-left-0 border-right-0 border-bottom border-dark shadow" };
	var _hoisted_2$1 = { class: "mx-1" };
	var _hoisted_3$1 = { class: "months" };
	function _sfc_render$1(_ctx, _cache, $props, $setup, $data, $options) {
		const _component_CalendarMonth = resolveComponent("CalendarMonth");
		const _component_TimelineLinear = resolveComponent("TimelineLinear");
		const _component_Tooltip = resolveComponent("Tooltip");
		return openBlock(), createElementBlock("div", _hoisted_1$1, [
			createBaseVNode("h2", null, [
				$options.previousYear ? (openBlock(), createElementBlock("i", {
					key: 0,
					class: "fas fa-arrow-left year-arrow",
					onClick: _cache[0] || (_cache[0] = (...args) => $options.gotoPreviousYear && $options.gotoPreviousYear(...args)),
					onKeyup: _cache[1] || (_cache[1] = withKeys((...args) => $options.gotoPreviousYear && $options.gotoPreviousYear(...args), ["enter"])),
					tabindex: "0"
				}, null, 32)) : createCommentVNode("", true),
				_cache[5] || (_cache[5] = createTextVNode()),
				createBaseVNode("span", _hoisted_2$1, toDisplayString($options.year.id) + " (" + toDisplayString(_ctx.$_($options.year.snapshotCount !== 1 ? "{count} captures" : "{count} capture", { count: $options.year.snapshotCount })) + ")\n      ", 1),
				_cache[6] || (_cache[6] = createTextVNode()),
				$options.nextYear ? (openBlock(), createElementBlock("i", {
					key: 1,
					class: "fas fa-arrow-right year-arrow",
					onClick: _cache[2] || (_cache[2] = (...args) => $options.gotoNextYear && $options.gotoNextYear(...args)),
					onKeyup: _cache[3] || (_cache[3] = withKeys((...args) => $options.gotoNextYear && $options.gotoNextYear(...args), ["enter"])),
					tabindex: "0"
				}, null, 32)) : createCommentVNode("", true)
			]),
			_cache[7] || (_cache[7] = createTextVNode()),
			createBaseVNode("div", _hoisted_3$1, [(openBlock(true), createElementBlock(Fragment, null, renderList($options.year.children, (month) => {
				return openBlock(), createBlock(_component_CalendarMonth, {
					key: month.id,
					month,
					year: $options.year,
					"current-snapshot": $options.containsCurrentSnapshot ? $props.currentSnapshot : null,
					"is-current": month === $options.currentMonth,
					onGotoPeriod: _cache[4] || (_cache[4] = ($event) => _ctx.$emit("goto-period", $event)),
					onShowDayTimeline: $options.setCurrentTimeline
				}, null, 8, [
					"month",
					"year",
					"current-snapshot",
					"is-current",
					"onShowDayTimeline"
				]);
			}), 128))]),
			_cache[8] || (_cache[8] = createTextVNode()),
			_ctx.currentTimelinePeriod ? (openBlock(), createBlock(_component_Tooltip, {
				key: 0,
				position: _ctx.currentTimelinePos,
				ref: "timelineLinearTooltip"
			}, {
				default: withCtx(() => [createVNode(_component_TimelineLinear, {
					period: _ctx.currentTimelinePeriod,
					"current-snapshot": $options.containsCurrentSnapshot ? $props.currentSnapshot : null,
					onGotoPeriod: $options.gotoPeriod
				}, null, 8, [
					"period",
					"current-snapshot",
					"onGotoPeriod"
				])]),
				_: 1
			}, 8, ["position"])) : createCommentVNode("", true)
		]);
	}
	var CalendarYear_default = _plugin_vue_export_helper_default(_sfc_main$1, [["render", _sfc_render$1], ["__scopeId", "data-v-f7e8c6b3"]]);
	//#endregion
	//#region src/App.vue
	var _sfc_main = {
		name: "PywbReplayApp",
		data: function() {
			return {
				snapshots: [],
				currentPeriod: null,
				currentSnapshot: null,
				currentSnapshotIndex: null,
				msgs: [],
				showFullView: false,
				showTimelineView: false,
				maxTimelineZoomLevel: PywbPeriod.Type.day,
				config: {
					title: "",
					initialView: {},
					allLocales: {}
				},
				timelineHighlight: false,
				locales: []
			};
		},
		components: {
			Timeline: Timeline_default,
			TimelineBreadcrumbs: TimelineBreadcrumbs_default,
			CalendarYear: CalendarYear_default
		},
		emits: ["show-snapshot", "data-set-and-render-completed"],
		mounted: function() {
			addEventListener("unload", (event) => {});
		},
		updated: function() {
			document.title = this.$_("Archived Page: ") + this.config.title;
		},
		computed: {
			sessionStorageUrlKey() {
				return "zoom__" + this.config.url.replace(/^https?:\/\/(www\.)?/, "").replace(/\/$/, "");
			},
			localesAreSet() {
				return Object.entries(this.config.allLocales).length > 0;
			},
			navbarStyle() {
				return {
					"--navbar-background": `#${this.config.navbarBackground}`,
					"--navbar-color": `#${this.config.navbarColor}`
				};
			},
			lightButtons() {
				return !!this.config.navbarLightButtons;
			},
			printingEnabled() {
				return !this.config.disablePrinting;
			},
			previousSnapshot() {
				if (!this.currentSnapshotIndex) return null;
				if (this.currentSnapshotIndex > 0) return this.snapshots[this.currentSnapshotIndex - 1];
				return null;
			},
			nextSnapshot() {
				if (this.currentSnapshotIndex == null) return null;
				if (this.currentSnapshotIndex >= 0 && this.currentSnapshotIndex !== this.snapshots.length - 1) return this.snapshots[this.currentSnapshotIndex + 1];
				return null;
			}
		},
		methods: {
			gotoPeriod: function(newPeriod, onlyZoomToPeriod) {
				if (this.timelineHighlight) setTimeout((() => {
					this.timelineHighlight = false;
				}).bind(this), 3e3);
				if (newPeriod.snapshot && !onlyZoomToPeriod) this.gotoSnapshot(newPeriod.snapshot, newPeriod, true);
				else {
					if (window.sessionStorage) window.sessionStorage.setItem(this.sessionStorageUrlKey, newPeriod.fullId);
					if (newPeriod.type > this.maxTimelineZoomLevel) this.currentPeriod = newPeriod.get(this.maxTimelineZoomLevel);
					else this.currentPeriod = newPeriod;
				}
			},
			gotoSnapshot(snapshot, fromPeriod, reloadIFrame = false) {
				this.currentSnapshot = snapshot;
				const isCurrentSnapshot = (snapshotInArray) => snapshotInArray.id == snapshot.id && snapshotInArray.url == snapshot.url;
				this.currentSnapshotIndex = this.snapshots.findIndex(isCurrentSnapshot);
				if (!this.currentPeriod || fromPeriod && !this.currentPeriod.contains(fromPeriod)) {
					const fromPeriodAtMaxZoomLevel = fromPeriod.get(this.maxTimelineZoomLevel);
					if (!this.currentPeriod || fromPeriodAtMaxZoomLevel !== this.currentPeriod) this.currentPeriod = fromPeriodAtMaxZoomLevel;
				}
				if (reloadIFrame !== false) this.$emit("show-snapshot", snapshot);
				this.initBannerState(true);
			},
			gotoPreviousSnapshot() {
				let periodToChangeTo = this.currentPeriod.findByFullId(this.previousSnapshot.getFullId());
				this.gotoPeriod(periodToChangeTo, false);
			},
			gotoNextSnapshot() {
				let periodToChangeTo = this.currentPeriod.findByFullId(this.nextSnapshot.getFullId());
				this.gotoPeriod(periodToChangeTo, false);
			},
			gotoUrl(event) {
				event.preventDefault();
				const newUrl = document.querySelector("#theurl").value;
				if (newUrl !== this.config.url) {
					const ts = this.config.timestamp === void 0 ? "*" : this.config.timestamp;
					window.location.href = this.config.prefix + ts + (ts ? "/" : "") + newUrl;
				}
			},
			toggleTimelineView() {
				this.showTimelineView = !this.showTimelineView;
				window.localStorage.setItem("showTimelineView", this.showTimelineView ? "1" : "0");
			},
			hasReplayFrame() {
				return !!window.frames.replay_iframe;
			},
			printReplayFrame() {
				window.frames.replay_iframe.contentWindow.focus();
				window.frames.replay_iframe.contentWindow.print();
				return false;
			},
			setData(data) {
				this.snapshots = data.snapshots;
				this.currentPeriod = data.timeline;
				if (window.sessionStorage) {
					const currentPeriodId = window.sessionStorage.getItem(this.sessionStorageUrlKey);
					if (currentPeriodId) {
						const newCurrentPeriodFromStorage = this.currentPeriod.findByFullId(currentPeriodId);
						if (newCurrentPeriodFromStorage) this.currentPeriod = newCurrentPeriodFromStorage;
					}
				}
				this.$nextTick(function isDone() {
					this.$emit("data-set-and-render-completed");
				}.bind(this));
			},
			setSnapshot(view) {
				if (!this.currentPeriod) return false;
				this.showFullView = false;
				const snapshot = new PywbSnapshot(view, 0);
				this.config.url = view.url;
				let periodToChangeTo = this.currentPeriod.findByFullId(snapshot.getFullId());
				if (periodToChangeTo) {
					this.gotoPeriod(periodToChangeTo, false);
					return true;
				}
				return false;
			},
			initBannerState(isReplay) {
				if (!isReplay) {
					this.showFullView = true;
					this.showTimelineView = true;
				} else {
					this.showFullView = false;
					this.showTimelineView = window.localStorage.getItem("showTimelineView") === "1";
				}
			},
			updateTitle(title) {
				this.config.title = title;
			}
		}
	};
	var _hoisted_1 = ["href"];
	var _hoisted_2 = ["src", "alt"];
	var _hoisted_3 = {
		key: 1,
		class: "navbar-brand flex-grow-1 my-1"
	};
	var _hoisted_4 = ["src", "alt"];
	var _hoisted_5 = {
		class: "flex-grow-1 d-flex",
		id: "searchdiv"
	};
	var _hoisted_6 = [
		"value",
		"aria-label",
		"title"
	];
	var _hoisted_7 = ["aria-label"];
	var _hoisted_8 = {
		class: "collapse navbar-collapse ml-auto",
		id: "navbarCollapse"
	};
	var _hoisted_9 = {
		class: "navbar-nav ml-3",
		id: "toggles"
	};
	var _hoisted_10 = { class: "nav-item" };
	var _hoisted_11 = ["title"];
	var _hoisted_12 = ["title"];
	var _hoisted_13 = { class: "nav-item" };
	var _hoisted_14 = ["title"];
	var _hoisted_15 = ["title"];
	var _hoisted_16 = { class: "nav-item active" };
	var _hoisted_17 = ["aria-pressed", "title"];
	var _hoisted_18 = { class: "nav-item" };
	var _hoisted_19 = ["aria-pressed", "title"];
	var _hoisted_20 = { class: "nav-item" };
	var _hoisted_21 = ["aria-pressed", "title"];
	var _hoisted_22 = {
		key: 0,
		class: "nav-item dropdown"
	};
	var _hoisted_23 = ["title"];
	var _hoisted_24 = ["title"];
	var _hoisted_25 = {
		class: "dropdown-menu dropdown-menu-right",
		"aria-labelledby": "locale-dropdown"
	};
	var _hoisted_26 = ["href"];
	var _hoisted_27 = {
		key: 0,
		class: "hidden"
	};
	var _hoisted_28 = { key: 1 };
	var _hoisted_29 = { class: "strong mr-1" };
	var _hoisted_30 = {
		key: 0,
		class: "ml-1"
	};
	var _hoisted_31 = {
		key: 0,
		class: "mr-1"
	};
	var _hoisted_32 = { class: "card border-top-0 border-left-0 border-right-0 timeline-wrap" };
	var _hoisted_33 = {
		key: 0,
		class: "card-body"
	};
	var _hoisted_34 = { class: "row" };
	var _hoisted_35 = { class: "col col-12" };
	var _hoisted_36 = { class: "col col-12 mt-2" };
	var _hoisted_37 = {
		key: 0,
		class: "card",
		id: "calendar-card"
	};
	var _hoisted_38 = {
		class: "card-body",
		id: "calendar-card-body"
	};
	function _sfc_render(_ctx, _cache, $props, $setup, $data, $options) {
		const _component_TimelineBreadcrumbs = resolveComponent("TimelineBreadcrumbs");
		const _component_Timeline = resolveComponent("Timeline");
		const _component_CalendarYear = resolveComponent("CalendarYear");
		return openBlock(), createElementBlock("div", {
			class: normalizeClass(["app", { expanded: _ctx.showTimelineView || _ctx.showFullView }]),
			"data-app": "webrecorder-replay-app"
		}, [
			createBaseVNode("nav", {
				class: "navbar navbar-light navbar-expand-lg fixed-top top-navbar justify-content-center",
				style: normalizeStyle($options.navbarStyle)
			}, [
				_ctx.config.logoHomeUrl ? (openBlock(), createElementBlock("a", {
					key: 0,
					class: "navbar-brand flex-grow-1 my-1",
					href: _ctx.config.logoHomeUrl
				}, [createBaseVNode("img", {
					src: _ctx.config.logoImg,
					id: "logo-img",
					alt: _ctx.$_("Logo")
				}, null, 8, _hoisted_2)], 8, _hoisted_1)) : (openBlock(), createElementBlock("div", _hoisted_3, [createBaseVNode("img", {
					src: _ctx.config.logoImg,
					id: "logo-img",
					alt: _ctx.$_("Logo")
				}, null, 8, _hoisted_4)])),
				_cache[16] || (_cache[16] = createTextVNode()),
				createBaseVNode("div", _hoisted_5, [createBaseVNode("form", {
					class: "form-inline my-2 my-md-0 mx-lg-auto",
					role: "search",
					onSubmit: _cache[0] || (_cache[0] = (...args) => $options.gotoUrl && $options.gotoUrl(...args))
				}, [createBaseVNode("input", {
					id: "theurl",
					type: "text",
					value: _ctx.config.url,
					height: "31",
					"aria-label": _ctx.$_("Search for archival capture of URL"),
					title: _ctx.$_("Search for archival capture of URL")
				}, null, 8, _hoisted_6)], 32)]),
				_cache[17] || (_cache[17] = createTextVNode()),
				createBaseVNode("button", {
					class: "navbar-toggler btn btn-sm",
					id: "collapse-button",
					type: "button",
					"data-toggle": "collapse",
					"data-target": "#navbarCollapse",
					"aria-controls": "navbarCollapse",
					"aria-expanded": "false",
					"aria-label": _ctx.$_("Toggle navigation")
				}, [..._cache[6] || (_cache[6] = [createBaseVNode("span", { class: "navbar-toggler-icon" }, null, -1)])], 8, _hoisted_7),
				_cache[18] || (_cache[18] = createTextVNode()),
				createBaseVNode("div", _hoisted_8, [createBaseVNode("ul", _hoisted_9, [
					createBaseVNode("li", _hoisted_10, [$options.previousSnapshot ? (openBlock(), createElementBlock("button", {
						key: 0,
						class: normalizeClass(["btn btn-sm", {
							active: _ctx.showFullView,
							"btn-outline-light": $options.lightButtons,
							"btn-outline-dark": !$options.lightButtons
						}]),
						title: _ctx.$_("Previous capture"),
						onClick: _cache[1] || (_cache[1] = (...args) => $options.gotoPreviousSnapshot && $options.gotoPreviousSnapshot(...args))
					}, [createBaseVNode("i", {
						class: "fas fa-arrow-left",
						title: _ctx.$_("Previous capture")
					}, null, 8, _hoisted_12)], 10, _hoisted_11)) : createCommentVNode("", true)]),
					_cache[11] || (_cache[11] = createTextVNode()),
					createBaseVNode("li", _hoisted_13, [$options.nextSnapshot ? (openBlock(), createElementBlock("button", {
						key: 0,
						class: normalizeClass(["btn btn-sm", {
							active: _ctx.showFullView,
							"btn-outline-light": $options.lightButtons,
							"btn-outline-dark": !$options.lightButtons
						}]),
						title: _ctx.$_("Next capture"),
						onClick: _cache[2] || (_cache[2] = (...args) => $options.gotoNextSnapshot && $options.gotoNextSnapshot(...args))
					}, [createBaseVNode("i", {
						class: "fas fa-arrow-right",
						title: _ctx.$_("Next capture")
					}, null, 8, _hoisted_15)], 10, _hoisted_14)) : createCommentVNode("", true)]),
					_cache[12] || (_cache[12] = createTextVNode()),
					createBaseVNode("li", _hoisted_16, [createBaseVNode("button", {
						class: normalizeClass(["btn btn-sm", {
							active: _ctx.showFullView,
							"btn-outline-light": $options.lightButtons,
							"btn-outline-dark": !$options.lightButtons
						}]),
						"aria-pressed": _ctx.showFullView ? true : false,
						onClick: _cache[3] || (_cache[3] = ($event) => _ctx.showFullView = !_ctx.showFullView),
						title: _ctx.showFullView ? _ctx.$_("Hide calendar") : _ctx.$_("Show calendar")
					}, [..._cache[7] || (_cache[7] = [createBaseVNode("i", { class: "far fa-calendar-alt" }, null, -1)])], 10, _hoisted_17)]),
					_cache[13] || (_cache[13] = createTextVNode()),
					createBaseVNode("li", _hoisted_18, [createBaseVNode("button", {
						class: normalizeClass(["btn btn-sm", {
							active: _ctx.showTimelineView,
							"btn-outline-light": $options.lightButtons,
							"btn-outline-dark": !$options.lightButtons
						}]),
						"aria-pressed": _ctx.showTimelineView,
						onClick: _cache[4] || (_cache[4] = (...args) => $options.toggleTimelineView && $options.toggleTimelineView(...args)),
						title: _ctx.showTimelineView ? _ctx.$_("Hide timeline") : _ctx.$_("Show timeline")
					}, [..._cache[8] || (_cache[8] = [createBaseVNode("i", { class: "far fa-chart-bar" }, null, -1)])], 10, _hoisted_19)]),
					_cache[14] || (_cache[14] = createTextVNode()),
					createBaseVNode("li", _hoisted_20, [$options.printingEnabled && $options.hasReplayFrame() ? (openBlock(), createElementBlock("button", {
						key: 0,
						class: normalizeClass(["btn btn-sm", {
							"btn-outline-light": $options.lightButtons,
							"btn-outline-dark": !$options.lightButtons
						}]),
						"aria-pressed": $options.printReplayFrame,
						onClick: _cache[5] || (_cache[5] = (...args) => $options.printReplayFrame && $options.printReplayFrame(...args)),
						title: _ctx.$_("Print")
					}, [..._cache[9] || (_cache[9] = [createBaseVNode("i", { class: "fas fa-print" }, null, -1)])], 10, _hoisted_21)) : createCommentVNode("", true)]),
					_cache[15] || (_cache[15] = createTextVNode()),
					$options.localesAreSet ? (openBlock(), createElementBlock("li", _hoisted_22, [
						createBaseVNode("button", {
							class: normalizeClass(["btn btn-sm dropdown-toggle", {
								"btn-outline-light": $options.lightButtons,
								"btn-outline-dark": !$options.lightButtons
							}]),
							type: "button",
							id: "locale-dropdown",
							"data-toggle": "dropdown",
							"aria-haspopup": "true",
							"aria-expanded": "false",
							title: _ctx.$_("Select language")
						}, [createBaseVNode("i", {
							class: "fas fa-globe-africa",
							title: _ctx.$_("Language:")
						}, null, 8, _hoisted_24)], 10, _hoisted_23),
						_cache[10] || (_cache[10] = createTextVNode()),
						createBaseVNode("div", _hoisted_25, [(openBlock(true), createElementBlock(Fragment, null, renderList(_ctx.config.allLocales, (locPath, key) => {
							return openBlock(), createElementBlock("a", {
								class: "dropdown-item",
								key,
								href: locPath + (_ctx.currentSnapshot ? _ctx.currentSnapshot.id : "*") + "/" + _ctx.config.url
							}, toDisplayString(key), 9, _hoisted_26);
						}), 128))])
					])) : createCommentVNode("", true)
				])])
			], 4),
			_cache[22] || (_cache[22] = createTextVNode()),
			createBaseVNode("nav", {
				class: "navbar navbar-light justify-content-center title-nav fixed-top",
				id: "second-navbar",
				style: normalizeStyle($options.navbarStyle)
			}, [
				!_ctx.currentSnapshot ? (openBlock(), createElementBlock("span", _hoisted_27, "\u00A0")) : createCommentVNode("", true),
				_cache[20] || (_cache[20] = createTextVNode()),
				_ctx.currentSnapshot ? (openBlock(), createElementBlock("span", _hoisted_28, [
					createBaseVNode("span", _hoisted_29, [createTextVNode(toDisplayString(_ctx.$_("Current Capture")) + ": \n          ", 1), _ctx.config.title ? (openBlock(), createElementBlock("span", _hoisted_30, toDisplayString(_ctx.config.title), 1)) : createCommentVNode("", true)]),
					_cache[19] || (_cache[19] = createTextVNode()),
					_ctx.config.title ? (openBlock(), createElementBlock("span", _hoisted_31, "|")) : createCommentVNode("", true),
					createTextVNode(" " + toDisplayString(_ctx.currentSnapshot.getTimeDateFormatted()), 1)
				])) : createCommentVNode("", true)
			], 4),
			_cache[23] || (_cache[23] = createTextVNode()),
			createBaseVNode("div", _hoisted_32, [_ctx.currentPeriod && _ctx.showTimelineView ? (openBlock(), createElementBlock("div", _hoisted_33, [createBaseVNode("div", _hoisted_34, [
				createBaseVNode("div", _hoisted_35, [createVNode(_component_TimelineBreadcrumbs, {
					period: _ctx.currentPeriod,
					onGotoPeriod: $options.gotoPeriod
				}, null, 8, ["period", "onGotoPeriod"])]),
				_cache[21] || (_cache[21] = createTextVNode()),
				createBaseVNode("div", _hoisted_36, [createVNode(_component_Timeline, {
					period: _ctx.currentPeriod,
					highlight: _ctx.timelineHighlight,
					"current-snapshot": _ctx.currentSnapshot,
					"max-zoom-level": _ctx.maxTimelineZoomLevel,
					onGotoPeriod: $options.gotoPeriod
				}, null, 8, [
					"period",
					"highlight",
					"current-snapshot",
					"max-zoom-level",
					"onGotoPeriod"
				])])
			])])) : createCommentVNode("", true)]),
			_cache[24] || (_cache[24] = createTextVNode()),
			_ctx.currentPeriod && _ctx.showFullView && _ctx.currentPeriod.children.length ? (openBlock(), createElementBlock("div", _hoisted_37, [createBaseVNode("div", _hoisted_38, [createVNode(_component_CalendarYear, {
				period: _ctx.currentPeriod,
				"current-snapshot": _ctx.currentSnapshot,
				onGotoPeriod: $options.gotoPeriod
			}, null, 8, [
				"period",
				"current-snapshot",
				"onGotoPeriod"
			])])])) : createCommentVNode("", true)
		], 2);
	}
	var App_default = _plugin_vue_export_helper_default(_sfc_main, [["render", _sfc_render]]);
	//#endregion
	//#region \0virtual:css-injected-by-js
	function injectCSS(opts) {
		if (typeof globalThis === "undefined") return;
		globalThis.__VITE_CSS_INJECT_OPTS__ = opts || {};
		var q = globalThis.__VITE_CSS_QUEUE__ || [];
		var exec = globalThis.__VITE_CSS_EXECUTED__ || [];
		for (var i = 0; i < exec.length; i++) exec[i](opts || {});
		for (var i = 0; i < q.length; i++) {
			q[i](opts || {});
			exec.push(q[i]);
		}
		globalThis.__VITE_CSS_QUEUE__ = [];
		globalThis.__VITE_CSS_EXECUTED__ = exec;
	}
	//#endregion
	//#region src/index.js
	function main(config, locale, i18nStrings) {
		injectCSS();
		PywbI18N.init(locale, i18nStrings);
		new CDXLoader(config);
	}
	var CDXLoader = class {
		constructor(config) {
			this.loadingSpinner = null;
			this.loaded = false;
			this.opts = {};
			this.url = config.url;
			this.prefix = config.prefix;
			this.staticPrefix = config.staticPrefix;
			this.logoUrl = config.logoUrl;
			this.logoHomeUrl = config.logoHomeUrl;
			this.navbarBackground = config.navbarBackground;
			this.navbarColor = config.navbarColor;
			this.navbarLightButtons = config.navbarLightButtons;
			this.disablePrinting = config.disablePrinting;
			this.timestamp = config.timestamp;
			this.isReplay = config.timestamp !== void 0;
			setTimeout(() => {
				if (!this.loaded) {
					this.loadingSpinner = new LoadingSpinner({
						text: PywbI18N.instance?.getText("Loading..."),
						isSmall: !!this.timestamp
					});
					this.loadingSpinner.setOn();
				}
			}, 500);
			if (this.isReplay) window.WBBanner = new VueBannerWrapper(this, this.url, this.timestamp);
			let queryURL;
			let url;
			if (window.location.href.indexOf("*?") > 0) {
				queryURL = window.location.href.replace("*?", "cdx?") + "&output=json";
				url = new URL(queryURL).searchParams.get("url");
			} else if (this.url) {
				url = this.url;
				const params = new URLSearchParams();
				params.set("url", url);
				params.set("output", "json");
				queryURL = this.prefix + "cdx?" + params.toString();
			} else throw new Error("No query URL specified");
			config.logoImg = this.staticPrefix + "/" + (!!this.logoUrl ? this.logoUrl : "pywb-logo-sm.png");
			this.app = this.initApp(config);
			this.loadCDX(queryURL).then((cdxList) => {
				this.setAppData(cdxList, url, config.timestamp);
			});
		}
		initApp(config = {}) {
			const app = createApp(App_default, {
				onShowSnapshot: (snapshot) => this.loadSnapshot(snapshot),
				onDataSetAndRenderCompleted: () => {
					if (this.loadingSpinner) this.loadingSpinner.setOff();
					this.loaded = true;
				}
			});
			app.config.globalProperties.$_ = (id, embeddedVariableStrings = null) => PywbI18N.instance.getText(id, embeddedVariableStrings);
			const container = document.querySelector("#app");
			const vm = app.mount(container);
			container.replaceWith(vm.$el);
			vm.config = {
				...vm.config,
				...config,
				prefix: this.prefix
			};
			return vm;
		}
		async updateSnapshot(url, timestamp) {
			const params = new URLSearchParams();
			params.set("url", url);
			params.set("output", "json");
			const queryURL = this.prefix + "cdx?" + params.toString();
			const cdxList = await this.loadCDX(queryURL);
			this.setAppData(cdxList, url, timestamp);
		}
		async updateTimestamp(url, timestamp) {
			this.timestamp = timestamp;
			if (this.cdxLoading) return;
			this.app.setSnapshot({
				url,
				timestamp
			});
		}
		setAppData(cdxList, url, timestamp) {
			this.app.setData(new PywbData(cdxList));
			this.app.initBannerState(this.isReplay);
			if (timestamp) this.updateTimestamp(url, timestamp);
		}
		async loadCDX(queryURL) {
			this.cdxLoading = true;
			const queryWorker = new Worker(this.staticPrefix + "/queryWorker.js");
			const p = new Promise((resolve) => {
				const cdxList = [];
				queryWorker.addEventListener("message", (event) => {
					const data = event.data;
					switch (data.type) {
						case "cdxRecord":
							cdxList.push(data.record);
							break;
						case "finished":
							this.cdxLoading = false;
							resolve(cdxList);
					}
				});
			});
			queryWorker.postMessage({
				type: "query",
				queryURL
			});
			const results = await p;
			queryWorker.terminate();
			return results;
		}
		loadSnapshot(snapshot, reloadIFrame = true) {
			if (!this.isReplay) window.location.href = this.prefix + snapshot.id + "/" + snapshot.url;
			else if (window.cframe) {
				const ts = snapshot.id + "";
				if (ts !== this.timestamp) window.cframe.load_url(snapshot.url, ts, reloadIFrame);
			}
		}
	};
	var VueBannerWrapper = class {
		constructor(loader, url, ts) {
			this.loading = true;
			this.lastSurt = this.getSurt(url);
			this.lastTs = ts;
			this.loader = loader;
		}
		init() {}
		stillIndicatesLoading() {
			return this.loading;
		}
		updateCaptureInfo() {
			this.loading = false;
		}
		onMessage(event) {
			const type = event.data.wb_type;
			if (type === "load" || type === "replace-url") {
				const surt = this.getSurt(event.data.url);
				if (event.data.title) this.loader.app.updateTitle(event.data.title);
				if (surt !== this.lastSurt) {
					this.loader.updateSnapshot(event.data.url, event.data.ts);
					this.lastSurt = surt;
				} else if (event.data.ts !== this.lastTs) {
					this.loader.updateTimestamp(event.data.url, event.data.ts);
					this.lastTs = event.data.ts;
				}
			}
		}
		getSurt(url) {
			try {
				if (!url.startsWith("https:") && !url.startsWith("http:")) return url;
				url = url.replace(/^(https?:\/\/)www\d*\./, "$1");
				const urlObj = new URL(url.toLowerCase());
				let surt = urlObj.hostname.split(".").reverse().join(",");
				if (urlObj.port) surt += ":" + urlObj.port;
				surt += ")";
				surt += urlObj.pathname;
				if (urlObj.search) {
					urlObj.searchParams.sort();
					surt += urlObj.search;
				}
				return surt;
			} catch (e) {
				return url;
			}
		}
	};
	//#endregion
	exports.main = main;
	return exports;
})({});
