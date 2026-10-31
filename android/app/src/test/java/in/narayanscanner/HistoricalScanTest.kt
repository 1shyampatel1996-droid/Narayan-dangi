package `in`.narayanscanner
import java.math.BigDecimal
import org.junit.Assert.*
import org.junit.Test
class HistoricalScanTest {
    private fun d(x: String) = BigDecimal(x)
    private val contract = Contract("2:123", 22500, "PUT", "2026-11-03")
    private fun bar(t: Long, o: String, h: String, l: String, c: String) = Candle(t, d(o), d(h), d(l), d(c))
    @Test fun keepsEarlierMatchAfterPriceLeavesBand() {
        val bars = listOf(bar(60000,"100","101","99","100"), bar(120000,"90","91","82","85"), bar(180000,"95","96","94","95"))
        val hits = HistoricalScan.scan(contract, bars, d("80"), Direction.BUY)
        assertEquals(1, hits.size)
        assertEquals(d("82"), hits.single().matchedPrice)
        assertTrue(hits.single().historical)
    }
    @Test fun strictSessionOpenAndReentry() {
        val bars = listOf(bar(60000,"88","90","80","82"))
        assertTrue(HistoricalScan.scan(contract, bars, d("80"), Direction.BUY).isEmpty())
        val reentry = listOf(bar(60000,"100","101","99","100"), bar(120000,"82","84","80","83"),
            bar(180000,"83","84","80","83"), bar(240000,"95","96","94","95"), bar(300000,"82","84","80","83"))
        val hits = HistoricalScan.scan(contract, reentry, d("80"), Direction.BUY)
        assertEquals(2, hits.size)
        assertNotEquals(hits[0].key, hits[1].key)
    }
    @Test fun doesNotInventTradeFromRangeOnly() {
        val bars = listOf(bar(60000,"100","105","60","100"))
        assertTrue(HistoricalScan.scan(contract, bars, d("80"), Direction.BUY).isEmpty())
    }
}
