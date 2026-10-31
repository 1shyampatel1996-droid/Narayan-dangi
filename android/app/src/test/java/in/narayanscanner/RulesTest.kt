package `in`.narayanscanner
import java.math.BigDecimal
import org.junit.Assert.*
import org.junit.Test
class RulesTest {
    private fun d(v: String) = BigDecimal(v)
    @Test fun strictBuyOpenBoundary() {
        assertFalse(Rules.matches(d("80"), d("85"), d("82"), Direction.BUY))
        assertFalse(Rules.matches(d("80"), d("88"), d("82"), Direction.BUY))
        assertTrue(Rules.matches(d("80"), d("88.05"), d("82"), Direction.BUY))
    }
    @Test fun strictSellOpenBoundary() {
        assertFalse(Rules.matches(d("80"), d("72"), d("82"), Direction.SELL_SHORT))
        assertTrue(Rules.matches(d("80"), d("71.95"), d("82"), Direction.SELL_SHORT))
    }
    @Test fun premiumRangeAndMissingOpen() {
        assertTrue(Rules.matches(d("80"), d("89"), d("72"), Direction.BUY))
        assertTrue(Rules.matches(d("80"), d("89"), d("88"), Direction.BUY))
        assertFalse(Rules.matches(d("80"), d("89"), d("88.05"), Direction.BUY))
        assertFalse(Rules.matches(d("80"), null, d("82"), Direction.BUY))
    }
    @Test fun openingCode() {
        assertEquals("281", Rules.openCode(d("22964.50")))
        assertEquals("324", Rules.openCode(d("74191.46")))
    }
}
