// ================================================================
//  MANEJO DE SSE Y ACTUALIZACIÓN EN TIEMPO REAL
// ================================================================
const estadoConexion = document.getElementById('estado-conexion');
let ultimoEstado = 'Conectado';

// Inicializar gráficos
let priceChartInstance = null;
let rsiChartInstance = null;

function initCharts() {
    const ctxPrice = document.getElementById('priceChart').getContext('2d');
    const ctxRsi = document.getElementById('rsiChart').getContext('2d');

    // Precio
    priceChartInstance = new Chart(ctxPrice, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Precio BTC (USD)',
                data: [],
                borderColor: '#818cf8',
                backgroundColor: 'rgba(99, 102, 241, 0.1)',
                fill: true,
                tension: 0.2,
                pointRadius: 2,
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: {
                    grid: { color: 'rgba(255,255,255,0.05)' },
                    ticks: { color: '#94a3b8', font: { size: 10 } }
                },
                x: {
                    grid: { display: false },
                    ticks: { color: '#94a3b8', font: { size: 10 }, maxTicksLimit: 8 }
                }
            }
        }
    });

    // RSI
    rsiChartInstance = new Chart(ctxRsi, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'RSI',
                data: [],
                borderColor: '#fbbf24',
                backgroundColor: 'rgba(251, 191, 36, 0.1)',
                fill: true,
                tension: 0.2,
                pointRadius: 2,
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: {
                    min: 0,
                    max: 100,
                    grid: { color: 'rgba(255,255,255,0.05)' },
                    ticks: { color: '#94a3b8', font: { size: 10 } }
                },
                x: {
                    grid: { display: false },
                    ticks: { color: '#94a3b8', font: { size: 10 }, maxTicksLimit: 8 }
                }
            }
        }
    });
}

// Fuente SSE
const source = new EventSource('/api/stream');
source.onmessage = (e) => {
    const data = JSON.parse(e.data);
    const d = data.datos;
    const inv = data.inversion || {};

    // Actualizar estado de conexión
    ultimoEstado = 'Conectado';
    estadoConexion.innerText = ultimoEstado;

    // Actualizar resumen de inversión
    const cantidad = inv.cantidad_btc || 0;
    const objetivo = inv.precio_objetivo || 0;
    const precioActual = d.precio_actual || 0;
    const valorActual = cantidad * precioActual;
    const ganancia = objetivo > 0 ? ((precioActual - objetivo) / objetivo) * 100 : 0;

    document.getElementById('cantidad-btc').innerText = cantidad.toFixed(8);
    document.getElementById('valor-inversion').innerText = '$' + valorActual.toFixed(2);
    document.getElementById('precio-objetivo').innerText = '$' + objetivo.toFixed(2);
    const gpEl = document.getElementById('ganancia-perdida');
    gpEl.innerText = (ganancia > 0 ? '+' : '') + ganancia.toFixed(2) + '%';
    gpEl.className = 'text-2xl font-bold ' + (ganancia > 0 ? 'text-emerald-400' : ganancia < 0 ? 'text-red-400' : 'text-slate-400');

    // Barra de progreso
    if (objetivo > 0) {
        const progreso = Math.min((precioActual / objetivo) * 100, 100);
        document.getElementById('progreso-texto').innerText = progreso.toFixed(1) + '%';
        document.getElementById('progreso-bar').style.width = progreso + '%';
        document.getElementById('objetivo-label').innerText = '$' + objetivo.toFixed(2);
        if (precioActual >= objetivo) {
            document.getElementById('progreso-bar').className = 'progress-fill bg-gradient-to-r from-emerald-500 to-green-400';
        } else {
            document.getElementById('progreso-bar').className = 'progress-fill bg-gradient-to-r from-indigo-500 to-emerald-400';
        }
    } else {
        document.getElementById('progreso-texto').innerText = '0%';
        document.getElementById('progreso-bar').style.width = '0%';
        document.getElementById('objetivo-label').innerText = '$0';
    }

    // Cargar valores en inputs si no están enfocados
    if (!document.activeElement || (document.activeElement.id !== 'input-cantidad' && document.activeElement.id !== 'input-objetivo')) {
        document.getElementById('input-cantidad').value = cantidad || '';
        document.getElementById('input-objetivo').value = objetivo || '';
    }

    // Actualizar gráficos
    const precio = d.precio_actual || 0;
    const rsi = d.rsi || 50;
    const hora = d.hora_venezuela || '--:--';

    // Precio chart
    if (priceChartInstance) {
        priceChartInstance.data.labels.push(hora);
        priceChartInstance.data.datasets[0].data.push(precio);
        if (priceChartInstance.data.labels.length > 20) {
            priceChartInstance.data.labels.shift();
            priceChartInstance.data.datasets[0].data.shift();
        }
        priceChartInstance.update('none');
    }

    // RSI chart
    if (rsiChartInstance) {
        rsiChartInstance.data.labels.push(hora);
        rsiChartInstance.data.datasets[0].data.push(rsi);
        if (rsiChartInstance.data.labels.length > 20) {
            rsiChartInstance.data.labels.shift();
            rsiChartInstance.data.datasets[0].data.shift();
        }
        rsiChartInstance.update('none');
    }

    // Actualizar historial detallado
    const historial = data.historial || [];
    const tbody = document.getElementById('historial-detallado');
    tbody.innerHTML = historial.map(h => {
        const valorInv = cantidad * h.precio;
        return `
            <tr>
                <td class="py-2 px-3 text-slate-400">${h.fecha}</td>
                <td class="py-2 px-3 text-right text-white font-medium">$${h.precio.toLocaleString()}</td>
                <td class="py-2 px-3 text-right">
                    <span class="text-xs px-2 py-1 rounded-full 
                        ${h.estado === 'Sobrevendido' ? 'bg-blue-500/20 text-blue-400' :
                          h.estado === 'Sobrecomprado' ? 'bg-red-500/20 text-red-400' :
                          'bg-amber-500/20 text-amber-400'}">
                        ${h.estado}
                    </span>
                </td>
                <td class="py-2 px-3 text-right text-slate-300">$${valorInv.toFixed(2)}</td>
            </tr>
        `;
    }).join('') || '<tr><td colspan="4" class="text-center text-slate-500 py-4">No hay datos históricos aún</td></tr>';
};

source.onerror = (e) => {
    estadoConexion.innerText = '⚠️ Reconectando...';
    // El navegador reintenta automáticamente
};

// ================================================================
//  FUNCIONES DE INVERSIÓN
// ================================================================
const mensajeInversion = document.getElementById('mensaje-inversion');

async function guardarInversion(cantidad, objetivo) {
    if (cantidad <= 0 || objetivo <= 0) {
        mensajeInversion.innerHTML = '<span class="text-red-400">⚠️ Ambos campos deben ser mayores a 0</span>';
        return false;
    }
    try {
        const resp = await fetch('/api/actualizar_inversion', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ cantidad_btc: cantidad, precio_objetivo: objetivo })
        });
        const data = await resp.json();
        if (data.status === 'ok') {
            mensajeInversion.innerHTML = '<span class="text-emerald-400">✅ ' + data.mensaje + '</span>';
            return true;
        } else {
            mensajeInversion.innerHTML = '<span class="text-red-400">❌ ' + data.mensaje + '</span>';
            return false;
        }
    } catch (err) {
        mensajeInversion.innerHTML = '<span class="text-red-400">❌ Error al guardar</span>';
        return false;
    }
}

// Botón Guardar
document.getElementById('btn-guardar-inversion').addEventListener('click', async function() {
    const cantidad = parseFloat(document.getElementById('input-cantidad').value) || 0;
    const objetivo = parseFloat(document.getElementById('input-objetivo').value) || 0;
    this.disabled = true;
    this.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Guardando...';
    await guardarInversion(cantidad, objetivo);
    this.disabled = false;
    this.innerHTML = '<i class="fas fa-save"></i> Guardar';
});

// Botón Limpiar
document.getElementById('btn-limpiar-inversion').addEventListener('click', async function() {
    document.getElementById('input-cantidad').value = '';
    document.getElementById('input-objetivo').value = '';
    mensajeInversion.innerHTML = '';
    try {
        await fetch('/api/actualizar_inversion', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ cantidad_btc: 0, precio_objetivo: 0 })
        });
        mensajeInversion.innerHTML = '<span class="text-slate-400">🧹 Datos limpiados</span>';
    } catch (err) {
        mensajeInversion.innerHTML = '<span class="text-red-400">❌ Error al limpiar</span>';
    }
});

// Botón Alertar ahora
document.getElementById('btn-enviar-alerta-inversion').addEventListener('click', async function() {
    this.disabled = true;
    this.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Enviando...';
    try {
        const resp = await fetch('/api/enviar_alerta', { method: 'POST' });
        const data = await resp.json();
        alert(data.status === 'ok' ? '✅ Alerta enviada con los datos de inversión' : '❌ ' + data.mensaje);
    } catch (err) {
        alert('❌ Error al enviar la alerta');
    } finally {
        this.disabled = false;
        this.innerHTML = '<i class="fas fa-bell"></i> Alertar ahora';
    }
});

// Botón de alerta en navbar
document.getElementById('btn-alerta').addEventListener('click', async function() {
    const original = this.innerHTML;
    this.disabled = true;
    this.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Enviando...';
    try {
        const resp = await fetch('/api/enviar_alerta', { method: 'POST' });
        const data = await resp.json();
        alert(data.status === 'ok' ? '✅ Alerta enviada' : '❌ ' + data.mensaje);
    } catch (err) {
        alert('❌ Error al enviar la alerta');
    } finally {
        this.disabled = false;
        this.innerHTML = original;
    }
});

// ================================================================
//  INICIALIZACIÓN
// ================================================================
initCharts();
