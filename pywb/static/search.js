var dtRE = /^\d{4,14}$/;
var didSetWasValidated = false;
var showBadDateTimeClass = 'show-optional-bad-input';

var elemIds = {
  filtering: {
    by: 'filter-by',
    modifier: 'filter-modifier',
    expression: 'filter-expression',
    list: 'filter-list',
    nothing: 'filtering-nothing',
    add: 'add-filter',
    clear: 'clear-filters'
  },
  dateTime: {
    from: 'dt-from',
    fromTime: 'ts-from',
    fromBad: 'dt-from-bad',
    to: 'dt-to',
    toTime: 'ts-to',
    toBad: 'dt-to-bad'
  },
  match: 'match-type-select',
  url: 'search-url',
  form: 'search-form',
  resultsNewWindow: 'open-results-new-window',
  advancedOptions: 'advanced-options',
  resetSearchForm: 'reset-search-form',
};

function resetSearchForm(event) {
  for (const field of [
    elemIds.url,
    elemIds.match,
    elemIds.dateTime.from,
    elemIds.dateTime.fromTime,
    elemIds.dateTime.to,
    elemIds.dateTime.toTime,
  ]) {
    document.getElementById(field).value = '';
  }
  clearFilters(event);
}

function makeCheckDateRangeChecker(dtInputId, dtBadNotice) {
  var dtInput = document.getElementById(dtInputId);
  dtInput.onblur = function() {
    if (
      dtInput.validity.valid &&
      dtBadNotice.classList.contains(showBadDateTimeClass)
    ) {
      return dtBadNotice.classList.remove(showBadDateTimeClass);
    }
    if (dtInput.validity.valueMissing) {
      if (dtBadNotice.classList.contains(showBadDateTimeClass)) {
        dtBadNotice.classList.remove(showBadDateTimeClass);
      }
      return;
    }
    if (dtInput.validity.badInput) {
      if (!dtBadNotice.classList.contains(showBadDateTimeClass)) {
        dtBadNotice.classList.add(showBadDateTimeClass);
      }
      return;
    }
    var validInput = dtRE.test(dtInput.value);
    if (validInput && dtBadNotice.classList.contains(showBadDateTimeClass)) {
      dtBadNotice.classList.remove(showBadDateTimeClass);
    } else if (!validInput) {
      dtBadNotice.classList.add(showBadDateTimeClass);
    }
  };
}

function createAndAddNoFilter(filterList) {
  var nothing = document.createElement('li');
  nothing.innerText = noFilter;
  nothing.id = elemIds.filtering.nothing;
  filterList.appendChild(nothing);
}

function addFilter(event) {
  var by = document.getElementById(elemIds.filtering.by).value;
  if (!by) return;
  var modifier = document.getElementById(elemIds.filtering.modifier).value;
  var expr = document.getElementById(elemIds.filtering.expression).value;
  if (!expr) return;
  var filterExpr = 'filter' + modifier + by + ':' + expr;
  var filterList = document.getElementById(elemIds.filtering.list);
  var previousFilters = filterList.children;
  for (var i = 0; i < previousFilters.length; ++i) {
    var filterData = previousFilters[i].dataset;
    if (filterData && filterData.filter && filterData.filter == filterExpr) return;
  }
  var filterNothing = document.getElementById(elemIds.filtering.nothing);
  if (filterNothing) {
    filterList.removeChild(filterNothing);
  }
  var li = document.createElement('li');
  li.innerText =
    by[0].toUpperCase() +
    by.substr(1) +
    ' ' +
    filterMods[modifier] +
    ' "' +
    expr +
    '"';
  li.dataset.filter = filterExpr;
  var nukeButton = document.createElement('button');
  nukeButton.type = 'button';
  nukeButton.role = 'button';
  nukeButton.className = 'btn btn-outline-danger close';
  nukeButton.setAttribute('aria-label', 'Remove Filter');
  var buttonX = document.createElement('span');
  buttonX.className = 'px-2';
  buttonX.innerHTML = '&times;';
  buttonX.setAttribute('aria-hidden', 'true');
  nukeButton.appendChild(buttonX);
  nukeButton.onclick = function() {
    filterList.removeChild(li);
    if (filterList.children.length === 0) {
      createAndAddNoFilter(filterList);
    }
  };
  li.appendChild(nukeButton);
  filterList.appendChild(li);
  return true;
}

function clearFilters(event) {
  if (document.getElementById(elemIds.filtering.nothing)) return;
  var filterList = document.getElementById(elemIds.filtering.list);
  while (filterList.firstElementChild) {
    filterList.firstElementChild.onclick = null;
    filterList.removeChild(filterList.firstElementChild);
  }
  createAndAddNoFilter(filterList);
}

function performQuery(url) {
  var query = [window.wb_prefix + '*?url=' + encodeURIComponent(url)];
  var filterExpressions = document.getElementById(elemIds.filtering.list)
    .children;
  if (filterExpressions.length) {
    for (var i = 0; i < filterExpressions.length; ++i) {
      var fexpr = filterExpressions[i];
      if (fexpr.dataset && fexpr.dataset.filter) {
        query.push(fexpr.dataset.filter.trim());
      }
    }
  }
  var matchType = document.getElementById(elemIds.match).value;
  if (matchType) {
    query.push('matchType=' + matchType.trim());
  }
  var fromT = document.getElementById(elemIds.dateTime.from).value;
  if (fromT) {
    fromT += document.getElementById(elemIds.dateTime.fromTime).value;
    query.push('from=' + fromT.replace(/[^0-9]/g, ''));
  }
  var toT = document.getElementById(elemIds.dateTime.to).value;
  if (toT) {
    toT += document.getElementById(elemIds.dateTime.toTime).value;
    query.push('to=' + toT.replace(/[^0-9]/g, ''));
  }
  var builtQuery = query.join('&');
  if (document.getElementById(elemIds.resultsNewWindow).checked) {
    try {
      var win = window.open(builtQuery);
      win.focus();
    } catch (e) {
      document.location.href = builtQuery;
    }
  } else {
    document.location.href = builtQuery;
  }
}

function validateFields(form) {
  if (!didSetWasValidated) {
    form.classList.add('was-validated');
    didSetWasValidated = true;
  }
}

function submitForm(event, form, searchURLInput) {
  event.preventDefault();
  event.stopPropagation();
  var url = searchURLInput.value;
  if (!url) {
    validateFields(form);
    return;
  }
  performQuery(url);
}

$(document).ready(function() {
  $('[data-toggle="tooltip"]').tooltip({
    container: 'body',
    delay: { show: 1000 }
  });
  makeCheckDateRangeChecker(
    elemIds.dateTime.from,
    document.getElementById(elemIds.dateTime.fromBad)
  );
  makeCheckDateRangeChecker(
    elemIds.dateTime.to,
    document.getElementById(elemIds.dateTime.toBad)
  );
  document.getElementById(elemIds.resetSearchForm).onclick = resetSearchForm;
  document.getElementById(elemIds.filtering.add).onclick = addFilter;
  document.getElementById(elemIds.filtering.clear).onclick = clearFilters;
  var searchURLInput = document.getElementById(elemIds.url);
  var form = document.getElementById(elemIds.form);
  form.addEventListener('submit', function(event) {
    submitForm(event, form, searchURLInput);
  });
  var filteringExpression = document.getElementById(elemIds.filtering.expression);
  filteringExpression.addEventListener("keypress", function(event) {
    if (event.key === "Enter") {
      event.preventDefault();
      if (! addFilter()) {
        submitForm(event, form, searchURLInput);
      }
    }
  });
});
