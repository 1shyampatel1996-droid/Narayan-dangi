package `in`.narayanscanner

import java.time.Instant
import java.time.LocalDate
import java.time.ZoneId

/** Policy only. The broker must authenticate the OTP before creating a session.
 * Store tokens through Android Keystore-backed encryption, never in plain preferences.
 * Never persist the OTP, PIN or authenticator seed here.
 */
data class BrokerSession(val authenticatedAt: Instant, val expiresAt: Instant, val revoked: Boolean = false)
object SessionPolicy {
    private val india = ZoneId.of("Asia/Kolkata")
    fun canResume(session: BrokerSession?, now: Instant): Boolean =
        session != null && !session.revoked &&
            now >= session.authenticatedAt && now < session.expiresAt &&
            LocalDate.ofInstant(session.authenticatedAt, india) == LocalDate.ofInstant(now, india)
}
