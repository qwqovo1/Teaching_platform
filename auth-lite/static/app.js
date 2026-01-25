const modal = document.getElementById("modal-backdrop");
const openButtons = [
  document.getElementById("open-login"),
  document.getElementById("open-login-secondary"),
];
const closeButton = document.getElementById("close-modal");
const registerBtn = document.getElementById("register-btn");
const forgotBtn = document.getElementById("forgot-btn");
const form = document.getElementById("login-form");
const statusEl = document.getElementById("status");

const API_BASE = "/api";

function showModal() {
  modal.style.display = "flex";
}

function hideModal() {
  modal.style.display = "none";
  statusEl.classList.add("hidden");
  statusEl.textContent = "";
  form.reset();
}

function alertIfInvalidPassword(password) {
  if (!password || password.length < 6) {
    alert("密码长度不得低于6位，请重新输入。");
    return true;
  }
  return false;
}

async function handleAuth(url, username, password) {
  statusEl.classList.remove("hidden");
  statusEl.textContent = "处理中...";
  try {
    const res = await fetch(`${API_BASE}${url}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || data.message || "请求失败");
    }
    statusEl.textContent = data.message || "成功";
    setTimeout(() => {
      statusEl.textContent = `欢迎，${data.username || username}`;
      hideModal();
      alert(`成功：${data.message || "操作成功"}`);
    }, 300);
  } catch (err) {
    statusEl.textContent = err.message;
    alert(err.message);
  }
}

openButtons.forEach((btn) => btn.addEventListener("click", showModal));
closeButton.addEventListener("click", hideModal);
modal.addEventListener("click", (e) => {
  if (e.target === modal) hideModal();
});

form.addEventListener("submit", (e) => {
  e.preventDefault();
  const username = form.username.value.trim();
  const password = form.password.value;
  if (alertIfInvalidPassword(password)) return;
  handleAuth("/login", username, password);
});

registerBtn.addEventListener("click", () => {
  const username = form.username.value.trim();
  const password = form.password.value;
  if (alertIfInvalidPassword(password)) return;
  handleAuth("/register", username, password);
});

forgotBtn.addEventListener("click", () => {
  alert("忘记密码功能暂未开放，敬请期待。");
});
