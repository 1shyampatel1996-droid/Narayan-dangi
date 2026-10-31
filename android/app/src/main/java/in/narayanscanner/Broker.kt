package `in`.narayanscanner

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import android.util.JsonReader
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import okio.ByteString
import org.json.JSONArray
import org.json.JSONObject
import java.math.BigDecimal
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.security.KeyStore
import java.time.*
import java.time.format.DateTimeFormatter
import java.util.Locale
import java.util.concurrent.TimeUnit
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

internal val IST: ZoneId = ZoneId.of("Asia/Kolkata")
internal data class Credentials(val apiKey: String, val clientId: String, val pin: String)
internal data class LoginSession(val jwt: String, val feed: String, val authenticated: Long, val expires: Long)
internal class BrokerError(message: String, val loginRequired: Boolean = false) : Exception(message)
internal class Vault(context: Context) {
    private val prefs = context.getSharedPreferences("encrypted_broker", Context.MODE_PRIVATE)
    private fun key(): SecretKey {
        val ks = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        (ks.getKey("narayan_session_v1", null) as? SecretKey)?.let { return it }
        return KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore").apply {
            init(KeyGenParameterSpec.Builder("narayan_session_v1",
                KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE).build())
        }.generateKey()
    }
    @Synchronized fun put(name: String, json: JSONObject) {
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.ENCRYPT_MODE, key())
        val ciphertext = cipher.doFinal(json.toString().toByteArray(Charsets.UTF_8))
        prefs.edit().putString(name, Base64.encodeToString(cipher.iv + ciphertext, Base64.NO_WRAP)).commit()
    }
    @Synchronized fun get(name: String): JSONObject? = runCatching {
        val bytes = Base64.decode(prefs.getString(name, null) ?: return null, Base64.NO_WRAP)
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.DECRYPT_MODE, key(), GCMParameterSpec(128, bytes.copyOfRange(0, 12)))
        JSONObject(String(cipher.doFinal(bytes.copyOfRange(12, bytes.size)), Charsets.UTF_8))
    }.getOrNull()
    fun credentials(): Credentials? = get("credentials")?.let {
        Credentials(it.getString("api"), it.getString("client"), it.getString("pin"))
    }
    fun save(c: Credentials) = put("credentials", JSONObject().put("api", c.apiKey).put("client", c.clientId).put("pin", c.pin))
    fun session(): LoginSession? = get("session")?.let {
        runCatching { LoginSession(it.getString("jwt"), it.getString("feed"), it.getLong("at"), it.getLong("expires")) }.getOrNull()
    }
    fun save(s: LoginSession) = put("session", JSONObject().put("jwt", s.jwt).put("feed", s.feed).put("at", s.authenticated).put("expires", s.expires))
    fun clearSession() { prefs.edit().remove("session").commit() }
}
internal data class Instrument(
    val token: String, val symbol: String, val name: String, val exchange: String,
    val kind: String, val expiry: LocalDate?, val strike: Int
) {
    val exchangeType get() = mapOf("NSE" to 1, "NFO" to 2, "BSE" to 3, "BFO" to 4).getValue(exchange)
    val key get() = "$exchangeType:$token"
    fun contract() = Contract(key, strike, if (symbol.endsWith("CE")) "CALL" else "PUT", expiry.toString())
}
internal data class Tick(val key: String, val open: BigDecimal?, val ltp: BigDecimal?, val exchangeMillis: Long, val received: Long)
internal object TickDecoder {
    fun decode(bytes: ByteArray): Tick? {
        if (bytes.size < 123 || bytes[0].toInt() !in 2..3) return null
        val b = ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN)
        val exchange = bytes[1].toInt() and 255
        if (exchange !in 1..4) return null
        val token = String(bytes.copyOfRange(2, 27), Charsets.US_ASCII).substringBefore('\u0000')
        if (token.isBlank()) return null
        fun price(offset: Int) = b.getLong(offset).takeIf { it > 0 }?.let { BigDecimal.valueOf(it, 2) }
        val stamp = b.getLong(35)
        if (stamp <= 0) return null
        return Tick("$exchange:$token", price(91), price(43), stamp, System.currentTimeMillis())
    }
}
internal class AngelApi {
    val http = OkHttpClient.Builder().connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS).build()
    private fun request(c: Credentials, path: String, session: LoginSession? = null, body: JSONObject? = null): JSONObject {
        val builder = Request.Builder().url("https://apiconnect.angelone.in" + path)
            .header("X-PrivateKey", c.apiKey).header("X-UserType", "USER").header("X-SourceID", "WEB")
            .header("X-ClientLocalIP", "127.0.0.1").header("X-ClientPublicIP", "0.0.0.0")
            .header("X-MACAddress", "02:00:00:00:00:00").header("Accept", "application/json")
        session?.let { builder.header("Authorization", "Bearer " + it.jwt.removePrefix("Bearer ")) }
        body?.let { builder.post(it.toString().toRequestBody("application/json".toMediaType())) }
        http.newCall(builder.build()).execute().use { response ->
            if (response.code == 401 || response.code == 403) throw BrokerError("Session rejected. Please log in again.", true)
            if (response.code == 429) throw BrokerError("Broker rate limit. Please wait before retrying.")
            if (!response.isSuccessful) throw BrokerError("Broker connection failed (HTTP ${response.code}).")
            val json = JSONObject(response.body?.string() ?: throw BrokerError("Empty broker response."))
            if (!json.optBoolean("status")) {
                val code = json.optString("errorcode")
                throw BrokerError("Broker rejected request (${code.ifBlank { "unknown" }}). Check account setup or OTP.",
                    code in setOf("AG8001", "AG8002", "AG8003", "AB1010"))
            }
            return json.getJSONObject("data")
        }
    }
    fun login(c: Credentials, otp: String): LoginSession {
        val data = request(c, "/rest/auth/angelbroking/user/v1/loginByPassword",
            body = JSONObject().put("clientcode", c.clientId).put("password", c.pin).put("totp", otp))
        val jwt = data.getString("jwtToken")
        val now = Instant.now()
        val midnight = LocalDate.now(IST).plusDays(1).atStartOfDay(IST).toInstant().epochSecond
        val expiry = runCatching {
            JSONObject(String(Base64.decode(jwt.removePrefix("Bearer ").split(".")[1],
                Base64.URL_SAFE or Base64.NO_WRAP), Charsets.UTF_8)).getLong("exp")
        }.getOrDefault(midnight)
        return LoginSession(jwt, data.getString("feedToken"), now.epochSecond, minOf(midnight, expiry))
    }
    fun validate(c: Credentials, s: LoginSession) { request(c, "/rest/secure/angelbroking/user/v1/getProfile", s) }
    fun snapshot(c: Credentials, s: LoginSession, instruments: List<Instrument>): List<Tick> {
        if (instruments.isEmpty()) return emptyList()
        val tokens = JSONObject()
        instruments.groupBy { it.exchange }.forEach { (exchange, items) ->
            tokens.put(exchange, JSONArray(items.map { it.token }.distinct()))
        }
        val data = request(c, "/rest/secure/angelbroking/market/v1/quote/", s,
            JSONObject().put("mode", "FULL").put("exchangeTokens", tokens))
        val fetched = data.optJSONArray("fetched") ?: return emptyList()
        val dateFormat = java.time.format.DateTimeFormatterBuilder().parseCaseInsensitive()
            .appendPattern("dd-MMM-yyyy HH:mm:ss").toFormatter(Locale.ENGLISH)
        return (0 until fetched.length()).mapNotNull { index ->
            val item = fetched.getJSONObject(index)
            val instrument = instruments.firstOrNull {
                it.exchange == item.optString("exchange") && it.token == item.optString("symbolToken")
            } ?: return@mapNotNull null
            fun price(name: String) = item.optString(name).toBigDecimalOrNull()?.takeIf { it.signum() > 0 }
            val timestamp = runCatching {
                LocalDateTime.parse(item.optString("exchFeedTime"), dateFormat).atZone(IST).toInstant().toEpochMilli()
            }.getOrDefault(0L)
            Tick(instrument.key, price("open"), price("ltp"), timestamp, System.currentTimeMillis())
        }
    }
    fun logout(c: Credentials, s: LoginSession) {
        request(c, "/rest/secure/angelbroking/user/v1/logout", s, JSONObject().put("clientcode", c.clientId))
    }
    fun master(context: Context): List<Instrument> {
        val today = LocalDate.now(IST)
        val file = java.io.File(context.cacheDir, "instrument-$today.json")
        if (!file.exists()) {
            val tmp = java.io.File(context.cacheDir, "master-download.tmp")
            try {
                http.newCall(Request.Builder().url(
                    "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json").build())
                    .execute().use { response ->
                        if (!response.isSuccessful) throw BrokerError("Instrument list download failed.")
                        val body = response.body ?: throw BrokerError("Empty instrument list.")
                        tmp.outputStream().use { output -> body.byteStream().use { it.copyTo(output) } }
                    }
                if (!tmp.renameTo(file)) throw BrokerError("Unable to cache instruments.")
            } finally { tmp.delete() }
        }
        val result = mutableListOf<Instrument>()
        val fmt = java.time.format.DateTimeFormatterBuilder().parseCaseInsensitive()
            .appendPattern("ddMMMyyyy").toFormatter(Locale.ENGLISH)
        JsonReader(file.reader()).use { reader ->
            reader.beginArray()
            while (reader.hasNext()) {
                val row = HashMap<String, String>()
                reader.beginObject()
                while (reader.hasNext()) {
                    val name = reader.nextName()
                    if (reader.peek() == android.util.JsonToken.NULL) reader.nextNull()
                    else if (name in setOf("token","symbol","name","exch_seg","instrumenttype","expiry","strike")) row[name] = reader.nextString()
                    else reader.skipValue()
                }
                reader.endObject()
                val name = row["name"].orEmpty().uppercase()
                val symbol = row["symbol"].orEmpty().uppercase()
                val exchange = row["exch_seg"].orEmpty()
                if (exchange !in setOf("NSE", "NFO", "BSE", "BFO")) continue
                if (name !in setOf("NIFTY", "NIFTY 50", "NIFTY50", "SENSEX", "BSE SENSEX") &&
                    symbol !in setOf("NIFTY", "NIFTY 50", "NIFTY50", "SENSEX", "BSE SENSEX")) continue
                val expiry = runCatching { LocalDate.parse(row["expiry"].orEmpty().uppercase(), fmt) }.getOrNull()
                if (expiry != null && expiry < today) continue
                result.add(Instrument(row["token"].orEmpty(), symbol, name, exchange,
                    row["instrumenttype"].orEmpty(), expiry,
                    row["strike"]?.toBigDecimalOrNull()?.divide(BigDecimal("100"))?.toInt() ?: 0))
            }
            reader.endArray()
        }
        if (result.isEmpty()) { file.delete(); throw BrokerError("No scanner instruments found.") }
        return result
    }
}
internal class LiveSocket(
    private val api: AngelApi, private val credentials: Credentials, private val session: LoginSession,
    private val onTick: (Tick) -> Unit, private val onStatus: (String, Boolean) -> Unit
) {
    private val handler = android.os.Handler(android.os.Looper.getMainLooper())
    private var socket: WebSocket? = null
    private var stopped = false
    private var opened = false
    private var retries = 0
    private var wanted = emptyList<Instrument>()
    private val heartbeat = object : Runnable {
        override fun run() {
            if (!stopped && opened) { socket?.send("ping"); handler.postDelayed(this, 25000) }
        }
    }
    @Synchronized fun subscribe(instruments: List<Instrument>) {
        val next = instruments.distinctBy { it.key }
        if (next.map { it.key }.toSet() == wanted.map { it.key }.toSet()) return
        val old = wanted
        wanted = next
        if (opened) { send(0, old.filter { it.key !in next.map { x -> x.key }.toSet() }); send(1, next.filter { it.key !in old.map { x -> x.key }.toSet() }) }
    }
    private fun send(action: Int, list: List<Instrument>) {
        if (list.isEmpty()) return
        val tokens = JSONArray()
        list.groupBy { it.exchangeType }.forEach { (exchange, rows) ->
            tokens.put(JSONObject().put("exchangeType", exchange).put("tokens", JSONArray(rows.map { it.token })))
        }
        socket?.send(JSONObject().put("correlationID", "scanner").put("action", action)
            .put("params", JSONObject().put("mode", 2).put("tokenList", tokens)).toString())
    }
    @Synchronized fun connect() {
        if (stopped) return
        if (Instant.now().epochSecond >= session.expires) { onStatus("Session expired. Log in again.", true); return }
        val req = Request.Builder().url("wss://smartapisocket.angelone.in/smart-stream")
            .header("Authorization", session.jwt).header("x-api-key", credentials.apiKey)
            .header("x-client-code", credentials.clientId).header("x-feed-token", session.feed).build()
        socket = api.http.newWebSocket(req, object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) {
                synchronized(this@LiveSocket) {
                    if (stopped) { webSocket.close(1000, "Stopped"); return }
                    socket = webSocket; opened = true; retries = 0
                    send(1, wanted)
                }
                handler.post { handler.removeCallbacks(heartbeat); handler.post(heartbeat) }
                onStatus("Feed connected · waiting for ticks", false)
            }
            override fun onMessage(webSocket: WebSocket, bytes: ByteString) {
                if (!stopped) runCatching { TickDecoder.decode(bytes.toByteArray()) }.getOrNull()?.let(onTick)
            }
            override fun onMessage(webSocket: WebSocket, text: String) {
                if (text != "pong") onStatus("Broker feed message · check subscriptions if quotes are missing", false)
            }
            override fun onClosing(webSocket: WebSocket, code: Int, reason: String) { webSocket.close(code, reason) }
            override fun onClosed(webSocket: WebSocket, code: Int, reason: String) { reconnect() }
            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                if (response?.code in listOf(401, 403)) {
                    onStatus("Feed session rejected. Log in again.", true)
                    close()
                } else reconnect()
            }
        })
    }
    @Synchronized private fun reconnect() {
        opened = false
        handler.removeCallbacks(heartbeat)
        if (stopped) return
        if (retries >= 8) { onStatus("Feed disconnected · tap Reconnect", false); return }
        val delay = minOf(30000L, 1000L shl retries++)
        onStatus("Reconnecting feed…", false)
        handler.postDelayed({ if (!stopped) connect() }, delay)
    }
    @Synchronized fun close() {
        stopped = true; opened = false
        handler.removeCallbacksAndMessages(null)
        socket?.cancel(); socket = null
    }
}
