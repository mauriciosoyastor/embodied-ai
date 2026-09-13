export const percepcion = {
  name: "Percepción fullscreen",
  mount(container) {
    container.classList.add("v-percepcion");
    const wrap = document.createElement("div");
    wrap.className = "percepcion-full";
    // Ancla reutilizada por attachPercepcionPanel (misma clase que controlroom
    // para no tocar main.js más que el reset de estilos flotantes).
    const dash = document.createElement("div");
    dash.className = "room-dash percepcion-dash";
    wrap.appendChild(dash);
    // Salida mínima: link discreto a las otras variantes (el switcher
    // queda oculto en este modo para no romper el fullscreen).
    const nav = document.createElement("div");
    nav.className = "percepcion-nav";
    nav.innerHTML = `variantes · <a href="?variant=a">a</a> · <a href="?variant=b">b</a> · <a href="?variant=c">c</a>`;
    wrap.appendChild(nav);
    container.appendChild(wrap);
    return {
      dispose() {
        wrap.remove();
        container.classList.remove("v-percepcion");
      },
    };
  },
};
