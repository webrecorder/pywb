const PywbMonthLabels = {1:"Jan", 2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"};

export function PywbData(rawSnaps) {
  const allTimePeriod = new PywbPeriod({type: PywbPeriod.Type.all, id: "all"});
  const snapshots = [];
  let lastSingle = null;
  rawSnaps.forEach((rawSnap, i) => {
    const snap = new PywbSnapshot(rawSnap, i);
    let year, month, day, hour, single;
    if (!(year = allTimePeriod.getChildById(snap.year))) {
      year = new PywbPeriod({type: PywbPeriod.Type.year, id: snap.year});
      allTimePeriod.addChild(year);
    }
    if (!(month = year.getChildById(snap.month))) {
      month = new PywbPeriod({type: PywbPeriod.Type.month, id: snap.month});
      year.addChild(month);
    }
    if (!(day = month.getChildById(snap.day))) {
      day = new PywbPeriod({type: PywbPeriod.Type.day, id: snap.day});
      month.addChild(day);
    }
    const hourValue = Math.ceil((snap.hour + .0001) / (24/8)); // divide day in 4 six-hour periods (aka quarters)
    //const hourValue = snap.hour;
    if (!(hour = day.getChildById(hourValue))) {
      hour = new PywbPeriod({type: PywbPeriod.Type.hour, id: hourValue});
      day.addChild(hour);
    }
    if (!(single = hour.getChildById(snap.id))) {
      single = new PywbPeriod({type: PywbPeriod.Type.snapshot, id: snap.id});
      hour.addChild(single);
    }
    single.setSnapshot(snap);
    if (lastSingle) {
      lastSingle.setNextSnapshotPeriod(single);
      single.setPreviousSnapshotPeriod(lastSingle);
    }
    lastSingle = single;

    snapshots.push(snap);
  });

  this.timeline = allTimePeriod;
  this.snapshots = snapshots;
  this.getSnapshot = function(index) {
    if (index < 0 || index >= this.snapshots.length) {
      return null;
    }
    return this.snapshots[index];
  };
  this.getPreviousSnapshot = function(snapshot) {
    const index = snapshot.index;
    return this.getSnapshot(index-1);
  };
  this.getNextSnapshot = function(snapshot) {
    const index = snapshot.index;
    return this.getSnapshot(index+1);
  };
}
/* ---------------- SNAP SHOT object ----------------- */
export class PywbSnapshot {
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
    return `${this.year}-${PywbMonthLabels[this.month]}-${this.day} ${this.getTimeFormatted()}`;
  }

  getDateFormatted() {
    return `${this.year}-${PywbMonthLabels[this.month]}-${this.day}`;
  }

  getTimeFormatted() {
    return (this.hour < 13 ? this.hour : (this.hour % 12)) + ":" + ((this.minute < 10 ? "0":"")+this.minute) + ":" + ((this.second < 10 ? "0":"")+this.second) + " " + (this.hour < 12 ? "am":"pm");
  }
}

/* ---------------- PERIOD object ----------------- */
export function PywbPeriod(init) {
  this.type = init.type;
  this.id = init.id;

  this.childrenIds = {}; // allow for query by ID
  this.children = []; // allow for sequentiality / order

  this.maxGrandchildSnapshotCount = 0;
  this.snapshotCount = 0;
}
PywbPeriod.Type = {all: 0,year: 1,month: 2,day: 3,hour: 4,snapshot:5};
PywbPeriod.TypeLabel = ["timeline","year","month","day","hour","snapshot"];

PywbPeriod.prototype.getTypeLabel = function() {
  return PywbPeriod.TypeLabel[this.type];
};
PywbPeriod.GetTypeLabel = function(type) {
  return PywbPeriod.TypeLabel[type] ? PywbPeriod.TypeLabel[type] : "";
};

PywbPeriod.prototype.getChildById = function(id) {
  return this.children[this.childrenIds[id]];
};

// previous period (ONLY SET at the period level/type: snapshot)
PywbPeriod.prototype.getPreviousSnapshotPeriod = () => {};
PywbPeriod.prototype.setPreviousSnapshotPeriod = function(period) {
  this.getPreviousSnapshotPeriod = () => period;
};
// next period (ONLY SET at the period level/type: snapshot)
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
  let iFailSafe = 100; // in case a parser has a bug and the snapshotCount is not correct; avoid infinite-loop
  while (period.snapshotCount && period.type !== PywbPeriod.Type.snapshot) {
    let i = 0;
    for(i=0; i < period.children.length; i++) {
      const ii = direction === "first" ? i : (period.children.length - 1 - i);
      if (period.children[ii].snapshotCount) {
        period = period.children[ii];
        break;
      }
    }
    if (iFailSafe-- < 0) {
      break;
    }
  }
  if (period.type === PywbPeriod.Type.snapshot && period.snapshot) {
    return period;
  }
  return null;
};

PywbPeriod.prototype.getPrevious = function() {
  const firstSnapshotPeriod = this.getFirstSnapshotPeriod();
  if (!firstSnapshotPeriod) {
    return null;
  }
  const previousSnapshotPeriod = firstSnapshotPeriod.getPreviousSnapshotPeriod();
  if (!previousSnapshotPeriod) {
    return null;
  }
  if (this.type === PywbPeriod.Type.snapshot) {
    return previousSnapshotPeriod;
  }
  let parent = previousSnapshotPeriod.parent;
  while(parent) {
    if (parent.type === this.type) {
      break;
    }
    parent = parent.parent;
  }
  return parent;
};
PywbPeriod.prototype.getNext = function() {
  const lastSnapshotPeriod = this.getLastSnapshotPeriod();
  if (!lastSnapshotPeriod) {
    return null;
  }
  const nextSnapshotPeriod = lastSnapshotPeriod.getNextSnapshotPeriod();
  if (!nextSnapshotPeriod) {
    return null;
  }
  if (this.type === PywbPeriod.Type.snapshot) {
    return nextSnapshotPeriod;
  }
  let parent = nextSnapshotPeriod.parent;
  while(parent) {
    if (parent.type === this.type) {
      break;
    }
    parent = parent.parent;
  }
  return parent;
};

PywbPeriod.prototype.parent = null;
PywbPeriod.prototype.addChild = function(period) {
  if (this.getChildById(period.id)) {
    return false;
  }
  period.parent = this;
  this.childrenIds[period.id] = this.children.length;
  this.children.push(period);
  return true;
};

PywbPeriod.prototype.getChildrenRange = function() {
  switch (this.type) {
  case PywbPeriod.Type.all:
    // year range: first to last year available
    return [this.children[0].id, this.children[this.children.length-1].id];
  case PywbPeriod.Type.year:
    // month is simple: 1 to 12
    return [1,12];
  case PywbPeriod.Type.month:
    // days in month: 1 to last day in month
    const y = this.parent.id; const m = this.id;
    const lastDateInMonth = (new Date((new Date(y, m, 1)).getTime() - 1000)).getDate(); // 1 sec earlier
    return [1, lastDateInMonth];
  case PywbPeriod.Type.day:
    // hours: 0 to 23
    // return [1,4];
    return [1,8];
  }
  return null;
};
PywbPeriod.prototype.fillEmptyGrancChildPeriods = function() {
  if (this.hasFilledEmptyGrandchildPeriods) {
    return;
  }
  this.children.forEach(c => {
    c.fillEmptyChildPeriods();
  });
  this.hasFilledEmptyGrandchildPeriods = true;
};

PywbPeriod.prototype.fillEmptyChildPeriods = function(isFillEmptyGrandChildrenPeriods=false) {
  if (this.snapshotCount === 0 || this.type > PywbPeriod.Type.day) {
    return;
  }

  if (isFillEmptyGrandChildrenPeriods) {
    this.fillEmptyGrancChildPeriods();
  }

  if (this.hasFilledEmptyChildPeriods) {
    return;
  }
  this.hasFilledEmptyChildPeriods = true;

  const idRange = this.getChildrenRange();
  if (!idRange) {
    return;
  }

  let i = 0;
  for (let newId = idRange[0]; newId <= idRange[1]; newId++) {
    if (i < this.children.length) {
      // if existing and new id match, skip, item already in place
      // else
      if (this.children[i].id !== newId) {
        const empty = new PywbPeriod({type: this.type + 1, id: newId});
        if (newId < this.children[i].id) {
          // insert new before existing
          this.children.splice(i, 0, empty);
        } else {
          // insert new after existing
          this.children.splice(i+1, 0, empty);
        }
        // manually push children (no need to reverse link parent
        //empty.parent = this;
      }
      i++;
    } else {
      const empty = new PywbPeriod({type: this.type + 1, id: newId});
      this.children.push(empty);
      // manually push children (no need to reverse link parent
      //empty.parent = this;
    }
  }

  // re-calculate indexes
  for(let i=0;i<this.children.length;i++) {
    this.childrenIds[this.children[i].id] = i;
  }

  return idRange;
};

PywbPeriod.prototype.getParents = function(skipAllTime=false) {
  let parents = [];
  let parent = this.parent;
  while(parent) {
    parents.push(parent);
    parent = parent.parent;
  }
  parents = parents.reverse();
  if (skipAllTime) {
    parents.shift(); // skip first "all-time"
  }
  return parents;
};

PywbPeriod.prototype.snapshot = null;
PywbPeriod.prototype.setSnapshot = function(snap) {
  this.snapshot = snap;
  this.snapshotCount++;
  let parent = this.parent;
  let child = this;
  while (parent) {
    parent.snapshotCount++;

    let grandParent = parent.parent;
    if (grandParent) { // grandparent
      grandParent.maxGrandchildSnapshotCount = Math.max(grandParent.maxGrandchildSnapshotCount, child.snapshotCount);
    }
    child = parent;
    parent = parent.parent;
  }
};

PywbPeriod.prototype.getFullReadableId = function(hasDayCardinalSuffix) {
  // remove "all-time" from parents (getParents(true) when printing readable id (of all parents and currrent
  return this.getParents(true).map(p => p.getReadableId(hasDayCardinalSuffix)).join(" ") + " " + this.getReadableId(hasDayCardinalSuffix);
};
PywbPeriod.prototype.getReadableId = function(hasDayCardinalSuffix) {
  switch (this.type) {
  case PywbPeriod.Type.all:
    return "All-time";
  case PywbPeriod.Type.year:
    return this.id;
  case PywbPeriod.Type.month:
    return PywbMonthLabels[this.id];
  case PywbPeriod.Type.day:
    let suffix = "";
    if (hasDayCardinalSuffix) {
      const singleDigit = this.id % 10;
      const isTens = Math.floor(this.id / 10) === 1;
      const suffixes = {1:"st", 2:"nd",3:"rd"};
      suffix = (isTens || !suffixes[singleDigit]) ? "th" : suffixes[singleDigit];
    }
    return this.id + suffix;
  case PywbPeriod.Type.hour:
    return ({1:"12 am", 2: "3 am", 3: "6 am", 4: "9 am", 5: "noon", 6: "3 pm", 7: "6 pm", 8: "9 pm"})[this.id];
    //return ({1:'midnight', 2: '6 am', 3: 'noon', 4: '6 pm'})[this.id];
    //return (this.id < 13 ? this.id : this.id % 12) + ' ' + (this.id < 12 ? 'am':'pm');
  case PywbPeriod.Type.snapshot:
    return this.snapshot.getTimeFormatted();
  }
};
