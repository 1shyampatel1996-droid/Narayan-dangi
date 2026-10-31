package `in`.narayanscanner
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.math.BigDecimal
import org.junit.Assert.*
import org.junit.Test
class TickDecoderTest {
    @Test fun quotePacketScalingAndIdentity() {
        val bytes = ByteArray(123)
        val b = ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN)
        b.put(0, 2.toByte()); b.put(1, 2.toByte())
        "12345".toByteArray().copyInto(bytes, 2)
        b.putLong(35, 1793420000000L); b.putLong(43, 8200L); b.putLong(91, 8900L)
        val tick = TickDecoder.decode(bytes)!!
        assertEquals("2:12345", tick.key)
        assertEquals(BigDecimal("82.00"), tick.ltp)
        assertEquals(BigDecimal("89.00"), tick.open)
        assertEquals(1793420000000L, tick.exchangeMillis)
    }
    @Test fun incompleteOrLtpOnlyPacketsCannotCreateOpenSignals() {
        assertNull(TickDecoder.decode(ByteArray(51)))
        val bytes = ByteArray(123); bytes[0] = 1
        assertNull(TickDecoder.decode(bytes))
    }
}
