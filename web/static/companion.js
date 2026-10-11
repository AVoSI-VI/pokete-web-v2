const screen = document.getElementById("screen");
const session = document.getElementById("session");
const notice = document.getElementById("notice");

const named = {
  ArrowUp: "up",
  ArrowDown: "down",
  ArrowLeft: "left",
  ArrowRight: "right",
  Enter: "enter",
  Escape: "esc",
  Backspace: "backspace",
  " ": "space",
};

async function showNotice() {
  const code = new URLSearchParams(location.search).get("notice");
  if (!code) return;
  const response = await fetch("/notices");
  const notices = await response.json();
  if (!Object.prototype.hasOwnProperty.call(notices, code)) return;
  notice.textContent = notices[code];
  notice.hidden = false;
}

async function refreshFrame() {
  const response = await fetch("/frame");
  screen.textContent = await response.text();
}

async function refreshSession() {
  const response = await fetch("/session");
  const data = await response.json();
  session.textContent = data.detail
    ? data.state + " — " + data.detail
    : data.state;
}

document.addEventListener("keydown", (event) => {
  const target = event.target;
  if (target instanceof Element && target.closest("input, textarea, button, a")) {
    return;
  }
  let token = named[event.key];
  if (!token && event.key.length === 1) token = event.key;
  if (!token || token === ":") return;
  event.preventDefault();
  fetch("/key", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ key: token }),
  });
});

showNotice();
refreshFrame();
refreshSession();
setInterval(refreshFrame, 150);
setInterval(refreshSession, 1000);
