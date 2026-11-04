async function request(path, { method = "GET", body, raw = false } = {}) {
  const headers = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";

  const res = await fetch(`/api${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    let message = `Request failed (${res.status})`;
    try {
      const data = await res.json();
      if (typeof data.detail === "string") message = data.detail;
      else if (Array.isArray(data.detail)) message = data.detail.map((d) => d.msg).join("; ");
    } catch {
      /* ignore non-JSON error bodies */
    }
    throw new Error(message);
  }
  if (raw) return res;
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  listRoadmaps: () => request("/roadmaps"),
  getRoadmap: (id) => request(`/roadmaps/${id}`),
  createRoadmap: (data) => request("/roadmaps", { method: "POST", body: data }),
  deleteRoadmap: (id) => request(`/roadmaps/${id}`, { method: "DELETE" }),
  retryRoadmap: (id) => request(`/roadmaps/${id}/retry`, { method: "POST" }),
  setDayProgress: (id, day, completed) =>
    request(`/roadmaps/${id}/days/${day}`, { method: "PATCH", body: { completed } }),
  saveQuizScore: (id, module, score, total) =>
    request(`/roadmaps/${id}/quizzes/${module}/score`, { method: "POST", body: { score, total } }),
  emailRoadmap: (id, to) => request(`/roadmaps/${id}/email`, { method: "POST", body: { to: to || null } }),
  downloadPdf: async (id, topic) => {
    const res = await request(`/roadmaps/${id}/pdf`, { raw: true });
    const url = URL.createObjectURL(await res.blob());
    const a = document.createElement("a");
    a.href = url;
    a.download = `${topic.replace(/[^A-Za-z0-9._-]+/g, "_") || "roadmap"}.pdf`;
    a.click();
    URL.revokeObjectURL(url);
  },
};
