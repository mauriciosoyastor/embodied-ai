/**
 * voice-chat.js — Panel voz push-to-talk + transcript chat + TTS (producción)
 * Variante chat elegida en ticket 003. Reusa STT browser es-AR y TTS, mock Muse Spark
 * hasta que ticket 004 provea POST /voz. Fix: pointer capture + robust onresult.
 */

const SUPPORTED = !!(window.SpeechRecognition || window.webkitSpeechRecognition);

// S3+T2: alias STT menor tasa→taza + normalización para voz YOLO-World
export function normalizeTranscriptForWorld(text) {
  if (!text) return text;
  return text.replace(/\btasa\b/gi, 'taza').replace(/\btasas\b/gi, 'tazas');
}

export function shouldSendTranscript(text) {
  const t = (text || '').trim();
  if (t.length < 3) return false;
  return true;
}

export function createVoiceChat({ onSendToLLM } = {}) {
  const wrap = document.createElement('div');
  wrap.className = 'voice-chat';
  wrap.innerHTML = `
    <div class="voice-head">
      <span>VOZ · MUSE SPARK 1.2</span>
      <span class="chip" id="vc-state">idle</span>
    </div>
    <div class="voice-transcript" id="vc-transcript"></div>
    <div class="voice-wave" id="vc-wave" style="display:none"><i></i><i></i><i></i><i></i><i></i></div>
    <button class="voice-btn" id="vc-btn">🎤 Mantené para hablar</button>
    <div class="voice-hint">STT ${SUPPORTED ? 'webkitSpeechRecognition es-AR' : 'no soportado → mock'} · TTS speechSynthesis es-AR · mantené presionado, soltá para enviar</div>
    <div class="voice-actions">
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
  const btn = wrap.querySelector('#vc-btn');
  const replayBtn = wrap.querySelector('#vc-replay');
  const clearBtn = wrap.querySelector('#vc-clear');
  const testBtn = wrap.querySelector('#vc-test');
  const inputEl = wrap.querySelector('#vc-input');
  const sendBtn = wrap.querySelector('#vc-send');
  const debugEl = wrap.querySelector('#vc-debug');

  let state = 'idle';
  let interim = '';
  let transcripts = [];
  let recog = null;
  let ttsVoices = [];
  let isHolding = false;

  function loadVoices() {
    if (!('speechSynthesis' in window)) return;
    const v = speechSynthesis.getVoices();
    if (v.length) ttsVoices = v;
  }
  loadVoices();
  if ('speechSynthesis' in window) speechSynthesis.onvoiceschanged = loadVoices;

  function setState(s) {
    state = s;
    stateEl.textContent = s;
    stateEl.className = 'chip ' + (s === 'listening' ? 'listen' : s === 'thinking' ? 'think' : s === 'speaking' ? 'on' : '');
    waveEl.style.display = s === 'listening' ? 'flex' : 'none';
    btn.textContent = s === 'listening' ? '● Soltá para enviar (escuchando...)' : '🎤 Mantené para hablar';
    btn.classList.toggle('listen', s === 'listening');
    // cancelar TTS si empieza a escuchar
    if (s === 'listening' && 'speechSynthesis' in window) speechSynthesis.cancel();
    renderDebug();
  }

  function renderTranscript() {
    if (!transcripts.length && !interim) {
      transcriptEl.innerHTML = '<div class="voice-empty">Sin transcript. Mantené el botón y hablá en es-AR, o usá el input abajo.</div>';
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
    debugEl.textContent = JSON.stringify({ state, supported: SUPPORTED, holding: isHolding, interim, last: transcripts.slice(-1)[0] || null }, null, 2);
  }

  function speak(text) {
    if (!('speechSynthesis' in window)) return;
    speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    const v = ttsVoices.find((x) => x.lang === 'es-AR') || ttsVoices.find((x) => x.lang.startsWith('es')) || null;
    if (v) u.voice = v;
    u.lang = v ? v.lang : 'es-AR';
    u.rate = 1;
    u.pitch = 1;
    u.onstart = () => setState('speaking');
    u.onend = () => setState('idle');
    u.onerror = () => setState('idle');
    setState('speaking');
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
    if (low.includes('hola')) return '¡Hola! Soy Muse Spark 1.2 free vía Cursor. ¿Cómo te registro por cámara? Mirá y hacé pulgar arriba.';
    if (low.includes('registr')) return 'Perfecto, para registrarte mirá a la cámara y hacé pulgar arriba. Voy a guardar tu embedding en localStorage.';
    if (low.includes('quien')) return 'Soy Muse Spark 1.2, orquestador cognitivo de Embodied AI.';
    return `Recibí: "${text}". (mock) Cuando el backend /voz esté listo, esta respuesta vendrá de fase-1/gemini_client.`;
  }

  function getRec() {
    const Rec = window.SpeechRecognition || window.webkitSpeechRecognition;
    const r = new Rec();
    r.lang = 'es-AR';
    r.continuous = false;
    r.interimResults = true;
    r.maxAlternatives = 1;
    return r;
  }

  let sendDebounceTimer = null;
  function handleUserText(text) {
    const raw = (text || '').trim();
    if (!shouldSendTranscript(raw)) return;
    const normalized = normalizeTranscriptForWorld(raw);
    // debounce 500ms para STT final + hola prefix
    if (sendDebounceTimer) clearTimeout(sendDebounceTimer);
    sendDebounceTimer = setTimeout(() => {
      sendDebounceTimer = null;
      transcripts.push({ role: 'user', text: normalized });
      renderTranscript();
      setState('thinking');
      sendToLLM(normalized).then((reply) => {
        transcripts.push({ role: 'bot', text: reply });
        renderTranscript();
        speak(reply);
      });
    }, 300);
  }

  function startListening(e) {
    // debe ser sincrónico dentro del gesto
    if (e) {
      e.preventDefault();
      try { btn.setPointerCapture(e.pointerId); } catch {}
    }
    if (isHolding) return;
    isHolding = true;
    if (state === 'speaking' && 'speechSynthesis' in window) speechSynthesis.cancel();
    if (!SUPPORTED) {
      setState('listening');
      interim = '(mock) Escuchando... soltá para enviar';
      renderTranscript();
      return;
    }
    // si había recog previo, abortar
    try { if (recog) recog.abort(); } catch {}
    recog = getRec();
    recog.onstart = () => {
      setState('listening');
      interim = 'Escuchando...';
      renderTranscript();
    };
    recog.onresult = (ev) => {
      // Manejo robusto: iterar resultados, separar interim vs final
      let finalText = '';
      let interimText = '';
      for (let i = ev.resultIndex; i < ev.results.length; i++) {
        const res = ev.results[i];
        const txt = res[0].transcript;
        if (res.isFinal) finalText += txt + ' ';
        else interimText += txt + ' ';
      }
      if (finalText.trim()) {
        interim = '';
        // solo un push por evento final
        handleUserText(finalText.trim());
      } else if (interimText.trim()) {
        interim = interimText.trim();
        renderTranscript();
        renderDebug();
      }
    };
    recog.onerror = (ev) => {
      console.warn('[voice-chat] STT error', ev.error, ev.message);
      if (ev.error === 'not-allowed' || ev.error === 'service-not-allowed') {
        interim = 'Micrófono bloqueado: permití el acceso en la barra del navegador y recargá.';
      } else if (ev.error === 'no-speech') {
        interim = 'No se detectó voz. Probá de nuevo, más cerca del mic.';
      } else if (ev.error === 'audio-capture') {
        interim = 'Mic no disponible. Revisá que no esté usado por otra app.';
      } else {
        interim = 'Error STT: ' + ev.error;
      }
      setState('idle');
      renderTranscript();
      isHolding = false;
    };
    recog.onend = () => {
      // onend puede disparar antes que pointerup si el usuario habló y pausó
      // no forzar isHolding=false aquí; lo maneja pointerup
      if (isHolding) {
        // si aún está manteniendo pero se cortó por silencio, mantener listening visual un momento
        // pero no resetear interim si ya se envió final
        if (!interim.includes('Error')) {
          // si no hubo final, mostrar hint
          if (!transcripts.length || transcripts[transcripts.length - 1].role !== 'user') {
            // no final aún, esperar pointerup para mock fallback
          }
        }
      } else {
        if (state === 'listening') setState('idle');
      }
      renderTranscript();
    };
    try {
      recog.start();
    } catch (err) {
      console.warn('[voice-chat] recog.start error', err);
      interim = 'STT error: ' + err.message;
      setState('idle');
      renderTranscript();
      isHolding = false;
    }
  }

  function stopListening(e) {
    if (e) {
      try { btn.releasePointerCapture(e.pointerId); } catch {}
    }
    if (!isHolding) return;
    isHolding = false;
    if (!SUPPORTED) {
      // mock: simula captura
      const t = interim.includes('mock') || !interim ? 'hola, quiero registrarme' : interim;
      interim = '';
      handleUserText(t);
      setState('idle');
      renderTranscript();
      return;
    }
    try {
      if (recog && state === 'listening') {
        recog.stop();
        // onend se encargará de setState idle si no hubo final
        // pero forzamos idle si no hay thinking/speaking
        setTimeout(() => { if (state === 'listening') setState('idle'); }, 300);
      }
    } catch {}
    interim = '';
    renderTranscript();
  }

  // Pointer events robustos (captura incluso si suelta fuera del botón)
  btn.addEventListener('pointerdown', startListening);
  btn.addEventListener('pointerup', stopListening);
  btn.addEventListener('pointercancel', stopListening);
  btn.addEventListener('pointerleave', (e) => {
    // no cortar si aún está presionado con captura; solo si perdió captura
    if (isHolding && e.buttons === 0) stopListening(e);
  });
  // Fallback mouse/touch por si pointer no disponible (ya cubierto, pero dejamos)
  // Evitar doble disparo: pointer ya cubre mouse/touch en browsers modernos

  replayBtn.addEventListener('click', () => {
    const last = [...transcripts].reverse().find((t) => t.role === 'bot');
    if (last) speak(last.text);
  });
  clearBtn.addEventListener('click', () => {
    transcripts = [];
    interim = '';
    isHolding = false;
    try { if (recog) recog.abort(); } catch {}
    speechSynthesis.cancel();
    setState('idle');
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
  setState('idle');

  return { element: wrap, getTranscripts: () => transcripts, speak, handleUserText, addBotMessage };
}
