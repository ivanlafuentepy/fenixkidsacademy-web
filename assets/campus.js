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

  /** Rellena los elementos de la página que pidan el dato por id. */
  function pintar() {
    var c = proximoCampus();
    var elFechas = document.getElementById('campusFechas');
    if (elFechas) elFechas.textContent = label(c);

    var elPrecio = document.getElementById('campusPrecio');
    if (elPrecio) {
      elPrecio.innerHTML = c.anticipada
        ? 'Reservando ahora: <b>' + fmt(PRECIO_ANTICIPADA) + ' Gs</b> · precio normal ' + fmt(PRECIO_NORMAL)
        : '<b>' + fmt(PRECIO_NORMAL) + ' Gs</b> · la reserva anticipada de este campus ya cerró';
    }
    return c;
  }

  return {
    proximoCampus: proximoCampus,
    label: label,
    precio: precio,
    fmt: fmt,
    pintar: pintar,
    PRECIO_ANTICIPADA: PRECIO_ANTICIPADA,
    PRECIO_NORMAL: PRECIO_NORMAL,
    EXTRA_HERMANO: EXTRA_HERMANO,
  };
})();
