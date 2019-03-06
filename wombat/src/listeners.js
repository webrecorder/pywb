/* eslint-disable camelcase */

/**
 *
 * @param {Function} origListener
 * @param {Window} win
 * @return {Function}
 */
export function wrapSameOriginEventListener(origListener, win) {
  return function wrappedSameOriginEventListener(event) {
    if (window != win) {
      return;
    }
    return origListener(event);
  };
}

/**
 * @param {Function} origListener
 * @param {Object} obj
 * @param {Wombat} wombat
 * @return {Function}
 */
export function wrapEventListener(origListener, obj, wombat) {
  return function wrappedEventListener(event) {
    var ne;

    if (event.data && event.data.from && event.data.message) {
      if (
        event.data.to_origin !== '*' &&
        obj.WB_wombat_location &&
        !wombat.startsWith(event.data.to_origin, obj.WB_wombat_location.origin)
      ) {
        console.warn(
          'Skipping message event to ' +
            event.data.to_origin +
            " doesn't start with origin " +
            obj.WB_wombat_location.origin
        );
        return;
      }

      var source = event.source;

      if (event.data.from_top) {
        source = obj.__WB_top_frame;
      } else if (
        event.data.src_id &&
        obj.__WB_win_id &&
        obj.__WB_win_id[event.data.src_id]
      ) {
        source = obj.__WB_win_id[event.data.src_id];
      }

      ne = new MessageEvent('message', {
        bubbles: event.bubbles,
        cancelable: event.cancelable,
        data: event.data.message,
        origin: event.data.from,
        lastEventId: event.lastEventId,
        source: wombat.proxyToObj(source),
        ports: event.ports
      });

      ne._target = event.target;
      ne._srcElement = event.srcElement;
      ne._currentTarget = event.currentTarget;
      ne._eventPhase = event.eventPhase;
      ne._path = event.path;
    } else {
      ne = event;
    }

    return origListener(ne);
  };
}
