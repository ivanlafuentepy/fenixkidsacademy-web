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

  /* Turnos de cada día. Espejo de TURNOS_VIERNES/TURNOS_SABADO y RANGO_TURNO de
   * agent/desafio.py: si cambian allá, cambian acá. */
  var TURNOS = {
    viernes: [{ h: '17:00', txt: '17:00 a 18:30', ic: '☀️' },
              { h: '19:30', txt: '19:30 a 20:45', ic: '🌙' }],
    sabado:  [{ h: '11:00', txt: '11:00 a 12:30', ic: '☀️' },
              { h: '15:30', txt: '15:30 a 17:00', ic: '☀️' }],
  };

  /* Días que corren con otros turnos (feriados). La clave es la fecha, así que
   * la excepción se apaga sola cuando pasa — igual que TURNOS_ESPECIALES del
   * agente, y por el mismo motivo: nadie tiene que acordarse de revertirla. */
  var TURNOS_ESPECIALES = {
    '2026-08-14': ['17:00'],
    '2026-08-15': ['11:00'],
  };
  var MOTIVO_ESPECIAL = 'feriado';

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

  /** "2026-08-14" — la fecha en ISO local, para buscar en TURNOS_ESPECIALES. */
  function iso(fecha) {
    var m = fecha.getMonth() + 1, d = fecha.getDate();
    return fecha.getFullYear() + '-' + (m < 10 ? '0' : '') + m + '-' + (d < 10 ? '0' : '') + d;
  }

  /** Los turnos que corren ESE día (uno solo si es feriado). */
  function turnosDe(fecha, normales) {
    var horas = TURNOS_ESPECIALES[iso(fecha)];
    if (!horas) return normales;
    return normales.filter(function (t) { return horas.indexOf(t.h) !== -1; });
  }

  /** ¿Este campus tiene algún día con turno único? */
  function tieneTurnoUnico(c) {
    c = c || proximoCampus();
    return turnosDe(c.viernes, TURNOS.viernes).length < TURNOS.viernes.length ||
           turnosDe(c.sabado, TURNOS.sabado).length < TURNOS.sabado.length;
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

  /** 297000000 → {dias:3, horas:10, minutos:30, segundos:5} */
  function faltante(ms) {
    var s = Math.max(0, Math.floor(ms / 1000));
    return {
      dias: Math.floor(s / 86400),
      horas: Math.floor((s % 86400) / 3600),
      minutos: Math.floor((s % 3600) / 60),
      segundos: s % 60,
    };
  }

  /** 7 → "07", para que el reloj no cambie de ancho al pasar de 10 a 9. */
  function dosDigitos(n) { return (n < 10 ? '0' : '') + n; }

  /** El reloj vivo: una cajita por unidad. Los días se omiten cuando ya no queda
   *  ninguno, así el viernes se lee "16 horas 04 min 12 seg" y no "00 días". */
  function reloj(ms) {
    var f = faltante(ms);
    var u = [];
    if (f.dias > 0) u.push([f.dias, f.dias === 1 ? 'día' : 'días']);
    u.push([dosDigitos(f.horas), 'horas'], [dosDigitos(f.minutos), 'min'], [dosDigitos(f.segundos), 'seg']);
    var html = '';
    for (var i = 0; i < u.length; i++) {
      html += '<span class="cnt-u"><b>' + u[i][0] + '</b><i>' + u[i][1] + '</i></span>';
    }
    return '<span class="cnt-reloj">' + html + '</span>';
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
  var firma = null;

  /** Aplica fn a todos los elementos con esa clase. Por clase y no por id porque
   *  la misma página repite el dato en el hero y en las bandas de cada sección. */
  function cada(clase, fn) {
    var els = document.querySelectorAll('.' + clase);
    for (var i = 0; i < els.length; i++) fn(els[i]);
  }

  /** Los turnos de los días 1 y 2, y las notas del feriado.
   *
   *  El HTML trae los dos turnos escritos como fallback (si el JS no corre, el
   *  padre ve los horarios de siempre); acá se reemplazan por los que de verdad
   *  corren ese fin de semana.
   */
  function pintarTurnos(c) {
    [['js-turnos-viernes', c.viernes, TURNOS.viernes],
     ['js-turnos-sabado', c.sabado, TURNOS.sabado]].forEach(function (par) {
      var vigentes = turnosDe(par[1], par[2]);
      var unico = vigentes.length === 1;
      var html = '<div class="dt-lbl">' +
                 (unico ? 'Turno único · ' + MOTIVO_ESPECIAL : 'Elegís un turno') + '</div>';
      vigentes.forEach(function (t) {
        html += '<div class="turno">' + t.ic + ' ' + t.txt + '</div>';
      });
      cada(par[0], function (el) { el.innerHTML = html; });
    });

    // Notas sueltas (hero y FAQ): solo aparecen el fin de semana que aplica.
    var nota = tieneTurnoUnico(c)
      ? 'Este fin de semana, por el ' + MOTIVO_ESPECIAL + ', hay un solo turno por día.'
      : '';
    cada('js-nota-feriado', function (el) {
      el.textContent = nota;
      el.style.display = nota ? '' : 'none';
    });
  }

  /** Fechas y precio. Cambian una vez por semana, así que se repintan solo
   *  cuando el campus que se está mostrando deja de ser el vigente. */
  function pintarCampus(c) {
    cada('js-campus-fechas', function (el) { el.textContent = label(c); });
    pintarTurnos(c);
    cada('js-campus-precio', function (el) {
      el.innerHTML = c.anticipada
        ? 'Reservando ahora: <b>' + fmt(PRECIO_ANTICIPADA) + ' Gs</b> · precio normal ' + fmt(PRECIO_NORMAL)
        : '<b>' + fmt(PRECIO_NORMAL) + ' Gs</b> · la reserva anticipada de este campus ya cerró';
    });
  }

  /** El reloj, una vez por segundo.
   *  Antes del viernes se cuenta al cierre del precio anticipado (jueves 23:59);
   *  el viernes ya no hay descuento que perder, se cuenta a la hora de arranque. */
  function pintarCuenta(c, ahora) {
    var meta = c.anticipada ? cierreAnticipada(c) : arranque(c);
    var restante = meta - ahora;
    var hoy = meta.toDateString() === ahora.toDateString();
    var titulo = c.anticipada
      ? '⏳ La reserva anticipada cierra ' + (hoy ? 'hoy' : 'el jueves') + ' a las 23:59'
      : '🔥 El campus arranca hoy a las 17:00';
    var html = '<span class="cnt-lbl">' + titulo + '</span>' + reloj(restante);
    cada('js-campus-cuenta', function (el) {
      if (restante > 0) { el.innerHTML = html; el.style.display = ''; }
      else { el.style.display = 'none'; }
    });
  }

  /** Rellena todos los elementos de la página que pidan el dato por clase y deja
   *  el reloj corriendo. El tick de 1 s también hace que la pestaña que quedó
   *  abierta pase sola al campus siguiente el viernes a las 17. */
  function pintar() {
    var ahora = ahoraPY();
    var c = proximoCampus(ahora);
    var actual = c.viernes.getTime() + '|' + c.anticipada;
    if (actual !== firma) { firma = actual; pintarCampus(c); }
    pintarCuenta(c, ahora);
    if (!tick) tick = setInterval(pintar, 1000);
    return c;
  }

  return {
    proximoCampus: proximoCampus,
    label: label,
    precio: precio,
    cierreAnticipada: cierreAnticipada,
    arranque: arranque,
    faltante: faltante,
    reloj: reloj,
    turnosDe: turnosDe,
    tieneTurnoUnico: tieneTurnoUnico,
    TURNOS: TURNOS,
    fmt: fmt,
    pintar: pintar,
    PRECIO_ANTICIPADA: PRECIO_ANTICIPADA,
    PRECIO_NORMAL: PRECIO_NORMAL,
    EXTRA_HERMANO: EXTRA_HERMANO,
  };
})();
