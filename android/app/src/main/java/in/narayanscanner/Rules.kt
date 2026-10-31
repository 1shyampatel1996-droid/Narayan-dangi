package `in`.narayanscanner

import java.math.BigDecimal

enum class Direction { BUY, SELL_SHORT }
data class Contract(val token: String, val strike: Int, val side: String, val expiry: String)
data class Quote(val contract: Contract, val open: BigDecimal?, val ltp: BigDecimal?, val sessionDate: String)
data class Signal(
    val key: String, val contract: Contract, val direction: Direction, val target: BigDecimal,
    val matchedPrice: BigDecimal, val openingPrice: BigDecimal, val time: String, val sessionDate: String, val historical: Boolean = false
)
object Rules {
    private val lower = BigDecimal("0.90")
    private val upper = BigDecimal("1.10")
    fun matches(target: BigDecimal, open: BigDecimal?, ltp: BigDecimal?, direction: Direction): Boolean {
        if (target.signum() <= 0 || open == null || ltp == null || open.signum() <= 0 || ltp.signum() <= 0) return false
        if (ltp < target * lower || ltp > target * upper) return false
        return if (direction == Direction.BUY) open > target * upper else open < target * lower
    }
    fun digit(value: Int): Int = if (value == 0) 0 else 1 + (kotlin.math.abs(value) - 1) % 9
    fun openCode(open: BigDecimal): String {
        val total = open.setScale(2, java.math.RoundingMode.HALF_UP).toPlainString()
            .filter { it.isDigit() }.sumOf { it.digitToInt() }
        return total.toString().padStart(2, '0') + digit(total)
    }
    fun nearby(strikes: List<Int>, selector: Int, spot: BigDecimal): List<Int> {
        val values = strikes.distinct().filter { digit(it) == selector }.sorted()
        val nearest = values.indices.minByOrNull { (values[it].toBigDecimal() - spot).abs() } ?: return emptyList()
        return values.subList(maxOf(0, nearest - 1), minOf(values.size, nearest + 2))
    }
    // One immutable record per day/contract/direction/target; repeated matching ticks do not duplicate it.
    fun signal(quote: Quote, target: BigDecimal, direction: Direction, time: String): Signal? {
        if (!matches(target, quote.open, quote.ltp, direction)) return null
        val key = SignalRecords.key(quote.sessionDate, quote.contract, direction, target)
        return Signal(key, quote.contract, direction, target, quote.ltp!!, quote.open!!, time, quote.sessionDate)
    }
}

// OHLC confirms the candle range, not the exact tick or execution price.
data class Candle(val millis: Long, val open: BigDecimal, val high: BigDecimal, val low: BigDecimal, val close: BigDecimal)
object HistoricalScan {
    fun scan(contract: Contract, candles: List<Candle>, target: BigDecimal, direction: Direction): List<Signal> {
        val sorted = candles.sortedBy { it.millis }
        val opening = sorted.firstOrNull()?.open ?: return emptyList()
        return sorted.mapNotNull { bar ->
            val lower = target * BigDecimal("0.90")
            val upper = target * BigDecimal("1.10")
            val sampled = listOf(bar.open, bar.high, bar.low, bar.close).firstOrNull { it >= lower && it <= upper }
            val hit = sampled != null && Rules.matches(target, opening, sampled, direction)
            if (!hit) null else {
                val stamp = java.time.Instant.ofEpochMilli(bar.millis).atZone(java.time.ZoneId.of("Asia/Kolkata"))
                val q = Quote(contract, opening, sampled, stamp.toLocalDate().toString())
                Rules.signal(q, target, direction, stamp.toOffsetDateTime().toString())?.let {
                    it.copy(historical = true)
                }
            }
        }.distinctBy { it.key }
    }
}

// Canonical identity shared by live ticks, candle backfill and saved-record migration.
object SignalRecords {
    fun key(day: String, contract: Contract, direction: Direction, target: BigDecimal): String =
        listOf(day, contract.token, contract.expiry, contract.side, direction.name,
            target.stripTrailingZeros().toPlainString()).joinToString("|")
    fun merge(records: List<Signal>): List<Signal> = records
        .sortedWith(compareBy<Signal>({ runCatching { java.time.OffsetDateTime.parse(it.time).toInstant() }
            .getOrDefault(java.time.Instant.MAX) }, { it.historical }))
        .map { it.copy(key = key(it.sessionDate, it.contract, it.direction, it.target)) }
        .distinctBy { it.key }
    fun visible(signal: Signal, exchangePrefix: String, day: String, expiry: String,
                digits: Set<Int>, targets: List<String>): Boolean =
        signal.contract.token.startsWith(exchangePrefix) && signal.sessionDate == day &&
            signal.contract.expiry == expiry && Rules.digit(signal.contract.strike) in digits &&
            targets.withIndex().any { (i, value) ->
                (if (i < 4) Direction.BUY else Direction.SELL_SHORT) == signal.direction &&
                    value.toBigDecimalOrNull()?.compareTo(signal.target) == 0
            }
}
