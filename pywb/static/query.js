var Text = {
  months: {
   '01': "January",
   '02': "February",
   '03': "March",
   '04': "April",
   '05': "May",
   '06': "June",
   '07': "July",
   '08': "August",
   '09': "September",
   '10': "October",
   '11': "November",
   '12': "December",
  },
  version: "capture",
  versions: "captures",
};

function RenderCalendar(prefix, url) {
  var years = [];

  function ts_to_date(ts, is_gmt)
  {
    if (ts.length < 14) {
      return ts;
    }

    var datestr = (ts.substring(0, 4) + "-" +
      ts.substring(4, 6) + "-" +
      ts.substring(6, 8) + "T" +
      ts.substring(8, 10) + ":" +
      ts.substring(10, 12) + ":" +
      ts.substring(12, 14) + "-00:00");

    var date = new Date(datestr);
    if (is_gmt) {
      return date.toGMTString();
    } else {
      return date.toLocaleString();
    }
  }

  function getYearTs(ts){
    return ts.substring(0, 4);
  }

  function getMonthTs(ts){
    return ts.substring(4, 6);
  }

  function getDayTs(ts){
    var day = ts.substring(6, 8);
    if (day.charAt(0) == '0') {
      day = day.charAt(1);
    }
    return day;
  }

  function getHoursMinutesTs(ts){
    return ts.substring(8, 10) + ':' + ts.substring(10, 12);
  }


  function getMonthName(ts){
    var month = getMonthTs(ts);
    return Text.months[month];
  }

  /*Get unique values from array*/
  function uniques(arr) {
    var a = [];
    for (var i = 0, l = arr.length; i < l; i++) {
      if (a.indexOf(arr[i]) === -1 && arr[i] !== '') {
        a.push(arr[i]);
      }
    }
    return a;
  }

  function init() {
    $.ajax(prefix + "cdx", {
      data: {"url": url, "output": "json"},
      dataType: "text",
      success: function(data) {
        processAll(data.trim());
      }
    });
  }

  function processAll(data) {
    var cdxLines = [];

    if (data) {
        cdxLines = data.split("\n");
    }

    $("#count").text(numVersionsText(cdxLines.length));

    for (var i = 0; i < cdxLines.length; i++) {
      var obj = JSON.parse(cdxLines[i]);
      processUrl(prefix, obj.timestamp, obj.url);
    }
    yearCount();
    handleClicks();
  }

  function numVersionsText(count) {
    var text = count + " ";
    text += count == 1 ? Text.version : Text.versions;
    return text;
  }
 

  function processUrl(prefix, ts, url) {
    var currentYear = getYearTs(ts);
    years.push(currentYear);

    var currentMonth = getMonthName(ts);
    var currentDay = getDayTs(ts);
    var currentHoursMinutes = getHoursMinutesTs(ts);

    if (! $('#year_' + currentYear).length){
      $("#captureYears").append('<div class="row"><a class="year col-xs-12 col-md-offset-1 col-md-10 col-lg-offset-2 col-lg-8" id="year_' + currentYear + '"><h4 class="text-left ">' + getYearTs(ts) + '<span id="'  +currentYear + '_right" class="pull-right"><i class="fa iCarret yearCarret fa-caret-down" aria-hidden="true"></i></span></h4></a></div><div class="months" id="months_' + currentYear + '"></div></div>'); /*insert year div if it does not exist*/
    }

    if (! $('#month_' + currentYear + '_' + currentMonth).length){
      $('#months_' + currentYear).append('<div class="row"><a class= "month col-xs-12 col-md-offset-1 col-md-10 col-lg-offset-2 col-lg-8" id="month_' + currentYear + '_' + currentMonth + '"><h5 class="text-left">'+ currentMonth + '<i class="pull-right fa fa-caret-down iCarret monthCarret" aria-hidden="true"></i></h5></a></div><div class="days" id="days_' + currentYear + '_' + currentMonth + '"></div>'); /*insert month div if it does not exist*/
    }

    //always insert current capture, assuming no duplicates
    $('#days_' + currentYear + '_' + currentMonth).append('<div class="row"><div id="day_' + currentYear + '_' + currentMonth + '_' + currentDay + '"><a class="day col-xs-12 col-md-offset-1 col-md-10 col-lg-offset-2 col-lg-8" href="' + prefix + ts + "/" + url + '">' + currentDay + ' ' + currentMonth + ' at ' + currentHoursMinutes + '</a></div></div>'); /*insert month div if it does not exist*/
  }

  function yearCount() {
    //Insert number of versions for each year
    years = uniques(years); //get list of years with versions
    var numberofVersions;
    var versionsString;

    for (var i = 0; i < years.length; i++) {
      numberofVersions = $('#year_' + years[i].toString()).parent().next().find(".day").length;
      $('#' + years[i] + '_right').prepend(numVersionsText(numberofVersions));
    }
  }

  // Init
  function handleClicks() {
    $(".year").click(function() {
      $(this).find(".yearCarret").toggleClass('fa-caret-up fa-caret-down');
      $(this).parent().next().slideToggle( "fast", "linear" );
    });
    $(".month").click(function() {
      $(this).find(".monthCarret").toggleClass('fa-caret-up fa-caret-down'); 
      $(this).parent().next().slideToggle( "fast", "linear" );
    });
  };

  init();

};

