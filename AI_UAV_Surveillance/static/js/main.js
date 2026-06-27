function renderBarChart(id, labels, values) {
  const el = document.getElementById(id);
  if (!el) return;
  new Chart(el, {
    type: "bar",
    data: { labels, datasets: [{ data: values, backgroundColor: ["#38bdf8", "#f97316", "#22c55e", "#e11d48"] }] },
    options: chartOptions()
  });
}

function renderLineChart(id, labels, values) {
  const el = document.getElementById(id);
  if (!el) return;
  new Chart(el, {
    type: "line",
    data: { labels, datasets: [{ data: values, borderColor: "#38bdf8", backgroundColor: "rgba(56,189,248,.16)", tension: .35, fill: true }] },
    options: chartOptions()
  });
}

function chartOptions() {
  return {
    responsive: true,
    plugins: { legend: { display: false } },
    scales: {
      x: { ticks: { color: "#94a3b8" }, grid: { color: "rgba(148,163,184,.15)" } },
      y: { ticks: { color: "#94a3b8" }, grid: { color: "rgba(148,163,184,.15)" }, beginAtZero: true }
    }
  };
}

function showProgress() {
  const box = document.getElementById("progressBox");
  if (box) box.classList.remove("d-none");
}

let videoJobPollTimer = null;
let videoFramePollTimer = null;
let activeVideoJobId = null;

function setVideoError(message) {
  const error = document.getElementById("videoError");
  if (!error) return;
  error.textContent = message;
  error.classList.toggle("d-none", !message);
}

function startVideoProcessing(event) {
  event.preventDefault();
  pauseVideoFrames();
  setVideoError("");
  showProgress();

  const form = document.getElementById("videoUploadForm");
  const livePanel = document.getElementById("liveVideoPanel");
  const liveFrame = document.getElementById("liveVideoFrame");
  const waiting = document.getElementById("waitingForFrame");
  if (livePanel) livePanel.classList.remove("d-none");
  if (liveFrame) liveFrame.classList.add("d-none");
  if (waiting) waiting.classList.remove("d-none");

  fetch("/video/start", { method: "POST", body: new FormData(form) })
    .then(async response => {
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || "Video processing failed.");
      activeVideoJobId = payload.job_id;
      beginVideoJobPolling(activeVideoJobId);
    })
    .catch(error => {
      setVideoError(error.message);
      const box = document.getElementById("progressBox");
      if (box) box.classList.add("d-none");
    });
}

function beginVideoJobPolling(jobId) {
  clearInterval(videoJobPollTimer);
  clearInterval(videoFramePollTimer);
  pollVideoStatus(jobId);
  videoJobPollTimer = setInterval(() => pollVideoStatus(jobId), 1000);
  videoFramePollTimer = setInterval(() => updateLiveVideoFrame(jobId), 500);
}

function updateLiveVideoFrame(jobId) {
  const liveFrame = document.getElementById("liveVideoFrame");
  const waiting = document.getElementById("waitingForFrame");
  if (!liveFrame) return;
  liveFrame.onload = () => {
    liveFrame.classList.remove("d-none");
    if (waiting) waiting.classList.add("d-none");
  };
  liveFrame.src = `/video/job/${jobId}/frame?t=${Date.now()}`;
}

function pollVideoStatus(jobId) {
  fetch(`/video/job/${jobId}/status`)
    .then(response => response.json())
    .then(job => {
      const status = document.getElementById("videoJobStatus");
      const frames = document.getElementById("videoFramesProcessed");
      const counter = document.getElementById("liveFrameCounter");
      const unique = document.getElementById("videoUniqueDetections");
      const classStats = document.getElementById("videoClassStats");
      if (status) status.textContent = job.status || "Processing";
      if (frames) frames.textContent = job.processed_frames || 0;
      if (counter) counter.textContent = `Processed frames: ${job.processed_frames || 0}`;
      if (job.has_frame) updateLiveVideoFrame(jobId);

      if (job.stats) {
        if (frames) frames.textContent = job.stats.frames || 0;
        if (unique) unique.textContent = job.stats.detections || 0;
        if (classStats) {
          classStats.innerHTML = "";
          Object.entries(job.stats.classes || {}).forEach(([name, count]) => {
            const item = document.createElement("li");
            item.className = "list-group-item";
            item.innerHTML = `<span>${name}</span><span>${count}</span>`;
            classStats.appendChild(item);
          });
        }
      }

      if (job.status === "complete") {
        clearInterval(videoJobPollTimer);
        clearInterval(videoFramePollTimer);
        const box = document.getElementById("progressBox");
        if (box) box.classList.add("d-none");
        const download = document.getElementById("processedVideoDownload");
        if (download && job.processed_video) {
          download.href = `/static/${job.processed_video.replace(/^static\//, "")}`;
          download.classList.remove("d-none");
        }
      }

      if (job.status === "error") {
        clearInterval(videoJobPollTimer);
        clearInterval(videoFramePollTimer);
        setVideoError(job.error || "Video processing failed.");
      }
    })
    .catch(() => {});
}

function startCamera() {
  const feed = document.getElementById("cameraFeed");
  if (feed) feed.src = "/webcam/start?" + Date.now();
}

function stopCamera() {
  const feed = document.getElementById("cameraFeed");
  const canvas = document.getElementById("snapshotCanvas");
  if (feed && canvas && feed.naturalWidth) {
    canvas.width = feed.naturalWidth;
    canvas.height = feed.naturalHeight;
    canvas.getContext("2d").drawImage(feed, 0, 0);
    feed.dataset.lastFrame = canvas.toDataURL("image/jpeg");
  }
  fetch("/webcam/stop").finally(() => {
    if (feed && feed.dataset.lastFrame) feed.src = feed.dataset.lastFrame;
  });
}

function snapshot() {
  const feed = document.getElementById("cameraFeed");
  const canvas = document.getElementById("snapshotCanvas");
  if (!feed || !canvas || !feed.naturalWidth) return;
  canvas.width = feed.naturalWidth;
  canvas.height = feed.naturalHeight;
  canvas.getContext("2d").drawImage(feed, 0, 0);
  const link = document.createElement("a");
  link.download = "uav_snapshot.jpg";
  link.href = canvas.toDataURL("image/jpeg");
  link.click();
}

let framePlaybackTimer = null;

function setVideoFrame(index) {
  const viewer = document.getElementById("frameByFrameViewer");
  const counter = document.getElementById("frameCounter");
  if (!viewer) return;
  const total = Number(viewer.dataset.total || 1);
  const nextIndex = Math.max(0, Math.min(index, total - 1));
  viewer.dataset.index = String(nextIndex);
  viewer.src = `/video/frame/${encodeURIComponent(viewer.dataset.video)}/${nextIndex}?t=${Date.now()}`;
  if (counter) counter.textContent = `Frame ${nextIndex + 1} / ${total}`;
}

function stepVideoFrame(direction) {
  pauseVideoFrames();
  const viewer = document.getElementById("frameByFrameViewer");
  if (!viewer) return;
  setVideoFrame(Number(viewer.dataset.index || 0) + direction);
}

function playVideoFrames() {
  pauseVideoFrames();
  const viewer = document.getElementById("frameByFrameViewer");
  if (!viewer) return;
  framePlaybackTimer = setInterval(() => {
    const total = Number(viewer.dataset.total || 1);
    const index = Number(viewer.dataset.index || 0);
    setVideoFrame(index >= total - 1 ? 0 : index + 1);
  }, 250);
}

function pauseVideoFrames() {
  if (framePlaybackTimer) {
    clearInterval(framePlaybackTimer);
    framePlaybackTimer = null;
  }
}
