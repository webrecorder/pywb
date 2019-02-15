var colon = ':';
var monthToText = {
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
};

var recordCount = 0;

// sentinel representing the \n character as an uint8 value
var newLine = 10;

// options used when converting a response body chunk represented as an Uint8Array to a string
var decoderOptions = { stream: true };

// TextDecoder instance use to convert the current chunk returned by the stream of the response body
var decoder = new TextDecoder('utf-8');

/**
 * The remaining string contents of the current response body chunk when we have not consumed
 * in its integrity, pre-pended to the next chunk
 * @type {Uint8Array}
 */
var bufferedPreviousChunk = null;

self.onmessage = function (event) {
  var data = event.data;
  if (data.type === 'query') {
    fetch(data.queryURL)
      .then(consumeResponseBodyAsStream)
      .catch(defaultErrorCatcher);
  }
};

function defaultErrorCatcher(error) {
  console.error('A fatal error occurred', error);
  self.postMessage({
    type: 'finished',
    recordCount: recordCount,
    recordCountFormatted: recordCount.toLocaleString()
  });
}

/**
 * Consumes the entirety of the response body by converting it into chunks
 * @param {Response} response
 */
function consumeResponseBodyAsStream(response) {
  var reader = response.body.getReader();
  reader.read()
    .then(function consumeStream(result) {
      if (result.done) {
        if (bufferedPreviousChunk) {
          var lastChunk = bufferedPreviousChunk;
          bufferedPreviousChunk = null;
          consumeChunk(lastChunk, true);
        }
        self.postMessage({
          type: 'finished',
          recordCount: recordCount,
          recordCountFormatted: recordCount.toLocaleString()
        });
        return;
      }
      transformChunk(result.value);
      reader.read().then(consumeStream).catch(defaultErrorCatcher);
    })
    .catch(defaultErrorCatcher);
}

/**
 * @desc Process a chunk that was returned from the reader (ReadableStream) for the query response body.
 * If we buffered a part of the previous chunk the previous chunk that was buffered is concatenated with
 * the current chunk
 * @param {Uint8Array} currentChunk - The current chunk of the response body to be transformed
 */
function transformChunk(currentChunk) {
  var chunk;
  if (bufferedPreviousChunk) {
    // concatenate the bufferedPreviousChunk chunk with the current chunk
    chunk = new Uint8Array(bufferedPreviousChunk.length + currentChunk.length);
    chunk.set(bufferedPreviousChunk);
    chunk.set(currentChunk, bufferedPreviousChunk.length);
    bufferedPreviousChunk = null;
  } else {
    chunk = currentChunk;
  }
  consumeChunk(chunk, false);
}

/**
 * @desc Extracts the individual cdx records from current chunk by performing binary
 * splitting on the \n character
 * @param {Uint8Array} chunk - The current chunk of the response body to be processed
 * @param {boolean} last - indicates that this is the last chunk to be processed
 */
function consumeChunk(chunk, last) {
  var offset = 0;
  var lastMatch = 0;
  var idx;
  var maybeCDXRecord;
  var chunkLen = chunk.length;
  while (true) {
    // idx will equal the index of the next \n from the current offset
    idx = offset >= chunkLen ? -1 : chunk.indexOf(newLine, offset);
    if (idx !== -1 && idx < chunkLen) {
      // extract the next json record from last match up to and including the newline
      maybeCDXRecord = chunk.slice(lastMatch, idx + 1);
      if (maybeCDXRecord.length > 0) {
        handleCDXRecord(maybeCDXRecord);
      }
      // idx = position of \n in front of the last } so we add 1 to it for our next offset
      offset = idx + 1;
      // make last match our current offset for the else branch
      lastMatch = offset;
    } else {
      // idx reached the end of the current chunk and we now need to check if we should buffer
      // any remaining portion of the current chunk
      if (lastMatch < chunkLen) {
        bufferedPreviousChunk = chunk.slice(lastMatch);
      }
      if (last && bufferedPreviousChunk && bufferedPreviousChunk.length > 0) {
        handleCDXRecord(bufferedPreviousChunk);
      }
      break;
    }
  }
}

/**
 * Converts the Uint8Array representation of the potential cdx object into an UTF-8 string and
 * then attempts to convert it into a JSON object. If the conversion process was successful
 * we post a message containing the conversion results to query results page we were created from
 * @param {Uint8Array} binaryCDXRecord - The potential cdx object to be converted
 */
function handleCDXRecord(binaryCDXRecord) {
  var decodedCDXRecord;
  var cdxRecord;
  try {
    decodedCDXRecord = decoder.decode(binaryCDXRecord, decoderOptions).trim();
    if (!decodedCDXRecord) return; // we had an empty string or a string with only whitespace and or \n
  } catch (e) {
    console.error('failed to decode the potential cdx record', e);
    return;
  }
  try {
    cdxRecord = JSON.parse(decodedCDXRecord);
  } catch (e) {
    console.error('bad JSON in the potential cdx record', e);
    return;
  }
  recordCount += 1;
  var ts = cdxRecord.timestamp;
  var day = ts.substring(6, 8);
  self.postMessage({
    type: 'cdxRecord',
    record: cdxRecord,
    timeInfo: {
      year: ts.substring(0, 4),
      month: monthToText[ts.substring(4, 6)],
      day: day.charAt(0) === '0' ? day.charAt(1) : day,
      time: ts.substring(8, 10) + colon +
        ts.substring(10, 12) + colon +
        ts.substring(12, 14)
    },
    wasError: false,
    recordCount: recordCount,
    recordCountFormatted: recordCount.toLocaleString()
  });
}






