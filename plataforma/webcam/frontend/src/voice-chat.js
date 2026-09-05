/**
 * voice-chat.js — Conversación continua sin push-to-talk (producción)
 * STT browser es-AR continuous + corte por silencio + barge-in + TTS.
 * Backend /voz con grounding Percepción viva; fallback mock local.
 */

const SUPPORTED = !!(window.SpeechRecognition || window.webkitSpeechRecognition);

// S3+T2: alias STT menor tasa→taza + normalización para voz YOLO-World
export function normalizeTranscriptForWorld(text) {
  if (!text) return text;
  return text.replace(/\btasa\b/gi, 'taza').replace(/\btasas\b/gi, 'tazas');
}

export function shouldSendTranscript(text) {
  const t = (text || '').trim();
  if (t.length < 2) return false;
  return true;
}

// Fragmento interim pobre (corte por silencio a mitad de frase, ej. "qué"
// de "qué ves", "ahora."): una sola palabra corta. El fallback por silencio
// no lo envía como turno — espera al final real. Los finales del browser
// (onresult isFinal) y el input manual sí pasan.
export function isLowInfoInterim(text) {
  const t = (text || '').trim();
  if (!t) return true;
  // Solo descartar fragmentos de 1 palabra muy corta ("qué", "ah").
  // "taza", "persona", "sí hay" ya son turnos válidos (backend describe
  // escena fresca ante fragmentos, test_fragmento_stt_describe_escena).
  if (t.length < 4) return true;
  if (t.split(/\s+/).filter(Boolean).length < 1) return true;
  return false;
}

export function createVoiceChat({ onSendToLLM, silenceMs = 900 } = {}) {
  const wrap = document.createElement('div');
  wrap.className = 'voice-chat';
  wrap.innerHTML = `
    <div class="voice-head">
      <span>VOZ CONTINUA · MUSE SPARK</span>
      <span class="chip" id="vc-state">idle</span>
    </div>
    <div class="voice-transcript" id="vc-transcript"></div>
    <div class="voice-wave" id="vc-wave" style="display:none"><i></i><i></i><i></i><i></i><i></i></div>
    <button class="voice-btn" id="vc-toggle">▶ Iniciar conversación</button>
    <div class="voice-hint">STT ${SUPPORTED ? 'continuo es-AR (sin botón)' : 'no soportado → usá el input de abajo'} · corte por silencio ${silenceMs}ms · hablar interrumpe TTS (barge-in)</div>
    <div class="voice-actions">
      <button class="chip" id="vc-mute">🔇 Mutear voz</button>
      <button class="chip" id="vc-replay">🔊 Replay</button>
      <button class="chip" id="vc-clear">🗑 Limpiar</button>
      <button class="chip" id="vc-test">🧪 Test mock</button>
    </div>
    <div style="margin-top:8px;display:flex;gap:6px">
      <input id="vc-input" placeholder="o escribí acá y Enter (fallback)" style="flex:1;padding:6px 8px;border-radius:6px;border:1px solid #334155;background:#020617;color:#e2e8f0;font-size:12px" />
      <button class="chip" id="vc-send">Enviar</button>
    </div>
    <div class="voice-debug"><pre id="vc-debug"></pre></div>
  `;

  const stateEl = wrap.querySelector('#vc-state');
  const transcriptEl = wrap.querySelector('#vc-transcript');
  const waveEl = wrap.querySelector('#vc-wave');
  const toggleBtn = wrap.querySelector('#vc-toggle');
  const muteBtn = wrap.querySelector('#vc-mute');
  const replayBtn = wrap.querySelector('#vc-replay');
  const clearBtn = wrap.querySelector('#vc-clear');
  const testBtn = wrap.querySelector('#vc-test');
  const inputEl = wrap.querySelector('#vc-input');
  const sendBtn = wrap.querySelector('#vc-send');
  const debugEl = wrap.querySelector('#vc-debug');

  let state = 'idle'; // idle|listening|thinking|speaking
  let active = false; // conversación on/off (toggle, sin PTT)
  let muted = false;
  let interim = '';
  let transcripts = [];
  let recog = null;
  let ttsVoices = [];
  let silenceTimer = null;
  let restartTimer = null;
  let sendDebounceTimer = null;
  let manualStop = false;
  let pausedForReply = false; // STT pausado mientras se piensa/habla (anti-eco)
  let restartFails = 0;
  let lastSentText = '';
  let lastSentTs = 0;
  let lastBotText = '';
  let speakStartTs = 0;
  let speakGuard = null;
  let lastBackend = 'unknown'; // ok|sin-percepcion|unreachable|mock
  // FSM explícita: IDLE→LISTENING→THINKING→SPEAKING→LISTENING. `transition`
  // valida cada cambio; a `idle` siempre se puede llegar (las vías de stop
  // jamás deben atascarse). Violaciones se cuentan en telemetría.
  const FSM_ALLOWED = {
    idle: ['listening'],
    listening: ['thinking', 'idle'],
    thinking: ['speaking', 'listening', 'idle'],
    speaking: ['listening', 'idle'],
  };
  let lastTransition = 'init→idle';
  let fsmViolations = 0;
  // Watchdog STT: si está activo+escuchando sin resultados, el recog murió
  // en silencio (Chrome lo corta por desuso/tras TTS) → reiniciar.
  let lastResultTs = 0;
  let watchdogTimer = null;
  const WATCHDOG_MS = 8000;
  // Log ingest de fragmentos descartados: texto + confidence + motivo para
  // calibrar el umbral low-info según ruido ambiente.
  let droppedLog = [];
  let lastError = null;
  let lastInterimConf = null;

  function logDropped(text, confidence, reason) {
    droppedLog.push({ text: String(text || ''), confidence, reason, ts: Date.now() });
    if (droppedLog.length > 20) droppedLog = droppedLog.slice(-20);
  }

  function transition(to, why) {
    const from = state;
    if (to === from) {
      setState(to); // re-render sin contar violación
      return;
    }
    const ok = (FSM_ALLOWED[from] || []).includes(to);
    if (!ok) {
      fsmViolations += 1;
      console.warn(`[voice-chat] FSM inválida ${from}→${to} (${why || '?'})`);
    }
    lastTransition = `${from}→${to}${why ? ` (${why})` : ''}`;
    setState(to);
  }

  function loadVoices() {
    if (!('speechSynthesis' in window)) return;
    const v = speechSynthesis.getVoices();
    if (v.length) ttsVoices = v;
  }
  loadVoices();
  if ('speechSynthesis' in window) speechSynthesis.onvoiceschanged = loadVoices;

  function setState(s) {
    state = s;
    stateEl.textContent = active ? s : 'idle';
    stateEl.className = 'chip ' + (s === 'listening' ? 'listen' : s === 'thinking' ? 'think' : s === 'speaking' ? 'on' : '');
    waveEl.style.display = active && (s === 'listening' || s === 'speaking') ? 'flex' : 'none';
    toggleBtn.textContent = active ? '■ Parar conversación (escuchando…)' : '▶ Iniciar conversación';
    toggleBtn.classList.toggle('listen', active);
    renderDebug();
  }

  function renderTranscript() {
    if (!transcripts.length && !interim) {
      transcriptEl.innerHTML = '<div class="voice-empty">Conversación detenida. Tocá “Iniciar conversación” y hablá en es-AR — corta solo por silencio, sin botón.</div>';
      return;
    }
    transcriptEl.innerHTML = '';
    for (const t of transcripts.slice(-8)) {
      const d = document.createElement('div');
      d.className = `bubble ${t.role}`;
      d.textContent = (t.role === 'user' ? '🧑 ' : '🤖 ') + t.text;
      transcriptEl.appendChild(d);
    }
    if (interim) {
      const d = document.createElement('div');
      d.className = 'bubble user interim';
      d.textContent = interim + ' …';
      transcriptEl.appendChild(d);
    }
    transcriptEl.scrollTop = transcriptEl.scrollHeight;
  }

  function renderDebug() {
    debugEl.textContent = JSON.stringify({ state, active, muted, backend: lastBackend, supported: SUPPORTED, interim, last: transcripts.slice(-1)[0] || null, fsm: lastTransition, fsmViolations, lastError, dropped: droppedLog.length, droppedLast: droppedLog.slice(-3) }, null, 2);
  }

  function detachRecog(r) {
    // Despegar handlers del objeto viejo ANTES de abortar: si no, su onend
    // dispara otro restart que mata al recog nuevo (loop mic-muerto).
    if (!r) return;
    try { r.onstart = null; } catch {}
    try { r.onresult = null; } catch {}
    try { r.onerror = null; } catch {}
    try { r.onend = null; } catch {}
    try { r.abort(); } catch {}
  }
  function pauseRecogForReply() {
    // Pausa STT mientras el LLM piensa/habla: evita eco TTS→STT y flapping.
    pausedForReply = true;
    if (silenceTimer) clearTimeout(silenceTimer);
    try { if (recog) recog.stop(); } catch {}
  }

  function resumeRecogAfterReply() {
    if (!active || manualStop) return;
    pausedForReply = false;
    interim = '';
    transition('listening', 'resume-mic');
    // Si el objeto actual murió con stop(), arrancar uno nuevo
    scheduleRestart(250);
  }

  function isEchoOfBot(text) {
    // Eco: lo que entra por mic es lo que acabamos de decir por parlantes.
    if (!lastBotText) return false;
    if (Date.now() - speakStartTs > 2500) return false; // barge-in real después de 2.5s pasa
    const norm = (s) => s.toLowerCase().replace(/[^a-záéíóúñü0-9 ]/gi, '').trim();
    const a = norm(text);
    const b = norm(lastBotText).slice(0, 120);
    if (!a || !b) return false;
    const head = b.split(' ').slice(0, 6).join(' ');
    return b.includes(a.slice(0, 24)) || (head && a.includes(head.slice(0, 12)));
  }

  function speak(text) {
    lastBotText = String(text || '');
    // Texto vacío (backend silenció G3 sin sentinel): no pasar por TTS —
    // reabrir el mic de inmediato para no dejar la charla 3s en "speaking".
    if (!String(text || '').trim()) {
      resumeRecogAfterReply();
      if (!active) transition('idle', 'speak-empty');
      return;
    }
    if (!('speechSynthesis' in window) || muted) {
      // Sin TTS igual hay que reabrir el mic para seguir conversando
      resumeRecogAfterReply();
      if (!active) transition('idle', 'speak-muted');
      return;
    }
    speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    const v = ttsVoices.find((x) => x.lang === 'es-AR') || ttsVoices.find((x) => x.lang.startsWith('es')) || null;
    if (v) u.voice = v;
    u.lang = v ? v.lang : 'es-AR';
    u.rate = 1;
    u.pitch = 1;
    u.onstart = () => { speakStartTs = Date.now(); transition('speaking', 'tts-start'); };
    u.onend = () => { if (speakGuard) clearTimeout(speakGuard); resumeRecogAfterReply(); };
    u.onerror = () => { if (speakGuard) clearTimeout(speakGuard); resumeRecogAfterReply(); };
    transition('speaking', 'tts-speak');
    speakStartTs = Date.now();
    // Safety: si el TTS nunca dispara onend (voces sin cargar/bloqueo),
    // reabrir el mic igual para no dejarlo muerto. Estimación ~80ms/char, cap 20s.
    if (speakGuard) clearTimeout(speakGuard);
    const estMs = Math.min(20000, Math.max(3000, String(text || '').length * 90));
    speakGuard = setTimeout(() => {
      speakGuard = null;
      console.warn('[voice-chat] TTS guard: onend no llegó, reabro mic');
      try { if ('speechSynthesis' in window) speechSynthesis.cancel(); } catch {}
      resumeRecogAfterReply();
    }, estMs);
    try {
      if ('speechSynthesis' in window && speechSynthesis.paused) speechSynthesis.resume();
    } catch {}
    speechSynthesis.speak(u);
  }

  async function sendToLLM(text) {
    if (onSendToLLM) {
      try {
        const reply = await onSendToLLM(text);
        if (reply) return reply;
      } catch {}
    }
    const low = text.toLowerCase();
    if (low.includes('hola')) return '¡Hola! Te escucho en continuo. ¿Qué ves por cámara? Describime y lo miramos juntos.';
    if (low.includes('registr')) return 'Perfecto, para registrarte mirá a la cámara y hacé pulgar arriba. Voy a guardar tu embedding en localStorage.';
    if (low.includes('quien')) return 'Soy Muse Spark, orquestador cognitivo de Embodied AI.';
    return `Recibí: "${text}". (mock) Cuando el backend /voz esté listo, esta respuesta vendrá de fase-1/gemini_client.`;
  }

  function getRec() {
    const Rec = window.SpeechRecognition || window.webkitSpeechRecognition;
    const r = new Rec();
    r.lang = 'es-AR';
    r.continuous = true;
    r.interimResults = true;
    r.maxAlternatives = 1;
    return r;
  }

  function handleUserText(text) {
    const raw = (text || '').trim();
    if (!shouldSendTranscript(raw)) return;
    const normalized = normalizeTranscriptForWorld(raw);
    // Dedupe anti "recibí recibí": mismo texto <2s se ignora (interim+final)
    const now = Date.now();
    if (normalized === lastSentText && now - lastSentTs < 2000) {
      logDropped(normalized, null, 'dedupe');
      return;
    }
    if (sendDebounceTimer) clearTimeout(sendDebounceTimer);
    sendDebounceTimer = setTimeout(() => {
      sendDebounceTimer = null;
      // Doble chequeo post-debounce por si interim y final encolaron dos timers
      if (normalized === lastSentText && Date.now() - lastSentTs < 2000) {
        logDropped(normalized, null, 'dedupe-debounced');
        return;
      }
      lastSentText = normalized;
      lastSentTs = Date.now();
      pauseRecogForReply();
      transcripts.push({ role: 'user', text: normalized });
      interim = '';
      renderTranscript();
      transition('thinking', 'send');
      sendToLLM(normalized).then((reply) => {
        if (typeof reply === 'string' && reply.startsWith('__SIN_CAMARA__')) {
          lastBackend = 'sin-percepcion';
          const isMock = typeof window !== 'undefined' && window.__mockActive;
          const msg = isMock
            ? 'Mock activo (demo local, no alimenta /voz) — iniciá la cámara para percepción real.'
            : 'No veo objetos ahora — iniciá la cámara para que te describa lo que ve.';
          transcripts.push({ role: 'bot', text: msg });
          renderTranscript();
          speak(msg);
          try { window.dispatchEvent(new CustomEvent('voz:sin-camara')); } catch {}
          return;
        }
        if (typeof reply === 'string' && reply.startsWith('__SIN_BACKEND__')) {
          lastBackend = 'unreachable';
          const msg = 'No llego al backend /voz en :8000 — ¿está corriendo? Te respondo en mock mientras.';
          transcripts.push({ role: 'bot', text: msg });
          renderTranscript();
          speak(msg);
          return;
        }
        lastBackend = typeof reply === 'string' && reply.includes('(mock)') ? 'mock' : 'ok';
        transcripts.push({ role: 'bot', text: reply });
        renderTranscript();
        speak(reply);
      });
    }, 300);
  }

  function armSilenceFallback() {
    if (silenceTimer) clearTimeout(silenceTimer);
    silenceTimer = setTimeout(() => {
      // Si el browser solo mandó interim y pausó, lo enviamos como turno,
      // salvo fragmento pobre de 1 palabra ("qué", "ahora.") que es corte
      // a mitad de frase: se descarta y se espera al final real.
      if (active && interim && shouldSendTranscript(interim) && !isLowInfoInterim(interim)) {
        const t = interim;
        interim = '';
        handleUserText(t);
      } else if (active && interim) {
        logDropped(interim, lastInterimConf, 'low-info');
        interim = '';
        renderTranscript();
      }
    }, silenceMs);
  }

  function startRecog() {
    if (!SUPPORTED) {
      transition('listening', 'no-stt-fallback');
      interim = '';
      renderTranscript();
      return;
    }
    try { if (recog) detachRecog(recog); } catch {}
    recog = null;
    manualStop = false;
    recog = getRec();
    recog.onstart = () => {
      restartFails = 0;
      transition('listening', 'recog-start');
      renderTranscript();
    };
    recog.onresult = (ev) => {
      if (pausedForReply) return; // mic pausado mientras piensa/habla
      lastResultTs = Date.now();
      // barge-in: si el bot hablaba y llega voz real (no eco), cortar TTS
      let finalText = '';
      let interimText = '';
      let bestConf = null;
      for (let i = ev.resultIndex; i < ev.results.length; i++) {
        const res = ev.results[i];
        const txt = res[0].transcript;
        if (typeof res[0].confidence === 'number') bestConf = res[0].confidence;
        if (res.isFinal) finalText += txt + ' ';
        else interimText += txt + ' ';
      }
      const candidate = (finalText || interimText).trim();
      if (candidate && isEchoOfBot(candidate)) {
        logDropped(candidate, bestConf, 'echo');
        interim = '';
        renderTranscript();
        return;
      }
      if (state === 'speaking' && candidate && 'speechSynthesis' in window) {
        try { speechSynthesis.cancel(); } catch {}
        transition('listening', 'barge-in');
      }
      if (finalText.trim()) {
        interim = '';
        if (silenceTimer) clearTimeout(silenceTimer);
        handleUserText(finalText.trim());
      } else if (interimText.trim()) {
        interim = interimText.trim();
        lastInterimConf = bestConf;
        renderTranscript();
        renderDebug();
        armSilenceFallback();
      }
    };
    recog.onerror = (ev) => {
      lastError = `${ev.error || 'unknown'}${ev.message ? `: ${ev.message}` : ''} @${new Date().toLocaleTimeString()}`;
      renderDebug();
      console.warn('[voice-chat] STT error', ev.error, ev.message);
      if (ev.error === 'not-allowed' || ev.error === 'service-not-allowed') {
        interim = 'Micrófono bloqueado: permití el acceso en la barra del navegador y tocá Iniciar de nuevo.';
        stopConversation();
        renderTranscript();
        return;
      }
      // no-speech / audio-capture / network: reintentar con backoff si sigue activo
      if (active && !manualStop && !pausedForReply) scheduleRestart();
    };
    recog.onend = () => {
      // continuous se corta por silencio largo o por pauseRecogForReply().stop():
      // solo re-arrancar si está activo, no pausado y no fue stop manual
      if (active && !manualStop && !pausedForReply) scheduleRestart();
      else if (!active && state !== 'idle') transition('idle', 'recog-end');
      renderTranscript();
    };
    try {
      recog.start();
    } catch (err) {
      console.warn('[voice-chat] recog.start error', err);
      if (active && !manualStop && !pausedForReply) scheduleRestart();
    }
  }

  function scheduleRestart(baseMs) {
    if (restartTimer) clearTimeout(restartTimer);
    // Backoff exponencial 250ms→4s: evita loop abort→restart→network-error
    const backoff = baseMs ?? Math.min(250 * 2 ** Math.min(restartFails, 4), 4000);
    restartTimer = setTimeout(() => {
      restartTimer = null;
      if (active && !manualStop && !pausedForReply) {
        restartFails += 1;
        startRecog();
      }
    }, backoff);
  }

  function armWatchdog() {
    if (watchdogTimer) clearInterval(watchdogTimer);
    watchdogTimer = setInterval(() => {
      // STT muerto en silencio: activo+escuchando, sin pausa por reply y
      // sin resultados por WATCHDOG_MS → forzar reinicio del recog.
      if (active && !manualStop && !pausedForReply && state === 'listening'
        && lastResultTs > 0 && Date.now() - lastResultTs > WATCHDOG_MS) {
        console.warn('[voice-chat] watchdog: sin resultados STT, reinicio recog');
        lastResultTs = Date.now();
        try { if (recog) detachRecog(recog); } catch {}
        recog = null;
        startRecog();
        renderDebug();
      }
    }, 2000);
  }

  function disarmWatchdog() {
    if (watchdogTimer) clearInterval(watchdogTimer);
    watchdogTimer = null;
  }

  function startConversation() {
    // Debe llamarse en gesto de usuario (click) por autoplay/mic policy
    if (active) return;
    active = true;
    manualStop = false;
    pausedForReply = false;
    restartFails = 0;
    lastResultTs = 0;
    if (restartTimer) clearTimeout(restartTimer);
    if (state === 'speaking' && 'speechSynthesis' in window) {
      try { speechSynthesis.cancel(); } catch {}
    }
    transition('listening', 'start');
    renderTranscript();
    armWatchdog();
    startRecog();
  }

  function stopConversation() {
    active = false;
    manualStop = true;
    pausedForReply = false;
    disarmWatchdog();
    if (restartTimer) clearTimeout(restartTimer);
    if (silenceTimer) clearTimeout(silenceTimer);
    if (sendDebounceTimer) clearTimeout(sendDebounceTimer);
    if (speakGuard) clearTimeout(speakGuard);
    speakGuard = null;
    // Un solo abort (no stop+abort): evita carrera onend/onerror que dejaba flapping
    try { if (recog) recog.abort(); } catch {}
    recog = null;
    interim = '';
    if ('speechSynthesis' in window) { try { speechSynthesis.cancel(); } catch {} }
    transition('idle', 'stop');
    renderTranscript();
  }

  function isActive() {
    return active;
  }

  toggleBtn.addEventListener('click', () => {
    if (active) stopConversation();
    else startConversation();
  });

  muteBtn.addEventListener('click', () => {
    muted = !muted;
    muteBtn.textContent = muted ? '🔊 Activar voz' : '🔇 Mutear voz';
    if (muted && 'speechSynthesis' in window) { try { speechSynthesis.cancel(); } catch {} }
    renderDebug();
  });

  replayBtn.addEventListener('click', () => {
    const last = [...transcripts].reverse().find((t) => t.role === 'bot');
    if (last) speak(last.text);
  });
  clearBtn.addEventListener('click', () => {
    transcripts = [];
    interim = '';
    if (silenceTimer) clearTimeout(silenceTimer);
    if ('speechSynthesis' in window) { try { speechSynthesis.cancel(); } catch {} }
    if (active) transition('listening', 'clear');
    else transition('idle', 'clear');
    renderTranscript();
  });
  testBtn.addEventListener('click', () => handleUserText('hola, quiero registrarme'));

  sendBtn.addEventListener('click', () => {
    const v = inputEl.value.trim();
    if (v) { handleUserText(v); inputEl.value = ''; }
  });
  inputEl.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      const v = inputEl.value.trim();
      if (v) { handleUserText(v); inputEl.value = ''; }
    }
  });

  function addBotMessage(text) {
    transcripts.push({ role: 'bot', text: String(text) });
    renderTranscript();
    speak(String(text));
  }

  renderTranscript();
  transition('idle', 'init');

  return {
    element: wrap,
    getTranscripts: () => transcripts,
    speak,
    handleUserText,
    addBotMessage,
    startConversation,
    stopConversation,
    isActive,
  };
}
