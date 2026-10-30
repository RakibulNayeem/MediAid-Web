// Shows medicine suggestions under every search box as the person types.
// Without JavaScript the search box still works as a normal form.
(function () {
  var MIN_LENGTH = 2;
  var WAIT_MS = 150; // wait for a pause in typing, so each key press doesn't cost a request

  document.querySelectorAll("[data-suggest-url]").forEach(function (form, formIndex) {
    var input = form.querySelector("input[name=q]");
    var list = document.createElement("ul");
    var options = [];
    var active = -1;
    var timer = null;
    var request = null;

    list.className = "suggestions";
    list.id = "suggestions-" + formIndex;
    list.setAttribute("role", "listbox");
    list.hidden = true;
    form.appendChild(list);
    input.setAttribute("role", "combobox");
    input.setAttribute("aria-autocomplete", "list");
    input.setAttribute("aria-expanded", "false");
    input.setAttribute("aria-controls", list.id);

    function close() {
      list.hidden = true;
      active = -1;
      input.setAttribute("aria-expanded", "false");
      input.removeAttribute("aria-activedescendant");
    }

    function setActive(index) {
      if (active >= 0) options[active].removeAttribute("aria-selected");
      active = index;
      if (active >= 0) {
        options[active].setAttribute("aria-selected", "true");
        input.setAttribute("aria-activedescendant", options[active].id);
      } else {
        input.removeAttribute("aria-activedescendant");
      }
    }

    function show(results) {
      list.textContent = "";
      options = results.map(function (result, index) {
        var item = document.createElement("li");
        var link = document.createElement("a");
        var title = document.createElement("strong");
        var detail = document.createElement("span");
        item.id = list.id + "-" + index;
        item.setAttribute("role", "option");
        link.href = result.url;
        title.textContent = result.title; // textContent, so names can never run as code
        detail.textContent = result.detail;
        link.append(title, detail);
        item.append(link);
        list.append(item);
        return item;
      });
      active = -1;
      list.hidden = options.length === 0;
      input.setAttribute("aria-expanded", String(options.length > 0));
    }

    function load() {
      var query = input.value.trim();
      if (request) request.abort();
      if (query.length < MIN_LENGTH) {
        close();
        return;
      }
      request = new AbortController();
      fetch(form.dataset.suggestUrl + "?q=" + encodeURIComponent(query), { signal: request.signal })
        .then(function (response) { return response.ok ? response.json() : { results: [] }; })
        .then(function (data) { show(data.results); })
        .catch(function () { /* a cancelled or failed request: the search button still works */ });
    }

    input.addEventListener("input", function () {
      clearTimeout(timer);
      timer = setTimeout(load, WAIT_MS);
    });

    input.addEventListener("keydown", function (event) {
      if (event.key === "Escape") {
        close();
      } else if (!list.hidden && options.length && event.key === "ArrowDown") {
        event.preventDefault();
        setActive((active + 1) % options.length);
      } else if (!list.hidden && options.length && event.key === "ArrowUp") {
        event.preventDefault();
        setActive((active - 1 + options.length) % options.length);
      } else if (event.key === "Enter" && active >= 0) {
        event.preventDefault();
        window.location.href = options[active].querySelector("a").href;
      }
    });

    document.addEventListener("pointerdown", function (event) {
      if (!form.contains(event.target)) close();
    });
  });
})();
