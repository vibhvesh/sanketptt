/**
 * Shared client for Sanket Transcribe.
 * POST raw audio/wav to /api/transcribe. Language and translate use the headers
 * the server allows. Basic auth is sent only when this browser saved a sign-in.
 */
(function (root) {
  var SERVER = "https://stlu-001.sanketptt.com";
  var REMEMBER_KEY = "sanket.ptt2.remember";

  function languageHeader(value) {
    var code = String(value || "").trim().toLowerCase();
    if (code === "hindi") return "hi";
    if (code === "english") return "en";
    if (code === "gujarati") return "gu";
    if (/^[a-z]{2}$/.test(code) && code !== "auto") return code;
    return "";
  }

  function authHeader() {
    try {
      var saved = JSON.parse(localStorage.getItem(REMEMBER_KEY) || "null");
      if (saved && saved.email && saved.password) return "Basic " + btoa(saved.email + ":" + saved.password);
    } catch (e) {
      /* no saved sign-in */
    }
    return "";
  }

  function postOnce(body, options) {
    var headers = { "Content-Type": "audio/wav" };
    var auth = authHeader();
    var language = languageHeader(options && options.language);
    if (auth) headers.Authorization = auth;
    if (language) headers["X-Sanket-Language"] = language;
    if (options && options.translate) headers["X-Sanket-Translate"] = "1";
    var controller = typeof AbortController === "function" ? new AbortController() : null;
    var timer = setTimeout(function () {
      if (controller) controller.abort();
    }, (options && options.timeoutMs) || 15000);
    return fetch(SERVER + "/api/transcribe", {
      method: "POST",
      headers: headers,
      body: body,
      signal: controller ? controller.signal : undefined,
    }).then(function (response) {
      if (!response.ok) throw new Error("Sanket Transcribe returned " + response.status);
      return response.json();
    }).then(function (data) {
      return {
        text: String((data && data.text) || "").trim(),
        language: String((data && data.language) || language || ""),
        segments: (data && data.segments) || [],
      };
    }).finally(function () {
      clearTimeout(timer);
    });
  }

  function postWav(body, options) {
    return postOnce(body, options).catch(function () {
      return postOnce(body, options);
    });
  }

  root.SanketTranscribe = { server: SERVER, postWav: postWav, languageHeader: languageHeader };
})(typeof window !== "undefined" ? window : globalThis);
