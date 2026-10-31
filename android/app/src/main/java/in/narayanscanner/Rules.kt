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
        val key = listOf(quote.sessionDate, quote.contract.token, direction.name,
            target.stripTrailingZeros().toPlainString()).joinToString("|")
        return Signal(key, quote.contract, direction, target, quote.ltp!!, quote.open!!, time, quote.sessionDate)
    }
}

// OHLC confirms the candle range, not the exact tick or execution price.
data class Candle(val millis: Long, val open: BigDecimal, val high: BigDecimal, val low: BigDecimal, val close: BigDecimal)
object HistoricalScan {
    fun scan(contract: Contract, candles: List<Candle>, target: BigDecimal, direction: Direction): List<Signal> {
        val sorted = candles.sortedBy { it.millis }
        val opening = sorted.firstOrNull()?.open ?: return emptyList()
        var inside = false
        return sorted.mapNotNull { bar ->
            val lower = target * BigDecimal("0.90")
            val upper = target * BigDecimal("1.10")
            val sampled = listOf(bar.open, bar.high, bar.low, bar.close).firstOrNull { it >= lower && it <= upper }
            val hit = sampled != null && Rules.matches(target, opening, sampled, direction)
            val entering = hit && !inside
            inside = hit
            if (!entering) null else {
                val stamp = java.time.Instant.ofEpochMilli(bar.millis).atZone(java.time.ZoneId.of("Asia/Kolkata"))
                val q = Quote(contract, opening, sampled, stamp.toLocalDate().toString())
                Rules.signal(q, target, direction, stamp.toOffsetDateTime().toString())?.let {
                    it.copy(key = it.key + "|history|" + bar.millis, historical = true)
                }
            }
        }
    }
}
