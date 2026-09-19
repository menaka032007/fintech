const $ = (id) => document.getElementById(id)
const ASSETS = ['Gold', 'Bitcoin', 'NVIDIA']
const COLORS = { Gold: '#e9b55f', Bitcoin: '#f28b65', NVIDIA: '#55d6a4' }
const state = { asset: 'Gold', btAsset: 'Gold', strategy: 'sma', mode: 'simple', selectedDate: null }
const money = (value) => value == null ? '—' : '$' + Number(value).toLocaleString('en-US', { maximumFractionDigits: 2 })
const pct = (value) => value == null ? '—' : (Number(value) * 100).toFixed(2) + '%'
const num = (value) => value == null ? '—' : Number(value).toFixed(2)
const dark = { paper_bgcolor: 'transparent', plot_bgcolor: 'transparent', font: { color: '#8ea1b0', family: 'Segoe UI,Arial' }, colorway: ['#62b4ff', '#42d3a6', '#e9b55f', '#ff7c83'], margin: { t: 28, l: 58, r: 18, b: 42 }, xaxis: { gridcolor: '#263747', linecolor: '#263747' }, yaxis: { gridcolor: '#263747', linecolor: '#263747' } }

async function get(url) {
  const response = await fetch(url)
  const body = await response.json()
  if (!response.ok || body.success === false) throw Error(body.error || 'Request failed')
  return body
}

function query() {
  return new URLSearchParams({ period: $('period').value, sma_short: $('smaShort').value, sma_long: $('smaLong').value, ema_period: $('emaPeriod').value, rolling_window: $('corrWindow').value }).toString()
}

function metric(label, value, tone = '') { return `<div class="metric"><small>${label}</small><b class="${tone}">${value}</b></div>` }
function formatDate(value) { return value ? new Date(value).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }) : '—' }
function value(value, formatter = num) { return value == null || Number.isNaN(Number(value)) ? 'N/A' : formatter(value) }
function plot(id, traces, layout = {}) { Plotly.newPlot(id, traces, { ...dark, ...layout }, { responsive: true, displaylogo: false }) }
function showError(error) { $('error').textContent = 'Market data could not be retrieved right now. Please try again.'; $('error').classList.remove('hidden'); console.error(error) }

async function load() {
  $('error').classList.add('hidden'); $('refresh').disabled = true; $('refresh').textContent = '↻ Loading market data…'
  try {
    const q = query()
    const [overview, market, risk, correlation] = await Promise.all([get('/api/overview?' + q), get('/api/market-data?' + q), get('/api/risk?' + q), get('/api/correlation?' + q)])
    state.overview = overview; state.market = market; state.risk = risk; state.correlation = correlation
    await loadAsset(); await loadBacktest(); await loadComparison(); renderAll()
  } catch (error) { showError(error) } finally { $('refresh').disabled = false; $('refresh').textContent = '↻ Refresh data' }
}

async function loadAsset() { state.assetData = await get(`/api/asset/${encodeURIComponent(state.asset)}?${query()}`) }
async function loadBacktest() {
  const parameters = `initial_capital=${$('initialCapital')?.value || 1000}&transaction_cost=${Number($('cost')?.value || .1) / 100}&position_size=${Number($('positionSize')?.value || 100) / 100}`
  state.backtest = await get(`/api/backtest?${query()}&asset=${state.btAsset}&strategy=${state.strategy}&${parameters}`)
}
async function loadComparison() { state.comparison = await get(`/api/strategy-comparison?${query()}&asset=${state.btAsset}`) }

function renderAll() {
  const period = state.overview.period
  $('dateWindow').textContent = `${formatDate(period.start)} → ${formatDate(period.end)}`
  $('dataDate').textContent = period.end
  renderCards(); renderAsset(); renderRisk(); renderCorrelation(); renderBacktest(); renderComparison(); renderSummary(); renderRegimes()
  $('marketExport').href = '/api/export/market.csv?' + query()
}

function renderCards() {
  const metrics = Object.fromEntries(state.overview.assets.map((item) => [item.asset, item]))
  const selected = metrics[state.asset] || state.overview.assets[0]
  $('whatHappenedText').textContent = selected.what_happened || `${selected.asset} recorded ${pct(selected.total_return)} during the selected historical period.`
  $('whatHappenedStats').innerHTML = metric('Return', pct(selected.total_return), selected.total_return >= 0 ? 'positive' : 'negative') + metric('Volatility', pct(selected.volatility)) + metric('Maximum drawdown', pct(selected.max_drawdown), 'negative')
  $('assetCards').innerHTML = ASSETS.map((name) => { const item = metrics[name]; return `<article class="asset-card"><div class="asset-card-top"><b><span style="color:${COLORS[name]}">●</span> ${name}</b><span class="ticker">${name === 'Gold' ? 'GC=F' : name === 'Bitcoin' ? 'BTC-USD' : 'NVDA'}</span></div><div class="asset-price">${money(item.latest_price)}</div><div class="asset-change"><b class="${item.daily_return >= 0 ? 'positive' : 'negative'}">${pct(item.daily_return)}</b><small>latest daily return</small></div><div class="asset-metrics">${metric('Selected return', pct(item.total_return), item.total_return >= 0 ? 'positive' : 'negative')}${metric('CAGR', pct(item.annualized_return))}${metric('Annualized vol', pct(item.volatility))}${metric('Sharpe ratio', num(item.sharpe), 'positive')}${metric('Max drawdown', pct(item.max_drawdown), 'negative')}${metric('Regime', item.regime)}</div><p class="card-explanation">${item.explanation || ''}</p></article>` }).join('')
  renderRiskReturn(state.overview.assets)
}

function renderRiskReturn(metrics) { plot('riskReturnChart', [{ x: metrics.map((item) => item.volatility), y: metrics.map((item) => item.total_return), text: metrics.map((item) => item.asset), mode: 'markers+text', textposition: 'top center', textfont: { color: '#e7eff5' }, marker: { size: 15, color: metrics.map((item) => COLORS[item.asset]), line: { color: '#081018', width: 1 } }, customdata: metrics.map((item) => [item.asset, item.sharpe, item.max_drawdown]), hovertemplate: '<b>%{customdata[0]}</b><br>Return: %{y:.2%}<br>Volatility: %{x:.2%}<br>Sharpe: %{customdata[1]:.2f}<br>Max drawdown: %{customdata[2]:.2%}<extra></extra>' }], { xaxis: { title: 'Annualized volatility', tickformat: '.0%' }, yaxis: { title: 'Historical return', tickformat: '.0%' }, margin: { t: 22, l: 65, r: 18, b: 55 } }) }

function renderAsset() {
  const rows = state.assetData.prices; const dates = rows.map((row) => row.date)
  state.selectedDate = rows.some((row) => row.date === state.selectedDate) ? state.selectedDate : rows[rows.length - 1]?.date
  $('chartExplanation').textContent = state.assetData.explanations?.chart || 'The chart shows price, moving averages, and historical drawdown.'
  plot('priceChart', [{ x: dates, y: rows.map((row) => row.close), name: 'Close', line: { color: COLORS[state.asset], width: 2 } }, { x: dates, y: rows.map((row) => row.sma), name: 'SMA ' + $('smaShort').value, line: { color: '#62b4ff' } }, { x: dates, y: rows.map((row) => row.sma_long), name: 'SMA ' + $('smaLong').value, line: { color: '#6a7d90', dash: 'dot' } }, { x: dates, y: rows.map((row) => row.ema), name: 'EMA ' + $('emaPeriod').value, line: { color: '#e9b55f', dash: 'dash' } }, { x: rows.filter((row) => row.buy_signal).map((row) => row.date), y: rows.filter((row) => row.buy_signal).map((row) => row.close), name: 'Buy', mode: 'markers', marker: { color: '#42d3a6', symbol: 'triangle-up', size: 9 } }, { x: rows.filter((row) => row.sell_signal).map((row) => row.date), y: rows.filter((row) => row.sell_signal).map((row) => row.close), name: 'Sell', mode: 'markers', marker: { color: '#ff7c83', symbol: 'triangle-down', size: 9 } }], { hovermode: 'x unified', yaxis: { title: 'Price' } })
  plot('performanceChart', [{ x: dates, y: rows.map((row) => row.cumulative_return), name: 'Cumulative return', fill: 'tozeroy', line: { color: '#42d3a6' } }], { yaxis: { tickformat: '.0%' } })
  plot('returnsChart', [{ x: dates, y: rows.map((row) => row.daily_return), name: 'Daily return', type: 'bar', marker: { color: '#62b4ff' } }, { x: dates, y: rows.map((row) => row.drawdown), name: 'Drawdown', line: { color: '#ff7c83' }, yaxis: 'y2' }], { yaxis: { tickformat: '.0%' }, yaxis2: { overlaying: 'y', side: 'right', tickformat: '.0%', gridcolor: 'transparent' } })
  $('indicatorTable').innerHTML = `<table><tr><th>Date</th><th>Close</th><th>Daily</th><th>Cumulative</th><th>Rolling return</th><th>Rolling vol</th><th>Regime</th></tr>${rows.slice(-8).reverse().map((row) => `<tr><td>${row.date}</td><td>${money(row.close)}</td><td>${pct(row.daily_return)}</td><td>${pct(row.cumulative_return)}</td><td>${pct(row.rolling_return)}</td><td>${pct(row.annualized_volatility)}</td><td>${row.regime}</td></tr>`).join('')}</table>`
  bindDateClicks(rows); renderSelectedDate(rows.find((row) => row.date === state.selectedDate))
}

function bindDateClicks(rows) {
  const selectDate = (event) => {
    const point = event?.points?.[0]
    if (!point) return
    const selected = rows.find((row) => row.date === String(point.x).slice(0, 10))
    if (selected) { state.selectedDate = selected.date; renderSelectedDate(selected) }
  }
  const priceChart = $('priceChart'); const performanceChart = $('performanceChart')
  priceChart.removeAllListeners?.('plotly_click'); performanceChart.removeAllListeners?.('plotly_click')
  priceChart.on('plotly_click', selectDate); performanceChart.on('plotly_click', selectDate)
}

function renderSelectedDate(row) {
  if (!row) { $('selectedDateDetails').innerHTML = '<p class="empty-state">No historical row is available for this selection.</p>'; return }
  $('selectedDateBadge').textContent = `${state.asset} · ${formatDate(row.date)}`
  const details = [
    metric('Selected date', formatDate(row.date)), metric('Asset', state.asset), metric('Closing price', money(row.close)),
    metric('Daily return', value(row.daily_return, pct), row.daily_return >= 0 ? 'positive' : 'negative'), metric('Cumulative return', value(row.cumulative_return, pct), row.cumulative_return >= 0 ? 'positive' : 'negative'),
    metric('SMA short', value(row.sma, money)), metric('SMA long', value(row.sma_long, money)), metric('EMA', value(row.ema, money)),
    metric('Rolling return', value(row.rolling_return, pct)), metric('Rolling volatility', value(row.annualized_volatility, pct)), metric('Drawdown', value(row.drawdown, pct), 'negative'),
    metric('Market regime', row.regime || 'N/A')
  ]
  $('selectedDateDetails').innerHTML = details.join('')
  Plotly.relayout('priceChart', { shapes: [{ type: 'line', x0: row.date, x1: row.date, y0: 0, y1: 1, yref: 'paper', line: { color: '#e7eff5', width: 1, dash: 'dot' } }] })
  Plotly.relayout('performanceChart', { shapes: [{ type: 'line', x0: row.date, x1: row.date, y0: 0, y1: 1, yref: 'paper', line: { color: '#e7eff5', width: 1, dash: 'dot' } }] })
}

function renderRisk() {
  const rows = state.risk.assets; $('riskTable').innerHTML = `<table><tr><th>Asset</th><th>Annualized return</th><th>Volatility</th><th>Downside vol</th><th>Sharpe</th><th>Max drawdown</th><th>Observations</th></tr>${rows.map((item) => `<tr><td><b>${item.asset}</b></td><td class="${item.annualized_return >= 0 ? 'positive' : 'negative'}">${pct(item.annualized_return)}</td><td>${pct(item.volatility)}</td><td>${pct(item.downside_volatility)}</td><td class="positive">${num(item.sharpe)}</td><td class="negative">${pct(item.max_drawdown)}</td><td>${item.observations}</td></tr>`).join('')}</table>`
  const item = rows.find((row) => row.asset === state.asset) || rows[0]
  plot('volChart', [{ x: item.rolling_volatility.map((row) => row.date), y: item.rolling_volatility.map((row) => row.value), name: 'Annualized volatility', line: { color: '#e9b55f' } }], { yaxis: { tickformat: '.0%' } })
  plot('drawdownChart', [{ x: item.drawdown.map((row) => row.date), y: item.drawdown.map((row) => row.value), name: 'Drawdown', fill: 'tozeroy', line: { color: '#ff7c83' } }], { yaxis: { tickformat: '.0%' } })
  if (state.assetData.drawdown && $('drawdownExplanation')) { const dd = state.assetData.drawdown; $('drawdownExplanation').innerHTML = `<b>UNDERSTAND THIS DRAWDOWN</b><p>The largest peak-to-trough decline was ${pct(dd.drawdown)}, from ${dd.peak_date} to ${dd.trough_date}. ${dd.recovered ? `The previous peak was recovered on ${dd.recovery_date}.` : 'The previous peak was not recovered within the selected period.'} ${dd.context}</p>` }
}

function renderCorrelation() {
  const assets = state.correlation.assets; const values = assets.map((row) => assets.map((column) => Number(state.correlation.matrix[row][column] || 0)))
  plot('heatmap', [{ z: values, x: assets, y: assets, type: 'heatmap', zmin: -1, zmax: 1, text: values.map((row) => row.map((value) => value.toFixed(2))), texttemplate: '%{text}', colorscale: [[0, '#29466e'], [.5, '#14212c'], [1, '#42d3a6']] }], { margin: { t: 15, l: 60, r: 10, b: 45 } })
  const pair = Object.keys(state.correlation.rolling)[0]; const series = state.correlation.rolling[pair] || []
  plot('corrChart', [{ x: series.map((row) => row.date), y: series.map((row) => row.value), name: pair, line: { color: '#62b4ff' } }], { yaxis: { range: [-1, 1] } })
  $('correlationExplanation').textContent = state.correlation.explanation || (pair ? `${pair.replace(':', ' and ')} showed the historical rolling co-movement displayed above. Correlation describes co-movement; it does not imply causation.` : 'No pair is available for the selected assets.')
}

function renderBacktest() {
  const result = state.backtest; const metrics = result.metrics; const benchmark = result.buy_hold
  $('strategyExplanation').textContent = result.explanations?.strategy || 'The selected strategy explanation is unavailable.'
  $('btMetrics').innerHTML = metric('Final portfolio', money(metrics.final_value), 'positive') + metric('Strategy return', pct(metrics.total_return), metrics.total_return >= 0 ? 'positive' : 'negative') + metric('Buy & hold', pct(benchmark.total_return), benchmark.total_return >= 0 ? 'positive' : 'negative') + metric('Sharpe', num(metrics.sharpe), 'positive') + metric('Trades', metrics.trades)
  plot('btChart', [{ x: result.chart.map((row) => row.date), y: result.chart.map((row) => row.equity), name: result.strategy_name, line: { color: '#42d3a6', width: 2 } }, { x: result.chart.map((row) => row.date), y: result.chart.map((row) => row.buy_hold), name: 'Buy & Hold', line: { color: '#6b7d8f', dash: 'dot' } }, { x: result.chart.filter((row) => row.buy).map((row) => row.date), y: result.chart.filter((row) => row.buy).map((row) => row.equity), name: 'Buy', mode: 'markers', marker: { color: '#42d3a6', symbol: 'triangle-up', size: 8 } }, { x: result.chart.filter((row) => row.sell).map((row) => row.date), y: result.chart.filter((row) => row.sell).map((row) => row.equity), name: 'Sell', mode: 'markers', marker: { color: '#ff7c83', symbol: 'triangle-down', size: 8 } }], { hovermode: 'x unified', yaxis: { title: 'Portfolio value' } })
  $('btTable').innerHTML = `<table><tr><th>Metric</th><th>Strategy</th><th>Buy & Hold</th></tr>${[['Total return', pct(metrics.total_return), pct(benchmark.total_return)], ['Annualized return', pct(metrics.annualized_return), pct(benchmark.annualized_return)], ['Volatility', pct(metrics.volatility), pct(benchmark.volatility)], ['Sharpe', num(metrics.sharpe), num(benchmark.sharpe)], ['Max drawdown', pct(metrics.max_drawdown), pct(benchmark.max_drawdown)], ['Trades', metrics.trades, 0]].map((row) => `<tr><td>${row[0]}</td><td class="positive">${row[1]}</td><td>${row[2]}</td></tr>`).join('')}</table>`
  const trades = result.trades.slice(-8).reverse(); $('tradesTable').innerHTML = `<table><tr><th>Date</th><th>Side</th><th>Price</th><th>Reason</th><th>Position</th><th>Cost</th></tr>${trades.map((trade) => `<tr><td>${trade.date}</td><td class="${trade.side === 'BUY' ? 'positive' : 'negative'}">${trade.side}</td><td>${money(trade.price)}</td><td>${trade.reason || 'Signal threshold changed.'}</td><td>${pct(trade.position)}</td><td>${money(trade.transaction_cost)}</td></tr>`).join('')}</table>`
  $('tradeExport').href = `/api/export/trades.csv?${query()}&asset=${state.btAsset}&strategy=${state.strategy}`
  $('backtestExplanation').textContent = ''
}

function renderComparison() { const rows = state.comparison?.strategies || []; $('comparisonTable').innerHTML = `<table><tr><th>Strategy</th><th>Return</th><th>Volatility</th><th>Sharpe</th><th>Max drawdown</th><th>Trades</th></tr>${rows.map((item) => `<tr><td><b>${item.strategy_name}</b></td><td class="${item.metrics.total_return >= 0 ? 'positive' : 'negative'}">${pct(item.metrics.total_return)}</td><td>${pct(item.metrics.volatility)}</td><td>${num(item.metrics.sharpe)}</td><td class="negative">${pct(item.metrics.max_drawdown)}</td><td>${item.metrics.trades}</td></tr>`).join('')}</table>` }

function renderSummary() { const rows = state.overview.assets; const highest = rows.reduce((a, b) => a.total_return > b.total_return ? a : b); const volatile = rows.reduce((a, b) => a.volatility > b.volatility ? a : b); $('summaryCards').innerHTML = rows.map((item) => `<article class="panel"><b>${item.asset}</b>${metric('Historical return', pct(item.total_return), item.total_return >= 0 ? 'positive' : 'negative')}${metric('Risk-adjusted return', num(item.sharpe), 'positive')}${metric('Drawdown', pct(item.max_drawdown), 'negative')}</article>`).join(''); $('insights').innerHTML = [`${highest.asset} recorded the highest historical return in the selected window.`, `${volatile.asset} recorded the highest annualized volatility.`, 'Correlation is historical and can change across market regimes.', 'Backtest results are historical research outputs, not future performance claims.'].map((text) => `<div class="insight">${text}</div>`).join('') }
function renderRegimes() { $('regimeTable').innerHTML = `<table><tr><th>Historical regime</th><th>Observations</th><th>Return</th><th>Volatility</th><th>Drawdown</th></tr>${(state.assetData.regimes || []).map((row) => `<tr><td><b>${row.regime}</b></td><td>${row.observations}</td><td class="${row.return >= 0 ? 'positive' : 'negative'}">${pct(row.return)}</td><td>${pct(row.volatility)}</td><td class="negative">${pct(row.drawdown)}</td></tr>`).join('')}</table>` }

async function applyAsset() { state.asset = $('assetSelect').value; state.btAsset = $('btAsset').value; await load() }
$('period').onchange = load; $('refresh').onclick = load; $('assetSelect').onchange = applyAsset; $('applyIndicators').onclick = load; $('corrWindow').onchange = load
$('runBacktest').onclick = async () => { state.btAsset = $('btAsset').value; state.strategy = $('strategy').value; $('runBacktest').textContent = 'Running historical simulation…'; await loadBacktest(); renderBacktest(); $('runBacktest').textContent = 'Run backtest' }
$('btAsset').onchange = async () => { state.btAsset = $('btAsset').value; await loadBacktest(); await loadComparison(); renderBacktest(); renderComparison() }
$('strategy').onchange = async () => { state.strategy = $('strategy').value; await loadBacktest(); renderBacktest() }
$('applyRobustness').onclick = async () => { await loadBacktest(); $('robustnessResult').innerHTML = `<div class="insight">Scenario rerun complete: ${state.backtest.strategy_name} ended at ${money(state.backtest.metrics.final_value)} with ${state.backtest.metrics.trades} trades. Historical sensitivity only.</div>` }
$('explainBacktest').onclick = () => { $('backtestExplanation').textContent = state.backtest.explanations?.summary || 'Historical backtest explanation is unavailable.' }
$('simpleMode').onclick = () => { state.mode = 'simple'; document.body.classList.remove('research-mode'); $('simpleMode').classList.add('selected'); $('researchMode').classList.remove('selected') }
$('researchMode').onclick = () => { state.mode = 'research'; document.body.classList.add('research-mode'); $('researchMode').classList.add('selected'); $('simpleMode').classList.remove('selected') }
$('menuBtn').onclick = () => document.querySelector('.sidebar').classList.toggle('open')
load()
