/** 
 * nguyenj/fullscreen-polyfill
 * https://github.com/nguyenj/fullscreen-polyfill 
 * MIT License

 * Copyright (c) 2018 John Ngyen

 * Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

 * The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES 
 * OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE 
 * LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR 
 * IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */

const spec = [
  "fullscreen",
  "fullscreenEnabled",
  "fullscreenElement",
  "fullscreenchange",
  "fullscreenerror",
  "exitFullscreen",
  "requestFullscreen",
];

const webkit = [
  "webkitIsFullScreen",
  "webkitFullscreenEnabled",
  "webkitFullscreenElement",
  "webkitfullscreenchange",
  "webkitfullscreenerror",
  "webkitExitFullscreen",
  "webkitRequestFullscreen",
];

const moz = [
  "mozFullScreen",
  "mozFullScreenEnabled",
  "mozFullScreenElement",
  "mozfullscreenchange",
  "mozfullscreenerror",
  "mozCancelFullScreen",
  "mozRequestFullScreen",
];

const ms = [
  "",
  "msFullscreenEnabled",
  "msFullscreenElement",
  "MSFullscreenChange",
  "MSFullscreenError",
  "msExitFullscreen",
  "msRequestFullscreen",
];

// Make sure document exist, if it doesn't make it a dumb object
document ? document : (document = {});

// Get the vendor fullscreen prefixed api
const fsVendorKeywords = (function getFullscreenApi() {
  const fullscreenEnabled = [spec[1], webkit[1], moz[1], ms[1]].find(
    (prefix) => document[prefix]
  );
  return (
    [spec, webkit, moz, ms].find((vendor) => {
      return vendor.find((prefix) => prefix === fullscreenEnabled);
    }) || []
  );
})();

function handleEvent(eventType, event) {
  document[spec[0]] =
    document[fsVendorKeywords[0]] || !!document[fsVendorKeywords[2]] || false;
  document[spec[1]] = document[fsVendorKeywords[1]] || false;
  document[spec[2]] = document[fsVendorKeywords[2]] || null;
  document.dispatchEvent(new Event(eventType), event.target);
}

function setupShim() {
  // fullscreen
  // Defaults to false for cases like MS where they do not have this
  // attribute. Another way to check whether fullscreen is active is to look
  // at the fullscreenElement attribute.
  document[spec[0]] =
    document[fsVendorKeywords[0]] || !!document[fsVendorKeywords[2]] || false;

  // fullscreenEnabled
  document[spec[1]] = document[fsVendorKeywords[1]] || false;

  // fullscreenElement
  document[spec[2]] = document[fsVendorKeywords[2]] || null;

  // onfullscreenchange
  document.addEventListener(
    fsVendorKeywords[3],
    handleEvent.bind(document, spec[3]),
    false
  );

  // onfullscreenerror
  document.addEventListener(
    fsVendorKeywords[4],
    handleEvent.bind(document, spec[4]),
    false
  );

  // exitFullscreen
  document[spec[5]] = function () {
    return document[fsVendorKeywords[5]]();
  };

  // requestFullscreen
  Element.prototype[spec[6]] = function () {
    return this[fsVendorKeywords[6]].apply(this, arguments);
  };
}

// Don't polyfill if it already exist
typeof document[spec[1]] !== "undefined" || !fsVendorKeywords.length ? {} : setupShim();
