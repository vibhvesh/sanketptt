/**
 * Enquiry form. Opens a mail draft to both public addresses.
 * Product cards can prefill the subject with data-enquiry-subject,
 * or the page can be opened with ?subject=…#contact.
 */
(function () {
  const form = document.getElementById("contactForm");
  const subject = document.getElementById("enquirySubject");
  const note = document.getElementById("formNote");
  const TO = "akshatsingh@canberravision.com";
  const CC = "akshat@sanketptt.com";

  function setSubject(value) {
    if (!subject || !value) return;
    subject.value = value;
  }

  function subjectFromUrl() {
    const params = new URLSearchParams(location.search);
    return params.get("subject") || params.get("enquiry") || "";
  }

  setSubject(subjectFromUrl());

  document.addEventListener("click", (event) => {
    const link = event.target.closest("[data-enquiry-subject]");
    if (!link) return;
    setSubject(link.getAttribute("data-enquiry-subject") || "");
    if (subject) subject.focus();
  });

  if (!form) return;
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const data = new FormData(form);
    const name = String(data.get("name") || "").trim();
    const chosen = String(data.get("subject") || "").trim();
    const mailSubject = chosen || ("Sanket product enquiry — " + name);
    const body = [
      "Name: " + name,
      "Email: " + String(data.get("email") || ""),
      "Organisation: " + String(data.get("org") || ""),
      "Subject: " + mailSubject,
      "",
      String(data.get("message") || "")
    ].join("\n");
    const href = "mailto:" + TO +
      "?cc=" + encodeURIComponent(CC) +
      "&subject=" + encodeURIComponent(mailSubject) +
      "&body=" + encodeURIComponent(body);
    location.href = href;
    if (note) {
      note.textContent = "Your email app should open a draft to Akshat Singh at " + TO + " and " + CC + ". Nothing is submitted to a website server.";
    }
    if (window.sanketToast) window.sanketToast("Opening your email draft");
  });
})();
