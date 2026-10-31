package `in`.narayanscanner
import java.time.Instant
import org.junit.Assert.*
import org.junit.Test
class SessionPolicyTest {
    private fun t(value: String) = Instant.parse(value)
    @Test fun resumeSameIndianDayOnly() {
        val s = BrokerSession(t("2026-10-31T03:30:00Z"), t("2026-11-01T03:30:00Z"))
        assertTrue(SessionPolicy.canResume(s, t("2026-10-31T07:40:00Z")))
        assertFalse(SessionPolicy.canResume(s, t("2026-10-31T18:30:00Z")))
    }
    @Test fun expiredRevokedAndMissingRequireLogin() {
        val s = BrokerSession(t("2026-10-31T03:30:00Z"), t("2026-10-31T07:00:00Z"))
        assertFalse(SessionPolicy.canResume(s, s.expiresAt))
        assertFalse(SessionPolicy.canResume(s.copy(revoked = true), t("2026-10-31T04:00:00Z")))
        assertFalse(SessionPolicy.canResume(null, t("2026-10-31T04:00:00Z")))
    }
}
