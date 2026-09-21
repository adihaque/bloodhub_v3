/**
 * Blood Hub Core Frontend Script
 * Handles API calls, Web Audio alert synthesizer, and client interactions.
 */

const API_BASE = '/api/v1';

// Token Management
function getToken() {
  return localStorage.getItem('bloodhub_token');
}

function setToken(token) {
  localStorage.setItem('bloodhub_token', token);
}

function clearToken() {
  localStorage.removeItem('bloodhub_token');
}

// HTTP Client
async function apiRequest(endpoint, method = 'GET', body = null) {
  const headers = { 'Content-Type': 'application/json' };
  const token = getToken();
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const options = { method, headers };
  if (body) {
    options.body = JSON.stringify(body);
  }

  try {
    const res = await fetch(`${API_BASE}${endpoint}`, options);
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || data.message || 'Request failed');
    }
    return data;
  } catch (err) {
    console.error(`API [${method} ${endpoint}] Error:`, err);
    throw err;
  }
}

// Emergency Ringtone Synthesizer using Web Audio API
let audioCtx = null;
let chimeInterval = null;

function playEmergencyChime() {
  try {
    if (!audioCtx) {
      audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    }
    if (audioCtx.state === 'suspended') {
      audioCtx.resume();
    }

    if (chimeInterval) clearInterval(chimeInterval);

    const playBeep = () => {
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();
      osc.type = 'sawtooth';
      osc.frequency.setValueAtTime(880, audioCtx.currentTime); // A5
      osc.frequency.exponentialRampToValueAtTime(440, audioCtx.currentTime + 0.3); // A4
      gain.gain.setValueAtTime(0.3, audioCtx.currentTime);
      gain.gain.linearRampToValueAtTime(0.01, audioCtx.currentTime + 0.3);

      osc.connect(gain);
      gain.connect(audioCtx.destination);
      osc.start();
      osc.stop(audioCtx.currentTime + 0.3);
    };

    playBeep();
    chimeInterval = setInterval(playBeep, 800);
  } catch (e) {
    console.warn('Web Audio playback warning:', e);
  }
}

function stopEmergencyChime() {
  if (chimeInterval) {
    clearInterval(chimeInterval);
    chimeInterval = null;
  }
}

// Simple Toast Notification
function showToast(msg, isError = false) {
  const toast = document.createElement('div');
  toast.innerText = msg;
  toast.style.position = 'fixed';
  toast.style.bottom = '20px';
  toast.style.right = '20px';
  toast.style.backgroundColor = isError ? '#dc2626' : '#16a34a';
  toast.style.color = 'white';
  toast.style.padding = '12px 20px';
  toast.style.borderRadius = '8px';
  toast.style.boxShadow = '0 4px 6px rgba(0,0,0,0.15)';
  toast.style.zIndex = '10000';
  toast.style.fontWeight = '600';
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 4000);
}
