const API_BASE_URL = "/api";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, options);
  const payload = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(payload.detail || "The request could not be completed.");
  }

  return payload;
}

export function getHealth() {
  return request("/health");
}

export function connectDatabase(connectionString) {
  return request("/connect", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ connection_string: connectionString }),
  });
}

export function runQuery(query) {
  return request("/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query }),
  });
}

export function estimateQuery(query) {
  return request("/estimate", {
    method: "POST",
    headers: { "Content-Type": "text/plain" },
    body: query,
  });
}
