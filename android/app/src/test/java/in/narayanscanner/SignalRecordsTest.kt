package `in`.narayanscanner
import java.math.BigDecimal
import org.junit.Assert.*
import org.junit.Test

class SignalRecordsTest {
    private val contract = Contract("2:123", 23100, "CALL", "2026-11-03")
    private val day = "2026-10-30"
    private fun signal(target: String, time: String = "10:00", price: String = target) =
        Rules.signal(Quote(contract, BigDecimal("200"), BigDecimal(price), day),
            BigDecimal(target), Direction.BUY, "${day}T${time}:00+05:30")!!
    @Test fun repeatedTicksAndNumericFormattingUseOneIdentity() {
        val first = signal("100")
        val repeat = signal("100.00", "11:00", "101")
        assertEquals(first.key, repeat.key)
        val records = SignalRecords.merge(listOf(repeat, first))
        assertEquals(1, records.size)
        assertEquals(first, records.single())
    }
    @Test fun distinctTargetsCallsPutsExpiriesAndDaysRemainSeparate() {
        val first = signal("100")
        val records = SignalRecords.merge(listOf(first, signal("120"),
            first.copy(contract = contract.copy(side = "PUT")),
            first.copy(contract = contract.copy(expiry = "2026-11-10")),
            first.copy(sessionDate = "2026-10-29"), first.copy(direction = Direction.SELL_SHORT)))
        assertEquals(6, records.size)
    }
    @Test fun migrationCollapsesOldTimestampKeysAndKeepsEarliestMatch() {
        val first = signal("100")
        val duplicate = signal("100", "11:00")
        val candle = signal("100", "09:30").copy(historical = true)
        val records = SignalRecords.merge(listOf(first.copy(key = "old|live|1"),
            duplicate.copy(key = "old|live|2"), candle.copy(key = "old|history|3")))
        assertEquals(1, records.size)
        assertEquals(candle.time, records.single().time)
        assertEquals(first.key, records.single().key)
        assertEquals(records, SignalRecords.merge(records))
    }
    @Test fun switchingDigitAwayAndBackRestoresStoredFirstMatch() {
        val first = signal("100")
        fun visible(digit: Int) = SignalRecords.visible(first, "2:", day, contract.expiry,
            setOf(digit), listOf("100.00", "", "", "", "", ""))
        assertTrue(visible(6))
        assertFalse(visible(9))
        assertTrue(visible(6))
        assertFalse(SignalRecords.visible(first, "4:", day, contract.expiry, setOf(6), listOf("100")))
    }
    @Test fun newlySelectedDigitCanFindBuyBeforeCurrentPriceDropped() {
        val candles = listOf(
            Candle(1793331900000, BigDecimal("200"), BigDecimal("201"), BigDecimal("195"), BigDecimal("200")),
            Candle(1793335500000, BigDecimal("100"), BigDecimal("102"), BigDecimal("98"), BigDecimal("100")),
            Candle(1793339100000, BigDecimal("60"), BigDecimal("65"), BigDecimal("55"), BigDecimal("60")))
        val records = HistoricalScan.scan(contract, candles, BigDecimal("100"), Direction.BUY)
        assertEquals(1, records.size)
        assertEquals(BigDecimal("100"), records.single().matchedPrice)
        assertTrue(records.single().historical)
    }
}
