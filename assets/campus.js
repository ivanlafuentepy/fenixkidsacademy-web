/* assets/campus.js — Fechas y precios del DESAFÍO FENIX, en un solo lugar.
 *
 * Lo usan index.html y desafio.html. Vive acá y no repetido en cada página
 * porque este proyecto ya se quemó con precios sueltos en varios archivos: uno
 * se actualiza, el otro no, y el padre recibe dos números distintos.
 *
 * Mismo criterio que agent/desafio.py del repo del agente:
 *   - el campus se identifica por su VIERNES;
 *   - se deja de vender cuando arranca el turno 1 (viernes 17:00 hora PY);
 *   - la reserva anticipada vale hasta el jueves 23:59.
 * Si cambia allá, cambia acá.
 */
window.FENIX_CAMPUS = (function () {
  'use strict';

  var MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
               'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];

  var PRECIO_ANTICIPADA = 350000;
  var PRECIO_NORMAL = 550000;
  var EXTRA_HERMANO = 150000;

  /** Hora de Paraguay, no la del visitante. */
  function ahoraPY() {
    return new Date(new Date().toLocaleString('en-US', { timeZone: 'America/Asuncion' }));
  }

  /** {viernes, sabado, domingo, anticipada} del campus que se está vendiendo. */
  function proximoCampus(ahora) {
    ahora = ahora || ahoraPY();
    var viernes = new Date(ahora);
    viernes.setHours(0, 0, 0, 0);
    viernes.setDate(viernes.getDate() + ((5 - viernes.getDay() + 7) % 7));
    var esHoyViernes = viernes.toDateString() === new Date(ahora).toDateString();
    if (esHoyViernes && ahora.getHours() >= 17) viernes.setDate(viernes.getDate() + 7);

    var sabado = new Date(viernes);  sabado.setDate(viernes.getDate() + 1);
    var domingo = new Date(viernes); domingo.setDate(viernes.getDate() + 2);
    var hoy0 = new Date(ahora); hoy0.setHours(0, 0, 0, 0);

    return { viernes: viernes, sabado: sabado, domingo: domingo, anticipada: hoy0 < viernes };
  }

  /** "viernes 14, sábado 15 y domingo 16 de agosto" */
  function label(c) {
    c = c || proximoCampus();
    if (c.viernes.getMonth() === c.domingo.getMonth()) {
      return 'viernes ' + c.viernes.getDate() + ', sábado ' + c.sabado.getDate() +
             ' y domingo ' + c.domingo.getDate() + ' de ' + MESES[c.viernes.getMonth()];
    }
    return 'viernes ' + c.viernes.getDate() + ' de ' + MESES[c.viernes.getMonth()] +
           ', sábado ' + c.sabado.getDate() + ' de ' + MESES[c.sabado.getMonth()] +
           ' y domingo ' + c.domingo.getDate() + ' de ' + MESES[c.domingo.getMonth()];
  }

  /** Momento en que se corta el precio anticipado: jueves 23:59:59 de esa semana. */
  function cierreAnticipada(c) {
    var t = new Date(c.viernes);
    t.setDate(t.getDate() - 1);
    t.setHours(23, 59, 59, 999);
    return t;
  }

  /** Momento en que arranca el campus: viernes 17:00, el turno 1. */
  function arranque(c) {
    var t = new Date(c.viernes);
    t.setHours(17, 0, 0, 0);
    return t;
  }

  /** 297000000 → "3 días y 10 horas". Días y horas mientras haya días; después
   *  horas y minutos, para que la última tarde no muestre siempre "0 días". */
  function faltante(ms) {
    var min = Math.floor(ms / 60000);
    var dias = Math.floor(min / 1440);
    var horas = Math.floor((min % 1440) / 60);
    var minutos = min % 60;
    function u(n, sing, plur) { return n + ' ' + (n === 1 ? sing : plur); }
    if (dias > 0) return u(dias, 'día', 'días') + ' y ' + u(horas, 'hora', 'horas');
    if (horas > 0) return u(horas, 'hora', 'horas') + ' y ' + u(minutos, 'minuto', 'minutos');
    if (minutos < 1) return 'menos de 1 minuto';
    return u(minutos, 'minuto', 'minutos');
  }

  /** 350000 → "350.000" */
  function fmt(n) {
    return n.toString().replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  }

  /** Precio del campus para esa cantidad de hijos. */
  function precio(hijos, c) {
    c = c || proximoCampus();
    var base = c.anticipada ? PRECIO_ANTICIPADA : PRECIO_NORMAL;
    return base + EXTRA_HERMANO * (Math.max(1, hijos || 1) - 1);
  }

  /* El pago con tarjeta NO se cobra desde la web: el botón abre WhatsApp y el
   * link de pago lo manda Aurora, firmado con el teléfono del padre. Así el pago
   * queda atribuido a la familia y dispara solo el formulario y la reserva —
   * un link de la web no lleva teléfono y el cobro quedaba huérfano. */

  var tick = null;

  /** Aplica fn a todos los elementos con esa clase. Por clase y no por id porque
   *  la misma página repite el dato en el hero y en las bandas de cada sección. */
  function cada(clase, fn) {
    var els = document.querySelectorAll('.' + clase);
    for (var i = 0; i < els.length; i++) fn(els[i]);
  }

  /** Rellena todos los elementos de la página que pidan el dato por clase.
   *  Se repite sola cada 30 s: así la pestaña que quedó abierta pasa al campus
   *  siguiente el viernes a las 17 sin que el padre tenga que recargar. */
  function pintar() {
    var c = proximoCampus();

    cada('js-campus-fechas', function (el) { el.textContent = label(c); });

    cada('js-campus-precio', function (el) {
      el.innerHTML = c.anticipada
        ? 'Reservando ahora: <b>' + fmt(PRECIO_ANTICIPADA) + ' Gs</b> · precio normal ' + fmt(PRECIO_NORMAL)
        : '<b>' + fmt(PRECIO_NORMAL) + ' Gs</b> · la reserva anticipada de este campus ya cerró';
    });

    // Antes del viernes se cuenta al cierre del precio anticipado (jueves a la
    // medianoche); el viernes mismo ya no hay descuento que perder, se cuenta
    // a la hora de arranque.
    var restante = (c.anticipada ? cierreAnticipada(c) : arranque(c)) - ahoraPY();
    var texto = c.anticipada
      ? '⏳ La reserva anticipada cierra en <b>' + faltante(restante) + '</b>'
      : '🔥 El campus arranca en <b>' + faltante(restante) + '</b>';
    cada('js-campus-cuenta', function (el) {
      if (restante > 0) { el.innerHTML = texto; el.style.display = ''; }
      else { el.style.display = 'none'; }
    });

    if (!tick) tick = setInterval(pintar, 30000);
    return c;
  }

  return {
    proximoCampus: proximoCampus,
    label: label,
    precio: precio,
    cierreAnticipada: cierreAnticipada,
    arranque: arranque,
    faltante: faltante,
    fmt: fmt,
    pintar: pintar,
    PRECIO_ANTICIPADA: PRECIO_ANTICIPADA,
    PRECIO_NORMAL: PRECIO_NORMAL,
    EXTRA_HERMANO: EXTRA_HERMANO,
  };
})();
