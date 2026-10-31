package `in`.narayanscanner

import android.app.Activity
import android.os.Bundle
import android.content.Context
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import org.json.JSONArray
import org.json.JSONObject
import java.math.BigDecimal
import java.time.LocalDate
import java.time.ZonedDateTime
import java.time.ZoneId
import java.time.format.DateTimeFormatter

private val Green = Color(0xFF4DE0A3)
private val Red = Color(0xFFFF8391)
private val Navy = Color(0xFF0B1220)
private val Panel = Color(0xFF162237)
private val India = ZoneId.of("Asia/Kolkata")
private fun money(v: BigDecimal?) = v?.setScale(2, java.math.RoundingMode.HALF_UP)?.toPlainString() ?: "—"

class MainActivity : ComponentActivity() {
    private lateinit var store: LocalStore
    private val quotes = mutableStateListOf<Quote>()
    private val history = mutableStateListOf<Signal>()
    private val inputs = mutableStateListOf<String>()
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        store = LocalStore(this)
        inputs.addAll((0..5).map { store.target(it) })
        history.addAll(store.load())
        setContent {
            MaterialTheme(colorScheme = darkColorScheme(
                primary = Green, background = Navy, surface = Panel,
                onBackground = Color(0xFFEAF0FA), onSurface = Color(0xFFEAF0FA)
            )) {
                Scanner(inputs, quotes, history) { index, value ->
                    inputs[index] = value
                    store.saveTarget(index, value)
                }
            }
        }
    }
    // Integration boundary for validated live feed; not wired to Angel One yet.
    fun onQuote(quote: Quote) {
        check(android.os.Looper.myLooper() == android.os.Looper.getMainLooper())
        if (quote.sessionDate != LocalDate.now(India).toString()) return
        val index = quotes.indexOfFirst { it.contract.token == quote.contract.token }
        if (index < 0) quotes.add(quote) else quotes[index] = quote
        val timestamp = ZonedDateTime.now(India).format(DateTimeFormatter.ISO_OFFSET_DATE_TIME)
        inputs.forEachIndexed { i, text ->
            val target = text.toBigDecimalOrNull() ?: return@forEachIndexed
            val signal = Rules.signal(quote, target, if (i < 4) Direction.BUY else Direction.SELL_SHORT, timestamp)
            if (signal != null && history.none { it.key == signal.key }) {
                history.add(signal)
                store.save(history)
            }
        }
    }
}

@Composable private fun Scanner(
    inputs: List<String>, live: List<Quote>, history: List<Signal>,
    update: (Int, String) -> Unit
) {
    var first by remember { mutableStateOf("6") }
    var second by remember { mutableStateOf("9") }
    var demo by remember { mutableStateOf(false) }
    var tab by remember { mutableStateOf(0) }
    val sample = listOf(
        Quote(Contract("demo-ce", 23100, "CALL", "DEMO"), BigDecimal("95"), BigDecimal("82"), "DEMO"),
        Quote(Contract("demo-pe", 23100, "PUT", "DEMO"), BigDecimal("68"), BigDecimal("79"), "DEMO")
    )
    val rows = if (demo) sample else live
    Surface(Modifier.fillMaxSize(), color = Navy) {
        LazyColumn(
            Modifier.fillMaxSize().windowInsetsPadding(WindowInsets.safeDrawing),
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            item {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Column {
                        Text("NARAYAN", fontSize = 24.sp, fontWeight = FontWeight.Bold)
                        Text("DIGIT SCANNER", fontSize = 11.sp, color = Green, letterSpacing = 2.sp)
                    }
                    Text(if (demo) "DEMO DATA" else "NOT CONNECTED",
                        color = if (demo) Red else Color(0xFFAAB7CC), fontSize = 11.sp)
                }
            }
            item {
                Text("DAY OPEN", color = Color(0xFFAAB7CC), fontSize = 11.sp)
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    listOf("NIFTY", "NIFTY FUT", "SENSEX", "SENSEX FUT").forEach { name ->
                        Card(Modifier.weight(1f), colors = CardDefaults.cardColors(containerColor = Panel)) {
                            Column(Modifier.padding(8.dp)) {
                                Text(name, fontSize = 9.sp)
                                Text("—", fontSize = 13.sp)
                                Text("—", fontSize = 24.sp, color = Green, fontWeight = FontWeight.Bold)
                            }
                        }
                    }
                }
            }
            item {
                Text("STRIKE DIGITS", fontSize = 11.sp, color = Color(0xFFAAB7CC))
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Entry("Digit 1", first, Modifier.weight(1f)) {
                        if (it.isEmpty() || (it.length == 1 && it[0] in '1'..'9')) first = it
                    }
                    Entry("Digit 2", second, Modifier.weight(1f)) {
                        if (it.isEmpty() || (it.length == 1 && it[0] in '1'..'9')) second = it
                    }
                }
            }
            item { Text("BUY TARGETS", color = Green, fontWeight = FontWeight.Bold) }
            items(listOf(0, 2)) { start ->
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    for (i in start..start + 1) {
                        Entry("Buy ${i + 1}", inputs[i], Modifier.weight(1f)) { update(i, it) }
                    }
                }
            }
            item { Text("SELL SHORT TARGETS", color = Red, fontWeight = FontWeight.Bold) }
            item {
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    for (i in 4..5) {
                        Entry("Sell ${i - 3}", inputs[i], Modifier.weight(1f)) { update(i, it) }
                    }
                }
            }
            item {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text("Preview sample quotes", fontSize = 13.sp)
                    Switch(checked = demo, onCheckedChange = { demo = it })
                }
                Text(
                    if (demo) "Simulated prices · no real signals saved"
                    else "Angel One connection pending · no live quotes",
                    fontSize = 11.sp, color = Color(0xFFAAB7CC)
                )
            }
            items(rows, key = { it.contract.token }) { quote ->
                val buy = inputs.take(4).any {
                    it.toBigDecimalOrNull()?.let { t -> Rules.matches(t, quote.open, quote.ltp, Direction.BUY) } == true
                }
                val sell = inputs.drop(4).any {
                    it.toBigDecimalOrNull()?.let { t -> Rules.matches(t, quote.open, quote.ltp, Direction.SELL_SHORT) } == true
                }
                Card(colors = CardDefaults.cardColors(containerColor = Panel)) {
                    Column(Modifier.fillMaxWidth().padding(14.dp)) {
                        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                            Text("${quote.contract.strike} ${quote.contract.side}", fontWeight = FontWeight.Bold)
                            Text("₹${money(quote.ltp)}", fontWeight = FontWeight.Bold, fontSize = 22.sp)
                        }
                        Text("OPEN ₹${money(quote.open)} · ${quote.contract.expiry}", fontSize = 11.sp)
                        if (buy || sell) Text(
                            (if (demo) "DEMO · " else "") + listOfNotNull(
                                "BUY MATCH".takeIf { buy }, "SELL SHORT MATCH".takeIf { sell }
                            ).joinToString(" / "),
                            color = if (buy) Green else Red, fontSize = 12.sp
                        )
                    }
                }
            }
            item {
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    FilterChip(selected = tab == 0, onClick = { tab = 0 }, label = { Text("Best Buy") })
                    FilterChip(selected = tab == 1, onClick = { tab = 1 }, label = { Text("Best Sell Short") })
                }
            }
            val records = history.filter { it.direction == if (tab == 0) Direction.BUY else Direction.SELL_SHORT }
            if (records.isEmpty()) item {
                Text("No locked matches yet", color = Color(0xFFAAB7CC), modifier = Modifier.padding(vertical = 16.dp))
            }
            items(records.reversed(), key = { it.key }) { signal ->
                Card(colors = CardDefaults.cardColors(containerColor = Panel)) {
                    Column(Modifier.fillMaxWidth().padding(14.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Text("${signal.contract.strike} ${signal.contract.side} · ${signal.contract.expiry}", fontWeight = FontWeight.Bold)
                        Text("LOCKED ₹${money(signal.matchedPrice)} · Target ₹${money(signal.target)}", color = if (tab == 0) Green else Red)
                        Text(signal.time, fontSize = 11.sp)
                        val current = live.firstOrNull { it.contract.token == signal.contract.token }
                        Text("Current LTP ₹${money(current?.ltp)}", fontSize = 12.sp)
                    }
                }
            }
            item { Text("Personal scanner · match records only", fontSize = 11.sp, color = Color(0xFFAAB7CC)) }
        }
    }
}
@Composable private fun Entry(label: String, value: String, modifier: Modifier, update: (String) -> Unit) {
    OutlinedTextField(
        value = value, onValueChange = { if (it.length <= 12 && it.matches(Regex("[0-9]*\\.?[0-9]{0,2}"))) update(it) },
        modifier = modifier, label = { Text(label, fontSize = 12.sp) }, singleLine = true,
        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal)
    )
}

private class LocalStore(context: Context) {
    private val prefs = context.getSharedPreferences("scanner", Context.MODE_PRIVATE)
    fun target(index: Int) = prefs.getString("target_$index", "") ?: ""
    fun saveTarget(index: Int, value: String) { prefs.edit().putString("target_$index", value).apply() }
    fun save(signals: List<Signal>) {
        val array = JSONArray()
        signals.forEach { s ->
            array.put(JSONObject().put("key", s.key).put("token", s.contract.token)
                .put("strike", s.contract.strike).put("side", s.contract.side).put("expiry", s.contract.expiry)
                .put("direction", s.direction.name).put("target", s.target.toPlainString())
                .put("price", s.matchedPrice.toPlainString()).put("open", s.openingPrice.toPlainString())
                .put("time", s.time).put("day", s.sessionDate))
        }
        prefs.edit().putString("history", array.toString()).apply()
    }
    fun load(): List<Signal> = runCatching {
        val array = JSONArray(prefs.getString("history", "[]"))
        (0 until array.length()).map { i ->
            val s = array.getJSONObject(i)
            Signal(s.getString("key"),
                Contract(s.getString("token"), s.getInt("strike"), s.getString("side"), s.getString("expiry")),
                Direction.valueOf(s.getString("direction")), s.getString("target").toBigDecimal(),
                s.getString("price").toBigDecimal(), s.getString("open").toBigDecimal(), s.getString("time"), s.getString("day"))
        }
    }.getOrDefault(emptyList())
}
