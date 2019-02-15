var colon = ':';
var jsonOutput = '&output=json';
var usingWorkerStrat = (
  typeof window.Worker === 'function' &&
  typeof window.fetch === 'function' &&
  typeof window.TextDecoder === 'function' &&
  typeof window.ReadableStream === 'function'
);

var first = 1;

/**
 * Class responsible for rendering the results of the query. If the query is considered regular
 * (no filter or match type query modifiers) the calender view is rendered otherwise the advanced search is rendered
 * @param {Object} init - Initialization info for rendering the results of the query
 */
function RenderCalendar(init) {
  if (!(this instanceof RenderCalendar)) return new RenderCalendar(init);
  this.prefix = init.prefix;
  this.cdxURL = this.prefix + 'cdx';
  this.staticPrefix = init.staticPrefix;
  this.queryURL = null;
  this.searchParams = null;
  this.isRenderingCalendarView = true;
  // references to the DOM structure elements that contain the to be rendered markup
  this.containers = {
    numCaptures: null,
    updatesSpinner: null,
    yearsListDiv: null,
    monthsListDiv: null,
    daysListDiv: null,
    advancedResultsList: null,
    countTextNode: null,
    versionsTextNode: null
  };
  // ids of the to be created dom elements that are important to rendering the query results
  this.domStructureIds = {
    queryInfoId: 'display-query-type-info',
    capturesMount: 'captures',
    numCaptures: 'num-captures',
    updatesSpinner: 'still-updating-spinner'
  };
  // memoized last active year month day tab information
  this.lastActiveYMD = {};
  this.lastActiveDaysTab = null;
  // regular expressing for checking the URL when no query params are present
  this.starQueries = {
    regular: /\/[^/]+\/\*\/(.+)/i,
    dt: /\/[^/]+\/([^-/]+)-?([^/]+)?\/(.+)/i
  };
  // regex for extracting the filter constraints and filter mods to human explanation
  this.filterRE = /filter([^a-z]+)([a-z]+):(.+)/i;
  this.filterMods = {
    '=': 'Contains',
    '==': 'Matches Exactly',
    '=~': 'Matches Regex',
    '=!': 'Does Not Contains',
    '=!=': 'Is Not',
    '=!~': 'Does Not Begins With'
  };
  this.text = {
    months: {
      '01': 'January',
      '02': 'February',
      '03': 'March',
      '04': 'April',
      '05': 'May',
      '06': 'June',
      '07': 'July',
      '08': 'August',
      '09': 'September',
      '10': 'October',
      '11': 'November',
      '12': 'December'
    },
    version: 'capture',
    versions: 'captures',
    result: 'result',
    results: 'results'
  };
  this.versionString = null;
}

/**
 * Initializes the rendering process and checks the our locations URL to determine which
 * result view to render (calendar or advanced)
 */
RenderCalendar.prototype.init = function () {
  // since we are mimicking the cdx api here we need to consider only the params our locations URL
  // location.search is un-helpful here and need to parse our locations URL using the WHATWG URL Standard
  var searchURL = new URL(location.href);
  if (!searchURL.search) {
    // there is no search params so we need to check for the two cases of * queries
    var query = this.constructRegularStarQuery(searchURL);
    if (query) {
      if (!this.isRenderingCalendarView) {
        this.searchParams = searchURL.searchParams;
      }
      return this.cdxRequest(query);
    }
  }
  // there were search params and in this case when constructing the URL used for the CDX api request
  // location.search is just what we need
  this.queryURL = searchURL.searchParams.get('url');
  this.searchParams = searchURL.searchParams;
  if (this.shouldRenderCalenderView(this.searchParams)) {
    return this.cdxRequest(location.search);
  }
  this.isRenderingCalendarView = false;
  this.cdxRequest(location.search);
};

/**
 * Constructs the query string used in the CDX api request if the path of our locations
 * URL contains the two cases of regular star queries (did not originate from the collections query interface),
 * otherwise undefined is returned to indicate no match.
 *
 * When the path does match the two cases the supplied instance of WHATWG URL's search params are updated
 * if the url for the CDX API query is a prefix or domain match type in order to allow the advanced results
 * view to be rendered properly and {@link RenderCalendar#isRenderingCalendarView} is set to false.
 * @param {URL} url - The WHATWG URL instance representing our location
 * @return {?string} - The query string for the CDX api request if the path matches
 */
RenderCalendar.prototype.constructRegularStarQuery = function (url) {
  var query;
  var match = this.starQueries.regular.exec(url.pathname);
  if (match) {
    // case possibility /collection/*/url*
    this.queryURL = match[1];
    query = '?url=' + this.queryURL;
    if (this.queryURL.charAt(this.queryURL.length - 1) === '*') {
      url.searchParams.set('matchType', 'prefix');
      this.isRenderingCalendarView = false;
    } else if (this.queryURL.substring(0, 2) === '*.') {
      url.searchParams.set('matchType', 'domain');
      this.isRenderingCalendarView = false;
    }
    return query;
  }
  match = this.starQueries.dt.exec(url.pathname);
  if (match) {
    // case possibility /collection/fromDT*-toDT*/url*
    this.queryURL = match[3];
    query = '?url=' + this.queryURL + '&from=' + match[1] + (match[2] ? '&to=' + match[2] : '');
    if (this.queryURL.charAt(this.queryURL.length - 1) === '*') {
      url.searchParams.set('matchType', 'prefix');
      this.isRenderingCalendarView = false;
    } else if (this.queryURL.substring(0, 2) === '*.') {
      url.searchParams.set('matchType', 'domain');
      this.isRenderingCalendarView = false;
    }
  }
  return query;
};

/**
 * Performs the query by requesting the CDX information from the cdx server.
 * How the results are received from the CDX API is done by of two strategies: using a web worker or in the main thread.
 * This is due to the fact that the query results can be LARGE and extracting the results in the main thread is not
 * preformat and will lock up the browser. The determination for if we can use the web worker strategy is
 * by checking if the browser has the symbols Worker, fetch, TextDecoder, and ReadableStream defined and are functions.
 * If we can use the web worker strategy a worker is created and updates the result view as it sends us the queries
 * cdx info. Otherwise the query is executed in the main thread and the results are both parsed and rendered in the
 * main thread.
 * @param {string} query - The CDX API query string to be used
 */
RenderCalendar.prototype.cdxRequest = function (query) {
  // construct the full query url checking to determine if we need to add &output=json to the end
  var queryURL = this.cdxURL + query + (query.indexOf(jsonOutput) === -1 ? jsonOutput : '');
  // if we are rendering the calendar view (regular result view) we need memoizedYMDT to be an object otherwise nothing
  var memoizedYMDT = this.isRenderingCalendarView ? {} : null;
  var renderCal = this;
  // initialized the dom structure
  this.createContainers();
  if (usingWorkerStrat) {
    // execute the query and render the results using the query worker
    var queryWorker = new window.Worker(this.staticPrefix + '/queryWorker.js');
    var cdxRecordMsg = 'cdxRecord';
    var done = 'finished';
    queryWorker.onmessage = function (msg) {
      var data = msg.data;
      var terminate = false;
      if (data.type === cdxRecordMsg) {
        // render the results sent to us from the worker
        renderCal.displayedCountStr(data.recordCount, data.recordCountFormatted);
        if (renderCal.isRenderingCalendarView) {
          renderCal.renderDateCalPart(memoizedYMDT, data.record, data.timeInfo, data.recordCount === first);
        } else {
          renderCal.renderAdvancedSearchPart(data.record);
        }
      } else if (data.type === done) {
        // the worker has consumed the entirety of the response body
        terminate = true;
        // if there were no results we need to inform the user
        renderCal.displayedCountStr(data.recordCount, data.recordCountFormatted);
      }
      if (terminate) {
        queryWorker.terminate();
        var spinner = document.getElementById(renderCal.domStructureIds.updatesSpinner);
        if (spinner) spinner.remove();
      }
    };
    queryWorker.postMessage({ type: 'query', queryURL: queryURL });
    return;
  }
  // main thread processing
  $.ajax(queryURL, {
    dataType: 'text',
    success: function (data) {
      var cdxLines = data ? data.trim().split('\n') : [];
      if (cdxLines.length === 0) {
        renderCal.displayedCountStr(0, '0');
        return;
      }
      var numCdxEntries = cdxLines.length;
      renderCal.displayedCountStr(numCdxEntries, numCdxEntries.toLocaleString());
      for (var i = 0; i < numCdxEntries; ++i) {
        var cdxObj = JSON.parse(cdxLines[i]);
        if (renderCal.isRenderingCalendarView) {
          renderCal.renderDateCalPart(memoizedYMDT, cdxObj, renderCal.makeTimeInfo(cdxObj), i === 0);
        } else {
          renderCal.renderAdvancedSearchPart(cdxObj);
        }
      }
      var spinner = document.getElementById(renderCal.domStructureIds.updatesSpinner);
      if (spinner) spinner.remove();
    }
  });
};

/**
 * Creates the DOM structure required for rendering the query results based on if we are rendering the
 * calendar view or the advanced query view and populates the containers object
 */
RenderCalendar.prototype.createContainers = function () {
  var queryResults = document.getElementById(this.domStructureIds.capturesMount);
  var queryInfo = document.getElementById(this.domStructureIds.queryInfoId);
  var renderCal = this;
  if (this.isRenderingCalendarView) {
    // create regulars count structure
    this.createAndAddElementTo(queryInfo, {
      tag: 'h3',
      children: [
        { tag: 'i', className: 'fas fa-spinner fa-pulse mr-2', id: this.domStructureIds.updatesSpinner },
        {
          tag: 'b',
          child: {
            tag: 'textNode',
            value: '',
            ref: function (refToElem) {
              renderCal.containers.countTextNode = refToElem;
            }
          }
        },
        { tag: 'textNode', value: ' ' },
        {
          tag: 'b',
          child: {
            tag: 'textNode',
            value: '',
            ref: function (refToElem) {
              renderCal.containers.versionsTextNode = refToElem;
            }
          }
        },
        { tag: 'textNode', value: ' of ' + this.queryURL }
      ]
    });
    // create the row that will hold the results of the regular query
    this.createAndAddElementTo(queryResults, {
      tag: 'div',
      className: 'row q-row',
      children: [
        // years column and initial display structure
        {
          tag: 'div',
          className: 'col-2 pr-1 pl-1 h-100',
          child: {
            tag: 'div',
            className: 'list-group h-100 auto-overflow',
            id: 'year-tab-list',
            attributes: { role: 'tablist' },
            ref: function (refToElem) {
              renderCal.containers.yearsListDiv = refToElem;
            }
          }
        },
        // months initial structure
        {
          tag: 'div',
          className: 'col-2 pr-1 pl-1 h-100',
          child: {
            tag: 'div',
            className: 'tab-content h-100',
            id: 'year-month-tab-list',
            ref: function (refToElem) {
              renderCal.containers.monthsListDiv = refToElem;
            }
          }
        },
        // days initial structure
        {
          tag: 'div',
          className: 'col-8 pl-1 h-100',
          child: {
            tag: 'div',
            className: 'tab-content h-100',
            id: 'year-month-day-tab-list',
            ref: function (refToElem) {
              renderCal.containers.daysListDiv = refToElem;
            }
          }
        }
      ]
    });
    this.containers.updatesSpinner = document.getElementById(this.domStructureIds.updatesSpinner);
    return;
  }
  // create the advanced results query info DOM structure
  var forString = ' for ';
  var forElems;
  if (this.searchParams.has('matchType')) {
    forString = ' for matching ';
    forElems = [
      { tag: 'b', innerText: this.queryURL },
      { tag: 'textNode', value: ' by ' },
      { tag: 'b', innerText: this.searchParams.get('matchType') }
    ];
  } else if (this.searchParams.has('from') || this.searchParams.has('to')) {
    forElems = [{ tag: 'b', innerText: this.queryURL }, { tag: 'textNode', value: ' ' + this.niceDateRange() }];
  } else {
    forElems = [{ tag: 'b', innerText: this.queryURL }];
  }
  this.createAndAddElementTo(queryInfo, {
    tag: 'h3',
    children: [
      { tag: 'i', className: 'fas fa-spinner fa-pulse mr-2', id: this.domStructureIds.updatesSpinner },
      {
        tag: 'b',
        children: [
          {
            tag: 'textNode',
            value: '',
            ref: function (refToElem) {
              renderCal.containers.countTextNode = refToElem;
            }
          },
          { tag: 'textNode', value: ' ' },
          {
            tag: 'textNode',
            value: '',
            ref: function (refToElem) {
              renderCal.containers.versionsTextNode = refToElem;
            }
          }
        ]
      },
      { tag: 'textNode', value: forString }
    ].concat(forElems)
  });
  // next we will display only the URL or the URL + match type or the URL + date range
  // if the executed query contained filters display the humanized version of them
  if (this.searchParams.has('filter')) {
    this.createAndAddElementTo(queryInfo, {
        tag: 'div',
        className: 'col-6',
        children: [
          { tag: 'p', className: 'text-center mb-0 mt-1', innerText: 'Filtering by' },
          {
            tag: 'ul',
            className: 'list-group auto-overflow',
            style: 'max-height: 150px',
            children: this.niceFilterDisplay()
          }
        ]
      }
    );
  }
  // create the advanced results DOM structure
  this.containers.advancedResultsList = this.createAndAddElementTo(queryResults, {
    tag: 'div',
    className: 'row q-row',
    child: {
      tag: 'ul',
      className: 'list-group h-100 auto-overflow w-100'
    }
  }).firstElementChild;
};

/**
 * Updates the calendar view with the supplied cdx information
 * @param {Object} memoizedYMDT - Object containing the counts for the captures
 * @param {Object} cdxObj - CDX object for this capture
 * @param {Object} timeInfo - Object containing the date time information for this capture
 * @param {boolean} active - Should we add the active classes to the markup rendered here
 */
RenderCalendar.prototype.renderDateCalPart = function (memoizedYMDT, cdxObj, timeInfo, active) {
  if (memoizedYMDT[timeInfo.year] == null) {
    // we have not seen this year month day before
    // create the year month day structure (occurs once per result year)
    memoizedYMDT[timeInfo.year] = {
      [timeInfo.month]: {
        [timeInfo.day]: {
          [timeInfo.time]: 1
        }
      }
    };
    this.addRegYearListItem(timeInfo, active);
    this.addRegYearMonthListItem(timeInfo, active);
    return this.addRegYearMonthDayListItem(cdxObj, timeInfo, 1, active);
  } else if (memoizedYMDT[timeInfo.year][timeInfo.month] == null) {
    // we have seen the year before but not the month and day
    // create the month day structure (occurs for every new month encountered for an existing year)
    memoizedYMDT[timeInfo.year][timeInfo.month] = {
      [timeInfo.day]: {
        [timeInfo.time]: 1
      }
    };
    this.addRegYearMonthListItem(timeInfo, active);
    return this.addRegYearMonthDayListItem(cdxObj, timeInfo, 1, active);
  }
  // in cases 1 & 2 a new day at time entry is added otherwise only the captures count is updated (case 3)
  var count = 1;
  var month = memoizedYMDT[timeInfo.year][timeInfo.month];
  if (month[timeInfo.day] == null) {
    // never seen this day (case 1)
    month[timeInfo.day] = {
      [timeInfo.time]: count
    };
  } else if (month[timeInfo.day][timeInfo.time] == null) {
    // we have seen this day before but not at this time (case 2)
    month[timeInfo.day][timeInfo.time] = count;
  } else {
    // we have seen this day at time before so just increment the captures count (case 3)
    count = month[timeInfo.day][timeInfo.time] + 1;
    month[timeInfo.day][timeInfo.time] = count;
  }
  this.addRegYearMonthDayListItem(cdxObj, timeInfo, count, active);
};

/**
 * Updates the advanced view with the supplied cdx information
 * @param {Object} cdxObj - CDX object for this capture
 */
RenderCalendar.prototype.renderAdvancedSearchPart = function (cdxObj) {
// display the URL of the result
  var displayedInfo = [{ tag: 'small', innerText: 'Date Time: ' + this.ts_to_date(cdxObj.timestamp) }];
  // display additional information about the result under the URL
  if (cdxObj.mime) {
    displayedInfo.push({ tag: 'small', innerText: 'Mime Type: ' + cdxObj.mime });
  }
  if (cdxObj.status) {
    displayedInfo.push({ tag: 'small', innerText: 'HTTP Status: ' + cdxObj.status });
  }
  displayedInfo.push({
    tag: 'a',
    attributes: {
      href: this.prefix + '*' + '/' + cdxObj.url,
      target: '_blank'
    },
    child: { tag: 'small', innerText: 'View All Captures' }
  });
  this.createAndAddElementTo(this.containers.advancedResultsList, {
    tag: 'li',
    className: 'list-group-item flex-column align-items-start w-100',
    children: [
      {
        tag: 'a',
        className: 'w-100 text-small long-text',
        attributes: {
          href: this.prefix + cdxObj.timestamp + '/' + cdxObj.url,
          target: '_blank'
        },
        innerText: cdxObj.url
      },
      {
        tag: 'div',
        className: 'pt-1 d-flex w-100 justify-content-between',
        children: displayedInfo
      }
    ]
  });
};

/**
 * Creates and adds a year entry for the calendar view
 * @param {Object} timeInfo - Object containing the date time information for this capture
 * @param {boolean} active - Should we add the active classes to the markup rendered here
 */
RenderCalendar.prototype.addRegYearListItem = function (timeInfo, active) {
  // adds an year to div[id=year-tab-list]
  var renderCal = this;
  var year = timeInfo.year;
  this.createAndAddElementTo(this.containers.yearsListDiv, {
    tag: 'a',
    className: 'list-group-item list-group-item-action' + (active ? ' active' : ''),
    innerText: year,
    attributes: { role: 'tab', href: '#' + this.displayMonthsId(year) },
    dataset: { toggle: 'list' },
    events: {
      // add a click listener to ensure we display the correct year month days combination
      // when choosing a new year or month
      click: function () {
        renderCal.ensureCorrectActive(year);
      }
    }
  });
};

/**
 * Adds a years months to it's month list. If the years month list was not previously created it is created.
 * @param {Object} timeInfo - Object containing the date time information for this capture
 * @param {boolean} active - Should we add the active classes to the markup rendered here
 */
RenderCalendar.prototype.addRegYearMonthListItem = function (timeInfo, active) {
  var yeaMonthsId = this.displayMonthsId(timeInfo.year); // _year-Display-Month
  var yearMonthListId = this.displayMonthsListId(timeInfo.year); // _year-Month-Display-List
  var yml = document.getElementById(yearMonthListId);
  if (yml == null) {
    /*
      we have not created this years month list before before
      so we must create a tab pane for it and month list
      <!-- adding -->
      div[id=_year-Display-Months, role=tabpanel].h-100.tab-pane
        div[id=_year-Display-Months-List, role=tablist].list-group.h-100.auto-overflow
     */
    yml = this.createAndAddElementTo(this.containers.monthsListDiv, {
      tag: 'div',
      className: 'h-100 tab-pane' + (active ? ' active show' : ''),
      id: yeaMonthsId,
      attributes: { role: 'tabpanel' },
      child: {
        tag: 'div',
        className: 'list-group h-100 auto-overflow',
        id: yearMonthListId,
        attributes: { role: 'tablist' }
      }
    }).firstElementChild;
  }
  var renderCal = this;
  var showDaysId = this.displayYearMonthDaysId(timeInfo.year, timeInfo.month);
  var year = timeInfo.year;
  // adds an years month to div[id=_year-Display-Months-List]
  this.createAndAddElementTo(yml, {
    tag: 'a',
    className: 'list-group-item list-group-item-action' + (active ? ' active' : ''),
    innerText: timeInfo.month,
    attributes: {
      role: 'tab',
      href: '#' + showDaysId // _year-month-Display-Days
    },
    events: {
      click: function () {
        renderCal.lastActiveYMD[year] = { month: yeaMonthsId, days: showDaysId };
        renderCal.lastActiveDaysTab = document.getElementById(showDaysId);
      }
    },
    dataset: { toggle: 'list' }
  });
};

/**
 * Updates the number of captures for a day at time for a year month. If the years month month day at time list
 * was not previously created it is created. If the day was not present in it's years months days list it is created.
 * @param {Object} cdxObj - CDX object for this capture
 * @param {Object} timeInfo - Object containing the date time information for this capture
 * @param {number} numCaptures - How many captures do we have currently for this URL
 * @param {boolean} active - Should we add the active classes to the markup rendered here
 */
RenderCalendar.prototype.addRegYearMonthDayListItem = function (cdxObj, timeInfo, numCaptures, active) {
  var yearMonthDaysListId = this.displayYearMonthDaysListId(timeInfo.year, timeInfo.month); // _year-month-Display-Days-List
  var ymlDL = document.getElementById(yearMonthDaysListId);
  if (ymlDL == null) {
    /*
     we have not created this years months day tab and list before before
     so we must create a tab pane for it and days list
     <!-- adding -->
     div[id=_year-month-Display-Days, role=tabpanel].h-100.tab-pane.active.show
       ul[id=_year-month-Display-Days-List].list-group.h-100.auto-overflow
    */
    ymlDL = this.createAndAddElementTo(this.containers.daysListDiv, {
      tag: 'div',
      className: 'h-100 tab-pane' + (active ? ' active show' : ''),
      id: this.displayYearMonthDaysId(timeInfo.year, timeInfo.month),
      attributes: { role: 'tabpanel' },
      child: {
        tag: 'ul',
        className: 'list-group h-100 auto-overflow',
        id: yearMonthDaysListId
      }
    }).firstElementChild;
  }
  // retrieve the existing days num captures display element
  var existingDayId = 'count_' + cdxObj.timestamp;
  var existingDayCount = document.getElementById(existingDayId);
  if (existingDayCount == null) {
    /*
      it does not exist so we have not displayed this day before
     <!-- adding -->
     li.list-group-item
       a[href="replay url"]
       span[id=count_ts].badge.badge-info.badge-pill.float-right
   */
    this.createAndAddElementTo(ymlDL, {
      tag: 'li',
      className: 'list-group-item',
      children: [
        {
          tag: 'a',
          attributes: {
            href: this.prefix + cdxObj.timestamp + '/' + cdxObj.url,
            target: '_blank'
          },
          innerText: timeInfo.month + ' ' + timeInfo.day + this.dateOrdinal(timeInfo.day) + ', ' + timeInfo.year + ' ' + ' at ' + timeInfo.time + '  '
        },
        {
          tag: 'span',
          id: existingDayId,
          className: 'badge badge-info badge-pill float-right',
          ref: function (refToElem) {
            existingDayCount = refToElem;
          }
        }
      ]
    });
    if (active) {
      // populate the lastActives with the selected correct year month days combination
      var daysID = this.displayYearMonthDaysId(timeInfo.year, timeInfo.month);
      this.lastActiveYMD[timeInfo.year] = {
        month: this.displayMonthsId(timeInfo.year),
        days: daysID
      };
      this.lastActiveDaysTab = document.getElementById(daysID);
    }
  }
  existingDayCount.innerText = numCaptures + '';
};

/**
 * Ensures that we display the correct year month days combination when switching year's.
 * Updates the lastActiveDaysTab property.
 * @param {string} year - The year to be shown
 */
RenderCalendar.prototype.ensureCorrectActive = function (year) {
  // un-activates currently active year month day display tab
  if (this.lastActiveDaysTab != null) {
    this.lastActiveDaysTab.classList.remove('active', 'show');
  }
  // activates the last year month day display tab for the current year chosen
  if (this.lastActiveYMD[year] && this.lastActiveYMD[year].days) {
    this.lastActiveDaysTab = document.getElementById(this.lastActiveYMD[year].days);
    this.lastActiveDaysTab.classList.add('active', 'show');
  }
};

/**
 * Creates a DOM element(s) based on the supplied creation options.
 * Creation options:
 *  - tag: The name of the tag to be created (supplied to doc.createElement) or 'textNode' to create a text
 *         node using doc.createTextNode [required]
 *  - value: A string used as the contents for the to be created text node (only used if tag == 'textNode')
 *  - id: An string used to set the `id` of the element
 *  - className: An string of CSS class names used to set the elements `className` property
 *  - style: An string containing style definition(s) used to set the elements `style` property
 *  - innerText: An string used to set the elements `innerText` property
 *  - innerHTML: An string used to set the elements `innerHTML` property
 *  - attributes: An object containing string key value pairs that will be used to set the elements attributes
 *                using element.setAttribute(key, value)
 *  - dataset: An object containing string key value pairs that will be used to set the elements attributes
 *             using element.dataset[key] = value
 *  - events: An object containing string keys and function value pairs that will be used to add event listeners
 *            on the element using addEventListener.addEventListener(key, value)
 *  - child: An object (same properties as the creationOptions parameter for this function) that represent a child
 *           element of the element created using this function, added via element.appendChild once created
 *  - children: An array of objects (same properties as the creationOptions parameter for this function) that
 *             represent a child element of the element created using this function, added via element.appendChild once created
 *  - ref: An function that if supplied will be called with the created element as the only argument
 * @param {Object} creationOptions - Options for new element creation
 * @return {HTMLElement|Node} - The newly created element
 */
RenderCalendar.prototype.createElement = function (creationOptions) {
  if (creationOptions.tag === 'textNode') {
    var tn = document.createTextNode(creationOptions.value);
    if (creationOptions.ref) {
      creationOptions.ref(tn);
    }
    return tn;
  }
  var elem = document.createElement(creationOptions.tag);
  if (creationOptions.id) {
    elem.id = creationOptions.id;
  }
  if (creationOptions.className) {
    elem.className = creationOptions.className;
  }
  if (creationOptions.style) {
    elem.style = creationOptions.style;
  }
  if (creationOptions.innerText) {
    elem.innerText = creationOptions.innerText;
  }
  if (creationOptions.innerHTML) {
    elem.innerHTML = creationOptions.innerHTML;
  }
  if (creationOptions.attributes) {
    var atts = creationOptions.attributes;
    for (var attributeName in atts) {
      elem.setAttribute(attributeName, atts[attributeName]);
    }
  }
  if (creationOptions.dataset) {
    var dataset = creationOptions.dataset;
    for (var dataName in dataset) {
      elem.dataset[dataName] = dataset[dataName];
    }
  }
  if (creationOptions.events) {
    var events = creationOptions.events;
    for (var eventName in events) {
      elem.addEventListener(eventName, events[eventName]);
    }
  }
  if (creationOptions.child) {
    elem.appendChild(this.createElement(creationOptions.child));
  }
  if (creationOptions.children) {
    var kids = creationOptions.children;
    for (var i = 0; i < kids.length; i++) {
      elem.appendChild(this.createElement(kids[i]));
    }
  }
  if (creationOptions.ref) {
    creationOptions.ref(elem);
  }
  return elem;
};

/**
 * Adds the newly created element to the supplied existing element.
 * @param {Node} addTo - The DOM node the newly created element will be added to via addTo.appendChild
 * @param {Object} creationOptions - Options for creating the new element.
 *        See the description of {@link createElement} for more information.
 * @return {HTMLElement|Node} - The newly created element
 */
RenderCalendar.prototype.createAndAddElementTo = function (addTo, creationOptions) {
  var created = this.createElement(creationOptions);
  addTo.appendChild(created);
  return created;
};

/**
 * Returns T/F to indicate if the calender view should be rendered by checking the search params of our current location
 * @param {URLSearchParams} searchParams - The serach params for our current location
 * @returns {boolean}
 */
RenderCalendar.prototype.shouldRenderCalenderView = function (searchParams) {
  // a regular query is one that is just the URL (contains no wild cards) and has no additional constraints
  var url = searchParams.get('url');
  if (url.indexOf('*.') !== -1 || url.indexOf('/*') !== -1) return false;
  return !(searchParams.has('matchType') || searchParams.has('filter'));
};

/**
 * Returns element creation options for the humanized filtering options of the advanced view
 * @returns {Array<Object>}
 */
RenderCalendar.prototype.niceFilterDisplay = function () {
  var filterList = [];
  var qSplit = location.search.split('&');
  for (var i = 0; i < qSplit.length; i++) {
    var match = this.filterRE.exec(qSplit[i]);
    if (match) {
      filterList.push({
        tag: 'li',
        className: 'list-group-item',
        innerText: match[2] + ' ' + this.filterMods[match[1]] + ' ' + match[3]
      });
    }
  }
  return filterList;
};

/**
 * Returns a humanized representation of an advanced queries from or to constraints
 * @returns {string}
 */
RenderCalendar.prototype.niceDateRange = function () {
  var from = this.searchParams.get('from');
  var to = this.searchParams.get('to');
  if (from && to) {
    return 'from ' + from + ' to ' + to;
  } else if (from) {
    return 'from ' + from + ' until ' + 'present';
  }
  return 'from earliest until ' + to;
};

/**
 * Returns the id for a years months tab
 * @param {string} year - The year part for the id
 * @returns {string}
 */
RenderCalendar.prototype.displayMonthsId = function (year) {
  return '_' + year + '-Display-Month';
};

/**
 * Returns the id for displaying a years months list within a years month tab
 * @param {string} year - The year part for the id
 * @returns {string}
 */
RenderCalendar.prototype.displayMonthsListId = function (year) {
  return '_' + year + '-Month-Display-List';
};

/**
 * Returns the id for a year month days tab
 * @param {string} year - The year part for the id
 * @param {string} month - The month part for the id
 * @returns {string}
 */
RenderCalendar.prototype.displayYearMonthDaysId = function (year, month) {
  return '_' + year + '-' + month + '-Display-Days';
};

/**
 * Returns the id for displaying a year month days list within a year month days tab
 * @param {string} year - The year part for the id
 * @param {string} month - The month part for the id
 * @returns {string}
 */
RenderCalendar.prototype.displayYearMonthDaysListId = function (year, month) {
  return '_' + year + '-' + month + '-Display-Days-List';
};

/**
 * Returns a numbers ordinal string
 * @param {number} d - The number to receive the ordinal string for
 * @returns {string}
 */
RenderCalendar.prototype.dateOrdinal = function (d) {
  if (d > 3 && d < 21) return 'th';
  switch (d % 10) {
    case 1:
      return 'st';
    case 2:
      return 'nd';
    case 3:
      return 'rd';
    default:
      return 'th';
  }
};

/**
 * Converts the supplied timestamp to either a local data string or a gmt string (if is_gmt is true)
 * @param {string} ts - The timestamp to be converted to a string
 * @param {boolean} [is_gmt] - Should the timestamp be converted to a gmt string
 * @returns {string}
 */
RenderCalendar.prototype.ts_to_date = function ts_to_date(ts, is_gmt) {
  if (ts.length < 14) return ts;
  var datestr = (ts.substring(0, 4) + '-' +
    ts.substring(4, 6) + '-' +
    ts.substring(6, 8) + 'T' +
    ts.substring(8, 10) + colon +
    ts.substring(10, 12) + colon +
    ts.substring(12, 14) + '-00:00');

  var date = new Date(datestr);
  return is_gmt ? date.toGMTString() : date.toLocaleString();
};

/**
 * Extracts the time information for a cdx object's timestamp
 * @param {Object} cdxObj - The cdx object to have its timestamp information extracted from
 * @returns {{month: string, year: string, time: string, day: string}}
 */
RenderCalendar.prototype.makeTimeInfo = function (cdxObj) {
  var ts = cdxObj.timestamp;
  var day = ts.substring(6, 8);
  return {
    year: ts.substring(0, 4),
    month: this.text.months[ts.substring(4, 6)],
    day: day.charAt(0) === '0' ? day.charAt(1) : day,
    time: ts.substring(8, 10) + colon +
      ts.substring(10, 12) + colon +
      ts.substring(12, 14)
  };
};

/**
 * Updates the displayed number of query results.
 *
 * The version(s) text that is displayed only needs to be updated a maximum of two times.
 * When count (1) === first (1) we are displaying the first or only result and need the
 * singular version text. Otherwise we are displaying result zero or n and need the
 * plural version text. After these two version text updates we are needlessly modifying
 * the element displaying the versions text with the same version.
 * @param {number} count - The number of query results
 * @param {string} countFormatted - The number of query results formatted for display
 * @returns {string}
 */
RenderCalendar.prototype.displayedCountStr = function (count, countFormatted) {
  this.containers.countTextNode.data = countFormatted;
  if (count === first) {
    this.containers.versionsTextNode.data = this.isRenderingCalendarView ? this.text.version : this.text.result;
  } else if (!this.versionString) {
    // case count = 0 or first nth record
    this.versionString = this.isRenderingCalendarView ? this.text.versions : this.text.results;
    this.containers.versionsTextNode.data = this.versionString;
  }
};
