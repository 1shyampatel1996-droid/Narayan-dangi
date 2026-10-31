package `in`.narayanscanner

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Modifier
import androidx.compose.ui.Alignment
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import java.math.BigDecimal
import java.time.*
import java.time.format.DateTimeFormatter

private val Green = Color(0xFF4DE0A3)
private val Red = Color(0xFFFF8391)
private val Navy = Color(0xFF0B1220)
private val Panel = Color(0xFF162237)
private val Muted = Color(0xFFAAB7CC)
private fun money(v: BigDecimal?) = v?.setScale(2, java.math.RoundingMode.HALF_UP)?.toPlainString() ?: "—"
private fun timeLabel(millis: Long) = if (millis <= 0) "समय नहीं मिला" else Instant.ofEpochMilli(millis).atZone(IST).format(DateTimeFormatter.ofPattern("dd MMM HH:mm:ss"))
private fun fresh(t: Tick): Boolean = System.currentTimeMillis() - t.exchangeMillis in 0..15000 &&
    Instant.ofEpochMilli(t.exchangeMillis).atZone(IST).toLocalDate() == LocalDate.now(IST)

class MainActivity : ComponentActivity() {
    private lateinit var controller: ScannerController
    private var screen by mutableStateOf(ScannerState())
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        controller = ScannerController(this) { screen = it }
        setContent {
            MaterialTheme(colorScheme = darkColorScheme(primary = Green, secondary = Green,
                background = Navy, surface = Panel, onBackground = Color(0xFFEAF0FA), onSurface = Color(0xFFEAF0FA))) {
                Surface(Modifier.fillMaxSize(), color = Navy) {
                    if (screen.checking) Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                        Column(horizontalAlignment = Alignment.CenterHorizontally) {
                            CircularProgressIndicator()
                            Spacer(Modifier.height(16.dp))
                            Text(screen.status)
                        }
                    } else if (!screen.loggedIn) LoginScreen(screen, controller)
                    else Dashboard(screen, controller)
                }
            }
        }
    }
    override fun onStart() { super.onStart(); if (::controller.isInitialized) controller.foreground(true) }
    override fun onStop() { if (::controller.isInitialized) controller.foreground(false); super.onStop() }
    override fun onDestroy() { if (::controller.isInitialized) controller.close(); super.onDestroy() }
}
@Composable private fun Branding(subtitle: String) {
    Column {
        Text("NARAYAN", fontSize = 25.sp, fontWeight = FontWeight.Bold, letterSpacing = 1.sp)
        Text(subtitle, fontSize = 10.sp, color = Green, letterSpacing = 2.sp)
    }
}
@Composable private fun LoginScreen(s: ScannerState, c: ScannerController) {
    // Secret fields are intentionally not rememberSaveable.
    var api by remember { mutableStateOf("") }
    var client by remember { mutableStateOf("") }
    var pin by remember { mutableStateOf("") }
    var otp by remember { mutableStateOf("") }
    LazyColumn(Modifier.fillMaxSize().windowInsetsPadding(WindowInsets.safeDrawing),
        contentPadding = PaddingValues(24.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
        item { Spacer(Modifier.height(40.dp)); Branding("PERSONAL DIGIT SCANNER") }
        item {
            Text(if (s.configured) "Welcome back" else "Account setup", fontSize = 30.sp, fontWeight = FontWeight.Bold)
            Text(if (s.configured) "Authenticator का मौजूदा code डालें।"
                else "पहली बार Angel One की जानकारी अपने फोन पर सेव करें।", color = Muted, fontSize = 14.sp)
        }
        if (!s.configured) {
            item { SecretField("SmartAPI API key", api, false) { api = it } }
            item { OutlinedTextField(client, { client = it }, label = { Text("Angel One client ID") }, singleLine = true, modifier = Modifier.fillMaxWidth()) }
            item { SecretField("Angel One PIN", pin, false) { pin = it } }
            item { Button(onClick = { c.saveSetup(api, client, pin); pin = ""; api = "" },
                enabled = !s.busy, modifier = Modifier.fillMaxWidth().height(52.dp)) { Text("Save account setup") } }
            item { Text("जानकारी Android Keystore से encrypt होगी। Authenticator seed की जरूरत नहीं है।", fontSize = 12.sp, color = Muted) }
        } else {
            item { SecretField("6-digit authenticator code", otp, true) {
                if (it.length <= 6 && it.all { char -> char in '0'..'9' }) otp = it
            } }
            item { Button(onClick = { c.login(otp); otp = "" }, enabled = !s.busy && otp.length == 6,
                modifier = Modifier.fillMaxWidth().height(52.dp)) {
                    if (s.busy) CircularProgressIndicator(Modifier.size(20.dp), strokeWidth = 2.dp)
                    else Text("Login to scanner")
                } }
            item { TextButton(onClick = c::accountSetup, enabled = !s.busy) { Text("Edit account setup") } }
            item { Text("Session वैध रहने तक ऐप दोबारा खोलने पर login बना रहेगा।", fontSize = 12.sp, color = Muted) }
        }
        item { Text(s.status, color = Muted, fontSize = 13.sp) }
        item { HorizontalDivider(); Text("Independent personal scanner", color = Muted, fontSize = 11.sp, modifier = Modifier.padding(top = 12.dp)) }
    }
}
@Composable private fun SecretField(label: String, value: String, digits: Boolean, update: (String) -> Unit) {
    OutlinedTextField(value, update, label = { Text(label) }, modifier = Modifier.fillMaxWidth(),
        singleLine = true, visualTransformation = PasswordVisualTransformation(),
        keyboardOptions = KeyboardOptions(keyboardType = if (digits) KeyboardType.NumberPassword else KeyboardType.Password))
}
@Composable private fun NumberField(label: String, value: String, modifier: Modifier, update: (String) -> Unit) {
    OutlinedTextField(value, update, modifier = modifier, label = { Text(label, fontSize = 12.sp) },
        singleLine = true, keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal))
}
@Composable private fun Dashboard(s: ScannerState, c: ScannerController) {
    var listMode by rememberSaveable { mutableStateOf(0) }
    var historyMode by rememberSaveable { mutableStateOf(0) }
    var expiryMenu by remember { mutableStateOf(false) }
    fun match(q: Quote, direction: Direction): Boolean = (if (direction == Direction.BUY) s.targets.take(4) else s.targets.drop(4)).any {
        it.toBigDecimalOrNull()?.let { target -> Rules.matches(target, q.open, q.ltp, direction) } == true
    }
    val rows = s.quotes.filter { (q, tick) ->
        listMode == 0 || (s.connected && fresh(tick) && match(q, if (listMode == 1) Direction.BUY else Direction.SELL_SHORT))
    }
    val history = s.history.filter { it.direction == if (historyMode == 0) Direction.BUY else Direction.SELL_SHORT }
    LazyColumn(Modifier.fillMaxSize().windowInsetsPadding(WindowInsets.safeDrawing),
        contentPadding = PaddingValues(14.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        item {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                Branding("LIVE DIGIT SCANNER")
                TextButton(onClick = c::logout) { Text("Logout", color = Muted, fontSize = 12.sp) }
            }
        }
        item {
            Card(colors = CardDefaults.cardColors(containerColor = Panel)) {
                Column(Modifier.fillMaxWidth().padding(12.dp)) {
                    Text(s.status, color = if (s.connected) Green else Muted, fontSize = 12.sp)
                    Text("Ticks ${s.ticks} · ${LocalDate.now(IST)}", color = Muted, fontSize = 10.sp)
                    if (!s.connected) TextButton(onClick = c::reconnect) { Text("Reconnect") }
                }
            }
        }
        item {
            Text("DAY OPEN  /  DIGIT", color = Muted, fontSize = 10.sp, letterSpacing = 1.sp)
            Spacer(Modifier.height(6.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(5.dp)) {
                val cards = if (s.markets.isEmpty()) listOf("NIFTY", "NIFTY FUT", "SENSEX", "SENSEX FUT").map { it to null } else s.markets
                cards.forEach { (label, tick) ->
                    Card(Modifier.weight(1f), colors = CardDefaults.cardColors(containerColor = Panel)) {
                        Column(Modifier.padding(horizontal = 6.dp, vertical = 12.dp)) {
                            Text(label, fontSize = 8.sp, color = Muted)
                            Text(money(tick?.open), fontSize = 11.sp, maxLines = 1)
                            Text(tick?.open?.let { Rules.openCode(it) } ?: "—", fontSize = 25.sp, color = Green, fontWeight = FontWeight.Bold)
                            Text(tick?.let { timeLabel(it.exchangeMillis) } ?: "Waiting", fontSize = 8.sp, color = Muted)
                        }
                    }
                }
            }
        }
        item {
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                NumberField("Strike digit 1", s.digit1, Modifier.weight(1f)) { c.digit(0, it) }
                NumberField("Strike digit 2", s.digit2, Modifier.weight(1f)) { c.digit(1, it) }
            }
        }
        item { Text("BUY भाव", color = Green, fontSize = 12.sp, fontWeight = FontWeight.Bold) }
        items(listOf(0, 2)) { start ->
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                for (i in start..start + 1) NumberField("Buy ${i + 1}", s.targets[i], Modifier.weight(1f)) { c.target(i, it) }
            }
        }
        item { Text("SELL SHORT भाव", color = Red, fontSize = 12.sp, fontWeight = FontWeight.Bold) }
        item {
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                for (i in 4..5) NumberField("Sell ${i - 3}", s.targets[i], Modifier.weight(1f)) { c.target(i, it) }
            }
            Text("भाव 0 / खाली = बंद · LTP ±10% · Buy OPEN >110% · Sell OPEN <90%", fontSize = 10.sp, color = Muted, modifier = Modifier.padding(top = 8.dp))
        }
        item {
            Box {
                OutlinedButton(onClick = { expiryMenu = true }) { Text("NIFTY expiry · ${s.expiry.ifBlank { "Waiting" }}") }
                DropdownMenu(expanded = expiryMenu, onDismissRequest = { expiryMenu = false }) {
                    s.expiries.forEach { value -> DropdownMenuItem(text = { Text(value) },
                        onClick = { c.expiry(value); expiryMenu = false }) }
                }
            }
        }
        item {
            Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                listOf("All", "Buying", "Sell Short").forEachIndexed { index, name ->
                    FilterChip(selected = listMode == index, onClick = { listMode = index }, label = { Text(name, fontSize = 12.sp) })
                }
            }
        }
        if (rows.isEmpty()) item {
            Text(if (s.quotes.isEmpty()) "Live quotes का इंतज़ार है।" else "इन शर्तों पर अभी कोई match नहीं है।", color = Muted, fontSize = 13.sp, modifier = Modifier.padding(vertical = 12.dp))
        }
        items(rows, key = { it.first.contract.token }) { (q, tick) ->
            val valid = fresh(tick) && s.connected
            val buy = valid && match(q, Direction.BUY)
            val sell = valid && match(q, Direction.SELL_SHORT)
            val accent = if (buy) Green else if (sell) Red else Muted
            Card(colors = CardDefaults.cardColors(containerColor = Panel)) {
                Column(Modifier.fillMaxWidth().padding(14.dp), verticalArrangement = Arrangement.spacedBy(5.dp)) {
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                        Column {
                            Text("${q.contract.strike} ${q.contract.side}", fontWeight = FontWeight.Bold, fontSize = 15.sp)
                            Text(q.contract.expiry, fontSize = 10.sp, color = Muted)
                        }
                        Text("₹${money(q.ltp)}", fontSize = 24.sp, fontWeight = FontWeight.Bold, color = accent)
                    }
                    Text("OPEN ₹${money(q.open)} · ${timeLabel(tick.exchangeMillis)} IST", fontSize = 10.sp, color = Muted)
                    if (!valid) Text("Last available quote · no new signal", color = Muted, fontSize = 10.sp)
                    if (buy || sell) Text(listOfNotNull("BUY MATCH".takeIf { buy }, "SELL SHORT MATCH".takeIf { sell }).joinToString(" / "), color = accent, fontSize = 11.sp)
                }
            }
        }
        item {
            HorizontalDivider(color = Panel)
            Text("LOCKED RECORDS", fontSize = 11.sp, color = Muted, modifier = Modifier.padding(top = 14.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                FilterChip(historyMode == 0, { historyMode = 0 }, label = { Text("Best Buy") })
                FilterChip(historyMode == 1, { historyMode = 1 }, label = { Text("Best Sell Short") })
            }
        }
        if (history.isEmpty()) item { Text("अभी कोई locked match नहीं है।", fontSize = 13.sp, color = Muted, modifier = Modifier.padding(vertical = 12.dp)) }
        items(history.reversed(), key = { it.key }) { signal ->
            val current = s.quotes.firstOrNull { it.first.contract.token == signal.contract.token }
            Card(colors = CardDefaults.cardColors(containerColor = Panel)) {
                Column(Modifier.fillMaxWidth().padding(14.dp), verticalArrangement = Arrangement.spacedBy(5.dp)) {
                    Text("${signal.contract.strike} ${signal.contract.side} · ${signal.contract.expiry}", fontWeight = FontWeight.Bold, fontSize = 14.sp)
                    Text("LOCKED ₹${money(signal.matchedPrice)}", fontSize = 22.sp, fontWeight = FontWeight.Bold, color = if (historyMode == 0) Green else Red)
                    Text("Target ₹${money(signal.target)} · OPEN ₹${money(signal.openingPrice)}", fontSize = 11.sp, color = Muted)
                    Text(signal.time, fontSize = 10.sp, color = Muted)
                    Text("Current LTP ₹${money(current?.first?.ltp)}" +
                        (if (current != null && (!s.connected || !fresh(current.second))) " · last available" else ""), fontSize = 12.sp)
                }
            }
        }
        item { Text("Scanner matches · कोई order अपने-आप नहीं लगता", fontSize = 10.sp, color = Muted, modifier = Modifier.padding(vertical = 10.dp)) }
    }
}
