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
import androidx.compose.ui.text.input.TextFieldValue
import androidx.compose.ui.text.TextRange
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
private fun timeLabel(millis: Long) = if (millis <= 0) "समय नहीं मिला" else Instant.ofEpochMilli(millis).atZone(IST).format(DateTimeFormatter.ofPattern("dd MMM, h:mm a"))
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
    // Own edits synchronously; delayed market renders must never reset selection.
    var local by remember { mutableStateOf(TextFieldValue(value, TextRange(value.length))) }
    OutlinedTextField(local, { next ->
        val valid = if (label.startsWith("Digit")) next.text.isEmpty() || (next.text.length == 1 && next.text[0] in '1'..'9')
            else next.text.length <= 12 && next.text.matches(Regex("[0-9]*\\.?[0-9]{0,2}"))
        if (valid) { local = next; update(next.text) }
    }, modifier = modifier, label = { Text(label, fontSize = 10.sp) },
        textStyle = androidx.compose.ui.text.TextStyle(fontSize = 16.sp),
        singleLine = true, keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal))
}
private fun signalTime(s: Signal): String = runCatching {
    OffsetDateTime.parse(s.time).atZoneSameInstant(IST).format(DateTimeFormatter.ofPattern("dd MMM, h:mm a")) + " IST"
}.getOrDefault(s.time)
@Composable private fun Dashboard(s: ScannerState, c: ScannerController) {
    val live = s.markets.firstOrNull { it.first == s.index }?.second?.let { fresh(it) } == true
    val signals = (s.history.filter { signal ->
        signal.contract.token.startsWith(if (s.index == "SENSEX") "4:" else "2:") &&
            signal.sessionDate == (if (live) LocalDate.now(IST).toString() else s.sessionDate)
    } + if (live) emptyList() else s.historical).distinctBy { it.key }
    var inputs by rememberSaveable { mutableStateOf(true) }
    var expiryMenu by remember { mutableStateOf(false) }
    LazyColumn(Modifier.fillMaxSize().windowInsetsPadding(WindowInsets.safeDrawing),
        contentPadding = PaddingValues(12.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
        item {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                Branding("DIGIT SCANNER · 0.2.1")
                TextButton(onClick = c::logout) { Text("Logout", color = Muted) }
            }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                listOf("NIFTY", "SENSEX").forEach { index ->
                    FilterChip(s.index == index, { c.switchIndex(index) }, label = { Text(index) })
                }
            }
            Text(if (live) "LIVE · ${LocalDate.now(IST)}" else "LAST SESSION · ${s.sessionDate.ifBlank { "Loading…" }}", color = Green, fontSize = 12.sp)
            Text(s.status, color = Muted, fontSize = 10.sp)
        }
        item {
            Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                s.markets.forEach { (name, tick) ->
                    Card(Modifier.weight(1f)) {
                        Column(Modifier.padding(5.dp)) {
                            Text(name, fontSize = 8.sp, color = Muted)
                            Text(money(tick?.open), fontSize = 10.sp)
                            Text(tick?.open?.let { Rules.openCode(it) } ?: "—", fontSize = 19.sp, color = Green)
                        }
                    }
                }
            }
        }
        item { TextButton(onClick = { inputs = !inputs }) { Text(if (inputs) "Hide settings · show all strikes" else "Edit digits / prices") } }
        if (inputs) item {
            key(s.index) {
                Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                        NumberField("Digit 1", s.digit1, Modifier.weight(1f)) { c.digit(0, it) }
                        NumberField("Digit 2", s.digit2, Modifier.weight(1f)) { c.digit(1, it) }
                    }
                    Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                        for (i in 0..3) NumberField("Buy ${i + 1}", s.targets[i], Modifier.weight(1f)) { c.target(i, it) }
                    }
                    Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                        for (i in 4..5) NumberField("Sell ${i - 3}", s.targets[i], Modifier.weight(1f)) { c.target(i, it) }
                    }
                }
            }
            Text("Auto saved · ±10% · Buy OPEN >110% · Sell OPEN <90%", color = Muted, fontSize = 9.sp)
        }
        item {
            Box {
                TextButton(onClick = { expiryMenu = true }) { Text("${s.index} expiry · ${s.expiry}", fontSize = 12.sp) }
                DropdownMenu(expiryMenu, { expiryMenu = false }) {
                    s.expiries.forEach { expiry -> DropdownMenuItem(text = { Text(expiry) }, onClick = { c.expiry(expiry); expiryMenu = false }) }
                }
            }
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text("CALL", color = Muted, fontSize = 11.sp)
                Text("STRIKE", color = Muted, fontSize = 11.sp)
                Text("PUT", color = Muted, fontSize = 11.sp)
            }
        }
        // One compact table contains all six strikes / twelve option contracts.
        item {
            Column(verticalArrangement = Arrangement.spacedBy(3.dp)) {
                s.quotes.groupBy { it.first.contract.strike }.toSortedMap().forEach { (strike, rows) ->
                    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(5.dp)) {
                        OptionCell(rows.firstOrNull { it.first.contract.side == "CALL" }, signals, Modifier.weight(1f))
                        Text(strike.toString(), fontWeight = FontWeight.Bold, fontSize = 14.sp, modifier = Modifier.width(65.dp))
                        OptionCell(rows.firstOrNull { it.first.contract.side == "PUT" }, signals, Modifier.weight(1f))
                    }
                }
            }
            if (s.quotes.isEmpty()) Text("Quotes का इंतज़ार · connection और expiry जाँचें", color = Muted, fontSize = 12.sp)
            if (!live) Text(s.scanStatus.ifBlank { "Historical scan loading…" }, color = Muted, fontSize = 10.sp)
            TextButton(onClick = c::reconnect) { Text("Refresh / retry data", fontSize = 11.sp) }
        }
        listOf(Direction.BUY, Direction.SELL_SHORT).forEach { direction ->
            item {
                HorizontalDivider()
                Text(if (direction == Direction.BUY) "BEST BUY · LOCKED MATCHES" else "SELL SHORT · LOCKED MATCHES",
                    color = if (direction == Direction.BUY) Green else Red, fontWeight = FontWeight.Bold, fontSize = 13.sp)
            }
            val records = signals.filter { it.direction == direction }.sortedBy { it.time }
            if (records.isEmpty()) item { Text("इस session में अभी कोई उपलब्ध match नहीं", color = Muted, fontSize = 11.sp) }
            items(records, key = { it.key }) { signal ->
                Card {
                    Column(Modifier.fillMaxWidth().padding(10.dp)) {
                        Text("${s.index} · ${signal.contract.strike} ${signal.contract.side} · ${signal.contract.expiry}", fontSize = 12.sp, fontWeight = FontWeight.Bold)
                        Text(if (signal.historical) "Candle reference ₹${money(signal.matchedPrice)}" else "LOCKED ₹${money(signal.matchedPrice)}",
                            color = if (direction == Direction.BUY) Green else Red, fontSize = 17.sp)
                        Text(signalTime(signal), fontSize = 12.sp)
                        Text("Target ₹${money(signal.target)} · OPEN ₹${money(signal.openingPrice)}", color = Muted, fontSize = 10.sp)
                        if (signal.historical) Text("Historical · one-minute OHLC · exact tick / fill unconfirmed", color = Muted, fontSize = 9.sp)
                    }
                }
            }
        }
        item { Text("Scanner records · automatic orders नहीं लगते", color = Muted, fontSize = 10.sp) }
    }
}
@Composable private fun OptionCell(row: Pair<Quote, Tick>?, signals: List<Signal>, modifier: Modifier) {
    val matches = signals.filter { it.contract.token == row?.first?.contract?.token }
    val buy = matches.any { it.direction == Direction.BUY }
    val sell = matches.any { it.direction == Direction.SELL_SHORT }
    val color = if (buy) Green else if (sell) Red else Muted
    Card(modifier, colors = CardDefaults.cardColors(containerColor = if (buy) Color(0xFF123D32) else if (sell) Color(0xFF402535) else Panel)) {
        Column(Modifier.padding(horizontal = 8.dp, vertical = 6.dp)) {
            Text("₹${money(row?.first?.ltp)}", color = color, fontSize = 16.sp, fontWeight = FontWeight.Bold)
            Text(if (buy) "BUY ✓" else if (sell) "SELL ✓" else "—", color = color, fontSize = 9.sp)
        }
    }
}
