const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export async function uploadResume(file) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/api/resume/upload`, {
    method: "POST",
    body: formData,
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || "Resume upload failed.");
  }
  return data;
}

export async function submitPreferences(candidateId, preferences) {
  const response = await fetch(`${API_BASE_URL}/api/candidate/${candidateId}/preferences`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(preferences),
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || "Saving preferences failed.");
  }
  return data;
}

export async function discoverCompanies(candidateId) {
  const response = await fetch(`${API_BASE_URL}/api/candidate/${candidateId}/discover-companies`, {
    method: "POST",
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || "Company discovery failed.");
  }
  return data;
}

export async function discoverJobs(candidateId, windowDays = 30) {
  const response = await fetch(
    `${API_BASE_URL}/api/candidate/${candidateId}/discover-jobs?window_days=${windowDays}`,
    { method: "POST" }
  );

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || "Job discovery failed.");
  }
  return data;
}

export async function getJobs(candidateId, windowDays = 30) {
  const response = await fetch(
    `${API_BASE_URL}/api/candidate/${candidateId}/jobs?window_days=${windowDays}`
  );

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || "Fetching jobs failed.");
  }
  return data;
}

export async function matchJobs(candidateId, windowDays = 30) {
  const response = await fetch(
    `${API_BASE_URL}/api/candidate/${candidateId}/match-jobs?window_days=${windowDays}`,
    { method: "POST" }
  );

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || "Matching jobs against your resume failed.");
  }
  return data;
}

export async function selectJobs(candidateId, jobIds, windowDays = 30) {
  const response = await fetch(
    `${API_BASE_URL}/api/candidate/${candidateId}/select-jobs?window_days=${windowDays}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ job_ids: jobIds }),
    }
  );

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || "Saving your job selection failed.");
  }
  return data;
}

export async function approveApplicationPreparation(candidateId) {
  const response = await fetch(
    `${API_BASE_URL}/api/candidate/${candidateId}/approve-application-preparation`,
    { method: "POST" }
  );

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || "Approving application preparation failed.");
  }
  return data;
}

export async function prepareApplication(candidateId, jobId) {
  const response = await fetch(
    `${API_BASE_URL}/api/candidate/${candidateId}/jobs/${jobId}/prepare-application`,
    { method: "POST" }
  );

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || "Preparing this application failed.");
  }
  return data;
}

export function screenshotUrl(candidateId, jobId) {
  return `${API_BASE_URL}/api/candidate/${candidateId}/jobs/${jobId}/screenshot`;
}

export async function updateReviewFields(candidateId, jobId, fields) {
  const response = await fetch(
    `${API_BASE_URL}/api/candidate/${candidateId}/jobs/${jobId}/review-fields`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ fields }),
    }
  );

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || "Saving your answers failed.");
  }
  return data;
}

