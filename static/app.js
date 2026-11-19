"use strict";

const fields = {
  name: ["Name", 120],
  email: ["Email address", 254],
  registration_number: ["Registration number", 80],
  assignment_title: ["Assignment title", 200],
  submission_url: ["Submission URL", 2048],
};
const urlError = "Submission URL must be a valid HTTP or HTTPS URL without credentials.";
const storageKey = "assignment-portal-static-demo-v1";
const form = document.getElementById("submission-form");
const submitButton = document.getElementById("submit-button");
const refreshButton = document.getElementById("refresh-button");
const formStatus = document.getElementById("form-status");
const listStatus = document.getElementById("list-status");
let mode = null;

function isHttpURL(value) {
  if (/\s|[\u0000-\u001f\u007f\\]/u.test(value) || !/^https?:\/\//i.test(value)) return false;
  try {
    const parsed = new URL(value);
    const authority = value.match(/^https?:\/\/([^/?#]+)/i)?.[1];
    if (!authority || authority.includes("@") || authority.endsWith(":") || !parsed.hostname) return false;
    if (!["http:", "https:"].includes(parsed.protocol) || parsed.username || parsed.password) return false;
    if (parsed.port && (Number(parsed.port) < 1 || Number(parsed.port) > 65535)) return false;
    if (authority.startsWith("[")) {
      const match = authority.match(/^\[[^\]]+\](?::([0-9]+))?$/);
      return Boolean(match && (!match[1] || (Number(match[1]) >= 1 && Number(match[1]) <= 65535)));
    }
    const rawHost = authority.split(":")[0].replace(/\.$/, "");
    if (/^[0-9.]+$/.test(rawHost)) {
      const parts = rawHost.split(".");
      return parts.length === 4 && parts.every(part => /^(0|[1-9][0-9]{0,2})$/.test(part) && Number(part) <= 255);
    }
    // Reject browser-only numeric shortcuts, escaped hosts, and extra colons.
    if (rawHost.includes("%") || authority.split(":").length > 2 || /^[0-9.]+$/.test(parsed.hostname)) return false;
    const host = parsed.hostname.replace(/\.$/, "");
    return host.length <= 253 && host.split(".").every(label => /^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/i.test(label));
  } catch {
    return false;
  }
}

function validate(payload) {
  const errors = {};
  for (const [field, [label, limit]] of Object.entries(fields)) {
    const value = payload[field];
    if (typeof value !== "string" || !value.trim()) errors[field] = `${label} is required and must be text.`;
    else if (value.length > limit) errors[field] = `${label} must be at most ${limit} characters.`;
    else if (/[\u0000-\u001f\u007f]/u.test(value)) errors[field] = `${label} must not contain control characters.`;
  }
  if (!errors.email) {
    const email = payload.email;
    const match = /^([^@\s]+)@([^@\s]+)$/.exec(email);
    if (!match || match[1].length > 64 || email.length > 254 ||
        match[1].startsWith(".") || match[1].endsWith(".") || match[1].includes("..") ||
        !/^[a-z0-9.!#$%&'*+/=?^_`{|}~-]+$/i.test(match[1]) ||
        !/^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/i.test(match[2])) {
      errors.email = "Email address must be a valid address such as name@gmail.com.";
    }
  }
  if (!errors.submission_url && !isHttpURL(payload.submission_url)) errors.submission_url = urlError;
  return errors;
}

function showErrors(errors) {
  for (const field of Object.keys(fields)) {
    document.getElementById(`${field}-error`).textContent = errors[field] || "";
    document.getElementById(field).setAttribute("aria-invalid", errors[field] ? "true" : "false");
  }
}

async function requestJSON(path, options = {}) {
  let response;
  try {
    response = await fetch(path, { ...options, signal: AbortSignal.timeout(10000), cache: "no-store" });
  } catch {
    throw new Error("Cannot reach the portal. Check that python3 server.py is running, then try again.");
  }
  let data;
  try { data = await response.json(); }
  catch { throw new Error("The portal returned an unreadable response. Please try again."); }
  if (!response.ok) {
    const error = new Error(data.error || "The request could not be completed.");
    error.fieldErrors = data.errors;
    throw error;
  }
  return data;
}

function readLocalSubmissions() {
  let stored;
  try { stored = JSON.parse(localStorage.getItem(storageKey) || "[]"); }
  catch { throw new Error("Browser demo storage is unavailable or damaged. Enable local storage or clear this site's demo data."); }
  if (!Array.isArray(stored) || stored.some(item => !item || typeof item !== "object" || Object.keys(validate(item)).length)) {
    throw new Error("Browser demo data is invalid. Clear this site's demo storage and try again.");
  }
  return stored;
}

function textElement(tag, text, className) {
  const element = document.createElement(tag);
  element.textContent = text;
  if (className) element.className = className;
  return element;
}

function renderSubmissions(submissions) {
  const list = document.getElementById("submission-list");
  list.replaceChildren();
  for (const submission of submissions) {
    const item = document.createElement("li");
    item.append(textElement("h3", submission.assignment_title));
    item.append(textElement("p", `${submission.name} · ${submission.registration_number}`));
    item.append(textElement("p", submission.email));
    if (isHttpURL(submission.submission_url)) {
      const link = textElement("a", submission.submission_url);
      link.href = submission.submission_url;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      item.append(link);
    } else {
      item.append(textElement("p", "Unsafe or invalid submission link hidden."));
    }
    item.append(textElement("p", `Saved: ${submission.submitted_at || "time unavailable"}`, "saved-time"));
    list.append(item);
  }
  listStatus.textContent = submissions.length ? `${submissions.length} saved submission(s).` : "No submissions yet. Add your first one above.";
}

async function loadSubmissions() {
  listStatus.textContent = "Loading submissions…";
  refreshButton.disabled = true;
  try {
    const submissions = mode === "static-demo" ? readLocalSubmissions() : (await requestJSON("api/submissions")).submissions;
    if (!Array.isArray(submissions)) throw new Error("The submission list response is invalid.");
    renderSubmissions(submissions);
  } catch (error) {
    document.getElementById("submission-list").replaceChildren();
    listStatus.textContent = error.message;
  } finally {
    refreshButton.disabled = false;
  }
}

form.addEventListener("submit", async event => {
  event.preventDefault();
  if (!mode) return;
  const payload = Object.fromEntries(Object.keys(fields).map(field => [field, document.getElementById(field).value.trim()]));
  const errors = validate(payload);
  showErrors(errors);
  if (Object.keys(errors).length) {
    formStatus.textContent = "Please correct the highlighted fields.";
    document.getElementById(Object.keys(errors)[0]).focus();
    return;
  }
  submitButton.disabled = true;
  formStatus.textContent = "Saving…";
  try {
    if (mode === "static-demo") {
      const submissions = readLocalSubmissions();
      submissions.unshift({ ...payload, submitted_at: new Date().toISOString() });
      try { localStorage.setItem(storageKey, JSON.stringify(submissions)); }
      catch { throw new Error("Could not save browser demo data. Storage may be disabled or full."); }
    } else {
      const result = await requestJSON("api/submissions", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
      formStatus.textContent = result.email_status === "sent"
        ? "Submission saved; confirmation email sent."
        : result.email_status === "failed"
          ? "Submission saved; confirmation email failed to send."
          : "Submission saved; confirmation email was not configured.";
      form.reset();
      showErrors({});
      await loadSubmissions();
      return;
    }
    form.reset();
    showErrors({});
    formStatus.textContent = mode === "static-demo"
      ? "Saved only in this browser's local storage. No confirmation email is sent by the static demo."
      : "Submission saved durably in SQLite.";
    await loadSubmissions();
  } catch (error) {
    if (error.fieldErrors) showErrors(error.fieldErrors);
    formStatus.textContent = error.message;
  } finally {
    submitButton.disabled = false;
  }
});

refreshButton.addEventListener("click", loadSubmissions);

async function initialize() {
  try {
    const config = await requestJSON("config.json");
    if (!["server", "static-demo"].includes(config.mode)) throw new Error("Unknown portal mode; refusing to guess where data will be saved.");
    mode = config.mode;
    document.getElementById("mode-label").textContent = mode === "static-demo"
      ? "STATIC DEMO — saved in this browser only (localStorage). No real email confirmation is sent; this demo has no Python server, SQLite, shared submissions, or CI receiver."
      : "LOCAL SERVER — submissions are saved durably in SQLite on this machine.";
    submitButton.disabled = false;
    await loadSubmissions();
  } catch (error) {
    document.getElementById("mode-label").textContent = error.message;
    listStatus.textContent = "Portal unavailable. Reload after resolving the connection problem.";
  }
}

initialize();
