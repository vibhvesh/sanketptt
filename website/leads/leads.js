(function () {
  var token = sessionStorage.getItem("sanket-leads-token") || "";
  var meta = null;
  var currentId = null;
  var picks = { country: null, state: null, city: null };

  var gate = document.getElementById("gate");
  var desk = document.getElementById("desk");
  var gateError = document.getElementById("gate-error");
  var serviceInput = document.getElementById("service");
  serviceInput.value = localStorage.getItem("sanket-leads-api") || window.SANKET_LEADS_API || "";

  function apiBase() {
    return (serviceInput.value || localStorage.getItem("sanket-leads-api") || window.SANKET_LEADS_API || "").replace(/\/$/, "");
  }

  function request(path, options) {
    options = options || {};
    var headers = Object.assign({}, options.headers || {});
    if (token) headers.Authorization = "Bearer " + token;
    if (options.body && !headers["Content-Type"]) headers["Content-Type"] = "application/json";
    return fetch(apiBase() + path, {
      method: options.method || "GET",
      headers: headers,
      body: options.body || null
    }).then(function (response) {
      if (response.status === 401) throw new Error("That password was not accepted.");
      if (!response.ok) {
        return response.json().catch(function () { return {}; }).then(function (body) {
          throw new Error(body.detail || "The lead service could not complete that request.");
        });
      }
      return response;
    });
  }

  function combo(inputId, listId, source) {
    var input = document.getElementById(inputId);
    var list = document.getElementById(listId);
    var options = [];
    var active = -1;
    var remoteTimer = 0;
    var chosen = null;

    function close() {
      list.hidden = true;
      input.setAttribute("aria-expanded", "false");
    }

    function render(items) {
      list.innerHTML = "";
      items.forEach(function (item, index) {
        var li = document.createElement("li");
        var button = document.createElement("button");
        button.type = "button";
        button.setAttribute("role", "option");
        button.setAttribute("aria-selected", index === active ? "true" : "false");
        button.textContent = item.label;
        button.addEventListener("mousedown", function (event) {
          event.preventDefault();
          choose(item);
        });
        li.appendChild(button);
        list.appendChild(li);
      });
      list.hidden = items.length === 0;
      input.setAttribute("aria-expanded", String(!list.hidden));
    }

    function filtered() {
      var query = input.value.trim().toLowerCase();
      return options.filter(function (item) {
        return !query || item.label.toLowerCase().indexOf(query) !== -1;
      }).slice(0, 12);
    }

    function choose(item) {
      chosen = item;
      input.value = item.label;
      close();
      if (source.onPick) source.onPick(item);
    }

    function open() {
      active = -1;
      var items = filtered();
      render(items);
      if (source.remote && input.value.trim().length >= 2) {
        clearTimeout(remoteTimer);
        remoteTimer = setTimeout(function () {
          source.remote(input.value.trim()).then(function (extra) {
            var seen = {};
            options.forEach(function (item) { seen[item.value + "|" + item.label] = true; });
            extra.forEach(function (item) {
              var key = item.value + "|" + item.label;
              if (!seen[key]) options.push(item);
            });
            render(filtered());
          }).catch(function () { /* suggestions are optional */ });
        }, 400);
      }
    }

    input.addEventListener("focus", open);
    input.addEventListener("input", function () {
      chosen = null;
      open();
    });
    input.addEventListener("keydown", function (event) {
      var buttons = list.querySelectorAll("button");
      if (event.key === "ArrowDown" || event.key === "ArrowUp") {
        event.preventDefault();
        if (list.hidden) open();
        if (!buttons.length) return;
        active += event.key === "ArrowDown" ? 1 : -1;
        if (active < 0) active = buttons.length - 1;
        if (active >= buttons.length) active = 0;
        buttons.forEach(function (button, index) {
          button.setAttribute("aria-selected", index === active ? "true" : "false");
        });
        buttons[active].scrollIntoView({ block: "nearest" });
      } else if (event.key === "Enter" && !list.hidden && active >= 0) {
        event.preventDefault();
        buttons[active].dispatchEvent(new MouseEvent("mousedown"));
      } else if (event.key === "Escape") {
        close();
      }
    });
    document.addEventListener("click", function (event) {
      if (!input.parentElement.contains(event.target)) close();
    });

    return {
      setOptions: function (next, preferred) {
        options = next.slice();
        chosen = null;
        input.value = "";
        if (preferred === undefined) return;
        var match = options.filter(function (item) { return item.value === preferred || item.label === preferred; })[0];
        if (match) choose(match);
      },
      value: function () { return chosen; },
      label: function () { return chosen ? chosen.label : ""; }
    };
  }

  var countryCombo = combo("country-input", "country-list", {
    onPick: function () { loadStates(true); }
  });
  var stateCombo = combo("state-input", "state-list", {
    onPick: function () { loadCities(true); },
    remote: function (query) {
      var country = countryCombo.value();
      if (!country) return Promise.resolve([]);
      return request("/api/places/suggest?country=" + encodeURIComponent(country.value) + "&q=" + encodeURIComponent(query))
        .then(function (response) { return response.json(); })
        .then(function (body) {
          var seen = {};
          var items = [{ label: "Whole country", value: "" }];
          (body.suggestions || []).forEach(function (item) {
            if (!item.state || seen[item.state]) return;
            seen[item.state] = true;
            items.push({ label: item.state, value: item.state });
          });
          return items;
        });
    }
  });
  var cityCombo = combo("city-input", "city-list", {
    remote: function (query) {
      var country = countryCombo.value();
      var state = stateCombo.value();
      if (!country) return Promise.resolve([]);
      var path = "/api/places/suggest?country=" + encodeURIComponent(country.value) +
        "&state=" + encodeURIComponent(state ? state.value : "") +
        "&q=" + encodeURIComponent(query);
      return request(path).then(function (response) { return response.json(); }).then(function (body) {
        return (body.suggestions || []).map(function (item) {
          var city = item.city || item.name || item.label;
          return { label: item.label, value: city };
        });
      });
    }
  });

  function loadStates(preferDefault) {
    var country = countryCombo.value();
    if (!country) return;
    request("/api/places/states?country=" + encodeURIComponent(country.value))
      .then(function (response) { return response.json(); })
      .then(function (body) {
        var items = [{ label: "Whole country", value: "" }].concat((body.states || []).map(function (name) {
          return { label: name, value: name };
        }));
        stateCombo.setOptions(items, preferDefault && country.value === "IN" ? "Gujarat" : "");
        loadCities(preferDefault);
      });
  }

  function loadCities(preferDefault) {
    var country = countryCombo.value();
    var state = stateCombo.value();
    var items = [{ label: "Not specific", value: "" }];
    if (!country) {
      cityCombo.setOptions(items, "");
      return;
    }
    request("/api/places/cities?country=" + encodeURIComponent(country.value) + "&state=" + encodeURIComponent(state ? state.value : ""))
      .then(function (response) { return response.json(); })
      .then(function (body) {
        (body.cities || []).forEach(function (name) { items.push({ label: name, value: name }); });
        var preferred = preferDefault && state && state.value === "Gujarat" ? "Vadodara" : "";
        cityCombo.setOptions(items, preferred);
      });
  }

  function helpText() {
    var kind = document.getElementById("query-type").value;
    var notes = {
      meet: "Walk-in list: a physical address and a phone, sorted by distance. Radius applies.",
      contacts: "Email, phone and address are kept only when they were found, then checked (MX, the company's own page, and whether the site responds).",
      sweep: "Covers the selected state, or the whole country when no state is chosen. Radius is not used.",
      person: "Separate search for a named decision-maker printed next to a title on a public page."
    };
    document.getElementById("query-help").textContent = notes[kind] || "";
    document.getElementById("radius").disabled = kind === "sweep";
  }

  document.getElementById("query-type").addEventListener("change", helpText);

  document.getElementById("gate-form").addEventListener("submit", function (event) {
    event.preventDefault();
    token = document.getElementById("token").value;
    gateError.textContent = "";
    var base = apiBase();
    localStorage.setItem("sanket-leads-api", base);
    request("/api/session", { method: "POST", body: "{}" }).then(function () {
      sessionStorage.setItem("sanket-leads-token", token);
      return request("/api/meta");
    }).then(function (response) { return response.json(); }).then(function (body) {
      meta = body;
      fillSelect("industry", body.industries.map(function (item) { return { value: item.id, label: item.label }; }), "two_way_radio");
      fillSelect("radius", body.radii.map(function (km) { return { value: String(km), label: km + " km" }; }), "100");
      countryCombo.setOptions(body.countries.map(function (item) {
        return { label: item.name, value: item.code };
      }), "IN");
      gate.hidden = true;
      desk.hidden = false;
      helpText();
      refreshHistory();
    }).catch(function (error) {
      gateError.textContent = error.message;
    });
  });

  function fillSelect(id, items, selected) {
    var select = document.getElementById(id);
    select.innerHTML = "";
    items.forEach(function (item) {
      var option = document.createElement("option");
      option.value = item.value;
      option.textContent = item.label;
      if (item.value === selected) option.selected = true;
      select.appendChild(option);
    });
  }

  document.getElementById("search-form").addEventListener("submit", function (event) {
    event.preventDefault();
    var country = countryCombo.value();
    var state = stateCombo.value();
    var city = cityCombo.value();
    var kind = document.getElementById("query-type").value;
    if (!country) return setStatus("Choose a country from the list.");
    if (kind !== "sweep" && (!city || !city.value)) return setStatus("Choose a city or a suggested spot.");
    setStatus("Searching public sources… this can take a minute.");
    document.getElementById("search-btn").disabled = true;
    request("/api/searches", {
      method: "POST",
      body: JSON.stringify({
        country_code: country.value,
        state: state && state.value ? state.value : "",
        city: city && city.value ? city.value : "",
        radius_km: Number(document.getElementById("radius").value),
        industry: document.getElementById("industry").value,
        query_type: kind,
        use_cache: document.getElementById("cache-mode").value === "reuse"
      })
    }).then(function (response) { return response.json(); }).then(function (body) {
      showSearch(body);
      refreshHistory();
      setStatus(body.reused_from && body.reused_from.length && !body.external ? "Reused saved results from the last 24 hours." : "Search finished.");
    }).catch(function (error) {
      setStatus(error.message);
    }).then(function () {
      document.getElementById("search-btn").disabled = false;
    });
  });

  function setStatus(text) {
    document.getElementById("status").textContent = text;
  }

  function refreshHistory() {
    request("/api/searches").then(function (response) { return response.json(); }).then(function (body) {
      var list = document.getElementById("history");
      list.innerHTML = "";
      if (!body.searches.length) {
        var empty = document.createElement("li");
        empty.className = "empty";
        empty.textContent = "None yet.";
        list.appendChild(empty);
        return;
      }
      body.searches.forEach(function (item) {
        var li = document.createElement("li");
        var button = document.createElement("button");
        button.type = "button";
        var title = document.createElement("b");
        title.textContent = [item.city || item.state || item.country, labelFor(item.industry), labelFor(item.query_type)].filter(Boolean).join(" · ");
        var meta = document.createElement("small");
        meta.textContent = item.created_at.replace("T", " ").replace("+00:00", " UTC") + " · " + item.result_count + " leads";
        button.appendChild(title);
        button.appendChild(document.createElement("br"));
        button.appendChild(meta);
        button.addEventListener("click", function () {
          request("/api/searches/" + item.id).then(function (response) { return response.json(); }).then(showSearch);
        });
        li.appendChild(button);
        list.appendChild(li);
      });
    }).catch(function (error) { setStatus(error.message); });
  }

  function labelFor(id) {
    if (!meta) return id;
    var industry = meta.industries.filter(function (item) { return item.id === id; })[0];
    if (industry) return industry.label;
    var kind = meta.query_types.filter(function (item) { return item.id === id; })[0];
    return kind ? kind.label : id;
  }

  function showSearch(body) {
    currentId = body.id;
    document.getElementById("results").hidden = false;
    document.getElementById("results-title").textContent = (body.result_count || body.leads.length) + " leads";
    document.getElementById("results-meta").textContent = [body.city, body.state, body.country].filter(Boolean).join(", ") +
      (body.query_type === "sweep" ? " · whole selected area" : " · " + body.radius_km + " km");
    var warnings = document.getElementById("warnings");
    warnings.innerHTML = "";
    warnings.hidden = !(body.warnings || []).length;
    (body.warnings || []).forEach(function (text) {
      var p = document.createElement("p");
      p.textContent = text;
      warnings.appendChild(p);
    });
    var rows = document.getElementById("rows");
    rows.innerHTML = "";
    if (!body.leads.length) {
      var tr = document.createElement("tr");
      var td = document.createElement("td");
      td.colSpan = 8;
      td.textContent = "No public record matched. Nothing was filled in.";
      tr.appendChild(td);
      rows.appendChild(tr);
    }
    body.leads.forEach(function (lead) { rows.appendChild(rowFor(lead)); });
    var log = document.getElementById("log");
    log.innerHTML = "";
    (body.log || []).forEach(function (line) {
      var item = document.createElement("li");
      item.textContent = line;
      log.appendChild(item);
    });
  }

  function rowFor(lead) {
    var tr = document.createElement("tr");
    function cell(label, node) {
      var td = document.createElement("td");
      td.dataset.label = label;
      td.appendChild(node);
      return td;
    }
    function textNode(value) {
      var span = document.createElement("span");
      if (!value) {
        span.className = "blank";
        span.textContent = "—";
      } else {
        span.textContent = value;
      }
      return span;
    }
    function withFlag(value, key) {
      var wrap = document.createElement("span");
      wrap.appendChild(textNode(value));
      var item = (lead.verification || {})[key] || {};
      if (value && item.verified) wrap.appendChild(flag("Verified", "yes"));
      else if (value && (item.checks || []).length) wrap.appendChild(flag("Listed", "listed"));
      return wrap;
    }
    tr.appendChild(cell("Name", textNode(lead.name)));
    tr.appendChild(cell("Distance", textNode(lead.distance_km == null ? "" : lead.distance_km + " km")));
    tr.appendChild(cell("Address", withFlag(lead.address, "address")));
    tr.appendChild(cell("Phone", withFlag(lead.phone, "phone")));
    tr.appendChild(cell("Email", withFlag(lead.email, "email")));
    var site = document.createElement("span");
    if (lead.website) {
      var link = document.createElement("a");
      link.className = "link";
      link.href = lead.website;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      link.textContent = lead.website.replace(/^https?:\/\//, "");
      site.appendChild(link);
      var web = (lead.verification || {}).website || {};
      if (web.verified) site.appendChild(flag("Reachable", "yes"));
    } else {
      site.appendChild(textNode(""));
    }
    tr.appendChild(cell("Website", site));
    var person = [lead.contact_name, lead.contact_title].filter(Boolean).join(", ");
    tr.appendChild(cell("Contact", textNode(person)));
    tr.appendChild(cell("Source", textNode(lead.source)));
    return tr;
  }

  function flag(text, kind) {
    var span = document.createElement("span");
    span.className = "flag " + kind;
    span.textContent = text;
    return span;
  }

  function download(kind) {
    if (!currentId) return;
    request("/api/searches/" + currentId + "/export." + kind).then(function (response) {
      return response.blob();
    }).then(function (blob) {
      var link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = "sanket-leads-" + currentId + "." + kind;
      link.click();
      URL.revokeObjectURL(link.href);
    }).catch(function (error) { setStatus(error.message); });
  }

  document.getElementById("export-csv").addEventListener("click", function () { download("csv"); });
  document.getElementById("export-xlsx").addEventListener("click", function () { download("xlsx"); });

  if (token) {
    document.getElementById("token").value = token;
  }
})();
