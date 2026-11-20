// Frontend logic: read the date, call our backend, show the result or an error.
// The browser never talks to Hebcal directly - only to our FastAPI backend.

const form = document.getElementById("convert-form");
const dateInput = document.getElementById("date-input");
const button = document.getElementById("convert-button");
const errorBox = document.getElementById("error");
const resultBox = document.getElementById("result");
const hebrewText = document.getElementById("hebrew-text");
const hebrewLatin = document.getElementById("hebrew-latin");
const eventsList = document.getElementById("events");

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  hideError();
  resultBox.hidden = true;


  // For <input type="date">, the browser sets .value to "" both when the field
  // is empty AND when the typed date is invalid or incomplete (e.g. 30/02/2026).
  // validity.badInput is true only in the second case, so we check it first.
  if (dateInput.validity.badInput) {
    showError("Please enter a valid date.");
    return;
  }

  const date = dateInput.value;
  if (!date) {
    showError("Please choose a date first.");
    return;
  }

  button.disabled = true;
  button.textContent = "Converting...";

  try {
    const response = await fetch(`/api/convert?date=${encodeURIComponent(date)}`);
    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      showError(data.detail || "Something went wrong. Please try again.");
      return;
    }

    showResult(data);
  } catch (err) {
    showError("Could not reach the server. Is it running?");
  } finally {
    button.disabled = false;
    button.textContent = "Convert";
  }
});

function showResult(data) {
  hebrewText.textContent = data.hebrew;
  hebrewLatin.textContent = `${data.hebrew_day} ${data.hebrew_month} ${data.hebrew_year}`;

  eventsList.innerHTML = "";
  for (const name of data.events) {
    const li = document.createElement("li");
    li.textContent = name; // textContent, not innerHTML, so API text can't inject HTML
    eventsList.appendChild(li);
  }

  resultBox.hidden = false;
}

function showError(message) {
  errorBox.textContent = message;
  errorBox.hidden = false;
}

function hideError() {
  errorBox.hidden = true;
  errorBox.textContent = "";
}
