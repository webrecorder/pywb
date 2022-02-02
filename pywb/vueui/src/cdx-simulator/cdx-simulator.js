const getMonthDays = (y, mZeroIndex) => {
  const firstOfNextMonth = new Date(y, mZeroIndex+1, 1);
  const lastOfMonth = new Date(firstOfNextMonth - 1000 * 3600 * 24);
  return lastOfMonth.getDate();
}

// read dynamically from local storage options for make
let simulateCdxOptions = window.localStorage.getItem('cdx_simulate');
simulateCdxOptions = !!simulateCdxOptions ? JSON.parse(simulateCdxOptions) : {};

class CDXRecordFactory {
  constructor() {}

  async make(url, opts={}) {
    // defaults
    opts = {count:1000, yearStart:2015, yearEnd:2022, fetchTime:5*1000, ...opts};

    const records = [];

    const total = opts.count;
    const years = [opts.yearStart, opts.yearEnd];
    const avgPerMonth = total / (years[1]-years[0]) / 12;
    // exaggerate max count per day, any day can hold up to 10th of the month's captures
    const maxPerDay = avgPerMonth/10;

    let startTime = Math.floor(new Date().getTime());
    let recordI = 0;

    for(let y=years[0]; y<=years[1]; y++) {
      for(let m=1; m<=12; m++) {
        for(let d=1; d<=getMonthDays(y, m-1); d++) {
          const dayTimestampPrefix = y + ('0'+m).substr(-2) + ('0'+d).substr(-2);
          // minumum to maximum count (random value)
          const timesCount = Math.floor(Math.random() * maxPerDay);

          const times = {}; // make sure we save to hash to de-dupe
          for(let i=0; i<timesCount; i++) {
            const newTime = [Math.floor(Math.random()*24), Math.floor(Math.random()*60), Math.floor(Math.random()*60)].join('');
            times[newTime] = 1;
          }
          Object.keys(times).sort().forEach(time => {
            records.push({url, timestamp: dayTimestampPrefix+time});
          });
        }
      }
    }
    let endTime = Math.floor(new Date().getTime());

    if (opts.fetchTime && opts.fetchTime > endTime - startTime) { // wait till we reac fetchTime
      const p = new Promise((resolve) => {
        setTimeout(() => {
          resolve(true);
        }, (opts.fetchTime - (endTime - startTime)));
      });
      await p;
    }
    return records;
  }
}

export class CDXQueryWorkerSimulator {
  constructor(workerPath) {
    this.messageCb = [];
    this.recordFactory = new CDXRecordFactory();
  }


  addEventListener(type, cb) {
    if (type === 'message') {
      this.messageCb = cb;
    }
  }

  async postMessage({type, queryUrl}) {
    const records = await this.recordFactory.make(queryUrl, simulateCdxOptions);
    records.forEach(record => this.messageCb({data: {type: 'cdxRecord', record}}));
    this.messageCb({data: {type: 'finished'}});
  }

  terminate() {
    return true;
  }
}
