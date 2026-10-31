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
    val checking: Boolean = true, val loggedIn: Boolean = false, val configured: Boolean = false,
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
    private var generation = 0
    private var pending = false
    private var state = ScannerState(
        targets = (0..5).map { prefs.getString("target_$it", "") ?: "" },
        digit1 = prefs.getString("digit1", "6") ?: "6",
        digit2 = prefs.getString("digit2", "9") ?: "9",
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
    private var spot: BigDecimal? = null
    private val seeded = HashSet<String>()
    private val clock = object : Runnable {
        override fun run() {
            synchronized(this@ScannerController) {
                if (closed || !foreground) return
                if (state.loggedIn && session?.let { Instant.now().epochSecond >= it.expires } == true) {
                    invalidate("Session expired · enter a new authenticator code")
                } else publish()
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
                val expiries = master.filter { it.name == "NIFTY" && it.kind == "OPTIDX" && it.exchange == "NFO" }
                    .mapNotNull { it.expiry?.toString() }.distinct().sorted()
                state = state.copy(expiries = expiries,
                    expiry = state.expiry.takeIf { it in expiries } ?: expiries.firstOrNull().orEmpty())
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
        if (tick.key == markets.firstOrNull()?.second?.key && tick.ltp != null) {
            spot = tick.ltp
            selectContracts()
        }
        val item = selected.firstOrNull { it.key == tick.key }
        if (streamed && item != null && fresh(tick)) {
            val quote = Quote(item.contract(), tick.open, tick.ltp, LocalDate.now(IST).toString())
            val stamp = Instant.ofEpochMilli(tick.exchangeMillis).atZone(IST).format(DateTimeFormatter.ISO_OFFSET_DATE_TIME)
            val added = state.targets.mapIndexedNotNull { index, input ->
                val target = input.toBigDecimalOrNull() ?: return@mapIndexedNotNull null
                Rules.signal(quote, target, if (index < 4) Direction.BUY else Direction.SELL_SHORT, stamp)
                    ?.takeIf { signalKeys.add(it.key) }
            }
            if (added.isNotEmpty()) {
                state = state.copy(history = state.history + added)
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
        val options = instruments.filter {
            it.name == "NIFTY" && it.exchange == "NFO" && it.kind == "OPTIDX" &&
                it.expiry?.toString() == state.expiry && it.strike > 0 &&
                (it.symbol.endsWith("CE") || it.symbol.endsWith("PE"))
        }
        val available = options.groupBy { it.strike }.filterValues { list ->
            list.any { it.symbol.endsWith("CE") } && list.any { it.symbol.endsWith("PE") }
        }.keys.toList()
        val price = spot
        val strikes = if (price == null) emptySet() else
            listOf(state.digit1, state.digit2).flatMap { d ->
                d.toIntOrNull()?.let { Rules.nearby(available, it, price) } ?: emptyList()
            }.toSet()
        selected = options.filter { it.strike in strikes }.distinctBy { it.key }.sortedWith(compareBy({ it.strike }, { it.symbol }))
        socket?.subscribe(markets.mapNotNull { it.second } + selected)
        seedQuotes(selected)
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
        prefs.edit().putString("target_$index", text).apply()
        publish()
    }
    @Synchronized fun digit(index: Int, value: String) {
        if (value.isNotEmpty() && (value.length != 1 || value[0] !in '1'..'9')) return
        state = if (index == 0) state.copy(digit1 = value) else state.copy(digit2 = value)
        prefs.edit().putString(if (index == 0) "digit1" else "digit2", value).apply()
        selectContracts(); publish()
    }
    @Synchronized fun expiry(value: String) {
        if (value !in state.expiries) return
        state = state.copy(expiry = value); selectContracts(); publish()
    }
    @Synchronized fun reconnect() {
        if (!state.loggedIn) { state = state.copy(checking = false); publish(); return }
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
                    quotes = selected.mapNotNull { item ->
                        latest[item.key]?.let { tick ->
                            Quote(item.contract(), tick.open, tick.ltp,
                                Instant.ofEpochMilli(tick.exchangeMillis).atZone(IST).toLocalDate().toString()) to tick
                        }
                    }
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
        (0 until a.length()).map { index ->
            val s = a.getJSONObject(index)
            Signal(s.getString("key"), Contract(s.getString("token"), s.getInt("strike"), s.getString("side"), s.getString("expiry")),
                Direction.valueOf(s.getString("direction")), s.getString("target").toBigDecimal(),
                s.getString("price").toBigDecimal(), s.getString("open").toBigDecimal(), s.getString("time"), s.getString("day"))
        }
    }.getOrDefault(emptyList())
    private fun writeHistory(history: List<Signal>) {
        val array = JSONArray()
        history.forEach { s ->
            array.put(JSONObject().put("key", s.key).put("token", s.contract.token).put("strike", s.contract.strike)
                .put("side", s.contract.side).put("expiry", s.contract.expiry).put("direction", s.direction.name)
                .put("target", s.target.toPlainString()).put("price", s.matchedPrice.toPlainString())
                .put("open", s.openingPrice.toPlainString()).put("time", s.time).put("day", s.sessionDate))
        }
        prefs.edit().putString("locked_v2", array.toString()).commit()
    }
}
