package `in`.narayanscanner

import android.content.Context
import android.os.Handler
import android.os.Looper
import org.json.JSONArray
import org.json.JSONObject
import java.math.BigDecimal
import java.time.*
import java.time.format.DateTimeFormatter
import java.util.concurrent.Executors

internal data class ScannerState(
    val index: String = "NIFTY", val scanStatus: String = "", val sessionDate: String = "",
    val historical: List<Signal> = emptyList(), val checking: Boolean = true, val loggedIn: Boolean = false, val configured: Boolean = false,
    val busy: Boolean = false, val status: String = "Checking saved session…",
    val markets: List<Pair<String, Tick?>> = emptyList(), val quotes: List<Pair<Quote, Tick>> = emptyList(),
    val history: List<Signal> = emptyList(), val targets: List<String> = List(6) { "" },
    val digit1: String = "6", val digit2: String = "9", val expiries: List<String> = emptyList(),
    val expiry: String = "", val ticks: Long = 0, val connected: Boolean = false
)
internal class ScannerController(context: Context, private val render: (ScannerState) -> Unit) {
    private val app = context.applicationContext
    private val vault = Vault(app)
    private val api = AngelApi()
    private val prefs = app.getSharedPreferences("scanner", Context.MODE_PRIVATE)
    private val io = Executors.newSingleThreadExecutor()
    private val main = Handler(Looper.getMainLooper())
    private var closed = false
    private var foreground = true
    private var sessionCheckAt = 0L
    private var historySave: Runnable? = null
    private var generation = 0
    private var pending = false
    private var state = ScannerState(
        targets = (0..5).map { prefs.getString("NIFTY_target_$it", prefs.getString("target_$it", "")) ?: "" },
        digit1 = prefs.getString("NIFTY_digit1", prefs.getString("digit1", "6")) ?: "6",
        digit2 = prefs.getString("NIFTY_digit2", prefs.getString("digit2", "9")) ?: "9",
        history = readHistory()
    )
    private var credentials: Credentials? = null
    private var session: LoginSession? = null
    private var socket: LiveSocket? = null
    private var instruments = emptyList<Instrument>()
    private var markets = emptyList<Pair<String, Instrument?>>()
    private var selected = emptyList<Instrument>()
    private val latest = HashMap<String, Tick>()
    private val signalKeys = state.history.map { it.key }.toMutableSet()
    private val candleCache = HashMap<String, List<Candle>>()
    private var candleRevision = 0L
    private var historicalSignature = ""
    private var cachedHistorical = emptyList<Signal>()
    private val candlePending = HashSet<String>()
    private val candleAttempted = HashSet<String>()
    private val candleFetchedAt = HashMap<String, Long>()
    private val sessionDays = HashMap<String, LocalDate>()
    private val confirmedDays = HashMap<String, LocalDate>()
    private val settings = HashMap<String, Triple<String, String, List<String>>>()
    private val expirySettings = HashMap<String, String>()
    private var spot: BigDecimal? = null
    private val seeded = HashSet<String>()
    private val clock = object : Runnable {
        override fun run() {
            synchronized(this@ScannerController) {
                if (closed || !foreground) return
                if (state.loggedIn && session?.let { Instant.now().epochSecond >= it.expires } == true) {
                    invalidate("Session expired · enter a new authenticator code")
                } else {
                    if (state.loggedIn && instruments.isNotEmpty() && System.currentTimeMillis() - sessionCheckAt > 60000) {
                        sessionCheckAt = System.currentTimeMillis(); loadSessionDays()
                    }
                    publish()
                }
            }
            main.postDelayed(this, 1000)
        }
    }
    init {
        main.post(clock)
        io.execute {
            runCatching {
                credentials = vault.credentials()
                val saved = vault.session()
                synchronized(this) { state = state.copy(configured = credentials != null) }
                if (credentials != null && saved != null &&
                    SessionPolicy.canResume(BrokerSession(Instant.ofEpochSecond(saved.authenticated), Instant.ofEpochSecond(saved.expires)), Instant.now())) {
                    try { api.validate(credentials!!, saved) }
                    catch (e: BrokerError) {
                        if (!e.loginRequired) throw e
                        vault.clearSession()
                        synchronized(this) { state = state.copy(checking = false, status = e.message.orEmpty()); publish() }
                        return@execute
                    }
                    session = saved
                    synchronized(this) { state = state.copy(checking = false, loggedIn = true, status = "Loading instruments…"); publish() }
                    loadFeed()
                } else {
                    vault.clearSession()
                    synchronized(this) { state = state.copy(checking = false, status = "Enter your Angel One authenticator code"); publish() }
                }
            }.onFailure { error ->
                synchronized(this) { state = state.copy(checking = false, busy = false, status = safeError(error)); publish() }
            }
        }
    }
    private fun safeError(error: Throwable): String = if (error is BrokerError) error.message.orEmpty()
        else "Connection unavailable. Check internet and retry."
    @Synchronized fun saveSetup(apiKey: String, clientId: String, pin: String) {
        if (apiKey.isBlank() || clientId.isBlank() || pin.isBlank()) {
            state = state.copy(status = "API key, client ID and PIN are required."); publish(); return
        }
        val next = Credentials(apiKey.trim(), clientId.trim(), pin.trim())
        state = state.copy(busy = true, status = "Saving account setup…"); publish()
        io.execute {
            runCatching { vault.save(next) }.onSuccess {
                synchronized(this) { credentials = next; state = state.copy(configured = true, busy = false, status = "Setup saved · enter authenticator code"); publish() }
            }.onFailure { synchronized(this) { state = state.copy(busy = false, status = "Secure storage unavailable. Setup was not saved."); publish() } }
        }
    }
    @Synchronized fun login(otp: String) {
        if (state.busy) return
        if (!otp.matches(Regex("[0-9]{6}"))) { state = state.copy(status = "Enter the current six-digit authenticator code."); publish(); return }
        val c = credentials ?: return
        val attempt = ++generation
        state = state.copy(busy = true, status = "Signing in…"); publish()
        io.execute {
            runCatching {
                val s = api.login(c, otp)
                synchronized(this) {
                    if (attempt != generation || closed) return@execute
                    vault.save(s); session = s
                    state = state.copy(loggedIn = true, busy = false, status = "Loading instruments…")
                    publish()
                }
                loadFeed()
            }.onFailure { error ->
                synchronized(this) { if (attempt == generation) { state = state.copy(busy = false, status = safeError(error)); publish() } }
            }
        }
    }
    private fun loadFeed() {
        runCatching {
            val master = api.master(app)
            synchronized(this) {
                if (closed || !state.loggedIn) return
                instruments = master
                fun spot(aliases: Set<String>, exchange: String) = master.firstOrNull {
                    it.exchange == exchange && (it.name in aliases || it.symbol in aliases)
                }
                fun future(name: String, exchange: String) = master.filter {
                    it.name == name && it.exchange == exchange && it.kind == "FUTIDX" && it.expiry != null
                }.minByOrNull { it.expiry!! }
                markets = listOf(
                    "NIFTY" to spot(setOf("NIFTY", "NIFTY 50", "NIFTY50"), "NSE"),
                    "NIFTY FUT" to future("NIFTY", "NFO"),
                    "SENSEX" to spot(setOf("SENSEX", "BSE SENSEX"), "BSE"),
                    "SENSEX FUT" to future("SENSEX", "BFO")
                )
                val expiries = master.filter { it.name == state.index && it.kind == "OPTIDX" && it.exchange == exchange(state.index) }
                    .mapNotNull { it.expiry?.toString() }.distinct().sorted()
                state = state.copy(expiries = expiries,
                    expiry = state.expiry.takeIf { it in expiries } ?: expiries.firstOrNull().orEmpty())
                prefs.edit().putString("${state.index}_expiry", state.expiry).apply()
                startSocket()
            }
        }.onFailure { error ->
            synchronized(this) { state = state.copy(busy = false, status = safeError(error)); publish() }
        }
    }
    @Synchronized private fun startSocket() {
        socket?.close(); socket = null
        if (!foreground || closed || !state.loggedIn) return
        val c = credentials ?: return
        val s = session ?: return
        val feedGeneration = ++generation
        state = state.copy(status = "Connecting live feed…", connected = false)
        socket = LiveSocket(api, c, s, { tick ->
            synchronized(this) { if (feedGeneration == generation) accept(tick) }
        }, { status, invalid ->
            synchronized(this) {
                if (feedGeneration != generation) return@synchronized
                if (invalid) invalidate(status)
                else {
                    state = state.copy(status = status, connected = status.startsWith("Feed connected"))
                    publish()
                }
            }
        })
        selectContracts()
        socket?.connect()
        seedQuotes(markets.mapNotNull { it.second })
        loadSessionDays()
        publish()
    }
    @Synchronized private fun accept(tick: Tick, streamed: Boolean = true) {
        if (!state.loggedIn || closed) return
        if (session?.let { Instant.now().epochSecond >= it.expires } != false) {
            invalidate("Session expired · log in again"); return
        }
        val old = latest[tick.key]
        if (old != null && tick.exchangeMillis < old.exchangeMillis) return
        latest[tick.key] = tick
        if (streamed) state = state.copy(ticks = state.ticks + 1, connected = true, status = "Live feed connected")
        if (markets.any { it.second?.key == tick.key } && tick.ltp != null) {
            spot = tick.ltp
            selectContracts()
        }
        val item = selected.firstOrNull { it.key == tick.key }
        if (streamed && item != null && fresh(tick)) {
            val quote = Quote(item.contract(), tick.open, tick.ltp, LocalDate.now(IST).toString())
            val stamp = Instant.ofEpochMilli(tick.exchangeMillis).atZone(IST).format(DateTimeFormatter.ISO_OFFSET_DATE_TIME)
            val added = config(item.name).third.mapIndexedNotNull { index, input ->
                val target = input.toBigDecimalOrNull() ?: return@mapIndexedNotNull null
                Rules.signal(quote, target, if (index < 4) Direction.BUY else Direction.SELL_SHORT, stamp)
                    ?.takeIf { signalKeys.add(it.key) }
            }
            if (added.isNotEmpty()) {
                state = state.copy(history = SignalRecords.merge(state.history + added))
                val history = state.history
                io.execute { writeHistory(history) }
            }
        }
        publish()
    }
    private fun fresh(t: Tick): Boolean {
        val now = System.currentTimeMillis()
        return now - t.exchangeMillis in 0..15000 &&
            Instant.ofEpochMilli(t.exchangeMillis).atZone(IST).toLocalDate() == LocalDate.now(IST)
    }
    @Synchronized private fun selectContracts() {
        val expiryByIndex = listOf("NIFTY", "SENSEX").associateWith { expiryFor(it) }
        val options = instruments.filter {
            it.name in setOf("NIFTY", "SENSEX") && it.exchange == exchange(it.name) && it.kind == "OPTIDX" &&
                it.expiry?.toString() == expiryByIndex[it.name] && it.strike > 0 &&
                (it.symbol.endsWith("CE") || it.symbol.endsWith("PE"))
        }
        val paired = options.groupBy { it.name to it.strike }.filterValues { list ->
            list.any { it.symbol.endsWith("CE") } && list.any { it.symbol.endsWith("PE") }
        }.keys
        val strikes = listOf("NIFTY", "SENSEX").associateWith { index ->
            val price = markets.firstOrNull { it.first == index }?.second?.let { latest[it.key]?.ltp }
            val config = config(index)
            if (price == null) emptySet() else listOf(config.first, config.second).flatMap { digit ->
                digit.toIntOrNull()?.let { Rules.nearby(paired.filter { pair -> pair.first == index }.map { pair -> pair.second }, it, price) } ?: emptyList()
            }.toSet()
        }
        selected = options.filter { it.strike in strikes[it.name].orEmpty() }.distinctBy { it.key }
            .sortedWith(compareBy({ it.name }, { it.strike }, { it.symbol }))
        socket?.subscribe(markets.mapNotNull { it.second } + selected)
        seedQuotes(selected)
        loadHistoryCandles()
    }
    @Synchronized private fun seedQuotes(items: List<Instrument>) {
        val missing = items.filter { it.key !in latest && seeded.add(it.key) }
        if (missing.isEmpty()) return
        val c = credentials ?: return
        val s = session ?: return
        val attempt = generation
        io.execute {
            runCatching { api.snapshot(c, s, missing) }.onSuccess { ticks ->
                synchronized(this) { if (attempt == generation) ticks.forEach { accept(it, false) } }
            }.onFailure { error ->
                synchronized(this) {
                    missing.forEach { seeded.remove(it.key) }
                    if (attempt == generation && error is BrokerError && error.loginRequired) invalidate(error.message.orEmpty())
                }
            }
        }
    }
    @Synchronized fun target(index: Int, text: String) {
        if (index !in 0..5 || !text.matches(Regex("[0-9]*\\.?[0-9]{0,2}")) || text.length > 12) return
        state = state.copy(targets = state.targets.toMutableList().apply { this[index] = text })
        prefs.edit().putString("${state.index}_target_$index", text).apply()
        rememberConfig(); loadHistoryCandles(); rescan()
        publish()
    }
    @Synchronized fun digit(index: Int, value: String) {
        if (value.isNotEmpty() && (value.length != 1 || value[0] !in '1'..'9')) return
        state = if (index == 0) state.copy(digit1 = value) else state.copy(digit2 = value)
        prefs.edit().putString("${state.index}_" + if (index == 0) "digit1" else "digit2", value).apply()
        rememberConfig()
        selectContracts(); rescan(); publish()
    }
    @Synchronized fun expiry(value: String) {
        if (value !in state.expiries) return
        state = state.copy(expiry = value); expirySettings[state.index] = value
        prefs.edit().putString("${state.index}_expiry", value).apply(); selectContracts(); rescan(); publish()
    }
    private fun exchange(index: String) = if (index == "SENSEX") "BFO" else "NFO"
    private fun config(index: String): Triple<String, String, List<String>> {
        if (index == state.index) return Triple(state.digit1, state.digit2, state.targets)
        return settings.getOrPut(index) { Triple(prefs.getString("${index}_digit1", "6") ?: "6",
            prefs.getString("${index}_digit2", "9") ?: "9",
            (0..5).map { prefs.getString("${index}_target_$it", "") ?: "" }) }
    }
    private fun rememberConfig() { settings[state.index] = Triple(state.digit1, state.digit2, state.targets) }
    private fun expiryFor(index: String): String {
        val available = instruments.filter { it.name == index && it.exchange == exchange(index) && it.kind == "OPTIDX" }
            .mapNotNull { it.expiry?.toString() }.distinct().sorted()
        val saved = if (index == state.index) state.expiry else expirySettings[index] ?: prefs.getString("${index}_expiry", "")
        return saved?.takeIf { it in available } ?: available.firstOrNull().orEmpty()
    }
    @Synchronized fun switchIndex(index: String) {
        if (index !in setOf("NIFTY", "SENSEX") || index == state.index) return
        rememberConfig(); expirySettings[state.index] = state.expiry
        val next = config(index)
        val expiry = expiryFor(index)
        val expiries = instruments.filter { it.name == index && it.exchange == exchange(index) && it.kind == "OPTIDX" }
            .mapNotNull { it.expiry?.toString() }.distinct().sorted()
        state = state.copy(index = index, digit1 = next.first, digit2 = next.second, targets = next.third,
            expiry = expiry, expiries = expiries)
        selectContracts(); rescan(); publish()
    }
    private fun scanDay(index: String): LocalDate? {
        val tick = markets.firstOrNull { it.first == index }?.second?.let { latest[it.key] }
        // A current-day feed confirms today's session. A stale/holiday feed uses the last completed session.
        val today = LocalDate.now(IST)
        if (tick != null && fresh(tick)) confirmedDays[index] = today
        return confirmedDays[index]?.takeIf { it == today } ?: sessionDays[index]
    }
    private fun historicalMatches(): List<Signal> {
        val day = scanDay(state.index) ?: return emptyList()
        val items = selected.filter { it.name == state.index }
        val signature = listOf(state.index, day, state.targets, items.map { it.key }, candleRevision).joinToString("|")
        if (signature == historicalSignature) return cachedHistorical
        historicalSignature = signature
        cachedHistorical = items.flatMap { item ->
            val bars = candleCache["${item.key}|$day"] ?: return@flatMap emptyList()
            state.targets.flatMapIndexed { i, input -> input.toBigDecimalOrNull()?.let {
                HistoricalScan.scan(item.contract(), bars, it, if (i < 4) Direction.BUY else Direction.SELL_SHORT)
            } ?: emptyList() }
        }.distinctBy { it.key }.sortedBy { it.time }
        return cachedHistorical
    }
    private fun rescan() {
        state = state.copy(historical = historicalMatches())
        historySave?.let { main.removeCallbacks(it) }
        val save = Runnable { synchronized(this) {
            if (!closed) {
                val merged = SignalRecords.merge(state.history + historicalMatches())
                if (merged != state.history) {
                    state = state.copy(history = merged)
                    signalKeys.clear(); signalKeys.addAll(merged.map { it.key })
                    val snapshot = state.history
                    io.execute { writeHistory(snapshot) }
                }
                publish()
            }
        } }
        historySave = save; main.postDelayed(save, 800)
        publish()
    }
    private fun loadSessionDays() {
        val c = credentials ?: return
        val s = session ?: return
        val attempt = generation
        val spots = markets.filter { it.first in setOf("NIFTY", "SENSEX") }.mapNotNull { it.second }
        io.execute {
            spots.forEach { item ->
                runCatching {
                    val now = ZonedDateTime.now(IST)
                    // Daily candles decide actual trading dates, including holidays.
                    val end = if (now.toLocalTime() < LocalTime.of(15, 30)) now.toLocalDate().minusDays(1) else now.toLocalDate()
                    Thread.sleep(400)
                    val bars = api.candles(c, s, item, end.minusDays(20), end, "ONE_DAY")
                    val day = bars.filter { Instant.ofEpochMilli(it.millis).atZone(IST).toLocalDate() <= end }.lastOrNull()?.let { Instant.ofEpochMilli(it.millis).atZone(IST).toLocalDate() }
                        ?: throw BrokerError("No completed session data for ${item.name}.")
                    synchronized(this) { if (attempt == generation && !closed) {
                        sessionDays[if (item.exchange == "BSE") "SENSEX" else "NIFTY"] = day
                        loadHistoryCandles(); publish()
                    } }
                }.onFailure { e -> synchronized(this) { if (attempt == generation) {
                    state = state.copy(scanStatus = "Historical data unavailable: ${safeError(e)}"); publish()
                } } }
            }
        }
    }
    @Synchronized private fun loadHistoryCandles() {
        val c = credentials ?: return
        val s = session ?: return
        val attempt = generation
        selected.forEach { item ->
            val day = scanDay(item.name) ?: return@forEach
            val key = "${item.key}|$day"
            val currentDay = day == LocalDate.now(IST)
            if (key in candlePending) return@forEach
            if (currentDay) {
                // Refresh current-session backfill without freezing it at the first digit selection.
                if (System.currentTimeMillis() - (candleFetchedAt[key] ?: 0L) < 60000) return@forEach
            } else if (key in candleCache || key in candleAttempted) return@forEach
            candleAttempted.add(key); candlePending.add(key)
            candleFetchedAt[key] = System.currentTimeMillis()
            state = state.copy(scanStatus = "Loading session · $day · first matches from one-minute data…")
            io.execute {
                val file = java.io.File(app.cacheDir, "candles-${item.exchangeType}-${item.token}-$day.json")
                runCatching {
                    val bars = if (!currentDay && file.exists()) {
                        val rows = JSONArray(file.readText())
                        (0 until rows.length()).map { i -> val r = rows.getJSONArray(i)
                            Candle(r.getLong(0), r.getString(1).toBigDecimal(), r.getString(2).toBigDecimal(), r.getString(3).toBigDecimal(), r.getString(4).toBigDecimal()) }
                    } else {
                        Thread.sleep(400)
                        api.candles(c, s, item, day, day).also { rows ->
                            if (!currentDay && rows.isNotEmpty()) file.writeText(JSONArray().apply { rows.forEach {
                                put(JSONArray(listOf(it.millis, it.open.toPlainString(), it.high.toPlainString(), it.low.toPlainString(), it.close.toPlainString())))
                            } }.toString())
                        }
                    }
                    if (bars.isEmpty()) throw BrokerError("No candles returned for ${item.symbol} on $day")
                    synchronized(this) { if (attempt == generation && !closed) {
                        candleCache[key] = bars; candleRevision++
                        state = state.copy(scanStatus = "Session $day · first one-minute OHLC matches · exact tick time unavailable")
                        rescan()
                    } }
                }.onFailure { error -> synchronized(this) { if (attempt == generation) {
                    state = state.copy(scanStatus = "Historical data incomplete: ${safeError(error)}"); publish()
                } } }
                synchronized(this) {
                    candlePending.remove(key)
                    if (attempt != generation) { candleAttempted.remove(key); candleFetchedAt.remove(key) }
                }
            }
        }
    }
    @Synchronized fun reconnect() {
        if (!state.loggedIn) { state = state.copy(checking = false); publish(); return }
        candleAttempted.clear(); candleFetchedAt.clear()
        if (instruments.isEmpty()) io.execute { loadFeed() } else startSocket()
    }
    @Synchronized private fun invalidate(message: String) {
        generation++; socket?.close(); socket = null; session = null; latest.clear(); seeded.clear(); spot = null
        vault.clearSession()
        state = state.copy(loggedIn = false, busy = false, connected = false, quotes = emptyList(), status = message)
        publish()
    }
    @Synchronized fun logout() {
        val c = credentials; val s = session
        invalidate("Logged out · enter authenticator code")
        if (c != null && s != null) io.execute { runCatching { api.logout(c, s) } }
    }
    @Synchronized fun accountSetup() {
        if (state.loggedIn) return
        state = state.copy(configured = false, status = "Set up your Angel One account"); publish()
    }
    @Synchronized fun foreground(value: Boolean) {
        foreground = value
        if (!value) {
            if (socket != null) generation++
            socket?.close(); socket = null
            main.removeCallbacks(clock)
            state = state.copy(connected = false)
        } else {
            main.removeCallbacks(clock); main.post(clock)
            if (state.loggedIn && instruments.isNotEmpty()) startSocket()
        }
    }
    @Synchronized private fun publish() {
        if (pending || closed) return
        pending = true
        main.postDelayed({
            synchronized(this) {
                pending = false
                if (closed) return@synchronized
                state = state.copy(
                    markets = markets.map { (label, item) -> label to item?.let { latest[it.key] } },
                    quotes = selected.filter { it.name == state.index }.map { item ->
                        val tick = latest[item.key] ?: Tick(item.key, null, null, 0L, 0L)
                        Quote(item.contract(), tick.open, tick.ltp,
                            Instant.ofEpochMilli(tick.exchangeMillis).atZone(IST).toLocalDate().toString()) to tick
                    },
                    historical = historicalMatches(),
                    sessionDate = scanDay(state.index)?.toString().orEmpty()
                )
                render(state)
            }
        }, 50)
    }
    @Synchronized fun close() {
        closed = true; generation++; socket?.close(); main.removeCallbacksAndMessages(null); io.shutdown()
    }
    private fun readHistory(): List<Signal> = runCatching {
        val a = JSONArray(prefs.getString("locked_v2", "[]"))
        SignalRecords.merge((0 until a.length()).map { index ->
            val s = a.getJSONObject(index)
            Signal(s.getString("key"), Contract(s.getString("token"), s.getInt("strike"), s.getString("side"), s.getString("expiry")),
                Direction.valueOf(s.getString("direction")), s.getString("target").toBigDecimal(),
                s.getString("price").toBigDecimal(), s.getString("open").toBigDecimal(), s.getString("time"), s.getString("day"), s.optBoolean("historical"))
        })
    }.getOrDefault(emptyList())
    private fun writeHistory(history: List<Signal>) {
        val array = JSONArray()
        history.forEach { s ->
            array.put(JSONObject().put("key", s.key).put("token", s.contract.token).put("strike", s.contract.strike)
                .put("side", s.contract.side).put("expiry", s.contract.expiry).put("direction", s.direction.name)
                .put("target", s.target.toPlainString()).put("price", s.matchedPrice.toPlainString())
                .put("open", s.openingPrice.toPlainString()).put("time", s.time).put("day", s.sessionDate).put("historical", s.historical))
        }
        prefs.edit().putString("locked_v2", array.toString()).commit()
    }
}
